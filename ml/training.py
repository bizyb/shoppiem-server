from __base__ import Doc2VecBase
from collections import namedtuple
import db as DB
from gensim.models.doc2vec import Doc2Vec
import random
import re
from services import logger
import yaml
logger = logger.Loggers(__name__).get_logger()

config = None
with open('config.yaml') as f:
    config = yaml.safe_load(f)
db = DB.init_db(config.get("sent_db"))

class Document2Vector(Doc2VecBase):
    '''
    Performs doc2vec modeling using gensim's doc2vec implementation.
    '''
    def __init__(self, data, sku):
        self.data = data
        path = config.get("doc2vec").get("path") 
        super(Document2Vector, self).__init__(sku, path) 
        
    def _tagged_docs(self):
        '''
        Return the training data as a tuple of sentence-uuid tag pairs.

        return tagged_docs: a list of 2-element tuples  
        '''
        TaggedDocuments = namedtuple('TaggedDocuments', 'words tags')
        tagged_docs =[]
        for doc in self.data:
            tags = self._get_sent_tags(doc)
            for tag in tags:
                words = doc.get(tag)
                obj = TaggedDocuments(words=words, tags=[tag])
                tagged_docs.append(obj)
        return tagged_docs 
    
    def _get_sent_tags(self, doc):
        """
        Get all sentence tags for a given tag with regex pattern matching.
        In order to allow for a constant reverse sentence lookup, we're using
        a 'flat' document structure, where UUIDs are used as keys for sentences.

        :param doc: a database record of raw data 
        :return tags: a list of tags 
        """
        pattern = '[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}'
        tags = []
        for key in doc.keys():
            found = re.findall(pattern, key)
            if found: tags.append(found[0])
        return tags

    def _get_params(self):
        """
        Set doc2vec training parameters.

		Default arguments:
		Doc2Vec(documents=None, dm_mean=None, dm=1, dbow_words=0, dm_concat=0, 
				dm_tag_count=1, docvecs=None, docvecs_mapfile=None, 
				comment=None, trim_rule=None, **kwargs)
		
		dm: distributed memory (algorithm to use for training)
		size: dimensionality of the feature vectors
		negative: number of noise words to (down?) sample
		min_count: ignore all words with total frequency lower than this
		iterations: number of iterations (epochs) over the corpus

        return params: a dictionary of doc2vec training hyperparameters
        """
        doc2vec = config.get("doc2vec")
        params = {
			'dm': doc2vec.get("dm"),
			'vector_size': doc2vec.get("vector_size"),
			'iter': doc2vec.get("epochs"),
			'negative': doc2vec.get("negative"),
			'min_count': doc2vec.get("min_count"),
		}
        return params

    def train(self):
        """
        Train a new doc2vec model for a given SKU using the PV-DBOW 
        (probability vectors - distributed bag of words) algorithm. If the 
        model alreaady exists, do nothing.

		We set dm=0 to disable distributed memory alogrithm. 
		dm=1 gave us vector inferences that made no sense. However,
		PV-DBOW gives us exactly what we want even though the actual 
		probability of the predicitons is 0.60 - 0.65. Predictions up to 0.90
		are possible with optimized, i.e. less ambiguous, match query.
        """

        d2v_model = self._load_model()
        if d2v_model == None:
            logger.info("Training a new model for SKU " + self.sku)
            tagged_docs = self._tagged_docs()
            
            # Set some parameters
            params = self._get_params()
            alpha = config.get("doc2vec").get("alpha")
            min_alpha = config.get("doc2vec").get("min_alpha")
            epochs = config.get("doc2vec").get("epochs")
            alpha_delta = (alpha - min_alpha) / epochs

            # Build an untrained model
            d2v_model = Doc2Vec(**params)
            d2v_model.build_vocab(tagged_docs)

            # Train away!
            for epoch in range(epochs):
                random.shuffle(tagged_docs)
                d2v_model.alpha, d2v_model.min_alpha = alpha, alpha
                train_params = {
                    'total_examples': d2v_model.corpus_count,
                    'epochs': d2v_model.iter
                }
                d2v_model.train(tagged_docs, **train_params)
                alpha -= alpha_delta
            logger.info("Finished training for SKU " + self.sku)
            d2v_model.save(self.path)