import db as DB
import spacy
from services import logger
from uuid import uuid4
import yaml
logger = logger.Loggers(__name__).get_logger()

config = None
with open('config.yaml') as f:
    config = yaml.safe_load(f)
db = DB.init_db(config.get("sent_db"))

class NLPreprocessor:
    """
    Performs NLP preprocessing using the spaCy NLP library to tokenize 
    reviews into sentences and tag them with UIDs.  
    """
    def __init__(self, data):
        """
        Load the pre-trained English NLP model.

        :param data: product reviews, a list of dictionaries 
        """
        self.data = data
        self.nlp = None

        logger.info('Loading spaCy en_core_web_lg NLP model')
        self.nlp = spacy.load('en_core_web_lg')
        logger.info("Finished loading NLP model")
    
    
    def tokenize(self):
        """
        Tokenize reviews into sentences and save them to the database.

        :return: None
        """
        logger.info("Tokenizing documents into sentences")
        for doc in self.data:
            review = self.nlp(doc.get("review_text"))
            sents = []
            for s in review.sents:
                words = []
                for token in s:
                    # tokenize into words and do clean up
                    if not token.is_punct:
                        #TODO: do not break conjuctions apart
                        words.append(token.lower_)
                if len(words) > 1: sents.append(words)
            self._save_sents(sents, doc.get("sku"), doc.get("_id"))
        logger.info("Finished document tokenization")
    
    def _save_sents(self, sent_list, sku, parent_id):
        """
        Save the sentences to the database.

        :param sent_list: a nested list where each sentence is a list of words
        :param sku: the product this sentence's parent review belongs to
        :param parent_id: the 'foreign key' for the untokenized review
        :return: None
        """
    
        tagged_sents = self._tag_sents(sent_list)
        record = {
                "sku": sku,
                "_parent": parent_id,
        }
        # Create/load sentence collection
        sentences = db.sentences
        for tag, sent in tagged_sents:
            record["tag"] = tag 
            record["sentence"] = sent
            sentences.update(record, record, upsert=True)

    def _tag_sents(self, sent_list):
        """
        Assign a uuid to each sentence.

        :param sent_list: A list of sentences (each sentence is in a turn a list of words)
        :return sent_list: a list of tag-sentence tuples
        """
        sent_list = [(str(uuid4()),sent) for sent in sent_list]
        return sent_list
