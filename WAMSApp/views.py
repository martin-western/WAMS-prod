from auditlog.models import *
from dealshub.models import *
from WAMSApp.models import *
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
from WAMSApp.views_noon import *
from WAMSApp.views_amazon_uae import *
from WAMSApp.views_amazon_uk import *
from WAMSApp.views_noon_integration import *
from WAMSApp.views_statistics import *
from WAMSApp.oc_reports import *
from WAMSApp.views_category_manager import *
from WAMSApp.views_SAP_Integration import *
from WAMSApp.utils_SAP_Integration import *
from WAMSApp.views_nesto import *

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

#@login_required(login_url='/login/')
def FlyerPage(request, pk):
    flyer_obj = Flyer.objects.get(pk=int(pk))
    return render(request, 'WAMSApp/flyer.html')
    # if flyer_obj.mode=="A4 Portrait":
    #     return render(request, 'WAMSApp/flyer.html')
    # elif flyer_obj.mode=="A4 Landscape":
    #     return render(request, 'WAMSApp/flyer-landscape.html')
    # elif flyer_obj.mode=="A5 Portrait":
    #     return render(request, 'WAMSApp/flyer-a5-portrait.html')
    # elif flyer_obj.mode=="A5 Landscape":
    #     return render(request, 'WAMSApp/flyer-a5-landscape.html')


class GithubWebhookAPI(APIView):

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("GithubWebhookAPI: %s", str(data))

            ref = str(data["ref"])
            branch = ref.split("/")[2:]
            branch = ''.join(branch)
            if(branch == "uat"):
                os.system("git pull origin uat")
                os.system("sudo systemctl restart gunicorn-5")
                os.system("sudo systemctl restart gunicorn-6")
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("GithubWebhookAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CreateNewBaseProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            if request.user.has_perm('WAMSApp.add_product') == False:
                logger.warning("CreateNewBaseProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("CreateNewBaseProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_name = convert_to_ascii(data["base_product_name"])
            seller_sku = convert_to_ascii(data["seller_sku"])
            brand_name = convert_to_ascii(data["brand_name"])
            manufacturer = convert_to_ascii(data["manufacturer"])
            manufacturer_part_number = convert_to_ascii(data["manufacturer_part_number"])
            base_dimensions = json.dumps(data["base_dimensions"])
            category_uuid = data["category_uuid"]
            sub_category_uuid = data["sub_category_uuid"]

            # Checking brand permission
            brand_obj = None
            organization_obj = CustomPermission.objects.get(user__username=request.user.username).organization
            try:
                permissible_brands = custom_permission_filter_brands(request.user)
                if Brand.objects.filter(name=brand_name, organization=organization_obj).exists()==True:
                    brand_obj = Brand.objects.get(name=brand_name, organization=organization_obj)
                    if brand_obj not in permissible_brands:
                        logger.warning("CreateNewBaseProductAPI Restricted Access Brand!")
                        response['status'] = 403
                        return Response(data=response)
                else:
                    custom_permission_obj = CustomPermission.objects.get(user__username=request.user.username)
                    brand_obj = Brand.objects.create(name=brand_name, organization=organization_obj)
                    custom_permission_obj.brands.add(brand_obj)
                    custom_permission_obj.save()
            except Exception as e:
                logger.error("CreateNewBaseProductAPI Restricted Access Brand!")
                response['status'] = 403
                return Response(data=response)
                

            if BaseProduct.objects.filter(seller_sku=seller_sku, brand=brand_obj).exists():
                
                logger.warning("CreateNewBaseProductAPI Duplicate product detected!")
                response["status"] = 409
                return Response(data=response)

            category_obj = None
            try:
                category_obj = Category.objects.get(uuid=category_uuid)
            except Exception as e:
                pass
            sub_category_obj = None
            try:
                sub_category_obj = SubCategory.objects.get(uuid=sub_category_uuid)
            except Exception as e:
                pass

            base_product_obj = BaseProduct.objects.create(base_product_name=product_name,
                                              seller_sku=seller_sku,
                                              brand=brand_obj,
                                              category=category_obj,
                                              sub_category=sub_category_obj,
                                              manufacturer=manufacturer,
                                              manufacturer_part_number=manufacturer_part_number,
                                              dimensions=base_dimensions)

            dynamic_form_attributes = {}
            
            try:
                property_data = json.loads(category_obj.property_data)
                for prop_data in property_data:
                    dynamic_form_attributes[prop_data["key"]] = {
                        "type": "dropdown",
                        "labelText": prop_data["key"].title(),
                        "value": "",
                        "options": prop_data["values"]
                    }
            except Exception as e:
                pass

            product_obj = Product.objects.create(product_name=product_name, base_product=base_product_obj, dynamic_form_attributes=json.dumps(dynamic_form_attributes))


            location_group_objs = LocationGroup.objects.filter(website_group__brands__in=[brand_obj])
            for location_group_obj in location_group_objs:
                DealsHubProduct.objects.create(product_name=product_obj.product_name, product=product_obj, location_group=location_group_obj, category=base_product_obj.category, sub_category=base_product_obj.sub_category)

            response["product_pk"] = product_obj.pk
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateNewBaseProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CreateNewProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            if request.user.has_perm('WAMSApp.add_product') == False:
                logger.warning("CreateNewProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("CreateNewProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            base_product_obj = BaseProduct.objects.get(pk=data["base_product_pk"])
            
            # Checking brand permission
            brand_obj = None
            
            try:
                permissible_brands = custom_permission_filter_brands(
                    request.user)
                brand_obj = base_product_obj.brand

                if brand_obj not in permissible_brands:
                    logger.warning(
                        "CreateNewProductAPI Restricted Access Brand!")
                    response['status'] = 403
                    return Response(data=response)
            except Exception as e:
                logger.error("CreateNewProductAPI Restricted Access Brand!")
                response['status'] = 403
                return Response(data=response)

            product_name = base_product_obj.base_product_name

            dynamic_form_attributes = {}
            try:
                property_data = json.loads(base_product_obj.category.property_data)
                for prop_data in property_data:
                    dynamic_form_attributes[prop_data["key"]] = {
                        "type": "dropdown",
                        "labelText": prop_data["key"].title(),
                        "value": "",
                        "options": prop_data["values"]
                    }
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("CreateNewProductAPI: %s at %s", e, str(exc_tb.tb_lineno))          

            product_obj = Product.objects.create(product_name = product_name,
                                            product_name_sap=product_name,
                                            pfl_product_name=product_name,
                                            base_product=base_product_obj,
                                            dynamic_form_attributes=json.dumps(dynamic_form_attributes))

            location_group_objs = LocationGroup.objects.filter(website_group__brands__in=[brand_obj])
            for location_group_obj in location_group_objs:
                DealsHubProduct.objects.create(product_name=product_obj.product_name, product=product_obj, location_group=location_group_obj, category=base_product_obj.category, sub_category=base_product_obj.sub_category)

            response["product_pk"] = product_obj.pk
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateNewProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveNoonChannelProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            if request.user.has_perm('WAMSApp.add_product') == False:
                logger.warning("SaveNoonChannelProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("SaveNoonChannelProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            channel_name = "Noon"
            product_obj = Product.objects.get(pk=data["product_pk"])
            base_product_obj = product_obj.base_product
            brand_obj = base_product_obj.brand

            permissible_brands = custom_permission_filter_brands(request.user)

            if brand_obj not in permissible_brands:
                logger.warning("SaveNoonChannelProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            try:
                permissible_channels = custom_permission_filter_channels(request.user)
                channel_obj = Channel.objects.get(name=channel_name)

                if channel_obj not in permissible_channels:
                    logger.warning(
                        "SaveNoonChannelProductAPI Restricted Access of Noon Channel!")
                    response['status'] = 403
                    return Response(data=response)
            
            except Exception as e:
                logger.error("SaveNoonChannelProductAPI Restricted Access of Noon Channel!")
                response['status'] = 403
                return Response(data=response)

            noon_product_json = json.loads(data["noon_product_json"])
            if(noon_product_json["created_date"]==""):
                noon_product_json["created_date"] = datetime.datetime.now().strftime("%d %b, %Y")

            channel_product = product_obj.channel_product
            channel_product.noon_product_json = json.dumps(noon_product_json)
            channel_product.is_noon_product_created = True
            channel_product.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveNoonChannelProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveAmazonUKChannelProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:
            
            if request.user.has_perm('WAMSApp.add_product') == False:
                logger.warning("SaveAmazonUKChannelProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("SaveAmazonUKChannelProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            channel_name = "Amazon UK"
            product_obj = Product.objects.get(pk=data["product_pk"])
            base_product_obj = product_obj.base_product
            brand_obj = base_product_obj.brand

            permissible_brands = custom_permission_filter_brands(request.user)

            if brand_obj not in permissible_brands:
                logger.warning("SaveAmazonUKChannelProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            try:
                permissible_channels = custom_permission_filter_channels(request.user)
                channel_obj = Channel.objects.get(name=channel_name)

                if channel_obj not in permissible_channels:
                    logger.warning("SaveAmazonUKChannelProductAPI Restricted Access of Amazon UK Channel!")
                    response['status'] = 403
                    return Response(data=response)
            
            except Exception as e:
                logger.error("SaveAmazonUKChannelProductAPI Restricted Access of Amazon UK Channel!")
                response['status'] = 403
                return Response(data=response)

            amazon_uk_product_json = json.loads(data["amazon_uk_product_json"])
            if(amazon_uk_product_json["created_date"]==""):
                amazon_uk_product_json["created_date"] = datetime.datetime.now().strftime("%d %b, %Y")

            channel_product = product_obj.channel_product

            channel_product.amazon_uk_product_json = json.dumps(amazon_uk_product_json)
            channel_product.is_amazon_uk_product_created = True
            channel_product.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveAmazonUKChannelProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveAmazonUAEChannelProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            if request.user.has_perm('WAMSApp.add_product') == False:
                logger.warning("SaveAmazonUAEChannelProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("SaveAmazonUAEChannelProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            channel_name = "Amazon UAE"
            product_obj = Product.objects.get(pk=data["product_pk"])
            base_product_obj = product_obj.base_product
            brand_obj = base_product_obj.brand

            permissible_brands = custom_permission_filter_brands(request.user)

            if brand_obj not in permissible_brands:
                logger.warning("SaveAmazonUAEChannelProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            try:
                permissible_channels = custom_permission_filter_channels(
                    request.user)
                channel_obj = Channel.objects.get(name=channel_name)

                if channel_obj not in permissible_channels:
                    logger.warning("SaveAmazonUAEChannelProductAPI Restricted Access of Amazon UAE Channel!")
                    response['status'] = 403
                    return Response(data=response)
            
            except Exception as e:
                logger.error("SaveAmazonUAEChannelProductAPI Restricted Access of Amazon UAE Channel!")
                response['status'] = 403
                return Response(data=response)

            amazon_uae_product_json = json.loads(data["amazon_uae_product_json"])
            if(amazon_uae_product_json["created_date"]==""):
                amazon_uae_product_json["created_date"] = datetime.datetime.now().strftime("%d %b, %Y")

            channel_product = product_obj.channel_product
            
            channel_product.amazon_uae_product_json = json.dumps(amazon_uae_product_json)
            channel_product.is_amazon_uae_product_created = True
            channel_product.save()
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveAmazonUAEChannelProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveEbayChannelProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            if request.user.has_perm('WAMSApp.add_product') == False:
                logger.warning("SaveEbayChannelProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("SaveEbayChannelProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            channel_name = "Ebay"
            product_obj = Product.objects.get(pk=data["product_pk"])
            base_product_obj = product_obj.base_product
            brand_obj = base_product_obj.brand

            permissible_brands = custom_permission_filter_brands(request.user)

            if brand_obj not in permissible_brands:
                logger.warning("SaveEbayChannelProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            try:
                permissible_channels = custom_permission_filter_channels(request.user)
                channel_obj = Channel.objects.get(name=channel_name)

                if channel_obj not in permissible_channels:
                    logger.warning("SaveEbayChannelProductAPI Restricted Access of Ebay Channel!")
                    response['status'] = 403
                    return Response(data=response)
            
            except Exception as e:
                logger.error("SaveEbayChannelProductAPI Restricted Access of Ebay Channel!")
                response['status'] = 403
                return Response(data=response)

            ebay_product_json = json.loads(data["ebay_product_json"])
            if(ebay_product_json["created_date"]==""):
                ebay_product_json["created_date"] = datetime.datetime.now().strftime("%d %b, %Y")

            channel_product = product_obj.channel_product
            
            channel_product.ebay_product_json = json.dumps(ebay_product_json)
            channel_product.is_ebay_product_created = True
            channel_product.save()
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveEbayChannelProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchChannelProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response["status"] = 500

        try:

            data = request.data

            if not isinstance(data, dict):
                data = json.loads(data)

            logger.info("FetchChannelProductAPI: %s", str(data))

            channel_name = data["channel_name"]

            product_obj = Product.objects.get(pk=data["product_pk"])
            channel_product_obj = product_obj.channel_product
            base_product_obj = product_obj.base_product
            brand_obj = base_product_obj.brand

            permissible_brands = custom_permission_filter_brands(request.user)

            if brand_obj not in permissible_brands:
                logger.warning("FetchChannelProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            channel_obj = Channel.objects.get(name=channel_name)
            channel_product_dict = get_channel_product_dict(channel_name,channel_product_obj)

            try:
                permissible_channels = custom_permission_filter_channels(request.user)
                
                if channel_obj not in permissible_channels:
                    logger.warning("Fetch"+channel_name.replace(" ","")+"ChannelProductAPI Restricted Access of "+channel_name+" Channel!")
                    response['status'] = 403
                    return Response(data=response)
            
            except Exception as e:
                logger.warning("Fetch"+channel_name.replace(" ","")+"ChannelProductAPI Restricted Access of "+channel_name+" Channel!")
                response['status'] = 403
                return Response(data=response)

            images = {}

            main_images_list = ImageBucket.objects.none()
            try:
                main_images_obj = MainImages.objects.get(product=product_obj,channel=channel_obj)
                main_images_list=main_images_obj.main_images.all()
                main_images_list = main_images_list.distinct()
                images["main_images"] = create_response_images_main(main_images_list)
            except Exception as e:
                images["main_images"] = []
                pass


            sub_images_list = ImageBucket.objects.none()
            try:
                sub_images_obj = SubImages.objects.get(product=product_obj,channel=channel_obj)
                sub_images_list = sub_images_obj.sub_images.all()
                sub_images_list = sub_images_list.distinct()
                images["sub_images"] = create_response_images_sub(sub_images_list)
            except Exception as e:
                images["sub_images"] = []
                pass


            images["all_images"] = create_response_images_main_sub_delete(main_images_list) \
                                    + create_response_images_main_sub_delete(sub_images_list)

            repr_image_url = Config.objects.all()[0].product_404_image.image.url
            repr_high_def_url = repr_image_url
            
            if main_images_list.filter(is_main_image=True).count() > 0:
                try:
                    repr_image_url = main_images_list.filter(
                        is_main_image=True)[0].image.mid_image.url
                except Exception as e:
                    repr_image_url = main_images_list.filter(is_main_image=True)[0].image.image.url

                repr_high_def_url = main_images_list.filter(is_main_image=True)[0].image.image.url

            response["repr_image_url"] = repr_image_url
            response["repr_high_def_url"] = repr_high_def_url

            response["images"] = images

            response["channel_product_json"] = channel_product_dict

            response["product_id"] = product_obj.product_id
            response["barcode"] = product_obj.barcode_string
            response["product_id_type"] = ""
            response["material_type"] = ""
            
            if product_obj.product_id_type != None:
                response["product_id_type"] = product_obj.product_id_type.name
            response['status'] = 200

            if product_obj.material_type != None:
                response["material_type"] = product_obj.material_type.name
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchChannelProductAPI: %s at %s",
                             e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchBaseProductDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("FetchBaseProductDetailsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            base_product_obj = BaseProduct.objects.get(pk=data["base_product_pk"])
            brand_obj = base_product_obj.brand

            permissible_brands = custom_permission_filter_brands(request.user)

            if brand_obj not in permissible_brands:
                logger.warning("FetchBaseProductDetailsAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            if brand_obj == None:
                response["brand_name"] = ""
            else:
                response["brand_name"] = brand_obj.name
            
            response["base_product_name"] = base_product_obj.base_product_name
            response["super_category"] = "" if base_product_obj.category==None else str(base_product_obj.category.super_category)
            response["category"] = "" if base_product_obj.category==None else str(base_product_obj.category)
            response["sub_category"] = "" if base_product_obj.sub_category==None else str(base_product_obj.sub_category)
            response["super_category_uuid"] = "" if base_product_obj.category==None else str(base_product_obj.category.super_category.uuid)
            response["category_uuid"] = "" if base_product_obj.category==None else str(base_product_obj.category.uuid)
            response["sub_category_uuid"] = "" if base_product_obj.sub_category==None else str(base_product_obj.sub_category.uuid)
            response["seller_sku"] = base_product_obj.seller_sku
            response["manufacturer_part_number"] = base_product_obj.manufacturer_part_number
            response["manufacturer"] = base_product_obj.manufacturer
            response["base_dimensions"] = json.loads(base_product_obj.dimensions)

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchBaseProductDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchProductDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("FetchProductDetailsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_obj = Product.objects.get(pk=data["product_pk"])
            base_product_obj = product_obj.base_product
            channel_product_obj = product_obj.channel_product
            noon_product_dict = json.loads(channel_product_obj.noon_product_json)
            amazon_uk_product_dict = json.loads(channel_product_obj.amazon_uk_product_json)
            amazon_uae_product_dict = json.loads(channel_product_obj.amazon_uae_product_json)
            ebay_product_dict = json.loads(channel_product_obj.ebay_product_json)
            brand_obj = base_product_obj.brand
            faqs = json.loads(product_obj.faqs)
            how_to_use = json.loads(product_obj.how_to_use)

            permissible_brands = custom_permission_filter_brands(request.user)

            if brand_obj not in permissible_brands:
                logger.warning("FetchProductDetails Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            response["pfl_product_name"] = product_obj.pfl_product_name
            try:
                response["pfl_product_features"] = json.loads(
                    product_obj.pfl_product_features)
            except Exception as e:
                response["pfl_product_features"] = []

            try:
                response["pfl_product_features_ar"] = json.loads(
                    product_obj.pfl_product_features_ar)
            except Exception as e:
                response["pfl_product_features_ar"] = []

            try:
                response["brand_logo"] = brand_obj.logo.image.url
            except Exception as e:
                response["brand_logo"] = ''
            
            if brand_obj == None:
                response["brand_name"] = ""
                response["brand_name_ar"] = ""
            else:
                response["brand_name"] = brand_obj.name
                response["brand_name_ar"] = brand_obj.name_ar
            
            response["base_product_name"] = base_product_obj.base_product_name
            response["super_category"] = "" if base_product_obj.category==None else str(base_product_obj.category.super_category)
            response["category"] = "" if base_product_obj.category==None else str(base_product_obj.category)
            response["sub_category"] = "" if base_product_obj.sub_category==None else str(base_product_obj.sub_category)
            response["super_category_uuid"] = "" if base_product_obj.category.super_category==None else str(base_product_obj.category.super_category.uuid)
            response["category_uuid"] = "" if base_product_obj.category==None else str(base_product_obj.category.uuid)
            response["sub_category_uuid"] = "" if base_product_obj.sub_category==None else str(base_product_obj.sub_category.uuid)

            response["seller_sku"] = base_product_obj.seller_sku
            response["manufacturer_part_number"] = base_product_obj.manufacturer_part_number
            response["manufacturer"] = base_product_obj.manufacturer
            response["base_dimensions"] = json.loads(base_product_obj.dimensions)

            response["product_name"] = product_obj.product_name
            response["product_description"] = product_obj.product_description
            response["product_name_sap"] = product_obj.product_name_sap
            response["product_id"] = product_obj.product_id
            response["barcode_string"] = product_obj.barcode_string
            response["standard_price"] = "" if product_obj.standard_price == None else product_obj.standard_price
            response["quantity"] = "" if product_obj.quantity == None else product_obj.quantity
            response["factory_notes"] = product_obj.factory_notes
            try:
                response["factory_code"] = product_obj.factory.factory_code
            except Exception as e:
                response["factory_code"] = ""
            response["verified"] = product_obj.verified
            response["locked"] = product_obj.locked
            response["partially_verified"] = product_obj.partially_verified
            response["color_map"] = product_obj.color_map
            response["color"] = product_obj.color
            response["weight"] = product_obj.weight
            response["dimensions"] = product_obj.get_dimensions()
            response["size"] = "NA" if str(product_obj.size)=="" else str(product_obj.size + product_obj.size_unit)
            response["capacity"] = "NA" if str(product_obj.capacity)=="" else str(product_obj.capacity + product_obj.capacity_unit)
            response["target_age_range"] = str(product_obj.target_age_range)

            response["min_price"] = product_obj.min_price
            response["max_price"] = product_obj.max_price

            response["is_bundle_product"] = product_obj.is_bundle_product

            response["variant_price_permission"] = custom_permission_price(request.user, "variant")


            response["product_description_amazon_uk"] = product_obj.product_description
            try:
                response["special_features"] = json.loads(amazon_uk_product_dict["special_features"])
            except Exception as e:
                response["special_features"] = []

            response["ecommerce_dimensions"] = amazon_uk_product_dict["dimensions"]

            
            if product_obj.product_id_type != None:
                response["product_id_type"] = product_obj.product_id_type.name
            else:
                response["product_id_type"] = ""
            
            if product_obj.material_type != None:
                response["material_type"] = product_obj.material_type.name
            else:
                response["material_type"] = ""
            
            warehouses_information = []
            response["warehouses_information"] = warehouses_information


            dynamic_form_attributes = {}
            try:
                dynamic_form_attributes = json.loads(product_obj.dynamic_form_attributes)
            except Exception as e:
                pass
            response["dynamic_form_attributes"] = dynamic_form_attributes

            images = {}

            main_images_list = ImageBucket.objects.none()
            try:
                main_images_obj = MainImages.objects.get(product=product_obj,is_sourced=True)
                main_images_list|=main_images_obj.main_images.all()
            except Exception as e:
                pass
            main_images_list = main_images_list.distinct()
            images["main_images"] = create_response_images_main(main_images_list)
            
            sub_images_list = ImageBucket.objects.none()
            try:
                sub_images_obj = SubImages.objects.get(product=product_obj,is_sourced=True)
                sub_images_list|=sub_images_obj.sub_images.all()
            except Exception as e:
                pass
            sub_images_list = sub_images_list.distinct()
            images["sub_images"] = create_response_images_sub(sub_images_list)
            
            images["pfl_images"] = create_response_images(
                product_obj.pfl_images.all())
            images["pfl_generated_images"] = create_response_images(
                product_obj.pfl_generated_images.all())
            images["white_background_images"] = create_response_images(
                product_obj.white_background_images.all())
            images["lifestyle_images"] = create_response_images(
                product_obj.lifestyle_images.all())
            images["certificate_images"] = create_response_images(
                product_obj.certificate_images.all())
            images["giftbox_images"] = create_response_images(
                product_obj.giftbox_images.all())
            images["diecut_images"] = create_response_images(
                product_obj.diecut_images.all())
            images["aplus_content_images"] = create_response_images(
                product_obj.aplus_content_images.all())
            images["ads_images"] = create_response_images(
                product_obj.ads_images.all())
            images["unedited_images"] = create_response_images(
                product_obj.base_product.unedited_images.all())
            images["transparent_images"] = create_response_images(
                product_obj.transparent_images.all())
            images["best_images"] = create_response_images(
                product_obj.get_best_images())

            images["all_images"] = images["pfl_images"] + images["pfl_generated_images"] + \
                images["white_background_images"] + images["lifestyle_images"] + \
                images["certificate_images"] + images["giftbox_images"] + \
                images["diecut_images"] + images["aplus_content_images"] + \
                images["ads_images"] + images["unedited_images"] + images["transparent_images"] + images["best_images"] + create_response_images_main_sub_delete(main_images_list) + create_response_images_main_sub_delete(sub_images_list)
            
            try:
                unique_image_dict = {}
                unique_image_list = []
                for image in images["all_images"]:
                    if image["pk"] not in unique_image_dict:
                        unique_image_list.append(image)
                        unique_image_dict[image["pk"]] = 1
                images["all_images"] = unique_image_list
            except Exception as e:
                pass

            repr_image_url = Config.objects.all()[0].product_404_image.image.url
            repr_high_def_url = repr_image_url
            
            main_images_obj = None
            try:
                main_images_obj = MainImages.objects.get(product=product_obj, channel=None)
            except Exception as e:
                pass

            if main_images_obj!=None and main_images_obj.main_images.filter(is_main_image=True).count() > 0:
                try:
                    repr_image_url = main_images_obj.main_images.filter(
                        is_main_image=True)[0].image.mid_image.url
                except Exception as e:
                    repr_image_url = main_images_obj.main_images.filter(is_main_image=True)[0].image.image.url

                repr_high_def_url = main_images_obj.main_images.filter(is_main_image=True)[0].image.image.url

            response["repr_image_url"] = repr_image_url
            response["repr_high_def_url"] = repr_high_def_url

            try:
                response["barcode_image_url"] = product_obj.barcode.image.url
            except Exception as e:
                response["barcode_image_url"] = ""

            pfl_pk = None
            if PFL.objects.filter(product=product_obj).exists() == False:
                pfl_obj = PFL.objects.create(product=product_obj)
                pfl_pk = pfl_obj.pk
            else:
                pfl_obj = PFL.objects.filter(product=product_obj)[0]
                pfl_pk = pfl_obj.pk

            response["pfl_pk"] = pfl_pk
            response["product_pk"] = product_obj.pk
            response["product_uuid"] = product_obj.uuid

            response["images"] = images
            response["base_product_pk"] = base_product_obj.pk

            custom_permission_obj = CustomPermission.objects.get(user=request.user)
            response["verify_product"] = custom_permission_obj.verify_product

            if custom_permission_obj.delete_product==True:
                if product_obj.verified==True or product_obj.locked==True or DealsHubProduct.objects.filter(product=product_obj, is_published=True).exists()==True:
                    response["delete_product"] = False
                else:
                    response["delete_product"] = True
            else:
                response["delete_product"] = False

            response['faqs'] = faqs
            response['how_to_use'] = how_to_use

            ## SAP Exception

            response["is_sap_exception"] = product_obj.is_sap_exception
            response["atp_threshold"] = product_obj.atp_threshold
            response["holding_threshold"] = product_obj.holding_threshold

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchDealsHubProductsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("FetchDealsHubProductsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            dealshub_product_objs = custom_permission_filter_dealshub_product(request.user)
            dealshub_product_objs = dealshub_product_objs.filter(location_group=location_group_obj)

            search_list = data.get("search_list", "[]")


            filter_parameters = data.get("filter_parameters", "{}")

            filter_parameters = json.loads(filter_parameters)
            search_list = json.loads(search_list)

            if "has_image" in filter_parameters:
                if filter_parameters["has_image"] == True:
                    dealshub_product_objs = dealshub_product_objs.exclude(product__no_of_images_for_filter=0)
                elif filter_parameters["has_image"] == False:
                    dealshub_product_objs = dealshub_product_objs.filter(product__no_of_images_for_filter=0)

            if "brand_name" in filter_parameters and filter_parameters["brand_name"]!="":
                dealshub_product_objs = dealshub_product_objs.filter(product__base_product__brand__name=filter_parameters["brand_name"])


            if "stock" in filter_parameters:
                if filter_parameters["stock"] == True:
                    dealshub_product_objs = dealshub_product_objs.exclude(stock=0)
                elif filter_parameters["stock"] == False:
                    dealshub_product_objs = dealshub_product_objs.filter(stock=0)


            if "active_status" in filter_parameters:
                if filter_parameters["active_status"] == True:
                    dealshub_product_objs = dealshub_product_objs.filter(is_published=True)
                elif filter_parameters["active_status"] == False:
                    dealshub_product_objs = dealshub_product_objs.filter(is_published=False)

            if "price_sort" in filter_parameters:
                if filter_parameters["price_sort"] == "low":
                    dealshub_product_objs = dealshub_product_objs.order_by('now_price')
                elif filter_parameters["price_sort"] == "high":
                    dealshub_product_objs = dealshub_product_objs.order_by('-now_price')


            if len(search_list)>0:
                temp_product_objs_list = DealsHubProduct.objects.none()
                for search_key in search_list:
                    temp_product_objs_list |= dealshub_product_objs.filter(Q(product__base_product__base_product_name__icontains=search_key) | Q(product__product_name__icontains=search_key) | Q(product__product_name_sap__icontains=search_key) | Q(product__product_id__icontains=search_key) | Q(product__base_product__seller_sku__icontains=search_key))
                dealshub_product_objs = temp_product_objs_list.distinct()
                
            page = int(data.get('page', 1))
            paginator = Paginator(dealshub_product_objs, 20)
            dealshub_product_objs_subset = paginator.page(page)
            products = []

            if "import_file" in data:
                path = default_storage.save('tmp/search-dh-file.xlsx', data["import_file"])
                path = "http://cdn.omnycomm.com.s3.amazonaws.com/"+path
                dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
                rows = len(dfs.iloc[:])
                search_list = []
                for i in range(rows):
                    try:
                        search_key = str(dfs.iloc[i][0]).strip()
                        search_list.append(search_key)
                    except Exception as e:
                        pass
                dealshub_product_objs_subset = dealshub_product_objs.filter(Q(product__product_id__in=search_list) | Q(product__base_product__seller_sku__in=search_list))

            for dealshub_product_obj in dealshub_product_objs_subset:
                try:
                    product_obj = dealshub_product_obj.product
                    temp_dict ={}
                    temp_dict["product_pk"] = product_obj.pk
                    temp_dict["product_uuid"] = dealshub_product_obj.uuid
                    temp_dict["product_id"] = product_obj.product_id
                    temp_dict["product_name"] = dealshub_product_obj.product_name
                    temp_dict["product_name_ar"] = dealshub_product_obj.product_name_ar
                    temp_dict["seller_sku"] = dealshub_product_obj.get_seller_sku()
                    temp_dict["brand_name"] = product_obj.base_product.brand.name
                    temp_dict["channel_status"] = dealshub_product_obj.is_published
                    temp_dict["is_cod_allowed"] = dealshub_product_obj.is_cod_allowed
                    temp_dict["is_new_arrival"] = dealshub_product_obj.is_new_arrival
                    temp_dict["is_on_sale"] = dealshub_product_obj.is_on_sale
                    temp_dict["category"] = dealshub_product_obj.get_category()
                    temp_dict["sub_category"] = dealshub_product_obj.get_sub_category()
                    temp_dict["was_price"] = str(dealshub_product_obj.was_price)
                    temp_dict["now_price"] = str(dealshub_product_obj.now_price)
                    temp_dict["stock"] = str(dealshub_product_obj.stock)
                    temp_dict["min_price"] = str(product_obj.min_price)
                    temp_dict["max_price"] = str(product_obj.max_price)

                    # repr_image_url = Config.objects.all()[0].product_404_image.image.url
                    # repr_high_def_url = repr_image_url
                    
                    # main_images_obj = None
                    # try:
                    #     main_images_obj = MainImages.objects.get(product=product_obj, channel=None)
                    # except Exception as e:
                    #     pass

                    # if main_images_obj!=None and main_images_obj.main_images.filter(is_main_image=True).count() > 0:
                    #     try:
                    #         repr_image_url = main_images_obj.main_images.filter(
                    #             is_main_image=True)[0].image.mid_image.url
                    #     except Exception as e:
                    #         repr_image_url = main_images_obj.main_images.filter(is_main_image=True)[0].image.image.url

                    #     repr_high_def_url = main_images_obj.main_images.filter(is_main_image=True)[0].image.image.url

                    temp_dict["repr_image_url"] = dealshub_product_obj.get_display_image_url()
                    temp_dict["repr_high_def_url"] = dealshub_product_obj.get_display_image_url()

                    products.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchDealsHubProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))

            is_available = True
            
            if paginator.num_pages == page:
                is_available = False

            response["active_products"] = DealsHubProduct.objects.filter(is_published=True).count()
            response["inactive_products"] = DealsHubProduct.objects.filter(is_published=False).count()

            response["variant_price_permission"] = custom_permission_price(request.user, "variant")
            response["dealshub_price_permission"] = custom_permission_price(request.user, "dealshub")
            response["dealshub_stock_permission"] = custom_permission_stock(request.user, "dealshub")

            response["is_available"] = is_available
            response["total_products"] = len(dealshub_product_objs)

            response['products'] = products
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchDealsHubProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UpdateDealshubProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("UpdateDealshubProductAPI: %s", str(data))

            is_b2b = False
            location_group_uuid = data.get("locationGroupUuid","")
            if location_group_uuid != "":
                location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
                is_b2b = location_group_obj.is_b2b

            if not isinstance(data, dict):
                data = json.loads(data)

            product_uuid = data["product_uuid"]

            dh_product_obj = DealsHubProduct.objects.get(uuid=product_uuid)

            price_permission = custom_permission_price(request.user, "dealshub")
            stock_permission = custom_permission_stock(request.user, "dealshub")

            if price_permission:
                if "was_price" in data:
                    was_price = float(data["was_price"])
                    dh_product_obj.was_price = was_price
                if "now_price" in data:
                    now_price = float(data["now_price"])        
                    dh_product_obj.now_price = now_price
                    if dh_product_obj.promotional_price==0:
                        dh_product_obj.promotional_price = now_price
                if "promotional_price" in data:
                    promotional_price = float(data["promotional_price"])
                    dh_product_obj.promotional_price = promotional_price

                    if is_b2b == True:
                        dh_product_obj.promotional_price_cohort1 = float(data["promotional_price_cohort1"])
                        dh_product_obj.promotional_price_cohort2 = float(data["promotional_price_cohort2"])
                        dh_product_obj.promotional_price_cohort3 = float(data["promotional_price_cohort3"])
                        dh_product_obj.promotional_price_cohort4 = float(data["promotional_price_cohort4"])
                        dh_product_obj.promotional_price_cohort5 = float(data["promotional_price_cohort5"])

            if stock_permission:
                if "stock" in data:
                    stock = float(data["stock"])
                    dh_product_obj.stock = stock

            dh_product_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateDealshubProductAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class BulkUpdateDealshubProductPriceAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("BulkUpdateDealshubProductPriceAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]

            price_permission = custom_permission_price(request.user, "dealshub")
            if not price_permission:
                response['status'] = 407
                logger.error("BulkUpdateDealshubProductPriceAPI: Permission not granted")
                return Response(data=response)

            path = default_storage.save('tmp/bulk-upload-price.xlsx', data["import_file"])
            path = "http://cdn.omnycomm.com.s3.amazonaws.com/"+path
            dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
            rows = len(dfs.iloc[:])

            for i in range(rows):
                try:
                    product_id = str(dfs.iloc[i][0]).strip()
                    product_id = product_id.split(".")[0]

                    now_price = float(dfs.iloc[i][1])
                    was_price = float(dfs.iloc[i][2])
                    
                    dh_product_obj = DealsHubProduct.objects.get(location_group__uuid=location_group_uuid, product__product_id=product_id)
                    dh_product_obj.now_price = now_price
                    dh_product_obj.was_price = was_price
                    dh_product_obj.save()
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("BulkUpdateDealshubProductPriceAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("BulkUpdateDealshubProductPriceAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class BulkUpdateB2BDealshubProductPriceAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:

            data = request.data
            logger.info("BulkUpdateB2BDealshubProductPriceAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]

            cohort_permission = custom_permission_cohort(request.user, "dealshub")
            if not cohort_permission:
                response['status'] = 407
                logger.error("BulkUpdateB2BDealshubProductPriceAPI: Permission not granted")
                return Response(data=response)

            path = default_storage.save('tmp/bulk-upload-b2b-price.xlsx', data["import_file"])
            path = "http://cdn.omnycomm.com.s3.amazonaws.com/"+path
            dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
            rows = len(dfs.iloc[:])

            for i in range(rows):
                try:
                    product_id = str(dfs.iloc[i][0]).strip()
                    product_id = product_id.split(".")[0]

                    dealshub_product_obj = DealsHubProduct.objects.get(location_group__uuid=location_group_uuid, product__product_id=product_id)

                    if str(dfs.iloc[i][1]) != "nan" and str(dfs.iloc[i][1]) != "":
                        now_price = float(dfs.iloc[i][1])
                        dealshub_product_obj.now_price = now_price

                    if str(dfs.iloc[i][2]) != "nan" and str(dfs.iloc[i][2]) != "":
                        now_price_cohort1 = float(dfs.iloc[i][2])
                        dealshub_product_obj.now_price_cohort1 = now_price_cohort1

                    if str(dfs.iloc[i][3]) != "nan" and str(dfs.iloc[i][3]) != "":
                        now_price_cohort2 = float(dfs.iloc[i][3])
                        dealshub_product_obj.now_price_cohort2 = now_price_cohort2

                    if str(dfs.iloc[i][4]) != "nan" and str(dfs.iloc[i][4]) != "":
                        now_price_cohort3 = float(dfs.iloc[i][4])
                        dealshub_product_obj.now_price_cohort3 = now_price_cohort3

                    if str(dfs.iloc[i][5]) != "nan" and str(dfs.iloc[i][5]) != "":
                        now_price_cohort4 = float(dfs.iloc[i][5])
                        dealshub_product_obj.now_price_cohort4 = now_price_cohort4

                    if str(dfs.iloc[i][6]) != "nan" and str(dfs.iloc[i][6]) != "":
                        now_price_cohort5 = float(dfs.iloc[i][6])
                        dealshub_product_obj.now_price_cohort5 = now_price_cohort5

                    if str(dfs.iloc[i][7]) != "nan" and str(dfs.iloc[i][7]) != "":
                        promotional_price = float(dfs.iloc[i][7])
                        dealshub_product_obj.promotional_price = promotional_price

                    if str(dfs.iloc[i][8]) != "nan" and str(dfs.iloc[i][8]) != "":
                        promotional_price_cohort1 = float(dfs.iloc[i][8])
                        dealshub_product_obj.promotional_price_cohort1 = promotional_price_cohort1

                    if str(dfs.iloc[i][9]) != "nan" and str(dfs.iloc[i][9]) != "":
                        promotional_price_cohort2 = float(dfs.iloc[i][9])
                        dealshub_product_obj.promotional_price_cohort2 = promotional_price_cohort2

                    if str(dfs.iloc[i][10]) != "nan" and str(dfs.iloc[i][10]) != "":
                        promotional_price_cohort3 = float(dfs.iloc[i][10])
                        dealshub_product_obj.promotional_price_cohort3 = promotional_price_cohort3

                    if str(dfs.iloc[i][11]) != "nan" and str(dfs.iloc[i][11]) != "":
                        promotional_price_cohort4 = float(dfs.iloc[i][11])
                        dealshub_product_obj.promotional_price_cohort4 = promotional_price_cohort4

                    if str(dfs.iloc[i][12]) != "nan" and str(dfs.iloc[i][12]) != "":
                        promotional_price_cohort5 = float(dfs.iloc[i][12])
                        dealshub_product_obj.promotional_price_cohort5 = promotional_price_cohort5

                    dealshub_product_obj.save()
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("BulkUpdateB2BDealshubProductPriceAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("BulkUpdateB2BDealshubProductPriceAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class BulkUpdateB2BDealshubProductMOQAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:

            data = request.data
            logger.info("BulkUpdateB2BDealshubProductMOQAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]

            cohort_permission = custom_permission_cohort(request.user, "dealshub")
            if not cohort_permission:
                response['status'] = 407
                logger.error("BulkUpdateB2BDealshubProductMOQAPI: Permission not granted")
                return Response(data=response)

            path = default_storage.save('tmp/bulk-upload-b2b-moq.xlsx', data["import_file"])
            path = "http://cdn.omnycomm.com.s3.amazonaws.com/"+path
            dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
            rows = len(dfs.iloc[:])

            for i in range(rows):
                try:
                    product_id = str(dfs.iloc[i][0]).strip()
                    product_id = product_id.split(".")[0]

                    dealshub_product_obj = DealsHubProduct.objects.get(location_group__uuid=location_group_uuid, product__product_id=product_id)

                    if str(dfs.iloc[i][1]) != "nan" and str(dfs.iloc[i][1]) != "":
                        moq = int(dfs.iloc[i][1])
                        dealshub_product_obj.moq = moq

                    if str(dfs.iloc[i][2]) != "nan" and str(dfs.iloc[i][2]) != "":
                        moq_cohort1 = int(dfs.iloc[i][2])
                        dealshub_product_obj.moq_cohort1 = moq_cohort1

                    if str(dfs.iloc[i][3]) != "nan" and str(dfs.iloc[i][3]) != "":
                        moq_cohort2 = int(dfs.iloc[i][3])
                        dealshub_product_obj.moq_cohort2 = moq_cohort2

                    if str(dfs.iloc[i][4]) != "nan" and str(dfs.iloc[i][4]) != "":
                        moq_cohort3 = int(dfs.iloc[i][4])
                        dealshub_product_obj.moq_cohort3 = moq_cohort3

                    if str(dfs.iloc[i][5]) != "nan" and str(dfs.iloc[i][5]) != "":
                        moq_cohort4 = int(dfs.iloc[i][5])
                        dealshub_product_obj.moq_cohort4 = moq_cohort4

                    if str(dfs.iloc[i][6]) != "nan" and str(dfs.iloc[i][6]) != "":
                        moq_cohort5 = int(dfs.iloc[i][6])
                        dealshub_product_obj.moq_cohort5 = moq_cohort5

                    dealshub_product_obj.save()
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("BulkUpdateB2BDealshubProductMOQAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("BulkUpdateB2BDealshubProductMOQAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class BulkUpdateDealshubProductStockAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("BulkUpdateDealshubProductStockAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]

            stock_permission = custom_permission_stock(request.user, "dealshub")
            if not stock_permission:
                response['status'] = 407
                logger.error("BulkUpdateDealshubProductStockAPI: Permission not granted")
                return Response(data=response)

            path = default_storage.save('tmp/bulk-upload-stock.xlsx', data["import_file"])
            path = "http://cdn.omnycomm.com.s3.amazonaws.com/"+path
            dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
            rows = len(dfs.iloc[:])

            for i in range(rows):
                try:
                    product_id = str(dfs.iloc[i][0]).strip()
                    product_id = product_id.split(".")[0]
                    stock = float(dfs.iloc[i][1])
                    
                    dh_product_obj = DealsHubProduct.objects.get(location_group__uuid=location_group_uuid, product__product_id=product_id)
                    dh_product_obj.stock = stock
                    dh_product_obj.save()
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("BulkUpdateDealshubProductStockAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("BulkUpdateDealshubProductStockAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class BulkUpdateDealshubProductPublishStatusAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:
            data = request.data
            logger.info("BulkUpdateDealshubProductPublishStatusAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            location_group_uuid = data["locationGroupUuid"]

            path = default_storage.save('tmp/bulk-publish-product.xlsx', data["import_file"])
            path = "http://cdn.omnycomm.com.s3.amazonaws.com/"+path

            try:
                dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
            except Exception as e:
                response['status'] = 406
                logger.warning("BulkUpdateDealshubProductPublishStatusAPI: UnSupported File Format or Sheet1 not found")
                return Response(data=response)
            
            rows = len(dfs.iloc[:])
            excel_errors = []

            for i in range(rows):
                try:
                    product_id = str(dfs.iloc[i][0]).strip()
                    product_id = product_id.split(".")[0]
                    is_published_str = str(dfs.iloc[i][1]).strip().lower()
                    
                    if is_published_str!="true" and is_published_str!="false":
                        excel_errors.append("status for "+product_id+" is not proper")
                        continue
                    is_published = True if is_published_str=="true" else False

                    dh_product_obj = DealsHubProduct.objects.get(location_group__uuid=location_group_uuid, product__product_id=product_id)
                    dh_product_obj.is_published = is_published
                    dh_product_obj.save()

                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("BulkUpdateDealshubProductPublishStatusAPI: %s at %s", e, str(exc_tb.tb_lineno))
            
            response['excel_errors'] = excel_errors
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("BulkUpdateDealshubProductPublishStatusAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveBaseProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            if request.user.has_perm('WAMSApp.change_product') == False:
                logger.warning("SaveBaseProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("SaveBaseProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            brand_obj = None
            organization_obj = CustomPermission.objects.get(user__username=request.user.username).organization
            try:
                permissible_brands = custom_permission_filter_brands(request.user)
                if Brand.objects.filter(name=data["brand_name"], organization=organization_obj).exists()==True:
                    brand_obj = Brand.objects.get(name=data["brand_name"], organization=organization_obj)
                    if brand_obj not in permissible_brands:
                        logger.warning("SaveBaseProductAPI Restricted Access Brand!")
                        response['status'] = 403
                        return Response(data=response)
                else:
                    custom_permission_obj = CustomPermission.objects.get(user__username=request.user.username)
                    brand_obj = Brand.objects.create(name=data["brand_name"], organization=organization_obj)
                    custom_permission_obj.brands.add(brand_obj)
                    custom_permission_obj.save()
            except Exception as e:
                logger.error("SaveBaseProductAPI Restricted Access Brand!")
                response['status'] = 403
                return Response(data=response)

            base_product_obj = BaseProduct.objects.get(pk=int(data["base_product_pk"]))
            
            base_product_name = convert_to_ascii(data["base_product_name"])
            seller_sku = convert_to_ascii(data["seller_sku"])
            brand_name = convert_to_ascii(data["brand_name"])
            manufacturer = convert_to_ascii(data["manufacturer"])
            manufacturer_part_number = convert_to_ascii(data["manufacturer_part_number"])
            category_uuid = data["category_uuid"]
            sub_category_uuid = data["sub_category_uuid"]
            
            dimensions = data["base_dimensions"]
            
            old_dimensions = json.loads(base_product_obj.dimensions)
            if len(list(dimensions.keys()))==len(list(old_dimensions.keys())):
                for key in dimensions:
                    if key not in old_dimensions:
                        dimensions = old_dimensions
                        break
            else:
                dimensions = old_dimensions
            dimensions = json.dumps(dimensions)

            if BaseProduct.objects.filter(seller_sku=seller_sku, brand=brand_obj).exclude(pk=data["base_product_pk"]).count() >= 1 :
                logger.warning("Duplicate product detected!")
                response['status'] = 409
                return Response(data=response)

            category_obj = None
            try:
                category_obj = Category.objects.get(uuid=category_uuid)
            except Exception as e:
                pass
            sub_category_obj = None
            try:
                sub_category_obj = SubCategory.objects.get(uuid=sub_category_uuid)
            except Exception as e:
                pass

            is_category_updated = False
            if base_product_obj.category!=category_obj:
                is_category_updated = True

            base_product_obj.base_product_name = base_product_name
            base_product_obj.seller_sku = seller_sku
            base_product_obj.brand = brand_obj
            base_product_obj.manufacturer = manufacturer
            base_product_obj.manufacturer_part_number = manufacturer_part_number
            base_product_obj.category = category_obj
            base_product_obj.sub_category = sub_category_obj
            base_product_obj.dimensions = dimensions
            
            base_product_obj.save()

            # Update dynamic_form_attributes for all Variants
            try:
                if is_category_updated:
                    dynamic_form_attributes = {}
                    property_data = json.loads(category_obj.property_data)
                    for prop_data in property_data:
                        dynamic_form_attributes[prop_data["key"]] = {
                            "type": "dropdown",
                            "labelText": prop_data["key"].title(),
                            "value": "",
                            "options": prop_data["values"]
                        }

                    product_objs = Product.objects.filter(base_product=base_product_obj)
                    product_objs.update(dynamic_form_attributes=json.dumps(dynamic_form_attributes))

            except Exception as e:
                pass
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveBaseProductAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            if request.user.has_perm('WAMSApp.change_product') == False:
                logger.warning("SaveProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("SaveProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)


            # Check for duplicate
            product_id = data["product_id"]

            product_obj = Product.objects.get(pk=int(data["product_pk"]))

            if product_obj.locked:
                logger.warning("SaveProductAPI Restricted Access - Locked!")
                response['status'] = 403
                return Response(data=response)

            product_obj.verified = False

            organization_obj = CustomPermission.objects.get(user__username=request.user.username).organization
            
            # Checking brand permission
            try:
                permissible_brands = custom_permission_filter_brands(request.user)
                brand_obj = Brand.objects.get(name=product_obj.base_product.brand.name, organization=organization_obj)
                if brand_obj not in permissible_brands:
                    logger.warning("SaveProductAPI Restricted Access Brand!")
                    response['status'] = 403
                    return Response(data=response)
            except Exception as e:
                logger.error("SaveProductAPI Restricted Access Brand!")
                response['status'] = 403
                return Response(data=response)

            if Product.objects.filter(product_id=product_id, base_product__brand__organization=organization_obj).exclude(pk=data["product_pk"]).count() >= 1 :
                logger.warning("Duplicate product detected!")
                response['status'] = 409
                return Response(data=response)


            product_name = convert_to_ascii(data["product_name"])
            product_description = convert_to_ascii(data["product_description"])
            barcode_string = data["barcode_string"]
            color = convert_to_ascii(data["color"])
            color_map = convert_to_ascii(data["color_map"])
            size = data.get("size","")
            size_unit = data.get("size_unit","")
            capacity = data.get("capacity","")
            capacity_unit = data.get("capacity_unit","")
            target_age_range = data.get("target_age_range","")

            weight = 0
            try:
                weight = float(data.get("weight", 0))
            except Exception as e:
                pass
            
            standard_price = None if data["standard_price"] == "" else float(data["standard_price"])
            quantity = None if data["quantity"] == "" else int(data["quantity"])
            
            product_id_type = convert_to_ascii(data["product_id_type"])
            product_id_type_obj , created = ProductIDType.objects.get_or_create(name=product_id_type)
            
            material_type = convert_to_ascii(data["material_type"])
            material_type_obj , created = MaterialType.objects.get_or_create(name=material_type)
            
            pfl_product_name = convert_to_ascii(data["pfl_product_name"])
            pfl_product_features = data["pfl_product_features"]
            pfl_product_features_ar = data.get("pfl_product_features_ar",[])

            factory_notes = convert_to_ascii(data["factory_notes"])

            dynamic_form_attributes = data["dynamic_form_attributes"]

            faqs = data["faqs"]
            how_to_use = data["how_to_use"]

            min_price = float(data.get("min_price", 0))
            max_price = float(data.get("max_price", 0))

            is_sap_exception = bool(data.get("is_sap_exception", False))
            atp_threshold = int(data.get("atp_threshold", 100))
            holding_threshold = int(data.get("holding_threshold", 5))

            is_cod_allowed = data.get("is_cod_allowed", False)
            is_bundle_product = data.get("is_bundle_product", False)

            response["variant_price_permission"] = custom_permission_price(request.user, "variant")
            response["dealshub_price_permission"] = custom_permission_price(request.user, "dealshub")

            response["dealshub_stock_permission"] = custom_permission_stock(request.user, "dealshub")

            if custom_permission_price(request.user, "variant")==True:
                product_obj.min_price = min_price
                product_obj.max_price = max_price


            product_obj.product_id = product_id
            product_obj.barcode_string = barcode_string
            product_obj.product_name = product_name
            product_obj.product_description = product_description

            product_obj.product_id_type = product_id_type_obj
            product_obj.color_map = color_map
            product_obj.color = color
            product_obj.size = size
            product_obj.size_unit = size_unit
            product_obj.capacity = capacity
            product_obj.capacity_unit = capacity_unit
            product_obj.target_age_range = target_age_range
            product_obj.weight = weight
            
            product_obj.material_type = material_type_obj
            product_obj.standard_price = standard_price
            product_obj.quantity = quantity
            
            product_obj.pfl_product_name = pfl_product_name
            product_obj.pfl_product_features = json.dumps(pfl_product_features)
            product_obj.pfl_product_features_ar = json.dumps(pfl_product_features_ar)

            product_obj.factory_notes = factory_notes

            product_obj.is_bundle_product = is_bundle_product

            product_obj.faqs = json.dumps(faqs)
            product_obj.how_to_use = json.dumps(how_to_use)
            
            if str(dynamic_form_attributes)!="{}":
                product_obj.dynamic_form_attributes = json.dumps(dynamic_form_attributes)
            
            product_obj.is_sap_exception = is_sap_exception

            if is_sap_exception == True:

                product_obj.atp_threshold = atp_threshold
                product_obj.holding_threshold = holding_threshold

            product_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveProductAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchProductListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("FetchProductListAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            filter_parameters = data["filter_parameters"]
            chip_data = data["tags"]

            page = int(data['page'])

            organization_obj = CustomPermission.objects.get(user__username=request.user.username).organization

            search_list_product_objs = custom_permission_filter_products(request.user)

            search_list_product_objs = search_list_product_objs.order_by('-pk')

            without_images = 0
            if filter_parameters["has_image"] == "1":
                without_images = 0
                search_list_product_objs = search_list_product_objs.exclude(no_of_images_for_filter=0)
            elif filter_parameters["has_image"] == "0":
                without_images = 1
                search_list_product_objs = search_list_product_objs.filter(no_of_images_for_filter=0)
            elif filter_parameters["has_image"] == "2":
                without_images = 0
                search_list_product_objs = search_list_product_objs.annotate(c=Count('base_product__unedited_images')).filter(c__gt=1)

            if filter_parameters.get("brand_name", "") != "":
                brand_obj = Brand.objects.get(name=filter_parameters["brand_name"], organization=organization_obj)
                search_list_product_objs = search_list_product_objs.filter(base_product__brand=brand_obj)

            search_list_product_objs = content_health_filtered_list(filter_parameters,search_list_product_objs)

            if len(chip_data) != 0:
                search_list_product_lookup = Product.objects.none()
                for tag in chip_data:
                    search_list_product_lookup |= search_list_product_objs.filter(
                        Q(base_product__base_product_name__icontains=tag) |
                        Q(product_name__icontains=tag) |
                        Q(product_name_sap__icontains=tag) |
                        Q(product_id__icontains=tag) |
                        Q(base_product__seller_sku__icontains=tag)
                    )
                
                search_list_product_objs = search_list_product_lookup.distinct()
            
            search_list_base_product_objs = search_list_product_objs.values_list('base_product',flat=True).order_by('-pk')

            search_list_base_product_objs = list(dict.fromkeys(search_list_base_product_objs))
            products = []

            paginator = Paginator(search_list_base_product_objs, 20)
            base_product_objs = paginator.page(page)

            for base_product_pk in base_product_objs:
                base_product_obj = BaseProduct.objects.get(pk=base_product_pk)
                temp_dict = {}
                temp_dict["base_product_pk"] = base_product_pk
                temp_dict["product_name"] = base_product_obj.base_product_name
                temp_dict["manufacturer"] = base_product_obj.manufacturer
                temp_dict["manufacturer_part_number"] = base_product_obj.manufacturer_part_number
                temp_dict["base_main_images"] = []

                if base_product_obj.brand != None:
                    temp_dict["brand_name"] = base_product_obj.brand.name
                else:
                    temp_dict["brand_name"] = "-"
                
                temp_dict["created_date"] = str(base_product_obj.created_date.strftime("%d %b, %Y"))

                temp_dict["products"] = []
                temp_dict["channel_products"] = []
                temp_dict["dimensions"] = {}

                temp_dict["seller_sku"] = base_product_obj.seller_sku
                temp_dict["category"] = "" if base_product_obj.category==None else str(base_product_obj.category)
                temp_dict["sub_category"] = "" if base_product_obj.sub_category==None else str(base_product_obj.sub_category)
                temp_dict["dimensions"] = json.dumps(base_product_obj.dimensions)
                
                product_objs = search_list_product_objs.filter(base_product = base_product_obj)

                for product_obj in product_objs:
                    
                    temp_dict2 = {}
                    temp_dict2["product_pk"] = product_obj.pk
                    temp_dict2["product_id"] = product_obj.product_id
                    temp_dict2["product_name"] = product_obj.product_name
                    temp_dict2["brand_name"] = str(product_obj.base_product.brand)
                    temp_dict2["sub_category"] = "" if base_product_obj.sub_category==None else str(base_product_obj.sub_category)
                    temp_dict2["category"] = "" if base_product_obj.category==None else str(base_product_obj.category)
                    temp_dict2["product_price"] = product_obj.standard_price
                    if temp_dict2["product_price"]==None:
                        temp_dict2["product_price"] = "-"
                    temp_dict2["status"] = product_obj.status
                    
                    temp_dict2["main_images"] = []
                    temp_dict["base_main_images"] = []


                    if without_images==0:
                        main_images_list = ImageBucket.objects.none()
                        main_images_objs = MainImages.objects.filter(product=product_obj)
                        for main_images_obj in main_images_objs:
                            main_images_list |= main_images_obj.main_images.all()

                        main_images_list = main_images_list.distinct()

                        try:
                            main_images = create_response_images_main(main_images_list)
                            temp_dict2["main_images"] = main_images
                            for main_image in main_images:
                                temp_dict["base_main_images"].append(main_image)
                        except Exception as e:
                            pass

                    channels_of_prod =0
                    inactive_channels = 0

                    if product_obj.channel_product.is_noon_product_created == True:
                        
                        channels_of_prod +=1
                        noon_product = json.loads(product_obj.channel_product.noon_product_json)
                        if noon_product["status"] == "Inactive":
                            inactive_channels +=1

                    if product_obj.channel_product.is_amazon_uk_product_created == True:
                        
                        channels_of_prod +=1
                        amazon_uk_product = json.loads(product_obj.channel_product.amazon_uk_product_json)
                        if amazon_uk_product["status"] == "Inactive":
                            inactive_channels +=1

                    if product_obj.channel_product.is_amazon_uae_product_created == True:
                        
                        channels_of_prod +=1
                        amazon_uae_product = json.loads(product_obj.channel_product.amazon_uae_product_json)
                        if amazon_uae_product["status"] == "Inactive":
                            inactive_channels +=1

                    if product_obj.channel_product.is_ebay_product_created == True:
                        
                        channels_of_prod +=1
                        ebay_product = json.loads(product_obj.channel_product.ebay_product_json)
                        if ebay_product["status"] == "Inactive":
                            inactive_channels +=1

                    temp_dict2["channels_of_prod"] = channels_of_prod
                    temp_dict2["inactive_channels"] = inactive_channels
                    temp_dict2["active_channels"] = channels_of_prod - inactive_channels
                    temp_dict["products"].append(temp_dict2)

                products.append(temp_dict)

            price_type = custom_permission_price(request.user, "price_type")

            is_available = True
            
            if paginator.num_pages == page:
                is_available = False
                        

            response["is_available"] = is_available
            response["total_products"] = len(search_list_base_product_objs)
            response["products"] = products
            response["price_type"] = price_type

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchExportListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("FetchExportListAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            chip_data = json.loads(data.get('tags', '[]'))

            search_list_objs = []
            export_list_objs = []

            if data.get("start_date", "") != "" and data.get("end_date", "") != "":
                start_date = datetime.datetime.strptime(
                    data["start_date"], "%b %d, %Y")
                end_date = datetime.datetime.strptime(
                    data["end_date"], "%b %d, %Y")
                export_list_objs = ExportList.objects.filter(
                    created_date__gte=start_date).filter(created_date__lte=end_date).filter(user=request.user).order_by('-pk')
            else:
                export_list_objs = ExportList.objects.all().filter(user=request.user).order_by('-pk')

            if len(chip_data) == 0:
                search_list_objs = export_list_objs
            
            else:
                for export_list in export_list_objs:
                    for product in export_list.products.all():
                        flag = 0
                        for chip in chip_data:
                            if chip.lower() in export_list.title.lower():
                                search_list_objs.append(export_list)
                                flag = 1
                                break
                            if (chip.lower() in product.product_name_sap.lower() or
                                    chip.lower() in product.product_name.lower() or
                                    chip.lower() in product.product_id.lower() or
                                    chip.lower() in product.seller_sku.lower()):
                                search_list_objs.append(export_list)
                                flag = 1
                                break
                        if flag == 1:
                            break

            export_list = []
            for export_list_obj in search_list_objs:
                temp_dict = {}
                temp_dict["title"] = export_list_obj.title
                temp_dict["created_date"] = str(
                    export_list_obj.created_date.strftime("%d %b, %Y"))
                temp_dict["pk"] = export_list_obj.pk
                temp_dict["product_count"] = export_list_obj.products.all().count()
                temp_dict["channel_name"] = str(export_list_obj.channel)
                export_list.append(temp_dict)

            response["export_list"] = export_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchExportListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class AddToExportAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            if request.user.has_perm('WAMSApp.change_exportlist') == False:
                logger.warning("AddToExportAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("AddToExportAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            select_all = data.get("select_all", False)
            export_option = data["export_option"]
            export_title_pk = data["export_title_pk"]
            export_title = data["export_title"]
            channel_name = data["channel_name"]
            channel_obj = Channel.objects.get(name=channel_name)
            products = data["products"]

            if select_all==True:
                
                filter_parameters = data["filter_parameters"]
                chip_data = data["tags"]

                search_list_product_objs = []
            
                permission_obj = CustomPermission.objects.get(user__username=request.user.username)
                brands = permission_obj.brands.all()

                if filter_parameters["brand_name"] != "":
                    brands = brands.filter(name__icontains=filter_parameters["brand_name"])              

                product_objs_list = Product.objects.filter(base_product__brand__in=brands).order_by('-pk')
                if channel_name=="Amazon UK":
                    product_objs_list = product_objs_list.filter(channel_product__is_amazon_uk_product_created=True)
                elif channel_name=="Amazon UAE":
                    product_objs_list = product_objs_list.filter(channel_product__is_amazon_uae_product_created=True)
                elif channel_name=="Ebay":
                    product_objs_list = product_objs_list.filter(channel_product__is_ebay_product_created=True)
                elif channel_name=="Noon":
                    product_objs_list = product_objs_list.filter(channel_product__is_noon_product_created=True)

                search_list_product_objs = product_objs_list
                
                if len(chip_data) > 0:
                    for tag in chip_data:
                        search = product_objs_list.filter(
                            Q(product_name__icontains=tag) |
                            Q(product_name_sap__icontains=tag) |
                            Q(product_id__icontains=tag) |
                            Q(base_product__seller_sku__icontains=tag)
                        )

                        for prod in search:
                            product_obj = Product.objects.filter(pk=prod.pk)
                            search_list_product_objs|=product_obj

                export_obj = None
                
                if export_option == "New":
                    export_obj = ExportList.objects.create(title=str(export_title), user=request.user)
                else:
                    export_obj = ExportList.objects.get(pk=int(export_title_pk))

                for product_obj in search_list_product_objs:
                    export_obj.products.add(product_obj)
                    export_obj.channel = channel_obj
                    export_obj.save()
            
            else:
                export_obj = None
                if export_option == "New":
                    export_obj = ExportList.objects.create(title=str(export_title), user=request.user)
                else:
                    export_obj = ExportList.objects.get(pk=int(export_title_pk))

                for product_pk in products:
                    product = Product.objects.get(pk=int(product_pk))
                    export_obj.products.add(product)
                    export_obj.channel = channel_obj
                    export_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddToExportAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchExportProductListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("FetchExportProductListAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            export_obj = ExportList.objects.get(pk=int(data["export_pk"]))
            channel_name = export_obj.channel.name
            products = export_obj.products.all()

            product_list = []
            for product in products:
                
                temp_dict = {}
                channel_product = product.channel_product
                
                if channel_name == "Amazon UK":
                    amazon_uk_product = json.loads(channel_product.amazon_uk_product_json)
                    temp_dict["amazon_uk_product"] = amazon_uk_product
                    temp_dict["product_id"] = product.product_id
                    temp_dict["seller_sku"] = product.base_product.seller_sku
                    temp_dict["product_pk"] = product.pk
                    main_images_list = ImageBucket.objects.none()
                    
                    try:
                        main_images_obj = MainImages.objects.get(product=product,channel=export_obj.channel)
                        main_images_list=main_images_obj.main_images.all()
                        main_images_list = main_images_list.distinct()
                        temp_dict["main_images"] = create_response_images_main(main_images_list)
                    except Exception as e:
                        temp_dict["main_images"] = []
                        pass
                
                elif channel_name == "Amazon UAE":
                    amazon_uae_product = json.loads(channel_product.amazon_uae_product_json)
                    temp_dict["amazon_uae_product"] = amazon_uae_product
                    temp_dict["product_id"] = product.product_id
                    temp_dict["product_pk"] = product.pk
                    main_images_list = ImageBucket.objects.none()
                    
                    try:
                        main_images_obj = MainImages.objects.get(product=product,channel=export_obj.channel)
                        main_images_list=main_images_obj.main_images.all()
                        main_images_list = main_images_list.distinct()
                        temp_dict["main_images"] = create_response_images_main(main_images_list)
                    except Exception as e:
                        temp_dict["main_images"] = []
                        pass
                
                elif channel_name == "Noon":
                    noon_product = json.loads(channel_product.noon_product_json)
                    temp_dict["noon_product"] = noon_product
                    temp_dict["product_id"] = product.product_id
                    temp_dict["product_pk"] = product.pk
                    main_images_list = ImageBucket.objects.none()
                    
                    try:
                        main_images_obj = MainImages.objects.get(product=product,channel=export_obj.channel)
                        main_images_list=main_images_obj.main_images.all()
                        main_images_list = main_images_list.distinct()
                        temp_dict["main_images"] = create_response_images_main(main_images_list)
                    except Exception as e:
                        temp_dict["main_images"] = []
                        pass
                
                elif channel_name == "Ebay":
                    ebay_product = json.loads(channel_product.ebay_product_json)
                    temp_dict["ebay_product"] = ebay_product
                    temp_dict["product_id"] = product.product_id
                    temp_dict["product_pk"] = product.pk
                    main_images_list = ImageBucket.objects.none()
                    
                    try:
                        main_images_obj = MainImages.objects.get(product=product,channel=export_obj.channel)
                        main_images_list=main_images_obj.main_images.all()
                        main_images_list = main_images_list.distinct()
                        temp_dict["main_images"] = create_response_images_main(main_images_list)
                    except Exception as e:
                        temp_dict["main_images"] = []
                        pass

                product_list.append(temp_dict)

            response["product_list"] = product_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchExportProductListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DownloadExportListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("DownloadExportListAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            export_format = data["export_format"]

            export_obj = ExportList.objects.get(pk=int(data["export_pk"]))
            products = export_obj.products.all()

            if export_format == "Amazon UK":
                success_products = export_amazon_uk(products)
                response["success_products"] = success_products
                response["total_products"] = products.count()
                response["file_path"] = "/files/csv/export-list-amazon-uk.xlsx"
            
            elif export_format == "Amazon UAE":
                success_products = export_amazon_uae(products)
                response["success_products"] = success_products
                response["total_products"] = products.count()
                response["file_path"] = "/files/csv/export-list-amazon-uae.xlsx"
            
            elif export_format == "Ebay":
                success_products = export_ebay(products)
                response["success_products"] = success_products
                response["total_products"] = products.count()
                response["file_path"] = "/files/csv/export-list-ebay.xlsx"
            
            elif export_format == "Noon":
                success_products = export_noon(products)
                response["success_products"] = success_products
                response["total_products"] = products.count()
                response["file_path"] = "/files/csv/export-list-noon.xlsx"

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DownloadExportListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DownloadProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("DownloadProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            export_format = data["export_format"]

            products = Product.objects.filter(pk=int(data["product_pk"]))

            if export_format == "Amazon UK":
                export_amazon_uk(products)
                response["file_path"] = "/files/csv/export-list-amazon-uk.xlsx"
            elif export_format == "Amazon UAE":
                export_amazon_uae(products)
                response["file_path"] = "/files/csv/export-list-amazon-uae.csv"
            elif export_format == "Ebay":
                export_ebay(products)
                response["file_path"] = "/files/csv/export-list-ebay.xlsx"
            elif export_format == "Noon":
                export_noon(products)
                response["file_path"] = "/files/csv/export-list-noon.xlsx"

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DownloadProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class ImportProductsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            if request.user.has_perm('WAMSApp.change_product') == False:
                logger.warning("ImportProductsAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("ImportProductsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            import_format = data["import_format"]
            import_rule = data["import_rule"]
            import_file = data["import_file"]

            if import_format == "Amazon UK":
                import_amazon_uk(import_rule, import_file)
            elif import_format == "Amazon UAE":
                import_amazon_uae(import_rule, import_file)

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ImportProductsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadProductImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            if request.user.has_perm("WAMSApp.add_image") == False:
                logger.warning("UploadProductImageAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("UploadProductImageAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_obj = Product.objects.get(pk=int(data["product_pk"]))

            if product_obj.locked:
                logger.warning("UploadProductImageAPI Restricted Access - Locked!")
                response['status'] = 403
                return Response(data=response)

            image_objs = []

            image_count = int(data["image_count"])
            for i in range(image_count):
                image_obj = Image.objects.create(image=data["image_"+str(i)])
                image_objs.append(image_obj)

            if data["image_category"] == "main_images":

                for image_obj in image_objs:
                    image_bucket_obj = ImageBucket.objects.create(
                        image=image_obj)
                    product_obj.no_of_images_for_filter += 1

                    if data["channel_name"] == "" or data["channel_name"] == None:

                        main_images_obj , created = MainImages.objects.get_or_create(product=product_obj,is_sourced=True)
                        main_images_obj.main_images.add(image_bucket_obj)
                        main_images_obj.save()

                        if main_images_obj.main_images.all().count() == image_count:
                            image_bucket_obj = main_images_obj.main_images.all()[0]
                            image_bucket_obj.is_main_image = True
                            image_bucket_obj.save()
                            try:
                                pfl_obj = PFL.objects.filter(product=product_obj)[0]
                                if pfl_obj.product_image == None:
                                    pfl_obj.product_image = image_objs[0]
                                    pfl_obj.save()
                            except Exception as e:
                                pass

                        add_imagebucket_to_channel_main_images(image_bucket_obj,product_obj)

                    else:
                        channel_obj = Channel.objects.get(name=data["channel_name"])
                        main_images_obj , created = MainImages.objects.get_or_create(product=product_obj,channel=channel_obj)
                        main_images_obj.main_images.add(image_bucket_obj)
                        main_images_obj.save()

            elif data["image_category"] == "sub_images":
                index = 0
                if data["channel_name"] == "" or data["channel_name"] == None:
                    sub_images_obj , created = SubImages.objects.get_or_create(product=product_obj,is_sourced=True)
                else:
                    channel_obj = Channel.objects.get(name=data["channel_name"])
                    sub_images_obj , created = SubImages.objects.get_or_create(product=product_obj,channel=channel_obj)
                    
                sub_images = sub_images_obj.sub_images.all().order_by('-sub_image_index')
                if sub_images.count() > 0:
                    index = sub_images[0].sub_image_index
                for image_obj in image_objs:
                    index += 1
                    sub_image_index = 0
                    is_sub_image = False
                    product_obj.no_of_images_for_filter += 1
                    if(index <= 8):
                        sub_image_index = index
                        is_sub_image = True
                    image_bucket_obj = ImageBucket.objects.create(image=image_obj,
                                                                  is_sub_image=is_sub_image,
                                                                  sub_image_index=sub_image_index)
                    sub_images_obj.sub_images.add(image_bucket_obj)
                    sub_images_obj.save()
            
            elif data["image_category"] == "pfl_images":
                for image_obj in image_objs:
                    product_obj.pfl_images.add(image_obj)
            elif data["image_category"] == "white_background_images":
                for image_obj in image_objs:
                    product_obj.no_of_images_for_filter += 1
                    product_obj.white_background_images.add(image_obj)
            elif data["image_category"] == "lifestyle_images":
                for image_obj in image_objs:
                    product_obj.no_of_images_for_filter += 1
                    product_obj.lifestyle_images.add(image_obj)
            elif data["image_category"] == "certificate_images":
                for image_obj in image_objs:
                    product_obj.certificate_images.add(image_obj)
            elif data["image_category"] == "giftbox_images":
                for image_obj in image_objs:
                    product_obj.giftbox_images.add(image_obj)
            elif data["image_category"] == "diecut_images":
                for image_obj in image_objs:
                    product_obj.diecut_images.add(image_obj)
            elif data["image_category"] == "aplus_content_images":
                for image_obj in image_objs:
                    product_obj.aplus_content_images.add(image_obj)
            elif data["image_category"] == "ads_images":
                for image_obj in image_objs:
                    product_obj.ads_images.add(image_obj)
            elif data["image_category"] == "unedited_images":
                for image_obj in image_objs:
                    product_obj.base_product.unedited_images.add(image_obj)
            elif data["image_category"] == "transparent_images":
                for image_obj in image_objs:
                    product_obj.transparent_images.add(image_obj)
            elif data["image_category"] == "best_images":
                number = 0
                if product_obj.best_images.count()>0:
                    number = ProductImage.objects.filter(product=product_obj).order_by('number').last().number
                
                for image_obj in image_objs:
                    if ProductImage.objects.filter(product=product_obj, image=image_obj).exists():
                        continue
                    number += 1
                    ProductImage.objects.create(image=image_obj, product=product_obj, number=number)

            product_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadProductImageAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class UpdateMainImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            if request.user.has_perm('WAMSApp.change_image') == False:
                logger.warning("UpdateMainImageAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("UpdateMainImageAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_obj = Product.objects.get(pk=int(data["product_pk"]))
            channel_obj = None
            
            if data["channel_name"]!="":
                channel_obj = Channel.objects.get(name=data["channel_name"])
                
            reset_main_images(product_obj, channel_obj)

            image_bucket_obj = ImageBucket.objects.get(
                pk=int(data["checked_pk"]))
            image_bucket_obj.is_main_image = True
            image_bucket_obj.save()

            try:
                pfl_obj = PFL.objects.filter(product=product_obj)[0]
                if pfl_obj.product_image == None:
                    pfl_obj.product_image = image_bucket_obj.image
                    pfl_obj.save()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("UpdateMainImageAPI: %s at %s",
                             e, str(exc_tb.tb_lineno))

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateMainImageAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UpdateSubImagesAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            if request.user.has_perm('WAMSApp.change_image') == False:
                logger.warning("UpdateSubImagesAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("UpdateSubImagesAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_obj = Product.objects.get(pk=int(data["product_pk"]))
            channel_obj = None
            
            if data["channel_name"]!="":
                channel_obj = Channel.objects.get(name=data["channel_name"])
            
            reset_sub_images(product_obj, channel_obj)

            sub_images = json.loads(data["sub_images"])
            for sub_image in sub_images:
                sub_image_obj = ImageBucket.objects.get(
                    pk=int(sub_image["pk"]))
                if sub_image["sub_image_index"] != "" and sub_image["sub_image_index"] != "0":
                    sub_image_obj.sub_image_index = int(
                        sub_image["sub_image_index"])
                    sub_image_obj.is_sub_image = True
                else:
                    sub_image_obj.sub_image_index = 0
                    sub_image_obj.is_sub_image = False
                sub_image_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateSubImagesAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


#################################### FLyer Section #######################


class CreateFlyerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            if request.user.has_perm('WAMSApp.add_flyer') == False:
                logger.warning("CreateFlyerAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("CreateFlyerAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            brand_obj = Brand.objects.get(pk=int(data["brand_pk"]))
            organization_obj = brand_obj.organization

            mode = data["mode"]

            flyer_obj = Flyer.objects.create(name=convert_to_ascii(data["name"]),
                                             template_data="{}",
                                             brand=brand_obj,
                                             mode=mode,
                                             user=request.user)

            create_option = data["create_option"]


            common = {
                "background-image-url": "none",
                "border-visible": True,
                "border-color": "#EBEBEB",
                "super-brand-logo": False,
                "iso-logo": False,
                "consumer-logo": False,
                "brand-name-visible": True,
                "white-container": True,
                "price-resizer": "100",
                "product-title-font-size": "12",
                "product-title-font-family": "Helvetica",
                "product-title-font-weight": "bold",
                "product-title-font-color": "#181818",
                "price-font-size": "18",
                "price-font-family": "Helvetica",
                "price-font-weight": "bold",
                "price-font-color": "#181818",
                "currency-font-size": "8.5",
                "currency-font-family": "Helvetica",
                "currency-font-weight": "bold",
                "currency-font-color": "#181818",
                "currency-unit": "AED",
                "price-box-bg-color": "#FBF00B",
                "strikeprice-font-size": "12",
                "strikeprice-font-family": "Helvetica",
                "strikeprice-font-weight": "bold",
                "strikeprice-font-color": "#181818",
                "strikeprice-visible": True,
                "header-color": "#181818",
                "footer-color": "#181818",
                "header-opacity": "1",
                "footer-opacity": "1",
                "all-promo-resizer": "40",
                "all-warranty-resizer": "40",
                "all-image-resizer": "100",
                "all-image-rotator": "0",
                "footer-text": "Your Footer Here"
            }

            template_data = {
                "item-data": [],
                "common": common
            }

            if create_option=="0":
                try:
                    item_data = []
                    flyer_items = int(data["flyer_items"])
                    col = int(data["columns_per_row"])
                    width = int(24/col)
                    height = int(data["grid_item_height"])
                    for i in range(flyer_items):
                        temp_dict = {}
                        temp_dict["container"] = {
                            "x": str((i*width)%24),
                            "y": str(height*(i/col)),
                            "width": str(width),
                            "height": str(height)
                        }
                        temp_dict["data"] = {
                            "image-url": "",
                            "banner-img": "",
                            "warranty-img": "",
                            "image-resizer": "100",
                            "image-rotator": "0",
                            "promo-resizer": "40",
                            "warranty-resizer": "40",
                            "price": "",
                            "strikeprice": "strikeprice",
                            "title": "",
                            "description": ""
                        }

                        item_data.append(temp_dict)
                    template_data["item-data"] = item_data
                    flyer_obj.template_data = json.dumps(template_data)
                    flyer_obj.save()
                
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("CreateFlyerAPI: %s at %s", e, str(exc_tb.tb_lineno))
            
            elif create_option=="1":
                # Read excel file and populate flyer
                try:
                    if data["import_file"] != "undefined" and data["import_file"] != None and data["import_file"] != "":
                        path = default_storage.save('tmp/temp-flyer.xlsx', data["import_file"])
                        path = "http://cdn.omnycomm.com.s3.amazonaws.com/"+path
                        dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
                        rows = len(dfs.iloc[:])
                        item_data = []

                        col = int(data["columns_per_row"])
                        width = int(24/col)
                        height = int(data["grid_item_height"])

                        for i in range(rows):

                            product_title = ""
                            product_description = ""
                            product_price = ""
                            product_strikeprice = ""
                            image_url = ""
                            try:
                                search_id = str(dfs.iloc[i][0]).strip()
                                product_obj = None
                                if Product.objects.filter(product_id=search_id, base_product__brand__organization=organization_obj).exists():
                                    product_obj = Product.objects.filter(product_id=search_id, base_product__brand__organization=organization_obj)[0]
                                elif BaseProduct.objects.filter(seller_sku=search_id, brand__organization=organization_obj).exists():
                                    base_product_obj = BaseProduct.objects.get(seller_sku=search_id, brand__organization=organization_obj)
                                    product_obj = Product.objects.filter(base_product=base_product_obj)[0]

                                flyer_obj.product_bucket.add(product_obj)
                                try:
                                    main_images_objs = MainImages.objects.filter(product = product_obj)
                                    
                                    for main_images_obj in main_images_objs:
                                        if main_images_obj.main_images.filter(is_main_image=True).count() > 0:
                                            break

                                    main_image_obj = main_images_obj.main_images.filter(is_main_image=True)[0]
                                    
                                    try:
                                        image_url = main_image_obj.image.mid_image.url
                                    except Exception as e:
                                        image_url = main_image_obj.image.image.url
                                except Exception as e:
                                    logger.warning("Main image does not exist for product id %s", dfs.iloc[i][0])

                                try:
                                    product_title = convert_to_ascii(dfs.iloc[i][1])
                                    if product_title == "nan":
                                        product_title = product_obj.product_name
                                except Exception as e:
                                    logger.warning("product_title error %s", str(e))

                                try:
                                    product_description = convert_to_ascii(dfs.iloc[i][2])
                                    if product_description=="nan":
                                        product_description = ""
                                except Exception as e:
                                    logger.warning("product_description error %s", str(e))


                                try:
                                    try:
                                        product_strikeprice = str(dfs.iloc[i][3])    
                                    except Exception as e:
                                        product_strikeprice = convert_to_ascii(dfs.iloc[i][3])

                                    if product_strikeprice == "nan":
                                        product_strikeprice = ""
                                    try:
                                        product_strikeprice = product_strikeprice.strip()
                                    except Exception as e:
                                        pass
                                except Exception as e:
                                    logger.warning("product_strikeprice error %s", str(e))


                                try:
                                    try:
                                        product_price = str(dfs.iloc[i][4])
                                    except Exception as e:
                                        product_price = convert_to_ascii(dfs.iloc[i][4])
                                    
                                    if product_price == "nan":
                                        product_price = ""
                                    try:
                                        product_price = product_price.strip()
                                    except Exception as e:
                                        pass
                                except Exception as e:
                                    logger.warning("product_price error %s", str(e))
                                

                            except Exception as e:
                                exc_type, exc_obj, exc_tb = sys.exc_info()
                                logger.error("product index: %s , error: %s at %s", str(i), str(e), str(exc_tb.tb_lineno))

                            temp_dict = {}

                            temp_dict["container"] = {
                                "x": str((i*width)%24),
                                "y": str(height*(i/col)),
                                "width": str(width),
                                "height": str(height)
                            }
                            temp_dict["data"] = {
                                "image-url": str(image_url),
                                "banner-img": "",
                                "warranty-img": "",
                                "image-resizer": "100",
                                "image-rotator": "0",
                                "promo-resizer": "40",
                                "warranty-resizer": "40",
                                "price": str(product_price),
                                "strikeprice": str(product_strikeprice),
                                "title": str(product_title),
                                "description": str(product_description)
                            }
                            item_data.append(temp_dict)

                        template_data["item-data"] = item_data

                        flyer_obj.template_data = json.dumps(template_data)
                        flyer_obj.save()
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("CreateFlyerAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["flyer_pk"] = flyer_obj.pk
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateFlyerAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchFlyerDetailsAPI(APIView):
    
    permission_classes = (permissions.AllowAny,)
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("FetchFlyerDetailsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            flyer_obj = Flyer.objects.get(pk=int(data["pk"]))

            name = flyer_obj.name
            product_objs = flyer_obj.product_bucket.all()
            product_list = []
            images_dict = {}
            for product_obj in product_objs:
                temp_dict = {}
                temp_dict["product_bucket_name"] = product_obj.product_name_sap
                temp_dict["product_bucket_pk"] = product_obj.pk
                temp_dict["seller_sku"] = product_obj.base_product.seller_sku
                main_image_url = Config.objects.all()[0].product_404_image.image.url
                
                try:

                    main_images_objs = MainImages.objects.filter(product = product_obj)
                    main_images_list = []

                    flag=0
                    for main_images_obj in main_images_objs:
                        main_images_list += main_images_obj.main_images.all()
                        if main_images_obj.main_images.filter(is_main_image=True).count() > 0 and flag==0:
                            main_image_obj = main_images_obj.main_images.filter(is_main_image=True)[0]
                            flag = 1

                    main_images_list = set(main_images_list)
                    
                    main_image_url = main_image_obj.image.mid_image.url
                
                except Exception as e:
                    
                    pass
                
                sub_images_objs = SubImages.objects.filter(product = product_obj)
                
                sub_images_list = []
                for sub_images_obj in sub_images_objs:
                    sub_images_list += sub_images_obj.sub_images.all()

                sub_images_list = set(sub_images_list)
                
                temp_dict["product_bucket_image_url"] = main_image_url

                images = {}

                images["main_images"] = create_response_images_flyer_pfl_main_sub(
                    main_images_list)
                images["sub_images"] = create_response_images_flyer_pfl_main_sub(
                    sub_images_list)
                images["pfl_images"] = create_response_images_flyer_pfl(
                    product_obj.pfl_images.all())
                images["white_background_images"] = create_response_images_flyer_pfl(
                    product_obj.white_background_images.all())
                images["lifestyle_images"] = create_response_images_flyer_pfl(
                    product_obj.lifestyle_images.all())
                images["certificate_images"] = create_response_images_flyer_pfl(
                    product_obj.certificate_images.all())
                images["giftbox_images"] = create_response_images_flyer_pfl(
                    product_obj.giftbox_images.all())
                images["diecut_images"] = create_response_images_flyer_pfl(
                    product_obj.diecut_images.all())
                images["aplus_content_images"] = create_response_images_flyer_pfl(
                    product_obj.aplus_content_images.all())
                images["ads_images"] = create_response_images_flyer_pfl(
                    product_obj.ads_images.all())
                images["unedited_images"] = create_response_images_flyer_pfl(
                    product_obj.base_product.unedited_images.all())
                images["transparent_images"] = create_response_images_flyer_pfl(
                    product_obj.transparent_images.all())

                images["all_images"] = images["main_images"]+images["sub_images"]+images["pfl_images"]+images["white_background_images"]+images["lifestyle_images"] + \
                    images["certificate_images"]+images["giftbox_images"]+images["diecut_images"] + \
                    images["aplus_content_images"] + \
                    images["ads_images"]+images["unedited_images"]+images["transparent_images"]

                images_dict[product_obj.pk] = images

                product_list.append(temp_dict)

            template_data = json.loads(flyer_obj.template_data)

            background_image_objs = BackgroundImage.objects.all()
            background_images_bucket = create_response_images_flyer_pfl_main_sub(background_image_objs)

            external_images_bucket_list = []
            external_images_bucket_objs = flyer_obj.external_images_bucket.all()
            for external_images_bucket_obj in external_images_bucket_objs:
                try:
                    temp_dict = {}
                    temp_dict["url"] = external_images_bucket_obj.mid_image.url
                    temp_dict["high_res_url"] = external_images_bucket_obj.image.url
                    temp_dict["image_pk"] = external_images_bucket_obj.pk
                    external_images_bucket_list.append(temp_dict)
                except Exception as e:
                    pass

            brand_image_url = None
            try:
                brand_image_url = flyer_obj.brand.logo.image.url
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("FetchFlyerDetailsAPI: %s at %s",
                               e, str(exc_tb.tb_lineno))

            response["flyer_name"] = name
            response["product_bucket_list"] = product_list
            response["template_data"] = template_data
            response["images"] = images_dict
            response["external_images_bucket_list"] = external_images_bucket_list
            response["background_images_bucket"] = background_images_bucket
            response["brand_image_url"] = brand_image_url
            response["brand-name"] = str(flyer_obj.brand)
            response["mode"] = flyer_obj.mode

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFlyerDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CreatePFLAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            if request.user.has_perm('WAMSApp.add_pfl') == False:
                logger.warning("CreatePFLAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("CreatePFLAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            pfl_obj = PFL.objects.create(name=convert_to_ascii(data["name"]))

            response["pfl_pk"] = pfl_obj.pk
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreatePFLAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchPFLDetailsAPI(APIView):
    
    permission_classes = (permissions.AllowAny,)
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("FetchPFLDetailsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            pfl_obj = PFL.objects.get(pk=int(data["pk"]))

            pfl_name = pfl_obj.name
            product_image = {"image_url": None, "image_pk": None}
            try:
                product_image["image_url"] = pfl_obj.product_image.image.url
                product_image["image_pk"] = pfl_obj.product_image.pk
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("FetchPFLDetailsAPI: %s at %s",
                               e, str(exc_tb.tb_lineno))

            pfl_product_features = []
            pfl_product_name = ""
            seller_sku = ""
            if pfl_obj.product != None:
                try:
                    pfl_product_features = json.loads(
                        pfl_obj.product.pfl_product_features)
                except Exception as e:
                    pfl_product_features = []

                pfl_product_name = pfl_obj.product.pfl_product_name
                seller_sku = pfl_obj.product.base_product.seller_sku

            external_images_bucket_list = []
            external_images_bucket_objs = pfl_obj.external_images_bucket.all()
            for external_images_bucket_obj in external_images_bucket_objs:
                try:
                    temp_dict = {}
                    temp_dict["url"] = external_images_bucket_obj.mid_image.url
                    temp_dict["high_res_url"] = external_images_bucket_obj.image.url
                    temp_dict["image_pk"] = external_images_bucket_obj.pk
                    external_images_bucket_list.append(temp_dict)
                except Exception as e:
                    pass

            logo_image_url = None
            barcode_image_url = None
            brand_name = None
            product_id = ""
            product_pk = None
            product_main_image_url = None
            product_name_sap = ""
            seller_sku = ""
            if pfl_obj.product != None:
                try:
                    brand_obj = pfl_obj.product.base_product.brand
                    brand_name = brand_obj.name
                    logo_image_url = brand_obj.logo.image.url
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.warning("FetchPFLDetailsAPI: %s at %s",
                                   e, str(exc_tb.tb_lineno))

                try:
                    barcode_image_url = pfl_obj.product.barcode.image.url
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.warning("FetchPFLDetailsAPI: %s at %s",
                                   e, str(exc_tb.tb_lineno))

                product_id = pfl_obj.product.product_id
                product_pk = pfl_obj.product.pk
                
                try:

                    main_images_objs = MainImages.objects.filter(product = pfl_obj.product)
                    for main_images_obj in main_images_objs:
                        if main_images_obj.main_images.filter(is_main_image=True).count() > 0:
                            break

                    main_image_obj = main_images_obj.main_images.filter(is_main_image=True)[0]
                    
                    product_main_image_url = main_image_obj.image.image.url
                
                except Exception as e:

                    product_main_image_url = Config.objects.all()[0].product_404_image.image.url

                product_name_sap = pfl_obj.product.product_name_sap
                seller_sku = pfl_obj.product.base_product.seller_sku

            template_data = {
                "container": {
                    "width": 24,
                    "height": 15,
                    "x": 0,
                    "y": 0
                },
                "common": {
                  "image-resizer": 100,
                  "product-title-font-size": "25",
                  "product-title-font-family": "Helvetica",
                  "product-title-font-weight": "normal",
                  "product-title-font-color": "#181818",
                  "seller-sku-font-size": "12",
                  "seller-sku-font-family": "Helvetica",
                  "seller-sku-font-weight": "normal",
                  "seller-sku-font-color": "#181818",
                  "feature-font-size": "12",
                  "feature-font-family": "Helvetica",
                  "feature-font-weight": "normal",
                  "feature-font-color": "#181818",
                  "header-color": "#573B93",
                  "footer-color": "#573B93"
                }
            }
            try:
                template_data = json.loads(pfl_obj.template_data)
            except Exception as e:
                pass

            response["pfl_name"] = pfl_name
            response["product_name"] = pfl_product_name
            response["product_name_sap"] = product_name_sap
            response["product_image"] = product_image
            response["pfl_product_features"] = pfl_product_features
            response["external_images_bucket_list"] = external_images_bucket_list
            response["template_data"] = template_data
            response["logo_image_url"] = logo_image_url
            response["brand_name"] = brand_name
            response["barcode_image_url"] = barcode_image_url
            response["product_id"] = product_id
            response["product_pk"] = product_pk
            response["product_main_image_url"] = product_main_image_url
            response["seller_sku"] = seller_sku

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchPFLDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchProductListFlyerPFLAPI(APIView):

    permission_classes = (permissions.AllowAny,)
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("FetchProductListFlyerPFLAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            #product_objs = custom_permission_filter_products(request.user)
            product_objs = Product.objects.all()

            try:
                if "flyer_pk" in data:
                    brand_obj = Flyer.objects.get(
                        pk=int(data["flyer_pk"])).brand
                    product_objs = product_objs.filter(base_product__brand=brand_obj)
                    search_string = data["search_string"]
                    product_objs = product_objs.filter(Q(base_product__seller_sku__icontains=search_string) | Q(product_name__icontains=search_string))[:10]
                    
            except Exception as e:
                logger.warning("Issue with filtering brands %s", str(e))

            product_list = []
            cnt = 1
            char_len = 80
            for product_obj in product_objs:
                try:
                    if has_atleast_one_image(product_obj)==False:
                        continue

                    temp_dict = {}
                    temp_dict["product_pk"] = product_obj.pk
                    temp_dict["product_name"] = product_obj.product_name_sap
                    short_product_name = str(product_obj.product_name_sap)
                    if len(short_product_name)>char_len:
                        short_product_name = short_product_name[:char_len] + "..."
                    temp_dict["product_name_autocomplete"] = short_product_name + " | " + str(product_obj.base_product.seller_sku) + " | " + str(product_obj.product_id)
                    main_image_url = None
                    
                    try:

                        main_images_objs = MainImages.objects.filter(product = product_obj)
                        for main_images_obj in main_images_objs:
                            if main_images_obj.main_images.filter(is_main_image=True).count() > 0:
                                break

                        main_image_obj = main_images_obj.main_images.filter(is_main_image=True)[0]
                        
                        main_image_url = main_image_obj.image.thumbnail.url
                    
                    except Exception as e:

                        main_image_url = Config.objects.all()[0].product_404_image.image.url

                    temp_dict["main_image_url"] = main_image_url
                    product_list.append(temp_dict)
                except Exception as e:
                    cnt += 1
                    pass

            response["product_list"] = product_list

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductListFlyerPFLAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddProductFlyerBucketAPI(APIView):

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            # if request.user.has_perm('WAMSApp.change_flyer') == False:
            #     logger.warning("AddProductFlyerBucketAPI Restricted Access!")
            #     response['status'] = 403
            #     return Response(data=response)

            data = request.data
            logger.info("AddProductFlyerBucketAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            flyer_obj = Flyer.objects.get(pk=int(data["flyer_pk"]))

            organization_obj = CustomPermission.objects.get(user__username=request.user.username).organization

            product_id = data["product_name"].split("|")[-1].strip()
            product_obj = Product.objects.get(product_id=product_id, base_product__brand__organization=organization_obj)

            flyer_obj.product_bucket.add(product_obj)
            flyer_obj.save()

            image_url = Config.objects.all()[0].product_404_image.image.url
            
            try:

                main_images_objs = MainImages.objects.filter(product = product_obj)
                
                main_images_list = []
                flag=0
                for main_images_obj in main_images_objs:
                    main_images_list += main_images_obj.main_images.all()
                    if main_images_obj.main_images.filter(is_main_image=True).count() > 0 and flag==0:
                        main_image_obj = main_images_obj.main_images.filter(is_main_image=True)[0]
                        flag=1

                main_images_list = set(main_images_list)
                
                image_url = main_image_obj.image.mid_image.url
            
            except Exception as e:
                pass

            sub_images_list = []
            sub_images_objs = SubImages.objects.filter(product=product_obj)
            
            for sub_images_obj in sub_images_objs:
                sub_images_list+=sub_images_obj.sub_images.all()
            
            sub_images_list = set(sub_images_list)

            images = {}

            images["main_images"] = create_response_images_flyer_pfl_main_sub(
                main_images_list)
            images["sub_images"] = create_response_images_flyer_pfl_main_sub(
                sub_images_list)
            images["pfl_images"] = create_response_images_flyer_pfl(
                product_obj.pfl_images.all())
            images["white_background_images"] = create_response_images_flyer_pfl(
                product_obj.white_background_images.all())
            images["lifestyle_images"] = create_response_images_flyer_pfl(
                product_obj.lifestyle_images.all())
            images["certificate_images"] = create_response_images_flyer_pfl(
                product_obj.certificate_images.all())
            images["giftbox_images"] = create_response_images_flyer_pfl(
                product_obj.giftbox_images.all())
            images["diecut_images"] = create_response_images_flyer_pfl(
                product_obj.diecut_images.all())
            images["aplus_content_images"] = create_response_images_flyer_pfl(
                product_obj.aplus_content_images.all())
            images["ads_images"] = create_response_images_flyer_pfl(
                product_obj.ads_images.all())
            images["unedited_images"] = create_response_images_flyer_pfl(
                product_obj.base_product.unedited_images.all())
            images["transparent_images"] = create_response_images_flyer_pfl(
                product_obj.transparent_images.all())

            images["all_images"] = images["main_images"]+images["sub_images"]+images["pfl_images"]+images["white_background_images"]+images["lifestyle_images"] + \
                images["certificate_images"]+images["giftbox_images"]+images["diecut_images"] + \
                images["aplus_content_images"] + \
                images["ads_images"]+images["unedited_images"]+images["transparent_images"]

            response["images"] = images
            response["product_pk"] = product_obj.pk
            response["product_name"] = product_obj.product_name_sap
            response["product_image_url"] = image_url
            response["seller_sku"] = product_obj.base_product.seller_sku

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddProductFlyerBucketAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddProductPFLBucketAPI(APIView):

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            # if request.user.has_perm('WAMSApp.change_pfl') == False:
            #     logger.warning("AddProductPFLBucketAPI Restricted Access!")
            #     response['status'] = 403
            #     return Response(data=response)

            data = request.data
            logger.info("AddProductPFLBucketAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            pfl_obj = PFL.objects.get(pk=int(data["pfl_pk"]))

            product_id = data["product_name"].split("|")[1].strip()
            product_obj = Product.objects.get(product_id=product_id)

            pfl_obj.product = product_obj
            pfl_obj.save()

            seller_sku = product_obj.seller_sku
            image_url = None

            main_images_objs = MainImages.objects.filter(product = product_obj)
            
            for main_images_obj in main_images_objs:
                if main_images_obj.main_images.filter(is_main_image=True).count() > 0:
                    main_image_obj = main_images_obj.main_images.filter(is_main_image=True)[0]
                    image_url = main_image_obj.image.image.url
                    break

            response["product_name"] = product_obj.product_name_sap
            response["product_pk"] = product_obj.pk
            response["image_url"] = image_url
            response["seller_sku"] = seller_sku

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddProductPFLBucketAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchProductDetailsFlyerPFLAPI(APIView):
    
    permission_classes = (permissions.AllowAny,)    
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("FetchProductDetailsFlyerPFLAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            pfl_obj = PFL.objects.get(pk=int(data["pfl_pk"]))
            product_obj = Product.objects.get(pk=int(data["product_pk"]))
            product_name = product_obj.product_name_sap
            product_price = product_obj.outdoor_price
            product_id = product_obj.product_id

            images = {}

            main_images_objs = MainImages.objects.filter(product = product_obj)
            
            main_images_list = []
            for main_images_obj in main_images_objs:
                main_images_list += main_images_obj.main_images.all()

            main_images_list = set(main_images_list)

            sub_images_objs = SubImages.objects.filter(product = product_obj)
            
            sub_images_list = []
            for sub_images_obj in sub_images_objs:
                sub_images_list += sub_images_obj.sub_images.all()

            sub_images_list = set(sub_images_list)

            images["main_images"] = create_response_images_flyer_pfl_main_sub(
                main_images_list)
            images["sub_images"] = create_response_images_flyer_pfl_main_sub(
                sub_images_list)
            images["pfl_images"] = create_response_images_flyer_pfl(
                product_obj.pfl_images.all())
            images["white_background_images"] = create_response_images_flyer_pfl(
                product_obj.white_background_images.all())
            images["lifestyle_images"] = create_response_images_flyer_pfl(
                product_obj.lifestyle_images.all())
            images["certificate_images"] = create_response_images_flyer_pfl(
                product_obj.certificate_images.all())
            images["giftbox_images"] = create_response_images_flyer_pfl(
                product_obj.giftbox_images.all())
            images["diecut_images"] = create_response_images_flyer_pfl(
                product_obj.diecut_images.all())
            images["aplus_content_images"] = create_response_images_flyer_pfl(
                product_obj.aplus_content_images.all())
            images["ads_images"] = create_response_images_flyer_pfl(
                product_obj.ads_images.all())
            images["unedited_images"] = create_response_images_flyer_pfl(
                product_obj.base_product.unedited_images.all())
            images["transparent_images"] = create_response_images_flyer_pfl(
                product_obj.transparent_images.all())
            images["pfl_generated_images"] = create_response_images_flyer_pfl(
                product_obj.pfl_generated_images.all())
            images["external_images"] = create_response_images_flyer_pfl(
                pfl_obj.external_images_bucket.all())

            images["all_images"] = images["main_images"]+images["sub_images"]+images["pfl_images"]+images["white_background_images"]+images["lifestyle_images"] + \
                    images["certificate_images"]+images["giftbox_images"]+images["diecut_images"] + \
                    images["aplus_content_images"] + \
                    images["ads_images"]+images["unedited_images"]+images["transparent_images"]

            barcode_image_url = None
            if product_obj.barcode != None:
                barcode_image_url = product_obj.barcode.image.url

            brand_obj = product_obj.base_product.brand
            brand_name = "" if brand_obj == None else brand_obj.name
            logo_image_url = ''
            logo_image_url = None

            try:
                logo_image_url = brand_obj.logo.image.url
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(
                    "FetchProductDetailsFlyerPFLAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["product_name"] = product_name
            response["product_id"] = product_id
            response["product_price"] = product_price
            response["images"] = images
            response["barcode_image_url"] = barcode_image_url
            response["brand_name"] = brand_name
            response["logo_image_url"] = logo_image_url
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductDetailsFlyerPFLAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveFlyerTemplateAPI(APIView):

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            # if request.user.has_perm('WAMSApp.change_flyer') == False:
            #     logger.warning("SaveFlyerTemplateAPI Restricted Access!")
            #     response['status'] = 403
            #     return Response(data=response)

            data = request.data
            logger.info("SaveFlyerTemplateAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            flyer_obj = Flyer.objects.get(pk=int(data["flyer_pk"]))
            flyer_obj.template_data = data["template_data"]
            flyer_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveFlyerTemplateAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SavePFLTemplateAPI(APIView):

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            # if request.user.has_perm('WAMSApp.change_pfl') == False:
            #     logger.warning("SavePFLTemplateAPI Restricted Access!")
            #     response['status'] = 403
            #     return Response(data=response)

            data = request.data
            logger.info("SavePFLTemplateAPI: %s", str(data))

            pfl_obj = PFL.objects.get(pk=int(data["pfl_pk"]))

            if data["image_pk"] != None and data["image_pk"] != "":
                image_obj = Image.objects.get(pk=data["image_pk"])
                pfl_obj.product_image = image_obj

            template_data = data["template_data"]

            product_name = convert_to_ascii(data["product_name"])
            product_features = convert_to_ascii(data["product_features"])

            pfl_obj.product.pfl_product_name = product_name
            pfl_obj.product.pfl_product_features = product_features
            pfl_obj.product.save()
            pfl_obj.template_data = template_data
            pfl_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SavePFLTemplateAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadImageExternalBucketFlyerAPI(APIView):

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("UploadImageExternalBucketFlyerAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            flyer_obj = Flyer.objects.get(pk=int(data["flyer_pk"]))
            image_obj = Image.objects.create(image=data["image"])
            flyer_obj.external_images_bucket.add(image_obj)
            flyer_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadImageExternalBucketFlyerAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadImageExternalBucketPFLAPI(APIView):

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("UploadImageExternalBucketPFLAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            pfl_obj = PFL.objects.get(pk=int(data["pfl_pk"]))
            image_obj = Image.objects.create(image=data["image"])
            pfl_obj.external_images_bucket.add(image_obj)
            pfl_obj.product_image = image_obj
            pfl_obj.save()

            response["image_url"] = image_obj.image.url
            response["image_pk"] = image_obj.pk
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadImageExternalBucketPFLAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchPFLListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("FetchPFLListAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            page = int(data["page"])

            all_pfl_objs = custom_permission_filter_pfls(request.user)
            pfl_objs = custom_permission_filter_pfls(request.user)

            all_pfl_objs = all_pfl_objs.exclude(
                product__pfl_product_features="[]")
            pfl_objs = pfl_objs.exclude(product__pfl_product_features="[]")

            for pfl_obj in all_pfl_objs:
                try:
                    if len(json.loads(pfl_obj.product.pfl_product_features)) < 3:
                        pfl_objs = pfl_objs.exclude(pk=pfl_obj.pk)
                except Exception as e:
                    pass

            chip_data = json.loads(data["tags"])
            if len(chip_data) > 0:
                search_list_objs = []
                for chip in chip_data:
                    search = pfl_objs.filter(
                        Q(product__product_name_sap__icontains=chip.lower()) |
                        Q(name__icontains=chip.lower()) |
                        Q(product__product_name_icontains=chip.lower()) |
                        Q(product__product_id__icontains=chip.lower()) |
                        Q(product__seller_sku__icontains=chip.lower())
                    )
                    for prod in search:
                        search_list_objs.append(prod)
                pfl_objs = list(set(search_list_objs))

            total_results = len(pfl_objs)
            paginator = Paginator(pfl_objs, 20)
            pfl_objs = paginator.page(page)

            pfl_list = []
            for pfl_obj in pfl_objs:
                temp_dict = {}
                temp_dict["pfl_name"] = pfl_obj.name
                temp_dict["pfl_pk"] = pfl_obj.pk
                temp_dict["product_name"] = ""
                temp_dict["product_id"] = ""
                if pfl_obj.product is not None:
                    temp_dict["product_name"] = pfl_obj.product.product_name_sap
                    temp_dict["product_id"] = pfl_obj.product.product_id

                # Update this later
                if pfl_obj.product is not None:
                    if pfl_obj.product.pfl_generated_images.all().count() > 0:
                        temp_dict["product_image_url"] = pfl_obj.product.pfl_generated_images.all()[
                            0].image.url
                    else:
                        temp_dict["product_image_url"] = Config.objects.all()[
                            0].product_404_image.image.url
                else:
                    temp_dict["product_image_url"] = Config.objects.all()[
                        0].product_404_image.image.url

                pfl_list.append(temp_dict)

            is_available = True
            if paginator.num_pages == page:
                is_available = False

            response["is_available"] = is_available
            response["total_results"] = total_results

            response["pfl_list"] = pfl_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchPFLListAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchFlyerListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("FetchFlyerListAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            page = int(data["page"])

            permissible_brands = custom_permission_filter_brands(request.user)
            flyer_objs = Flyer.objects.filter(brand__in=permissible_brands).order_by('-pk')

            chip_data = data["tags"]

            if len(chip_data) > 0:
                flyer_objs = Flyer.objects.all().order_by('-pk')
                search_list_objs = []

                for flyer_obj in flyer_objs:

                    flag = False
                    for chip in chip_data:
                        if chip.lower() in flyer_obj.name.lower():
                            flag = True
                            search_list_objs.append(flyer_obj)
                            break

                    if flag:
                        continue

                    for product in flyer_obj.product_bucket.all():
                        for chip in chip_data:
                            if (chip.lower() in product.product_name_sap.lower() or
                                    chip.lower() in product.product_name.lower() or
                                    chip.lower() in product.product_id.lower() or
                                    chip.lower() in product.base_product.seller_sku.lower()):
                                search_list_objs.append(flyer_obj)
                                break
                flyer_objs = list(set(search_list_objs))

            total_results = len(flyer_objs)
            paginator = Paginator(flyer_objs, 20)
            flyer_objs = paginator.page(page)

            flyer_list = []
            for flyer_obj in flyer_objs:
                temp_dict = {}
                temp_dict["flyer_name"] = flyer_obj.name
                temp_dict["flyer_pk"] = flyer_obj.pk
                # Update this later
                if flyer_obj.flyer_image != None:
                    temp_dict["flyer_image"] = flyer_obj.flyer_image.mid_image.url
                else:
                    temp_dict["flyer_image"] = Config.objects.all()[
                        0].product_404_image.image.url
                flyer_list.append(temp_dict)

            is_available = True
            if paginator.num_pages == page:
                is_available = False

            response["is_available"] = is_available
            response["total_results"] = total_results

            response["flyer_list"] = flyer_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFlyerListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadNewFlyerBGImageAPI(APIView):

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            # if request.user.has_perm('WAMSApp.change_flyer') == False:
            #     logger.warning("UploadNewFlyerBGImageAPI Restricted Access!")
            #     response['status'] = 403
            #     return Response(data=response)

            data = request.data
            logger.info("UploadNewFlyerBGImageAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            image_obj = Image.objects.create(image=data["bg_image"])
            BackgroundImage.objects.create(image=image_obj)

            response["bg_image_url"] = image_obj.image.url
            response["bg_image_pk"] = image_obj.pk
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadNewFlyerBGImageAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadFlyerTagAPI(APIView):

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            # if request.user.has_perm('WAMSApp.change_flyer') == False:
            #     logger.warning("UploadNewFlyerBGImageAPI Restricted Access!")
            #     response['status'] = 403
            #     return Response(data=response)

            data = request.data
            logger.info("UploadFlyerTagAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            image_obj = Image.objects.create(image=data["tag_image"])
            TagBucket.objects.create(image=image_obj)

            response["tag_image_url"] = image_obj.image.url
            response["tag_image_pk"] = image_obj.pk
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadFlyerTagAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadFlyerPriceTagAPI(APIView):

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            # if request.user.has_perm('WAMSApp.change_flyer') == False:
            #     logger.warning("UploadNewFlyerBGImageAPI Restricted Access!")
            #     response['status'] = 403
            #     return Response(data=response)

            data = request.data
            logger.info("UploadFlyerPriceTagAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            image_obj = Image.objects.create(image=data["price_tag_image"])
            PriceTagBucket.objects.create(image=image_obj)

            response["price_tag_image_url"] = image_obj.image.url
            response["price_tag_image_pk"] = image_obj.pk
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadFlyerPriceTagAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)



class DownloadImagesS3API(APIView):

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("DownloadImagesS3API: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            links = json.loads(data['links'])

            # [{"key": "grind-1", "url": "aws/im1.png"}, {}]

            s3 = boto3.client('s3',
                              aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                              aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

            local_links = []
            
            for link in links:
                try:
                    if "url" not in link or link["url"]=="":
                        continue
                    filename = urllib.parse.unquote(link["url"])
                    filename = "/".join(filename.split("/")[3:])
                    temp_dict = {}
                    temp_dict["key"] = link["key"]
                    temp_dict["url"] = "/files/images_s3/" + str(filename)
                    local_links.append(temp_dict)

                    s3.download_file(settings.AWS_STORAGE_BUCKET_NAME,
                                     filename, "." + temp_dict["url"])
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("DownloadImagesS3API: %s at %s",
                                 e, str(exc_tb.tb_lineno))    

            response['local_links'] = local_links
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DownloadImagesS3API: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchBrandsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("FetchBrandsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            brand_objs = None
            if FactoryUser.objects.filter(username=request.user.username).exists():
                brand_objs = Brand.objects.all()
            else:
                brand_objs = custom_permission_filter_brands(request.user)
            
            brand_list = []
            for brand_obj in brand_objs:
                temp_dict = {}
                temp_dict["name"] = brand_obj.name
                temp_dict["name_ar"] = brand_obj.name_ar
                temp_dict["pk"] = brand_obj.pk
                brand_list.append(temp_dict)

            response["brand_list"] = brand_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchBrandsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchChannelsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("FetchChannelsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            channel_objs = custom_permission_filter_channels(request.user)
            channel_list = []
            
            for channel_obj in channel_objs:
                temp_dict = {}
                temp_dict["name"] = channel_obj.name
                temp_dict["pk"] = channel_obj.pk
                channel_list.append(temp_dict)

            response["channel_list"] = channel_list
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchChannelsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SavePFLInBucketAPI(APIView):

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("SavePFLInBucketAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            image_obj = None

            if "product_pk" in data:
                product_obj = Product.objects.get(pk=int(data["product_pk"]))

                image_decoded = decode_base64_file(data["image_data"])
                image_obj = Image.objects.create(image=image_decoded)
                product_obj.pfl_generated_images.clear()
                product_obj.pfl_generated_images.add(image_obj)
                product_obj.save()
            
            elif "pfl_pk" in data:
                image_decoded = decode_base64_file(data["image_data"])
                image_obj = Image.objects.create(image=image_decoded)
                pfl_obj = PFL.objects.get(pk=int(data["pfl_pk"]))
                product_obj = pfl_obj.product
                product_obj.pfl_generated_images.clear()
                product_obj.pfl_generated_images.add(image_obj)
                product_obj.save()

            response["main-url"] = image_obj.image.url
            response["midimage-url"] = image_obj.mid_image.url
            response["thumbnail-url"] = image_obj.thumbnail.url

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SavePFLInBucketAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveFlyerInBucketAPI(APIView):

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            #logger.info("SavePFLInBucketAPI: %s", str(data))
            logger.info("SavePFLInBucketAPI called")

            if not isinstance(data, dict):
                data = json.loads(data)

            flyer_obj = Flyer.objects.get(pk=int(data["flyer_pk"]))

            image_decoded = decode_base64_file(data["image_data"])
            image_obj = Image.objects.create(image=image_decoded)
            flyer_obj.flyer_image = image_obj
            flyer_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveFlyerInBucketAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class VerifyProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("VerifyProductAPI: %s", str(data))
            
            if not isinstance(data, dict):
                data = json.loads(data)

            custom_permission_obj = CustomPermission.objects.get(user=request.user)
            if custom_permission_obj.verify_product==False:
                logger.warning("VerifyProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            product_obj = Product.objects.get(pk=int(data["product_pk"]))
            verify = data["verify"]
            product_obj.verified = verify
            if verify:
                product_obj.partially_verified = verify

            product_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("VerifyProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class LockProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("LockProductAPI: %s", str(data))
            
            if not isinstance(data, dict):
                data = json.loads(data)

            custom_permission_obj = CustomPermission.objects.get(user=request.user)
            if custom_permission_obj.verify_product==False:
                logger.warning("LockProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            product_obj = Product.objects.get(pk=int(data["product_pk"]))
            locked = data["locked"]
            product_obj.locked = locked

            product_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("LockProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CopyBestImagesAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("CopyBestImagesAPI: %s", str(data))
            
            if not isinstance(data, dict):
                data = json.loads(data)

            if request.user.has_perm('WAMSApp.add_image') == False:
                logger.warning("CopyBestImagesAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            product_obj = Product.objects.get(pk=int(data["product_pk"]))
            image_pk_list = data["image_pk_list"]

            number = 0
            if product_obj.best_images.count()>0:
                number = ProductImage.objects.filter(product=product_obj).order_by('number').last().number
            
            for image_pk in image_pk_list:
                image_obj = Image.objects.get(pk=int(image_pk))
                if ProductImage.objects.filter(product=product_obj, image=image_obj).exists():
                    continue
                number += 1
                ProductImage.objects.create(image=image_obj, product=product_obj, number=number)

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CopyBestImagesAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class RemoveImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("RemoveImageAPI: %s", str(data))
            
            if not isinstance(data, dict):
                data = json.loads(data)

            if request.user.has_perm('WAMSApp.delete_image') == False:
                logger.warning("RemoveImageAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            product_obj = Product.objects.get(pk=int(data["product_pk"]))
            image_pk = data["image_pk"]
            image_obj = Image.objects.get(pk=int(image_pk))

            if data["image_category"] == "pfl_images":
                product_obj.pfl_images.remove(image_obj)
            elif data["image_category"] == "white_background_images":
                product_obj.white_background_images.remove(image_obj)
            elif data["image_category"] == "lifestyle_images":
                product_obj.lifestyle_images.remove(image_obj)
            elif data["image_category"] == "certificate_images":
                product_obj.certificate_images.remove(image_obj)
            elif data["image_category"] == "giftbox_images":
                product_obj.giftbox_images.remove(image_obj)
            elif data["image_category"] == "diecut_images":
                product_obj.diecut_images.remove(image_obj)
            elif data["image_category"] == "aplus_content_images":
                product_obj.aplus_content_images.remove(image_obj)
            elif data["image_category"] == "ads_images":
                product_obj.ads_images.remove(image_obj)
            elif data["image_category"] == "unedited_images":
                product_obj.base_product.unedited_images.remove(image_obj)
            elif data["image_category"] == "transparent_images":
                product_obj.transparent_images.remove(image_obj)
            elif data["image_category"] == "best_images":
                ProductImage.objects.get(product=product_obj, image=image_obj).delete()
                
            product_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("RemoveImageAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DeleteImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            if request.user.has_perm('WAMSApp.delete_image') == False:
                logger.warning("DeleteImageAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("DeleteImageAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            image_type = data["image_type"]
            image_pk = int(data["image_pk"])
            channel_name = data["channel_name"]
            product_pk = data["product_pk"]

            product_obj = Product.objects.get(pk=product_pk)
            if product_obj.locked:
                logger.warning("DeleteImageAPI Restricted Access - Locked!")
                response['status'] = 403
                return Response(data=response)

            if image_type == "other":
                Image.objects.get(pk=int(image_pk)).delete()
            elif image_type == "main":
                main_images_obj = None
                if channel_name=="":
                    main_images_obj = MainImages.objects.get(product__pk=product_pk, is_sourced=True)
                elif channel_name in ["Amazon UK", "Amazon UAE", "Ebay", "Noon"]:
                    main_images_obj = MainImages.objects.get(product__pk=product_pk, channel__name=channel_name)

                image_bucket_obj = ImageBucket.objects.get(pk=int(image_pk))
                main_images_obj.main_images.remove(image_bucket_obj)
                main_images_obj.save()

            elif image_type == "sub":
                sub_images_obj = None
                if channel_name=="":
                    sub_images_obj = SubImages.objects.get(product__pk=product_pk, is_sourced=True)
                elif channel_name in ["Amazon UK", "Amazon UAE", "Ebay", "Noon"]:
                    sub_images_obj = SubImages.objects.get(product__pk=product_pk, channel__name=channel_name)

                image_bucket_obj = ImageBucket.objects.get(pk=int(image_pk))
                sub_images_obj.sub_images.remove(image_bucket_obj)
                sub_images_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteImageAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class RemoveProductFromExportListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            if request.user.has_perm('WAMSApp.change_exportlist') == False:
                logger.warning(
                    "RemoveProductFromExportListAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("RemoveProductFromExportListAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_pk = int(data["product_pk"])
            export_pk = int(data["export_pk"])

            export_obj = ExportList.objects.get(pk=export_pk)
            product_obj = Product.objects.get(pk=product_pk)

            export_obj.products.remove(product_obj)
            export_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("RemoveProductFromExportListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadFlyerExternalImagesAPI(APIView):

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            # if request.user.has_perm("WAMSApp.add_image") == False:
            #     logger.warning("UploadProductImageAPI Restricted Access!")
            #     response['status'] = 403
            #     return Response(data=response)

            data = request.data
            logger.info("UploadFlyerExternalImagesAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            flyer_obj = Flyer.objects.get(pk=int(data["flyer_pk"]))

            image_count = int(data["image_count"])
            external_images_bucket_list = []
            for i in range(image_count):
                try:
                    image_obj = Image.objects.create(image=data["image_"+str(i)])
                    flyer_obj.external_images_bucket.add(image_obj)
                    temp_dict = {}
                    temp_dict["url"] = image_obj.mid_image.url
                    temp_dict["high_res_url"] = image_obj.image.url
                    external_images_bucket_list.append(temp_dict)
                except Exception as e:
                    pass

            flyer_obj.save()

            response["external_images_bucket_list"] = external_images_bucket_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadFlyerExternalImagesAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadPFLExternalImagesAPI(APIView):

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            # if request.user.has_perm("WAMSApp.add_image") == False:
            #     logger.warning("UploadPFLExternalImagesAPI Restricted Access!")
            #     response['status'] = 403
            #     return Response(data=response)

            data = request.data
            logger.info("UploadFlyerExternalImagesAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            pfl_obj = PFL.objects.get(pk=int(data["pfl_pk"]))

            image_count = int(data["image_count"])
            
            external_images_bucket_list = []
            for i in range(image_count):
                try:
                    image_obj = Image.objects.create(image=data["image_"+str(i)])
                    pfl_obj.external_images_bucket.add(image_obj)
                    temp_dict = {}
                    temp_dict["url"] = image_obj.mid_image.url
                    temp_dict["high_res_url"] = image_obj.image.url
                    external_images_bucket_list.append(temp_dict)
                except Exception as e:
                    pass

            pfl_obj.save()

            response["external_images_bucket_list"] = external_images_bucket_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadFlyerExternalImagesAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class SapIntegrationAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("SapIntegrationAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_obj = Product.objects.get(pk=data["product_pk"])
            seller_sku = product_obj.base_product.seller_sku

            url="http://wig.westernint.com:8000/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"
            #headers = {'content-type': 'application/soap+xml'}
            #headers = {'content-type': 'text/xml'}
            headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}

            credentials = ("MOBSERVICE", "~lDT8+QklV=(")

            company_codes = []

            warehouses_information = []

            if product_obj.base_product.brand.name == "Geepas":
                company_codes = ["1070","1000"]
            elif product_obj.base_product.brand.name == "Royalford":
                company_codes = ["3000"]
            elif product_obj.base_product.brand.name == "Olsenmark":
                company_codes = ["3050"]
            elif product_obj.base_product.brand.name == "Crystal":
                company_codes = ["5110"]


            for company_code in company_codes:
                warehouse_dict = {}
                
                body = """<soapenv:Envelope xmlns:urn="urn:sap-com:document:sap:rfc:functions" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
                <soapenv:Header />
                <soapenv:Body>
                <urn:ZAPP_STOCK_PRICE>

                 <IM_MATNR>
                  <item>
                   <MATNR>""" + seller_sku + """</MATNR>
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
                
                warehouse_dict["company_code"] = company_code

                items = content["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_STOCK_PRICEResponse"]["T_DATA"]["item"]
                EX_EA = 0.0
                IC_EA = 0.0
                OD_EA = 0.0
                RET_EA = 0.0
                qty=0.0

                if isinstance(items, dict):
                    temp_price = items["EX_EA"]
                    if temp_price!=None:
                        temp_price = float(temp_price)
                        EX_EA = max(temp_price, EX_EA)
                    temp_price = items["IC_EA"]
                    if temp_price!=None:
                        temp_price = float(temp_price)
                        IC_EA = max(temp_price, IC_EA)
                    temp_price = items["OD_EA"]
                    if temp_price!=None:
                        temp_price = float(temp_price)
                        OD_EA = max(temp_price, OD_EA)
                    temp_price = items["RET_EA"]
                    if temp_price!=None:
                        temp_price = float(temp_price)
                        RET_EA = max(temp_price, RET_EA)
                    temp_qty = items["TOT_QTY"]
                    if temp_qty!=None:
                        temp_qty = float(temp_qty)
                        qty = max(temp_qty, qty)
                else:
                    for item in items:
                        temp_price = item["EX_EA"]
                        if temp_price!=None:
                            temp_price = float(temp_price)
                            EX_EA = max(temp_price, EX_EA)
                        temp_price = item["IC_EA"]
                        if temp_price!=None:
                            temp_price = float(temp_price)
                            IC_EA = max(temp_price, IC_EA)
                        temp_price = item["OD_EA"]
                        if temp_price!=None:
                            temp_price = float(temp_price)
                            OD_EA = max(temp_price, OD_EA)
                        temp_price = item["RET_EA"]
                        if temp_price!=None:
                            temp_price = float(temp_price)
                            RET_EA = max(temp_price, RET_EA)
                        temp_qty = item["TOT_QTY"]
                        if temp_qty!=None:
                            temp_qty = float(temp_qty)
                            qty = max(temp_qty, qty)
                
                prices = {}
                prices["EX_EA"] = str(EX_EA)
                prices["IC_EA"] = str(IC_EA)
                prices["OD_EA"] = str(OD_EA)
                prices["RET_EA"] = str(RET_EA)
                
                warehouse_dict["prices"] = prices
                warehouse_dict["qty"] = qty

                warehouses_information.append(warehouse_dict)

            response['warehouses_information'] = warehouses_information
            response['status'] = 200
                
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SapIntegrationAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchUserProfileAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data
            
            content_manager = OmnyCommUser.objects.get(username=request.user.username)

            response["contact_number"] = "" if content_manager.contact_number==None else content_manager.contact_number
            response["designation"] = "" if content_manager.designation==None else content_manager.designation

            response["username"] = content_manager.username
            response["first_name"] = content_manager.first_name
            response["last_name"] = content_manager.last_name
            response["email"] = "" if content_manager.email==None else content_manager.email
            
            permissible_brands = custom_permission_filter_brands(request.user)
            
            response["permissible_brands"] = []
            for brand in permissible_brands:
                response["permissible_brands"].append(brand.name)
            
            response["img_url"] = ""
            if content_manager.image!=None:
                response["img_url"] = content_manager.image.image.url

            user = request.user
            permissions = user.user_permissions.all()

            permissions_dict = {}

            custom_permission_obj = CustomPermission.objects.get(user=user)

            if(custom_permission_obj.brands.all().count()):
                permissions_dict["Brand"] = {}
                permissions_dict["Brand"]["Items"] = []

            for brand in custom_permission_obj.brands.all():            
                permissions_dict["Brand"]["Items"].append(brand.name)

            if(custom_permission_obj.channels.all().count()):
                permissions_dict["Channel"] = {}
                permissions_dict["Channel"]["Items"] = []

            for channel in custom_permission_obj.channels.all():         
                permissions_dict["Channel"]["Items"].append(channel.name)

            price = json.loads(custom_permission_obj.price)
            stock = json.loads(custom_permission_obj.stock)
            mws_functions = json.loads(custom_permission_obj.mws_functions)
            noon_functions = json.loads(custom_permission_obj.noon_functions)
            verify_product = custom_permission_obj.verify_product

            if(custom_permission_obj.location_groups.count()>0):
                permissions_dict["Ecommerce"] = {}
                permissions_dict["Ecommerce"]["Items"] = []
                for location_group_obj in custom_permission_obj.location_groups.all():
                    permissions_dict["Ecommerce"]["Items"].append(location_group_obj.name)

            for key in price.keys():
                if(price[key]==True):
                    if(key=="variant"):
                        permissions_dict["Product"] = {}
                        permissions_dict["Product"]["Items"] = []
                        permissions_dict["Product"]["Items"].append("Can Update Min/Max Price")
                    elif(key=="dealshub"):
                        if("Ecommerce" not in permissions_dict):
                            permissions_dict["Ecommerce"] = {}
                            permissions_dict["Ecommerce"]["Items"] = []
                        permissions_dict["Ecommerce"]["Items"].append("Can Update Price")
                    elif(key=="Amazon UAE"):
                        if("Ecommerce" not in permissions_dict):
                            permissions_dict["Ecommerce"] = {}
                            permissions_dict["Ecommerce"]["Items"] = []
                        permissions_dict["Ecommerce"]["Items"].append("Can Update Price on Amazon UAE")
                    elif(key=="Amazon UK"):
                        if("Ecommerce" not in permissions_dict):
                            permissions_dict["Ecommerce"] = {}
                            permissions_dict["Ecommerce"]["Items"] = []
                        permissions_dict["Ecommerce"]["Items"].append("Can Update Price on Amazon UK")
                    elif(key=="Ebay"):
                        if("Ecommerce" not in permissions_dict):
                            permissions_dict["Ecommerce"] = {}
                            permissions_dict["Ecommerce"]["Items"] = []
                        permissions_dict["Ecommerce"]["Items"].append("Can Update Price on Ebay")
                    elif(key=="Noon"):
                        if("Ecommerce" not in permissions_dict):
                            permissions_dict["Ecommerce"] = {}
                            permissions_dict["Ecommerce"]["Items"] = []
                        permissions_dict["Ecommerce"]["Items"].append("Can Update Price on Noon")                        

            for key in stock.keys():
                if(stock[key]==True):
                    if(key=="dealshub"):
                        if("Ecommerce" not in permissions_dict):
                            permissions_dict["Ecommerce"] = {}
                            permissions_dict["Ecommerce"]["Items"] = []
                        permissions_dict["Ecommerce"]["Items"].append("Can Update Stock")
                    elif(key=="Amazon UAE"):
                        if("Ecommerce" not in permissions_dict):
                            permissions_dict["Ecommerce"] = {}
                            permissions_dict["Ecommerce"]["Items"] = []
                        permissions_dict["Ecommerce"]["Items"].append("Can Update Stock on Amazon UAE")
                    elif(key=="Amazon UK"):
                        if("Ecommerce" not in permissions_dict):
                            permissions_dict["Ecommerce"] = {}
                            permissions_dict["Ecommerce"]["Items"] = []
                        permissions_dict["Ecommerce"]["Items"].append("Can Update Stock on Amazon UK")
                    elif(key=="Ebay"):
                        if("Ecommerce" not in permissions_dict):
                            permissions_dict["Ecommerce"] = {}
                            permissions_dict["Ecommerce"]["Items"] = []
                        permissions_dict["Ecommerce"]["Items"].append("Can Update Stock on Ebay")
                    elif(key=="Noon"):
                        if("Ecommerce" not in permissions_dict):
                            permissions_dict["Ecommerce"] = {}
                            permissions_dict["Ecommerce"]["Items"] = []
                        permissions_dict["Ecommerce"]["Items"].append("Can Update Stock on Noon")

            if(verify_product):
                if("Product" not in permissions_dict):
                    permissions_dict["Product"] = {}
                    permissions_dict["Product"]["Items"] = []
                permissions_dict["Product"]["Items"].append("Can Verify Product")

            flag = 0
            for key in mws_functions.keys():
                if(mws_functions[key]==True):
                    flag = 1
            
            if(flag == 1):
                permissions_dict["MWS"] = {}
                permissions_dict["MWS"]["Items"] = []

                for key in mws_functions.keys():
                    if(mws_functions[key]==True):
                        if(key=="push_product_on_amazon"):
                            permissions_dict["MWS"]["Items"].append("Can Push Products on Amazon")
                        if(key=="pull_product_from_amazon"):
                            permissions_dict["MWS"]["Items"].append("Can Pull Products on Amazon")
                        if(key=="push_inventory_on_amazon"):
                            permissions_dict["MWS"]["Items"].append("Can Push Inventory on Amazon")
                        if(key=="push_price_on_amazon"):
                            permissions_dict["MWS"]["Items"].append("Can Push Price on Amazon")

            flag = 0
            for key in noon_functions.keys():
                if(noon_functions[key]==True):
                    flag = 1
            
            if(flag == 1):
                permissions_dict["Noon_Integration"] = {}
                permissions_dict["Noon_Integration"]["Items"] = []

                for key in noon_functions.keys():
                    if(noon_functions[key]==True):
                        if(key=="push_inventory_on_noon"):
                            permissions_dict["Noon_Integration"]["Items"].append("Can Push Inventory on Noon")
                        if(key=="push_price_on_noon"):
                            permissions_dict["Noon_Integration"]["Items"].append("Can Push Price on Noon")

            for permission in permissions:

                permission_string = str(permission).split("|")

                permission_string[1] = permission_string[1].strip()

                if(permission_string[1] != "Flyer" and permission_string[1] != "Image" and permission_string[1] != "Product"):
                    continue

                if(permission_string[1] == "Image"):
                    permission_string[1] = "Product"

                if(permission_string[1] not in permissions_dict):
                    permissions_dict[permission_string[1]] = {}
                    permissions_dict[permission_string[1]]["Items"] = []

                permissions_dict[permission_string[1]]["Items"].append(permission_string[2].strip().title())

            response["permissions"] = []

            for metric in permissions_dict.keys():

                temp_dict = {}
                temp_dict["title"] = metric
                temp_dict["Items"] = permissions_dict[metric]["Items"]
                response["permissions"].append(temp_dict)

            response['status'] = 200
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchUserProfileAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class EditUserProfileAPI(APIView):
    
    def post(self, request, *args, **kwargs):
    
        response = {}
        response['status'] = 500
        
        try:
            data = request.data
            logger.info("EditUserProfileAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            first_name = data["first_name"]
            last_name = data["last_name"]
            contact_number = data["contact_number"]
            email = data["email"]
            designation = data["designation"]

            omnycomm_user = OmnyCommUser.objects.get(username=request.user.username)

            omnycomm_user.first_name = first_name
            omnycomm_user.last_name = last_name
            omnycomm_user.contact_number = contact_number
            omnycomm_user.email = email
            omnycomm_user.designation = designation
            omnycomm_user.save()
        
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("EditUserProfileAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchAuditLogsByUserAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data
            logger.info("FetchAuditLogsByUserAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            page = data["page"]

            all_log_entry_objs = LogEntry.objects.filter(actor=request.user)

            paginator = Paginator(all_log_entry_objs, 20)
            log_entry_objs = paginator.page(page)

            log_entry_list = []
            for log_entry_obj in log_entry_objs:
                
                try:
                    temp_dict = {}
                    object_pk = log_entry_obj.object_pk
                    content_type = str(log_entry_obj.content_type)
                    logger.info("%s ",content_type)
                    temp_dict["created_date"] = datetime.datetime.strftime(log_entry_obj.timestamp, "%b %d, %Y")
                    temp_dict["resource"] = content_type

                    if content_type.lower() == "baseproduct":
                        base_product_obj = BaseProduct.objects.get(pk=int(object_pk))
                        seller_sku = base_product_obj.seller_sku
                        temp_dict2 = {}
                        temp_dict2["name"] = str(base_product_obj.base_product_name)
                        temp_dict2["seller_sku"] = str(base_product_obj.seller_sku)
                        temp_dict["identifier"] = temp_dict2
                    
                    elif content_type.lower() == "product":
                        base_product_obj = Product.objects.get(pk=int(object_pk)).base_product
                        seller_sku = base_product_obj.seller_sku
                        temp_dict2 = {}
                        temp_dict2["name"] = str(base_product_obj.base_product_name)
                        temp_dict2["seller_sku"] = str(base_product_obj.seller_sku)
                        temp_dict["identifier"] = temp_dict2
                    
                    elif content_type.lower() == "channelproduct":
                        channel_product_obj = ChannelProduct.objects.get(pk=int(object_pk))
                        base_product_obj = Product.objects.get(channel_product=channel_product_obj).base_product
                        seller_sku = base_product_obj.seller_sku
                        temp_dict2 = {}
                        temp_dict2["name"] = str(base_product_obj.base_product_name)
                        temp_dict2["seller_sku"] = str(base_product_obj.seller_sku)
                        temp_dict["identifier"] = temp_dict2
                    
                    elif content_type.lower() == "main images":
                        main_images_obj = MainImages.objects.get(pk=int(object_pk))
                        base_product_obj = main_images_obj.product.base_product
                        seller_sku = base_product_obj.seller_sku
                        temp_dict2 = {}
                        temp_dict2["name"] = str(base_product_obj.base_product_name)
                        temp_dict2["seller_sku"] = str(base_product_obj.seller_sku)
                        temp_dict["identifier"] = temp_dict2
                    
                    elif content_type.lower() == "sub images":
                        main_images_obj = MainImages.objects.get(pk=int(object_pk))
                        base_product_obj = main_images_obj.product.base_product
                        seller_sku = base_product_obj.seller_sku
                        temp_dict2 = {}
                        temp_dict2["name"] = str(base_product_obj.base_product_name)
                        temp_dict2["seller_sku"] = str(base_product_obj.seller_sku)
                        temp_dict["identifier"] = temp_dict2
                    
                    else:
                        temp_dict2 = {}
                        temp_dict2["name"] = content_type
                        temp_dict2["seller_sku"] = ""
                        temp_dict["identifier"] = temp_dict2

                    temp_dict["action"] = ""
                    if log_entry_obj.action==0:
                        temp_dict["action"] = "create"
                    elif log_entry_obj.action==1:
                        temp_dict["action"] = "update"
                    elif log_entry_obj.action==2:
                        temp_dict["action"] = "delete"
                    # changes = json.loads(log_entry_obj.changes)
                    # logger.info("%s ",str(changes))

                    changes = log_entry_obj.changes.replace("_", " ")
                    changes = changes.title()
                    changes = json.loads(changes)

                    changes = logentry_dict_to_attributes(changes)
                    
                    temp_dict["changes"] = changes

                    log_entry_list.append(temp_dict)
                
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchAuditLogsByUserAPI: %s at %s",
                                 e, str(exc_tb.tb_lineno))

            is_available = True
            if paginator.num_pages == page:
                is_available = False

            response["log_entry_list"] = log_entry_list
            response["is_available"] = is_available
            response['status'] = 200
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchAuditLogsByUserAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchAuditLogsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("FetchAuditLogsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            page = data["page"]

            all_log_entry_objs = LogEntry.objects.exclude(actor=None)

            paginator = Paginator(all_log_entry_objs, 20)
            log_entry_objs = paginator.page(page)

            log_entry_list = []
            
            for log_entry_obj in log_entry_objs:
                
                try:
                    temp_dict = {}

                    object_pk = log_entry_obj.object_pk
                    content_type = str(log_entry_obj.content_type)

                    temp_dict["created_date"] = datetime.datetime.strftime(log_entry_obj.timestamp, "%b %d, %Y")
                    temp_dict["resource"] = content_type
                    temp_dict["user"] = str(log_entry_obj.actor)
                    temp_dict["action"] = ""
                    
                    if content_type.lower() == "baseproduct":
                        base_product_obj = BaseProduct.objects.get(pk=int(object_pk))
                        seller_sku = base_product_obj.seller_sku
                        temp_dict2 = {}
                        temp_dict2["name"] = str(base_product_obj.base_product_name)
                        temp_dict2["seller_sku"] = str(base_product_obj.seller_sku)
                        temp_dict["identifier"] = temp_dict2
                    
                    elif content_type.lower() == "product":
                        base_product_obj = Product.objects.get(pk=int(object_pk)).base_product
                        seller_sku = base_product_obj.seller_sku
                        temp_dict2 = {}
                        temp_dict2["name"] = str(base_product_obj.base_product_name)
                        temp_dict2["seller_sku"] = str(base_product_obj.seller_sku)
                        temp_dict["identifier"] = temp_dict2
                    
                    elif content_type.lower() == "channelproduct":
                        channel_product_obj = ChannelProduct.objects.get(pk=int(object_pk))
                        base_product_obj = Product.objects.get(channel_product=channel_product_obj).base_product
                        seller_sku = base_product_obj.seller_sku
                        temp_dict2 = {}
                        temp_dict2["name"] = str(base_product_obj.base_product_name)
                        temp_dict2["seller_sku"] = str(base_product_obj.seller_sku)
                        temp_dict["identifier"] = temp_dict2
                    
                    elif content_type.lower() == "main images":
                        main_images_obj = MainImages.objects.get(pk=int(object_pk))
                        base_product_obj = main_images_obj.product.base_product
                        seller_sku = base_product_obj.seller_sku
                        temp_dict2 = {}
                        temp_dict2["name"] = str(base_product_obj.base_product_name)
                        temp_dict2["seller_sku"] = str(base_product_obj.seller_sku)
                        temp_dict["identifier"] = temp_dict2
                    
                    elif content_type.lower() == "sub images":
                        main_images_obj = MainImages.objects.get(pk=int(object_pk))
                        base_product_obj = main_images_obj.product.base_product
                        seller_sku = base_product_obj.seller_sku
                        temp_dict2 = {}
                        temp_dict2["name"] = str(base_product_obj.base_product_name)
                        temp_dict2["seller_sku"] = str(base_product_obj.seller_sku)
                        temp_dict["identifier"] = temp_dict2
                    
                    else:
                        temp_dict2 = {}
                        temp_dict2["name"] = content_type
                        temp_dict2["seller_sku"] = ""
                        temp_dict["identifier"] = temp_dict2

                    if log_entry_obj.action==0:
                        temp_dict["action"] = "create"
                    elif log_entry_obj.action==1:
                        temp_dict["action"] = "update"
                    elif log_entry_obj.action==2:
                        temp_dict["action"] = "delete"

                    changes = log_entry_obj.changes.replace("_", " ")
                    changes = changes.title()
                    changes = json.loads(changes)

                    changes = logentry_dict_to_attributes(changes)

                    temp_dict["changes"] = changes
                    log_entry_list.append(temp_dict)
                
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchAuditLogsAPI: %s at %s", e, str(exc_tb.tb_lineno))

            is_available = True
            if paginator.num_pages == page:
                is_available = False            

            response["log_entry_list"] = log_entry_list
            response["is_available"] = is_available
            
            response['status'] = 200
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchAuditLogsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)
        

class CreateRequestHelpAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("CreateRequestHelpAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            message = data["message"]
            page = data["page"]

            RequestHelp.objects.create(message=message, page=page, user=request.user)

            response['status'] = 200
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateRequestHelpAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class RefreshProductPriceAndStockAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("RefreshProductPriceAndStockAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_pk = data["product_pk"]
            warehouse_code = data["warehouse_code"]
            
            product_obj = Product.objects.get(pk=product_pk)
            warehouses_dict = fetch_prices(product_obj.base_product.seller_sku,warehouse_code)

            response["warehouses_dict"] = warehouses_dict
            
            response['status'] = 200
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("RefreshProductPriceAndStockAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class RefreshPagePriceAndStockAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("RefreshPagePriceAndStockAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_pk_list = data["product_pk_list"]
            warehouse_code = data["warehouse_code"]
            
            warehouses_information = []
            
            for pk in product_pk_list:
                product_obj = Product.objects.get(pk=int(pk))
                warehouses_dict = fetch_prices(product_obj.base_product.seller_sku,warehouse_code)
                warehouses_dict["product_pk"] = pk
                warehouses_information.append(warehouses_dict)

            response["warehouses_information"] = warehouses_information
            
            response['status'] = 200
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("RefreshPagePriceAndStockAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchCompanyProfileAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("FetchCompanyProfileAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            website_group_obj = OmnyCommUser.objects.get(username=request.user.username).website_group

            company_data = {}
            company_data["name"] = website_group_obj.name
            company_data["contact_info"] = json.loads(website_group_obj.contact_info)
            company_data["whatsapp_info"] = website_group_obj.whatsapp_info
            company_data["email_info"] = website_group_obj.email_info
            company_data["address"] = website_group_obj.address
            company_data["primary_color"] = website_group_obj.primary_color
            company_data["secondary_color"] = website_group_obj.secondary_color
            company_data["navbar_text_color"] = website_group_obj.navbar_text_color
            company_data["facebook_link"] = website_group_obj.facebook_link
            company_data["twitter_link"] = website_group_obj.twitter_link
            company_data["instagram_link"] = website_group_obj.instagram_link
            company_data["youtube_link"] = website_group_obj.youtube_link
            company_data["linkedin_link"] = website_group_obj.linkedin_link
            company_data["crunchbase_link"] = website_group_obj.crunchbase_link

            company_data["color_scheme"] = json.loads(website_group_obj.color_scheme)
            
            company_data["logo"] = []
            if website_group_obj.logo != None:
                company_data["logo"] = [{
                    "uid" : "123",
                    "url" : ""
                }]
                company_data["logo"][0]["url"] = website_group_obj.logo.image.url

            company_data["footer_logo"] = []
            if website_group_obj.footer_logo != None:
                company_data["footer_logo"] = [{
                    "uid" : "123",
                    "url" : ""
                }]
                company_data["footer_logo"][0]["url"] = website_group_obj.footer_logo.image.url


            response["company_data"] = company_data
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCompanyProfileAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class SaveCompanyProfileAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("SaveCompanyProfileAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            website_group_obj = OmnyCommUser.objects.get(username=request.user.username).website_group

            company_data = data["company_data"]
            
            #name = company_data["name"]
            contact_info = company_data["contact_info"]
            whatsapp_info = company_data["whatsapp_info"]
            email_info = company_data["email_info"]
            address = company_data["address"]
            # primary_color = company_data["primary_color"]
            # secondary_color = company_data["secondary_color"]
            # navbar_text_color = company_data["navbar_text_color"]
            facebook_link = company_data["facebook_link"]
            twitter_link = company_data["twitter_link"]
            instagram_link = company_data["instagram_link"]
            youtube_link = company_data["youtube_link"]
            linkedin_link = company_data["linkedin_link"]
            crunchbase_link = company_data["crunchbase_link"]

            color_scheme = company_data["color_scheme"]
        
            #organization.name=name
            website_group_obj.contact_info=json.dumps(contact_info)
            website_group_obj.whatsapp_info=whatsapp_info
            website_group_obj.email_info=email_info
            website_group_obj.address=address
            # website_group_obj.primary_color=primary_color
            # website_group_obj.secondary_color=secondary_color
            # website_group_obj.navbar_text_color=navbar_text_color
            website_group_obj.facebook_link=facebook_link
            website_group_obj.twitter_link=twitter_link
            website_group_obj.instagram_link=instagram_link
            website_group_obj.youtube_link=youtube_link
            website_group_obj.linkedin_link=linkedin_link
            website_group_obj.crunchbase_link=crunchbase_link

            website_group_obj.color_scheme = json.dumps(color_scheme)
            
            website_group_obj.save()

            response['status'] = 200
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveCompanyProfileAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class UploadCompanyLogoAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            if request.user.has_perm("WAMSApp.add_image") == False:
                logger.warning("UploadCompanyLogoAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("UploadCompanyLogoAPI: %s", str(data))

            website_group_obj = OmnyCommUser.objects.get(username=request.user.username).website_group
           
            logo_image_url = data["logo_image_url"]

            if logo_image_url != "":
                image_obj = Image.objects.create(image=logo_image_url)
                website_group_obj.logo = image_obj
                website_group_obj.save()
                response["image_url"] = image_obj.mid_image.url

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadCompanyLogoAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadCompanyFooterLogoAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            if request.user.has_perm("WAMSApp.add_image") == False:
                logger.warning("UploadCompanyFooterLogoAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("UploadCompanyFooterLogoAPI: %s", str(data))

            website_group_obj = OmnyCommUser.objects.get(username=request.user.username).website_group
           
            logo_image_url = data["logo_image_url"]

            if logo_image_url != "":
                image_obj = Image.objects.create(image=logo_image_url)
                website_group_obj.footer_logo = image_obj
                website_group_obj.save()
                response["image_url"] = image_obj.mid_image.url

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadCompanyFooterLogoAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchChannelProductListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("FetchChannelProductListAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            chip_data = data.get("tags", "[]")
            filter_parameters = data.get("filter_parameters", "{}")

            filter_parameters = json.loads(filter_parameters)
            chip_data = json.loads(chip_data)

            channel_name = data["channel_name"]

            page = int(data.get('page', 1))

            search_list_product_objs = []
        
            permission_obj = CustomPermission.objects.get(user__username=request.user.username)
            organization_obj = permission_obj.organization
            brands = permission_obj.brands.all()

            if "brand_name" in filter_parameters and filter_parameters["brand_name"]!="":
                brands = brands.filter(name__icontains=filter_parameters["brand_name"])              

            product_objs_list = Product.objects.filter(base_product__brand__in=brands).order_by('-pk')
            
            if channel_name=="Amazon UK":
                product_objs_list = product_objs_list.filter(channel_product__is_amazon_uk_product_created=True)
            elif channel_name=="Amazon UAE":
                product_objs_list = product_objs_list.filter(channel_product__is_amazon_uae_product_created=True)
            elif channel_name=="Ebay":
                product_objs_list = product_objs_list.filter(channel_product__is_ebay_product_created=True)
            elif channel_name=="Noon":
                product_objs_list = product_objs_list.filter(channel_product__is_noon_product_created=True)

            if "has_image" in filter_parameters:
                if filter_parameters["has_image"] == True:
                    product_objs_list = product_objs_list.exclude(no_of_images_for_filter=0)
                elif filter_parameters["has_image"] == False:
                    product_objs_list = product_objs_list.filter(no_of_images_for_filter=0)

            search_list_product_objs = product_objs_list
            
            if len(chip_data) > 0:
                search_list_product_objs = Product.objects.none()
                for tag in chip_data:
                    search = product_objs_list.filter(
                        Q(product_name__icontains=tag) |
                        Q(product_name_sap__icontains=tag) |
                        Q(product_id__icontains=tag) |
                        Q(base_product__seller_sku__icontains=tag)
                    )
                    
                    for prod in search:
                        product_obj = Product.objects.filter(pk=prod.pk)
                        search_list_product_objs|=product_obj

            products = []

            paginator = Paginator(search_list_product_objs, 20)
            product_objs = paginator.page(page)

            if "import_file" in data:

                product_objs = Product.objects.none()

                try :
                    
                    path = default_storage.save('tmp/search-channel-file.xlsx', data["import_file"])
                    path = "http://cdn.omnycomm.com.s3.amazonaws.com/"+path
                    dfs = pd.read_excel(path, sheet_name=None)

                except Exception as e:
                    response['status'] = 407
                    logger.warning("FetchChannelProductListAPI UnSupported File Format ")
                    return Response(data=response)

                try :
                    dfs = dfs["Sheet1"]
                except Exception as e:
                    response['status'] = 406
                    logger.warning("FetchChannelProductListAPI Sheet1 not found!")
                    return Response(data=response)

                rows = len(dfs.iloc[:])

                search_list = []
                excel_errors = []

                flag=0
                
                if "option" not in data:
                    flag=1
                else:
                    option = data["option"]

                for i in range(rows):
                    try:
                        
                        search_key = str(dfs.iloc[i][0]).strip()
                        logger.info(search_key)

                        if flag == 1:
                            search_list.append(search_key)

                        else:

                            if option == "Product ID":
                                
                                search_key = str(int(dfs.iloc[i][0])).strip()
                                
                                try :
                                    product_obj = Product.objects.filter(product_id=search_key, base_product__brand__organization=organization_obj)
                                    product_objs|=product_obj

                                    if product_obj == None :
                                        excel_errors.append("No product found for " + search_key)

                                except Exception as e:
                                    pass

                            elif option == "Seller SKU":                               
                                try :
                                    product_obj = Product.objects.filter(base_product__seller_sku=search_key, base_product__brand__organization=organization_obj)
                                    product_objs |= product_obj
                                    
                                    if product_obj == None :
                                        excel_errors.append("No product found for " + search_key)
                                        
                                except Exception as e:
                                    pass

                            elif option == "Noon SKU" and channel_name=="Noon":
                                try :
                                    product_obj = Product.objects.filter(channel_product__noon_product_json__icontains='"noon_sku": "'+search_key+'"', base_product__brand__organization=organization_obj)
                                    product_objs.add(product_obj)
                                    
                                    if product_obj == None :
                                        excel_errors.append("No product found for " + search_key)
                                        
                                except Exception as e:
                                    pass

                            elif option == "Partner SKU" and channel_name=="Noon":
                                try :
                                    product_obj = Product.objects.filter(channel_product__noon_product_json__icontains='"partner_sku": "'+search_key+'"', base_product__brand__organization=organization_obj)
                                    product_objs |= product_obj
                                    
                                    if product_obj == None :
                                        excel_errors.append("No product found for " + search_key)
                                        
                                except Exception as e:
                                    pass

                            elif option == "ASIN" and channel_name=="Amazon UAE":
                                try :
                                    product_obj = Product.objects.filter(channel_product__amazon_uae_product_json__icontains='"ASIN": "'+search_key+'"', base_product__brand__organization=organization_obj)
                                    product_objs |= product_obj
                                    
                                    if product_obj == None :
                                        excel_errors.append("No product found for " + search_key)
                                        
                                except Exception as e:
                                    pass

                            elif option == "ASIN" and channel_name=="Amazon UK":
                                try :
                                    product_obj = Product.objects.get(channel_product__amazon_uk_product_json__icontains='"ASIN": "'+search_key+'"', base_product__brand__organization=organization_obj)
                                    product_objs |= product_obj
                                    
                                    if product_obj == None :
                                        excel_errors.append("No product found for " + search_key)
                                        
                                except Exception as e:
                                    pass

                            else:
                                response['status'] = 405
                                logger.warning("FetchChannelProductListAPI Wrong Template Uploaded for " + data["option"])
                                return Response(data=response)

                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        logger.warning("FetchChannelProductListAPI: %s at %s", e, str(exc_tb.tb_lineno))
                        pass
                
                if flag==1:
                    product_objs = search_list_product_objs.filter(Q(product_id__in=search_list) | Q(base_product__seller_sku__in=search_list))

                product_objs = product_objs.distinct()

            for product_obj in product_objs:
                try:
                    temp_dict = {}
                    temp_dict["product_pk"] = product_obj.pk
                    
                    if channel_name=="Amazon UK":
                        amazon_uk_product_json = json.loads(product_obj.channel_product.amazon_uk_product_json)
                        temp_dict["product_name"] = amazon_uk_product_json["product_name"]
                        temp_dict["category"] = amazon_uk_product_json["category"]
                        temp_dict["sub_category"] = amazon_uk_product_json["sub_category"]
                        temp_dict["status"] = amazon_uk_product_json["status"]
                        temp_dict["now_price"] = amazon_uk_product_json["now_price"]
                        temp_dict["was_price"] = amazon_uk_product_json["was_price"]
                        temp_dict["stock"] = amazon_uk_product_json["stock"]
                    
                    if channel_name=="Amazon UAE":
                        amazon_uae_product_json = json.loads(product_obj.channel_product.amazon_uae_product_json)
                        temp_dict["product_name"] = amazon_uae_product_json["product_name"]
                        temp_dict["category"] = amazon_uae_product_json["category"]
                        temp_dict["sub_category"] = amazon_uae_product_json["sub_category"]
                        temp_dict["status"] = amazon_uae_product_json["status"]
                        temp_dict["now_price"] = amazon_uae_product_json["sale_price"]
                        temp_dict["was_price"] = amazon_uae_product_json["was_price"]
                        temp_dict["stock"] = amazon_uae_product_json["stock"]
                    
                    if channel_name=="Ebay":
                        ebay_product_json = json.loads(product_obj.channel_product.ebay_product_json)
                        temp_dict["product_name"] = ebay_product_json["product_name"]
                        temp_dict["category"] = ebay_product_json["category"]
                        temp_dict["sub_category"] = ebay_product_json["sub_category"]
                        temp_dict["status"] = ebay_product_json["status"]
                        temp_dict["now_price"] = ebay_product_json["now_price"]
                        temp_dict["was_price"] = ebay_product_json["was_price"]
                        temp_dict["stock"] = ebay_product_json["stock"]
                    
                    if channel_name=="Noon":
                        noon_product_json = json.loads(product_obj.channel_product.noon_product_json)
                        temp_dict["product_name"] = noon_product_json["product_name"]
                        temp_dict["noon_sku"] = noon_product_json["noon_sku"]
                        temp_dict["category"] = noon_product_json["category"]
                        temp_dict["sub_category"] = noon_product_json["sub_category"]
                        temp_dict["status"] = noon_product_json["status"]
                        temp_dict["now_price"] = noon_product_json["sale_price"]
                        temp_dict["was_price"] = noon_product_json["was_price"]
                        temp_dict["stock"] = noon_product_json["stock"]

                    temp_dict["seller_sku"] = product_obj.base_product.seller_sku
                    
                    if product_obj.base_product.brand != None:
                        temp_dict["brand_name"] = product_obj.base_product.brand.name
                    else:
                        temp_dict["brand_name"] = "-"

                    try:
                        main_images_list = ImageBucket.objects.none()
                        main_images_obj = MainImages.objects.get(product = product_obj, channel__name=channel_name)
                        
                        main_images_list |= main_images_obj.main_images.all()

                        main_images_list = main_images_list.distinct()
                        
                        temp_dict["main_image"] = main_images_list[0].image.mid_image.url
                    except Exception as e:
                        temp_dict["main_image"] = Config.objects.all()[0].product_404_image.image.url

                    products.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchChannelProductListAPI: %s at %s", e, str(exc_tb.tb_lineno))

            is_available = True
            if paginator.num_pages == page:
                is_available = False

            response["is_available"] = is_available
            response["total_products"] = len(search_list_product_objs)
            response["products"] = products


            response['status'] = 200
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchChannelProductListAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchLocationGroupListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchLocationGroupListAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_list = []
            for location_group_obj in LocationGroup.objects.all():
                temp_dict = {}
                temp_dict["uuid"] = location_group_obj.uuid
                temp_dict["name"] = location_group_obj.name
                location_group_list.append(temp_dict)

            response["location_group_list"] = location_group_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchLocationGroupListAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadBulkExportAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("UploadBulkExportAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            path = default_storage.save('tmp/temp-bulk-upload.xlsx', data["import_file"])
            path = "http://cdn.omnycomm.com.s3.amazonaws.com/"+path
            dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
            rows = len(dfs.iloc[:])

            organization_obj = CustomPermission.objects.get(user__username=request.user.username).organization

            product_list = []
            for i in range(rows):
                try:
                    search_string = str(dfs.iloc[i][0]).strip()
                    #product_obj = Product.objects.get(product_id=product_id)
                    product_objs = Product.objects.filter(base_product__brand__organization=organization_obj).filter(Q(base_product__seller_sku=search_string) | Q(product_id=search_string))
                    for product_obj in product_objs:
                        temp_dict = {}
                        temp_dict["name"] = product_obj.product_name
                        temp_dict["product_id"] = product_obj.product_id
                        temp_dict["product_pk"] = product_obj.pk
                        temp_dict["seller_sku"] = product_obj.base_product.seller_sku
                        temp_dict["uuid"] = product_obj.uuid
                        try:
                            temp_dict["image_url"] = MainImages.objects.get(product=product_obj, is_sourced=True).main_images.all()[0].image.mid_image.url
                        except Exception as e:
                            temp_dict["image_url"] = Config.objects.all()[0].product_404_image.image.url
                        product_list.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("UploadBulkExportAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["product_list"] = product_list
            
            response['status'] = 200
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadBulkExportAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SearchBulkExportAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("SearchBulkExportAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            search_string = data["search_string"]

            organization_obj = CustomPermission.objects.get(user__username=request.user.username).organization

            product_objs = Product.objects.filter(base_product__brand__organization=organization_obj).filter(Q(base_product__seller_sku__icontains=search_string) | Q(product_name__icontains=search_string))[:10]

            product_list = []
            for product_obj in product_objs:
                try:
                    temp_dict = {}
                    temp_dict["name"] = product_obj.product_name
                    temp_dict["product_id"] = product_obj.product_id
                    temp_dict["product_pk"] = product_obj.pk
                    temp_dict["seller_sku"] = product_obj.base_product.seller_sku
                    temp_dict["uuid"] = product_obj.uuid
                    try:
                        temp_dict["image_url"] = MainImages.objects.get(product=product_obj, is_sourced=True).main_images.all()[0].image.mid_image.url
                    except Exception as e:
                        temp_dict["image_url"] = Config.objects.all()[0].product_404_image.image.url
                    product_list.append(temp_dict)
                except Exception as e:
                    pass

            response["product_list"] = product_list
            
            response['status'] = 200
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchBulkExportAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchDataPointsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("FetchDataPointsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            data_point_objs = DataPoint.objects.all()
            data_point_list = []
            for data_point_obj in data_point_objs:
                temp_dict = {}
                temp_dict["name"] = data_point_obj.name
                temp_dict["variable"] = data_point_obj.variable
                data_point_list.append(temp_dict)
            
            response["data_point_list"] = data_point_list
            
            response['status'] = 200
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchDataPointsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DownloadBulkExportAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("DownloadBulkExportAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            data_point_list = data["data_point_list"]
            product_uuid_list = data["product_uuid_list"]

            filename = str(datetime.datetime.now().strftime("%d%m%Y%H%M_dynamic_export"))+".xlsx"

            generate_dynamic_export(filename, product_uuid_list, data_point_list)

            response["file_path"] = SERVER_IP+"/files/csv/"+filename
            
            response['status'] = 200
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DownloadBulkExportAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class TransferBulkChannelAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("TransferBulkChannelAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            channel_list = data["channel_list"]
            product_uuid_list = data["product_uuid_list"]

            for product_uuid in product_uuid_list:
                
                try:
                    channel_product_obj = ChannelProduct.objects.get(product__uuid=product_uuid)
                    if "Amazon UK" in channel_list:
                        channel_product_obj.is_amazon_uk_product_created = True
                    if "Amazon UAE" in channel_list:
                        channel_product_obj.is_amazon_uae_product_created = True
                    if "Ebay" in channel_list:
                        channel_product_obj.is_ebay_product_created = True
                    if "Noon" in channel_list:
                        channel_product_obj.is_noon_product_created = True
                    channel_product_obj.save()
                
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("TransferBulkChannelAPI: %s at %s", e, str(exc_tb.tb_lineno))
            
            response['status'] = 200
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("TransferBulkChannelAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchAllCategoriesAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("FetchAllCategoriesAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            super_category_objs = SuperCategory.objects.all()
            super_category_list = []
            for super_category_obj in super_category_objs:
                try:
                    temp_dict = {}
                    temp_dict["name"] = super_category_obj.name
                    temp_dict["name_ar"] = super_category_obj.name_ar
                    temp_dict["super_category_uuid"] = super_category_obj.uuid
                    category_objs = Category.objects.filter(super_category=super_category_obj)
                    category_list = []
                    for category_obj in category_objs:
                        temp_dict2 = {}
                        temp_dict2["name"] = category_obj.name
                        temp_dict2["name_ar"] = category_obj.name_ar
                        temp_dict2["category_uuid"] = category_obj.uuid
                        sub_category_objs = SubCategory.objects.filter(category=category_obj)
                        sub_category_list = []
                        for sub_category_obj in sub_category_objs:
                            temp_dict3 = {}
                            temp_dict3["name"] = sub_category_obj.name
                            temp_dict3["name_ar"] = sub_category_obj.name_ar
                            temp_dict3["sub_category_uuid"] = sub_category_obj.uuid
                            sub_category_list.append(temp_dict3)
                        temp_dict2["sub_category_list"] = sub_category_list
                        category_list.append(temp_dict2)
                    temp_dict["category_list"] = category_list
                    super_category_list.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchAllCategoriesAPI: %s at %s", e, str(exc_tb.tb_lineno))
                
            response["super_category_list"] = super_category_list
            response['status'] = 200
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchAllCategoriesAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CheckSectionPermissionsAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("CheckSectionPermissionsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            website_group_name = ""
            ecommerce_pages = []
            custom_permission_obj = CustomPermission.objects.get(user__username=request.user.username)
            location_group_objs = custom_permission_obj.location_groups.all()
            for location_group_obj in location_group_objs:
                temp_dict = {}
                temp_dict["name"] = location_group_obj.name
                temp_dict["uuid"] = location_group_obj.uuid
                temp_dict["is_b2b"] = location_group_obj.is_b2b
                ecommerce_pages.append(temp_dict)

            omnycomm_user_obj = OmnyCommUser.objects.get(username=request.user.username)
            if omnycomm_user_obj.website_group!=None:
                website_group_name = omnycomm_user_obj.website_group.name

            misc = json.loads(custom_permission_obj.misc)

            response["page_list"] = get_custom_permission_page_list(request.user)
            response["ecommerce_pages"] = ecommerce_pages
            response["misc"] = misc
            response["websiteGroupName"] = website_group_name

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CheckSectionPermissionsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CreateOCReportAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("CreateOCReportAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if OCReport.objects.filter(is_processed=False).count()>4:
                response["approved"] = False
                response['status'] = 200
                return Response(data=response)

            report_type = data["report_type"]
            note = data["note"]
            brand_list = data.get("brand_list", [])
            
            from_date = data.get("from_date", "")
            to_date = data.get("to_date", "")

            filename = "files/reports/"+str(datetime.datetime.now().strftime("%d%m%Y%H%M_"))+report_type+".xlsx"
            oc_user_obj = OmnyCommUser.objects.get(username=request.user.username)
            
            custom_permission_obj = CustomPermission.objects.get(user=request.user)
            organization_obj = custom_permission_obj.organization

            oc_report_obj = OCReport.objects.create(name=report_type, report_title=report_type, created_by=oc_user_obj, note=note, filename=filename, organization=custom_permission_obj.organization)

            if len(brand_list)==0:
                brand_objs = custom_permission_filter_brands(request.user)
                for brand_obj in brand_objs:
                    brand_list.append(brand_obj.name)

            if report_type.lower()=="mega":
                p1 = threading.Thread(target=create_mega_bulk_oc_report, args=(filename,oc_report_obj.uuid,brand_list,"",organization_obj,))
                p1.start()
            elif report_type.lower()=="flyer":
                p1 = threading.Thread(target=create_flyer_report, args=(filename,oc_report_obj.uuid,brand_list,organization_obj,))
                p1.start()
            elif report_type.lower()=="image":
                p1 = threading.Thread(target=create_image_report, args=(filename,oc_report_obj.uuid,brand_list,organization_obj,))
                p1.start()
            elif report_type.lower()=="ecommerce":
                p1 = threading.Thread(target=create_wigme_report, args=(filename,oc_report_obj.uuid,brand_list,custom_permission_obj,))
                p1.start()
            elif report_type.lower()=="search keyword":
                p1 = threading.Thread(target=create_search_keyword_report, args=(filename,oc_report_obj.uuid,custom_permission_obj,))
                p1.start()
            elif report_type.lower()=="sales":
                p1 = threading.Thread(target=create_sales_report, args=(filename,oc_report_obj.uuid,from_date, to_date, brand_list,custom_permission_obj,))
                p1.start()
            elif report_type.lower()=="order":
                p1 = threading.Thread(target=create_order_report, args=(filename,oc_report_obj.uuid,from_date, to_date, brand_list,custom_permission_obj,))
                p1.start()
            elif report_type.lower()=="sap billing":
                p1 = threading.Thread(target=create_sap_billing_report, args=(filename,oc_report_obj.uuid,from_date, to_date, custom_permission_obj,))
                p1.start()
            elif report_type.lower()=="verified products":
                p1 = threading.Thread(target=create_verified_products_report, args=(filename,oc_report_obj.uuid,from_date, to_date, brand_list,custom_permission_obj,))
                p1.start()
            elif report_type.lower()=="wishlist":
                p1 = threading.Thread(target=create_wishlist_report, args=(filename,oc_report_obj.uuid, brand_list,custom_permission_obj,))
                p1.start()
            elif report_type.lower()=="abandoned cart":
                p1 = threading.Thread(target=create_abandoned_cart_report, args=(filename,oc_report_obj.uuid, brand_list,custom_permission_obj,))
                p1.start()
            elif report_type.lower()=="delivery":
                shipping_method = data["shipping_method"]
                oc_report_obj.report_title = oc_report_obj.report_title + " " + shipping_method
                oc_report_obj.save()
                if shipping_method.lower()=="sendex":
                    p1 = threading.Thread(target=create_sendex_courier_report, args=(filename, oc_report_obj.uuid, from_date, to_date, custom_permission_obj,))
                    p1.start()
                elif shipping_method.lower()=="standard":
                    p1 = threading.Thread(target=create_standard_courier_report, args=(filename, oc_report_obj.uuid, from_date, to_date, custom_permission_obj,))
                    p1.start()
                elif shipping_method.lower()=="postaplus":
                    p1 =  threading.Thread(target=create_postaplus_courier_report, args=(filename, oc_report_obj.uuid, from_date, to_date, custom_permission_obj,))
                    p1.start()
            elif report_type.lower()=="sales executive":
                p1 = threading.Thread(target=create_sales_executive_value_report, args=(filename, oc_report_obj.uuid, from_date, to_date, custom_permission_obj,))
                p1.start()
            elif report_type.lower()=="bulk image":
                p1 = threading.Thread(target=create_bulk_image_report, args=(filename,oc_report_obj.uuid,brand_list,organization_obj,))
                p1.start()
            elif report_type.lower()=="stock":
                location_group_uuid = data["locationGroupUuid"]
                location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
                p1 = threading.Thread(target=create_stock_report, args=(filename,oc_report_obj.uuid,brand_list,location_group_obj,))
                p1.start()
            elif report_type.lower()=="nesto ecommerce product":
                p1 = threading.Thread(target=bulk_download_nesto_ecommerce_report, args=(filename,oc_report_obj.uuid,))
                p1.start()
            elif report_type.lower()=="nesto detailed product":
                p1 = threading.Thread(target=bulk_download_nesto_detailed_product_report, args=(filename,oc_report_obj.uuid,))
                p1.start()
            elif report_type.lower()=="nesto product summary":
                p1 = threading.Thread(target=nesto_products_summary_report, args=(filename,oc_report_obj.uuid,))
                p1.start()
            response["approved"] = True
            response['status'] = 200
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateOCReportAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class CreateSEOReportAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:
            data = request.data
            logger.info("CreateSEOReportAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if OCReport.objects.filter(is_processed=False).count()>4:
                response["approved"] = False
                response['status'] = 200
                return Response(data=response)
            
            report_type = "SEO"
            seo_type = data["seo_type"] 
            note = data["note"]
            location_group_uuid = data["locationGroupUuid"]

            filename = "files/reports/"+str(datetime.datetime.now().strftime("%d%m%Y%H%M_"))+report_type+".xlsx"
            oc_user_obj = OmnyCommUser.objects.get(username=request.user.username)
            
            custom_permission_obj = CustomPermission.objects.get(user=request.user)
            organization_obj = custom_permission_obj.organization
            report_name = report_type+" "+seo_type
            oc_report_obj = OCReport.objects.create(name=report_type, report_title=report_name, created_by=oc_user_obj, note=note, filename=filename, organization=organization_obj)
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            if seo_type=="product":
                p1 = threading.Thread(target=bulk_download_product_seo_details_report, args=(filename,oc_report_obj.uuid,location_group_obj,))
                p1.start()
            elif seo_type=="subcategory":
                p1 = threading.Thread(target=bulk_download_categories_seo_details_report, args=(filename,oc_report_obj.uuid,location_group_obj,"sub",))
                p1.start()
            elif seo_type=="category":
                p1 = threading.Thread(target=bulk_download_categories_seo_details_report, args=(filename,oc_report_obj.uuid,location_group_obj,"",))
                p1.start()
            elif seo_type=="supercategory":
                p1 = threading.Thread(target=bulk_download_categories_seo_details_report, args=(filename,oc_report_obj.uuid,location_group_obj,"super",))
                p1.start()
            elif seo_type=="brand":
                p1 = threading.Thread(target=bulk_download_brand_seo_details_report, args=(filename,oc_report_obj.uuid,location_group_obj,))
                p1.start()
            elif seo_type=="brandsubcategory":
                p1 = threading.Thread(target=bulk_download_brand_categories_seo_details_report, args=(filename,oc_report_obj.uuid,location_group_obj,"sub",))
                p1.start()
            elif seo_type=="brandcategory":
                p1 = threading.Thread(target=bulk_download_brand_categories_seo_details_report, args=(filename,oc_report_obj.uuid,location_group_obj,"",))
                p1.start()
            elif seo_type=="brandsupercategory":
                p1 = threading.Thread(target=bulk_download_brand_categories_seo_details_report, args=(filename,oc_report_obj.uuid,location_group_obj,"super",))
                p1.start()

            response["approved"] = True
            response['status'] = 200
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateSEOReportAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class BulkUploadSEODetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:
            data = request.data
            logger.info("BulkUploadSEODetailsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            path = default_storage.save('tmp/bulk-upload-seo-details.xlsx', data["import_file"])
            path = "http://cdn.omnycomm.com.s3.amazonaws.com/"+path

            dfs = pd.read_excel(path, sheet_name=None, header=None)["Sheet1"]
            dfs = dfs.fillna("")

            seo_type = dfs.iloc[0][1] # identifier

            if seo_type=="product":
                p1 = threading.Thread(target=bulk_upload_product_seo_details_report, args=(dfs, seo_type, location_group_obj,))
                p1.start()
            elif seo_type=="subcategory":
                p1 = threading.Thread(target=bulk_upload_categories_seo_details_report, args=(dfs, seo_type, location_group_obj,))
                p1.start()
            elif seo_type=="category":
                p1 = threading.Thread(target=bulk_upload_categories_seo_details_report, args=(dfs, seo_type, location_group_obj,))
                p1.start()
            elif seo_type=="supercategory":
                p1 = threading.Thread(target=bulk_upload_categories_seo_details_report, args=(dfs, seo_type, location_group_obj,))
                p1.start()
            elif seo_type=="brandsubcategory":
                p1 = threading.Thread(target=bulk_upload_brand_categories_seo_details_report, args=(dfs, seo_type, location_group_obj,))
                p1.start()
            elif seo_type=="brandcategory":
                p1 = threading.Thread(target=bulk_upload_brand_categories_seo_details_report, args=(dfs, seo_type, location_group_obj,))
                p1.start()
            elif seo_type=="brandsupercategory":
                p1 = threading.Thread(target=bulk_upload_brand_categories_seo_details_report, args=(dfs, seo_type, location_group_obj,))
                p1.start()
            elif seo_type=="brand":
                p1 = threading.Thread(target=bulk_upload_brand_seo_details_report, args=(dfs, seo_type, location_group_obj,))
                p1.start()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("BulkUploadSEODetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)
        


class CreateContentReportAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:
            data = request.data
            logger.info("CreateContentReportAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if OCReport.objects.filter(is_processed=False).count()>4:
                response["approved"] = False
                response['status'] = 200
                return Response(data=response)

            brand_name = data["brand_name"]
            brand_list = [brand_name]

            report_type = "Mega"

            filename = "files/reports/"+str(datetime.datetime.now().strftime("%d%m%Y%H%M_"))+report_type+".xlsx"

            oc_user_obj = OmnyCommUser.objects.get(username=request.user.username)

            custom_permission_obj = CustomPermission.objects.get(user=request.user)

            organization_obj = custom_permission_obj.organization

            oc_report_obj = OCReport.objects.create(name=report_type, report_title="Content Health", created_by=oc_user_obj, note="", filename=filename, organization=organization_obj)

            filter_parameters = data["filter_parameters"]

            search_list_product_objs = Product.objects.filter(base_product__brand__name=brand_name, base_product__brand__organization=custom_permission_obj.organization)

            search_list_product_objs = content_health_filtered_list(filter_parameters,search_list_product_objs)

            search_list_product_objs = search_list_product_objs.values_list("uuid")

            p1 = threading.Thread(target=create_mega_bulk_oc_report, args=(filename,oc_report_obj.uuid,brand_list,search_list_product_objs,organization_obj,))

            p1.start()         

            response["approved"] = True
            response["status"] = 200   

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateContentReportAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchOCReportPermissionsAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("FetchOCReportPermissionsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            custom_permission_obj = CustomPermission.objects.get(user=request.user)
            oc_reports = json.loads(custom_permission_obj.oc_reports)

            response["oc_report_permission_list"] = oc_reports
            response['status'] = 200
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOCReportPermissionsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchOCReportListAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("FetchOCReportListAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            custom_permission_obj = CustomPermission.objects.get(user=request.user)
            oc_reports = json.loads(custom_permission_obj.oc_reports)

            oc_report_objs = OCReport.objects.filter(name__in=oc_reports,
                                organization=custom_permission_obj.organization).order_by('-pk')

            page = int(data.get("page",1))
            paginator = Paginator(oc_report_objs, 20)
            total_reports = len(oc_report_objs)
            oc_report_objs = paginator.page(page)

            oc_report_list = []
            for oc_report_obj in oc_report_objs:
                try:
                    completion_date = ""
                    if oc_report_obj.completion_date!=None:
                        completion_date = str(timezone.localtime(oc_report_obj.completion_date).strftime("%d %m, %Y %H:%M"))
                    temp_dict = {
                        "name": oc_report_obj.report_title,
                        "created_date": str(timezone.localtime(oc_report_obj.created_date).strftime("%d %m, %Y %H:%M")),
                        "created_by": str(oc_report_obj.created_by),
                        "is_processed": oc_report_obj.is_processed,
                        "completion_date": completion_date,
                        "note": oc_report_obj.note,
                        "filename": SERVER_IP+"/"+oc_report_obj.filename,
                        "uuid": oc_report_obj.uuid
                    }
                    oc_report_list.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchOCReportListAPI: %s at %s", e, str(exc_tb.tb_lineno))        

            is_available = True
            if paginator.num_pages == page:
                is_available = False

            response["is_available"] = is_available
            response["total_reports"] = total_reports

            response["oc_report_list"] = oc_report_list
            response['status'] = 200
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOCReportListAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class UpdateChannelProductStockandPriceAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:
            
            data = request.data
            logger.info("UpdateChannelProductStockandPriceAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_pk = data["product_pk"]
            channel_name = data["channel_name"]

            channel_obj = Channel.objects.get(name=channel_name)

            if(permission_channel_boolean_response(request.user,channel_obj)==False):
                response['status'] = 403
                logger.warning("UpdateChannelProductStockandPriceAPI Restricted Access of "+channel_name+" Channel!")
                return Response(data=response)

            product_obj = Product.objects.get(pk=int(product_pk))
            channel_product = product_obj.channel_product

            channel_product_dict = get_channel_product_dict(channel_name,channel_product)

            price_permission = custom_permission_price(request.user, channel_name)
            stock_permission = custom_permission_stock(request.user, channel_name)

            if price_permission:

                if "now_price" in data:
                    if channel_name == "Noon":
                        channel_product_dict["sale_price"] = float(data["now_price"])
                    else:
                        channel_product_dict["now_price"] = float(data["now_price"])
                if "was_price" in data:
                    channel_product_dict["was_price"] = float(data["was_price"])
            
            if stock_permission:
                if "stock" in data:
                    channel_product_dict["stock"] = int(data["stock"])

            channel_product = assign_channel_product_json(channel_name,channel_product,channel_product_dict)

            channel_product.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateChannelProductStockandPriceAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class DownloadDynamicExcelTemplateAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:
            
            data = request.data
            logger.info("DownloadDynamicExcelTemplateAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            data_point_list = data["data_point_list"]

            filename = "files/dynamic bulk upload excel/Excel Template.xlsx"

            workbook = xlsxwriter.Workbook(filename)
            worksheet1 = workbook.add_worksheet()

            row = generate_dynamic_row(data_point_list,False)
            colnum = 0
            for k in row:
                worksheet1.write(0, colnum, k)
                colnum += 1

            worksheet2 = workbook.add_worksheet()
            worksheet2.write(0, 0, "Category")
            worksheet2.write(0, 1, "SubCategory")
            category_objs = Category.objects.all()
            rownum = 1
            for category_obj in category_objs:
                category_name = category_obj.name
                for sub_category_obj in SubCategory.objects.filter(category=category_obj):
                    sub_category_name = sub_category_obj.name
                    worksheet2.write(rownum, 0, category_name)
                    worksheet2.write(rownum, 1, sub_category_name)
                    rownum += 1

            workbook.close()

            response["path"] = SERVER_IP+"/"+filename
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DownloadDynamicExcelTemplateAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class BulkUploadDynamicExcelAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:
            
            data = request.data
            logger.info("BulkUploadDynamicExcelAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            operation = data["operation"]

            path = default_storage.save('tmp/temp-dynamic-template-upload.xlsx', data["import_file"])
            path = "http://cdn.omnycomm.com.s3.amazonaws.com/"+path

            incoming_response = upload_dynamic_excel_for_product(path,operation,request.user)
                
            if(incoming_response["status"]!=200):
                response["error"] = incoming_response["status_message"]
                return Response(data=response)

            response["path"] = SERVER_IP+"/"+incoming_response["result_path"]
            response["accepted_products"] = incoming_response["accepted_products"]
            response["rejected_products"] = incoming_response["rejected_products"]
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("BulkUploadDynamicExcelAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchDataPointsForUploadAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:
            
            data = request.data
            logger.info("FetchDataPointsForUploadAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            operation = data["operation"]

            data_point_objs = DataPoint.objects.all().exclude(name__icontains="image").exclude(name__icontains="Image")

            for i in range(2,11):
                data_point_objs = data_point_objs.exclude(variable__icontains="_"+str(i))

            required_fields_to_create = ["seller_sku","product_id","product_name","brand","manufacturer","manufacturer_part_number","category","sub_category"]
            required_fields_to_update = ["product_id"]

            data_point_list = []
            for data_point_obj in data_point_objs:
                temp_dict = {}
                temp_dict["name"] = data_point_obj.name
                temp_dict["variable"] = data_point_obj.variable
                if(str(data_point_obj.variable).split("_")[-1]=="1"):
                    temp_dict["is_list"] = True
                else:
                    temp_dict["is_list"] = False
                if(operation == "Create"): 
                    if(str(data_point_obj.variable) in required_fields_to_create):
                        temp_dict["is_required"] = True
                    else:
                        temp_dict["is_required"] = False
                if(operation == "Update"): 
                    if(str(data_point_obj.variable) in required_fields_to_update):
                        temp_dict["is_required"] = True
                    else:
                        temp_dict["is_required"] = False

                data_point_list.append(temp_dict)

            response["data_point_list"] = data_point_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchDataPointsForUploadAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchDealshubProductDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:

            data = request.data
            logger.info("FetchDealshubProductDetailsAPI: %s", str(data))
            
            if not isinstance(data, dict):
                data = json.loads(data)

            uuid = data["product_uuid"]
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=uuid)

            is_b2b = False
            location_group_uuid = data.get("locationGroupUuid","")
            if location_group_uuid != "":
                location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
                is_b2b = location_group_obj.is_b2b

            response["product_name"] = dealshub_product_obj.get_name()
            response["product_name_ar"] = dealshub_product_obj.get_name("ar")
            response["product_description"] = dealshub_product_obj.get_description()
            response["product_description_ar"] = dealshub_product_obj.get_description("ar")
            response["seller_sku"] = dealshub_product_obj.get_seller_sku()
            response["product_id"] = dealshub_product_obj.get_product_id()
            response["moq"] = dealshub_product_obj.moq
            response["was_price"] = dealshub_product_obj.was_price
            response["now_price"] = dealshub_product_obj.now_price
            response["promotional_price"] = dealshub_product_obj.promotional_price
            response["stock"] = dealshub_product_obj.stock
            response["allowed_qty"] = dealshub_product_obj.allowed_qty
            response["is_cod_allowed"] = dealshub_product_obj.is_cod_allowed
            response["is_published"] = dealshub_product_obj.is_published
            response["is_new_arrival"] = dealshub_product_obj.is_new_arrival
            response["is_on_sale"] = dealshub_product_obj.is_on_sale
            response["is_promotional"] = dealshub_product_obj.promotion!=None
            response["product_is_promotional"] = dealshub_product_obj.is_promotional
            if dealshub_product_obj.promotion!=None:
                response["promo_tag_name"] = dealshub_product_obj.promotion.promotion_tag
                response["promo_start_time"] = dealshub_product_obj.promotion.start_time
                response["promo_end_time"] = dealshub_product_obj.promotion.end_time

            if is_b2b == True:
                response["now_price_cohort1"] = dealshub_product_obj.now_price_cohort1
                response["now_price_cohort2"] = dealshub_product_obj.now_price_cohort2
                response["now_price_cohort3"] = dealshub_product_obj.now_price_cohort3
                response["now_price_cohort4"] = dealshub_product_obj.now_price_cohort4
                response["now_price_cohort5"] = dealshub_product_obj.now_price_cohort5

                response["promotional_price_cohort1"] = dealshub_product_obj.promotional_price_cohort1
                response["promotional_price_cohort2"] = dealshub_product_obj.promotional_price_cohort2
                response["promotional_price_cohort3"] = dealshub_product_obj.promotional_price_cohort3
                response["promotional_price_cohort4"] = dealshub_product_obj.promotional_price_cohort4
                response["promotional_price_cohort5"] = dealshub_product_obj.promotional_price_cohort5

                response["moq_cohort1"] = dealshub_product_obj.moq_cohort1
                response["moq_cohort2"] = dealshub_product_obj.moq_cohort2
                response["moq_cohort3"] = dealshub_product_obj.moq_cohort3
                response["moq_cohort4"] = dealshub_product_obj.moq_cohort4
                response["moq_cohort5"] = dealshub_product_obj.moq_cohort5

            response["search_keywords"] = dealshub_product_obj.get_search_keywords()

            response["url"] = dealshub_product_obj.url

            response["category"] = dealshub_product_obj.get_category()
            response["sub_category"] = dealshub_product_obj.get_sub_category()
            response["category_uuid"] = "" if dealshub_product_obj.category==None else str(dealshub_product_obj.category.uuid)
            response["sub_category_uuid"] = "" if dealshub_product_obj.sub_category==None else str(dealshub_product_obj.sub_category.uuid)

            response["is_promo_restricted"] = dealshub_product_obj.is_promo_restricted

            response["super_category"] = "" if dealshub_product_obj.category==None else str(dealshub_product_obj.category.super_category)
            response["super_category_uuid"] = "" if dealshub_product_obj.category==None else str(dealshub_product_obj.category.super_category.uuid)

            response["dealshub_price_permission"] = custom_permission_price(request.user, "dealshub")
            response["dealshub_stock_permission"] = custom_permission_stock(request.user, "dealshub")

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchDealshubProductDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveDealshubProductDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:

            data = request.data
            logger.info("SaveDealshubProductDetailsAPI: %s", str(data))
            
            if not isinstance(data, dict):
                data = json.loads(data)

            uuid = data["product_uuid"]
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=uuid)

            is_b2b = False
            location_group_uuid = data.get("locationGroupUuid","")
            if location_group_uuid != "":
                location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
                is_b2b = location_group_obj.is_b2b

            was_price = data["was_price"]
            now_price = data["now_price"]
            promotional_price = data["promotional_price"]
            stock = data["stock"]
            allowed_qty = data.get("allowed_qty", 100)
            moq = data.get("moq", 5)
            is_cod_allowed = data["is_cod_allowed"]
            is_new_arrival = data.get("is_new_arrival", False)
            is_on_sale = data.get("is_on_sale", False)
            is_promotional = data.get("is_promotional",False)
            category_uuid = data["category_uuid"]
            sub_category_uuid = data["sub_category_uuid"]

            product_name = data.get("product_name", "")
            product_name_ar = data.get("product_name_ar","")
            product_description = data.get("product_description", "")
            product_description_ar = data.get("product_description_ar","")

            is_promo_restricted = data.get("is_promo_restricted", False)

            search_keywords = data.get("search_keywords", [])

            url = data.get("url", "default-product")

            dealshub_product_obj.was_price = was_price
            dealshub_product_obj.now_price = now_price
            dealshub_product_obj.promotional_price = promotional_price
            dealshub_product_obj.stock = stock
            dealshub_product_obj.allowed_qty = allowed_qty
            dealshub_product_obj.is_cod_allowed = is_cod_allowed
            dealshub_product_obj.is_new_arrival = is_new_arrival
            dealshub_product_obj.is_on_sale = is_on_sale
            dealshub_product_obj.is_promo_restricted = is_promo_restricted

            dealshub_product_obj.product_name = product_name
            dealshub_product_obj.product_name_ar = product_name_ar
            dealshub_product_obj.product_description = product_description
            dealshub_product_obj.product_description_ar = product_description_ar
            dealshub_product_obj.url = url
            dealshub_product_obj.moq = moq

            if is_b2b == True:
                dealshub_product_obj.now_price_cohort1 = data["now_price_cohort1"]
                dealshub_product_obj.now_price_cohort2 = data["now_price_cohort2"]
                dealshub_product_obj.now_price_cohort3 = data["now_price_cohort3"]
                dealshub_product_obj.now_price_cohort4 = data["now_price_cohort4"]
                dealshub_product_obj.now_price_cohort5 = data["now_price_cohort5"]

                dealshub_product_obj.promotional_price_cohort1 = data["promotional_price_cohort1"]
                dealshub_product_obj.promotional_price_cohort2 = data["promotional_price_cohort2"]
                dealshub_product_obj.promotional_price_cohort3 = data["promotional_price_cohort3"]
                dealshub_product_obj.promotional_price_cohort4 = data["promotional_price_cohort4"]
                dealshub_product_obj.promotional_price_cohort5 = data["promotional_price_cohort5"]

                dealshub_product_obj.moq_cohort1 = data["moq_cohort1"]
                dealshub_product_obj.moq_cohort2 = data["moq_cohort2"]
                dealshub_product_obj.moq_cohort3 = data["moq_cohort3"]
                dealshub_product_obj.moq_cohort4 = data["moq_cohort4"]
                dealshub_product_obj.moq_cohort5 = data["moq_cohort5"]

            dealshub_product_obj.set_search_keywords(search_keywords)

            promotion_obj = dealshub_product_obj.promotion
            if is_promotional:
                promotion = data["promotion"]
                start_date = str(promotion["start_date"])[:-1] + "+0400"
                end_date = str(promotion["end_date"])[:-1] + "+0400"
                promotional_tag = promotion["promotional_tag"]
                if promotion_obj==None:
                    promotion_obj = Promotion.objects.create(promotion_tag=promotional_tag, start_time=start_date, end_time=end_date)
                else:
                    promotion_obj.promotion_tag = promotional_tag
                    promotion_obj.start_time = start_date
                    promotion_obj.end_time = end_date
                    promotion_obj.save()
                dealshub_product_obj.is_promotional = True
            else:
                if dealshub_product_obj.is_promotional==True:
                    promotion_obj = None
                dealshub_product_obj.is_promotional = False

            dealshub_product_obj.promotion = promotion_obj
            
            category_obj = None
            try:
                category_obj = Category.objects.get(uuid=category_uuid)
            except Exception as e:
                pass

            sub_category_obj = None
            try:
                sub_category_obj = SubCategory.objects.get(uuid=sub_category_uuid)
            except Exception as e:
                pass

            dealshub_product_obj.category = category_obj
            dealshub_product_obj.sub_category = sub_category_obj
            dealshub_product_obj.save()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveDealshubProductDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchExportTemplatesAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:

            data = request.data
            logger.info("FetchExportTemplatesAPI: %s", str(data))
            
            if not isinstance(data, dict):
                data = json.loads(data)

            export_template_objs = ExportTemplate.objects.filter(user__username=request.user.username)

            export_template_list = []
            for export_template_obj in export_template_objs:
                try:
                    temp_dict = {}
                    temp_dict["name"] = export_template_obj.name
                    temp_dict["uuid"] = export_template_obj.uuid
                    data_point_list = []
                    data_point_objs = export_template_obj.data_points.all()
                    for data_point_obj in data_point_objs:
                        temp_dict2 = {}
                        temp_dict2["name"] = data_point_obj.name
                        temp_dict2["variable"] = data_point_obj.variable
                        data_point_list.append(temp_dict2)
                    temp_dict["data_point_list"] = data_point_list
                    export_template_list.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchExportTemplatesAPI: %s at %s", e, str(exc_tb.tb_lineno))                    

            response["export_template_list"] = export_template_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchExportTemplatesAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CreateExportTemplateAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:
            data = request.data
            logger.info("CreateExportTemplateAPI: %s", str(data))
            
            if not isinstance(data, dict):
                data = json.loads(data)

            name = data["name"]
            data_point_list = data["data_point_list"]

            omnycomm_user_obj = OmnyCommUser.objects.get(username=request.user.username)
            export_template_obj = ExportTemplate.objects.create(user=omnycomm_user_obj, name=name)

            for data_point in data_point_list:
                data_point_obj = DataPoint.objects.get(variable=data_point)
                export_template_obj.data_points.add(data_point_obj)

            export_template_obj.save()
            response["uuid"] = export_template_obj.uuid
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateExportTemplateAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DeleteExportTemplateAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:
            data = request.data
            logger.info("DeleteExportTemplateAPI: %s", str(data))
            
            if not isinstance(data, dict):
                data = json.loads(data)

            uuid = data["uuid"]

            export_template_obj = ExportTemplate.objects.get(uuid=uuid)
            export_template_obj.delete()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteExportTemplateAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SecureDeleteProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:
            data = request.data
            logger.info("SecureDeleteProductAPI: %s", str(data))
            
            if not isinstance(data, dict):
                data = json.loads(data)

            custom_permission_obj = CustomPermission.objects.get(user__username=request.user.username)
            if custom_permission_obj.delete_product==False:
                response["status"] = 403
                logger.warning("SecureDeleteProductAPI: Access denied!")
                return Response(data=response)

            uuid = data["uuid"]
            product_obj = Product.objects.get(uuid=uuid)

            if product_obj.verified==True or product_obj.locked==True:
                response["status"] = 403
                logger.warning("SecureDeleteProductAPI: Product is verified or locked!")
                return Response(data=response)

            base_product_obj = product_obj.base_product

            dealshub_product_objs = DealsHubProduct.objects.filter(product=product_obj)
            if dealshub_product_objs.filter(is_published=True).exists()==True:
                response["status"] = 403
                logger.warning("SecureDeleteProductAPI: DealsHubProduct is active!")
                return Response(data=response)


            product_obj.is_deleted = True
            product_obj.save()

            dealshub_product_objs.update(is_deleted=True)

            if Product.objects.filter(base_product=base_product_obj).exists()==False:
                base_product_obj.is_deleted = True
                base_product_obj.save()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SecureDeleteProductAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class LogoutOCUserAPI(APIView):
    
    def post(self, request, *args, **kwargs):
    
        response = {}
        response['status'] = 500

        try:
            data = request.data
            logger.info("LogoutUserAPI: %s", str(data))
            
            if not isinstance(data, dict):
                data = json.loads(data)
            
            token = request.META["HTTP_AUTHORIZATION"].split(" ")[1]
            blacklist_token_obj, created = BlackListToken.objects.get_or_create(token=token)

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("LogoutUserAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


DownloadDynamicExcelTemplate = DownloadDynamicExcelTemplateAPI.as_view()

BulkUploadDynamicExcel = BulkUploadDynamicExcelAPI.as_view()

FetchDataPointsForUpload = FetchDataPointsForUploadAPI.as_view()

GithubWebhook = GithubWebhookAPI.as_view()

SapIntegration = SapIntegrationAPI.as_view()

FetchUserProfile = FetchUserProfileAPI.as_view()

EditUserProfile = EditUserProfileAPI.as_view()

CreateNewProduct = CreateNewProductAPI.as_view()

CreateNewBaseProduct = CreateNewBaseProductAPI.as_view()

FetchBaseProductDetailsAPI = FetchBaseProductDetailsAPI.as_view()

FetchProductDetails = FetchProductDetailsAPI.as_view()

SaveProduct = SaveProductAPI.as_view()

FetchProductList = FetchProductListAPI.as_view()

FetchExportList = FetchExportListAPI.as_view()

AddToExport = AddToExportAPI.as_view()

FetchExportProductList = FetchExportProductListAPI.as_view()

DownloadExportList = DownloadExportListAPI.as_view()

ImportProducts = ImportProductsAPI.as_view()

UploadProductImage = UploadProductImageAPI.as_view()

UpdateMainImage = UpdateMainImageAPI.as_view()

UpdateSubImages = UpdateSubImagesAPI.as_view()

CreateFlyer = CreateFlyerAPI.as_view()

CreatePFL = CreatePFLAPI.as_view()

FetchFlyerDetails = FetchFlyerDetailsAPI.as_view()

FetchPFLDetails = FetchPFLDetailsAPI.as_view()

FetchProductListFlyerPFL = FetchProductListFlyerPFLAPI.as_view()

AddProductFlyerBucket = AddProductFlyerBucketAPI.as_view()

AddProductPFLBucket = AddProductPFLBucketAPI.as_view()

FetchProductDetailsFlyerPFL = FetchProductDetailsFlyerPFLAPI.as_view()

SaveFlyerTemplate = SaveFlyerTemplateAPI.as_view()

SavePFLTemplate = SavePFLTemplateAPI.as_view()

UploadImageExternalBucketFlyer = UploadImageExternalBucketFlyerAPI.as_view()

UploadImageExternalBucketPFL = UploadImageExternalBucketPFLAPI.as_view()

FetchPFLList = FetchPFLListAPI.as_view()

FetchFlyerList = FetchFlyerListAPI.as_view()

UploadNewFlyerBGImage = UploadNewFlyerBGImageAPI.as_view()

UploadFlyerTag = UploadFlyerTagAPI.as_view()

UploadFlyerPriceTag = UploadFlyerPriceTagAPI.as_view()

DownloadImagesS3 = DownloadImagesS3API.as_view()

FetchBrands = FetchBrandsAPI.as_view()

SavePFLInBucket = SavePFLInBucketAPI.as_view()

SaveFlyerInBucket = SaveFlyerInBucketAPI.as_view()

VerifyProduct = VerifyProductAPI.as_view()

LockProduct = LockProductAPI.as_view()

CopyBestImages = CopyBestImagesAPI.as_view()

DeleteImage = DeleteImageAPI.as_view()

RemoveImage = RemoveImageAPI.as_view()

RemoveProductFromExportList = RemoveProductFromExportListAPI.as_view()

DownloadProduct = DownloadProductAPI.as_view()

UploadFlyerExternalImages = UploadFlyerExternalImagesAPI.as_view()

UploadPFLExternalImages = UploadPFLExternalImagesAPI.as_view()

SaveAmazonUKChannelProduct = SaveAmazonUKChannelProductAPI.as_view()

SaveAmazonUAEChannelProduct = SaveAmazonUAEChannelProductAPI.as_view()

SaveEbayChannelProduct = SaveEbayChannelProductAPI.as_view()

SaveNoonChannelProduct = SaveNoonChannelProductAPI.as_view()

FetchChannelProduct = FetchChannelProductAPI.as_view()

SaveBaseProduct = SaveBaseProductAPI.as_view()

FetchDealsHubProducts = FetchDealsHubProductsAPI.as_view()

UpdateDealshubProduct = UpdateDealshubProductAPI.as_view()

BulkUpdateDealshubProductPrice = BulkUpdateDealshubProductPriceAPI.as_view()

BulkUpdateB2BDealshubProductPrice = BulkUpdateB2BDealshubProductPriceAPI.as_view()

BulkUpdateB2BDealshubProductMOQ = BulkUpdateB2BDealshubProductMOQAPI.as_view()

BulkUpdateDealshubProductStock = BulkUpdateDealshubProductStockAPI.as_view()

BulkUpdateDealshubProductPublishStatus  = BulkUpdateDealshubProductPublishStatusAPI.as_view()

FetchAuditLogsByUser = FetchAuditLogsByUserAPI.as_view()

CreateRequestHelp = CreateRequestHelpAPI.as_view()

FetchChannelProductList = FetchChannelProductListAPI.as_view()

FetchLocationGroupList = FetchLocationGroupListAPI.as_view()

FetchAuditLogs = FetchAuditLogsAPI.as_view()

SaveCompanyProfile = SaveCompanyProfileAPI.as_view()

UploadCompanyLogo = UploadCompanyLogoAPI.as_view()

UploadCompanyFooterLogo = UploadCompanyFooterLogoAPI.as_view()

FetchCompanyProfile = FetchCompanyProfileAPI.as_view()

RefreshProductPriceAndStock = RefreshProductPriceAndStockAPI.as_view()

RefreshPagePriceAndStock = RefreshPagePriceAndStockAPI.as_view()

# Bulk Export APIs
UploadBulkExport = UploadBulkExportAPI.as_view()

SearchBulkExport = SearchBulkExportAPI.as_view()

FetchDataPoints = FetchDataPointsAPI.as_view()

DownloadBulkExport = DownloadBulkExportAPI.as_view()

TransferBulkChannel = TransferBulkChannelAPI.as_view()

FetchAllCategories = FetchAllCategoriesAPI.as_view()

CheckSectionPermissions = CheckSectionPermissionsAPI.as_view()

CreateOCReport = CreateOCReportAPI.as_view()

FetchOCReportPermissions = FetchOCReportPermissionsAPI.as_view()

FetchOCReportList = FetchOCReportListAPI.as_view()

CreateSEOReport = CreateSEOReportAPI.as_view()

BulkUploadSEODetails = BulkUploadSEODetailsAPI.as_view()

CreateContentReport = CreateContentReportAPI.as_view()

UpdateChannelProductStockandPrice = UpdateChannelProductStockandPriceAPI.as_view()

FetchDealshubProductDetails = FetchDealshubProductDetailsAPI.as_view()

SaveDealshubProductDetails = SaveDealshubProductDetailsAPI.as_view()

FetchExportTemplates = FetchExportTemplatesAPI.as_view()

CreateExportTemplate = CreateExportTemplateAPI.as_view()

DeleteExportTemplate = DeleteExportTemplateAPI.as_view()

SecureDeleteProduct = SecureDeleteProductAPI.as_view()

LogoutOCUser = LogoutOCUserAPI.as_view()