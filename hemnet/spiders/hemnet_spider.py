# -*- coding: utf-8 -*-

from urlparse import urlparse
import re
import scrapy
from hemnet.items import HemnetItem
from scrapy import Selector
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import TimeoutError, TCPTimedOutError

from sqlalchemy.orm import sessionmaker

from hemnet.models import HemnetItem as HemnetSQL, db_connect, create_hemnet_table

# BASE_URL = 'http://www.hemnet.se/salda/bostader?location_ids%5B%5D=17744&item_types[]=villa&item_types[]=radhus&item_types[]=bostadsratt'
# BASE_URL = 'http://www.hemnet.se/salda/bostader?'
BASE_URL = 'https://www.hemnet.se/salda/bostader?location_ids%5B%5D=17744&item_types%5B%5D=villa&item_types%5B%5D=radhus&item_types%5B%5D=bostadsratt&sold_age=13m'

def start_urls(start, stop):
    return ['{}&page={}'.format(BASE_URL, x) for x in xrange(start, stop)]


class HemnetSpider(scrapy.Spider):
    name = 'hemnetspider'
    rotate_user_agent = True

    def __init__(self, start=1, stop=10, *args, **kwargs):
        super(HemnetSpider, self).__init__(*args, **kwargs)
        self.start = int(start)
        self.stop = int(stop)
        self.err_file = 'errors.txt'
        engine = db_connect()
        create_hemnet_table(engine)
        self.session = sessionmaker(bind=engine)()

    def start_requests(self):
        for url in start_urls(self.start, self.stop):
            yield scrapy.Request(url, self.parse, errback=self.download_err_back)

    def _write_err(self, code, url):
        with open(self.err_file, 'a') as f:
            f.write('{}: {}\n'.format(code, url))

    def download_err_back(self, failure):
        if failure.check(HttpError):
            response = failure.value.response
            self._write_err(response.status, response.url)
        elif failure.check(TimeoutError, TCPTimedOutError):
            request = failure.request
            self._write_err('TimeoutError', request.url)
        else:
            request = failure.request
            self._write_err('Other', request.url)

    def parse(self, response):
        urls = response.css('#search-results li > div > a::attr("href")')
        for url in urls.extract():
            session = self.session
            q = session.query(HemnetSQL).filter(HemnetSQL.hemnet_id == get_hemnet_id(url))
            if not session.query(q.exists()).scalar():
                yield scrapy.Request(url, self.parse_detail_page, errback=self.download_err_back)

    def parse_detail_page(self, response):
        item = HemnetItem()

        broker = response.css('.broker-info > div.broker')[0]  # type: Selector
        property_attributes = get_property_attributes(response)

        item['url'] = response.url

        slug = urlparse(response.url).path.split('/')[-1]

        item['hemnet_id'] = get_hemnet_id(response.url)

        item['type'] = slug.split('-')[0]

        raw_rooms = property_attributes.get(u'Antal rum', '').replace(u' rum', u'').replace(u',', u'.')
        try:
            item['rooms'] = float(raw_rooms)
        except ValueError:
            pass

        try:
            fee = int(property_attributes.get(u'Avgift/månad', '').replace(u' kr/m\xe5n', '').replace(u'\xa0', u''))
        except ValueError:
            fee = None
        item['monthly_fee'] = fee

        try:
            item['square_meters'] = float(property_attributes.get(u'Boarea', '').split(' ')[0].replace(',', '.'))
        except ValueError:
            pass

        try:
            cost = int(property_attributes.get(u'Driftskostnad', '').replace(u' kr/\xe5r', '').replace(u'\xa0', u''))
        except ValueError:
            cost = None
        item['cost_per_year'] = cost

        item['year'] = property_attributes.get(u'Byggår', '')  # can be '2008-2009'

        try:
            association = property_attributes.get(u'Förening').strip()
        except:
            association = None
        item['association'] = association

        try:
            lot_size = int(property_attributes.get(u'Tomtarea').strip().rsplit(' ')[0].replace(u'\xa0', ''))
        except:
            lot_size = None
        item['lot_size'] = lot_size

        try:
            biarea = int(property_attributes.get(u'Biarea').strip().rsplit(' ')[0].replace(u'\xa0', ''))
        except:
            biarea = None
        item['biarea'] = biarea

        item['broker_name'] = broker.css('b::text').extract_first().strip()
        item['broker_phone'] = strip_phone(broker.css('.phone-number::attr("href")').extract_first())

        try:
            encoded_email = broker.css('a.broker__email::attr(href)').extract_first()
            item['broker_email'] = decode_email(encoded_email)
        except:
            pass

        try:
            broker_firm = broker.css('a::text').extract_first().strip()
            if not broker_firm:
                broker_firm = broker.css('p:nth-child(2)::text').extract_first().strip()
        except:
            broker_firm = None
        item['broker_firm'] = broker_firm

        try:
            firm_phone = (broker.css('.phone-number::attr("href")')[1]).extract()
            broker_firm_phone = strip_phone(firm_phone)
        except:
            broker_firm_phone = None
        item['broker_firm_phone'] = broker_firm_phone

        raw_price = response.css('.sold-property__price-value::text').extract_first()
        item['price'] = price_to_int(raw_price)

        get_selling_statistics(response, item)

        metadata = response.css('.sold-property__metadata')[0]

        item['sold_date'] = metadata.css('time::attr(datetime)').extract_first()
        item['address'] = ' '.join(response.css('.sold-property__address::text').extract()).strip()

        meta_text = ' '.join([i.strip() for i in metadata.css('::text').extract()])
        item['geographic_area'] = extract_municipality(meta_text)

        yield item


def extract_municipality(address_line):
    pattern_comma = '(?<=,)(.*)(?=kommun)'
    pattern_dash = '(?<=-)(.*)(?=kommun)'
    address_line = address_line.replace('\n', '')
    grouped = re.search(pattern_comma, address_line)
    if not grouped:
        grouped = re.search(pattern_dash, address_line)
    try:
        kommun = grouped.group(1).strip()
    except:
        kommun = None
    finally:
        return kommun


def cfDecodeEmail(encodedString):
    r = int(encodedString[:2],16)
    email = ''.join([chr(int(encodedString[i:i+2], 16) ^ r) for i in range(2, len(encodedString), 2)])
    return email


def decode_email(encoded_str):
    # u'/cdn-cgi/l/email-protection#b2d8d7c1c2d7c09cdedbdcd6c3c4dbc1c6f2dac7c1dfd3dcdad3d5d0d7c0d59cc1d7'
    try:
        decoded = cfDecodeEmail(encoded_str.split('#')[-1])
    except:
        decoded = None
    finally:
        return decoded


def get_hemnet_id(url):
    slug = urlparse(url).path.split('/')[-1]
    return int(slug.split('-')[-1])


def get_selling_statistics(response, item):
    a = response.css('.sold-property__price-stats > dt::text').extract()
    x = [x.strip() for x in a]
    b = response.css('.sold-property__price-stats > dd::text').extract()
    stats = dict(zip(x, b))
    try:
        item['asked_price'] = price_to_int(stats[u'Begärt pris'])
    except:
        pass

    try:
        raw_price = stats[u'Pris per kvadratmeter']
        item['price_per_square_meter'] = int(raw_price.replace(u'\xa0', '').split(' ')[0])
    except:
        pass


def get_property_attributes(response):
    a = response.css('.sold-property__attributes > dt::text').extract()
    x = [x.strip() for x in a]
    b = response.css('.sold-property__attributes > dd::text').extract()

    return dict(zip(x, b))


def price_to_int(price_text):
    return int(price_text.replace(u'\xa0', u'').replace(u' kr', u'').encode())


def strip_phone(phone_text):
    if phone_text:
        return phone_text.replace(u'tel:', u'')
    else:
        return u''


def price_trend(price_text):
    r = '(?P<sign>[+-])(?P<flat>\d*)\([+-]?(?P<percentage>\d*)\%\)$'

    temp = price_text.replace(u'\xa0', '').replace(' ', '').replace('kr', '')

    matches = re.search(r, temp)

    sign = matches.group('sign')
    flat = int('{}{}'.format(sign, matches.group('flat')))
    percentage = int('{}{}'.format(sign, matches.group('percentage')))
    return flat, percentage

