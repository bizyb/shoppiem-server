from services import logger
logger = logger.Loggers(__name__).get_logger()

class Cluster(object):
    """
    Cluster user-generated question-answer pair into a super question-answer
    pair. The likelihood of multiple users viewing the same product asking 
    questions that are X% related and receiving answers that are Y% related
    is low. The inference engine is entirely stochastic so even the same 
    person asking the same question multiple times may not get answers
    that are related to each other by X% or by whatever cutoff threshold 
    we set. Therefore, we need more data on the real-world performance of 
    the Q&A engine. For now, we'll use MongoDB's search feature and 
    'cluster' the questions and answers by cutoff weight. 

    In mongo, we store the voting data as a tree, where the root of the tree is the 
    sku. The second level is the uuids that cluster a variation of all quesiton-
    answer pairs above a certain similarity threshold. This node also stores 
    the up_vote and down_vote values. The leaves are the question-answer 
    pairs. Note that this tree structure is not optimized for constant 
    search (key lookup) because of the uuid tags on the second level. 
    Everytime we need to get or put a new q&a pair, we need to iterate 
    through all the uuids and stop the momement we encounter a node 
    whose leaf node is similar to our query. If none exists, we create a new 
    entry.

    ***Ignore all of the above*** Mongodb does text-matching with some preprocessing
    like lemmatization and etc. We want something as powerful as doc2vec. We'll 
    wait until later and see how well the exact matching algorithm we have 
    now works.
    """
    def __init__(self, record):
        self.record = record
        self.query = {
            "sku": self.record.get("sku"),
            "question": self.record.get("question"),
            "answer": self.record.get("answer")
        }
  
    def put_votes(self, db):
        """
        If no question-answer pair exists for a given sku, use it as a baseline
        against which future queuries will be searched. Create a cluster for this 
        pair of question and answer using its sku as a tag. Save the votes with the
        cluster tag, not with the question and answer. 
        """
        
        entry = list(db.votes.find(self.query))
        if len(entry) == 0:
            db.votes.insert_one(self.record)
            logger.info("Inserted a new vote for sku " + self.record.get("sku"))
        else:
            db.votes.update_one(self.query, {"$set": {
                                "up_count": self.record.get("up_count"),
                                "down_count": self.record.get("down_count")
                                }
                            })
    
    def get_votes(self, db):
        """
        If there are any votes for the current query, return the up_vote
        and down_vote count on file. Otherwise, return 0 for both.
        """
        result = {"up_votes": 0, "down_votes": 0}
        entry = list(db.votes.find(self.query))
        if len(entry) == 0: return result 
        return {
            "up_votes": entry[0].get("up_count"),
            "down_votes": entry[0].get("down_count")
        }