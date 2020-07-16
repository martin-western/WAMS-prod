from django.db.models import Count

from WAMSApp.models import *

from auditlog.models import *
from dealshub.models import DealsHubProduct
from WAMSApp.utils import *
from WAMSApp.constants import *

from django.shortcuts import render, HttpResponse, get_object_or_404
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required

from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models import Count
from django.conf import settings

from PIL import Image as IMage
from io import BytesIO as StringIO
from django.core.files.uploadedfile import InMemoryUploadedFile

import barcode
from barcode.writer import ImageWriter

import xmltodict
import requests
import json
import os
import xlrd
import csv
import datetime
import boto3
import urllib.request, urllib.error, urllib.parse
import pandas as pd
import threading

logger = logging.getLogger(__name__)

class BulkUpdateAmazonUAEProductPriceAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("BulkUpdateAmazonUAEProductPriceAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            channel_name = "Amazon UAE"
            channel_obj = Channel.objects.get(name=channel_name)

            if(permission_channel_boolean_response(request.user,channel_obj)==False):
                response['status'] = 403
                logger.warning("BulkUpdateAmazonUAEProductPriceAPI Restricted Access of "+channel_name+" Channel!")
                return Response(data=response)

            price_permission = custom_permission_price(request.user, channel_name)
            
            if not price_permission:
                response['status'] = 403
                logger.warning("BulkUpdateAmazonUAEProductPriceAPI Restricted Access for Price Updation on "+channel_name+" Channel!")
                return Response(data=response)

            path = default_storage.save('tmp/bulk-upload-noon-price.xlsx', data["import_file"])
            path = "https://wig-wams-s3-bucket.s3.ap-south-1.amazonaws.com/"+path

            try :
                dfs = pd.read_excel(path, sheet_name=None)
            except Exception as e:
                response['status'] = 407
                logger.warning("BulkUpdateAmazonUAEProductPriceAPI UnSupported File Format ")
                return Response(data=response)

            try :
                dfs = dfs["Sheet1"]
            except Exception as e:
                response['status'] = 406
                logger.warning("BulkUpdateAmazonUAEProductPriceAPI Sheet1 not found!")
                return Response(data=response)

            rows = len(dfs.iloc[:])
            excel_header = str(dfs.columns[0]).strip()

            if data["option"] != excel_header:
                response['status'] = 405
                logger.warning("BulkUpdateAmazonUAEProductPriceAPI Wrong Template Uploaded for " + data["option"])
                return Response(data=response)

            excel_errors = []

            for i in range(rows):
                try:

                    product_obj = None

                    if data["option"] == "Product ID":
                        search_key = str(int(dfs.iloc[i][0])).strip()
                        
                        try :
                            product_obj = Product.objects.get(product_id=search_key)
                        except Exception as e:
                            excel_errors.append("More than one product found for " + search_key)
                            continue

                    elif data["option"] == "Seller SKU":
                        search_key = str(dfs.iloc[i][0]).strip()
                        
                        try :
                            product_obj = Product.objects.get(base_product__seller_sku=search_key)
                        except Exception as e:
                            excel_errors.append("More than one product found for " + search_key)
                            continue

                    elif data["option"] == "ASIN":
                        search_key = str(dfs.iloc[i][0]).strip()
                        
                        try :
                            product_obj = Product.objects.get(channel_product_amazon_uae_product_json_icontains='"ASIN": "'+search_key+'"')
                        except Exception as e:
                            excel_errors.append("More than one product found for " + search_key)
                            continue

                    try :
                        was_price = float(dfs.iloc[i][1])
                        sale_price = float(dfs.iloc[i][2])
                    except Exception as e:
                        excel_errors.append("Wrong Price Value for " + search_key)
                        continue
                    
                    channel_product = product_obj.channel_product

                    channel_product_dict = get_channel_product_dict(channel_name,channel_product)
                    
                    channel_product_dict["was_price"] = was_price
                    channel_product_dict["sale_price"] = sale_price

                    channel_product = assign_channel_product_json(channel_name,channel_product,channel_product_dict)
                        
                    channel_product.save()

                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("BulkUpdateAmazonUAEProductPriceAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["excel_errors"] = excel_errors
            response['status'] = 200               

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("BulkUpdateAmazonUAEProductPriceAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class BulkUpdateAmazonUAEProductStockAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("BulkUpdateAmazonUAEProductStockAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            channel_name = "Amazon UAE"
            channel_obj = Channel.objects.get(name=channel_name)

            if(permission_channel_boolean_response(request.user,channel_obj)==False):
                response['status'] = 403
                logger.warning("BulkUpdateAmazonUAEProductStockAPI Restricted Access of "+channel_name+" Channel!")
                return Response(data=response)

            stock_permission = custom_permission_stock(request.user, channel_name)
            
            if not stock_permission:
                response['status'] = 403
                logger.warning("BulkUpdateAmazonUAEProductStockAPI Restricted Access for Price Updation on "+channel_name+" Channel!")
                return Response(data=response)

            path = default_storage.save('tmp/bulk-upload-noon-stock.xlsx', data["import_file"])
            path = "https://wig-wams-s3-bucket.s3.ap-south-1.amazonaws.com/"+path

            try :
                dfs = pd.read_excel(path, sheet_name=None)
            except Exception as e:
                response['status'] = 407
                logger.warning("BulkUpdateAmazonUAEProductStockAPI UnSupported File Format ")
                return Response(data=response)

            try :
                dfs = dfs["Sheet1"]
            except Exception as e:
                response['status'] = 406
                logger.warning("BulkUpdateAmazonUAEProductStockAPI Sheet1 not found!")
                return Response(data=response)

            rows = len(dfs.iloc[:])
            excel_header = str(dfs.columns[0]).strip()

            if data["option"] != excel_header:
                response['status'] = 405
                logger.warning("BulkUpdateAmazonUAEProductStockAPI Wrong Template Uploaded for " + data["option"])
                return Response(data=response)

            excel_errors = []

            for i in range(rows):
                try:

                    product_obj = None

                    if data["option"] == "Product ID":
                        search_key = str(int(dfs.iloc[i][0])).strip()
                        
                        try :
                            product_obj = Product.objects.get(product_id=search_key)
                        except Exception as e:
                            excel_errors.append("More then one product found for " + search_key)
                            continue

                    elif data["option"] == "Seller SKU":
                        search_key = str(dfs.iloc[i][0]).strip()
                        
                        try :
                            product_obj = Product.objects.get(base_product__seller_sku=search_key)
                        except Exception as e:
                            excel_errors.append("More then one product found for " + search_key)
                            continue

                    elif data["option"] == "ASIN":
                        search_key = str(dfs.iloc[i][0]).strip()
                        
                        try :
                            product_obj = Product.objects.get(channel_product_amazon_uae_product_json_icontains='"ASIN": "'+search_key+'"')
                        except Exception as e:
                            excel_errors.append("More then one product found for " + search_key )
                            continue

                    try :
                        stock = int(dfs.iloc[i][1])
                    except Exception as e:
                        response["excel_errors"].append("Wrong Stock Value for " + search_key)
                        continue
                    
                    channel_product = product_obj.channel_product

                    channel_product_dict = get_channel_product_dict(channel_name,channel_product)
                    
                    channel_product_dict["stock"] = stock

                    channel_product = assign_channel_product_json(channel_name,channel_product,channel_product_dict)
                        
                    channel_product.save()

                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("BulkUpdateAmazonUAEProductStockAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["excel_errors"] = excel_errors
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("BulkUpdateAmazonUAEProductStockAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class BulkUpdateAmazonUAEProductPriceAndStockAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("BulkUpdateAmazonUAEProductPriceAndStockAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            channel_name = "Amazon UAE"
            channel_obj = Channel.objects.get(name=channel_name)

            if(permission_channel_boolean_response(request.user,channel_obj)==False):
                response['status'] = 403
                logger.warning("BulkUpdateAmazonUAEProductPriceAndStockAPI Restricted Access of "+channel_name+" Channel!")
                return Response(data=response)

            price_permission = custom_permission_price(request.user, channel_name)
            stock_permission = custom_permission_stock(request.user, channel_name)

            if not price_permission or not stock_permission:
                response['status'] = 403
                logger.warning("BulkUpdateAmazonUAEProductPriceAndStockAPI Restricted Access for Price and Stock Updation on "+channel_name+" Channel!")
                return Response(data=response)

            path = default_storage.save('tmp/bulk-upload-noon-price-and-stock.xlsx', data["import_file"])
            path = "https://wig-wams-s3-bucket.s3.ap-south-1.amazonaws.com/"+path

            try :
                dfs = pd.read_excel(path, sheet_name=None)
            except Exception as e:
                response['status'] = 407
                logger.warning("BulkUpdateAmazonUAEProductPriceAndStockAPI UnSupported File Format ")
                return Response(data=response)

            try :
                dfs = dfs["Sheet1"]
            except Exception as e:
                response['status'] = 406
                logger.warning("BulkUpdateAmazonUAEProductPriceAndStockAPI Sheet1 not found!")
                return Response(data=response)

            rows = len(dfs.iloc[:])
            excel_header = str(dfs.columns[0]).strip()

            if data["option"] != excel_header:
                response['status'] = 405
                logger.warning("BulkUpdateAmazonUAEProductPriceAPI Wrong Template Uploaded for " + data["option"])
                return Response(data=response)

            excel_errors = []

            for i in range(rows):
                try:

                    product_obj = None

                    if data["option"] == "Product ID":
                        search_key = str(int(dfs.iloc[i][0])).strip()
                        
                        try :
                            product_obj = Product.objects.get(product_id=search_key)
                        except Exception as e:
                            excel_errors.append("More then one product found for " + search_key)
                            continue

                    elif data["option"] == "Seller SKU":
                        search_key = str(dfs.iloc[i][0]).strip()
                        
                        try :
                            product_obj = Product.objects.get(base_product__seller_sku=search_key)
                        except Exception as e:
                            excel_errors.append("More then one product found for " + search_key)
                            continue

                    elif data["option"] == "ASIN":
                        search_key = str(dfs.iloc[i][0]).strip()
                        
                        try :
                            product_obj = Product.objects.get(channel_product_amazon_uae_product_json_icontains='"ASIN": "'+search_key+'"')
                        except Exception as e:
                            excel_errors.append("More then one product found for " + search_key)
                            continue

                    try :
                        was_price = float(dfs.iloc[i][1])
                        sale_price = float(dfs.iloc[i][2])
                    except Exception as e:
                        excel_errors.append("Wrong Price Value for " + search_key)
                        continue
                    
                    try :
                        stock = int(dfs.iloc[i][5])
                    except Exception as e:
                        excel_errors.append("Wrong Stock Value for " + search_key)
                        continue
                    
                    channel_product = product_obj.channel_product

                    channel_product_dict = get_channel_product_dict(channel_name,channel_product)
                    
                    channel_product_dict["was_price"] = was_price
                    channel_product_dict["sale_price"] = sale_price
                    channel_product_dict["stock"] = stock

                    channel_product = assign_channel_product_json(channel_name,channel_product,channel_product_dict)
                        
                    channel_product.save()

                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("BulkUpdateAmazonUAEProductPriceAndStockAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["excel_errors"] = excel_errors
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("BulkUpdateAmazonUAEProductPriceAndStockAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

BulkUpdateAmazonUAEProductPrice = BulkUpdateAmazonUAEProductPriceAPI.as_view()

BulkUpdateAmazonUAEProductStock = BulkUpdateAmazonUAEProductStockAPI.as_view()

BulkUpdateAmazonUAEProductPriceAndStock = BulkUpdateAmazonUAEProductPriceAndStockAPI.as_view()