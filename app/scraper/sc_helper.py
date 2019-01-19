from concurrent.futures import ThreadPoolExecutor
import db as DB
from os import listdir
from os.path import isfile, join
import pymongo
from services import logger
import scraper
import time
import yaml
logger = logger.Loggers(__name__).get_logger()

config = None
base_urls = None
with open('config.yaml') as f:
    config = yaml.safe_load(f)
with open('scraper/base_urls.yaml') as f:
    base_urls = yaml.safe_load(f)

q_db = DB.init_db(config.get("queue_db")).queue
db_status = DB.init_db(config.get("status_db")).job_status

def _set_status(msg, sku):
    """
    Update current work status.

    :param msg: status message
    :param sku: product sku
    """
    print "====================DEBUG 102=================="
    record = {"msg": msg, "sku": sku}
    if (len(list(db_status.find({"sku": sku}))) == 0):
        print "====================DEBUG 103=================="
        db_status.insert_one(record)
        print "====================DEBUG 104=================="
    else: db_status.update_one({"sku": sku}, {"$set": {"msg": msg}})
    print "====================DEBUG 105=================="

def in_inventory(sku):
    """
    Return True if the sku is already in the queue or has a previously
    trained model.

    :param sku: product sku
    :return: whether or not the sku is in inventory
    """
    print "====================DEBUG 100=================="

    # is there a model available?
    mypath = config.get("doc2vec").get("path")
    onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    if sku in onlyfiles:
        print "====================DEBUG 101=================="
        _set_status("Ready", sku)
        return True

    print "====================DEBUG 106=================="
    is_in_queue = False
    is_ready = False
    queue = list(q_db.find({"sku": sku}))
    print "====================DEBUG 107=================="
    if len(queue) > 0: is_in_queue = True 

    record = {"msg": "Ready", "sku": sku}
    res = list(db_status.find(record))
    print "====================DEBUG 108=================="
    if len(res) > 0: is_ready = True 
    print "====================DEBUG 109=================="
    return {"is_ready": is_ready, "is_in_queue":is_in_queue}

def _build_urls(source, sku, page_count):
    """
    Generate review page urls using the page_count and merchant-specific
    url attributes.

    :param source: merchant
    :param sku: product sku
    :param page_count: number of pages of reviews
    :return urls: a list of the generated urls
    """
    urls = []
    base, landing, prefix, suffix = None, None, None, None
    if source.lower() == "amazon":
        base = base_urls.get("amazon")
        landing = base + 'product-reviews/' + sku 
        prefix = landing + '?pageNumber='
        suffix = '&reviewerType=all_reviews'
    
    for i in range(page_count):
        review_url = prefix + str(i+1)
        if suffix != None: review_url += suffix
        urls.append(review_url)
    return urls

def add_to_queue(source, sku, page_count, in_queue=False):
    """
    Generate review URLs and add them to the queue.

    :param source: merchant
    :param sku: product sku
    :param page_count: number of pages with reviews
    """
    if not in_queue: 
        urls = _build_urls(source, sku, page_count)
        for url in urls:
            record = {
                    "url": url,
                    "sku": sku,
                    "timestamp": time.time(),
            }
            q_db.update(record, record, upsert=True)
    logger.info(sku + " is already in the queue. No new URLs generated.")
    
def scrape(sku, prod_name, source):
    """
    Run the scraper until the queue is empty.
    """
    thread_count = config.get("scraper").get("thread_count")
    urls = q_db.find({"sku": sku}).sort('timestamp', pymongo.ASCENDING)
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        sc = scraper.Scraper(sku, prod_name, source)
        for url in urls:
            url = url.get("url")
            executor.submit(sc.get_request, url, init=False)










