from WAMSApp.models import *
from dealshub.models import *
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

customer_id = "40000195"

stock_price_production_url="http://wig.westernint.com:8000/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"

class FetchPriceAndStockAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("FetchPriceAndStockAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_pk = data["product_pk"]
            warehouse_code = data["warehouse_code"]

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

            if not isinstance(data, dict):
                data = json.loads(data)

            seller_sku_list = GES4026

EXTENSION SOCKET- BS PLUG

BS

1278

GES4026

EXTENSION SOCKET- BS PLUG

ESMA

1000

GESL121

20W/2U/PIN ENERGY SAVING LAMP 1X100

 

2051

GFL3803

287 MM Length Flash Light  1X20

 

3255

GFL3855

208 MM LENGTH FLASH LIGHT 1X20

BS

875

GFL3882

3In 1 Family Pack Led Flashlight 1X12

 

1909

GK175

TRAVELING KETTLE

 

950

GPM825

POPCORN MAKER 1X8

BS

2138

GTR1384

RECHARGEABLE TRIMMER 1X24

 

1304

GTR34
            for seller_sku in seller_sku_list:


            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("HoldingTransferAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)

FetchPriceAndStock = FetchPriceAndStockAPI.as_view()

HoldingTransfer = HoldingTransferAPI.as_view()