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

from datetime import datetime
from django.utils import timezone
from django.core.files import File

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

            w = WebsiteGroup.objects.get(name="shopnesto")
            deashub_products = DealsHubProduct.objects.filter(location_group__website_group=w, product__base_product__brand__in=w.brands.all())
            
            filename = "holding_transfer_report.xlsx"

            workbook = xlsxwriter.Workbook('./'+filename)
            worksheet = workbook.add_worksheet()

            row = ["Seller SKU",
                   "Brand Name",
                   "Company Code",
                   "Holding Before",
                   "Holding After",
                   "ATP Before",
                   "ATP After",
                   "Status",
                   "SAP Message"]

            cnt = 0
                
            colnum = 0
            for k in row:
                worksheet.write(cnt, colnum, k)
                colnum += 1

            for dealshub_product in deashub_products:

                cnt+=1
                common_row = ["" for i in range(9)]

                seller_sku = dealshub_product.get_seller_sku()
                brand_name = dealshub_product.get_brand()
                status = "FAILED"
                
                try:
                    company_code = BRAND_COMPANY_DICT[brand_name.lower()]
                except Exception as e:
                    company_code = "BRAND NOT RECOGNIZED"
                    continue

                common_row[0] = str(seller_sku)
                common_row[1] = str(brand_name)
                common_row[2] = str(company_code)

                try :
                    response_dict = transfer_from_atp_to_holding(seller_sku,company_code)
                   
                    common_row[3] = str(response_dict["total_holding_before"])
                    common_row[5] = str(response_dict["total_atp_before"])
                    common_row[4] = str(response_dict["total_holding_after"])
                    common_row[6] = str(response_dict["total_atp_after"])
                    common_row[7] = str(response_dict["stock_status"])
                    common_row[8] = str(response_dict["SAP_message"])

                except Exception as e:
                    common_row[7] = str("INTERNAL ERROR")
                    continue

                colnum = 0
                for k in common_row:
                    worksheet.write(cnt, colnum, k)
                    colnum += 1
            
            workbook.close()
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("HoldingTransferAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)

FetchPriceAndStock = FetchPriceAndStockAPI.as_view()

HoldingTransfer = HoldingTransferAPI.as_view()