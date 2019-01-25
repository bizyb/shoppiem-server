import db as DB
import main
from parser import parser
import random
import requests
from services import logger
import time
import yaml

logger = logger.Loggers(__name__).get_logger()

config = None
ua = None
with open('config.yaml') as f:
    config = yaml.safe_load(f)
with open("scraper/user_agents.yaml") as f:
    ua = yaml.safe_load(f)
settings = config.get("scraper")
q_db = DB.init_db(config.get("queue_db")).queue
__error__ = config.get("misc").get("error_msg")

class Scraper(object):
    """
    Scrapes customer reviews and product detail page from a merchant site.
    """

    def __init__(self, sku=None, prod_name=None, source=None):
        self.sku = sku 
        self.prod_name = prod_name
        self.source = source.lower()
        self.user_agents = self._get_user_agents()
        logger.info("**************Scraper has been instantiated**************")
        
    def _get_user_agents(self):
        """
        Load all existing user agents.

        :return: a list of user agents
        """
        return [value for key, value in ua.get("all_agents").items()]
        
    def _get_duration(self):
        ''' 
        Return a random sleep duration.

        :return num: an integer 
        '''
        sm = settings.get("sleep_min")
        smx = settings.get("sleep_max")
        num = random.randint(sm, smx)
        return num

    def _set_headers(self):
        '''
        Set the response header with a random user agent.

        return headers: HTTP headers with updated user agent
        '''
        headers = requests.utils.default_headers()
        user_agent = random.choice(self.user_agents)
        headers.update({'User-Agent': user_agent})
        return headers

    def get_request(self, url, init=True):
        '''
        Return HTTP response object.

        :param init: initial request for product detail or image download
        :return response: an html response
        '''
        try:
            response = None
            params = {
                'headers': self._set_headers(),
                'timeout': settings.get("http_timeout"),
            }
            proxies = {
                'http': settings.get("proxies").get("http"),
                'https': settings.get("proxies").get("https"),
            }
            logger.info("About to make a request on url: " + url)
            try:
                if not init:
                    t = self._get_duration()
                    logger.info('Throttling by {} second/s'.format(t))
                    time.sleep(t)
                # response = requests.get(url, proxies=proxies, **params)
                response = requests.get(url, **params) # Enable when debugging
                msg = 'New response: status_code={} url={}'
                logger.info(msg.format(response.status_code, response.url))
            except Exception as e:
                msg = '{}: {} url={}'.format(type(e).__name__, e.args[0], url)
                logger.exception(msg)
                if init:
                    # If exception raised while parsing detail page, we're in trouble so need 
                    # to update the status of the job 
                    main._set_status(__error__, self.sku)
                    
            
            if not init and response != None:
                # parse the reviews and save them to the database 
                logger.info("About to call review parser for url " + url)
                pr = parser.Parser(sku=self.sku, prod_name=self.prod_name, source=self.source)
                pr.parse(response.text)
                logger.info("Parser has finished parsing (may or may not have succeeded) url " + url)

                # remove it from the queue; Log the counts for some sanity check
                logger.info("Attempting to remove from the queue: " + url)
                before = len(list(q_db.find({"sku": self.sku})))
                q_db.delete_one({"sku": self.sku, "url": url})
                after = len(list(q_db.find({"sku": self.sku})))
                logger.info("Count in db before: {} after: {}".format(before, after))

            if response:
                logger.info("HTTP status code: " + str(response.status_code)) 
                return response.text

        except Exception as e:
            msg = '{}: {} url={}'.format(type(e).__name__, e.args[0], url)
            logger.exception(msg)

        

            

        
    
