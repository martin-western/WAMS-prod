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
            print((json.dumps(content, indent=4, sort_keys=True)))
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
            #print "Error: "+str(e)
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

            response["category"] = str(temp_product_obj.category)
            response["subCategory"] = str(temp_product_obj.sub_category)
            response["id"] = temp_product_obj.product.uuid
            response["uuid"] = data["uuid"]
            response["name"] = product_obj.product_name
            response["price"] = self.fetch_price(product_obj.base_product.seller_sku)
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
            
            response["productDispDetails"] = product_description
            
            response["productImagesUrl"] = []
            images = {}

            main_images_list = ImageBucket.objects.none()
            main_images_obj = MainImages.objects.get(
                product=product_obj, is_sourced=True)
            try:
                main_images_obj = MainImages.objects.get(
                    product=product_obj, is_sourced=True)
                print(main_images_obj)
                main_images_list |= main_images_obj.main_images.all()
            except Exception as e:
                pass
            main_images_list = main_images_list.distinct()
            images["main_images"] = create_response_images_main(
                main_images_list)
            try:
                logger.info("images %s", str(images))
                response["heroImageUrl"] = images["main_images"][0]["main_url"]
            except Exception as e:
                response["heroImageUrl"] = ""

            response["subtitle"] = base_product_obj.subtitle
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
            
            for temp_image in images["sub_images"]:
                temp_images = {}
                temp_images["original"] = temp_image["main_url"]
                temp_images["thumbnail"] = temp_image["thumbnail_url"]
                response["productImagesUrl"].append(temp_images)
            response["productImagesUrl"].append({"original":response["heroImageUrl"], "thumbnail":response["heroImageUrl"]})
            
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
            logger.info("Passing response %s", str(response))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductDetailsAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)


FetchProductDetails = FetchProductDetailsAPI.as_view()

"""
class FetchCarouselAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchCarouselAPI: %s", str(data))

            carousel_obj = [
                {
                    "productName": "Airfryer Mechanical - 3.4 L, 1300 W AF 3501 - M Black",
                    "productCategory": "Fashion",
                    "productSubCategory": "Men's Fashion",
                    "brand": "Puma",
                    "price": "2,239",
                    "prevPrice": "3,300",
                    "currency": "AED",
                    "discount": "15",
                    "rating": "4.5",
                    "totalRatings": "5,372",
                    "heroImage": "https://k.nooncdn.com/t_desktop-thumbnail-v2/v1568636323/N28431691A_1.jpg",
                    "id": 1
                },
                {
                    "productName": "2-Slice Bread Toaster, 700W TA01105 Milk White",
                    "productCategory": "Fashion",
                    "productSubCategory": "Men's Fashion",
                    "brand": "Provogue",
                    "price": "4,000",
                    "prevPrice": "4,500",
                    "currency": "AED",
                    "discount": "15",
                    "rating": "3.9",
                    "totalRatings": "1,772",
                    "heroImage": "https://k.nooncdn.com/t_desktop-thumbnail-v2/v1571139454/N29227703A_8.jpg",
                    "id": 2
                },
                {
                    "productName": "6-Piece Granite/Marble Coated Aluminium Cookware Set… ",
                    "productCategory": "Fashion",
                    "productSubCategory": "Men's Fashion",
                    "brand": "Reebok",
                    "price": "3,999",
                    "prevPrice": "4,700",
                    "currency": "AED",
                    "discount": "28",
                    "rating": "4.5",
                    "totalRatings": "5,372",
                    "heroImage": "https://k.nooncdn.com/t_desktop-thumbnail-v2/v1574085587/N17109502A_15.jpg",
                    "id": 3
                },
                {
                    "productName": "Realme 5s (Crystal Blue, 128 GB)",
                    "productCategory": "Fashion",
                    "productSubCategory": "Men's Fashion",
                    "brand": "Sparx",
                    "price": "1,200",
                    "prevPrice": "1,800",
                    "currency": "AED",
                    "discount": "10",
                    "rating": "4.5",
                    "totalRatings": "5,372",
                    "heroImage": "https://rukminim1.flixcart.com/image/312/312/k2jbyq80pkrrdj/mobile-refurbished/v/w/c/x-128-u-rmx1901-realme-8-original-imafgzg9yvran9r3.jpeg?q=70",
                    "id": 4
                },
                {
                    "productName": "Realme X (Space Blue, 128 GB)",
                    "productCategory": "Fashion",
                    "productSubCategory": "Men's Fashion",
                    "brand": "Reebok",
                    "price": "3,999",
                    "prevPrice": "5,600",
                    "currency": "AED",
                    "discount": "28",
                    "rating": "4.5",
                    "totalRatings": "5,372",
                    "heroImage": "https://rukminim1.flixcart.com/image/312/312/k1fbmvk0/mobile/k/b/e/mi-redmi-8-mzb8250in-original-imafhyabpggagngr.jpeg?q=70",
                    "id": 5
                },
                {
                    "productName": "Lenovo Ideapad 130 Core i5 8th Gen - (8 GB/1 TB HDD/Windows 10 Home/2 GB Graphics) 130-15IKB Laptop  (15.6 inch, Black, 2.1 kg)",
                    "productCategory": "Fashion",
                    "productSubCategory": "Women's Fashion",
                    "brand": "vaidehi",
                    "price": "2,000",
                    "prevPrice": "2,900",
                    "currency": "AED",
                    "discount": "10",
                    "rating": "4.5",
                    "totalRatings": "5,372",
                    "heroImage": "https://rukminim1.flixcart.com/image/312/312/jz7az680/computer/b/3/k/lenovo-na-laptop-original-imafj9wscwkeyu45.jpeg?q=70",
                    "id": 6
                },
                {
                    "productName": "Amayra Women's Cotton Anarkali Kurti(Blue)",
                    "productCategory": "Fashion",
                    "productSubCategory": "Women's Fashion",
                    "brand": "Amarya",
                    "price": "4,099",
                    "prevPrice": "4,199",
                    "currency": "AED",
                    "discount": "20",
                    "rating": "4.5",
                    "totalRatings": "5,372",
                    "heroImage": "https://rukminim1.flixcart.com/image/150/150/k0wqwsw0/wall-clock/g/g/b/round-wall-clock-957-gold-analog-ajanta-original-imafkhkfdempaphb.jpeg?q=70",
                    "id": 7
                },
                {
                    "productName": "Garment Steamer, 1.3 L Capacity, 1800W HY - 288 Black",
                    "productCategory": "Fashion",
                    "productSubCategory": "Women's Fashion",
                    "brand": "Sparx",
                    "price": "999",
                    "prevPrice": "1,099",
                    "currency": "AED",
                    "discount": "10",
                    "rating": "4.5",
                    "totalRatings": "5,372",
                    "heroImage": "https://k.nooncdn.com/t_desktop-thumbnail-v2/v1570427257/N28431698A_1.jpg",
                    "id": 8
                }
            ]
            response['carousel'] = carousel_obj

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FecthProductDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)
"""

# class FetchCarouselAPI(APIView):
    
#     permission_classes = [AllowAny]
    
#     def fetch_price(self,product_id):
#         try:
#             url="http://94.56.89.114:8001/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"
#             headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
#             credentials = ("MOBSERVICE", "~lDT8+QklV=(")
#             company_code = "1070" # GEEPAS
#             body = """<soapenv:Envelope xmlns:urn="urn:sap-com:document:sap:rfc:functions" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
#             <soapenv:Header />
#             <soapenv:Body>
#             <urn:ZAPP_STOCK_PRICE>
#              <IM_MATNR>
#               <item>
#                <MATNR>""" + product_id + """</MATNR>
#               </item>
#              </IM_MATNR>
#              <IM_VKORG>
#               <item>
#                <VKORG>""" + company_code + """</VKORG>
#               </item>
#              </IM_VKORG>
#              <T_DATA>
#               <item>
#                <MATNR></MATNR>
#                <MAKTX></MAKTX>
#                <LGORT></LGORT>
#                <CHARG></CHARG>
#                <SPART></SPART>
#                <MEINS></MEINS>
#                <ATP_QTY></ATP_QTY>
#                <TOT_QTY></TOT_QTY>
#                <CURRENCY></CURRENCY>
#                <IC_EA></IC_EA>
#                <OD_EA></OD_EA>
#                <EX_EA></EX_EA>
#                <RET_EA></RET_EA>
#                <WERKS></WERKS>
#               </item>
#              </T_DATA>
#             </urn:ZAPP_STOCK_PRICE>
#             </soapenv:Body>
#             </soapenv:Envelope>"""
#             response2 = requests.post(url, auth=credentials, data=body, headers=headers)
#             content = response2.content
#             content = xmltodict.parse(content)
#             content = json.loads(json.dumps(content))
#             print((json.dumps(content, indent=4, sort_keys=True)))
#             items = content["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_STOCK_PRICEResponse"]["T_DATA"]["item"]
#             price = 0
#             temp_price = 0
#             for item in items:
#                 temp_price = item["EX_EA"]
#                 if temp_price!=None:
#                     temp_price = float(temp_price)
#                     price = max(temp_price, price)
#             return float(price)
#         except Exception as e:
#             #print "Error: "+str(e)
#             return 0
#     def get(self, request, *args, **kwargs):
#         response = {}
#         response['status'] = 500
#         try:
#             data = request.data
#             logger.info("FetchCarouselAPI: %s", str(data))
#             product_pks = [942, 943, 944,950,951,957,958,959,961,966]
#             carousel_obj = []
#             for product_pk in product_pks:
#                 prod_obj = Product.objects.get(pk = product_pk)
#                 temp_dict={}
#                 temp_dict["productName"] = prod_obj.product_name
#                 temp_dict["productCategory"] = prod_obj.base_product.category
#                 temp_dict["productSubCategory"] = prod_obj.base_product.subtitle
#                 temp_dict["brand"] = str(prod_obj.base_product.brand)
#                 temp_dict["price"] = self.fetch_price(prod_obj.base_product.seller_sku)
#                 temp_dict["prevPrice"] = self.fetch_price(prod_obj.base_product.seller_sku)
#                 temp_dict["currency"] = "AED"
#                 temp_dict["discount"] = "0%"
#                 temp_dict["rating"] = "3.5"
#                 temp_dict["totalRatings"] = "356"
#                 temp_dict["uuid"] = prod_obj.uuid
                
#                 main_images_list = ImageBucket.objects.none()
#                 main_images_objs = MainImages.objects.filter(product=prod_obj)
#                 for main_images_obj in main_images_objs:
#                     main_images_list |= main_images_obj.main_images.all()
#                 main_images_list = main_images_list.distinct()
#                 if main_images_list.filter(is_main_image=True).count() > 0:
#                     try:
#                         temp_dict["heroImage"] = main_images_list.filter(is_main_image=True)[
#                             0].image.thumbnail.url
#                     except Exception as e:
#                         temp_dict["heroImage"] = Config.objects.all()[
#                             0].product_404_image.image.url
#                 else:
#                     temp_dict["heroImage"] = Config.objects.all()[
#                         0].product_404_image.image.url
#                 temp_dict["id"] = prod_obj.pk
#                 carousel_obj.append(temp_dict)

#             response['carousel'] = carousel_obj
#             response['status'] = 200
#         except Exception as e:
#             exc_type, exc_obj, exc_tb = sys.exc_info()
#             logger.error("FetchCarouselProductAPI: %s at %s",
#                          e, str(exc_tb.tb_lineno))
#         return Response(data=response)



# FetchCarousel = FetchCarouselAPI.as_view()



class FetchSectionsProductsAPI(APIView):
    
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
            print((json.dumps(content, indent=4, sort_keys=True)))
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
            #print "Error: "+str(e)
            return 0
    def get(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchSectionsProductsAPI: %s", str(data))

            section_objs = Section.objects.filter(is_published=True)

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
                    temp_dict2["productCategory"] = product_obj.base_product.category
                    temp_dict2["productSubCategory"] = product_obj.base_product.sub_category
                    temp_dict2["brand"] = str(product_obj.base_product.brand)
                    temp_dict2["price"] = self.fetch_price(product_obj.base_product.seller_sku)
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
            logger.error("FetchSectionsProductsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)

FetchSectionsProducts = FetchSectionsProductsAPI.as_view()




class FetchSectionsProductsLimitAPI(APIView):
    
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
            print((json.dumps(content, indent=4, sort_keys=True)))
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
            #print "Error: "+str(e)
            return 0
    def get(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchSectionsProductsLimitAPI: %s", str(data))

            section_objs = Section.objects.filter(is_published=True).order_by("-pk")

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
                    temp_dict2["productCategory"] = product_obj.base_product.category
                    temp_dict2["productSubCategory"] = product_obj.base_product.sub_category
                    temp_dict2["brand"] = str(product_obj.base_product.brand)
                    temp_dict2["price"] = self.fetch_price(product_obj.base_product.seller_sku)
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
            print((json.dumps(content, indent=4, sort_keys=True)))
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
            #print "Error: "+str(e)
            return 0
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
                temp_dict2["price"] = self.fetch_price(product_obj.base_product.seller_sku)
                temp_dict2["prevPrice"] = temp_dict2["price"]
                temp_dict2["currency"] = "AED"
                temp_dict2["discount"] = "10%"
                temp_dict2["rating"] = "4.5"
                temp_dict2["totalRatings"] = "5,372"
                temp_dict2["uuid"] = str(product_obj.uuid)
                temp_dict2["id"] = str(product_obj.uuid)
                main_images_list = ImageBucket.objects.none()
                main_images_objs = MainImages.objects.filter(product=product_obj)
                for main_images_obj in main_images_objs:
                    main_images_list |= main_images_obj.main_images.all()
                main_images_list = main_images_list.distinct()
                if main_images_list.filter(is_main_image=True).count() > 0:
                    try:
                        temp_dict2["heroImageUrl"] = main_images_list.filter(is_main_image=True)[
                            0].image.mid_image.url
                    except Exception as e:
                        temp_dict2["heroImageUrl"] = Config.objects.all()[
                            0].product_404_image.image.url
                else:
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



class FetchCategoryGridBannerCardsAPI(APIView):
    
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchCategoryGridBannerCardsAPI: %s", str(data))

            carousel_obj = [
                {
                    "src": "wp-content/uploads/2018/04/cat-22-330x308.png",
                    "alt": "Home &amp; Audio Enternteinment",
                    "title": "Home &amp; Audio Enternteinment"
                },
                {
                    "src": "wp-content/uploads/2018/04/cat-2-330x308.png",
                    "alt": "Smartphones &amp; Tablets",
                    "title": "Smartphones &amp; Tablets"
                },
                {
                    "src": "wp-content/uploads/2018/04/cat-3-330x308.png",
                    "alt": "Desktop PCs &amp; Laptops",
                    "title": "Desktop PCs &amp; Laptops"
                },
                {
                    "src": "wp-content/uploads/2018/04/cat-4-330x308.png",
                    "alt": "Video Games &amp; Consoles",
                    "title": "Video Games &amp; Consoles"
                },
                {
                    "src": "wp-content/uploads/2018/04/cat-5-330x308.png",
                    "alt": "Gadgets &amp; Accesories",
                    "title": "Gadgets &amp; Accesories"
                },
                {
                    "src": "wp-content/uploads/2018/04/cat-6-330x308.png",
                    "alt": "Photo Cameras",
                    "title": "Photo Cameras"
                }
            ]
            response['cards'] = carousel_obj

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCategoryGridBannerCardsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


FetchCategoryGridBannerCards = FetchCategoryGridBannerCardsAPI.as_view()


class FetchCategoriesAPI(APIView):
    
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchCategoriesAPI: %s", str(data))
            temp_categories = Category.objects.all()
            categories_obj = []
            for category in temp_categories:
                temp_dict = {}
                temp_dict["name"] = category.name
                temp_dict["catId"] = category.category_id
                temp_dict["subCategories"] = []
                for sub_category in category.sub_categories.all():
                    temp_sub_category_dict = {}
                    temp_sub_category_dict["name"] = sub_category.name
                    temp_sub_category_dict["catId"] = sub_category.sub_category
                    temp_dict["subCategories"].append(temp_sub_category_dict)
                categories_obj.append(temp_dict)
            categories_obj = [
                {
                    "name": "electronics",
                    "catId": "fw-234",
                    "subCategories": [
                        {
                            "catId": "",
                            "name": ""
                        }
                    ]
                },
                {
                    "name": "fashion",
                    "catId": "",
                    "subCategories": [
                        {
                            "catId": "",
                            "name": ""
                        }
                    ]
                },
                {
                    "name": "home and kitchen",
                    "catId": "",
                    "subCategories": [
                        {
                            "catId": "",
                            "name": ""
                        }
                    ]
                },
                {
                    "name": "beauty and fragrance",
                    "catId": "",
                    "subCategories": [
                        {
                            "catId": "",
                            "name": ""
                        }
                    ]
                },
                {
                    "name": "baby and kids",
                    "catId": "",
                    "subCategories": [
                        {
                            "catId": "",
                            "name": ""
                        }
                    ]
                },
                {
                    "name": "deals",
                    "catId": "",
                    "subCategories": [
                        {
                            "catId": "",
                            "name": ""
                        }
                    ]
                }
            ]

            response['categories'] = categories_obj

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCategoriesAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


FetchCategories = FetchCategoriesAPI.as_view()


class FetchDashboardBannerDetailsAPI(APIView):
    
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchDashboardBannerDetailsAPI: %s", str(data))

            banner_details = [
                {
                    "id": "1",
                    "imgUrl": "https://rukminim1.flixcart.com/flap/1688/280/image/614f5288d387863b.jpg?q=50"
                },
                {
                    "id": "2",
                    "imgUrl": "https://rukminim1.flixcart.com/flap/1688/280/image/fe0fdf911e24c3b7.jpg?q=50"
                },
                {
                    "id": "3",
                    "imgUrl": "https://rukminim1.flixcart.com/flap/1688/280/image/4a4a041b1cb541f4.jpg?q=50"
                }
            ]
            response['banner_details'] = banner_details

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchDashboardBannerDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


FetchDashboardBannerDetails = FetchDashboardBannerDetailsAPI.as_view()


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
                        "id": "ca300cbf-955c-4e0b-bfc2-d99e6dd22028"
                    },
                    {
                        "productName": "Geepas GAC9433 3-in-1 Air Cooler, 65W",
                        "productCategory": "Electronics",
                        "productSubCategory": "Cooler",
                        "brand": "Geepas",
                        "price": "4,000",
                        "prevPrice": "4,500",
                        "currency": "AED",
                        "discount": "15",
                        "rating": "3.9",
                        "totalRatings": "1,772",
                        "heroImage": "https://wig-wams-s3-bucket.s3.amazonaws.com/midsize/1569505981GAC9433_3.JPG",
                        "id": "9259d36f-4356-450a-a0d1-17193aded65b"
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
                        "id": "7f1f18fe-6c5d-4d44-a710-384aa219929a"
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
                        "id": "a56a294d-4054-4caf-a6e4-9b639a4da958"
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
                        "id": "cfbdc5bd-391a-4d26-a6e0-e5a923ae3973"
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

# FetchSpecialDiscountProduct


class FetchSpecialDiscountProductAPI(APIView):
    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchSpecialDiscountProductAPI: %s", str(data))

            special_discount_deals = {
                "id": "789",
                "discountDealImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/console.png",
                "name": "Game Console Controller + USB 3.0 Cable",
                "price": "90",
                "currency": "AED",
                "totalUnits": "25",
                "soldUnits": "9",
                "counter": {
                    "timeToEnd": "Wed Jan 16 2020 20:47:52 GMT+0530",
                    "originalPrice": "99"
                }
            }
            response['special_discount_deals'] = special_discount_deals

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSpecialDiscountProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


FetchSpecialDiscountProduct = FetchSpecialDiscountProductAPI.as_view()


class FetchSchedularProductsAPI(APIView):
    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchSchedularProductsAPI: %s", str(data))

            schedular_products = [
                {
                    "id": "1",
                    "schedularImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/console-banner.png",
                    "schedularGraphicsText": "https://wig-wams-s3-bucket.s3.amazonaws.com/deals-text.png",
                    "schedularProductImage": "https://wig-wams-s3-bucket.s3.amazonaws.com/console.png",
                    "category": "electronics",
                    "subCategory": "gaming",
                    "name": "Game Console Controller + USB 3.0 Cable",
                    "price": "90",
                    "currency": "AED",
                    "totalUnits": "25",
                    "soldUnits": "9",
                    "counter": {
                        "timeToEnd": "Wed Jan 16 2020 19:57:52",
                        "originalPrice": "99"
                    }
                },
                {
                    "id": "2",
                    "schedularImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/tv-schedular.png",
                    "schedularGraphicsText": "https://wig-wams-s3-bucket.s3.amazonaws.com/deals-text.png",
                    "schedularProductImage": "https://wig-wams-s3-bucket.s3.amazonaws.com/tv.png",
                    "category": "electronics",
                    "subCategory": "television",
                    "name": "Widescreen 4K SUHD TV",
                    "price": "3299.00",
                    "currency": "AED",
                    "totalUnits": "32",
                    "soldUnits": "5"
                },
                {
                    "id": "3",
                    "schedularImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/console-banner.png",
                    "schedularGraphicsText": "https://wig-wams-s3-bucket.s3.amazonaws.com/deals-text.png",
                    "schedularProductImage": "https://wig-wams-s3-bucket.s3.amazonaws.com/console.png",
                    "category": "electronics",
                    "subCategory": "gaming",
                    "name": "Game Console Controller + USB 3.0 Cable",
                    "price": "90",
                    "currency": "AED",
                    "totalUnits": "25",
                    "soldUnits": "9",
                    "counter": {
                        "timeToEnd": "Wed Jan 16 2020 14:47:52 GMT+0530",
                        "originalPrice": "99"
                    }
                },
                {
                    "id": "4",
                    "schedularImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/console-banner.png",
                    "schedularGraphicsText": "https://wig-wams-s3-bucket.s3.amazonaws.com/deals-text.png",
                    "schedularProductImage": "https://wig-wams-s3-bucket.s3.amazonaws.com/console.png",
                    "category": "electronics",
                    "subCategory": "gaming",
                    "name": "Game Console Controller + USB 3.0 Cable",
                    "price": "90",
                    "currency": "AED",
                    "totalUnits": "25",
                    "soldUnits": "9",
                    "counter": {
                        "timeToEnd": "Wed Jan 16 2020 20:47:52 GMT+0530",
                        "originalPrice": "99"
                    }
                }
            ]
            response['schedular_products'] = schedular_products

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSchedularProductsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


FetchSchedularProducts = FetchSchedularProductsAPI.as_view()


class FetchFeaturedProductsAPI(APIView):
    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchFeaturedProductsAPI: %s", str(data))
            
            """
            featured_products = [
                {
                    "productName": "Airfryer Mechanical - 3.4 L, 1300 W AF 3501 - M Black",
                    "productCategory": "Fashion",
                    "productSubCategory": "Men's Fashion",
                    "brand": "Puma",
                    "price": "500",
                    "prevPrice": "3,300",
                    "currency": "AED",
                    "discount": "15",
                    "rating": "4.5",
                    "totalRatings": "5,372",
                    "heroImage": "https://k.nooncdn.com/t_desktop-thumbnail-v2/v1568636323/N28431691A_1.jpg",
                    "id": 1
                },
                {
                    "productName": "2-Slice Bread Toaster, 700W TA01105 Milk White",
                    "productCategory": "Fashion",
                    "productSubCategory": "Men's Fashion",
                    "brand": "Provogue",
                    "price": "4,000",
                    "prevPrice": "4,500",
                    "currency": "AED",
                    "discount": "15",
                    "rating": "3.9",
                    "totalRatings": "1,772",
                    "heroImage": "https://k.nooncdn.com/t_desktop-thumbnail-v2/v1571139454/N29227703A_8.jpg",
                    "id": 2
                },
                {
                    "productName": "6-Piece Granite/Marble Coated Aluminium Cookware Set… ",
                    "productCategory": "Fashion",
                    "productSubCategory": "Men's Fashion",
                    "brand": "Reebok",
                    "price": "3,999",
                    "prevPrice": "4,700",
                    "currency": "AED",
                    "discount": "28",
                    "rating": "4.5",
                    "totalRatings": "5,372",
                    "heroImage": "https://k.nooncdn.com/t_desktop-thumbnail-v2/v1574085587/N17109502A_15.jpg",
                    "id": 3
                },
                {
                    "productName": "Realme 5s (Crystal Blue, 128 GB)",
                    "productCategory": "Fashion",
                    "productSubCategory": "Men's Fashion",
                    "brand": "Sparx",
                    "price": "1,200",
                    "prevPrice": "1,800",
                    "currency": "AED",
                    "discount": "10",
                    "rating": "4.5",
                    "totalRatings": "5,372",
                    "heroImage": "https://rukminim1.flixcart.com/image/312/312/k2jbyq80pkrrdj/mobile-refurbished/v/w/c/x-128-u-rmx1901-realme-8-original-imafgzg9yvran9r3.jpeg?q=70",
                    "id": 4
                },
                {
                    "productName": "Realme X (Space Blue, 128 GB)",
                    "productCategory": "Fashion",
                    "productSubCategory": "Men's Fashion",
                    "brand": "Reebok",
                    "price": "3,999",
                    "prevPrice": "5,600",
                    "currency": "AED",
                    "discount": "28",
                    "rating": "4.5",
                    "totalRatings": "5,372",
                    "heroImage": "https://rukminim1.flixcart.com/image/312/312/k1fbmvk0/mobile/k/b/e/mi-redmi-8-mzb8250in-original-imafhyabpggagngr.jpeg?q=70",
                    "id": 5
                }
            ]
            """

            featured_products = [
                {
                    "productName": "Geepas GAC9602 Air Cooler 70L",
                    "productCategory": "Electronics",
                    "productSubCategory": "Cooler",
                    "brand": "Geepas",
                    "price": "500",
                    "prevPrice": "3,300",
                    "currency": "AED",
                    "discount": "15",
                    "rating": "4.5",
                    "totalRatings": "5,372",
                    "heroImage": "https://wig-wams-s3-bucket.s3.amazonaws.com/1569674764GEEPAS%20MODEL%20GAC9602%20STRAIGHT.jpg",
                    "id": "ca300cbf-955c-4e0b-bfc2-d99e6dd22028"
                },
                {
                    "productName": "Geepas GAC9433 3-in-1 Air Cooler, 65W",
                    "productCategory": "Electronics",
                    "productSubCategory": "Cooler",
                    "brand": "Geepas",
                    "price": "255",
                    "prevPrice": "4,500",
                    "currency": "AED",
                    "discount": "15",
                    "rating": "3.9",
                    "totalRatings": "1,772",
                    "heroImage": "https://wig-wams-s3-bucket.s3.amazonaws.com/1569506104GAC9433%20(1).JPG",
                    "id": "9259d36f-4356-450a-a0d1-17193aded65b"
                },
                {
                    "productName": "Geepas GA1960 4 USB Travel Charger ",
                    "productCategory": "Electronics",
                    "productSubCategory": "Plugs",
                    "brand": "Geepas",
                    "price": "18",
                    "prevPrice": "4,700",
                    "currency": "AED",
                    "discount": "28",
                    "rating": "4.5",
                    "totalRatings": "5,372",
                    "heroImage": "https://wig-wams-s3-bucket.s3.amazonaws.com/1569505000GA1960-2.jpg",
                    "id": "7f1f18fe-6c5d-4d44-a710-384aa219929a"
                },
                {
                    "productName": "Geepas GACW1818HCS 1.5 Ton Window Air Conditioner",
                    "productCategory": "Electronics",
                    "productSubCategory": "Cooler",
                    "brand": "Geepas",
                    "price": "760",
                    "prevPrice": "1,800",
                    "currency": "AED",
                    "discount": "10",
                    "rating": "4.5",
                    "totalRatings": "5,372",
                    "heroImage": "https://wig-wams-s3-bucket.s3.amazonaws.com/1569677989GACW1818HCS-.jpg",
                    "id": "a56a294d-4054-4caf-a6e4-9b639a4da958"
                },
                {
                    "productName": "Geepas GAC9580 High Speed Rechargeable Air Cooler",
                    "productCategory": "Electronics",
                    "productSubCategory": "Cooler",
                    "brand": "Geepas",
                    "price": "27",
                    "prevPrice": "5,600",
                    "currency": "AED",
                    "discount": "28",
                    "rating": "4.5",
                    "totalRatings": "5,372",
                    "heroImage": "https://wig-wams-s3-bucket.s3.amazonaws.com/1569674216GAC9580%20(2).jpg",
                    "id": "cfbdc5bd-391a-4d26-a6e0-e5a923ae3973"
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


# FetchOnSaleProducts


class FetchOnSaleProductsAPI(APIView):
    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchOnSaleProductsAPI: %s", str(data))

            on_sale_products = [
                {
                    "productName": "Lenovo Ideapad 130 Core i5 8th Gen - (8 GB/1 TB HDD/Windows 10 Home/2 GB Graphics) 130-15IKB Laptop  (15.6 inch, Black, 2.1 kg)",
                    "productCategory": "Fashion",
                    "productSubCategory": "Women's Fashion",
                    "brand": "vaidehi",
                    "price": "2,000",
                    "prevPrice": "2,900",
                    "currency": "AED",
                    "discount": "10",
                    "rating": "4.5",
                    "totalRatings": "5,372",
                    "heroImage": "https://rukminim1.flixcart.com/image/312/312/jz7az680/computer/b/3/k/lenovo-na-laptop-original-imafj9wscwkeyu45.jpeg?q=70",
                    "id": 6
                },
                {
                    "productName": "Amayra Women's Cotton Anarkali Kurti(Blue)",
                    "productCategory": "Fashion",
                    "productSubCategory": "Women's Fashion",
                    "brand": "Amarya",
                    "price": "4,099",
                    "prevPrice": "4,199",
                    "currency": "AED",
                    "discount": "20",
                    "rating": "4.5",
                    "totalRatings": "5,372",
                    "heroImage": "https://rukminim1.flixcart.com/image/150/150/k0wqwsw0/wall-clock/g/g/b/round-wall-clock-957-gold-analog-ajanta-original-imafkhkfdempaphb.jpeg?q=70",
                    "id": 7
                },
                {
                    "productName": "Garment Steamer, 1.3 L Capacity, 1800W HY - 288 Black",
                    "productCategory": "Fashion",
                    "productSubCategory": "Women's Fashion",
                    "brand": "Sparx",
                    "price": "999",
                    "prevPrice": "1,099",
                    "currency": "AED",
                    "discount": "10",
                    "rating": "4.5",
                    "totalRatings": "5,372",
                    "heroImage": "https://k.nooncdn.com/t_desktop-thumbnail-v2/v1570427257/N28431698A_1.jpg",
                    "id": 8
                }
            ]
            response['on_sale_products'] = on_sale_products

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOnSaleProductsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


FetchOnSaleProducts = FetchOnSaleProductsAPI.as_view()

# FetchTopRatedProducts


class FetchTopRatedProductsAPI(APIView):
    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchTopRatedProductsAPI: %s", str(data))

            top_rated_products = [
                {
                    "productName": "Amayra Women's Cotton Anarkali Kurti(Blue)",
                    "productCategory": "Fashion",
                    "productSubCategory": "Women's Fashion",
                    "brand": "Amarya",
                    "price": "4,099",
                    "prevPrice": "4,199",
                    "currency": "AED",
                    "discount": "20",
                    "rating": "4.5",
                    "totalRatings": "5,372",
                    "heroImage": "https://rukminim1.flixcart.com/image/150/150/k0wqwsw0/wall-clock/g/g/b/round-wall-clock-957-gold-analog-ajanta-original-imafkhkfdempaphb.jpeg?q=70",
                    "id": 7
                },
                {
                    "productName": "2-Slice Bread Toaster, 700W TA01105 Milk White",
                    "productCategory": "Fashion",
                    "productSubCategory": "Men's Fashion",
                    "brand": "Provogue",
                    "price": "4,000",
                    "prevPrice": "4,500",
                    "currency": "AED",
                    "discount": "15",
                    "rating": "3.9",
                    "totalRatings": "1,772",
                    "heroImage": "https://k.nooncdn.com/t_desktop-thumbnail-v2/v1571139454/N29227703A_8.jpg",
                    "id": 2
                },
                {
                    "productName": "6-Piece Granite/Marble Coated Aluminium Cookware Set… ",
                    "productCategory": "Fashion",
                    "productSubCategory": "Men's Fashion",
                    "brand": "Reebok",
                    "price": "3,999",
                    "prevPrice": "4,700",
                    "currency": "AED",
                    "discount": "28",
                    "rating": "4.5",
                    "totalRatings": "5,372",
                    "heroImage": "https://k.nooncdn.com/t_desktop-thumbnail-v2/v1574085587/N17109502A_15.jpg",
                    "id": 3
                },
                {
                    "productName": "Realme 5s (Crystal Blue, 128 GB)",
                    "productCategory": "Fashion",
                    "productSubCategory": "Men's Fashion",
                    "brand": "Sparx",
                    "price": "1,200",
                    "prevPrice": "1,800",
                    "currency": "AED",
                    "discount": "10",
                    "rating": "4.5",
                    "totalRatings": "5,372",
                    "heroImage": "https://rukminim1.flixcart.com/image/312/312/k2jbyq80pkrrdj/mobile-refurbished/v/w/c/x-128-u-rmx1901-realme-8-original-imafgzg9yvran9r3.jpeg?q=70",
                    "id": 4
                }
            ]
            response['top_rated_products'] = top_rated_products

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchTopRatedProductsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


FetchTopRatedProducts = FetchTopRatedProductsAPI.as_view()


# Search
"""
class SearchAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("SearchAPI: %s", str(data))

            search = {
         "query": "macbook",
      "category": "laptops",
      "filters": [
        {
          "id": "1",
          "name": "brand",
          "values": [
            "Apple",
            "Samsung",
            "Dell",
            "Micosoft",
            "iBall"
          ]
        },
        {
          "id": "2",
          "name": "cpu type",
          "values": [
            "Intel Core i5",
            "Intel Core i7"
          ]
        },
        {
          "id": "3",
          "name": "weight",
          "values": [
            "Up to 0.9 kg",
            "1 - 1.4 kg",
            "2 - 2.5 kg",
            "2.5 kg and more"
          ]
        },
        {
          "id": "4",
          "name": "OS",
          "values": [
            "Windows",
            "Linux",
            "DoS",
            "MacOS"
          ]
        }
      ],
      "products": [
        {
          "name": "MacBook Air 13.3-Inch Retina Display, Core i5 with 1.6GHz Dual Core Processor/8GB RAM/128GB SSD/Intel UHD Graphics 617/English Keyboard -  2019 Space Grey",
          "brand": "Puma",
          "price": "2,239",
          "prevPrice": "3,300",
          "currency": "AED",
          "discount": "15",
          "rating": "5",
          "totalRatings": "5,372",
          "heroImageUrl": "https://rukminim1.flixcart.com/image/312/312/jyq5oy80/computer/s/v/n/apple-na-thin-and-light-laptop-original-imafgwevstseefc9.jpeg?q=70",
          "id": 1
        },
        {
          "name": "MacBook Air 13.3-inch Retina Display, Core i5 Processor/8GB RAM/256GB SSD/Integrated Graphics/English Keyboard 2018 Gold",
          "brand": "Provogue",
          "price": "4,000",
          "prevPrice": "4,500",
          "currency": "AED",
          "discount": "15",
          "rating": "2",
          "totalRatings": "1,772",
          "heroImageUrl": "https://rukminim1.flixcart.com/image/312/312/jyq5oy80/computer/r/g/d/apple-na-thin-and-light-laptop-original-imafgwew9puxqp3k.jpeg?q=70",
          "id": 2
        },
        {
          "name": "MacBook Air 13.3-inch Retina Display, Core i5 Processor/8GB RAM/256GB SSD/Integrated Graphics/English Keyboard 2018 Gold",
          "brand": "Provogue",
          "price": "4,000",
          "prevPrice": "4,500",
          "currency": "AED",
          "discount": "15",
          "rating": "1",
          "totalRatings": "1,772",
          "heroImageUrl": "https://rukminim1.flixcart.com/image/312/312/jyq5oy80/computer/r/g/d/apple-na-thin-and-light-laptop-original-imafgwew9puxqp3k.jpeg?q=70",
          "id": 3
        },
        {
          "name": "MacBook Air 13.3-inch Retina Display, Core i5 Processor/8GB RAM/256GB SSD/Integrated Graphics/English Keyboard 2018 Gold",
          "brand": "Provogue",
          "price": "4,000",
          "prevPrice": "4,500",
          "currency": "AED",
          "discount": "15",
          "rating": "2",
          "totalRatings": "1,772",
          "heroImageUrl": "https://rukminim1.flixcart.com/image/312/312/jyq5oy80/computer/r/g/d/apple-na-thin-and-light-laptop-original-imafgwew9puxqp3k.jpeg?q=70",
          "id": 4
        },
        {
          "name": "MacBook Air 13.3-inch Retina Display, Core i5 Processor/8GB RAM/256GB SSD/Integrated Graphics/English Keyboard 2018 Gold",
          "brand": "Provogue",
          "price": "4,000",
          "prevPrice": "4,500",
          "currency": "AED",
          "discount": "15",
          "rating": "3",
          "totalRatings": "1,772",
          "heroImageUrl": "https://rukminim1.flixcart.com/image/312/312/jyq5oy80/computer/r/g/d/apple-na-thin-and-light-laptop-original-imafgwew9puxqp3k.jpeg?q=70",
          "id": 5
        },
        {
          "name": "MacBook Air 13.3-inch Retina Display, Core i5 Processor/8GB RAM/256GB SSD/Integrated Graphics/English Keyboard 2018 Gold",
          "brand": "Provogue",
          "price": "4,000",
          "prevPrice": "4,500",
          "currency": "AED",
          "discount": "15",
          "rating": "2",
          "totalRatings": "1,772",
          "heroImageUrl": "https://rukminim1.flixcart.com/image/312/312/jyq5oy80/computer/r/g/d/apple-na-thin-and-light-laptop-original-imafgwew9puxqp3k.jpeg?q=70",
          "id": 6
        },
        {
          "name": "MacBook Air 13.3-inch Retina Display, Core i5 Processor/8GB RAM/256GB SSD/Integrated Graphics/English Keyboard 2018 Gold",
          "brand": "Provogue",
          "price": "4,000",
          "prevPrice": "4,500",
          "currency": "AED",
          "discount": "15",
          "rating": "3",
          "totalRatings": "1,772",
          "heroImageUrl": "https://rukminim1.flixcart.com/image/312/312/jyq5oy80/computer/r/g/d/apple-na-thin-and-light-laptop-original-imafgwew9puxqp3k.jpeg?q=70",
          "id": 7
        },
        {
          "name": "MacBook Air 13.3-inch Retina Display, Core i5 Processor/8GB RAM/256GB SSD/Integrated Graphics/English Keyboard 2018 Gold",
          "brand": "Provogue",
          "price": "4,000",
          "prevPrice": "4,500",
          "currency": "AED",
          "discount": "15",
          "rating": "2",
          "totalRatings": "1,772",
          "heroImageUrl": "https://rukminim1.flixcart.com/image/312/312/jyq5oy80/computer/r/g/d/apple-na-thin-and-light-laptop-original-imafgwew9puxqp3k.jpeg?q=70",
          "id": 8
        }
      ]
    }
            response['search'] = search
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)
"""


class SearchAPI(APIView):
    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

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
            print((json.dumps(content, indent=4, sort_keys=True)))
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
            #print "Error: "+str(e)
            return 0

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SearchAPI: %s", str(data))
            query_string_name = data.get("name", "")
            query_string_category = data.get("category", "")
            query_string_brand = data.get("brand", "geepas")
            search = {}
            if query_string_name == '':
                response['status'] = 404
                return Response(data=response)
            products_by_category = Product.objects.filter(base_product__brand__name=query_string_brand)
            if query_string_category!="ALL":
                query_string_category = query_string_category.replace("-", " ")
                products_by_category = products_by_category.filter(base_product__category__icontains = query_string_category)
            products_by_name = products_by_category.filter(product_name__icontains=query_string_name)
            products = []
            filters = []
            logger.info("products by category %s", str(products_by_category))
            logger.info("products by name %s", str(products_by_name))
            for product in products_by_name:
                if DealsHubProduct.objects.filter(product=product, is_published=True).exists()==False:
                    continue
                temp_dict = {}
                temp_dict["name"] = product.product_name
                temp_dict["brand"] = str(product.base_product.brand)
                temp_dict["price"] = self.fetch_price(product.base_product.seller_sku)
                temp_dict["prevPrice"] = self.fetch_price(product.base_product.seller_sku)
                temp_dict["currency"] = "AED"
                temp_dict["discount"] = "10%"
                temp_dict["rating"] = "4.5"
                temp_dict["totalRatings"] = "453"
                temp_dict["uuid"] = product.uuid
                temp_dict["id"] = product.uuid
                
                main_images_list = ImageBucket.objects.none()
                main_images_objs = MainImages.objects.filter(product=product)
                for main_images_obj in main_images_objs:
                    main_images_list |= main_images_obj.main_images.all()
                main_images_list = main_images_list.distinct()
                if main_images_list.filter(is_main_image=True).count() > 0:
                    try:
                        temp_dict["heroImageUrl"] = main_images_list.filter(is_main_image=True)[
                            0].image.thumbnail.url
                    except Exception as e:
                       temp_dict["heroImageUrl"] = Config.objects.all()[
                            0].product_404_image.image.url
                else:
                    temp_dict["heroImageUrl"] = Config.objects.all()[
                        0].product_404_image.image.url
               
                dealshub_product = DealsHubProduct.objects.get(product=product)
                category = dealshub_product.category
                if category!=None:
                    sub_categories = category.sub_categories.all()
                    for sub_category in sub_categories:
                        temp_dict_filter = {}
                        temp_dict_filter["id"] = sub_category.pk
                        temp_dict_filter["name"] = sub_category.name
                        temp_dict_filter["values"] = []
                        properties = sub_category.properties.all()
                        for prop in properties:
                            if prop.label in temp_dict_filter["values"]:
                                temp_dict_filter["values"].append(prop.label)
                        if sub_category.pk not in [x["id"] for x in filters ]:
                            filters.append(temp_dict_filter)
                if main_images_list.filter(is_main_image=True).count() > 0:
                    products.append(temp_dict)
            """
            dealshub_product = DealsHubProduct.objects.get(product=product)
            category = dealshub_product.category
            if category!=None:
                sub_categories = category.sub_categories.all()
                for sub_category in sub_categories:
                    temp_dict_filter = {}
                    temp_dict_filter["id"] = sub_category.pk
                    temp_dict_filter["name"] = sub_category.name
                    temp_dict_filter["values"] = []
                    properties = sub_category.properties.all()
                    for prop in properties:
                        temp_dict_filter["values"].append(prop.label)
                    filters.append(temp_dict_filter)
            """
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


# class AddProductAPI(APIView):
#     authentication_classes = (
#         CsrfExemptSessionAuthentication, BasicAuthentication)

#     def post(self, request, *args, **kwargs):

#         response['status'] = 500
#         try:

#             # if request.user.has_perm('WAMSApp.change_product') == False:
#             #     logger.warning("SaveProductAPI Restricted Access!")
#             #     response['status'] = 403
#             #     return Response(data=response)

#             data = request.data
#             logger.info("AddProductAPI: %s", str(data))

#             if not isinstance(data, dict):
#                 data = json.loads(data)

#             # Check for duplicate
#             product_id = data["product_id"]

#             product_obj = Product.objects.get(pk=int(data["product_pk"]))

#             # Checking brand permission
#             try:
#                 permissible_brands = custom_permission_filter_brands(
#                     request.user)
#                 brand_obj = Brand.objects.get(
#                     name=product_obj.base_product.brand.name)
#                 if brand_obj not in permissible_brands:
#                     logger.warning("SaveProductAPI Restricted Access Brand!")
#                     response['status'] = 403
#                     return Response(data=response)
#             except Exception as e:
#                 logger.error("SaveProductAPI Restricted Access Brand!")
#                 response['status'] = 403
#                 return Response(data=response)

#             if Product.objects.filter(product_id=product_id).exclude(pk=data["product_pk"]).count() >= 1:
#                 logger.warning("Duplicate product detected!")
#                 response['status'] = 409
#                 return Response(data=response)

#             product_name = convert_to_ascii(data["product_name"])
#             barcode_string = convert_to_ascii(data["barcode_string"])
#             color = convert_to_ascii(data["color"])
#             color_map = convert_to_ascii(data["color_map"])
#             standard_price = None if data["standard_price"] == "" else float(
#                 data["standard_price"])
#             quantity = None if data["quantity"] == "" else int(
#                 data["quantity"])

#             product_id_type = convert_to_ascii(data["product_id_type"])
#             product_id_type_obj, created = ProductIDType.objects.get_or_create(
#                 name=product_id_type)

#             material_type = convert_to_ascii(data["material_type"])
#             material_type_obj, created = MaterialType.objects.get_or_create(
#                 name=material_type)

#             pfl_product_name = convert_to_ascii(data["pfl_product_name"])
#             pfl_product_features = convert_to_ascii(
#                 data["pfl_product_features"])

#             factory_notes = convert_to_ascii(data["factory_notes"])

#             product_obj.product_id = product_id

#             try:
#                 if product_obj.barcode_string != barcode_string and barcode_string != "":
#                     EAN = barcode.ean.EuropeanArticleNumber13(
#                         str(barcode_string), writer=ImageWriter())

#                     thumb = EAN.save('temp_image')
#                     thumb = IMage.open(open(thumb, "rb"))
#                     thumb_io = StringIO.StringIO()
#                     thumb.save(thumb_io, format='PNG')
#                     thumb_file = InMemoryUploadedFile(
#                         thumb_io, None, 'barcode_' + product_obj.product_id + '.png', 'image/PNG', thumb_io.len, None)

#                     barcode_image = Image.objects.create(image=thumb_file)
#                     product_obj.barcode = barcode_image
#                     product_obj.barcode_string = barcode_string

#                     try:
#                         import os
#                         os.remove("temp_image.png")
#                     except Exception as e:
#                         exc_type, exc_obj, exc_tb = sys.exc_info()
#                         logger.warning("AddProductAPI: %s at %s",
#                                        e, str(exc_tb.tb_lineno))

#             except Exception as e:
#                 exc_type, exc_obj, exc_tb = sys.exc_info()
#                 logger.error("AddProductAPI: %s at %s",
#                              e, str(exc_tb.tb_lineno))

#             product_obj.product_name = product_name

#             product_obj.product_id_type = product_id_type_obj
#             product_obj.color_map = color_map
#             product_obj.color = color

#             product_obj.material_type = material_type_obj
#             product_obj.standard_price = standard_price
#             product_obj.quantity = quantity

#             product_obj.pfl_product_name = pfl_product_name
#             product_obj.pfl_product_features = pfl_product_features

#             product_obj.factory_notes = factory_notes

#             product_obj.save()

#             response['status'] = 200


# AddProduct = AddProductAPI.as_view()


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

            data = data["sectionData"]

            for key in data:
                logger.info("CreateAdminCategoryAPI KEY: %s", str(key))

            name = data["name"]
            listing_type = data["listingType"]
            products = data["products"]
            
            section_obj = Section.objects.create(uuid=str(uuid.uuid4()), name=name, listing_type=listing_type)
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

    def get(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchAdminCategoriesAPI: %s", str(data))

            section_objs = Section.objects.all()

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
            logger.info("DeleteAdminCategoryAPI: %s", str(data))

            uuid = data["uuid"]
            
            section_obj = Section.objects.get(uuid=uuid)
            section_obj.is_published = True
            section_obj.save()
            
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteAdminCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))
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


class FetchBrandsCarouselAPI(APIView):
    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchBrandsCarouselAPI: %s", str(data))

            brands_carousel = [
                {
                  "id": "1",
                  "name": "geepas",
                  "heroImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/geepas-logo.png"
                },
                {
                  "id": "2",
                  "name": "krypton",
                  "heroImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/krypton-logo.png"
                },
                {
                  "id": "3",
                  "name": "olsenmark",
                  "heroImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/olsenmark-logo.png"
                },
                {
                  "id": "4",
                  "name": "geepas",
                  "heroImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/geepas-logo.png"
                },
                {
                  "id": "5",
                  "name": "krypton",
                  "heroImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/krypton-logo.png"
                },
                {
                  "id": "6",
                  "name": "olsenmark",
                  "heroImageUrl": "https://wig-wams-s3-bucket.s3.amazonaws.com/olsenmark-logo.png"
                }]

            response['brands_carousel'] = brands_carousel

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchBrandsCarouselAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
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



class CreateDealsBannerAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("CreateDealsBannerAPI: %s", str(data))

            image = data["image"]

            if image=="" or image=="undefined" or image==None:
                return Response(data=response)

            image_obj = Image.objects.create(image=image)

            deals_banner_obj = DealsBanner.objects.create(image=image_obj, uuid=str(uuid.uuid4()))
            
            response['uuid'] = deals_banner_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateDealsBannerAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchDealsBannerAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchDealsBannerAPI: %s", str(data))

            resolution = data["resolution"]

            deals_banner_objs = DealsBanner.objects.all()

            banner_deals = []

            for deals_banner_obj in deals_banner_objs:
                try:
                    temp_dict = {}
                    temp_dict["uid"] = deals_banner_obj.uuid
                    temp_dict["isPublished"] = deals_banner_obj.is_published
                    if deals_banner_obj.image!=None:
                        if resolution=="low":
                            temp_dict["url"] = deals_banner_obj.image.thumbnail.url
                        else:
                            temp_dict["url"] = deals_banner_obj.image.image.url
                    else:
                        temp_dict["url"] = ""
                    banner_deals.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchDealsBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
            
            response['banner_deals'] = banner_deals
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchDealsBannerAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class DeleteDealsBannerAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteDealsBannerAPI: %s", str(data))

            uuid = data["uuid"]
            DealsBanner.objects.get(uuid=uuid).delete()
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteDealsBannerAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class PublishDealsBannerAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("PublishDealsBannerAPI: %s", str(data))

            uuid = data["uuid"]
            deals_banner_obj = DealsBanner.objects.get(uuid=uuid)
            deals_banner_obj.is_published = True
            deals_banner_obj.save()
            
            response['uuid'] = deals_banner_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PublishDealsBannerAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UnPublishDealsBannerAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UnPublishDealsBannerAPI: %s", str(data))

            uuid = data["uuid"]
            deals_banner_obj = DealsBanner.objects.get(uuid=uuid)
            deals_banner_obj.is_published = False
            deals_banner_obj.save()
            
            response['uuid'] = deals_banner_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UnPublishDealsBannerAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)



class CreateFullBannerAdAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("CreateFullBannerAdAPI: %s", str(data))

            image = data["image"]

            image_obj = Image.objects.create(image=image)

            full_banner_ad_obj = FullBannerAd.objects.create(image=image_obj, uuid=str(uuid.uuid4()))
            
            response['uuid'] = full_banner_ad_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateFullBannerAdAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchFullBannerAdAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchFullBannerAdAPI: %s", str(data))

            full_banner_ad_objs = FullBannerAd.objects.all()

            banner_deals = []

            for full_banner_ad_obj in full_banner_ad_objs:
                temp_dict = {}
                temp_dict["uid"] = full_banner_ad_obj.uuid
                temp_dict["isPublished"] = full_banner_ad_obj.is_published
                if full_banner_ad_obj.image!=None:
                    temp_dict["url"] = full_banner_ad_obj.image.image.url
                else:
                    temp_dict["url"] = ""
                banner_deals.append(temp_dict)
            
            response['full_banner_ads'] = banner_deals
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchDealsBannerAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class DeleteFullBannerAdAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteFullBannerAdAPI: %s", str(data))

            uuid = data["uuid"]
            FullBannerAd.objects.get(uuid=uuid).delete()
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteFullBannerAdAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class PublishFullBannerAdAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("PublishFullBannerAdAPI: %s", str(data))

            uuid = data["uuid"]
            full_banner_ad_obj = FullBannerAd.objects.get(uuid=uuid)
            full_banner_ad_obj.is_published = True
            full_banner_ad_obj.save()
            
            response['uuid'] = full_banner_ad_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PublishFullBannerAdAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UnPublishFullBannerAdAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UnPublishFullBannerAdAPI: %s", str(data))

            uuid = data["uuid"]
            full_banner_ad_obj = FullBannerAd.objects.get(uuid=uuid)
            full_banner_ad_obj.is_published = False
            full_banner_ad_obj.save()
            
            response['uuid'] = full_banner_ad_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UnPublishFullBannerAdAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class CreateDealsHubProductAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("CreateDealsHubProductAPI: %s", str(data))
            product_pk = data["product_pk"]
            product_obj = Product.objects.get(pk=product_pk)
            product_obj.is_dealshub_product_created = True
            product_obj.save()
            if(DealsHubProduct.objects.filter(product=product_obj).exists()==False):
                DealsHubProduct.objects.create(product=product_obj)
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateDealsHubProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class PublishDealsHubProductAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]
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
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]
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


class CreateCategoryGridBannerAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("CreateCategoryGridBannerAPI: %s", str(data))

            image = data["image"]

            if image=="" or image=="undefined" or image==None:
                return Response(data=response)

            image_obj = Image.objects.create(image=image)

            category_grid_banner_obj = CategoryGridBanner.objects.create(image=image_obj, uuid=str(uuid.uuid4()))
            
            response['uuid'] = category_grid_banner_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateCategoryGridBannerAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchCategoryGridBannerAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchCategoryGridBannerAPI: %s", str(data))

            resolution = data.get("resolution", "low")

            category_grid_banner_objs = CategoryGridBanner.objects.all()

            category_grid_banners = []

            for category_grid_banner_obj in category_grid_banner_objs:
                try:
                    temp_dict = {}
                    temp_dict["uid"] = category_grid_banner_obj.uuid
                    temp_dict["isPublished"] = category_grid_banner_obj.is_published
                    if category_grid_banner_obj.image!=None:
                        if resolution=="low":
                            temp_dict["url"] = category_grid_banner_obj.image.thumbnail.url
                        else:
                            temp_dict["url"] = category_grid_banner_obj.image.image.url
                    else:
                        temp_dict["url"] = ""
                    category_grid_banners.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchCategoryGridBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
            
            response['category_grid_banners'] = category_grid_banners
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCategoryGridBannerAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class DeleteCategoryGridBannerAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteCategoryGridBannerAPI: %s", str(data))

            uuid = data["uuid"]
            CategoryGridBanner.objects.get(uuid=uuid).delete()
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteCategoryGridBannerAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)



class DeleteProductFromSectionAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

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




class CreateHomePageSchedularAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("CreateHomePageSchedularAPI: %s", str(data))

            image = data["image"]

            if image=="" or image=="undefined" or image==None:
                return Response(data=response)

            image_obj = Image.objects.create(image=image)

            home_page_schedular_obj = HomePageSchedular.objects.create(image=image_obj, uuid=str(uuid.uuid4()))
            
            response['uuid'] = home_page_schedular_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateHomePageSchedularAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchHomePageSchedularAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchHomePageSchedularAPI: %s", str(data))

            resolution = data.get("resolution", "low")

            home_page_schedular_objs = HomePageSchedular.objects.all()

            home_page_schedulars = []

            for home_page_schedular_obj in home_page_schedular_objs:
                try:
                    temp_dict = {}
                    temp_dict["uid"] = home_page_schedular_obj.uuid
                    temp_dict["isPublished"] = home_page_schedular_obj.is_published
                    if home_page_schedular_obj.image!=None:
                        if resolution=="low":
                            temp_dict["url"] = home_page_schedular_obj.image.thumbnail.url
                        else:
                            temp_dict["url"] = home_page_schedular_obj.image.image.url
                    else:
                        temp_dict["url"] = ""
                    home_page_schedulars.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchHomePageSchedularAPI: %s at %s", e, str(exc_tb.tb_lineno))
            
            response['home_page_schedulars'] = home_page_schedulars
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchHomePageSchedularAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class DeleteHomePageSchedularAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteHomePageSchedularAPI: %s", str(data))

            uuid = data["uuid"]
            HomePageSchedular.objects.get(uuid=uuid).delete()
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteHomePageSchedularAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)













CreateAdminCategory = CreateAdminCategoryAPI.as_view()

FetchAdminCategories = FetchAdminCategoriesAPI.as_view()

UpdateAdminCategory = UpdateAdminCategoryAPI.as_view()

DeleteAdminCategory = DeleteAdminCategoryAPI.as_view()

PublishAdminCategory = PublishAdminCategoryAPI.as_view()

UnPublishAdminCategory = UnPublishAdminCategoryAPI.as_view()

FetchBrandsCarousel = FetchBrandsCarouselAPI.as_view()

SectionBulkUpload = SectionBulkUploadAPI.as_view()

CreateDealsBanner = CreateDealsBannerAPI.as_view()

FetchDealsBanner = FetchDealsBannerAPI.as_view()

DeleteDealsBanner = DeleteDealsBannerAPI.as_view()

PublishDealsBanner = PublishDealsBannerAPI.as_view()

UnPublishDealsBanner = UnPublishDealsBannerAPI.as_view()


CreateFullBannerAd = CreateFullBannerAdAPI.as_view()

FetchFullBannerAd = FetchFullBannerAdAPI.as_view()

DeleteFullBannerAd = DeleteFullBannerAdAPI.as_view()

PublishFullBannerAd = PublishFullBannerAdAPI.as_view()

UnPublishFullBannerAd = UnPublishFullBannerAdAPI.as_view()

CreateDealsHubProduct = CreateDealsHubProductAPI.as_view()

PublishDealsHubProduct = PublishDealsHubProductAPI.as_view()

UnPublishDealsHubProduct = UnPublishDealsHubProductAPI.as_view()

CreateCategoryGridBanner = CreateCategoryGridBannerAPI.as_view()

FetchCategoryGridBanner = FetchCategoryGridBannerAPI.as_view()

DeleteCategoryGridBanner = DeleteCategoryGridBannerAPI.as_view()

DeleteProductFromSection = DeleteProductFromSectionAPI.as_view()

CreateHomePageSchedular = CreateHomePageSchedularAPI.as_view()

FetchHomePageSchedular = FetchHomePageSchedularAPI.as_view()

DeleteHomePageSchedular = DeleteHomePageSchedularAPI.as_view()