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
    if ("amazon.com" and "/dp") not in url:
        return
    tokens = url.split("/dp/")
    sku = tokens[-1].split("/")[0]
    canonical = tokens[0] + "/dp/" + sku 
    return ("Amazon", sku, canonical)

def get_status(sku):
    print "Getting status ==================================== "
    res = None
    try:
        # print "all db content: ", list(db.job_status.find())
        # print "sku db content: ", sku, list(db.job_status.find({"sku": sku}))
        res = list(db.job_status.find({"sku": sku}))[0]
        return res.get("msg")
    except IndexError as e:
        # this happens due to a race condition because the sku hasn't been
        # saved to the database yet
        print e
        pass
    
    

def _set_status(msg, sku):
    """
    Update current work status.

    :param msg: status message
    :param sku: product sku
    """
    
    print "Setting the status to=================================> ", msg
    record = {"msg": msg, "sku": sku}
    if (len(list(db.job_status.find({"sku": sku}))) == 0):
        db.job_status.insert_one(record)
    else: db.job_status.update_one({"sku": sku}, {"$set": {"msg": msg}})
    
    
def _get_product_details(source, url):
    """
    Scrape product metadata.

    :param url: canonical product url
    :return number of reviews and product name
    """
    sc = scraper.Scraper(source=source)
    response = sc.get_request(url)
    pr = parser.Parser(source=source)
    return pr.parse(response, init=True)

def get_answer():
    time.sleep(5)
    
def test_status_update(url):
    print "in test_status_update"
    sku = "0972683275"
    _set_status("Checking url for validity", sku)
    time.sleep(2)
    _set_status("Adding to queue", sku)
    time.sleep(2)
    _set_status("Gathering data", sku)
    time.sleep(2)
    _set_status("Analyzing language", sku)
    time.sleep(2)
    _set_status("Building knowledge base", sku)
    time.sleep(2)
    _set_status("Ready", sku)



def _threaded(decoded, url):
    print "Thread function running!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    return test_status_update(url)
    sku = decoded[1]
    _set_status("Gathering item details", sku)
    parsed = _get_product_details(decoded[0], decoded[-1])
    prod_name, review_count, page_count = parsed

    if review_count <= config.get("misc").get("min_review_count"):
        _set_status("Not Enough Data", sku)
        return

    if not sc_helper.in_inventory(sku):
        _set_status("Adding to queue", sku)
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

    
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(_threaded, decoded, url)
    executor.shutdown(wait=False)
    response = {"sku": decoded[1], "product_url": decoded[2], "in_progress": True}
    return response



# url = "https://www.amazon.com/All-new-Kindle-Paperwhite-Waterproof-Storage/dp/B07CXG6C9W/ref=redir_mobile_desktop?_encoding=UTF8&ref_=ods_gw_ha_eink_ms_jan"
# start(url)
# # 0972683275"




