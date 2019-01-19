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
    print "================_set_status--------entering....-------------"
    record = {"msg": msg, "sku": sku}
    if (len(list(db_status.find({"sku": sku}))) == 0):
        db_status.insert_one(record)
    else: db_status.update_one({"sku": sku}, {"$set": {"msg": msg}})
    print "================_set_status--------returning....-------------"




# def in_inventory(sku):
#     """
#     Return True if the sku is already in the queue or has a previously
#     trained model. It's possible that the job for sku could have been 
#     interrupted at any point along the process.If this is true, we would 
#     like to avoid any time-intensive steps. 
#         Interrupted during or right after | What to do
#         -----------------------------------------------------------------------
#         Product detail scraping/parsing   | Do it again if review_count not available
#         Review scraping/parsing           | Only scrape+parse what's in the queue
#         NLP                               | Do it again (skip if model trained)
#         Training                          | Do it again (skip if model trained)

#     :param sku: product sku
#     :return: whether or not the sku is in inventory
#     """
#     print "================in_inventory--------entering....-------------"
#     # is there a model available?
#     mypath = config.get("doc2vec").get("path")
#     onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
#     if sku in onlyfiles:
#         _set_status("Ready", sku)
#         return True

#     is_in_queue = False
#     is_ready = False
#     print "================in_inventory--------waiting on db for queue status....-------------"
#     queue = list(q_db.find({"sku": sku}))
#     if len(queue) > 0: is_in_queue = True 

#     record = {"msg": "Ready", "sku": sku}
#     res = list(db_status.find(record))
#     if len(res) > 0: is_ready = True 
#     print "================in_inventory--------returning....-------------"
#     return {"is_ready": is_ready, "is_in_queue":is_in_queue}

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

def add_to_queue(source, sku, page_count):
    """
    Generate review URLs and add them to the queue.

    :param source: merchant
    :param sku: product sku
    :param page_count: number of pages with reviews
    """ 
    urls = _build_urls(source, sku, page_count)
    for url in urls:
        record = {
                "url": url,
                "sku": sku,
                "timestamp": time.time(),
        }
        q_db.update(record, record, upsert=True)
    logger.info("Added new URLs to the queue for " + sku)
    
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










