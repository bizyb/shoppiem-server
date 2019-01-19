import db as DB
from services import logger
import yaml
logger = logger.Loggers(__name__).get_logger()

config = None
with open('config.yaml') as f:
    config = yaml.safe_load(f)
db = DB.init_db(config.get("ingestion_db"))

def ingest(raw):
    """
    Save raw product reviews to the database.

    :param raw: a dictionary (JSON) containing all reviews
    """
    for record in raw:
        # Create/load raw collection
        raw = db.raw 
        raw.update(record, record, upsert=True)
        logger.info("Added record to raw feed db")