import time
import db as DB
from ml import training, inference, qna_classifier
from nlp import preprocess
from os import listdir
from os.path import isfile, join
from parser import parser
import pymongo
import re
from scraper import scraper, sc_helper
from services import logger
import yaml
logger = logger.Loggers(__name__).get_logger()
config = None
with open('config.yaml') as f:
    config = yaml.safe_load(f)

db_status = DB.init_db(config.get("status_db")).job_status
__error__ = config.get("misc").get("error_msg")
__ready__ = "Ready"

"""******************************************************************************
Site operations can be interrupted at any point in the data processing workflow. 
We should continue the work from where it was left off instead of repeating the 
operations or making duplicate http requests. The general rule is as follows:

        Interrupted during or right after | What to do
        -----------------------------------------------------------------------
        Product detail scraping/parsing   | Do it again if review_count not available
        Review scraping/parsing           | Only scrape+parse what's in the queue
        NLP                               | Do it again (skip if model trained)
        Training                          | Do it again (skip if model trained)
"""
def _db_product_details(sku):
    """
    Return product details from the database.
    """
    db_details = DB.init_db(config.get("details_db")).product_details
    product = list(db_details.find({"sku": sku}))
    if product:
        product_name = product[0].get("product_name")
        product_url = product[0].get("url")
        image_url = product[0].get("img")
        review_count = product[0].get("review_count")
        page_count =  product[0].get("review_page_count")
        valid = all([product_name, product_url, image_url, review_count, page_count])
        if valid:
            return {
                    "product_name": product_name,
                    "review_count": review_count,
                    "page_count": page_count,
            }
        else:
            logger.info("Unable to validate product details for {}. Deleting entry".format(sku)) 
            db_details.delete_one({"sku": sku})
    return {}



def _detail_parsed(sku):
    """
    Return True if the detail page of sku has been parsed. Return
    False otherwise.

    :param sku: product sku
    :return: whether or not the product detail page has been parsed
    """
    if _db_product_details(sku):
        logger.info("Product detail page for {} has already been parsed".format(sku))
        return True
    logger.info("Product detail page for {} is yet to be downloaded and parsed".format(sku))
    return False 

def _is_in_queue(sku):
    """Return True if any URLs belonging to sku are in the queue. Return False
    otherwise. 

    :param sku: product sku
    :return: whether or not there are review urls in queue
    """
    db_q = DB.init_db(config.get("queue_db")).queue
    queue = list(db_q.find({"sku": sku}))
    if len(queue) > 0: 
        logger.info(sku + " is already in the queue")
        return True 
    return False

def _reviews_scraped(sku):
    """
    Return True if sku reviews have been parsed. Return False otherwise.

    :param sku: product sku
    :return: whether or not the reviews have been scraped+parsed+ingested
    """
    db_raw = DB.init_db(config.get("ingestion_db")).raw 
    feed = list(db_raw.find({"sku": sku}))
    if len(feed) > 0:
        logger.info(sku + " reviews have been parsed and ingested")
        return True
    logger.info(sku + " has neither been parsed nor ingested")
    return False 
     
def _nlp_reset(sku):
    """
    Clear the database of any existing sentences for sku.

    :param sku: product sku
    """ 
    db_sents = DB.init_db(config.get("sent_db")).sentences
    db_sents.delete_many({"sku": sku})
    logger.info("Cleared sentence table for " + sku)

def _is_trained(sku):
    """
    Return True if a model has already been trained for this product. Return
    False otherwise.

    :param sku: product sku
    :return: whether or not there is a doc2vec model
    """
    #TODO: Always best to retrain with more data so if there are new raw reviews, retrain
    mypath = config.get("doc2vec").get("path")
    onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    if sku in onlyfiles:
        _set_status(__ready__, sku)
        logger.info(sku + " has a trained model")
        return True 
    logger.info(sku + " does not have a trained model. Start training")
    return False 

"""******************************************************************************"""

def _decode_url(url):
    """
    Decode the url for merchant name and product sku. Then build the 
    canonical url.

    :param url: the raw url (may not be canonical)
    return decoded: a list of the merchant name, sku, and url
    """
    
    if "amazon.com" not in url: return 
    suffix = "gp/product"
    tokens = re.findall("/gp/product/\w{10}", url)
    if not tokens: 
        tokens = re.findall("/dp/\w{10}", url)
        suffix = "dp"
    if not tokens:
        # handle mobile URLs 
        tokens = re.findall("/gp/aw/d/\w{10}", url)
        suffix = "dp" # are we sure about this? 
    if not tokens: return 
    try:
        sku = tokens[0].split("/")[-1]
        canonical = "https://www.amazon.com" + "/" + suffix + "/" + sku 
        return ("Amazon", sku, canonical)
    except Exception:
        return 

def vote_to_db(question, answer, sku, up_count, down_count):
    """
    Save user voting on question-answer pair to the database.
    Saving every question-answer combination as a unique pair would 
    result in many duplicate entries in the database. Please refer to 
    the comments to the question/answer pair classifier for more details
    on how deal with this problem.
    """
    db_votes = DB.init_db(config.get("votes_db")).votes 
    record = {
        "question": question,
        "answer": answer,
        "sku": sku,
        "up_count": up_count,
        "down_count": down_count
    }
    classifier = qna_classifier.Classify(record)
    classifier.put_votes(db_votes)
    logger.info("Received new voting data for {} and question: {}".format(sku, question))

def get_status(sku):
    res = None
    try:
        msg = list(db_status.find({"sku": sku}))[0]
        msg = msg.get("msg")
        db_details = DB.init_db(config.get("details_db")).product_details
        product = list(db_details.find({"sku": sku}))
        product_url, product_name, image_url, sku = "", "", "", ""
        if product: 
            product_name = product[0].get("product_name")
            product_url = product[0].get("url")
            image_url = product[0].get("img")
            sku = product[0].get("sku")
        logger.info("Status for {} is {}".format(sku, msg))
        return {
            "status": msg,
            "product_name": product_name,
            "product_url": product_url,
            "image_url": image_url,
            "sku": sku,
        }
    except IndexError:
        # this happens due to a race condition because the sku hasn't been
        # added to the database yet
        logger.warning("Product status not yet available")
        # pass
    return {}
        
    
def _set_status(msg, sku):
    """
    Update current work status.

    :param msg: status message
    :param sku: product sku
    """
    record = {"msg": msg, "sku": sku}
    if (len(list(db_status.find({"sku": sku}))) == 0):
        db_status.insert_one(record)
    else: db_status.update_one({"sku": sku}, {"$set": {"msg": msg}})
    
    
def _get_product_details(source, url, sku):
    """
    Scrape product metadata.

    :param url: canonical product url
    :return number of reviews and product name
    """
    sc = scraper.Scraper(source=source)
    response = sc.get_request(url)
    pr = parser.Parser(sku=sku, source=source)
    res = pr.parse(response, init=True)
    if res:
        # Save it to the database
        db_details = DB.init_db(config.get("details_db"))
        db_details = db_details.product_details 
        record = {
            "status": "processing",
            "url": url,
            "product_name": res.get("product_name"),
            "review_count": res.get("review_count"),
            "review_page_count": res.get("page_count"), 
            "source": source,
            "sku": sku,
            "img": res.get("img_url"),
            "timestamp": time.time(),
        }
        db_details.insert_one(record)
        logger.info("Saved new product details: ")
        logger.info(record)
    return res

def get_answer(question, sku):
    """
    Open a websocket and keep the connection alive for the duration 
    of the session so that the sku model is loaded only once. 
    """
    db_votes = DB.init_db(config.get("votes_db")).votes
    inf = inference.Inference(sku)
    answer, confidence = inf.infer(question)
    classifier = qna_classifier.Classify({"question": question, "answer": answer, "sku": sku})
    votes = classifier.get_votes(db_votes)
    response = {"confidence": confidence,
                "answer": answer,
            }
    response.update(votes)
    return response

def get_most_recent():
    """
    Get the most recent three items that have been analyzed.
    """
    db_recent = DB.init_db(config.get("details_db")).product_details
    res = list(db_recent.find({"status": "ready"}).sort('timestamp', pymongo.DESCENDING))
    items = []
    try:
        for i in range(3):
            obj = res[i]
            title = obj.get("product_name")
            _max_length = config.get("misc").get("max_title_length")
            if len(title) > _max_length:
                title = title[:_max_length]
                title += "..."
            item = {
                "image_url": obj.get("img"), 
                "title": title,
                "product_url": obj.get("url"),
                "sku": obj.get("sku")
            }
            items.append(item)
    except IndexError:
        pass 
    return items
    

def _update_details_db(sku):
    """
    Update the status field of 
    """
    db_details = DB.init_db(config.get("details_db")).product_details
    record = {"status": "ready"}
    db_details.update_one({"sku": sku}, {"$set": record})


def _workflow(decoded, url):
    """
    Run the whole data scraping, processing, and analysis in new threads.
    Each thread, beginning with this one, will make its calls in a try-except
    block. Why do it this way? Because the parent thread that launched this 
    thread dies immediately. Therefore, when an exception is raised in the child
    thread, there's no one to receive it. This is bad for the client. The client
    relies on the status of the job. If an exception is raised in the child thread,
    the thread would die and the status would no longer be updated. This would cause
    the client to stall forever with a progress animation. If an exception 
    is raised, we want to update the status right away so that the user 
    doesn't have to wait. 

    All operations down the line like scraping or some other launch their own 
    child threads. Those operations also need to update the status before 
    exiting.
    """
    logger.info("Running a new thread for scraping and data processing")
    source = decoded[0]
    sku = decoded[1]
    url = decoded[2]
    parsed = _db_product_details(sku)
    _set_status("Gathering data", sku)
    try:
        # Has the detail page been parsed?
        if not parsed:
            logger.info("Detail page not available for {}. Proceeding to download...".format(sku))
            parsed = _get_product_details(source, url, sku)
            if not parsed:
                logger.error("Error while parsing product detail page for " + sku)
                logger.error("Aborting process")
                _set_status(__error__, sku)
                return 
        else:
            logger.info("Detail page for {} already parsed. Skipping download...".format(sku))
        prod_name = parsed.get("product_name")
        review_count = parsed.get("review_count")
        page_count = parsed.get("page_count")
        
        # Do we have enough data to train on?
        if review_count <= config.get("misc").get("min_review_count"):
            logger.warning("Not enough reviews for " + sku)
            logger.error("Aborting process")
            _set_status("Not Enough Data", sku)
            return
        # If it's not in the queue, add it
        if not _is_in_queue(sku):
            logger.info(sku + " not in queue. Checking if it's been scraped before")
            if not _reviews_scraped(sku):
                logger.info(sku + " has not been scraped. Adding to the queue...")
                sc_helper.add_to_queue(source, sku, page_count)
        # If it's in the queue, scrape it 
        if _is_in_queue(sku):
            logger.info(sku + " is in the queue. Launching the scraper")
            sc_helper.scrape(sku, prod_name, source)
        
        # If it hasn't been trained, train it
        if not _is_trained(sku):
            _nlp_reset(sku)
            logger.info("Starting NLP preprocessing")
            _set_status("Analyzing language", sku)
            preprocess.NLPreprocessor(sku).tokenize()
            logger.info("Finished NLP preprocessing")
            logger.info("Starting model trianing")
            _set_status("Building knowledge base", sku)
            d2v = training.Document2Vector(sku).train()
            logger.info("Finished model training")
            _update_details_db(sku)
            _set_status("Ready", sku)
    except Exception as e:
        logger.exception(e)
        _set_status(__error__, sku)


def start(url, progress=False):
    """
    Initiate scraping, parsing, data ingestion, preprocessing, 
    and training. Note that this is a blocking call. Flask will wait on start(). 
    We don't want that. We want the script to return control to Flask immediately
    and continue with the data processing. That way, the sku status can be updated
    at the appropriate time and everyone is happy :). 
    """
    logger.info("Received new url to process: {}".format(url))
    decoded = _decode_url(url)
    if not decoded: return {}
    if progress:
        sku = decoded[1]
        __in_progress__ = True
        status = get_status(sku)
        if status.get("status") == __ready__: __in_progress__ = False
        response = {
                    "sku": sku, 
                    "product_url": decoded[2], 
                    "in_progress": __in_progress__,
                }
        response.update(status)
        return response
    else:
        _workflow(decoded, url) # Enable when debugging
