from dealshub.models import *
from WAMSApp.SAP_constants import *
from WAMSApp.utils import *
from WAMSApp.utils_SAP_Integration import *

from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny

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

logger = logging.getLogger(__name__)

class CsrfExemptSessionAuthentication(SessionAuthentication):

    def enforce_csrf(self, request):
        return

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

    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("HoldingTransferAPI: %s", str(data))

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


class BulkHoldingTransferAPI(APIView):

    def post(self,request,*args, **kwargs):
        
        response = {}
        response['status'] = 500

        try:

            data = request.data
            logger.info("BulkHoldingTransferAPI: %s",str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            # TODO: get the seller_sku from xlxs file in request (" DOUBT ")
            file_name = request.files['excel'].filename
            content = request.files['excel'].read()
            if sys.version_info[0] > 2:
                # in order to support python 3 have to decode bytes to str
                content = content.decode('utf-8')

            df = pd.read_excel(file_name, sheet_name=None)

            data_seller_skus = df['seller_sku'] 

            # assuming the data_seller_skus is avaliable

            transfer_information_list = []
            for data_seller_sku in data_seller_skus:              
                # TODO: transfer the holding to seller_sku
                dealshub_product_obj = DealsHubProduct.objects.get(product__base_product__seller_sku=data_seller_sku)
                brand_name = dealshub_product_obj.get_brand()

                try:
                    company_code = BRAND_COMPANY_DICT[brand_name.lower()]
                except Exception as e:
                    company_code = "BRAND NOT RECOGNIZED"
                
                if(company_code != "BRAND NOT RECOGNIZED"):
                    transfer_information = transfer_from_atp_to_holding(data_seller_sku,company_code)
                    transfer_information_list.append(transfer_information)
            
            response['transfer_information'] = transfer_information_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("BulkHoldingTransferAPI: %s at %s", str(e), str(exc_tb.tb_lineno))
        
        return Response(data=response)


BulkHoldingTransfer = BulkHoldingTransferAPI.as_view()

FetchPriceAndStock = FetchPriceAndStockAPI.as_view()

HoldingTransfer = HoldingTransferAPI.as_view()