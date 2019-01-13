import db as DB
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

class Scraper(object):
    """
    Scrapes customer reviews and product detail page from a merchant site.
    """

    def __init__(self):
        self.user_agents = self._get_user_agents()
        
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

        :param init: initial request for product detail
        :return response: an html response
        ''' 
        response = None
        if init:
            with open("response.html", "r") as f:
                response = f.read()
            return response

        params = {
            'headers': self._set_headers(),
            'timeout': settings.get("http_timeout"),
        }
        proxies = {
            'http': settings.get("proxies").get("http"),
            'https': settings.get("proxies").get("https"),
        }
        
        try:
            if not init:
                t = self._get_duration()
                # t = 0 # TODO: for debugging
                logger.info('Throttling by {} second/s'.format(t))
                time.sleep(t)
            response = requests.get(url, proxies=proxies, **params)
            msg = 'New response: status_code={} url={}'
            logger.info(msg.format(response.status_code, response.url))
        except Exception as e:
            msg = '{}: {} url={}'.format(type(e).__name__, e.args[0], url)
            logger.exception(msg)
        return response

            

        
    