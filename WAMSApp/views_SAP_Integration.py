from WAMSApp.models import *
from WAMSApp.utils import *

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Count
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

import requests
import json
import pytz
import csv
import logging
import sys
import xlrd
import time

from datetime import datetime
from django.utils import timezone
from django.core.files import File

logger = logging.getLogger(__name__)

partner_id = "11109"
country_code = "ae"
partner_warehouse_code = "12345"

class FetchPriceAndStockAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchStatisticsAPI: %s", str(data))

            page = int(data["page"])
            brand_name = data.get("brand_name","")

            filter_parameters = data["filter_parameters"]
           
            permissible_brands = custom_permission_filter_brands(request.user)

            if(brand_name != ""):
                permissible_brands = permissible_brands.filter(name=brand_name)

            permissible_brands = permissible_brands.annotate(num_products=Count('baseproduct')).order_by('-num_products')

            paginator = Paginator(permissible_brands, 5)
            brand_objs = paginator.page(page)

            brand_list = []
            for brand_obj in brand_objs:

                search_list_product_objs = Product.objects.filter(base_product__brand=brand_obj)
                total_products = search_list_product_objs.count()

                search_list_product_objs = content_health_filtered_list(filter_parameters,search_list_product_objs)


                temp_dict = {}
                temp_dict["brand_name"] = brand_obj.name
                temp_dict["value"] = search_list_product_objs.count()
                temp_dict["total_products"] = total_products

                brand_list.append(temp_dict)

            attribute_list = [
                "Product Description",
                "Product Name",
                "Product ID",
                "Product Verified",
                "Amazon UK Product",
                "Amazon UAE Product",
                "Noon Product",
                "Ebay Product",
                "Product Features",
                "White Background Images > 0",
                "White Background Images > 1",
                "White Background Images > 2",
                "Lifestyle Images > 0",
                "Lifestyle Images > 1",
                "Lifestyle Images > 2",
                "Giftbox Images > 0",
                "Giftbox Images > 1",
                "Giftbox Images > 2",
                "Transparent Images > 0",
                "Transparent Images > 1",
                "Transparent Images > 2",
                "Main Images",
                "Sub Images > 0",
                "Sub Images > 1",
                "Sub Images > 2"]

            is_available = True

            if paginator.num_pages == page:
                is_available = False

            response["is_available"] = is_available
            response["keys"] = attribute_list
            response["brand_list"] = brand_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchPriceAndStockAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)

FetchPriceAndStock = FetchPriceAndStockAPI.as_view()