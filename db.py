from pymongo import MongoClient
import yaml

def init_db(db_name):
    """
    Initialize a new MongoDB instance. If the database already exists, return
    the existing one.

    :return: a database instance
    :rtype: MongoClient

    """
    config = None
    with open('config.yaml') as f:
        config = yaml.safe_load(f)

    client = MongoClient(config['host'], config['port'])
    return client[db_name]


