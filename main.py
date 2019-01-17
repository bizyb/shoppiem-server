import time
from concurrent.futures import ThreadPoolExecutor
import db as DB
# import ingestion
from ml import training, inference
from nlp import preprocess
from parser import parser
import pymongo
from scraper import scraper, sc_helper
from services import logger
import yaml
logger = logger.Loggers(__name__).get_logger()
config = None
with open('config.yaml') as f:
    config = yaml.safe_load(f)
db = DB.init_db("status_db")

def _decode_url(url):
    """
    Decode the url for merchant name and product sku. Then build the 
    canonical url.

    :param url: the raw url (may not be canonical)
    return decoded: a list of the merchant name, sku, and url
    """
    # TODO: there are many more URL types to handle 

    if ("amazon.com" and "/dp") not in url:
        return
    tokens = url.split("/dp/")
    sku = tokens[-1].split("/")[0]
    canonical = tokens[0] + "/dp/" + sku 
    return ("Amazon", sku, canonical)

def vote_to_db(question, answer, sku, vote):
    """
    Save user voting on question-answer pair to the database.
    TODO: Could we ever get duplicate key conflict?
    """
    db_votes = DB.init_db(config.get("votes_db")).votes 
    record = {
        "question": question,
        "answer": answer,
        "sku": sku,
        "vote": vote
    }
    db_votes.insert_one(record)


def get_status(sku):
    res = None
    try:
        msg = list(db.job_status.find({"sku": sku}))[0]
        msg = msg.get("msg")
        # print "==in get_status======msg: ", msg, sku 
        db_details = DB.init_db(config.get("details_db")).product_details
        product = list(db_details.find({"sku": sku}))[0]
        return {
            "status": msg,
            "product_name": product.get("product_name"),
            "product_url": product.get("url"),
        }

    except IndexError as e:
        # this happens due to a race condition because the sku hasn't been
        # saved to the database yet
        logger.error(e)
        
    
def _set_status(msg, sku):
    """
    Update current work status.

    :param msg: status message
    :param sku: product sku
    """
    # print "setting status================================= ", sku, msg
    record = {"msg": msg, "sku": sku}
    if (len(list(db.job_status.find({"sku": sku}))) == 0):
        db.job_status.insert_one(record)
    else: db.job_status.update_one({"sku": sku}, {"$set": {"msg": msg}})
    
    
def _get_product_details(source, url, sku):
    """
    Scrape product metadata.

    :param url: canonical product url
    :return number of reviews and product name
    """
    # response = "DEBUGGGGGG"
    sc = scraper.Scraper(source=source)
    response = sc.get_request(url)
    pr = parser.Parser(source=source)
    res = pr.parse(response, init=True)
    if res:
        # Save it to the database
        db_details = DB.init_db(config.get("details_db"))
        db_details = db_details.product_details 
        record = {
            "status": "processing",
            "url": url,
            "product_name": res[0],
            "review_count": res[1],
            "review_page_count": res[2], 
            "source": source,
            "sku": sku,
            "img": res[3]
        }
        db_details.insert_one(record)

    return res

def get_answer(question, sku):
    """
    Open a websocket and keep the connection alive for the duration 
    of the session so that the sku model is loaded only once. 
    """
    time.sleep(5)
    response = {"confidence": 0.85,
                "question": "What is the meaning of life?",
                "answer": 42
            }
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
            item = {
                "img": obj.get("img"), 
                "title": obj.get("product_name"),
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
    db_details = DB.init_db(config.get("details_db"))
    db_details = db_details.product_details
    record = {"status": "ready"}
    db_details.update_one({"sku": sku}, {"$set": record})


def _threaded(decoded, url):

    sku = decoded[1]
    _set_status("Gathering item details", sku)
    parsed = _get_product_details(decoded[0], decoded[-1], sku)
    if not parsed: 
        """
        Unable to parse the details page so cannot move forward.
        """
        _set_status("Parsing Error", sku)
        return

    prod_name, review_count, page_count, img = parsed
    if review_count <= config.get("misc").get("min_review_count"):
        _set_status("Not Enough Data", sku)
        return

    if not sc_helper.in_inventory(sku):
        _set_status("Waiting to be picked up from queue", sku)
        sc_helper.add_to_queue(decoded[0], decoded[1], parsed[-1])
        _set_status("Gathering data", sku)
        sc_helper.scrape(sku, prod_name, decoded[0])
       
        _set_status("Analyzing language", sku)
        logger.info("Starting NLP preprocessing")
        preprocess.NLPreprocessor(sku).tokenize()
        logger.info("Finished NLP preprocessing")

        _set_status("Building knowledge base", sku)
        logger.info("Starting model trianing")
        d2v = training.Document2Vector(sku).train()
        logger.info("Finished model training")
        _update_details_db(sku)
        _set_status("Ready", sku)


def start(url):
    """
    Initiate scraping, parsing, data ingestion, preprocessing, 
    and training. Note that this is a blocking call. Flask will wait on start(). 
    We don't want that. We want the script to return control to Flask immediately
    and continue with the data processing. That way, the sku status can be updated
    at the appropriate time and everyone is happy :). 
    """
    decoded = _decode_url(url)
    if not decoded: return {}
    # _threaded(decoded, url)
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(_threaded, decoded, url)
    executor.shutdown(wait=False)
    response = {"sku": decoded[1], "product_url": decoded[2], "in_progress": True}
    return response



# url = "https://www.amazon.com/All-new-Kindle-Paperwhite-Waterproof-Storage/dp/B07CXG6C9W/ref=redir_mobile_desktop?_encoding=UTF8&ref_=ods_gw_ha_eink_ms_jan"
# start(url)
# # 0972683275"




# https://www.amazon.com/Dell-Screen-LED-Lit-Monitor-S2418H/dp/B06XYSZRQT/ref=pd_ybh_a_3?_encoding=UTF8&psc=1&refRID=EAAK98ZMTWNX5S28XRXT



#unsupported url
# https://www.amazon.com/gp/product/B075ZYR6VK/ref=s9_acsd_al_bw_c_x_3_w?pf_rd_m=ATVPDKIKX0DER&pf_rd_s=merchandised-search-7&pf_rd_r=YAAGZ9808TP4D5BMEWCK&pf_rd_r=YAAGZ9808TP4D5BMEWCK&pf_rd_t=101&pf_rd_p=68591a72-1aae-4981-b0e3-232056249df1&pf_rd_p=68591a72-1aae-4981-b0e3-232056249df1&pf_rd_i=17877490011