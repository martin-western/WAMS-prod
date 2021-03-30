from dealshub.models import *
from dealshub.utils import *
from algoliasearch.search_client import SearchClient
from dealshub.algolia.constants import *
import json

import requests
import json
import pytz
import csv
import logging
import sys
import xlrd
import uuid
import time

logger = logging.getLogger(__name__)

def add_product_to_index(dealshub_product_obj):

    client = SearchClient.create(APPLICATION_KEY, ADMIN_KEY)
    index = client.init_index('DealsHubProduct')
    
    try:
        logger.info("add_product_to_index: %s", str(dealshub_product_obj.__dict__))
        dealshub_product_dict = {}
        dealshub_product_dict["locationGroup"] = dealshub_product_obj.location_group.uuid
        dealshub_product_dict["objectID"] = dealshub_product_obj.uuid
        dealshub_product_dict["productName"] = dealshub_product_obj.get_name()
        dealshub_product_dict["category"] = dealshub_product_obj.get_category()
        dealshub_product_dict["superCategory"] = dealshub_product_obj.get_super_category()
        dealshub_product_dict["subCategory"] = dealshub_product_obj.get_sub_category()
        dealshub_product_dict["brand"] = dealshub_product_obj.get_brand()
        dealshub_product_dict["sellerSKU"] = dealshub_product_obj.get_seller_sku()
        dealshub_product_dict["isPublished"] = dealshub_product_obj.is_published
        dealshub_product_dict["price"] = dealshub_product_obj.now_price
        dealshub_product_dict["stock"] = dealshub_product_obj.stock
        
        index.save_objects(dealshub_product_dict, {'autoGenerateObjectIDIfNotExist': False})
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("add_product_to_index: %s at %s", e, str(exc_tb.tb_lineno))

def search_algolia_index(data):
    try:
        logger.info("search_algolia_index: %s",str(data))
        if not isinstance(data, dict):
            data = json.loads(data)
 
        search_string = data["search_string"]
        filters = {}
        filters['hitsPerPage'] = data["pageSize"]
        filters['page'] = data["page"]
        filters['filters'] = ""

        filters['filters'] += "locationGroup: " + str(data["locationGroupUuid"]) + " "

        if filters['filters'] != "":
            filters['filters'] = filters['filters'] + "AND "
        filters['filters'] += "isPublished: true AND stock > 0 AND price > 0.0 "

        if data["superCategory"] != "":
            if filters['filters'] != "":
                filters['filters'] = filters['filters'] + "AND "
            filters['filters'] += "superCategory:" + "'" + data["superCategory"] + "' "

        if data["category"] !="":
            if filters['filters'] != "":
                filters['filters'] = filters['filters'] + "AND "
            filters['filters'] += "category:" + "'" + data["category"] + "' "

        if data["subCategory"] != "":
            if filters['filters'] != "":
                filters['filters'] = filters['filters'] + "AND "
            filters['filters'] += "subCategory:" + "'" +  data["subCategory"] + "' "

        if len(data["brands"]) !=0:
            filters['filters'] += "AND " + "("

        for brand in data["brands"]:
            filters['filters'] += "brand:"  + "'" + brand + "' "
            if filters['filters'] != "":
                filters['filters'] = filters['filters'] + "OR "

        if len(data["brands"]) !=0:
            filters['filters'] = filters['filters'][:-3] +  ")"

        client = SearchClient.create(APPLICATION_KEY, ADMIN_KEY)
        if data["ranking"] == 0:
            index = client.init_index('DealsHubProduct')
        elif data["ranking"] == 1:
            index = client.init_index('DealsHubProductPriceAsc')
        else:
            index = client.init_index('DealsHubProductPriceDesc')

        result = index.search(search_string,filters)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("search_algolia_index: %s at %s", e, str(exc_tb.tb_lineno))
    return result

def get_dealshub_product_details(dealshub_product_objs,dealshub_user_obj):
    products = []

    for dealshub_product_obj in dealshub_product_objs:
        try:
            if dealshub_product_obj.now_price==0:
                continue
            temp_dict = {}
            temp_dict["name"] = dealshub_product_obj.get_name()
            temp_dict["brand"] = dealshub_product_obj.get_brand()
            temp_dict["seller_sku"] = dealshub_product_obj.get_seller_sku()
            temp_dict["now_price"] = dealshub_product_obj.get_now_price(dealshub_user_obj)
            temp_dict["was_price"] = dealshub_product_obj.get_was_price(dealshub_user_obj)
            temp_dict["promotional_price"] = dealshub_product_obj.get_promotional_price(dealshub_user_obj)
            temp_dict["moq"] = dealshub_product_obj.get_moq(dealshub_user_obj)
            temp_dict["stock"] = dealshub_product_obj.stock
            temp_dict["is_new_arrival"] = dealshub_product_obj.is_new_arrival
            temp_dict["is_on_sale"] = dealshub_product_obj.is_on_sale
            temp_dict["allowedQty"] = dealshub_product_obj.get_allowed_qty()
            temp_dict["isStockAvailable"] = dealshub_product_obj.stock>0
            product_promotion_details = get_product_promotion_details(dealshub_product_obj)
            for key in product_promotion_details.keys():
                temp_dict[key]=product_promotion_details[key]
            temp_dict["currency"] = dealshub_product_obj.get_currency()
            temp_dict["uuid"] = dealshub_product_obj.uuid
            temp_dict["link"] = dealshub_product_obj.url
            temp_dict["id"] = dealshub_product_obj.uuid
            temp_dict["heroImageUrl"] = dealshub_product_obj.get_display_image_url()
            products.append(temp_dict)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("get_dealshub_product_details: %s at %s", e, str(exc_tb.tb_lineno))

    return products
