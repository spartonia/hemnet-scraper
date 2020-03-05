# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from sqlalchemy.orm import sessionmaker
from .models import db_connect, create_hemnet_table
from .models import HemnetItem as HemnetDBItem
from .models import HemnetCompItem as HemnetCompDBItem
from .items import HemnetItem


class HemnetPipeline(object):
    def __init__(self):
        engine = db_connect()
        create_hemnet_table(engine)
        self.Session = sessionmaker(bind=engine)

    def process_item(self, item, spider):
        session = self.Session()
        if isinstance(item, HemnetItem):
            deal = HemnetDBItem(**item)
        else:
            deal = HemnetCompDBItem(**item)

        try:
            session.add(deal)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

        return item
