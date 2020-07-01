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

from WAMSApp.views_sourcing import *
from WAMSApp.views_mws_report import *
from WAMSApp.views_mws_orders import *
from WAMSApp.views_mws_amazon_uk import *
from WAMSApp.views_mws_amazon_uae import *
from WAMSApp.views_noon_integration import *
from WAMSApp.views_dh import *
from WAMSApp.views_statistics import *
from WAMSApp.oc_reports import *

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

class BulkUpdateNoonProductPriceAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("BulkUpdateNoonProductPriceAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            channel_name = "Noon"
            channel_obj = Channel.objects.get(name=channel_name)

            if(permission_channel_boolean_response(request.user,channel_obj)==False):
                response['status'] = 403
                logger.warning("BulkUpdateNoonProductPriceAPI Restricted Access of "+channel_name+" Channel!")
                return Response(data=response)

            price_permission = custom_permission_price(request.user, channel_name)
            
            if price_permission:
                path = default_storage.save('tmp/bulk-upload-noon-price.xlsx', data["import_file"])
                path = "https://wig-wams-s3-bucket.s3.ap-south-1.amazonaws.com/"+path

                try :
                    dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
                except Exception as e:
                    response['status'] = 406
                    logger.warning("BulkUpdateNoonProductPriceAPI Sheet 1 not found!")
                    return Response(data=response)

                rows = len(dfs.iloc[:])

                response["excel_errors"] = []

                for i in range(rows):
                    try:

                        if data["option"] = "Product ID" and str(dfs.iloc[0][0]).strip() == "Product ID":
                            search_key = str(dfs.iloc[i][0]).strip()
                            
                            try :
                                product_obj = Product.objects.get(product_id=search_key)
                            except Exception as e:
                                response["excel_errors"].append("More then one product found for " + search_key +)
                                pass

                        elif data["option"] = "Seller SKU" and str(dfs.iloc[0][0]).strip() == "Seller SKU":
                            search_key = str(dfs.iloc[i][0]).strip()
                            
                            try :
                                product_obj = Product.objects.get(base_product__seller_sku=search_key)
                            except Exception as e:
                                response["excel_errors"].append("More then one product found for " + search_key +)
                                pass

                        elif data["option"] = "Noon SKU" and str(dfs.iloc[0][0]).strip() == "Noon SKU":
                            search_key = str(dfs.iloc[i][0]).strip()
                            
                            try :
                                product_obj = Product.objects.get(channel_product_noon_product_json_icontains='"noon_sku": "'+search_key+'"')
                            except Exception as e:
                                response["excel_errors"].append("More then one product found for " + search_key +)
                                pass

                        elif data["option"] = "Partner SKU" and str(dfs.iloc[0][0]).strip() == "Partner SKU":
                            search_key = str(dfs.iloc[i][0]).strip()

                            try :
                                product_obj = Product.objects.get(channel_product_noon_product_json_icontains='"partner_sku": "'+search_key+'"')
                            except Exception as e:
                                response["excel_errors"].append("More then one product found for " + search_key)
                                pass

                        else:
                            response['status'] = 405
                            logger.warning("BulkUpdateNoonProductPriceAPI Wrong Template Uploaded for " + data["option"])
                            return Response(data=response)

                        try :
                            was_price = float(dfs.iloc[i][1])
                            sale_price = float(dfs.iloc[i][2])
                        except Exception as e:
                            response["excel_errors"].append("Wrong Price Value for " + search_key)
                            pass
                        
                        channel_product = product_obj.channel_product

                        channel_product_dict = get_channel_product_dict(channel_name,channel_product)
                        
                        channel_product_dict["was_price"] = was_price
                        channel_product_dict["sale_price"] = sale_price

                        channel_product = assign_channel_product_json(channel_name,channel_product,channel_product_dict)
                            
                        channel_product.save()

                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        logger.error("BulkUpdateNoonProductPriceAPI: %s at %s", e, str(exc_tb.tb_lineno))

                response['status'] = 200

            else :
                response['status'] = 403
                logger.warning("BulkUpdateNoonProductPriceAPI Restricted Access for Price Updation on "+channel_name+" Channel!")
                return Response(data=response)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("BulkUpdateNoonProductPriceAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class BulkUpdateNoonProductStockAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("BulkUpdateNoonProductStockAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            channel_name = "Noon"
            channel_obj = Channel.objects.get(name=channel_name)

            if(permission_channel_boolean_response(request.user,channel_obj)==False):
                response['status'] = 403
                logger.warning("BulkUpdateNoonProductStockAPI Restricted Access of "+channel_name+" Channel!")
                return Response(data=response)

            price_permission = custom_permission_price(request.user, channel_name)
            
            if price_permission:
                path = default_storage.save('tmp/bulk-upload-noon-stock.xlsx', data["import_file"])
                path = "https://wig-wams-s3-bucket.s3.ap-south-1.amazonaws.com/"+path

                try :
                    dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
                except Exception as e:
                    response['status'] = 406
                    logger.warning("BulkUpdateNoonProductStockAPI Sheet 1 not found!")
                    return Response(data=response)

                rows = len(dfs.iloc[:])

                response["excel_errors"] = []

                for i in range(rows):
                    try:

                        if data["option"] = "Product ID" and str(dfs.iloc[0][0]).strip() == "Product ID":
                            search_key = str(dfs.iloc[i][0]).strip()
                            
                            try :
                                product_obj = Product.objects.get(product_id=search_key)
                            except Exception as e:
                                response["excel_errors"].append("More then one product found for " + search_key +)
                                pass

                        elif data["option"] = "Seller SKU" and str(dfs.iloc[0][0]).strip() == "Seller SKU":
                            search_key = str(dfs.iloc[i][0]).strip()
                            
                            try :
                                product_obj = Product.objects.get(base_product__seller_sku=search_key)
                            except Exception as e:
                                response["excel_errors"].append("More then one product found for " + search_key +)
                                pass

                        elif data["option"] = "Noon SKU" and str(dfs.iloc[0][0]).strip() == "Noon SKU":
                            search_key = str(dfs.iloc[i][0]).strip()
                            
                            try :
                                product_obj = Product.objects.get(channel_product_noon_product_json_icontains='"noon_sku": "'+search_key+'"')
                            except Exception as e:
                                response["excel_errors"].append("More then one product found for " + search_key +)
                                pass

                        elif data["option"] = "Partner SKU" and str(dfs.iloc[0][0]).strip() == "Partner SKU":
                            search_key = str(dfs.iloc[i][0]).strip()

                            try :
                                product_obj = Product.objects.get(channel_product_noon_product_json_icontains='"partner_sku": "'+search_key+'"')
                            except Exception as e:
                                response["excel_errors"].append("More then one product found for " + search_key)
                                pass

                        else:
                            response['status'] = 405
                            logger.warning("BulkUpdateNoonProductStockAPI Wrong Template Uploaded for " + data["option"])
                            return Response(data=response)

                        try :
                            stock = int(dfs.iloc[i][1])
                        except Exception as e:
                            response["excel_errors"].append("Wrong Stock Value for " + search_key)
                            pass
                        
                        channel_product = product_obj.channel_product

                        channel_product_dict = get_channel_product_dict(channel_name,channel_product)
                        
                        channel_product_dict["stock"] = stock

                        channel_product = assign_channel_product_json(channel_name,channel_product,channel_product_dict)
                            
                        channel_product.save()

                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        logger.error("BulkUpdateNoonProductStockAPI: %s at %s", e, str(exc_tb.tb_lineno))

                response['status'] = 200

            else :
                response['status'] = 403
                logger.warning("BulkUpdateNoonProductStockAPI Restricted Access for Price Updation on "+channel_name+" Channel!")
                return Response(data=response)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("BulkUpdateNoonProductStockAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class BulkUpdateNoonProductPriceAndStockAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("BulkUpdateNoonProductPriceAndStockAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            channel_name = "Noon"
            channel_obj = Channel.objects.get(name=channel_name)

            if(permission_channel_boolean_response(request.user,channel_obj)==False):
                response['status'] = 403
                logger.warning("BulkUpdateNoonProductPriceAndStockAPI Restricted Access of "+channel_name+" Channel!")
                return Response(data=response)

            price_permission = custom_permission_price(request.user, channel_name)
            
            if price_permission:
                path = default_storage.save('tmp/bulk-upload-noon-price-and-stock.xlsx', data["import_file"])
                path = "https://wig-wams-s3-bucket.s3.ap-south-1.amazonaws.com/"+path

                try :
                    dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
                except Exception as e:
                    response['status'] = 406
                    logger.warning("BulkUpdateNoonProductPriceAndStockAPI Sheet 1 not found!")
                    return Response(data=response)

                rows = len(dfs.iloc[:])

                response["excel_errors"] = []

                for i in range(rows):
                    try:

                        if data["option"] = "Product ID" and str(dfs.iloc[0][0]).strip() == "Product ID":
                            search_key = str(dfs.iloc[i][0]).strip()
                            
                            try :
                                product_obj = Product.objects.get(product_id=search_key)
                            except Exception as e:
                                response["excel_errors"].append("More then one product found for " + search_key +)
                                pass

                        elif data["option"] = "Seller SKU" and str(dfs.iloc[0][0]).strip() == "Seller SKU":
                            search_key = str(dfs.iloc[i][0]).strip()
                            
                            try :
                                product_obj = Product.objects.get(base_product__seller_sku=search_key)
                            except Exception as e:
                                response["excel_errors"].append("More then one product found for " + search_key +)
                                pass

                        elif data["option"] = "Noon SKU" and str(dfs.iloc[0][0]).strip() == "Noon SKU":
                            search_key = str(dfs.iloc[i][0]).strip()
                            
                            try :
                                product_obj = Product.objects.get(channel_product_noon_product_json_icontains='"noon_sku": "'+search_key+'"')
                            except Exception as e:
                                response["excel_errors"].append("More then one product found for " + search_key +)
                                pass

                        elif data["option"] = "Partner SKU" and str(dfs.iloc[0][0]).strip() == "Partner SKU":
                            search_key = str(dfs.iloc[i][0]).strip()

                            try :
                                product_obj = Product.objects.get(channel_product_noon_product_json_icontains='"partner_sku": "'+search_key+'"')
                            except Exception as e:
                                response["excel_errors"].append("More then one product found for " + search_key)
                                pass

                        else:
                            response['status'] = 405
                            logger.warning("BulkUpdateNoonProductPriceAndStockAPI Wrong Template Uploaded for " + data["option"])
                            return Response(data=response)

                        try :
                            was_price = float(dfs.iloc[i][1])
                            sale_price = float(dfs.iloc[i][2])
                        except Exception as e:
                            response["excel_errors"].append("Wrong Price Value for " + search_key)
                            pass
                        
                        try :
                            stock = int(dfs.iloc[i][5])
                        except Exception as e:
                            response["excel_errors"].append("Wrong Stock Value for " + search_key)
                            pass
                        
                        channel_product = product_obj.channel_product

                        channel_product_dict = get_channel_product_dict(channel_name,channel_product)
                        
                        channel_product_dict["was_price"] = was_price
                        channel_product_dict["sale_price"] = sale_price
                        channel_product_dict["stock"] = stock

                        channel_product = assign_channel_product_json(channel_name,channel_product,channel_product_dict)
                            
                        channel_product.save()

                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        logger.error("BulkUpdateNoonProductPriceAndStockAPI: %s at %s", e, str(exc_tb.tb_lineno))

                response['status'] = 200

            else :
                response['status'] = 403
                logger.warning("BulkUpdateNoonProductPriceAndStockAPI Restricted Access for Price Updation on "+channel_name+" Channel!")
                return Response(data=response)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("BulkUpdateNoonProductPriceAndStockAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

BulkUpdateNoonProductPrice = BulkUpdateNoonProductPriceAPI.as_view()

BulkUpdateNoonProductStock = BulkUpdateNoonProductStockAPI.as_view()

BulkUpdateNoonProductPriceAndStock = BulkUpdateNoonProductPriceAndStockAPI.as_view()