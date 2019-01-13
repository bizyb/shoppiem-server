import db as DB
from services import logger
import yaml
logger = logger.Loggers(__name__).get_logger()

config = None
with open('config.yaml') as f:
    config = yaml.safe_load(f)
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
    queue = list(db.sku_queue.find({"sku": sku}))
    if len(queue) > 0 : is_in_queue = True 

    db_job_status = DB.init_db(config.get("jobs_db"))
    res = list(db.job_status.find({"sku": sku}))
    if len(res) > 0 : 
        if res[0].get("msg") == "Ready":
            is_ready = True
    
    return is_ready or is_in_queue

def add_to_queue(source, sku, page_count):
    """
    Generate review URLs and add them to the queue.

    :param source: merchant
    :param sku: product sku
    :param page_count: number pages with reviews
    """ 

    

