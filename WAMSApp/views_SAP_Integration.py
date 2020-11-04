from dealshub.models import *
from WAMSApp.SAP_constants import *
from WAMSApp.utils import *
from WAMSApp.utils_SAP_Integration import *

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
import datetime
import threading

from datetime import datetime
from django.utils import timezone
from django.core.files import File

from django.core.mail import send_mail, get_connection
from django.core.mail import EmailMultiAlternatives
from django.core.mail import EmailMessage

logger = logging.getLogger(__name__)

class FetchPriceAndStockAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("FetchPriceAndStockAPI: %s", str(data))

            if custom_permission_sap_functions(request.user,"price_and_stock") == False:
                logger.warning("FetchPriceAndStockAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            if not isinstance(data, dict):
                data = json.loads(data)

            product_pk_list = data["product_pk_list"]
            warehouse_code = data["warehouse_code"]
            
            warehouses_information = []
            
            for product_pk in product_pk_list:

                product_obj = Product.objects.get(pk=int(product_pk))
                price_and_stock_information = fetch_prices_and_stock(product_obj.base_product.seller_sku,warehouse_code)
                
                warehouses_dict = {}
                warehouses_dict["company_code"] = warehouse_code
                warehouses_dict["product_pk"] = product_pk
                warehouses_dict["prices"] = price_and_stock_information["prices"]
                warehouses_dict["total_holding"] = price_and_stock_information["total_holding"]
                warehouses_dict["total_atp"] = price_and_stock_information["total_atp"]
                
                warehouses_information.append(warehouses_dict)

            response["warehouses_information"] = warehouses_information

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchPriceAndStockAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)


class HoldingTransferAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("HoldingTransferAPI: %s", str(data))

            if custom_permission_sap_functions(request.user,"holding_transfer") == False:
                logger.warning("HoldingTransferAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            if not isinstance(data, dict):
                data = json.loads(data)

            website_group_obj = WebsiteGroup.objects.get(name="shopnesto")
            location_group_obj = LocationGroup.objects.first()
            dealshub_product_objs = DealsHubProduct.objects.filter(location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all())
            
            p1 = threading.Thread(target=create_holding_transfer_report, args=(dealshub_product_objs,))
            p1.start()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("HoldingTransferAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)

FetchPriceAndStock = FetchPriceAndStockAPI.as_view()

HoldingTransfer = HoldingTransferAPI.as_view()