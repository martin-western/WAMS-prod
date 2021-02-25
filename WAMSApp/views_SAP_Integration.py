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
import pandas as pd

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
            dealshub_product_objs = DealsHubProduct.objects.filter(is_published=True, location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all()).exclude(now_price=0)
            
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
        response["message"] = ""

        try:

            data = request.data
            logger.info("BulkHoldingTransferAPI: %s",str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if custom_permission_sap_functions(request.user,"holding_transfer") == False:
                logger.warning("HoldingTransferAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            path = default_storage.save('tmp/bulk-upload-holding-transfer.xlsx', data["import_file"])
            path = "http://cdn.omnycomm.com.s3.amazonaws.com/"+path

            try :
                dfs = pd.read_excel(path, sheet_name=None)
            except Exception as e:
                response['status'] = 407
                response['message'] = "UnSupported File Format"
                logger.warning("BulkHoldingTransferAPI UnSupported File Format")
                return Response(data=response)

            try :
                dfs = dfs["Sheet1"]
            except Exception as e:
                response['status'] = 406
                response['message'] = "Sheet1 not found!"
                logger.warning("BulkHoldingTransferAPI Sheet1 not found")
                return Response(data=response)

            dfs = dfs.fillna("")
            rows = len(dfs.iloc[:])
            column_header = str(dfs.columns[0]).strip()

            if column_header != "Seller SKU":
                response['status'] = 405
                response['message'] = "Seller SKU Column not found"
                logger.warning("BulkHoldingTransferAPI Seller SKU Column not found")
                return Response(data=response)


            sku_list = dfs['Seller SKU'] 

            excel_errors = []

            for sku in sku_list:

                sku = sku.strip()              
                dealshub_product_objs = DealsHubProduct.objects.filter(product__base_product__seller_sku=sku)
                    
                if dealshub_product_objs.count()==0:
                    temp_dict = {}
                    temp_dict["seller_sku"] = sku
                    temp_dict['error_message'] = "Product not found"
                    excel_errors.append(temp_dict)
                    continue
                    
                if dealshub_product_objs.count()>1:
                    temp_dict = {}
                    temp_dict["seller_sku"] = sku
                    temp_dict['error_message'] = "More then one product found"
                    excel_errors.append(temp_dict)
                    continue   

                brand_name = dealshub_product_obj.get_brand().lower()

                try:
                    company_code = BRAND_COMPANY_DICT[brand_name]
                except Exception as e:
                    company_code = "BRAND NOT RECOGNIZED"
                    temp_dict = {}
                    temp_dict["seller_sku"] = sku
                    temp_dict['error_message'] = "BRAND NOT RECOGNIZED"
                    excel_errors.append(temp_dict)
                    continue
                
                if company_code != "BRAND NOT RECOGNIZED":
                    
                    try :
                        transfer_result = transfer_from_atp_to_holding(data_seller_sku,company_code)
                        SAP_message = transfer_result["SAP_message"]
                        
                        if SAP_message != "NO HOLDING TRANSFER" and SAP_message != "Successfully Updated.":
                            temp_dict = {}
                            temp_dict["seller_sku"] = sku
                            temp_dict['error_message'] = SAP_message
                            excel_errors.append(temp_dict)

                    except Exception as e:
                        temp_dict = {}
                        temp_dict["seller_sku"] = sku
                        temp_dict['error_message'] = "INTERNAL ERROR"
                        excel_errors.append(temp_dict)
                        continue
            
            response['excel_errors'] = excel_errors
            response['status'] = 200
            response['message'] = "Succesful"

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("BulkHoldingTransferAPI: %s at %s", str(e), str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchProductHoldingDetailsAPI(APIView):
    
    def post(self, request, *args, **kwargs):
    
        response = {}
        response['status'] = 500

        try:
            data = request.data
            logger.info("FetchProductHoldingDetailsAPI: %s", str(data))

            product_uuid = data["product_uuid"]

            dealshub_product_obj = DealsHubProduct.objects.get(uuid=product_uuid)  

            result = fetch_product_holding_details(dealshub_product_obj)
            
            response['holding_details'] = result
            response['seller_sku'] = dealshub_product_obj.get_seller_sku()
            response['product_id'] = dealshub_product_obj.get_product_id()
            response['product_name'] = dealshub_product_obj.get_name()
            response['product_image'] = dealshub_product_obj.get_main_image_url()
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductHoldingDetailsAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)


class UpdateProductHoldingDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):
        
        response = {}
        response['status'] = 500

        try:
            data = request.data
            logger.info("UpdateProductHoldingDetailsAPI: %s", str(data))

            product_uuid = data["product_uuid"]
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=product_uuid)
            
            final_holding = data.get("holding",0)
            brand_name = dealshub_product_obj.get_brand().lower()
            data_seller_sku = str(dealshub_product_obj.get_seller_sku())
            try:
                company_code = BRAND_COMPANY_DICT[brand_name]
            except Exception as e:
                company_code = "BRAND NOT RECOGNIZED"

            if company_code != "BRAND NOT RECOGNIZED":
                try :
                    transfer_result = holding_atp_transfer(data_seller_sku,company_code,final_holding)
                    SAP_message = transfer_result["SAP_message"]
                    
                    if SAP_message != "NO HOLDING TRANSFER" and SAP_message != "Successfully Updated.":
                        response["seller_sku"] = data_seller_sku
                        response['error_message'] = SAP_message
                        return Response(data=response)
                except Exception as e:
                    response["message"] = "INTERNAL ERROR"
                    response['status'] = 501
                    return Response(data=response)
    
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateProductHoldingDetailsAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)


BulkHoldingTransfer = BulkHoldingTransferAPI.as_view()

FetchPriceAndStock = FetchPriceAndStockAPI.as_view()

HoldingTransfer = HoldingTransferAPI.as_view()

FetchProductHoldingDetails = FetchProductHoldingDetailsAPI.as_view()

UpdateProductHoldingDetails = UpdateProductHoldingDetailsAPI.as_view()