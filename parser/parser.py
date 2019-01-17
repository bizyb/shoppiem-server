from bs4 import BeautifulSoup as bsoup
import ingestion
import re
from services import logger
import yaml
logger = logger.Loggers(__name__).get_logger()

selectors = None
with open('parser/css_selectors.yaml') as f:
    selectors = yaml.safe_load(f)

class Parser(object):
    """
    Prase product detail page or reviews.
    """
    # TODO: parse the image url, download the image in a separate thread, and save it to S3
    def __init__(self, sku=None, prod_name=None, source=None):
        self.sku = sku 
        self.prod_name = prod_name
        self.source = source.lower()
    
    def parse(self, response, init=False):
        # for testing
        prod_name = """Acer SB220Q bi 21.5" Full HD (1920 x 1080) IPS Ultra-Thin Zero Frame Monitor (HDMI & VGA Port)"""
        img = "https://images-na.ssl-images-amazon.com/images/I/71mJZSQXuRL._SX679_.jpg"
        return [prod_name, 2015, 202, img]


        if init:
            #TODO: validate that all the parameters for review scraping are there; otherwise, return None
            return self._parse_detail(response)
        self._parse_reviews(response)
    
    def _parse_detail(self, response):
        soup = bsoup(response, 'lxml')
        _parser = "_" + self.source.lower() + "_detail_parser"
        _parser = getattr(self, _parser)
        return _parser(soup)
    
    def _parse_reviews(self, response):
        soup = bsoup(response, 'lxml')
        _parser = "_" + self.source.lower() + "_review_parser"
        _parser = getattr(self, _parser)
        return _parser(soup)
    
    def _amazon_review_parser(self, soup):
        review_list = soup.find_all('div', id=re.compile('customer_review-\w+'))
        sel = selectors.get(self.source).get("review_text")
        raw = []
        for review in review_list:
            record = {
                "product_name": self.prod_name,
                "source": self.source,
                "sku": self.sku,
                "review_text": review.find('span', sel).text
            }
            raw.append(record)
        ingestion.ingest(raw)


    def _amazon_detail_parser(self, soup):
        rcount_selector = selectors.get(self.source).get("review_count")
        name_selector = selectors.get(self.source).get("product_name")

        # get review count
        text = soup.select(rcount_selector)[0].contents[0]
        if isinstance(text, unicode):
            text = text.replace(',', '')
        review_count = int(''.join(re.findall(r'\d+', text)))
        page_count = self._get_page_count(review_count, divisor=10)

        # get product name
        name = soup.select(name_selector)[0].text.strip()
        
        return (name, review_count, page_count)
    
    def _get_page_count(self, count, divisor=1):
		count = int(count)
		page_count = count/divisor
		if count % divisor != 0:
			page_count += 1
		return page_count


