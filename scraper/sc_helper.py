from concurrent.futures import ThreadPoolExecutor
import db as DB
import pymongo
from services import logger
import scraper
import yaml
logger = logger.Loggers(__name__).get_logger()

config = None
base_urls = None
with open('config.yaml') as f:
    config = yaml.safe_load(f)
with open('scraper/base_urls.yaml') as f:
    base_urls = yaml.safe_load(f)
db = DB.init_db(config.get("status_db"))

 # logger.info("Starting data ingestion")
    # # ingestion.ingest(raw, source)
    # logger.info("Finished data ingestion")

def in_inventory(sku):
    """
    Return True if the sku is already in the queue or has a previously
    trained model.

    :param sku: product sku
    :return: whether or not the sku is in inventory
    """
    is_in_queue = False
    is_ready = False
    q_db = DB.init_db(config.get("queue_db"))
    queue = list(q_db.sku_queue.find({"sku": sku}))
    if len(queue) > 0 : is_in_queue = True 

    db_job_status = DB.init_db(config.get("jobs_db"))
    res = list(db.job_status.find({"sku": sku}))
    if len(res) > 0 : 
        if res[0].get("msg") == "Ready":
            is_ready = True
    return is_ready or is_in_queue

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

    q_db = DB.init_db(config.get("queue_db"))
    for url in urls:
        record = {
                "url": url,
                "sku": sku,
                "done": False
        }
        q_db.queue.update(record, record, upsert=True)
    
def scrape(sku, prod_name, source):
    """
    Run the scraper until the queue is empty.

    #TODO: if something is funky, disable executor call. It suppresses
    exceptions.
    """
    thread_count = config.get("scraper").get("thread_count")
    q_db = DB.init_db(config.get("queue_db")) 
    urls = q_db.queue.find({"sku": sku}).sort('timestamp', pymongo.ASCENDING)
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        sc = scraper.Scraper(sku, prod_name, source)
        for url in urls[:1]:
            url = url.get("url")
            sc.get_request(url, init=False)
            # executor.submit(sc.get_request, url, init=False)










