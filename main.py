import ingestion
from nlp import preprocess
from ml import training, inference
from services import logger
logger = logger.Loggers(__name__).get_logger()

def start(raw, source, sku):
    """
    Initiate data ingestion, preprocessing, and training.
    """
    logger.info("Starting data ingestion")
    # ingestion.ingest(raw, source)
    logger.info("Finished data ingestion")

    logger.info("Starting NLP preprocessing")
    # preprocess.NLPreprocessor(sku).tokenize()
    logger.info("Finished NLP preprocessing")

    logger.info("Starting model trianing")
    d2v = training.Document2Vector(sku).train()
    logger.info("Finished model training")


start(None, None, "0972683275")


