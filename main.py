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
    res = list(db.job_status.find({"sku": sku}))[0]
    return res.get("msg")

def _set_status(msg, sku):
    """
    Update current work status.

    :param msg: status message
    :param sku: product sku
    """
    record = {"msg": msg, "sku": sku}
    db.job_status.update(record, record, upsert=True)
    
def _get_product_details(source, url):
    """
    Scrape product metadata.

    :param url: canonical product url
    :return number of reviews and product name
    """
    sc = scraper.Scraper()
    response = sc.get_request(url)
    pr = parser.Parser(source)
    return pr.parse(response, init=True)

def start(url):
    """
    Initiate scraping, parsing, data ingestion, preprocessing, 
    and training. 
    """
    
    decoded = _decode_url(url)
    if not decoded:
        return "Unsupported URL"
   
    sku = decoded[1]
    _set_status("Gathering item details", sku)
    parsed = _get_product_details(decoded[0], decoded[-1])
    prod_name, review_count, page_count = parsed

    if review_count <= config.get("misc").get("min_review_count"):
        return "Not enough data"

    if not sc_helper.in_inventory(sku):
        _set_status("Adding to queue", sku)
        sc_helper.add_to_queue(decoded[0], decoded[1], parsed[-1])
        _set_status("Gathering data", sku)
        sc_helper.scrape(sku, prod_name, decoded[0])
        # sc_helper.parse(sku)

        _set_status("Analyzing language", sku)
        # logger.info("Starting NLP preprocessing")
        # # preprocess.NLPreprocessor(sku).tokenize()
        # logger.info("Finished NLP preprocessing")

        _set_status("Building knowledge base", sku)
        # logger.info("Starting model trianing")
        # d2v = training.Document2Vector(sku).train()
        # logger.info("Finished model training")

    return "Ready"

url = "https://www.amazon.com/All-new-Kindle-Paperwhite-Waterproof-Storage/dp/B07CXG6C9W/ref=redir_mobile_desktop?_encoding=UTF8&ref_=ods_gw_ha_eink_ms_jan"
start(url)
# 0972683275"




