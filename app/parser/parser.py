import aws
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
    #TODO: do image downloading and uploading in the background after the model has been trained with celery
    #TODO: parse product breadcrumb 
    def __init__(self, sku=None, prod_name=None, source=None):
        self.sku = sku 
        self.prod_name = prod_name
        self.source = source.lower()
    
    def parse(self, response, init=False):
        what_for = "detail parsing"
        if not init:
            what_for = "review parsing"
        try:
            if init:
                return self._parse_detail(response)
            self._parse_reviews(response)
        except Exception as e:
            logger.exception(e)
    
    def _parse_detail(self, response):
        logger.info("About to parse the product detail page for {} from {}".format(self.sku, self.source))
        soup = bsoup(response, 'lxml')
        _parser = "_" + self.source.lower() + "_detail_parser"
        _parser = getattr(self, _parser)
        return _parser(soup)
        
    
    def _parse_reviews(self, response):
        logger.info("About to parse reviews for {} from {}".format(self.sku, self.source))
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
                "review_text": review.find('span', sel).text,
                "sent_tokenized": False
            }
            raw.append(record)
        ingestion.ingest(raw)
        logger.info("Finished parsing single-page reviews for {} from {}".format(self.sku, self.source))


    def _amazon_detail_parser(self, soup):
        logger.info("Started parsing Amazon product detail page for {}".format(self.sku))
        rcount_sel_outer = selectors.get(self.source).get("review_count_outer")
        rcount_sel_inner = selectors.get(self.source).get("review_count_inner")
        name_selector = selectors.get(self.source).get("product_name")
        image_selector = selectors.get(self.source).get("product_image")
        
        # get review count
        review_count = -1
        try:
            review_count = self._amazon_review_count(soup, rcount_sel_outer, rcount_sel_inner)
        except Exception as e:
            # if we have a problem parsing the review count, then 
            # we have nothing to work with
            logger.exception(e)
            return {}
        
        page_count = self._get_page_count(review_count, divisor=10)

        # get product name and image url
        name = soup.select(name_selector)[0].text.strip()
        img_url = self._amazon_image_url(soup, image_selector)
        logger.info("Finished parsing Amazon product detail page for {}".format(self.sku))
        return {"product_name": name,
                "review_count": review_count,
                "page_count": page_count,
                "img_url": img_url,
            }
    
    def _get_page_count(self, count, divisor=1):
		count = int(count)
		page_count = count/divisor
		if count % divisor != 0:
			page_count += 1
		return page_count
    
    def _amazon_image_url(self, soup, sel):
        """
        Select the largest image and return its url.
        """
        img_dict = eval(soup.select(sel)[0].attrs.get('data-a-dynamic-image'))
        _max, _key = -1, -1
        for k, v in img_dict.items():
            if v[0] > _max:
                _max = v[0]
                _key = k
        return _key
    
    def _amazon_review_count(self, soup, sel_outer, sel_inner):
        """
        Return the correct review count for the given sku.
        """
        
        blocks = soup.select(sel_outer)
        target = None
        for block in blocks:
            if block.attrs.get("data-asin") == self.sku:
                target = block

        target = target.select(sel_inner)[0].contents[0]
        if isinstance(target, unicode):
            target = target.replace(',', '')
        review_count = int(''.join(re.findall(r'\d+', target))) 
        return review_count
        



    
    # def _upload_image(self, url):
    #     """
    #     Upload the image to our S3 bucket and return its url. 
    #     If upload fails for some reason, just return the original 
    #     url.
    #     """
    #     try:
    #         sc = scraper.Scraper(sku, prod_name, source)
    #         sc.get_request(url, init=False)
    #         stream = 
    #         url = aws.upload_file(stream, self.sku, mime) 
    #     except Exception:
    #         return url


