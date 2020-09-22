from WAMSApp.models import *
from dealshub.models import *
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

from datetime import datetime
from django.utils import timezone
from django.core.files import File

logger = logging.getLogger(__name__)

customer_id = "40000195"

stock_price_production_url="http://wig.westernint.com:8000/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"

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

            seller_sku_list = ["GES4026","GES4026","GESL121","GFL3803","GFL3855",
                                "GFL3882","GK175","GPM825","GTR1384","GTR34"]

            company_code = "1000"

            response_dict = transfer_from_atp_to_holding(seller_sku_list,company_code)
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("HoldingTransferAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)

FetchPriceAndStock = FetchPriceAndStockAPI.as_view()

HoldingTransfer = HoldingTransferAPI.as_view()