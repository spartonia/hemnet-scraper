# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class HemnetItem(scrapy.Item):
    url = scrapy.Field()

    hemnet_id = scrapy.Field()

    broker_name = scrapy.Field()
    broker_phone = scrapy.Field()
    broker_email = scrapy.Field()

    broker_firm = scrapy.Field()
    broker_firm_phone = scrapy.Field()

    sold_date = scrapy.Field()

    price_per_square_meter = scrapy.Field()
    price = scrapy.Field()
    asked_price = scrapy.Field()
    price_trend_flat = scrapy.Field()
    price_trend_percentage = scrapy.Field()

    rooms = scrapy.Field()
    monthly_fee = scrapy.Field()
    square_meters = scrapy.Field()
    cost_per_year = scrapy.Field()
    year = scrapy.Field()
    type = scrapy.Field()
    association = scrapy.Field()
    lot_size = scrapy.Field()
    biarea = scrapy.Field()

    address = scrapy.Field()
    geographic_area = scrapy.Field()


class HemnetCompItem(scrapy.Item):
    url = scrapy.Field()
    
    hemnet_id = scrapy.Field()
    salda_id = scrapy.Field()

    lattitude = scrapy.Field()
    longitude = scrapy.Field()

    city = scrapy.Field()
    postal_city = scrapy.Field()
    district = scrapy.Field()
    country = scrapy.Field()
    region = scrapy.Field()
    municipality = scrapy.Field()
    street = scrapy.Field()

    offers_selling_price = scrapy.Field()
    living_area = scrapy.Field()
    rooms = scrapy.Field()
    cost_per_year = scrapy.Field()
    new_production = scrapy.Field()
    broker_firm = scrapy.Field()
    upcoming_open_houses = scrapy.Field()
    location = scrapy.Field()
    home_swapping = scrapy.Field()
    has_price_change = scrapy.Field()
    status = scrapy.Field()
    price = scrapy.Field()
    monthly_fee = scrapy.Field()
    main_location = scrapy.Field()
    publication_date = scrapy.Field()
    has_active_toplisting = scrapy.Field()
    images_count = scrapy.Field()
    item_type = scrapy.Field()
    price_per_m2 = scrapy.Field()
    street_address = scrapy.Field()
