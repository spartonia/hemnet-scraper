# -*- coding: utf-8 -*-

import re
import json
import scrapy

from urlparse import urlparse, urljoin
from urllib import urlencode
from itertools import product

from scrapy import Selector
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import TimeoutError, TCPTimedOutError
from sqlalchemy.orm import sessionmaker

from hemnet.items import HemnetItem, HemnetCompItem
from hemnet.models import (
    HemnetItem as HemnetSQL,
    db_connect,
    create_hemnet_table
)


BASE_URL = 'http://www.hemnet.se/salda/bostader?'

location_ids = [17744]
item_types = ['radhus', 'bostadsratt', 'villa']
rooms = [None, 1, 1.5, 2, 2.5, 3, 3.5, 4, 5, 100]
living_area = [None, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 500]
fee = [None, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 5000, 7000, 30000]


def url_queries():
    d_ = {
        'location_ids': location_ids,
        'item_types': item_types,
        'rooms': rooms,
        'living_area': zip(living_area, living_area[1:]),
        'fee': zip(fee, fee[1:]),
    }

    def _encode_query(params):
        url_query = {
            'location_ids[]': params['location_ids'],
            'item_types[]': params['item_types'],
            'rooms_min': params['rooms'],
            'rooms_max': params['rooms'],
            'living_area_min': params['living_area'][0],
            'living_area_max': params['living_area'][1],
            'fee_min': params['fee'][0],
            'fee_max': params['fee'][1],
        }
        return urlencode(url_query)

    param_list = [dict(zip(d_, v)) for v in product(*d_.values())]
    return [_encode_query(p) for p in param_list]


def start_urls():
    return [BASE_URL + qry for qry in url_queries()]


class HemnetSpider(scrapy.Spider):
    name = 'hemnetspider'
    rotate_user_agent = True

    def __init__(self, *args, **kwargs):
        super(HemnetSpider, self).__init__(*args, **kwargs)
        engine = db_connect()
        create_hemnet_table(engine)
        self.session = sessionmaker(bind=engine)()

    def start_requests(self):
        for url in start_urls():
            yield scrapy.Request(url, self.parse,
                                 errback=self.download_err_back)

    def _write_err(self, code, url):
        with open(self.name + '_err.txt', 'a') as f:
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
            q = session.query(HemnetSQL)\
                .filter(HemnetSQL.hemnet_id == get_hemnet_id(url))
            if not session.query(q.exists()).scalar():
                yield scrapy.Request(url, self.parse_detail_page,
                                     errback=self.download_err_back)

        next_href = response.css('a.next_page::attr("href")').extract_first()
        if next_href:
            next_url = urljoin(response.url, next_href)
            scrapy.Request(next_url, self.parse_detail_page,
                           errback=self.download_err_back)

    @staticmethod
    def _get_layer_data(response):
        pattern = 'dataLayer\s*=\s*(\[.*\]);'
        g = re.search(pattern, response.body)
        d = json.loads(g.group(1))
        return d

    def parse_detail_page(self, response):

        props = {}
        try:
            layer_data = self._get_layer_data(response)
        except:
            self._write_err('JSONError', response.url)
        else:
            props = next((el for el in layer_data if u'sold_property' in el),
                         {}).get('sold_property', {})

        item = HemnetItem()

        # type: Selector
        broker_sel = response.css('.broker-contact-card__information')[0]
        property_attributes = get_property_attributes(response)

        item['url'] = response.url
        slug = urlparse(response.url).path.split('/')[-1]
        item['hemnet_id'] = props.get('id')
        item['type'] = slug.split('-')[0]

        raw_rooms = props.get('rooms')
        try:
            item['rooms'] = float(raw_rooms)
        except ValueError:
            pass

        try:
            fee = int(property_attributes.get(u'Avgift/månad', '')
                      .replace(u' kr/m\xe5n', '').replace(u'\xa0', u''))
        except ValueError:
            fee = None
        item['monthly_fee'] = fee

        try:
            item['square_meters'] = float(props.get('living_area'))
        except ValueError:
            pass

        try:
            cost = int(property_attributes.get(u'Driftskostnad', '')
                       .replace(u' kr/\xe5r', '').replace(u'\xa0', u''))
        except ValueError:
            cost = None
        item['cost_per_year'] = cost

        # can be '2008-2009'
        item['year'] = property_attributes.get(u'Byggår', '')

        try:
            association = property_attributes.get(u'Förening').strip()
        except:
            association = None
        item['association'] = association

        try:
            lot_size = int(property_attributes.get(u'Tomtarea')
                           .strip().rsplit(' ')[0].replace(u'\xa0', ''))
        except:
            lot_size = None
        item['lot_size'] = lot_size

        try:
            biarea = int(property_attributes.get(u'Biarea').strip()
                         .rsplit(' ')[0].replace(u'\xa0', ''))
        except:
            biarea = None
        item['biarea'] = biarea

        item['broker_name'] = broker_sel.css('strong::text')\
            .extract_first().strip()
        phone, encoded_email = broker_sel.\
            css('a.broker-contact__link::attr("href")').extract()
        item['broker_phone'] = strip_phone(phone)

        try:
            item['broker_email'] = decode_email(encoded_email).split('?')[0]
        except:
            pass

        item['broker_firm'] = props.get('broker_agency')

        try:
            firm_phone = (broker_sel.css('.phone-number::attr("href")')[1])\
                .extract()
            broker_firm_phone = strip_phone(firm_phone)
        except:
            broker_firm_phone = None
        item['broker_firm_phone'] = broker_firm_phone
        item['price'] = props.get('selling_price')
        item['asked_price'] = props.get('price')
        item['sold_date'] = props.get('sold_at_date')
        item['address'] = props.get('street_address')
        item['geographic_area'] = props.get('location')
        yield item

        prev_page_url = response.css('link[rel=prev]::attr(href)')\
            .extract_first()
        lat, lon = extract_coords(response)

        yield scrapy.Request(prev_page_url, self.parse_prev_page,
                             meta={'lat': lat, 'lon': lon,
                                   'salda_id': props['id']},
                             errback=self.download_err_back)

    def parse_prev_page(self, response):
        try:
            layer_data = self._get_layer_data(response)
        except:
            self._write_err('JSONError', response.url)
        else:
            prop = next((e for e in layer_data if u'property' in e),
                        {}).get('property', {})

            item = HemnetCompItem()

            item['url'] = response.url

            item['lattitude'] = response.meta['lat']
            item['longitude'] = response.meta['lon']

            item['salda_id'] = response.meta['salda_id']

            locations = prop.get('locations', {})

            item['city'] = locations.get('city')
            item['district'] = locations.get('district')
            item['postal_city'] = locations.get('postal_city')
            item['country'] = locations.get('country')
            item['municipality'] = locations.get('municipality')
            item['region'] = locations.get('county')
            item['street'] = locations.get('street')

            item['offers_selling_price'] = prop.get('offers_selling_price')
            item['living_area'] = prop.get('living_area')
            item['rooms'] = prop.get('rooms')
            item['hemnet_id'] = prop.get('id')
            item['cost_per_year'] = prop.get('driftkostnad')
            item['new_production'] = prop.get('new_production')
            item['broker_firm'] = prop.get('broker_firm')
            item['upcoming_open_houses'] = prop.get('upcoming_open_houses')
            item['location'] = prop.get('location')
            item['home_swapping'] = prop.get('home_swapping')
            item['has_price_change'] = prop.get('has_price_change')
            item['status'] = prop.get('status')
            item['price'] = prop.get('price')
            item['monthly_fee'] = prop.get('borattavgift')
            item['main_location'] = prop.get('main_location')
            item['publication_date'] = prop.get('publication_date')
            item['has_active_toplisting'] = prop.get('has_active_toplisting')
            item['images_count'] = prop.get('images_count')
            item['item_type'] = prop.get('item_type')
            item['price_per_m2'] = prop.get('price_per_m2')
            item['street_address'] = prop.get('street_address')

            yield item


def extract_coords(response):
    coord_pattern = 'coordinate.*\[(\d{2}\.\d+\,\d{2}\.\d+)\]'
    g = re.search(coord_pattern, response.body)
    try:
        lat, lon = map(float, g.group(1).split(','))
    except:
        lat, lon = None, None
    return lat, lon


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
    email = ''.join([chr(int(encodedString[i:i+2], 16) ^ r) for i in
                     range(2, len(encodedString), 2)])
    return email


def decode_email(encoded_str):
    # u'/cdn-cgi/l/email-protection#b2d8d7c1c2d7c09cdead...'
    try:
        decoded = cfDecodeEmail(encoded_str.split('#')[-1])
    except:
        decoded = None
    return decoded


def get_hemnet_id(url):
    slug = urlparse(url).path.split('/')[-1]
    return int(slug.split('-')[-1])


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
