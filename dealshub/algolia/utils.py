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

# def add_product_to_index(dealshub_product_obj):

#     client = SearchClient.create(APPLICATION_KEY, ADMIN_KEY)
#     index = client.init_index('DealsHubProduct')
    
#     try:
#         logger.info("add_product_to_index: %s", str(dealshub_product_obj.__dict__))
#         dealshub_product_dict = {}
#         dealshub_product_dict["locationGroup"] = dealshub_product_obj.location_group.uuid
#         dealshub_product_dict["objectID"] = dealshub_product_obj.uuid
#         dealshub_product_dict["productName"] = dealshub_product_obj.get_name()
#         dealshub_product_dict["category"] = dealshub_product_obj.get_category()
#         dealshub_product_dict["superCategory"] = dealshub_product_obj.get_super_category()
#         dealshub_product_dict["subCategory"] = dealshub_product_obj.get_sub_category()
#         dealshub_product_dict["brand"] = dealshub_product_obj.get_brand()
#         dealshub_product_dict["sellerSKU"] = dealshub_product_obj.get_seller_sku()
#         dealshub_product_dict["isPublished"] = dealshub_product_obj.is_published
#         dealshub_product_dict["price"] = dealshub_product_obj.now_price
#         dealshub_product_dict["stock"] = dealshub_product_obj.stock
        
#         index.save_objects(dealshub_product_dict, {'autoGenerateObjectIDIfNotExist': False})
#     except Exception as e:
#         exc_type, exc_obj, exc_tb = sys.exc_info()
#         logger.error("add_product_to_index: %s at %s", e, str(exc_tb.tb_lineno))

def search_algolia_index(data):
    try:
        logger.info("search_algolia_index: %s",str(data))
        if not isinstance(data, dict):
            data = json.loads(data)
 
        search_string = data["search_string"]
        filters = {}
        filters['hitsPerPage'] = data["pageSize"]
        filters['page'] = data["page"]
        filters['facets'] = ['brand','category']
        filters['filters'] = ""

        filters['filters'] += "locationGroup: " + str(data["locationGroupUuid"]) + " "

        if filters['filters'] != "":
            filters['filters'] = filters['filters'] + "AND "
        filters['filters'] += "isPublished: true AND stock > 0 AND price > 0.0 "

        if data.get("superCategory","") != "":
            if filters['filters'] != "":
                filters['filters'] = filters['filters'] + "AND "
            filters['filters'] += "superCategory:" + "'" + data["superCategory"] + "' "

        if data.get("category","") !="":
            if filters['filters'] != "":
                filters['filters'] = filters['filters'] + "AND "
            filters['filters'] += "category:" + "'" + data["category"] + "' "

        if data.get("subCategory","") != "":
            if filters['filters'] != "":
                filters['filters'] = filters['filters'] + "AND "
            filters['filters'] += "subCategory:" + "'" +  data["subCategory"] + "' "

        if len(data.get("brands",[])) !=0:
            filters['filters'] += "AND " + "("

        for brand in data.get("brands",[]):
            filters['filters'] += "brand:"  + "'" + brand + "' "
            if filters['filters'] != "":
                filters['filters'] = filters['filters'] + "OR "

        if len(data.get("brands",[])) !=0:
            filters['filters'] = filters['filters'][:-3] +  ")"

        client = SearchClient.create(APPLICATION_KEY, ADMIN_KEY)
        if data["ranking"] == 0:
            index = client.init_index('DealsHubProduct')
        elif data["ranking"] == 1:
            index = client.init_index('DealsHubProductPriceDesc')
        else:
            index = client.init_index('DealsHubProductPriceAsc')

        result = index.search(search_string,filters)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("search_algolia_index: %s at %s", e, str(exc_tb.tb_lineno))
    return result


def search_algolia_suggestions(data):
    try:
        logger.info("search_algolia_suggestions: %s",str(data))
        if not isinstance(data, dict):
            data = json.loads(data)

        search_string = data["search_string"]
        filters = {}

        client = SearchClient.create(APPLICATION_KEY, ADMIN_KEY)
        index = client.init_index('DealsHubProductQuerySuggestions')

        result = index.search(search_string,filters)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("search_algolia_suggestions: %s at %s", e, str(exc_tb.tb_lineno))
    return result
