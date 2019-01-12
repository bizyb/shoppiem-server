import db as DB
from services import logger
import yaml
logger = logger.Loggers(__name__).get_logger()

config = None
with open('config.yaml') as f:
    config = yaml.safe_load(f)
db = DB.init_db(config.get("ingestion_db"))

def ingest(raw, source):
    """
    Save raw product reviews to the database.

    :param raw: a dictionary (JSON) containing all reviews
    """
    keys = config.get("merchants").get(source)
    for entry in raw:
        record = {
                "product_name": "",
                "source": source,
                "sku": entry.get(keys.get("sku")),
                "review_text": entry.get(keys.get("review_text"))
        }
        # Create/load raw collection
        raw = db.raw 
        raw.update(record, record, upsert=True)