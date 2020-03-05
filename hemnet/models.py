from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Boolean
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.declarative import declarative_base

from . import settings

DeclarativeBase = declarative_base()


def db_connect():
    return create_engine(URL(**settings.DATABASE))


def create_hemnet_table(engine):
    DeclarativeBase.metadata.create_all(engine)


class HemnetItem(DeclarativeBase):
    __tablename__ = "hemnet_items"

    id = Column(Integer, primary_key=True)

    hemnet_id = Column(Integer, index=True)

    url = Column(String)

    broker_name = Column(String, default='')
    broker_phone = Column(String, default='')
    broker_email = Column(String, default='', index=True)

    broker_firm = Column(String, nullable=True)
    broker_firm_phone = Column(String, nullable=True)

    sold_date = Column(Date, nullable=True)

    price_per_square_meter = Column(Float, nullable=True)
    price = Column(Integer, nullable=True)
    asked_price = Column(Integer, nullable=True)
    price_trend_flat = Column(Integer, nullable=True)
    price_trend_percentage = Column(Integer, nullable=True)

    rooms = Column(Float, nullable=True)
    monthly_fee = Column(Integer, nullable=True)
    square_meters = Column(Float, nullable=True)
    cost_per_year = Column(Integer, nullable=True)
    year = Column(String, default='')
    type = Column(String, default='')
    association = Column(String, nullable=True)
    lot_size = Column(Integer, nullable=True)
    biarea = Column(Integer, nullable=True)

    address = Column(String, default='')
    geographic_area = Column(String, default='')
    collected_at = Column(Date, default=datetime.now())


class HemnetCompItem(DeclarativeBase):
    __tablename__ = "hemnet_comp_items"

    id = Column(Integer, primary_key=True)

    salda_id = Column(Integer, index=True)
    hemnet_id = Column(Integer, index=True)

    url = Column(String)

    lattitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    city = Column(String, nullable=True)
    postal_city = Column(String, nullable=True)
    district = Column(String, nullable=True)
    country = Column(String, nullable=True)
    region = Column(String, nullable=True)
    municipality = Column(String, nullable=True)
    street = Column(String, nullable=True)

    location = Column(String, nullable=True)
    main_location = Column(String, nullable=True)
    street_address = Column(String, nullable=True)

    offers_selling_price = Column(Boolean)
    living_area = Column(Float)
    rooms = Column(Float, nullable=True)

    broker_firm = Column(String, nullable=True)

    new_production = Column(Boolean)
    upcoming_open_houses = Column(Boolean, default=False)
    home_swapping = Column(Boolean, nullable=True)
    has_price_change = Column(Boolean, nullable=True)
    has_active_toplisting = Column(Boolean, nullable=True)

    status = Column(String, nullable=True)
    price = Column(Integer)
    cost_per_year = Column(Integer, nullable=True)
    monthly_fee = Column(Integer, nullable=True)
    publication_date = Column(Date, nullable=True)
    images_count = Column(Integer, nullable=True)
    item_type = Column(String, nullable=True)
    price_per_m2 = Column(Integer, nullable=True)

    collected_at = Column(Date, default=datetime.now())
