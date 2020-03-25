# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render

# Create your views here.


from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

from WAMSApp.models import *
from WAMSApp.utils import *
from dealshub.models import *

from django.shortcuts import render, HttpResponse, get_object_or_404
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import AllowAny


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
import uuid

try:
    import urllib.request as urllib2
except ImportError:
    import urllib2
import pandas as pd
import xml.dom.minidom


logger = logging.getLogger(__name__)


class CsrfExemptSessionAuthentication(SessionAuthentication):

    def enforce_csrf(self, request):
        return


class FetchProductDetailsAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,) 
    permission_classes = [AllowAny]

    def fetch_price(self,product_id):
        try:
            url="http://94.56.89.114:8001/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"
            headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
            credentials = ("MOBSERVICE", "~lDT8+QklV=(")
            company_code = "1070" # GEEPAS
            body = """<soapenv:Envelope xmlns:urn="urn:sap-com:document:sap:rfc:functions" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
            <soapenv:Header />
            <soapenv:Body>
            <urn:ZAPP_STOCK_PRICE>
             <IM_MATNR>
              <item>
               <MATNR>""" + product_id + """</MATNR>
              </item>
             </IM_MATNR>
             <IM_VKORG>
              <item>
               <VKORG>""" + company_code + """</VKORG>
              </item>
             </IM_VKORG>
             <T_DATA>
              <item>
               <MATNR></MATNR>
               <MAKTX></MAKTX>
               <LGORT></LGORT>
               <CHARG></CHARG>
               <SPART></SPART>
               <MEINS></MEINS>
               <ATP_QTY></ATP_QTY>
               <TOT_QTY></TOT_QTY>
               <CURRENCY></CURRENCY>
               <IC_EA></IC_EA>
               <OD_EA></OD_EA>
               <EX_EA></EX_EA>
               <RET_EA></RET_EA>
               <WERKS></WERKS>
              </item>
             </T_DATA>
            </urn:ZAPP_STOCK_PRICE>
            </soapenv:Body>
            </soapenv:Envelope>"""
            response2 = requests.post(url, auth=credentials, data=body, headers=headers)
            content = response2.content
            content = xmltodict.parse(content)
            content = json.loads(json.dumps(content))
            items = content["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_STOCK_PRICEResponse"]["T_DATA"]["item"]
            price = 0
            temp_price = 0
            for item in items:
                temp_price = item["EX_EA"]
                if temp_price!=None:
                    temp_price = float(temp_price)
                    price = max(temp_price, price)
            return float(price)
        except Exception as e:
            return 0


    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchProductDetailsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            

            temp_product_obj = DealsHubProduct.objects.get(
                product__uuid=data["uuid"])
            product_obj = temp_product_obj.product
            base_product_obj = product_obj.base_product

            response["category"] = "" if temp_product_obj.product.base_product.category==None else str(temp_product_obj.product.base_product.category)
            response["subCategory"] = "" if temp_product_obj.product.base_product.sub_category==None else str(temp_product_obj.product.base_product.sub_category)
            response["id"] = temp_product_obj.product.uuid
            response["uuid"] = data["uuid"]
            response["name"] = product_obj.product_name

            if(product_obj.base_product.brand.name=="Geepas"):
                response["price"] = self.fetch_price(product_obj.base_product.seller_sku)
            else:
                response["price"] = product_obj.standard_price
            
            response["currency"] = "AED"
            response["minLimit"] = "1"
            response["maxLimit"] = "5"
            response["productImagesUrl"] = []
            product_description = [
                "Brand new and high quality",
                "Made of supreme quality, durable EVA crush resistant, anti-shock material.",
                "Soft inner cloth lining, one mesh pocket inside.",
                "Compact and functional hard case keeps items safe and extremely portable.",
                "Force Touch trackpad (13-inch model)"
            ]

            try:
                product_description = json.loads(product_obj.channel_product.amazon_uk_product_json)["product_description"]
            except Exception as e:
                pass

            try:
                response["noonHttpLink"] = json.loads(product_obj.channel_product.noon_product_json)["http_link"]
                response["amazonUKHttpLink"] = json.loads(product_obj.channel_product.amazon_uk_product_json)["http_link"]
                response["amazonUAEHttpLink"] = json.loads(product_obj.channel_product.amazon_uae_product_json)["http_link"]
                response["ebayHttpLink"] = json.loads(product_obj.channel_product.ebay_product_json)["http_link"]
            except Exception as e:
                response["noonHttpLink"] = ""
                response["amazonUKHttpLink"] = ""
                response["amazonUAEHttpLink"] = ""
                response["ebayHttpLink"] = ""
            
            response["productDispDetails"] = product_description
            
            response["productImagesUrl"] = []
            images = {}

            main_images_list = ImageBucket.objects.none()
            main_images_objs = MainImages.objects.filter(product=product_obj)
            for main_images_obj in main_images_objs:
                main_images_list |= main_images_obj.main_images.all()
            main_images_list = main_images_list.distinct()
            images["main_images"] = create_response_images_main(main_images_list)
            try:
                response["heroImageUrl"] = main_images_list.all()[0].image.mid_image.url
            except Exception as e:
                response["heroImageUrl"] = Config.objects.all()[0].product_404_image.image.url

            response["sub_category"] = "" if base_product_obj.sub_category==None else str(base_product_obj.sub_category)
            response["seller_sku"] = base_product_obj.seller_sku
            response["manufacturer_part_number"] = base_product_obj.manufacturer_part_number
            response["manufacturer"] = base_product_obj.manufacturer
            response["dimensions"] = json.loads(base_product_obj.dimensions)

            response["product_name"] = product_obj.product_name
            response["product_name_sap"] = product_obj.product_name_sap
            response["product_id"] = product_obj.product_id
            response["barcode_string"] = product_obj.barcode_string
            response["standard_price"] = "" if product_obj.standard_price == None else product_obj.standard_price
            response["quantity"] = "" if product_obj.quantity == None else product_obj.quantity
            response["factory_notes"] = product_obj.factory_notes
            response["verified"] = product_obj.verified
            response["color_map"] = product_obj.color_map
            response["color"] = product_obj.color
            try:
                response["features"] = json.loads(product_obj.pfl_product_features)
            except Exception as e:
                response["features"] = []

            if product_obj.product_id_type != None:
                response["product_id_type"] = product_obj.product_id_type.name
            else:
                response["product_id_type"] = ""

            if product_obj.material_type != None:
                response["material_type"] = product_obj.material_type.name
            else:
                response["material_type"] = ""

            images = {}

            main_images_list = ImageBucket.objects.none()
            main_images_obj = MainImages.objects.get(
                product=product_obj, is_sourced=True)
            try:
                main_images_obj = MainImages.objects.get(
                    product=product_obj, is_sourced=True)
                
                main_images_list |= main_images_obj.main_images.all()
            except Exception as e:
                pass
            main_images_list = main_images_list.distinct()
            images["main_images"] = create_response_images_main(
                main_images_list)

            sub_images_list = ImageBucket.objects.none()
            try:
                sub_images_obj = SubImages.objects.get(
                    product=product_obj, is_sourced=True)
                sub_images_list |= sub_images_obj.sub_images.all()
            except Exception as e:
                pass
            sub_images_list = sub_images_list.distinct()
            images["sub_images"] = create_response_images_sub(sub_images_list)
            
            response["productImagesUrl"].append({"original":response["heroImageUrl"], "thumbnail":response["heroImageUrl"]})
            for temp_image in images["sub_images"]:
                temp_images = {}
                temp_images["original"] = temp_image["main_url"]
                temp_images["thumbnail"] = temp_image["thumbnail_url"]
                response["productImagesUrl"].append(temp_images)
            
            
            response["productProperties"] = json.loads(
                temp_product_obj.properties)

            repr_image_url = Config.objects.all(
            )[0].product_404_image.image.url
            repr_high_def_url = repr_image_url

            main_images_obj = None
            try:
                main_images_obj = MainImages.objects.get(product=product_obj, channel=None)
            except Exception as e:
                pass

            if main_images_obj != None and main_images_obj.main_images.filter(is_main_image=True).count() > 0:
                try:
                    repr_image_url = main_images_obj.main_images.filter(
                        is_main_image=True)[0].image.mid_image.url
                except Exception as e:
                    repr_image_url = main_images_obj.main_images.filter(is_main_image=True)[
                        0].image.image.url

                repr_high_def_url = main_images_obj.main_images.filter(is_main_image=True)[
                    0].image.image.url

            response["repr_image_url"] = repr_image_url
            response["repr_high_def_url"] = repr_high_def_url

            try:
                response["barcode_image_url"] = product_obj.barcode.image.url
            except Exception as e:
                response["barcode_image_url"] = ""

            response["images"] = images

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductDetailsAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)


FetchProductDetails = FetchProductDetailsAPI.as_view()


class FetchSectionsProductsAPI(APIView):
    
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchSectionsProductsAPI: %s", str(data))

            organization_name = data["organizationName"]
            organization_obj = Organization.objects.get(name=organization_name)

            section_objs = Section.objects.filter(organization=organization_obj, is_published=True)

            section_list =  []

            for section_obj in section_objs:
                product_objs = section_obj.products.all()
                temp_dict = {}
                temp_dict["sectionName"] = section_obj.name
                temp_dict["uid"] = section_obj.uuid
                temp_dict["productsArray"] = []
                for product_obj in product_objs:
                    temp_dict2 = {}
                    temp_dict2["productName"] = product_obj.product_name
                    temp_dict2["productCategory"] = "" if product_obj.base_product.category==None else str(product_obj.base_product.category)
                    temp_dict2["productSubCategory"] = "" if product_obj.base_product.sub_category==None else str(product_obj.base_product.sub_category)
                    temp_dict2["brand"] = str(product_obj.base_product.brand)
                    
                    if(product.base_product.brand.name=="Geepas"):
                        temp_dict2["price"] = "0"
                    else:
                        temp_dict2["price"] = product.standard_price

                    temp_dict2["prevPrice"] = temp_dict2["price"]
                    temp_dict2["currency"] = "AED"
                    #temp_dict2["discount"] = "10"
                    temp_dict2["rating"] = "0"
                    temp_dict2["totalRatings"] = "0"
                    temp_dict2["id"] = str(product_obj.uuid)
                    main_images_list = ImageBucket.objects.none()
                    main_images_objs = MainImages.objects.filter(product=product_obj)
                    for main_images_obj in main_images_objs:
                        main_images_list |= main_images_obj.main_images.all()
                    main_images_list = main_images_list.distinct()
                    try:
                        temp_dict2["heroImage"] = main_images_list.all()[0].image.mid_image.url
                    except Exception as e:
                        temp_dict2["heroImage"] = Config.objects.all()[0].product_404_image.image.url

                    temp_dict["productsArray"].append(temp_dict2)
                section_list.append(temp_dict)

            response['section_list'] = section_list
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSectionsProductsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)

FetchSectionsProducts = FetchSectionsProductsAPI.as_view()


class FetchSectionsProductsLimitAPI(APIView):
    
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchSectionsProductsLimitAPI: %s", str(data))

            organization_name = data["organizationName"]
            organization_obj = Organization.objects.get(name=organization_name)

            section_objs = Section.objects.filter(organization=organization_obj, is_published=True)

            section_list =  []

            for section_obj in section_objs:
                product_objs = section_obj.products.all()
                temp_dict = {}
                temp_dict["sectionName"] = section_obj.name
                temp_dict["uid"] = section_obj.uuid
                temp_dict["productsArray"] = []
                for product_obj in product_objs[:12]:
                    temp_dict2 = {}
                    temp_dict2["productName"] = product_obj.product_name
                    temp_dict2["productCategory"] = "" if product_obj.base_product.category==None else str(product_obj.base_product.category)
                    temp_dict2["productSubCategory"] = "" if product_obj.base_product.sub_category==None else str(product_obj.base_product.sub_category)
                    temp_dict2["brand"] = str(product_obj.base_product.brand)

                    if(product_obj.base_product.brand.name=="Geepas"):
                        temp_dict2["price"] = "0"
                    else:
                        temp_dict2["price"] = product_obj.standard_price
                    temp_dict2["prevPrice"] = temp_dict2["price"]
                    temp_dict2["currency"] = "AED"
                    temp_dict2["discount"] = "10"
                    temp_dict2["rating"] = "4.5"
                    temp_dict2["totalRatings"] = "5,372"
                    temp_dict2["id"] = str(product_obj.uuid)
                    main_images_list = ImageBucket.objects.none()
                    main_images_objs = MainImages.objects.filter(product=product_obj)
                    for main_images_obj in main_images_objs:
                        main_images_list |= main_images_obj.main_images.all()
                    main_images_list = main_images_list.distinct()
                    if main_images_list.filter(is_main_image=True).count() > 0:
                        try:
                            temp_dict2["heroImage"] = main_images_list.filter(is_main_image=True)[
                                0].image.mid_image.url
                        except Exception as e:
                            temp_dict2["heroImage"] = Config.objects.all()[
                                0].product_404_image.image.url
                    else:
                        temp_dict2["heroImage"] = Config.objects.all()[
                            0].product_404_image.image.url


                    temp_dict["productsArray"].append(temp_dict2)
                section_list.append(temp_dict)

            response['section_list'] = section_list
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSectionsProductsLimitAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)

FetchSectionsProductsLimit = FetchSectionsProductsLimitAPI.as_view()


class FetchSectionProductsAPI(APIView):
    
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchSectionProductsAPI: %s", str(data))

            uuid = data["sectionUuid"]
            section_obj = Section.objects.get(uuid=uuid)
            product_objs = section_obj.products.all()
            temp_dict = {}
            temp_dict["sectionName"] = section_obj.name
            temp_dict["productsArray"] = []
            for product_obj in product_objs:
                temp_dict2 = {}
                temp_dict2["name"] = product_obj.product_name
                temp_dict2["brand"] = str(product_obj.base_product.brand)
                temp_dict2["price"] = "0"
                temp_dict2["prevPrice"] = temp_dict2["price"]
                temp_dict2["currency"] = "AED"
                #temp_dict2["discount"] = "10%"
                temp_dict2["rating"] = "0"
                temp_dict2["totalRatings"] = "0"
                temp_dict2["uuid"] = str(product_obj.uuid)
                temp_dict2["id"] = str(product_obj.uuid)
                main_images_list = ImageBucket.objects.none()
                main_images_objs = MainImages.objects.filter(product=product_obj)
                for main_images_obj in main_images_objs:
                    main_images_list |= main_images_obj.main_images.all()
                main_images_list = main_images_list.distinct()
                
                try:
                    temp_dict2["heroImageUrl"] = main_images_list.all()[
                        0].image.mid_image.url
                except Exception as e:
                    temp_dict2["heroImageUrl"] = Config.objects.all()[
                        0].product_404_image.image.url


                temp_dict["productsArray"].append(temp_dict2)

            response['sectionData'] = temp_dict
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSectionProductsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)

FetchSectionProducts = FetchSectionProductsAPI.as_view()


class FetchCategoriesAPI(APIView):
    
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchCategoriesAPI: %s", str(data))
            organization_name = data["organizationName"]

            category_objs = Category.objects.filter(organization__name=organization_name)

            category_list = []
            for category_obj in category_objs:
                temp_dict = {}
                temp_dict["name"] = category_obj.name
                temp_dict["uuid"] = category_obj.uuid
                category_list.append(temp_dict)

            response['categoryList'] = category_list

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCategoriesAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


FetchCategories = FetchCategoriesAPI.as_view()


class FetchBatchDiscountDealsAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchBatchDiscountDealsAPI: %s", str(data))

            batch_discount_deals = {
                "id": "8564",
                "counter": {
                    "timeToEnd": "Wed Jan 16 2020 20:47:52 GMT+0530",
                    "originalPrice": "99"
                },
                "products": [
                    {
                        "productName": "Geepas GAC9602 Air Cooler 70L",
                        "productCategory": "Electronics",
                        "productSubCategory": "Cooler",
                        "brand": "Geepas",
                        "price": "2,239",
                        "prevPrice": "3,300",
                        "currency": "AED",
                        "discount": "15",
                        "rating": "4.5",
                        "totalRatings": "5,372",
                        "heroImage": "https://wig-wams-s3-bucket.s3.amazonaws.com/midsize/1569674764GEEPAS_MODEL_GAC9602_STRAIGHT.jpg",
                        "id": Product.objects.get(base_product__seller_sku="GAC9602").uuid
                    },
                    {
                        "name": "Geepas Citrus Juicer/1.0L Plstc cup",
                        "category": "Juicer",
                        "subCategory": "Juicer",
                        "brand": "Geepas",
                        "price": "26",
                        "prevPrice": "30",
                        "currency": "AED",
                        "discount": "4",
                        "rating": "3.9",
                        "totalRatings": "1,772",
                        "thumbnailImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/midsize/289A2524_AVCns5Q.jpg",
                        "uuid": Product.objects.get(base_product__seller_sku="GCJ9900").uuid
                    },
                    {
                        "productName": "Geepas GA1960 4 USB Travel Charger ",
                        "productCategory": "Electronics",
                        "productSubCategory": "Plugs",
                        "brand": "Geepas",
                        "price": "3,999",
                        "prevPrice": "4,700",
                        "currency": "AED",
                        "discount": "28",
                        "rating": "4.5",
                        "totalRatings": "5,372",
                        "heroImage": "https://wig-wams-s3-bucket.s3.amazonaws.com/midsize/1569505000GA1960-2.jpg",
                        "id": Product.objects.get(base_product__seller_sku="GA1960").uuid
                    },
                    {
                        "productName": "Geepas GACW1818HCS 1.5 Ton Window Air Conditioner",
                        "productCategory": "Electronics",
                        "productSubCategory": "Cooler",
                        "brand": "Geepas",
                        "price": "1,200",
                        "prevPrice": "1,800",
                        "currency": "AED",
                        "discount": "10",
                        "rating": "4.5",
                        "totalRatings": "5,372",
                        "heroImage": "https://wig-wams-s3-bucket.s3.amazonaws.com/midsize/1569677989GACW1818HCS-.jpg",
                        "id": Product.objects.get(base_product__seller_sku="GACW1818HCS").uuid
                    },
                    {
                        "productName": "Geepas GAC9580 High Speed Rechargeable Air Cooler",
                        "productCategory": "Electronics",
                        "productSubCategory": "Cooler",
                        "brand": "Geepas",
                        "price": "3,999",
                        "prevPrice": "5,600",
                        "currency": "AED",
                        "discount": "28",
                        "rating": "4.5",
                        "totalRatings": "5,372",
                        "heroImage": "https://wig-wams-s3-bucket.s3.amazonaws.com/midsize/1569674206GAC9580-1.jpg",
                        "id": Product.objects.get(base_product__seller_sku="GAC9580").uuid
                    }
                ]
            }
            response['batch_discount_deals'] = batch_discount_deals

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchBatchDiscountDealsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


FetchBatchDiscountDeals = FetchBatchDiscountDealsAPI.as_view()


class FetchFeaturedProductsAPI(APIView):
    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchFeaturedProductsAPI: %s", str(data))
            
            organization_name = data["organizationName"]

            featured_products = []
            if organization_name.lower()=="geepas":
                featured_products = [
                    {
                        "name": "Geepas GAC9602 Air Cooler 70L",
                        "category": "Electronics",
                        "subCategory": "Cooler",
                        "brand": "Geepas",
                        "price": "500",
                        "prevPrice": "3,300",
                        "currency": "AED",
                        "discount": "15",
                        "rating": "4.5",
                        "totalRatings": "5,372",
                        "thumbnailImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/1569674764GEEPAS%20MODEL%20GAC9602%20STRAIGHT.jpg",
                        "uuid": Product.objects.get(base_product__seller_sku="GAC9602").uuid
                    },
                    {
                        "name": "Geepas Citrus Juicer/1.0L Plstc cup",
                        "category": "Juicer",
                        "subCategory": "Juicer",
                        "brand": "Geepas",
                        "price": "26",
                        "prevPrice": "30",
                        "currency": "AED",
                        "discount": "4",
                        "rating": "3.9",
                        "totalRatings": "1,772",
                        "thumbnailImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/midsize/289A2524_AVCns5Q.jpg",
                        "uuid": Product.objects.get(base_product__seller_sku="GCJ9900").uuid
                    },
                    {
                        "name": "Geepas GA1960 4 USB Travel Charger ",
                        "category": "Electronics",
                        "subCategory": "Plugs",
                        "brand": "Geepas",
                        "price": "18",
                        "prevPrice": "4,700",
                        "currency": "AED",
                        "discount": "28",
                        "rating": "4.5",
                        "totalRatings": "5,372",
                        "thumbnailImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/1569505000GA1960-2.jpg",
                        "uuid": Product.objects.get(base_product__seller_sku="GA1960").uuid
                    },
                    {
                        "name": "Geepas GACW1818HCS 1.5 Ton Window Air Conditioner",
                        "category": "Electronics",
                        "subCategory": "Cooler",
                        "brand": "Geepas",
                        "price": "760",
                        "prevPrice": "1,800",
                        "currency": "AED",
                        "discount": "10",
                        "rating": "4.5",
                        "totalRatings": "5,372",
                        "thumbnailImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/1569677989GACW1818HCS-.jpg",
                        "uuid": Product.objects.get(base_product__seller_sku="GACW1818HCS").uuid
                    },
                    {
                        "name": "Geepas GAC9580 High Speed Rechargeable Air Cooler",
                        "category": "Electronics",
                        "subCategory": "Cooler",
                        "brand": "Geepas",
                        "price": "27",
                        "prevPrice": "5,600",
                        "currency": "AED",
                        "discount": "28",
                        "rating": "4.5",
                        "totalRatings": "5,372",
                        "thumbnailImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/1569674216GAC9580%20(2).jpg",
                        "uuid": Product.objects.get(base_product__seller_sku="GAC9580").uuid
                    }
                ]
            elif organization_name.lower()=="pex":
                featured_products = [
                    {
                        "name": "Pex antiseptic disinfectant 500 ml",
                        "category": "Cleaning Products",
                        "subCategory": "Cleaning Products",
                        "brand": "Pex",
                        "price": "12",
                        "prevPrice": "20",
                        "currency": "AED",
                        "discount": "15",
                        "rating": "4.5",
                        "totalRatings": "5,372",
                        "thumbnailImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/thumbnails/AD150_1_FlM0XTE.jpg",
                        "uuid": "379e83c4-7f21-4291-8329-3d7ede846d69"
                    },
                    {
                        "name": "Pex Active Air Freshener Lavender 550 ml",
                        "category": "Cleaning Products",
                        "subCategory": "Cleaning Products",
                        "brand": "Pex",
                        "price": "30",
                        "prevPrice": "20",
                        "currency": "AED",
                        "discount": "15",
                        "rating": "4.5",
                        "totalRatings": "5,372",
                        "thumbnailImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/thumbnails/AL555_1_ph0QKB8.jpg",
                        "uuid": "8dc7b633-dfcf-4d3b-a39d-770edc545b03"
                    },
                    {
                        "name": "Pex antiseptic disinfectant 5 ltr",
                        "category": "Cleaning Products",
                        "subCategory": "Cleaning Products",
                        "brand": "Pex",
                        "price": "43",
                        "prevPrice": "20",
                        "currency": "AED",
                        "discount": "15",
                        "rating": "4.5",
                        "totalRatings": "5,372",
                        "thumbnailImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/thumbnails/AD2500_1_hxCL5xe.jpg",
                        "uuid": "cf2b5ddc-5737-4fa5-a777-059699a3d480"
                    }
                ]
            elif organization_name.lower()=="aqua":
                featured_products = [
                    {
                        "name": "Aqua Dish Wash liquid Lemon 1Ltr",
                        "category": "Cleaning Products",
                        "subCategory": "Cleaning Products",
                        "brand": "Aqua",
                        "price": "5",
                        "prevPrice": "20",
                        "currency": "AED",
                        "discount": "15",
                        "rating": "4.5",
                        "totalRatings": "5,372",
                        "thumbnailImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/thumbnails/6297000881003_1.jpg",
                        "uuid": "f4c15dce-23a1-456c-a5ab-3592b14c67a1"
                    },
                    {
                        "name": "Aqua Hand Wash Liquid Rose 5 Ltr",
                        "category": "Cleaning Products",
                        "subCategory": "Cleaning Products",
                        "brand": "Aqua",
                        "price": "10",
                        "prevPrice": "20",
                        "currency": "AED",
                        "discount": "15",
                        "rating": "4.5",
                        "totalRatings": "5,372",
                        "thumbnailImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/thumbnails/6297000881034_1.jpg",
                        "uuid": "52c47297-dcd8-4809-89af-051c7ac3b244"
                    },
                    {
                        "name": "Aqua Glass Cleaner Liquid 650 Ml",
                        "category": "Cleaning Products",
                        "subCategory": "Cleaning Products",
                        "brand": "Aqua",
                        "price": "5",
                        "prevPrice": "20",
                        "currency": "AED",
                        "discount": "15",
                        "rating": "4.5",
                        "totalRatings": "5,372",
                        "thumbnailImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/thumbnails/6297000881171_1.jpg",
                        "uuid": "d696bd92-7fd9-4d76-b53c-93ce5e69a991"
                    },
                    {
                        "name": "Aqua Antiseptic Disinfectant Liquid 5 ltr",
                        "category": "Cleaning Products",
                        "subCategory": "Cleaning Products",
                        "brand": "Aqua",
                        "price": "6",
                        "prevPrice": "20",
                        "currency": "AED",
                        "discount": "15",
                        "rating": "4.5",
                        "totalRatings": "5,372",
                        "thumbnailImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/thumbnails/6297000881218_1.jpg",
                        "uuid": "55d7b55c-0060-4e94-90d0-021a74b6fd0d"
                    }
                ]
            elif organization_name.lower()=="future-lux":
                featured_products = [
                    {
                        "name": "24 Watt LED Panel Light Square Warm White Colour with Inbuilt Driver",
                        "category": "Lights and Fixtures",
                        "subCategory": "Lights and Fixtures",
                        "brand": "Future Lux",
                        "price": "32.5",
                        "prevPrice": "20",
                        "currency": "AED",
                        "discount": "15",
                        "rating": "4.5",
                        "totalRatings": "5,372",
                        "thumbnailImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/FDWWPANELSQR_1.jpg",
                        "uuid": "11fc3bc2-5ba1-44ac-ab42-c99330ae2cdc"
                    },
                    {
                        "name": "Wooden Type Wall Light Fitting Cylindrical Shape",
                        "category": "Lights and Fixtures",
                        "subCategory": "Lights and Fixtures",
                        "brand": "Future Lux",
                        "price": "84.5",
                        "prevPrice": "20",
                        "currency": "AED",
                        "discount": "15",
                        "rating": "4.5",
                        "totalRatings": "5,372",
                        "thumbnailImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/FD3009_1.jpg",
                        "uuid": "2648adbc-e4ff-4693-8c01-a0f93b6f3c11"
                    },
                    {
                        "name": "Brass Chandelier Bell Type Modern Design E14 Lamp",
                        "category": "Lights and Fixtures",
                        "subCategory": "Lights and Fixtures",
                        "brand": "Future Lux",
                        "price": "1430",
                        "prevPrice": "20",
                        "currency": "AED",
                        "discount": "15",
                        "rating": "4.5",
                        "totalRatings": "5,372",
                        "thumbnailImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/FD1515_1.jpg",
                        "uuid": "f73325fd-bc46-4be5-8c96-705e80b6be94"
                    },
                    {
                        "name": "Hanging Type Decorative Interior Light",
                        "category": "Lights and Fixtures",
                        "subCategory": "Lights and Fixtures",
                        "brand": "Future Lux",
                        "price": "780",
                        "prevPrice": "20",
                        "currency": "AED",
                        "discount": "15",
                        "rating": "4.5",
                        "totalRatings": "5,372",
                        "thumbnailImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/FDHL2451_1.jpg",
                        "uuid": "e9001f29-3313-4056-9dec-b1b4cef64d17"
                    }
                ]
            
            response['featured_products'] = featured_products

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFeaturedProductsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


FetchFeaturedProducts = FetchFeaturedProductsAPI.as_view()


class SearchAPI(APIView):
    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SearchAPI: %s", str(data))
            query_string_name = data.get("name", "")
            query_string_category = data.get("category", "")
            query_string_organization = data.get("organizationName", "geepas")
            filter_list = data.get("filters", "[]")
            filter_list = json.loads(filter_list)

            page = data.get("page", 1)
            search = {}
            

            available_dealshub_products = DealsHubProduct.objects.filter(product__base_product__brand__organization__name=query_string_organization, is_published=True)
            if query_string_category!="ALL":
                query_string_category = query_string_category.replace("-", " ")
                available_dealshub_products = available_dealshub_products.filter(product__base_product__category__name=query_string_category)
            
            if query_string_name!="":
                available_dealshub_products = available_dealshub_products.filter(product__product_name__icontains=query_string_name)

            filtered_products = DealsHubProduct.objects.none()
            try:
                if len(filter_list)>0:
                    for filter_metric in filter_list:
                        for filter_value in filter_metric["values"]:
                            filtered_products |= available_dealshub_products.objects.filter(product__dynamic_form_attributes__icontains="'value': '"+filter_value+"'")
                    filtered_products = filtered_products.distinct()
                else:
                    filtered_products = available_dealshub_products
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SearchAPI: %s at %s", e, str(exc_tb.tb_lineno))


            paginator = Paginator(filtered_products, 20)
            dealshub_products_list = paginator.page(page)            
            products = []
            for dealshub_product in dealshub_products_list:
                try:
                    product = dealshub_product.product
                    temp_dict = {}
                    temp_dict["name"] = product.product_name
                    temp_dict["brand"] = str(product.base_product.brand)
                    if(product.base_product.brand.name=="Geepas"):
                        temp_dict["price"] = "0"
                    else:
                        temp_dict["price"] = product.standard_price

                    temp_dict["currency"] = "AED"
                    #temp_dict["discount"] = "0"
                    temp_dict["rating"] = "0"
                    temp_dict["totalRatings"] = "0"
                    temp_dict["uuid"] = product.uuid
                    temp_dict["id"] = product.uuid
                    
                    main_images_list = ImageBucket.objects.none()
                    main_images_objs = MainImages.objects.filter(product=product)
                    for main_images_obj in main_images_objs:
                        main_images_list |= main_images_obj.main_images.all()
                    main_images_list = main_images_list.distinct()

                    try:
                        temp_dict["heroImageUrl"] = main_images_list.all()[0].image.mid_image.url
                    except Exception as e:
                        temp_dict["heroImageUrl"] = Config.objects.all()[0].product_404_image.image.url
                    
                    products.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("SearchAPI: %s at %s", e, str(exc_tb.tb_lineno))

            filters = []
            try:
                if query_string_category!="ALL":
                    category_obj = Category.objects.get(name = query_string_category)
                    property_data = json.loads(category_obj.property_data)
                    for p_data in property_data:
                        temp_dict = {}
                        temp_dict["key"] = p_data["key"]
                        temp_dict["values"] = p_data["values"]
                        filters.append(temp_dict)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SearchAPI filter creation: %s at %s", e, str(exc_tb.tb_lineno))

            is_available = True
            
            if int(paginator.num_pages) == int(page):
                is_available = False

            response["is_available"] = is_available
            response["total_products"] = len(products_by_name)

            search['filters'] = filters
            search['category'] = query_string_category
            search['products'] = products
            response['search'] = search
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


Search = SearchAPI.as_view()


class CreateAdminCategoryAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("CreateAdminCategoryAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            organization_name = data["organizationName"]
            organization_obj = Organization.objects.get(name=organization_name)

            data = data["sectionData"]

            name = data["name"]
            listing_type = data["listingType"]
            products = data["products"]
            
            order_index = Banner.objects.filter(organization=organization_obj).count()+Section.objects.filter(organization=organization_obj).count()+1

            section_obj = Section.objects.create(organization=organization_obj, uuid=str(uuid.uuid4()), name=name, listing_type=listing_type, order_index=order_index)
            for product in products:
                product_obj = Product.objects.get(uuid=product)
                section_obj.products.add(product_obj)

            section_obj.save()

            response['uuid'] = str(section_obj.uuid)
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateAdminCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchAdminCategoriesAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchAdminCategoriesAPI: %s", str(data))

            organization_name = data["organizationName"]
            organization_obj = Organization.objects.get(name=organization_name)

            section_objs = Section.objects.filter(organization=organization_obj)

            section_list = []
            
            for section_obj in section_objs:
                temp_dict = {}
                temp_dict["uuid"] = str(section_obj.uuid)
                temp_dict["name"] = str(section_obj.name)
                temp_dict["listingType"] = str(section_obj.listing_type)
                temp_dict["createdBy"] = str(section_obj.created_by)
                temp_dict["modifiedBy"] = str(section_obj.modified_by)
                temp_dict["createdOn"] = str(section_obj.created_date)
                temp_dict["modifiedOn"] = str(section_obj.modified_date)
                temp_dict["type"] = "ProductListing"
                temp_products = []
                for prod in section_obj.products.all():
                    temp_dict2 = {}

                    main_images_list = ImageBucket.objects.none()
                    try:
                        main_images_obj = MainImages.objects.get(
                            product=prod, is_sourced=True)
                        main_images_list |= main_images_obj.main_images.all()
                        main_images_list = main_images_list.distinct()
                        images = create_response_images_main(main_images_list)
                        temp_dict2["thumbnailImageUrl"] = images[0]["thumbnail_url"]
                    except Exception as e:
                        temp_dict2["thumbnailImageUrl"] = ""

                    
                    temp_dict2["name"] = str(prod.product_name)
                    temp_dict2["displayId"] = str(prod.product_id)
                    temp_dict2["uuid"] = str(prod.uuid)
                    temp_products.append(temp_dict2)
                temp_dict["products"] = temp_products
                temp_dict["isPublished"] = section_obj.is_published
                section_list.append(temp_dict)

            response['section_list'] = section_list
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchAdminCategoriesAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UpdateAdminCategoryAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateAdminCategoryAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            data = data["sectionData"]

            uuid = data["uuid"]
            name = data["name"]
            listing_type = data["listingType"]
            is_published = data["isPublished"]
            products = data["products"]
            
            section_obj = Section.objects.get(uuid=uuid)
            section_obj.name = name
            section_obj.listing_type = listing_type
            section_obj.is_published = is_published
            section_obj.modified_by = None
            section_obj.products.clear()
            for product in products:
                product_obj = Product.objects.get(uuid=product)
                section_obj.products.add(product_obj)

            section_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateAdminCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class DeleteAdminCategoryAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("DeleteAdminCategoryAPI: %s", str(data))

            uuid = data["uuid"]
            
            Section.objects.get(uuid=uuid).delete()
            
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteAdminCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class PublishAdminCategoryAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("PublishAdminCategoryAPI: %s", str(data))

            uuid = data["uuid"]
            
            section_obj = Section.objects.get(uuid=uuid)
            section_obj.is_published = True
            section_obj.save()
            
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PublishAdminCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UnPublishAdminCategoryAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UnPublishAdminCategoryAPI: %s", str(data))

            uuid = data["uuid"]
            
            section_obj = Section.objects.get(uuid=uuid)
            section_obj.is_published = False
            section_obj.save()
            
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UnPublishAdminCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class SectionBulkUploadAPI(APIView):
    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("SectionBulkUploadAPI: %s", str(data))

            path = default_storage.save('tmp/temp-section.xlsx', data["import_file"])
            path = "https://wig-wams-s3-bucket.s3.ap-south-1.amazonaws.com/"+path
            dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
            rows = len(dfs.iloc[:])

            uuid = data["uuid"]
            section_obj = Section.objects.get(uuid=uuid)

            products = []
            unsuccessful_count = 0
            for i in range(rows):
                try:
                    product_id = dfs.iloc[i][0]
                    product_obj = Product.objects.get(product_id=product_id)
                    section_obj.products.add(product_obj)

                    temp_dict2 = {}

                    main_images_list = ImageBucket.objects.none()
                    try:
                        main_images_obj = MainImages.objects.get(
                            product=product_obj, is_sourced=True)
                        main_images_list |= main_images_obj.main_images.all()
                        main_images_list = main_images_list.distinct()
                        images = create_response_images_main(main_images_list)
                        temp_dict2["thumbnailImageUrl"] = images[0]["thumbnail_url"]
                    except Exception as e:
                        temp_dict2["thumbnailImageUrl"] = ""

                    temp_dict2["name"] = str(product_obj.product_name)
                    temp_dict2["displayId"] = str(product_obj.product_id)
                    temp_dict2["uuid"] = str(product_obj.uuid)
                    products.append(temp_dict2)

                except Exception as e:
                    unsuccessful_count += 1
                    
            section_obj.save()

            response["products"] = products
            response["unsuccessful_count"] = unsuccessful_count
            response["filepath"] = path 
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SectionBulkUploadAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)



class FetchBannerTypesAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchBannerTypesAPI: %s", str(data))

            organization_name = data["organizationName"]
            organization_obj = Organization.objects.get(name=organization_name)

            banner_type_objs = BannerType.objects.filter(organization=organization_obj)

            banner_types = []
            for banner_type_obj in banner_type_objs:
                temp_dict = {}
                temp_dict["type"] = banner_type_obj.name
                temp_dict["name"] = banner_type_obj.display_name
                temp_dict["limit"] = banner_type_obj.limit
                banner_types.append(temp_dict)

            response['bannerTypes'] = banner_types
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchBannerTypesAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)



class CreateBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("CreateBannerAPI: %s", str(data))

            banner_type = data["bannerType"]
            organization_name = data["organizationName"]
            organization_obj = Organization.objects.get(name=organization_name)

            banner_type_obj = BannerType.objects.get(name=banner_type)

            order_index = Banner.objects.filter(organization=organization_obj).count()+Section.objects.filter(organization=organization_obj).count()+1

            banner_obj = Banner.objects.create(organization=organization_obj, order_index=order_index, banner_type=banner_type_obj)
            
            response['uuid'] = banner_obj.uuid
            response["limit"] = banner_type_obj.limit
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class AddBannerImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("AddBannerImageAPI: %s", str(data))

            uuid = data["uuid"]
            banner_image = data["image"]

            banner_obj = Banner.objects.get(uuid=uuid)
            image_obj = Image.objects.create(image=banner_image)
            unit_banner_image_obj = UnitBannerImage.objects.create(image=image_obj, banner=banner_obj)

            response['uuid'] = unit_banner_image_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddBannerImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class DeleteBannerImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteBannerImageAPI: %s", str(data))

            uuid = data["uuid"]

            UnitBannerImage.objects.get(uuid=uuid).delete()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteBannerImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)



class FetchBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchBannerAPI: %s", str(data))

            resolution = data.get("resolution", "low")
            banner_uuid = data["uuid"]

            banner_obj = Banner.objects.get(uuid=banner_uuid)
            unit_banner_image_objs = UnitBannerImage.objects.filter(banner=banner_obj)

            banner_images = []

            for unit_banner_image_obj in unit_banner_image_objs:
                try:
                    temp_dict = {}
                    temp_dict["uid"] = unit_banner_image_obj.uuid
                    temp_dict["httpLink"] = unit_banner_image_obj.http_link
                    if unit_banner_image_obj.image!=None:
                        if resolution=="low":
                            temp_dict["url"] = unit_banner_image_obj.image.thumbnail.url
                        else:
                            temp_dict["url"] = unit_banner_image_obj.image.image.url
                    else:
                        temp_dict["url"] = ""
                    banner_images.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
            
            response["bannerImages"] = banner_images
            response["limit"] = banner_obj.banner_type.limit
            response["type"] = banner_obj.banner_type.name
            response["name"] = banner_obj.banner_type.display_name
            response["is_published"] = banner_obj.is_published
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchDealsBannerAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class DeleteBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteBannerAPI: %s", str(data))

            uuid = data["uuid"]
            Banner.objects.get(uuid=uuid).delete()
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class PublishBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("PublishBannerAPI: %s", str(data))

            uuid = data["uuid"]
            banner_obj = Banner.objects.get(uuid=uuid)
            banner_obj.is_published = True
            banner_obj.save()
            
            response['uuid'] = banner_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PublishBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UnPublishBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UnPublishBannerAPI: %s", str(data))

            uuid = data["uuid"]
            banner_obj = Banner.objects.get(uuid=uuid)
            banner_obj.is_published = False
            banner_obj.save()
            
            response['uuid'] = banner_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UnPublishBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class PublishDealsHubProductAPI(APIView):
    
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("PublishDealsHubProductAPI: %s", str(data))
            product_pk = data["product_pk"]
            product_obj = Product.objects.get(pk=product_pk)
            dealshub_product_obj = DealsHubProduct.objects.get(product=product_obj)
            dealshub_product_obj.is_published = True
            dealshub_product_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PublishDealsHubProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UnPublishDealsHubProductAPI(APIView):
    
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UnPublishDealsHubProductAPI: %s", str(data))
            product_pk = data["product_pk"]
            product_obj = Product.objects.get(pk=product_pk)
            dealshub_product_obj = DealsHubProduct.objects.get(product=product_obj)
            dealshub_product_obj.is_published = False
            dealshub_product_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UnPublishDealsHubProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class DeleteProductFromSectionAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteProductFromSectionAPI: %s", str(data))

            section_uuid = data["sectionUuid"]
            product_uuid = data["productUuid"]

            section_obj = Section.objects.get(uuid=section_uuid)
            product_obj = Product.objects.get(uuid=product_uuid)
            section_obj.products.remove(product_obj)
            section_obj.save()
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteProductFromSectionAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class PublishDealsHubProductsAPI(APIView):
    
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("PublishDealsHubProductsAPI: %s", str(data))
            product_pk_list = data["product_pk_list"]
            for product_pk in product_pk_list:
                product_obj = Product.objects.get(pk=product_pk)
                dealshub_product_obj = DealsHubProduct.objects.get(product=product_obj)
                dealshub_product_obj.is_published = True
                dealshub_product_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PublishDealsHubProductsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UnPublishDealsHubProductsAPI(APIView):
    
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UnPublishDealsHubProductsAPI: %s", str(data))
            product_pk_list = data["product_pk_list"]
            for product_pk in product_pk_list:
                product_obj = Product.objects.get(pk=product_pk)
                dealshub_product_obj = DealsHubProduct.objects.get(product=product_obj)
                dealshub_product_obj.is_published = False
                dealshub_product_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UnPublishDealsHubProductsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UpdateLinkBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UpdateLinkBannerAPI: %s", str(data))

            http_link = data["httpLink"]
            uuid = data["uuid"]

            unit_banner_image_obj = UnitBannerImage.objects.get(uuid=uuid)
            unit_banner_image_obj.http_link = http_link
            unit_banner_image_obj.save()
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateLinkBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchHeadingDataAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchHeadingDataAPI: %s", str(data))

            organization_name = data["organizationName"]
            organization_obj = Organization.objects.get(name=organization_name)

            included_category_dict = {}

            dealshub_heading_objs = DealsHubHeading.objects.filter(organization=organization_obj)
            heading_list = []
            for dealshub_heading_obj in dealshub_heading_objs:
                temp_dict = {}
                temp_dict["headingName"] = dealshub_heading_obj.name
                category_list = []
                category_objs = dealshub_heading_obj.categories.all()
                for category_obj in category_objs:
                    included_category_dict[category_obj.pk] = 1
                    temp_dict2 = {}
                    temp_dict2["categoryName"] = category_obj.name
                    sub_category_list = []
                    sub_category_objs = SubCategory.objects.filter(category=category_obj)
                    for sub_category_obj in sub_category_objs:
                        temp_dict3 = {}
                        temp_dict3["subcategoryName"] = sub_category_obj.name
                        sub_category_list.append(temp_dict3)
                    temp_dict2["subcategoryList"] = sub_category_list
                    category_list.append(temp_dict2)
                temp_dict["categoryList"] = category_list
                
                image_list = []
                image_link_objs = dealshub_heading_obj.image_links.all()
                for image_link_obj in image_link_objs:
                    temp_dict4 = {}
                    temp_dict4["imageUrl"] = image_link_obj.image.image.url
                    temp_dict4["httpLink"] = image_link_obj.http_link
                    image_list.append(temp_dict4)
                temp_dict["imageList"] = image_list

                heading_list.append(temp_dict)

            temp_dict = {}
            other_category_list = []
            temp_dict["headingName"] = "Others"
            category_objs = Category.objects.filter(organization=organization_obj)
            for category_obj in category_objs:
                if category_obj.pk not in included_category_dict:
                    temp_dict2 = {}
                    temp_dict2["categoryName"] = category_obj.name
                    sub_category_list = []
                    sub_category_objs = SubCategory.objects.filter(category=category_obj)
                    for sub_category_obj in sub_category_objs:
                        temp_dict3 = {}
                        temp_dict3["subcategoryName"] = sub_category_obj.name
                        sub_category_list.append(temp_dict3)
                    temp_dict2["subcategoryList"] = sub_category_list
                    other_category_list.append(temp_dict2)
            temp_dict["categoryList"] = other_category_list
            temp_dict["imageList"] = []
            if len(other_category_list)>0:
                heading_list.append(temp_dict)

            response["headingList"] = heading_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchHeadingDataAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchHeadingDataAdminAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchHeadingDataAdminAPI: %s", str(data))

            organization_name = data["organizationName"]
            organization_obj = Organization.objects.get(name=organization_name)

            dealshub_heading_objs = DealsHubHeading.objects.filter(organization=organization_obj)
            heading_list = []
            for dealshub_heading_obj in dealshub_heading_objs:
                temp_dict = {}
                temp_dict["headingName"] = dealshub_heading_obj.name
                temp_dict["uuid"] = dealshub_heading_obj.uuid
                category_list = []
                category_objs = dealshub_heading_obj.categories.all()
                for category_obj in category_objs:
                    temp_dict2 = {}
                    temp_dict2["key"] = category_obj.uuid+"|"+category_obj.name

                    category_list.append(temp_dict2)
                temp_dict["categoryList"] = category_list
                
                image_list = []
                image_link_objs = dealshub_heading_obj.image_links.all()
                for image_link_obj in image_link_objs:
                    temp_dict4 = {}
                    temp_dict4["url"] = image_link_obj.image.image.url
                    temp_dict4["httpLink"] = image_link_obj.http_link
                    temp_dict4["uid"] = image_link_obj.uuid
                    image_list.append(temp_dict4)
                temp_dict["imageList"] = image_list

                heading_list.append(temp_dict)

            response["headingList"] = heading_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchHeadingDataAdminAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchHeadingCategoryListAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchHeadingCategoryListAPI: %s", str(data))

            organization_name = data["organizationName"]
            organization_obj = Organization.objects.get(name=organization_name)
            
            category_list = []
            category_objs = Category.objects.filter(organization=organization_obj)
            for category_obj in category_objs:
                temp_dict = {}
                temp_dict["name"] = category_obj.name
                temp_dict["uuid"] = category_obj.uuid+"|"+category_obj.name
                category_list.append(temp_dict)
            
            response["categoryList"] = category_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchHeadingCategoryListAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class DeleteHeadingAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteHeadingAPI: %s", str(data))

            uuid = data["uuid"]
            
            DealsHubHeading.objects.get(uuid=uuid).delete()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteHeadingAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class CreateHeadingDataAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("CreateHeadingDataAPI: %s", str(data))

            organization_name = data["organizationName"]
            organization_obj = Organization.objects.get(name=organization_name)

            heading_name = data["headingName"]
            
            uuid1 = str(uuid.uuid4())
            dealshub_heading_obj = DealsHubHeading.objects.create(organization=organization_obj, name=heading_name, uuid=uuid1)

            response["uuid"] = dealshub_heading_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateHeadingDataAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class SaveHeadingDataAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("SaveHeadingDataAPI: %s", str(data))

            data = data["dataObj"]

            uuid1 = data["uuid"]

            dealshub_heading_obj = DealsHubHeading.objects.get(uuid=uuid1)

            heading_name = data["headingName"]

            category_list = data["categoryList"]

            dealshub_heading_obj.categories.clear()            
            dealshub_heading_obj.name = heading_name
            for category in category_list:
                category_obj = Category.objects.get(uuid=category["key"].split("|")[0])
                dealshub_heading_obj.categories.add(category_obj)

            dealshub_heading_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveHeadingDataAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UploadImageHeadingAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UploadImageHeadingAPI: %s", str(data))

            uuid1 = data["uuid"]
            image = data["image"]

            if image=="" or image=="undefined" or image==None:
                return Response(data=response)

            dealshub_heading_obj = DealsHubHeading.objects.get(uuid=uuid1)

            image_obj = Image.objects.create(image=image)
            url = image_obj.image.url
            image_link_obj = ImageLink.objects.create(image=image_obj, uuid=str(uuid.uuid4()))
            dealshub_heading_obj.image_links.add(image_link_obj)
            dealshub_heading_obj.save()


            dataObj = {
                "uid": image_link_obj.uuid,
                "url": url,
                "httpLink": ""
            }
            response["dataObj"] = dataObj
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadImageHeadingAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UpdateImageHeadingLinkAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UpdateImageHeadingLinkAPI: %s", str(data))

            uuid = data["uuid"]
            http_link = data["httpLink"]

            image_link_obj = ImageLink.objects.get(uuid=uuid)
            image_link_obj.http_link = http_link
            image_link_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateImageHeadingLinkAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class DeleteImageHeadingAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteImageHeadingAPI: %s", str(data))

            uuid = data["uuid"]

            ImageLink.objects.get(uuid=uuid).delete()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteImageHeadingAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchUserOrganizationAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchUserOrganizationAPI: %s", str(data))

            username = data["userName"]
            custom_permission_obj = CustomPermission.objects.get(user__username=username)
            organization_name = custom_permission_obj.brands.all()[0].organization.name
            
            response["organizationName"] = organization_name
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchUserOrganizationAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchDealshubAdminSectionsAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchDealshubAdminSectionsAPI: %s", str(data))

            limit = data.get("limit", False)
            is_dealshub = data.get("isDealshub", False)

            organization_name = data["organizationName"]
            resolution = data.get("resolution", "low")

            organization_obj = Organization.objects.get(name=organization_name)

            section_objs = Section.objects.filter(organization=organization_obj).order_by('order_index')

            if is_dealshub==True:
                section_objs = section_objs.filter(is_published=True)                
            
            dealshub_admin_sections = []
            for section_obj in section_objs:
                temp_dict = {}
                temp_dict["orderIndex"] = section_obj.order_index
                temp_dict["type"] = "ProductListing"
                temp_dict["uuid"] = str(section_obj.uuid)
                temp_dict["name"] = str(section_obj.name)
                temp_dict["listingType"] = str(section_obj.listing_type)
                temp_dict["createdOn"] = str(datetime.datetime.strftime(section_obj.created_date, "%d %b, %Y"))
                temp_dict["modifiedOn"] = str(datetime.datetime.strftime(section_obj.modified_date, "%d %b, %Y"))
                temp_dict["createdBy"] = str(section_obj.created_by)
                temp_dict["modifiedBy"] = str(section_obj.modified_by)
                temp_dict["isPublished"] = section_obj.is_published
                
                temp_products = []

                section_products = section_obj.products.all()
                if limit==True:
                    if section_obj.listing_type=="Carousel":
                        section_products = section_products[:14]
                    elif section_obj.listing_type=="Grid Stack":
                        section_products = section_products[:14]

                for prod in section_products:
                    temp_dict2 = {}

                    main_images_list = ImageBucket.objects.none()
                    try:
                        main_images_obj = MainImages.objects.get(product=prod, is_sourced=True)
                        main_images_list |= main_images_obj.main_images.all()
                        main_images_list = main_images_list.distinct()
                        images = create_response_images_main(main_images_list)
                        temp_dict2["thumbnailImageUrl"] = images[0]["midimage_url"]
                    except Exception as e:
                        temp_dict2["thumbnailImageUrl"] = Config.objects.all()[0].product_404_image.image.url

                    
                    temp_dict2["name"] = str(prod.product_name)
                    temp_dict2["displayId"] = str(prod.product_id)
                    temp_dict2["uuid"] = str(prod.uuid)

                    if is_dealshub==True:
                        temp_dict2["category"] = "" if prod.base_product.category==None else str(prod.base_product.category)
                        temp_dict2["currency"] = "AED"

                    temp_products.append(temp_dict2)
                temp_dict["products"] = temp_products

                dealshub_admin_sections.append(temp_dict)

            banner_objs = Banner.objects.filter(organization=organization_obj).order_by('order_index')

            if is_dealshub==True:
                banner_objs = banner_objs.filter(is_published=True)

            for banner_obj in banner_objs:
                unit_banner_image_objs = UnitBannerImage.objects.filter(banner=banner_obj)

                banner_images = []
                temp_dict = {}
                temp_dict["orderIndex"] = banner_obj.order_index
                temp_dict["type"] = "Banner"
                temp_dict["uuid"] = banner_obj.uuid
                temp_dict["name"] = banner_obj.banner_type.display_name
                temp_dict["bannerType"] = banner_obj.banner_type.name
                temp_dict["limit"] = banner_obj.banner_type.limit
                for unit_banner_image_obj in unit_banner_image_objs:
                    temp_dict2 = {}
                    temp_dict2["uid"] = unit_banner_image_obj.uuid
                    temp_dict2["httpLink"] = unit_banner_image_obj.http_link
                    if unit_banner_image_obj.image!=None:
                        if resolution=="low":
                            temp_dict2["url"] = unit_banner_image_obj.image.mid_image.url
                        else:
                            temp_dict2["url"] = unit_banner_image_obj.image.image.url
                    else:
                        temp_dict2["url"] = ""
                    banner_images.append(temp_dict2)
                
                temp_dict["bannerImages"] = banner_images
                temp_dict["isPublished"] = banner_obj.is_published

                dealshub_admin_sections.append(temp_dict)

            dealshub_admin_sections = sorted(dealshub_admin_sections, key = lambda i: i["orderIndex"]) 

            response["sections_list"] = dealshub_admin_sections
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchDealshubAdminSectionsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class SaveDealshubAdminSectionsOrderAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("SaveDealshubAdminSectionsOrderAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            dealshub_admin_sections = data["dealshubAdminSections"]

            cnt = 1
            for dealshub_admin_section in dealshub_admin_sections:
                if dealshub_admin_section["type"]=="Banner":
                    uuid = dealshub_admin_section["uuid"]
                    banner_obj = Banner.objects.get(uuid=uuid)
                    banner_obj.order_index = cnt
                    banner_obj.save()
                elif dealshub_admin_section["type"]=="ProductListing":
                    uuid = dealshub_admin_section["uuid"]
                    section_obj = Section.objects.get(uuid=uuid)
                    section_obj.order_index = cnt
                    section_obj.save()
                
                cnt += 1

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveDealshubAdminSectionsOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class SearchSectionProductsAutocompleteAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("SearchSectionProductsAutocompleteAPI: %s", str(data))

            search_string = data["searchString"]
            organization_name = data["organizationName"]

            dealshub_products = DealsHubProduct.objects.filter(product__base_product__brand__organization__name=organization_name)

            dealshub_products = dealshub_products.filter(Q(product__base_product__seller_sku__icontains=search_string) | Q(product__product_name__icontains=search_string))[:10]

            dealshub_products_list = []
            for dealshub_product in dealshub_products:
                temp_dict = {}
                temp_dict["name"] = dealshub_product.product.product_name
                temp_dict["uuid"] = dealshub_product.product.uuid
                dealshub_products_list.append(temp_dict)

            response["productList"] = dealshub_products_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchSectionProductsAutocompleteAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class SearchProductsAutocompleteAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("SearchProductsAutocompleteAPI: %s", str(data))

            search_string = data["searchString"]
            organization_name = data["organizationName"]

            category_key_list = DealsHubProduct.objects.filter(is_published=True, product__base_product__brand__organization__name=organization_name, product__product_name__icontains=search_string).values('product__base_product__category').annotate(dcount=Count('product__base_product__category')).order_by('-dcount')[:5]

            category_list = []
            from dealshub.models import Category
            for category_key in category_key_list:
                try:
                    category_name = Category.objects.get(pk=category_key["product__base_product__category"]).name
                    category_list.append(category_name)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.warning("SearchProductsAutocompleteAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["categoryList"] = category_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchProductsAutocompleteAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchDealshubPriceAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchDealshubPriceAPI: %s", str(data))

            uuid1 = data["uuid"]
            company_code = data["companyCode"]

            price = fetch_prices_dealshub(uuid1, company_code)

            response["price"] = price
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchDealshubPriceAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchCompanyProfileDealshubAPI(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data

            logger.info("FetchCompanyProfileDealshubAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            organization_obj = Organization.objects.get(name=data["organizationName"])

            company_data = {}
            company_data["name"] = organization_obj.name
            company_data["contact_info"] = organization_obj.contact_info
            company_data["address"] = organization_obj.address
            company_data["primary_color"] = organization_obj.primary_color
            company_data["secondary_color"] = organization_obj.secondary_color
            company_data["facebook_link"] = organization_obj.facebook_link
            company_data["twitter_link"] = organization_obj.twitter_link
            company_data["instagram_link"] = organization_obj.instagram_link
            company_data["youtube_link"] = organization_obj.youtube_link

            company_data["logo_url"] = ""
            if organization_obj.logo != None:
                company_data["logo_url"] = organization_obj.logo.image.url


            response["company_data"] = company_data
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCompanyProfileDealshubAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddProductToSectionAPI(APIView):
    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("AddProductToSectionAPI: %s", str(data))

            section_uuid = data["sectionUuid"]
            product_uuid = data["productUuid"]

            section_obj = Section.objects.get(uuid=section_uuid)
            product_obj = Product.objects.get(uuid=product_uuid)

            temp_dict = {}

            main_images_list = ImageBucket.objects.none()
            try:
                main_images_obj = MainImages.objects.get(product=product_obj, is_sourced=True)
                main_images_list |= main_images_obj.main_images.all()
                main_images_list = main_images_list.distinct()
                images = create_response_images_main(main_images_list)
                response["thumbnailImageUrl"] = images[0]["midimage_url"]
            except Exception as e:
                response["thumbnailImageUrl"] = ""

            
            response["name"] = str(product_obj.product_name)
            response["displayId"] = str(product_obj.product_id)

            section_obj.products.add(product_obj)
            section_obj.save()
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddProductToSectionAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchBulkProductInfoAPI(APIView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchBulkProductInfoAPI: %s", str(data))

            uuidList = json.loads(data["uuidList"])

            productInfo = {}
            for uuid in uuidList:
                product_obj = Product.objects.get(uuid=uuid)

                main_image_url = Config.objects.all()[0].product_404_image.image.url
                try:
                    main_images_obj = MainImages.objects.get(product=product_obj, is_sourced=True)
                    main_images_list = main_images_obj.main_images.all()
                    main_image_url = main_images_list.all()[0].image.mid_image.url
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchBulkProductInfoAPI: %s at %s", e, str(exc_tb.tb_lineno))

                temp_dict = {
                    "productName": product_obj.product_name,
                    "productImageUrl": main_image_url
                }

                productInfo[uuid] = temp_dict
            
            response["productInfo"] = productInfo
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchBulkProductInfoAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)



CreateAdminCategory = CreateAdminCategoryAPI.as_view()

FetchAdminCategories = FetchAdminCategoriesAPI.as_view()

UpdateAdminCategory = UpdateAdminCategoryAPI.as_view()

DeleteAdminCategory = DeleteAdminCategoryAPI.as_view()

PublishAdminCategory = PublishAdminCategoryAPI.as_view()

UnPublishAdminCategory = UnPublishAdminCategoryAPI.as_view()

SectionBulkUpload = SectionBulkUploadAPI.as_view()


FetchBannerTypes = FetchBannerTypesAPI.as_view()

CreateBanner = CreateBannerAPI.as_view()

FetchBanner = FetchBannerAPI.as_view()

DeleteBanner = DeleteBannerAPI.as_view()

PublishBanner = PublishBannerAPI.as_view()

UnPublishBanner = UnPublishBannerAPI.as_view()

UpdateLinkBanner = UpdateLinkBannerAPI.as_view()

AddBannerImage = AddBannerImageAPI.as_view()

DeleteBannerImage = DeleteBannerImageAPI.as_view()

PublishDealsHubProduct = PublishDealsHubProductAPI.as_view()

UnPublishDealsHubProduct = UnPublishDealsHubProductAPI.as_view()

PublishDealsHubProducts = PublishDealsHubProductsAPI.as_view()

UnPublishDealsHubProducts = UnPublishDealsHubProductsAPI.as_view()

DeleteProductFromSection = DeleteProductFromSectionAPI.as_view()


FetchHeadingData = FetchHeadingDataAPI.as_view()

FetchHeadingDataAdmin = FetchHeadingDataAdminAPI.as_view()

FetchHeadingCategoryList = FetchHeadingCategoryListAPI.as_view()

DeleteHeading = DeleteHeadingAPI.as_view()

CreateHeadingData = CreateHeadingDataAPI.as_view()

SaveHeadingData = SaveHeadingDataAPI.as_view()

UploadImageHeading = UploadImageHeadingAPI.as_view()

UpdateImageHeadingLink = UpdateImageHeadingLinkAPI.as_view()

DeleteImageHeading = DeleteImageHeadingAPI.as_view()


FetchUserOrganization = FetchUserOrganizationAPI.as_view()

FetchDealshubAdminSections = FetchDealshubAdminSectionsAPI.as_view()

SaveDealshubAdminSectionsOrder = SaveDealshubAdminSectionsOrderAPI.as_view() 

SearchSectionProductsAutocomplete = SearchSectionProductsAutocompleteAPI.as_view()

SearchProductsAutocomplete = SearchProductsAutocompleteAPI.as_view()

FetchDealshubPrice = FetchDealshubPriceAPI.as_view()

FetchCompanyProfileDealshub = FetchCompanyProfileDealshubAPI.as_view()

AddProductToSection = AddProductToSectionAPI.as_view()

FetchBulkProductInfo = FetchBulkProductInfoAPI.as_view()