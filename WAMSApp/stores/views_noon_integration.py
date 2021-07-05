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


class PushPriceAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:

            if custom_permission_noon_functions(request.user,"push_price_on_noon") == False:
                logger.warning("Noon Integration PushPriceAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("PushPriceAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_pk_list = data["product_pk_list"]

            headers = {
                        "x-partner": "11109", 
                        "x-api-token": "AIzaSyCxOIBdBpXFeo_4YctGCimGaVkusHDu4ZQ",
                        "content-type" : "application/json"
                    }

            with open('/tmp/noon_price_update.tsv', 'wt') as out_file:
                tsv_writer = csv.writer(out_file, delimiter='\t')
                tsv_writer.writerow(['country_code', 'id_partner','partner_sku','price','sale_end','sale_price','sale_start'])
                
                for product_pk in product_pk_list:
                    
                    product_obj = Product.objects.get(pk=int(product_pk))
                    channel_product = product_obj.channel_product
                    noon_product = json.loads(channel_product.noon_product_json)

                    seller_sku = product_obj.base_product.seller_sku
                    was_price = noon_product["was_price"]
                    sale_price = noon_product["sale_price"]
                    sale_start = noon_product["sale_start"]
                    sale_end = noon_product["sale_end"]

                    tsv_writer.writerow([country_code, partner_id ,seller_sku,str(float(was_price)),str(sale_end),str(float(sale_price)),str(sale_start)])
                
            urls = requests.post('https://integration.noon.partners/public/signed-url/noon_price_update.tsv',
                                     headers=headers, timeout=10).json()

            response_noon_excel = requests.put(urls['upload_url'], data=open('/tmp/noon_price_update.tsv','rb')).raise_for_status()

            payload = {
                        "filename": "noon_price_update.tsv", 
                        "import_type": "integration_psku_update", 
                        "url": urls['download_url'],
                        "partner_import_ref": ""
                    }

            response_noon_api = requests.post('https://integration.noon.partners/public/webhook/v2/partner-import', 
                data=json.dumps(payload),
                headers=headers, timeout=10)

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Noon Integration PushPriceAPI: %s at %s",e, str(exc_tb.tb_lineno))

        return Response(data=response)

class PushStockAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            if custom_permission_noon_functions(request.user,"push_stock_on_noon") == False:
                logger.warning("Noon Integration PushStockAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("PushStockAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_pk_list = data["product_pk_list"]

            headers = {
                        "x-partner": "11109", 
                        "x-api-token": "AIzaSyCxOIBdBpXFeo_4YctGCimGaVkusHDu4ZQ",
                        "content-type" : "application/json"
                    }

            with open('/tmp/noon_stock_update.tsv', 'wt') as out_file:
                tsv_writer = csv.writer(out_file, delimiter='\t')
                tsv_writer.writerow(['id_partner','partner_sku','partner_warehouse_code','stock_gross','stock_updated_at'])
                
                for product_pk in product_pk_list:
                    
                    product_obj = Product.objects.get(pk=int(product_pk))
                    channel_product = product_obj.channel_product
                    noon_product = json.loads(channel_product.noon_product_json)

                    seller_sku = product_obj.base_product.seller_sku
                    stock = noon_product["stock"]

                    tsv_writer.writerow([partner_id , seller_sku, partner_warehouse_code,str(int(stock)),""])
               

            urls = requests.post('https://integration.noon.partners/public/signed-url/noon_stock_update.tsv',
                                     headers=headers, timeout=10).json()

            response_noon_excel = requests.put(urls['upload_url'], data=open('/tmp/noon_stock_update.tsv','rb')).raise_for_status()

            payload = {
                        "filename": "noon_stock_update.tsv", 
                        "import_type": "integration_partner_warehouse_stock", 
                        "url": urls['download_url'],
                        "partner_import_ref": ""
                    }

            response_noon_api = requests.post('https://integration.noon.partners/public/webhook/v2/partner-import', 
                            data=json.dumps(payload),
                            headers=headers, timeout=10)

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Noon Integration PushStockAPI: %s at %s",e, str(exc_tb.tb_lineno))

        return Response(data=response)


PushPrice = PushPriceAPI.as_view()

PushStock = PushStockAPI.as_view()