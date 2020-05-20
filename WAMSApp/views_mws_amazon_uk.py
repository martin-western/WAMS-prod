from WAMSApp.models import *
from WAMSApp.utils import *
from WAMSApp.xml_generators_uk import *

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


from datetime import datetime
from django.utils import timezone
from django.core.files import File

logger = logging.getLogger(__name__)

MWS_PARAMS = settings.MWS_PARAMS

MWS_ACCESS_KEY = MWS_PARAMS["MWS_ACCESS_KEY"] 
MWS_SECRET_KEY = MWS_PARAMS["MWS_SECRET_KEY"]
SELLER_ID = MWS_PARAMS["SELLER_ID"]

class GetMatchingProductsAmazonUKMWSAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if custom_permission_mws_functions(request.user,"push_product_on_amazon") == False:
                logger.warning("GetMatchingProductsAmazonUKMWSAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("GetMatchingProductsAmazonUKMWSAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_pk_list = data["product_pk_list"]

            if(len(product_pk_list)>30):
                logger.warning("GetMatchingProductsAmazonUKMWSAPI More then 30 Products!")
                response['status'] = 429
                return Response(data=response)

            permissible_channels = custom_permission_filter_channels(request.user)
            channel_obj = Channel.objects.get(name="Amazon UK")

            if channel_obj not in permissible_channels:
                logger.warning(
                    "GetMatchingProductsAmazonUKMWSAPI Restricted Access of UK Channel!")
                response['status'] = 403
                return Response(data=response)

            products_api = APIs.Products(MWS_ACCESS_KEY,MWS_SECRET_KEY,SELLER_ID, 
                                        region='UK')

            marketplace_id = mws.Marketplaces["UK"].marketplace_id

            barcodes_list = []
            matched_products_list = []

            for product_pk in product_pk_list:

                product_obj = Product.objects.get(pk=product_pk)
                product_id_type = None
                if(product_obj.product_id_type!=None):
                    product_id_type = product_obj.product_id_type
                barcode_string = product_obj.barcode_string

                if barcode_string!= None and barcode_string!="" and product_id_type!=None:
                    barcodes_list.append((product_id_type.name,barcode_string,product_pk))
                else:
                    temp_dict = {}
                    temp_dict["status"] = "Barcode Not Found"
                    temp_dict["product_pk"] = product_pk
                    temp_dict["matched_ASIN"] = ""
                    temp_dict["matched_product_feed_submission_id"] = ""
                    matched_products_list.append(temp_dict)

            final_barcodes_list = sorted(barcodes_list, key=lambda x: x[0])

            temp = final_barcodes_list[0][0]
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
                                    temp_dict["matched_product_feed_submission_id"] = parsed_products[0]["AttributeSets"]["ItemAttributes"]["feed_submission_id"]["value"]
                                else:
                                    temp_dict["matched_ASIN"] = products.parsed[j]["Products"]["Product"]["Identifiers"]["MarketplaceASIN"]["ASIN"]["value"]
                                    temp_dict["matched_product_feed_submission_id"] = products.parsed[j]["Products"]["Product"]["AttributeSets"]["ItemAttributes"]["feed_submission_id"]["value"]
                                amazon_uk_product["ASIN"] = temp_dict["matched_ASIN"]
                                channel_product.amazon_uk_product_json = json.dumps(amazon_uk_product)
                                channel_product.save()
                            else :
                                temp_dict["status"] = "New Product"

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
                                temp_dict["matched_product_feed_submission_id"] = parsed_products[0]["AttributeSets"]["ItemAttributes"]["feed_submission_id"]["value"]
                            else:
                                temp_dict["matched_ASIN"] = products.parsed["Products"]["Product"]["Identifiers"]["MarketplaceASIN"]["ASIN"]["value"]
                                temp_dict["matched_product_feed_submission_id"] = products.parsed["Products"]["Product"]["AttributeSets"]["ItemAttributes"]["feed_submission_id"]["value"]
                            amazon_uk_product["ASIN"] = temp_dict["matched_ASIN"]
                            channel_product.amazon_uk_product_json = json.dumps(amazon_uk_product)
                            channel_product.save()
                        else :
                            temp_dict["status"] = "New Product"

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
            logger.error("GetMatchingProductsAmazonUKMWSAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class GetPricingProductsAmazonUKMWSAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if custom_permission_mws_functions(request.user,"push_product_on_amazon") == False:
                logger.warning("GetPricingProductsAmazonUKMWSAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("GetPricingProductsAmazonUKMWSAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_pk_list = data["product_pk_list"]

            if(len(product_pk_list)>30):
                logger.warning("GetPricingProductsAmazonUKMWSAPI More then 30 Products!")
                response['status'] = 429
                return Response(data=response)

            permissible_channels = custom_permission_filter_channels(request.user)
            channel_obj = Channel.objects.get(name="Amazon UK")

            if channel_obj not in permissible_channels:
                logger.warning(
                    "GetPricingProductsAmazonUKMWSAPI Restricted Access of UK Channel!")
                response['status'] = 403
                return Response(data=response)

            products_api = APIs.Products(MWS_ACCESS_KEY,MWS_SECRET_KEY,SELLER_ID, 
                                        region='UK')

            marketplace_id = mws.Marketplaces["UK"].marketplace_id

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
            logger.error("GetPricingProductsAmazonUKMWSAPI: %s at %s",
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

            xml_string = generate_xml_for_post_product_data_amazon_uk(product_pk_list,SELLER_ID)

            feeds_api = APIs.Feeds(MWS_ACCESS_KEY,MWS_SECRET_KEY,SELLER_ID, 
                                        region='UK')

            marketplace_id = mws.Marketplaces["UK"].marketplace_id

            response_submeet_feed = feeds_api.submit_feed(xml_string,"_POST_PRODUCT_DATA_",marketplaceids=marketplace_id)

            feed_submission_id = response_submeet_feed.parsed["FeedSubmissionInfo"]["FeedSubmissionId"]["value"]

            response["feed_submission_id"] = feed_submission_id

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PushProductsAmazonUKAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class GetPushProductsResultAmazonUKAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:

            if custom_permission_mws_functions(request.user,"push_product_on_amazon") == False:
                logger.warning("GetPushProductsResultAmazonUKAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("GetPushProductsResultAmazonUKAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            feed_submission_id = data["feed_submission_id"]

            permissible_channels = custom_permission_filter_channels(request.user)
            channel_obj = Channel.objects.get(name="Amazon UK")

            if channel_obj not in permissible_channels:
                logger.warning(
                    "PushProductsAmazonUKAPI Restricted Access of UK Channel!")
                response['status'] = 403
                return Response(data=response)

            feeds_api = APIs.Feeds(MWS_ACCESS_KEY,MWS_SECRET_KEY,SELLER_ID, 
                                        region='UK')

            response["errors"] = []

            try :
                response_feed_submission_result = feeds_api.get_feed_submission_result(feed_submission_id)

                feed_submission_result = response_feed_submission_result.parsed

                result = feed_submission_result["ProcessingReport"]["Result"]

                if isinstance(result,list):

                    for i in range(len(result)):
                        temp_dict = {}
                        temp_dict["product_pk"] = result[i]["MessageID"]["value"]
                        temp_dict["error_type"] = result[i]["ResultCode"]["value"]
                        temp_dict["error_code"] = result[i]["ResultMessageCode"]["value"]
                        temp_dict["error_message"] = result[i]["ResultDescription"]["value"]
                        response["errors"].append(temp_dict)

                else:
                    temp_dict = {}
                    temp_dict["product_pk"] = result["MessageID"]["value"]
                    temp_dict["error_type"] = result["ResultCode"]["value"]
                    temp_dict["error_code"] = result["ResultMessageCode"]["value"]
                    temp_dict["error_message"] = result["ResultDescription"]["value"]
                    response["errors"].append(temp_dict)


            except Exception as e:

                response["status"] = "In Progress"

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PushProductsAmazonUKAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

GetMatchingProductsAmazonUKMWS = GetMatchingProductsAmazonUKMWSAPI.as_view()

GetPricingProductsAmazonUKMWS = GetPricingProductsAmazonUKMWSAPI.as_view()

PushProductsAmazonUK = PushProductsAmazonUKAPI.as_view()

GetPushProductsResultAmazonUK = GetPushProductsResultAmazonUKAPI.as_view()

