from dealshub.models import *
from dealshub.core_utils import *


import datetime
from django.utils import timezone

import hashlib
import random
import sys
import logging
import os
import json
import requests
from dealshub.constants import *


def index_on_elasticsearch(dealshub_product_obj):

	try:
		location_group_obj = dealshub_product_obj.location_group
		location_group_name = location_group_obj.name
	    updated_fields = {
	        "productName":dealshub_product_obj.get_name(),
	        "brandName":dealshub_product_obj.get_brand(),
	        "superCategory":dealshub_product_obj.get_super_category(),
	        "category":dealshub_product_obj.get_category(),
	        "subCategory":dealshub_product_obj.get_sub_category(),
	        "sellerSKU":dealshub_product_obj.get_seller_sku(),
	        "price":dealshub_product_obj.now_price,
	    }

	    data = {
	    	"doc": updated_fields,
	    	"doc_as_upsert": true
	    }
	    url = ELASTICSEARCH_IP+"/"+location_group_name + "/" + dealshub_product_obj.uuid + "/_update"
	    requests.put(url = url, data = data)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("index_on_elasticsearch: %s at %s", e, str(exc_tb.tb_lineno))

