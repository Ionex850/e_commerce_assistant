import re
from bs4 import BeautifulSoup, Comment
import time
from headless_browser import HeadlessBrowser

test_run=False

import requests
from urllib.parse import urlencode, urlparse, parse_qs
class HttpProvider:
    session = requests.Session()
    chrome_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'sec-ch-ua': '"Not-A.Brand";v="99", "Chromium";v="124", "Google Chrome";v="124"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }
    session.headers.update(chrome_headers)

    @classmethod
    def fetch(cls, href, retry_times=1):
        for _ in range(retry_times):
            response = requests.get(href)
            if response.status_code == 200:
                print(f'Success @{href}')
                return response
            time.sleep(5)
        raise RuntimeError(f"HTTP request @URL:{href} failed with status code {response.status_code}")

from abc import ABC, abstractmethod
class Provider(ABC):
    @classmethod
    @abstractmethod
    def search(cls, query, filters=None):
        pass
    
    @classmethod
    @abstractmethod
    def parse_webpage(cls, html):
        pass

def getValue(txt):
    txt=re.sub(r'[^\d.]','',txt)
    try:
        return float(txt)
    except:
        return float('nan')
def getText(elt):
    if elt is None:
        return ''
    return elt.text

class AmazonProvider(Provider):
    mappings = [
        ('max-price','high-price'),
        ('min-price','low-price')
    ]

    @classmethod
    def search(cls, query, filters=[]):
        base_url = "https://www.amazon.in/s?"
        params = {'k': query}
        for a, b in AmazonProvider.mappings:
            if a in filters:
                params[b] = filters[a]
        query_string = urlencode(params) 
        full_url = base_url + query_string
        parsed_opts = []
        if test_run:
            for optpath in ['ps/p1.html','ps/p2.html','ps/p3.html','ps/p4.html','ps/p5.html']:
                with open(optpath,'r',encoding='utf-8') as f:
                    content = f.read()
                    parsed_wbpg = AmazonProvider.parse_webpage(content)
                    parsed_wbpg['link'] = optpath
                    parsed_opts.append(parsed_wbpg)
            return parsed_opts
        
        res_html = HeadlessBrowser.fetch(full_url)
        soup = BeautifulSoup(res_html, "html.parser")
        with open('jjj.html','w',encoding='utf-8') as f:
            f.write(soup.text)
        opts = soup.find_all('div',class_='sg-col-4-of-4',attrs={"role": "listitem"})
        print(f"{len(opts)} options found.")
        HeadlessBrowser.driver.switch_to.new_window('tab')
        for opt in opts[0:10]:
            time.sleep(10)
            link=opt.find('a')['href']
            parsed_url = urlparse(link)
            if parsed_url.path == '/sspa/click':
                correct_url = parse_qs(parsed_url.query)['url'][0]
            else:
                correct_url = link
            idx=correct_url.find('/ref=')
            link = correct_url if idx == -1 else correct_url[:idx]
            try:
                prod_res_html = HeadlessBrowser.fetch(f'https://www.amazon.in{link}')
            except RuntimeError as e:
                print(f"WARNING: {str(e)}")
                continue
            parsed_wbpg = AmazonProvider.parse_webpage(prod_res_html)
            parsed_wbpg['link'] = link
            parsed_opts.append(parsed_wbpg)
        return parsed_opts

    @classmethod
    def parse_webpage(cls, html):
        #parses html to json
        result = {}
        soup = BeautifulSoup(html,"html.parser")
        result['source'] = 'Amazon'
        title = soup.title.text
        top_features = re.split(',|:',title)
        top_features = [s.strip() for s in top_features]
        result['name'] = top_features[0]
        result['features'] = top_features[1:-2] 
        result['price'] = getValue(getText(soup.find('span', class_='a-price-whole')))
        result['discount'] = getValue(getText(soup.find('span', class_='apex-savings-container')))
        result['mrp'] = getValue(getText(soup.find('span', class_='apex-basisprice-offscreen-label')).replace('M.R.P.',''))
        delivery_elt=soup.find('div', id='deliveryBlockMessage').find('span') or {'data-csa-c-delivery-time':'not mentioned'}
        result['delivery'] = delivery_elt['data-csa-c-delivery-time']
        offers = soup.find_all('div', class_='offers-items-content')
        result['offers'] = [getText(offer.find('span',class_='a-offscreen')) for offer in offers]

        details_tables = soup.find_all('table', class_='prodDetTable')
        all_keys=['price','discount','delivery']
        details_dict = {'price': result['price'], 'discount': result['discount'], 'delivery': result['delivery']}
        for table in details_tables:
            if 'id' in table and 'feedback' in table['id']:
                continue
            for row in table.find_all('tr'):
                _key=row.find('th').get_text(strip=True)
                all_keys.append(_key)
                details_dict[_key] = row.find('td').get_text(strip=True)
        result['details'] = details_dict
        result['all_keys'] = all_keys
        top_specs=soup.find('div',id='feature-bullets').find_all('span',class_='a-list-item')
        result['top_specs'] = "\n".join([getText(elt).strip() for elt in top_specs])

        review_list = soup.find(id='localTopReviewsList')
        if review_list is None:
          reviews = []
        else:
          reviews = review_list.find_all(attrs={"data-hook": "reviewRichContentContainer"})
        result['reviews'] = [getText(r) for r in reviews]
        rating_text = soup.find(id='acrPopover')['title']
        result['rating'] = getValue(rating_text[0:rating_text.find('out')])
        result['ratings_count'] = getText(soup.find(id='acrCustomerReviewText')).strip()[1:-1]
        result['trusted_reviews'] = True

        return result
            