from __base__ import Doc2VecBase
import db as DB
from gensim.models.doc2vec import Doc2Vec
from services import logger
import yaml
logger = logger.Loggers(__name__).get_logger()

config = None
with open('config.yaml') as f:
    config = yaml.safe_load(f)
db = DB.init_db(config.get("sent_db"))

class Inference(Doc2VecBase):
    """
    Performs inference using hitherto unforseen query against
    a previously trained model.
    """
    def __init__(self, sku):
        path = config.get("doc2vec").get("path") 
        super(Inference, self).__init__(sku, path)
        self.d2v_model = self._load_model()
    
    def infer(self, query):
        '''
        Query the model to infer vectors for an unseen sentence 
        and return a list of sentence tags and their probabilities. 

        steps: number of iterations (?); tested step=1 to step=10e6. 10e5
                is optimal
        topn: number of top n sentences to return; n is determined 
                empirically based on the quality of the predictions 
                generated at or above a given probability threshold
            
        param query: an enriched query
        return sents: a list of inferred sentences 
        '''
        steps = config.get("doc2vec").get("inference").get("steps") 
        topn = config.get("doc2vec").get("inference").get("topn")

        logger.info('Sentence inference in progress')
        query_tokens = query.split()
        inference = self.d2v_model.infer_vector(query_tokens,steps=steps)
        sims = self.d2v_model.docvecs.most_similar([inference], topn=topn)
        return map(lambda x: self._lookup(x[0]), sims)
            
    def _lookup(self, tag):
        """
        Perform a reverse sentence lookup given its tag.

        :param tag: a unique sentence identifier
        :return sent: the target sentence
        """
        sentence = "Sorry, could not find any matching result"
        try:
            obj = list(db.sentences.find({"tag": tag}))[0]
            sentence = " ".join(obj.get("sentence"))
        except Exception:
            # this should never happen
            logger.error("Failed to do reverse sentence lookup")
        return sentence
      