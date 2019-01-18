from gensim.models.doc2vec import Doc2Vec
from services import logger
logger = logger.Loggers(__name__).get_logger()

class Doc2VecBase(object):

    def __init__(self, sku, path):
        self.sku = sku
        self.path = path

    def _load_model(self):
        """
        Load a trained model if one already exists for a given sku.
        Otherwise, return None.

        return model: a previously trained model or None

        #TODO: could models belonging to products from different merchants
        #TODO: have conflicting names due to identical SKUs? How likely is this?
        """
        self.path += "/" + self.sku
        model = None
        try:
            model = Doc2Vec.load(self.path)
            logger.info("Model successfully loaded")
        except IOError:
            logger.warn("Model not found")
        return model