
# from gensim.models.doc2vec import Doc2Vec
# import pytest
# import sunbeam.db as DB
# import sunbeam.ml.training as training
# import os
# import yaml 

# config = None
# with open('config.yaml') as f:
#     config = yaml.safe_load(f)

# def test_doc2vec_training():
#     sku = "0972683275"
#     db = DB.init_db("test_sentencedb")
#     data = list(db.sentences.find())
#     d2v = training.Document2Vector(data, '0972683275')

#     # Delete a previous model for the SKU if one exists
#     d2v_model_path = config.get("doc2vec").get("path") + "/" + sku 
#     try:
#         os.remove(d2v_model_path)
#     except OSError:
#         pass 

#     # Make sure the number of epochs in config is set to 1 for testing
#     d2v.train()

#     # confirm that we have a trained model on disk
#     # Exception raised if model does not exist
#     void = Doc2Vec.load(d2v_model_path)

    