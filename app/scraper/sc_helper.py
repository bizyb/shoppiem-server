from concurrent.futures import ThreadPoolExecutor
import db as DB
import pymongo
import random
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
    url_objs = list(q_db.find({"sku": sku}).sort('timestamp', pymongo.ASCENDING))
    if url_objs: random.shuffle(url_objs)
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        sc = scraper.Scraper(sku, prod_name, source)
        for url_obj in url_objs: 
            url = url_obj.get("url")
            sc.get_request(url, init=False) # Enable when debugging
            # executor.submit(sc.get_request, url, init=False) # Disable when debugging










