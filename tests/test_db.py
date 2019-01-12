from sunbeam import db as DB
from pymongo import MongoClient

def test_db():
    """
    Perform basic API tests on our database. Note that we're not 
    testing for the functionality of MongoDB but rather our ability to
    use its API properly.
    """

    db = DB.init_db("test_db")
    assert (isinstance(type(db), type(MongoClient)))

    # Create a collection of articles
    articles = db.articles
    article_0 = {
        'title': 'The Effect of Spatial Harmonics on the Accelerated Decay of Krieger Waves',
        'article_number': 1,
        'author': 'Vulcan Science Academy'
    }
    result = articles.insert_one(article_0)

    article_1 = {
        'title': 'Where God Went Wrong',
        'article_number': 2,
        'author': 'Oolon Colluphid'
    }

    article_2 = {
        'title': 'Some More of God\'s Greatest Mistakes',
        'article_number': 3,
        'author': 'Oolon Colluphid'
    }

    article_3 = {
        'title': 'Who is this God Person Anyway?',
        'article_number': 4,
        'author': 'Oolon Colluphid'
    }
    articles.insert_many([article_1, article_2, article_3])

    # Test retrieval
    article = articles.find_one({'author': 'Vulcan Science Academy'})
    article.pop("_id")
    article_0.pop("_id")
    assert (article) == article_0

    article = articles.find_one({'author': 'Oolon Colluphid', "article_number": 4})
    article.pop("_id")
    article_3.pop("_id")
    assert (article) == article_3










