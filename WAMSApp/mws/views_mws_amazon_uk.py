from WAMSApp.models import *
from WAMSApp.utils import *
from WAMSApp.mws.xml_generators_uk import *

from MWS import mws,APIs

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Count
from django.conf import settings
from django.core.mail import EmailMessage

import requests
import json
import pytz
import csv
import logging
import sys
import xlrd
import time
import re

from datetime import datetime
from django.utils import timezone
from django.core.files import File

logger = logging.getLogger(__name__)

MWS_PARAMS = settings.MWS_PARAMS

MWS_ACCESS_KEY = MWS_PARAMS["MWS_ACCESS_KEY"] 
MWS_SECRET_KEY = MWS_PARAMS["MWS_SECRET_KEY"]
SELLER_ID = MWS_PARAMS["SELLER_ID"]

marketplace_id = mws.Marketplaces["UK"].marketplace_id

class GetMatchingProductsAmazonUKAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if custom_permission_mws_functions(request.user,"push_product_on_amazon") == False:
                logger.warning("GetMatchingProductsAmazonUKAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("GetMatchingProductsAmazonUKAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_pk_list = data["product_pk_list"]

            if(len(product_pk_list)>30):
                logger.warning("GetMatchingProductsAmazonUKAPI More then 30 Products!")
                response['status'] = 429
                return Response(data=response)

            permissible_channels = custom_permission_filter_channels(request.user)
            channel_obj = Channel.objects.get(name="Amazon UK")

            if channel_obj not in permissible_channels:
                logger.warning(
                    "GetMatchingProductsAmazonUKAPI Restricted Access of UK Channel!")
                response['status'] = 403
                return Response(data=response)

            products_api = APIs.Products(MWS_ACCESS_KEY,MWS_SECRET_KEY,SELLER_ID, 
                                        region='UK')

            barcodes_list = []
            matched_products_list = []

            for product_pk in product_pk_list:

                product_obj = Product.objects.get(pk=product_pk)
                product_id_type = None
                if(product_obj.product_id_type!=None):
                    product_id_type = product_obj.product_id_type
                barcode_string = product_obj.barcode_string
                product_id = product_obj.product_id

                if product_id!= None and product_id!="" and product_id_type!=None:
                    barcodes_list.append((product_id_type.name,product_id,product_pk))
                else:
                    temp_dict = {}
                    temp_dict["status"] = "Product ID Not Found"
                    temp_dict["product_pk"] = product_pk
                    temp_dict["matched_ASIN"] = ""
                    temp_dict["matched_product_title"] = ""
                    matched_products_list.append(temp_dict)

            final_barcodes_list = sorted(barcodes_list, key=lambda x: x[0])

            if len(final_barcodes_list) > 0:
                temp = final_barcodes_list[0][0]
            else:
                temp = "ASIN"
            flag=0
            id_list = []
            pk_list = []
            cnt=0
            i=0

            while i < len(final_barcodes_list):
                
                barcode_type = final_barcodes_list[i][0]
                barcode_string = final_barcodes_list[i][1]
                pk = final_barcodes_list[i][2]

                id_list.append(barcode_string)
                pk_list.append(pk)
                
                if temp != barcode_type:
                    flag=1
                    i-=1
                    id_list.pop()
                    pk_list.pop()
                
                if flag != 1:
                    if i%5 == 4:
                        flag=1

                if i == len(final_barcodes_list) - 1:
                    flag=1

                if flag==1 and len(id_list) !=0:
                    

                    products = products_api.get_matching_product_for_id(marketplace_id=marketplace_id, type_=temp, ids = id_list)
                    # print(products.parsed)
                    logger.info("Parsed Products : %s ",products.parsed)
                    
                    if isinstance(products.parsed,list):
                        
                        for j in range(len(products.parsed)):
                            
                            temp_dict = {}
                            temp_dict["status"] = products.parsed[j]["status"]["value"]
                            temp_dict["product_pk"] = pk_list[j]
                            temp_dict["matched_ASIN"] = ""
                            if temp_dict["status"] == "Success":
                                channel_product = Product.objects.get(pk=pk_list[j]).channel_product
                                amazon_uk_product = json.loads(channel_product.amazon_uk_product_json)
                                parsed_products = products.parsed[j]["Products"]["Product"]
                                if isinstance(parsed_products,list):
                                    temp_dict["matched_ASIN"] = parsed_products[0]["Identifiers"]["MarketplaceASIN"]["ASIN"]["value"]
                                    temp_dict["matched_product_title"] = parsed_products[0]["AttributeSets"]["ItemAttributes"]["Title"]["value"]
                                else:
                                    temp_dict["matched_ASIN"] = products.parsed[j]["Products"]["Product"]["Identifiers"]["MarketplaceASIN"]["ASIN"]["value"]
                                    temp_dict["matched_product_title"] = products.parsed[j]["Products"]["Product"]["AttributeSets"]["ItemAttributes"]["Title"]["value"]
                                amazon_uk_product["ASIN"] = temp_dict["matched_ASIN"]
                                channel_product.amazon_uk_product_json = json.dumps(amazon_uk_product)
                                channel_product.save()
                            else :
                                temp_dict["status"] = "New Product"
                                product_obj = Product.objects.get(pk=pk_list[j])
                                channel_product = product_obj.channel_product
                                amazon_uk_product = json.loads(channel_product.amazon_uk_product_json)
                                amazon_uk_product["status"] = "New"
                                channel_product.amazon_uk_product_json = json.dumps(amazon_uk_product)
                                channel_product.save()

                            matched_products_list.append(temp_dict)

                    else:
                        temp_dict = {}
                        temp_dict["status"] = products.parsed["status"]["value"]
                        temp_dict["product_pk"] = pk_list[0]
                        temp_dict["matched_ASIN"] = ""
                        if temp_dict["status"] == "Success":
                            product_obj = Product.objects.get(pk=pk_list[0])
                            channel_product = product_obj.channel_product
                            amazon_uk_product = json.loads(channel_product.amazon_uk_product_json)
                            parsed_products = products.parsed["Products"]["Product"]
                            if isinstance(parsed_products,list):
                                temp_dict["matched_ASIN"] = parsed_products[0]["Identifiers"]["MarketplaceASIN"]["ASIN"]["value"]
                                temp_dict["matched_product_title"] = parsed_products[0]["AttributeSets"]["ItemAttributes"]["Title"]["value"]
                            else:
                                temp_dict["matched_ASIN"] = products.parsed["Products"]["Product"]["Identifiers"]["MarketplaceASIN"]["ASIN"]["value"]
                                temp_dict["matched_product_title"] = products.parsed["Products"]["Product"]["AttributeSets"]["ItemAttributes"]["Title"]["value"]
                            amazon_uk_product["ASIN"] = temp_dict["matched_ASIN"]
                            channel_product.amazon_uk_product_json = json.dumps(amazon_uk_product)
                            channel_product.save()
                        else :
                            temp_dict["status"] = "New Product"
                            product_obj = Product.objects.get(pk=pk_list[0])
                            channel_product = product_obj.channel_product
                            amazon_uk_product = json.loads(channel_product.amazon_uk_product_json)
                            amazon_uk_product["status"] = "New"
                            channel_product.amazon_uk_product_json = json.dumps(amazon_uk_product)
                            channel_product.save()

                        temp_dict["amazon_url"] = ""
                        if temp_dict["matched_ASIN"] != "":
                            temp_dict["amazon_url"] = "https://www.amazon.UK/dp/"+str(temp_dict["matched_ASIN"])
                        
                        matched_products_list.append(temp_dict)
                        
                    id_list = []
                    pk_list = []
                    flag = 0
                    cnt+=1

                    if(cnt%2==0):
                        time.sleep(1)

                temp = barcode_type
                i+=1

                if len(id_list)==0:
                    flag=0

            response['matched_products_list'] = matched_products_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("GetMatchingProductsAmazonUKAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class GetPricingProductsAmazonUKAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if custom_permission_mws_functions(request.user,"push_product_on_amazon") == False:
                logger.warning("GetPricingProductsAmazonUKAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("GetPricingProductsAmazonUKAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_pk_list = data["product_pk_list"]

            if(len(product_pk_list)>30):
                logger.warning("GetPricingProductsAmazonUKAPI More then 30 Products!")
                response['status'] = 429
                return Response(data=response)

            permissible_channels = custom_permission_filter_channels(request.user)
            channel_obj = Channel.objects.get(name="Amazon UK")

            if channel_obj not in permissible_channels:
                logger.warning(
                    "GetPricingProductsAmazonUKAPI Restricted Access of UK Channel!")
                response['status'] = 403
                return Response(data=response)

            products_api = APIs.Products(MWS_ACCESS_KEY,MWS_SECRET_KEY,SELLER_ID, 
                                        region='UK')

            barcodes_list = []
            pricing_information = {}
            competitive_pricing_list = []
            lowest_offer_listings_list = []
            lowest_priced_offers_list = []

            for product_pk in product_pk_list:

                product_obj = Product.objects.get(pk=product_pk)
                channel_product = product_obj.channel_product
                amazon_uk_product = json.loads(channel_product.amazon_uk_product_json)
                product_asin = amazon_uk_product["ASIN"]

                if product_asin!="":
                    barcodes_list.append((product_asin,product_pk))
                else:
                    temp_dict = {}
                    temp_dict["status"] = "ASIN Not Found"
                    temp_dict["product_pk"] = product_pk
                    temp_dict["competitive_pricing"] = {}
                    competitive_pricing_list.append(temp_dict)
                    temp_dict = {}
                    temp_dict["status"] = "ASIN Not Found"
                    temp_dict["product_pk"] = product_pk
                    temp_dict["lowest_priced_offers"] = {}
                    lowest_priced_offers_list.append(temp_dict)
                    temp_dict = {}
                    temp_dict["status"] = "ASIN Not Found"
                    temp_dict["product_pk"] = product_pk
                    temp_dict["lowest_offer_listings"] = {}
                    lowest_offer_listings_list.append(temp_dict)

                    

            id_list = []
            pk_list = []
            cnt=0
            i=0
            flag=0

            while i < len(barcodes_list):
                
                barcode_string = barcodes_list[i][0]
                pk = barcodes_list[i][1]

                id_list.append(barcode_string)
                pk_list.append(pk)
                
                if i%5 == 4:
                    flag=1

                if i == len(barcodes_list) - 1:
                    flag=1

                if flag==1:
                    
                    products = products_api.get_competitive_pricing_for_asin(marketplace_id=marketplace_id, asins = id_list)
                    # parsed[0]["Product"]["CompetitivePricing"]["CompetitivePrices"]["CompetitivePrice"]["Price"]
                    if isinstance(products.parsed,list):
                        
                        for j in range(len(products.parsed)):
                            temp_dict = {}
                            temp_dict["product_pk"] = pk_list[j]
                            temp_dict["competitive_pricing"] = {}
                            temp_dict["status"] = products.parsed[j]["status"]["value"]
                            if temp_dict["status"] == "Success":
                                parsed_products = products.parsed[j]["Product"]
                                try:
                                    if isinstance(parsed_products,list):
                                        temp_dict["competitive_pricing"] = parsed_products[0]["CompetitivePricing"]["CompetitivePrices"]["CompetitivePrice"]["Price"]
                                    else:
                                        temp_dict["competitive_pricing"] = products.parsed[j]["Product"]["CompetitivePricing"]["CompetitivePrices"]["CompetitivePrice"]["Price"]
                                except Exception as e:
                                    temp_dict["status"] = "Competitive Price Not Found"
                            else :
                                temp_dict["status"] = "Competitive Price Not Found"

                            competitive_pricing_list.append(temp_dict)

                    else:
                        temp_dict = {}
                        temp_dict["status"] = products.parsed["status"]["value"]
                        temp_dict["product_pk"] = pk_list[0]
                        temp_dict["competitive_pricing"] = {}
                        if temp_dict["status"] == "Success":
                            try:
                                parsed_products = products.parsed["Product"]
                                if isinstance(parsed_products,list):
                                    temp_dict["competitive_pricing"] = parsed_products[0]["CompetitivePricing"]["CompetitivePrices"]["CompetitivePrice"]["Price"]
                                else:
                                    temp_dict["competitive_pricing"] = products.parsed["Product"]["CompetitivePricing"]["CompetitivePrices"]["CompetitivePrice"]["Price"]
                            except Exception as e:
                                temp_dict["status"] = "Competitive Price Not Found"
                        else :
                            temp_dict["status"] = "Competitive Price Not Found"

                        competitive_pricing_list.append(temp_dict)
                        
                    id_list = []
                    pk_list = []
                    flag = 0
                    cnt+=1

                    if(cnt%2==0):
                        time.sleep(1)

                i+=1

                if len(id_list)==0:
                    flag=0

            pricing_information["competitive_pricing_list"] = competitive_pricing_list
            pricing_information["lowest_priced_offers_list"] = lowest_priced_offers_list
            pricing_information["lowest_offer_listings_list"] = lowest_offer_listings_list
            response["pricing_information"] = pricing_information
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("GetPricingProductsAmazonUKAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class PushProductsAmazonUKAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:

            if custom_permission_mws_functions(request.user,"push_product_on_amazon") == False:
                logger.warning("PushProductsAmazonUKAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("PushProductsAmazonUKAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_pk_list = data["product_pk_list"]

            if(len(product_pk_list)>30):
                logger.warning("PushProductsAmazonUKAPI More then 30 Products!")
                response['status'] = 429
                return Response(data=response)

            permissible_channels = custom_permission_filter_channels(request.user)
            channel_obj = Channel.objects.get(name="Amazon UK")

            if channel_obj not in permissible_channels:
                logger.warning(
                    "PushProductsAmazonUKAPI Restricted Access of UK Channel!")
                response['status'] = 403
                return Response(data=response)

            response["feed_submission_id"] = ""

            is_partial = data.get("is_partial",False)

            xml_string = ""

            if(is_partial == False):
                xml_string= generate_xml_for_post_product_data_amazon_uk(product_pk_list,SELLER_ID)
            else:
                xml_string = generate_xml_for_partial_update_product_amazon_uk(product_pk_list,SELLER_ID)

            feeds_api = APIs.Feeds(MWS_ACCESS_KEY,MWS_SECRET_KEY,SELLER_ID, 
                                        region='UK')

            response_submeet_feed = feeds_api.submit_feed(xml_string,"_POST_PRODUCT_DATA_",marketplaceids=marketplace_id)

            feed_submission_id = response_submeet_feed.parsed["FeedSubmissionInfo"]["FeedSubmissionId"]["value"]

            report_obj = Report.objects.create(feed_submission_id=feed_submission_id,
                                                operation_type="Push",
                                                channel = channel_obj,
                                                user=request.user)

            for product_pk in product_pk_list:
                product = Product.objects.get(pk=int(product_pk))
                report_obj.products.add(product)

            report_obj.save()

            response["feed_submission_id"] = feed_submission_id

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PushProductsAmazonUKAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class PushProductsInventoryAmazonUKAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:

            if custom_permission_mws_functions(request.user,"push_inventory_on_amazon") == False and custom_permission_mws_functions(request.user,"push_price_on_amazon") == False:
                logger.warning("PushProductsInventoryAmazonUKAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("PushProductsInventoryAmazonUKAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_pk_list = data["product_pk_list"]

            if(len(product_pk_list)>30):
                logger.warning("PushProductsInventoryAmazonUKAPI More then 30 Products!")
                response['status'] = 429
                return Response(data=response)

            permissible_channels = custom_permission_filter_channels(request.user)
            channel_obj = Channel.objects.get(name="Amazon UK")

            if channel_obj not in permissible_channels:
                logger.warning(
                    "PushProductsInventoryAmazonUKAPI Restricted Access of UK Channel!")
                response['status'] = 403
                return Response(data=response)

            response["feed_submission_id"] = ""

            xml_string= generate_xml_for_inventory_data_amazon_uk(product_pk_list,SELLER_ID)

            feeds_api = APIs.Feeds(MWS_ACCESS_KEY,MWS_SECRET_KEY,SELLER_ID, 
                                        region='UK')

            response_submeet_feed = feeds_api.submit_feed(xml_string,"_POST_INVENTORY_AVAILABILITY_DATA_",marketplaceids=marketplace_id)

            feed_submission_id = response_submeet_feed.parsed["FeedSubmissionInfo"]["FeedSubmissionId"]["value"]

            report_obj = Report.objects.create(feed_submission_id=feed_submission_id,
                                                operation_type="Inventory",
                                                channel = channel_obj,
                                                user=request.user)

            for product_pk in product_pk_list:
                product = Product.objects.get(pk=int(product_pk))
                report_obj.products.add(product)

            report_obj.save()

            response["feed_submission_id"] = feed_submission_id

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PushProductsInventoryAmazonUKAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class PushProductsPriceAmazonUKAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:

            if custom_permission_mws_functions(request.user,"push_price_on_amazon") == False:
                logger.warning("PushProductsPriceAmazonUKAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("PushProductsPriceAmazonUKAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_pk_list = data["product_pk_list"]

            if(len(product_pk_list)>30):
                logger.warning("PushProductsPriceAmazonUKAPI More then 30 Products!")
                response['status'] = 429
                return Response(data=response)

            permissible_channels = custom_permission_filter_channels(request.user)
            channel_obj = Channel.objects.get(name="Amazon UK")

            if channel_obj not in permissible_channels:
                logger.warning(
                    "PushProductsPriceAmazonUKAPI Restricted Access of UK Channel!")
                response['status'] = 403
                return Response(data=response)

            response["feed_submission_id"] = ""

            xml_string= generate_xml_for_price_data_amazon_uk(product_pk_list,SELLER_ID)

            feeds_api = APIs.Feeds(MWS_ACCESS_KEY,MWS_SECRET_KEY,SELLER_ID, 
                                        region='UK')

            response_submeet_feed = feeds_api.submit_feed(xml_string,"_POST_PRODUCT_PRICING_DATA_",marketplaceids=marketplace_id)

            feed_submission_id = response_submeet_feed.parsed["FeedSubmissionInfo"]["FeedSubmissionId"]["value"]

            report_obj = Report.objects.create(feed_submission_id=feed_submission_id,
                                                operation_type="Price",
                                                channel = channel_obj,
                                                user=request.user)

            for product_pk in product_pk_list:
                product = Product.objects.get(pk=int(product_pk))
                report_obj.products.add(product)

            report_obj.save()

            response["feed_submission_id"] = feed_submission_id

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PushProductsPriceAmazonUKAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class GetProductInventoryAmazonUKAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:

            if custom_permission_mws_functions(request.user,"push_inventory_on_amazon") == False:
                logger.warning("GetProductInventoryAmazonUKAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("GetProductInventoryAmazonUKAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_pk_list = data["product_pk_list"]

            permissible_channels = custom_permission_filter_channels(request.user)
            channel_obj = Channel.objects.get(name="Amazon UK")

            if channel_obj not in permissible_channels:
                logger.warning("GetProductInventoryAmazonUKAPI Restricted Access of UK Channel!")
                response['status'] = 403
                return Response(data=response)

            inventory_list = []

            for product_pk in product_pk_list:

                temp_dict = {}
                temp_dict["product_pk"] = product_pk
                product_obj = Product.objects.get(pk=int(product_pk))
                channel_product = product_obj.channel_product
                amazon_uk_product = json.loads(channel_product.amazon_uk_product_json)
                temp_dict["was_price"] = amazon_uk_product["was_price"]
                temp_dict["now_price"] = amazon_uk_product["now_price"]
                temp_dict["stock"] = amazon_uk_product["stock"]
                temp_dict["status"] = amazon_uk_product["status"]
                inventory_list.append(temp_dict)

            response["inventory_list"] = inventory_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("GetProductInventoryAmazonUKAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchPriceAndStockAmazonUKAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:

            data = request.data

            logger.info("FetchPriceAndStockAmazonUKAPI: %s", str(data))

            reports_api = APIs.Reports(MWS_ACCESS_KEY,MWS_SECRET_KEY,SELLER_ID, region="UK")

            request_report = reports_api.request_report(report_type="_GET_MERCHANT_LISTINGS_ALL_DATA_", marketplace_ids=marketplace_id)

            request_report = request_report.parsed

            request_report_id = request_report["ReportRequestInfo"]["ReportRequestId"]["value"]

            time.sleep(30)

            report_list = reports_api.get_report_list(request_ids=request_report_id)

            report_list = report_list._response_dict

            report_id = report_list["GetReportListResult"]["ReportInfo"]["ReportId"]["value"]

            report = reports_api.get_report(report_id)

            report = report.parsed

            report = report.decode("windows-1252").splitlines()

            organization_obj = CustomPermission.objects.get(user__username=request.user.username).organization

            cnt = 0
            for line in report:

                try:

                    row = re.split('\t',line)

                    if(cnt > 0):
                        price = float(row[4])
                        quantity = int(float(row[5]))
                        status = str(row[-1])
                        ASIN = ""
                        seller_sku = str(row[3])

                        asin_list = [16,17,18,-7]
                        for col in asin_list:
                            if(row[col]!="" and len(row[col])==10):
                                ASIN = str(row[col])
                                break

                        try:
                            product = Product.objects.filter(base_product__seller_sku=seller_sku, base_product__brand__organization=organization_obj)[0]
                            channel_product = product.channel_product   
                            amazon_uk_product_json = json.loads(channel_product.amazon_uk_product_json)
                            amazon_uk_product_json["now_price"] = price
                            amazon_uk_product_json["stock"] = quantity
                            if(status != "Active"):
                                status = "Listed"
                            amazon_uk_product_json["status"] = status
                            amazon_uk_product_json["ASIN"] = ASIN
                            channel_product.amazon_uk_product_json = json.dumps(amazon_uk_product_json)
                            channel_product.save()

                            updated_products += 1

                        except Exception as e:
                            pass

                    cnt += 1

                except Exception as e:
                    pass

            response["total_products"] = cnt-1
            response["updated_products"] = updated_products
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchPriceAndStockAmazonUKAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class PushProductImagesAmazonUKAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:

            data = request.data
            
            logger.info("PushProductImagesAmazonUKAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if custom_permission_mws_functions(request.user,"push_product_on_amazon") == False:
                logger.warning("PushProductImagesAmazonUKAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            permissible_channels = custom_permission_filter_channels(request.user)

            channel_obj = Channel.objects.get(name="Amazon UK")

            if channel_obj not in permissible_channels:
                logger.warning("PushProductImagesAmazonUKAPI Restricted Access of UK Channel!")
                response['status'] = 403
                return Response(data=response)

            product_pk_list = data["product_pk_list"]

            if(len(product_pk_list)>30):
                logger.warning("PushProductImagesAmazonUKAPI More then 30 Products!")
                response['status'] = 429
                return Response(data=response)

            xml_string = generate_xml_for_product_image_amazon_uk(product_pk_list,SELLER_ID)

            feeds_api = APIs.Feeds(MWS_ACCESS_KEY,MWS_SECRET_KEY,SELLER_ID, region='UK')

            response_submeet_feed = feeds_api.submit_feed(xml_string,"_POST_PRODUCT_IMAGE_DATA_",marketplaceids=marketplace_id)

            feed_submission_id = response_submeet_feed.parsed["FeedSubmissionInfo"]["FeedSubmissionId"]["value"]

            report_obj = Report.objects.create(feed_submission_id=feed_submission_id,
                                                operation_type="Push",
                                                channel = channel_obj,
                                                user=request.user)

            for product_pk in product_pk_list:
                product_obj = Product.objects.get(pk=product_pk)
                report_obj.products.add(product_obj)

            report_obj.save()

            response["feed_submission_id"] = feed_submission_id

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PushProductImagesAmazonUKAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

GetMatchingProductsAmazonUK = GetMatchingProductsAmazonUKAPI.as_view()

GetPricingProductsAmazonUK = GetPricingProductsAmazonUKAPI.as_view()

PushProductsAmazonUK = PushProductsAmazonUKAPI.as_view()

PushProductsInventoryAmazonUK = PushProductsInventoryAmazonUKAPI.as_view()

PushProductsPriceAmazonUK = PushProductsPriceAmazonUKAPI.as_view()

GetProductInventoryAmazonUK = GetProductInventoryAmazonUKAPI.as_view()

FetchPriceAndStockAmazonUK = FetchPriceAndStockAmazonUKAPI.as_view()

PushProductImagesAmazonUK = PushProductImagesAmazonUKAPI.as_view()