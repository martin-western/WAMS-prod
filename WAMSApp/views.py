from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

from WAMSApp.models import *
from WAMSApp.utils import *

from django.shortcuts import render, HttpResponse, get_object_or_404
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models import Count
from django.conf import settings

from PIL import Image as IMage
import StringIO
from django.core.files.uploadedfile import InMemoryUploadedFile

import barcode
from barcode.writer import ImageWriter

import requests
import json
import os
import xlrd
import csv
import datetime
import boto3
import urllib2
import pandas as pd

logger = logging.getLogger(__name__)


class CsrfExemptSessionAuthentication(SessionAuthentication):

    def enforce_csrf(self, request):
        return


def Login(request):
    return render(request, 'WAMSApp/login.html')


@login_required(login_url='/login/')
def Logout(request):
    logout(request)
    return HttpResponseRedirect('/login/')


@login_required(login_url='/login/')
def EditProductPage(request, pk):

    product_obj = Product.objects.get(pk=int(pk))
    base_product_obj = product_obj.base_product
    permissible_brands = custom_permission_filter_brands(request.user)
    if base_product_obj.brand not in permissible_brands:
        return HttpResponseRedirect('/products/')

    return render(request, 'WAMSApp/edit-product-page.html')

@login_required(login_url='/login/')
def EcommerceListingPage(request, pk):

    product_obj = Product.objects.get(pk=int(pk))
    base_product_obj = product_obj.base_product
    permissible_brands = custom_permission_filter_brands(request.user)
    if base_product_obj.brand not in permissible_brands:
        return HttpResponseRedirect('/products/')

    return render(request, 'WAMSApp/ecommerce-listing-page.html')


@login_required(login_url='/login/')
def Products(request):
    return render(request, 'WAMSApp/products.html')


@login_required(login_url='/login/')
def ExportListPage(request):
    return render(request, 'WAMSApp/export-list.html')


def RedirectHome(request):
    return HttpResponseRedirect('/products/')


@login_required(login_url='/login/')
def PFLPage(request, pk):
    return render(request, 'WAMSApp/pfl.html')


@login_required(login_url='/login/')
def PFLDashboardPage(request):
    return render(request, 'WAMSApp/pfl-dashboard.html')


@login_required(login_url='/login/')
def FlyerPage(request, pk):
    flyer_obj = Flyer.objects.get(pk=int(pk))
    if flyer_obj.mode=="A4 Portrait":
        return render(request, 'WAMSApp/flyer.html')
    elif flyer_obj.mode=="A4 Landscape":
        return render(request, 'WAMSApp/flyer-landscape.html')
    elif flyer_obj.mode=="A5 Portrait":
        return render(request, 'WAMSApp/flyer-a5-portrait.html')
    elif flyer_obj.mode=="A5 Landscape":
        return render(request, 'WAMSApp/flyer-a5-landscape.html')


@login_required(login_url='/login/')
def FlyerDashboardPage(request):
    return render(request, 'WAMSApp/flyer-dashboard.html')


@login_required(login_url='/login/')
def ChannelProductAmazonUKPage(request, pk):
    return render(request, 'WAMSApp/channel-product-amazon-uk-page.html')

@login_required(login_url='/login/')
def ChannelProductAmazonUAEPage(request, pk):
    return render(request, 'WAMSApp/channel-product-amazon-uae-page.html')

@login_required(login_url='/login/')
def ChannelProductEbayPage(request, pk):
    return render(request, 'WAMSApp/channel-product-ebay-page.html')

@login_required(login_url='/login/')
def ChannelProductNoonPage(request, pk):
    return render(request, 'WAMSApp/channel-product-noon-page.html')

class LoginSubmitAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("LoginSubmitAPI: %s", str(data))

            username = data['username']
            password = data['password']

            user = authenticate(username=username, password=password)

            login(request, user)

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("LoginSubmitAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchConstantValuesAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchConstantValuesAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            category_list = []
            category_objs = Category.objects.all()
            for category_obj in category_objs:
                temp_dict = {}
                temp_dict["name"] = category_obj.name
                temp_dict["pk"] = category_obj.pk
                category_list.append(temp_dict)

            material_list = []
            material_objs = MaterialType.objects.all()
            for material_obj in material_objs:
                temp_dict = {}
                temp_dict["name"] = material_obj.name
                temp_dict["pk"] = material_obj.pk
                material_list.append(temp_dict)

            brand_list = []
            brand_objs = custom_permission_filter_brands(request.user)
            for brand_obj in brand_objs:
                temp_dict = {}
                temp_dict["name"] = brand_obj.name
                temp_dict["pk"] = brand_obj.pk
                brand_list.append(temp_dict)

            product_id_type_list = []
            product_id_type_objs = ProductIDType.objects.all()
            for product_id_type_obj in product_id_type_objs:
                temp_dict = {}
                temp_dict["name"] = product_id_type_obj.name
                temp_dict["pk"] = product_id_type_obj.pk
                product_id_type_list.append(temp_dict)

            ebay_category_list = []
            ebay_category_objs = EbayCategory.objects.all()
            for ebay_category_obj in ebay_category_objs:
                temp_dict = {}
                temp_dict["name"] = ebay_category_obj.name
                temp_dict["category_id"] = ebay_category_obj.category_id
                temp_dict["pk"] = ebay_category_obj.pk
                ebay_category_list.append(temp_dict)

            response["category_list"] = category_list
            response["ebay_category_list"] = ebay_category_list
            response["material_list"] = material_list
            response["brand_list"] = brand_list
            response["product_id_type_list"] = product_id_type_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchConstantValuesAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CreateNewBaseProductAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if request.user.has_perm('WAMSApp.add_product') == False:
                logger.warning("CreateNewProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("CreateNewBaseProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_name = convert_to_ascii(data["product_name"])
            seller_sku = convert_to_ascii(data["seller_sku"])
            brand_name = convert_to_ascii(data["brand_name"])

            # Checking brand permission
            brand_obj = None
            try:
                permissible_brands = custom_permission_filter_brands(
                    request.user)
                brand_obj = Brand.objects.get(name=brand_name)
                logger.info("Brand Obj is %s", str(brand_obj))
                if brand_obj not in permissible_brands:
                    logger.warning(
                        "CreateNewBaseProductAPI Restricted Access Brand!")
                    response['status'] = 403
                    return Response(data=response)
            except Exception as e:
                logger.error("CreateNewBaseProductAPI Restricted Access Brand!")
                response['status'] = 403
                return Response(data=response)

            if BaseProduct.objects.filter(seller_sku=seller_sku).exists():
                logger.warning("CreateNewBaseProductAPI Duplicate product detected!")
                response["status"] = 409
                return Response(data=response)

            base_product_obj = BaseProduct.objects.create(base_product_name=product_name,
                                              seller_sku=seller_sku,
                                              brand=brand_obj)

            product_obj = Product.objects.create(product_name=product_name,
                                              base_product=base_product_obj)

            response["product_pk"] = product_obj.pk
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateNewBaseProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class CreateNewProductAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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
            try:
                permissible_brands = custom_permission_filter_brands(
                    request.user)
                brand_obj = base_product_obj.brand
                logger.info("Brand Obj is %s", str(brand_obj))
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
            product_obj = Product.objects.create(product_name = product_name,
                                            product_name_sap=product_name,
                                            pfl_product_name=product_name,
                                            base_product=base_product_obj)

            response["product_pk"] = product_obj.pk
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateNewProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveNoonChannelProductAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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
                permissible_channels = custom_permission_filter_channels(
                    request.user)
                channel_obj = Channel.objects.get(name=channel_name)
                logger.info("Channel Obj is %s", str(channel_obj))
                
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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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
                permissible_channels = custom_permission_filter_channels(
                    request.user)
                channel_obj = Channel.objects.get(name=channel_name)
                logger.info("Channel Obj is %s", str(channel_obj))
                
                if channel_obj not in permissible_channels:
                    logger.warning(
                        "SaveAmazonUKChannelProductAPI Restricted Access of Amazon UK Channel!")
                    response['status'] = 403
                    return Response(data=response)
            
            except Exception as e:
                logger.error("SaveAmazonUKChannelProductAPI Restricted Access of Amazon UK Channel!")
                response['status'] = 403
                return Response(data=response)

            amazon_uk_product_json = json.loads(data["amazon_uk_product_json"])
            amazon_uk_product_json["created_date"] = datetime.datetime.now().strftime("%d %b, %Y")

            channel_product = product_obj.channel_product
            logger.info(" Amazon UK Product JSON Saved %s",amazon_uk_product_json)
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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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
                logger.info("Channel Obj is %s", str(channel_obj))
                
                if channel_obj not in permissible_channels:
                    logger.warning(
                        "SaveAmazonUAEChannelProductAPI Restricted Access of Amazon UAE Channel!")
                    response['status'] = 403
                    return Response(data=response)
            
            except Exception as e:
                logger.error("SaveAmazonUAEChannelProductAPI Restricted Access of Amazon UAE Channel!")
                response['status'] = 403
                return Response(data=response)

            amazon_uae_product_json = json.loads(data["amazon_uae_product_json"])
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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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
                permissible_channels = custom_permission_filter_channels(
                    request.user)
                channel_obj = Channel.objects.get(name=channel_name)
                logger.info("Channel Obj is %s", str(channel_obj))
                
                if channel_obj not in permissible_channels:
                    logger.warning(
                        "SaveEbayChannelProductAPI Restricted Access of Ebay Channel!")
                    response['status'] = 403
                    return Response(data=response)
            
            except Exception as e:
                logger.error("SaveEbayChannelProductAPI Restricted Access of Ebay Channel!")
                response['status'] = 403
                return Response(data=response)

            ebay_product_json = json.loads(data["ebay_product_json"])
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

class FetchNoonChannelProductAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchNoonChannelProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_obj = Product.objects.get(pk=data["product_pk"])
            channel_product_obj = product_obj.channel_product
            base_product_obj = product_obj.base_product
            brand_obj = base_product_obj.brand

            permissible_brands = custom_permission_filter_brands(request.user)

            if brand_obj not in permissible_brands:
                logger.warning("FetchNoonChannelProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            channel_name = "Noon"
            channel_obj = Channel.objects.get(name=channel_name)
            noon_product_json = channel_product_obj.noon_product_json

            images = {}

            main_images_list = ImageBucket.objects.none()
            try:
                main_images_obj = MainImages.objects.get(product=product_obj,channel=channel_obj)
                main_images_list=main_images_obj.main_images.all()
                main_images_list = main_images_list.distinct()
                images["main_images"] = create_response_images_main(main_images_list)
            except Exception as e:
                images["main_images"] = []
                temp_dict = {}
                image = Config.objects.all()[0].product_404_image
                temp_dict["main-url"] = image.image.url
                
                try:
                    temp_dict["thumbnail-url"] = image.thumbnail.url
                except Exception as e:
                    logger.warning("No thumbnail for main image with pk %s", str(image.pk))
                    temp_dict["thumbnail-url"] = image.image.url

                try:
                    temp_dict["midimage-url"] = image.mid_image.url
                except Exception as e:
                    logger.warning("No mid_image for main image with pk %s", str(image.pk))
                    temp_dict["midimage-url"] = image.image.url

                temp_dict["pk"] = image.pk
                temp_dict["is_main_image"] = False
                pass


            sub_images_list = ImageBucket.objects.none()
            try:
                sub_images_obj = SubImages.objects.get(product=product_obj,channel=channel_obj)
                sub_images_list = sub_images_obj.sub_images.all()
                sub_images_list = sub_images_list.distinct()
            except Exception as e:
                pass

            images["sub_images"] = create_response_images_sub(sub_images_list)

            images["all_images"] = create_response_images_main_sub_delete(main_images_list) \
                                    + create_response_images_main_sub_delete(sub_images_list)


            response["images"] = images
            response["noon_product_json"] = noon_product_json
            response["product_id"] = product_obj.product_id
            response["material_type"] = ""
            if product_obj.material_type != None:
                response["material_type"] = product_obj.material_type.name
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchNoonChannelProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchAmazonUKChannelProductAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchAmazonUKChannelProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_obj = Product.objects.get(pk=data["product_pk"])
            channel_product_obj = product_obj.channel_product
            base_product_obj = product_obj.base_product
            brand_obj = base_product_obj.brand

            permissible_brands = custom_permission_filter_brands(request.user)

            if brand_obj not in permissible_brands:
                logger.warning("FetchAmazonUKChannelProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            channel_name = "Amazon UK"
            channel_obj = Channel.objects.get(name=channel_name)
            amazon_uk_product_json = channel_product_obj.amazon_uk_product_json

            images = {}

            main_images_list = ImageBucket.objects.none()
            try:
                main_images_obj = MainImages.objects.get(product=product_obj,channel=channel_obj)
                main_images_list=main_images_obj.main_images.all()
                main_images_list = main_images_list.distinct()
                images["main_images"] = create_response_images_main(main_images_list)
            except Exception as e:
                images["main_images"] = []
                temp_dict = {}
                image = Config.objects.all()[0].product_404_image
                temp_dict["main-url"] = image.image.url
                
                try:
                    temp_dict["thumbnail-url"] = image.thumbnail.url
                except Exception as e:
                    logger.warning("No thumbnail for main image with pk %s", str(image.pk))
                    temp_dict["thumbnail-url"] = image.image.url

                try:
                    temp_dict["midimage-url"] = image.mid_image.url
                except Exception as e:
                    logger.warning("No mid_image for main image with pk %s", str(image.pk))
                    temp_dict["midimage-url"] = image.image.url

                temp_dict["pk"] = image.pk
                temp_dict["is_main_image"] = False
                pass


            sub_images_list = ImageBucket.objects.none()
            try:
                sub_images_obj = SubImages.objects.get(product=product_obj,channel=channel_obj)
                sub_images_list = sub_images_obj.sub_images.all()
                sub_images_list = sub_images_list.distinct()
            except Exception as e:
                pass

            images["sub_images"] = create_response_images_sub(sub_images_list)

            images["all_images"] = create_response_images_main_sub_delete(main_images_list) \
                                    + create_response_images_main_sub_delete(sub_images_list)


            response["images"] = images

            response["amazon_uk_product_json"] = json.loads(amazon_uk_product_json)
            logger.info(" Amazon UK Product JSON Fetched %s",amazon_uk_product_json)
            response["product_id"] = product_obj.product_id
            response["material_type"] = ""
            if product_obj.material_type != None:
                response["material_type"] = product_obj.material_type.name
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchAmazonUKChannelProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchAmazonUAEChannelProductAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchAmazonUAEChannelProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_obj = Product.objects.get(pk=data["product_pk"])
            channel_product_obj = product_obj.channel_product
            base_product_obj = product_obj.base_product
            brand_obj = base_product_obj.brand

            permissible_brands = custom_permission_filter_brands(request.user)

            if brand_obj not in permissible_brands:
                logger.warning("FetchAmazonUAEChannelProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            channel_name = "Amazon UAE"
            channel_obj = Channel.objects.get(name=channel_name)
            amazon_uae_product_json = channel_product_obj.amazon_uae_product_json

            images = {}

            main_images_list = ImageBucket.objects.none()
            try:
                main_images_obj = MainImages.objects.get(product=product_obj,channel=channel_obj)
                main_images_list=main_images_obj.main_images.all()
                main_images_list = main_images_list.distinct()
                images["main_images"] = create_response_images_main(main_images_list)
            except Exception as e:
                images["main_images"] = []
                temp_dict = {}
                image = Config.objects.all()[0].product_404_image
                temp_dict["main-url"] = image.image.url
                
                try:
                    temp_dict["thumbnail-url"] = image.thumbnail.url
                except Exception as e:
                    logger.warning("No thumbnail for main image with pk %s", str(image.pk))
                    temp_dict["thumbnail-url"] = image.image.url

                try:
                    temp_dict["midimage-url"] = image.mid_image.url
                except Exception as e:
                    logger.warning("No mid_image for main image with pk %s", str(image.pk))
                    temp_dict["midimage-url"] = image.image.url

                temp_dict["pk"] = image.pk
                temp_dict["is_main_image"] = False
                pass

            sub_images_list = ImageBucket.objects.none()
            try:
                sub_images_obj = SubImages.objects.get(product=product_obj,channel=channel_obj)
                sub_images_list = sub_images_obj.sub_images.all()
                sub_images_list = sub_images_list.distinct()
            except Exception as e:
                pass

            images["sub_images"] = create_response_images_sub(sub_images_list)

            images["all_images"] = create_response_images_main_sub_delete(main_images_list) \
                                    + create_response_images_main_sub_delete(sub_images_list)


            response["images"] = images

            response["amazon_uae_product_json"] = amazon_uae_product_json
            response["product_id"] = product_obj.product_id
            response["material_type"] = ""
            if product_obj.material_type != None:
                response["material_type"] = product_obj.material_type.name
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchAmazonUAEChannelProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchEbayChannelProductAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchEbayChannelProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_obj = Product.objects.get(pk=data["product_pk"])
            channel_product_obj = product_obj.channel_product
            base_product_obj = product_obj.base_product
            brand_obj = base_product_obj.brand

            permissible_brands = custom_permission_filter_brands(request.user)

            if brand_obj not in permissible_brands:
                logger.warning("FetchEbayChannelProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            channel_name = "Ebay"
            channel_obj = Channel.objects.get(name=channel_name)
            ebay_product_json = channel_product_obj.ebay_product_json

            images = {}

            main_images_list = ImageBucket.objects.none()
            
            try:
                main_images_obj = MainImages.objects.get(product=product_obj,channel=channel_obj)
                main_images_list=main_images_obj.main_images.all()
                main_images_list = main_images_list.distinct()
                images["main_images"] = create_response_images_main(main_images_list)
            
            except Exception as e:
                images["main_images"] = []
                temp_dict = {}
                image = Config.objects.all()[0].product_404_image
                temp_dict["main-url"] = image.image.url
                
                try:
                    temp_dict["thumbnail-url"] = image.thumbnail.url
                except Exception as e:
                    logger.warning("No thumbnail for main image with pk %s", str(image.pk))
                    temp_dict["thumbnail-url"] = image.image.url

                try:
                    temp_dict["midimage-url"] = image.mid_image.url
                except Exception as e:
                    logger.warning("No mid_image for main image with pk %s", str(image.pk))
                    temp_dict["midimage-url"] = image.image.url

                temp_dict["pk"] = image.pk
                temp_dict["is_main_image"] = False
                pass

            sub_images_list = ImageBucket.objects.none()
            try:
                sub_images_obj = SubImages.objects.get(product=product_obj,channel=channel_obj)
                sub_images_list = sub_images_obj.sub_images.all()
                sub_images_list = sub_images_list.distinct()
            except Exception as e:
                pass

            images["sub_images"] = create_response_images_sub(sub_images_list)

            images["all_images"] = create_response_images_main_sub_delete(main_images_list) \
                                    + create_response_images_main_sub_delete(sub_images_list)


            response["images"] = images
            
            response["ebay_product_json"] = ebay_product_json
            response["product_id"] = product_obj.product_id
            response["material_type"] = ""
            if product_obj.material_type != None:
                response["material_type"] = product_obj.material_type.name
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchEbayChannelProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchProductDetailsAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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
                response["brand_logo"] = brand_obj.logo.image.url
            except Exception as e:
                response["brand_logo"] = ''

            try:
                response["barcode_string"] = product_obj.barcode_string
            except Exception as e:
                response["barcode_string"] = ''
            logger.info("%s",amazon_uk_product_dict)
            response["product_name_amazon_uk"] = amazon_uk_product_dict["product_name"]
            response["product_name_amazon_uae"] = amazon_uae_product_dict["product_name"]
            response["product_name_ebay"] = ebay_product_dict["product_name"]
            response["product_name_noon"] = noon_product_dict["product_name"]

            response["product_name"] = product_obj.product_name
            response["product_name_sap"] = product_obj.product_name_sap
            response["category"] = base_product_obj.category
            response["subtitle"] = base_product_obj.subtitle
            
            response["factory_notes"] = product_obj.factory_notes

            if brand_obj == None:
                response["brand_name"] = ""
            else:
                response["brand_name"] = brand_obj.name

            response["manufacturer"] = base_product_obj.manufacturer
            response["product_id"] = product_obj.product_id
            
            if product_obj.product_id_type != None:
                response["product_id_type"] = product_obj.product_id_type.name
            else:
                response["product_id_type"] = ""


            response["noon_product_type"] = noon_product_dict["product_type"]
            response["noon_product_subtype"] = noon_product_dict["product_subtype"]
            response["noon_model_number"] = noon_product_dict["model_number"]
            response["noon_model_name"] = noon_product_dict["model_name"]

            response["seller_sku"] = base_product_obj.seller_sku
            response["manufacturer_part_number"] = base_product_obj.manufacturer_part_number
            
            response["condition_type"] = amazon_uk_product_dict["condition_type"]
            response["feed_product_type"] = amazon_uk_product_dict["feed_product_type"]
            response["update_delete"] = amazon_uk_product_dict["update_delete"]
            response["recommended_browse_nodes"] = amazon_uk_product_dict["recommended_browse_nodes"]
            response["product_description_amazon_uk"] = amazon_uk_product_dict["product_description"]
            response["product_description_amazon_uae"] = amazon_uae_product_dict["product_description"]
            response["product_description_ebay"] = ebay_product_dict["product_description"]
            response["product_description_noon"] = noon_product_dict["product_description"]
            response["product_attribute_list_amazon_uk"] = amazon_uk_product_dict["product_attribute_list"]
            response["product_attribute_list_amazon_uae"] = amazon_uae_product_dict["product_attribute_list"]
            response["product_attribute_list_ebay"] = ebay_product_dict["product_attribute_list"]
            response["product_attribute_list_noon"] = noon_product_dict["product_attribute_list"]
            response["search_terms"] = amazon_uk_product_dict["search_terms"]
            response["color_map"] = product_obj.color_map
            response["color"] = product_obj.color
            response["enclosure_material"] = amazon_uk_product_dict["enclosure_material"]
            response["cover_material_type"] = amazon_uk_product_dict["cover_material_type"]
            response["special_features"] = amazon_uk_product_dict["special_features"]

            response["package_length"] = "" if base_product_obj.package_length == None else base_product_obj.package_length
            response["package_length_metric"] = base_product_obj.package_length_metric
            response["package_width"] = "" if base_product_obj.package_width == None else base_product_obj.package_width
            response["package_width_metric"] = base_product_obj.package_width_metric
            response["package_height"] = "" if base_product_obj.package_height == None else base_product_obj.package_height
            response["package_height_metric"] = base_product_obj.package_height_metric
            response["package_weight"] = "" if base_product_obj.package_weight == None else base_product_obj.package_weight
            response["package_weight_metric"] = base_product_obj.package_weight_metric
            response["shipping_weight"] = "" if base_product_obj.shipping_weight == None else base_product_obj.shipping_weight
            response["shipping_weight_metric"] = base_product_obj.shipping_weight_metric
            response["item_display_weight"] = "" if base_product_obj.item_display_weight == None else base_product_obj.item_display_weight
            response["item_display_weight_metric"] = base_product_obj.item_display_weight_metric
            response["item_display_volume"] = "" if base_product_obj.item_display_volume == None else base_product_obj.item_display_volume
            response["item_display_volume_metric"] = base_product_obj.item_display_volume_metric
            response["item_display_length"] = "" if base_product_obj.item_display_length == None else base_product_obj.item_display_length
            response["item_display_length_metric"] = base_product_obj.item_display_length_metric
            response["item_weight"] = "" if base_product_obj.item_weight == None else base_product_obj.item_weight
            response["item_weight_metric"] = base_product_obj.item_weight_metric
            response["item_length"] = "" if base_product_obj.item_length == None else base_product_obj.item_length
            response["item_length_metric"] = base_product_obj.item_length_metric
            response["item_width"] = "" if base_product_obj.item_width == None else base_product_obj.item_width
            response["item_width_metric"] = base_product_obj.item_width_metric
            response["item_height"] = "" if base_product_obj.item_height == None else base_product_obj.item_height
            response["item_height_metric"] = base_product_obj.item_height_metric
            response["item_display_width"] = "" if base_product_obj.item_display_width == None else base_product_obj.item_display_width
            response["item_display_width_metric"] = base_product_obj.item_display_width_metric
            response["item_display_height"] = "" if base_product_obj.item_display_height == None else base_product_obj.item_display_height
            response["item_display_height_metric"] = base_product_obj.item_display_height_metric

            
            response["item_count"] = "" if amazon_uk_product_dict["item_count"] == None else amazon_uk_product_dict["item_count"]
            response["item_count_metric"] = amazon_uk_product_dict["item_count_metric"]
            response["item_condition_note"] = amazon_uk_product_dict["item_condition_note"]
            response["max_order_quantity"] = "" if amazon_uk_product_dict["max_order_quantity"] == None else amazon_uk_product_dict["max_order_quantity"]
            response["number_of_items"] = "" if amazon_uk_product_dict["number_of_items"] == None else amazon_uk_product_dict["number_of_items"]
            
            response["wattage"] = "" if amazon_uk_product_dict["wattage"] == None else amazon_uk_product_dict["wattage"]
            response["wattage_metric"] = amazon_uk_product_dict["wattage_metric"]
            
            if product_obj.material_type != None:
                response["material_type"] = product_obj.material_type.name
            else:
                response["material_type"] = ""
            
            response["parentage"] = amazon_uk_product_dict["parentage"]
            response["parent_sku"] = amazon_uk_product_dict["parent_sku"]
            response["relationship_type"] = amazon_uk_product_dict["relationship_type"]
            response["variation_theme"] = amazon_uk_product_dict["variation_theme"]
            response["standard_price"] = "" if product_obj.standard_price == None else product_obj.standard_price
            response["quantity"] = "" if product_obj.quantity == None else product_obj.quantity
            response["sale_price"] = "" if amazon_uk_product_dict["sale_price"] == None else amazon_uk_product_dict["sale_price"]
            response["sale_from"] = "" if amazon_uk_product_dict["sale_from"] == None else amazon_uk_product_dict["sale_from"]
            response["sale_end"] = "" if amazon_uk_product_dict["sale_end"] == None else amazon_uk_product_dict["sale_end"]
            response["sale_price"] = "" if amazon_uk_product_dict["sale_price"] == None else amazon_uk_product_dict["sale_price"]
            

            response["noon_msrp_ae"] = "" if noon_product_dict["msrp_ae"] == None else noon_product_dict["msrp_ae"]
            response["noon_msrp_ae_unit"] = str(noon_product_dict["msrp_ae_unit"])

            response["verified"] = product_obj.verified

            images = {}

            main_images_list = ImageBucket.objects.none()
            main_images_objs = MainImages.objects.filter(product=product_obj)
            for main_images_obj in main_images_objs:
                main_images_list|=main_images_obj.main_images.all()
            main_images_list = main_images_list.distinct()
            images["main_images"] = create_response_images_main(main_images_list)
            
            sub_images_list = ImageBucket.objects.none()
            sub_images_objs = SubImages.objects.filter(product=product_obj)
            for sub_images_obj in sub_images_objs:
                sub_images_list|=sub_images_obj.sub_images.all()
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
                product_obj.unedited_images.all())
            images["transparent_images"] = create_response_images(
                product_obj.transparent_images.all())

            images["all_images"] = images["pfl_images"] + images["pfl_generated_images"] + \
                images["white_background_images"] + images["lifestyle_images"] + \
                images["certificate_images"] + images["giftbox_images"] + \
                images["diecut_images"] + images["aplus_content_images"] + \
                images["ads_images"] + images["unedited_images"] + images["transparent_images"] + create_response_images_main_sub_delete(main_images_list) + create_response_images_main_sub_delete(sub_images_list)


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

            response["images"] = images
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class SaveBaseProductAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

            try:
                permissible_brands = custom_permission_filter_brands(request.user)
                brand_obj = Brand.objects.get(name=data["brand_name"])
                if brand_obj not in permissible_brands:
                    logger.warning("SaveBaseProductAPI Restricted Access Brand!")
                    response['status'] = 403
                    return Response(data=response)
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
            category = convert_to_ascii(data["category"])
            subtitle = convert_to_ascii(data["subtitle"])
            package_length = None if data["package_length"] == "" else float(data["package_length"])
            package_length_metric = data["package_length_metric"]
            package_width = None if data["package_width"] == "" else float(data["package_width"])
            package_width_metric = data["package_width_metric"]
            package_height = None if data["package_height"] == "" else float(data["package_height"])
            package_height_metric = data["package_height_metric"]
            package_weight = None if data["package_weight"] == "" else float(data["package_weight"])
            package_weight_metric = data["package_weight_metric"]
            package_quantity = None if data["package_quantity"] == "" else float(data["package_quantity"])
            shipping_weight = None if data["shipping_weight"] == "" else float(data["shipping_weight"])
            shipping_weight_metric = data["shipping_weight_metric"]
            item_display_weight = None if data["item_display_weight"] == "" else float(data["item_display_weight"])
            item_display_weight_metric = data["item_display_weight_metric"]
            item_display_volume = None if data["item_display_volume"] == "" else float(data["item_display_volume"])
            item_display_volume_metric = data["item_display_volume_metric"]
            item_display_length = None if data["item_display_length"] == "" else float(data["item_display_length"])
            item_display_length_metric = data["item_display_length_metric"]
            item_weight = None if data["item_weight"] == "" else float(data["item_weight"])
            item_weight_metric = data["item_weight_metric"]
            item_length = None if data["item_length"] == "" else float(data["item_length"])
            item_length_metric = data["item_length_metric"]
            item_width = None if data["item_width"] == "" else float(data["item_width"])
            item_width_metric = data["item_width_metric"]
            item_height = None if data["item_height"] == "" else float(data["item_height"])
            item_height_metric = data["item_height_metric"]
            item_display_width = None if data["item_display_width"] == "" else float(data["item_display_width"])
            item_display_width_metric = data["item_display_width_metric"]
            item_display_height = None if data["item_display_height"] == "" else float(data["item_display_height"])
            item_display_height_metric = data["item_display_height_metric"]
            
            if BaseProduct.objects.filter(seller_sku=seller_sku).exclude(pk=data["base_product_pk"]).count() >= 1 :
                logger.warning("Duplicate product detected!")
                response['status'] = 409
                return Response(data=response)

            base_product_obj.base_product_name = base_product_name
            base_product_obj.seller_sku = seller_sku
            base_product_obj.brand = brand_obj
            base_product_obj.manufacturer = manufacturer
            base_product_obj.manufacturer_part_number = manufacturer_part_number
            base_product_obj.category = category
            base_product_obj.subtitle = subtitle

            base_product_obj.package_length = package_length
            base_product_obj.package_length_metric = package_length_metric
            base_product_obj.package_width = package_width
            base_product_obj.package_width_metric = package_width_metric
            base_product_obj.package_height = package_height
            base_product_obj.package_height_metric = package_height_metric
            base_product_obj.package_weight = package_weight
            base_product_obj.package_weight_metric = package_weight_metric
            base_product_obj.package_quantity = package_quantity
            base_product_obj.shipping_weight = shipping_weight
            base_product_obj.shipping_weight_metric = shipping_weight_metric
            base_product_obj.item_display_weight = item_display_weight
            base_product_obj.item_display_weight_metric = item_display_weight_metric
            base_product_obj.item_display_volume = item_display_volume
            base_product_obj.item_display_volume_metric = item_display_volume_metric
            base_product_obj.item_display_length = item_display_length
            base_product_obj.item_display_length_metric = item_display_length_metric
            base_product_obj.item_weight = item_weight
            base_product_obj.item_weight_metric = item_weight_metric
            base_product_obj.item_length = item_length
            base_product_obj.item_length_metric = item_length_metric
            base_product_obj.item_width = item_width
            base_product_obj.item_width_metric = item_width_metric
            base_product_obj.item_height = item_height
            base_product_obj.item_height_metric = item_height_metric
            base_product_obj.item_display_width = item_display_width
            base_product_obj.item_display_width_metric = item_display_width_metric
            base_product_obj.item_display_height = item_display_height
            base_product_obj.item_display_height_metric = item_display_height_metric
            
            base_product_obj.save()
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveBaseProductAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveProductAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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
            
            # Checking brand permission
            try:
                permissible_brands = custom_permission_filter_brands(request.user)
                brand_obj = Brand.objects.get(name=product_obj.base_product.brand.name)
                if brand_obj not in permissible_brands:
                    logger.warning("SaveProductAPI Restricted Access Brand!")
                    response['status'] = 403
                    return Response(data=response)
            except Exception as e:
                logger.error("SaveProductAPI Restricted Access Brand!")
                response['status'] = 403
                return Response(data=response)

            if Product.objects.filter(product_id=product_id).exclude(pk=data["product_pk"]).count() >= 1 :
                logger.warning("Duplicate product detected!")
                response['status'] = 409
                return Response(data=response)

            product_name = convert_to_ascii(data["product_name"])
            barcode_string = convert_to_ascii(data["barcode_string"])
            color = convert_to_ascii(data["color"])
            color_map = convert_to_ascii(data["color_map"])
            standard_price = None if data["standard_price"] == "" else float(data["standard_price"])
            quantity = None if data["quantity"] == "" else int(data["quantity"])
            
            product_id_type = convert_to_ascii(data["product_id_type"])
            product_id_type_obj , created = ProductIDType.objects.get_or_create(name=product_id_type)
            
            material_type = convert_to_ascii(data["material_type"])
            material_type_obj , created = MaterialType.objects.get_or_create(name=material_type)
            
            pfl_product_name = convert_to_ascii(data["pfl_product_name"])
            pfl_product_features = convert_to_ascii(data["pfl_product_features"])

            factory_notes = convert_to_ascii(data["factory_notes"])

            product_obj.product_id = product_id

            try:
                if product_obj.barcode_string != barcode_string and barcode_string != "":
                    EAN = barcode.ean.EuropeanArticleNumber13(str(barcode_string), writer=ImageWriter())
                    
                    thumb = EAN.save('temp_image')
                    thumb = IMage.open(open(thumb, "rb"))
                    thumb_io = StringIO.StringIO()
                    thumb.save(thumb_io, format='PNG')
                    thumb_file = InMemoryUploadedFile(thumb_io, None, 'barcode_' + product_obj.product_id + '.png', 'image/PNG', thumb_io.len, None)

                    barcode_image = Image.objects.create(image=thumb_file)
                    product_obj.barcode = barcode_image
                    product_obj.barcode_string = barcode_string

                    try:
                        import os
                        os.remove("temp_image.png")
                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        logger.warning("SaveProductAPI: %s at %s",
                                       e, str(exc_tb.tb_lineno))

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SaveProductAPI: %s at %s",
                             e, str(exc_tb.tb_lineno))

            product_obj.product_name = product_name

            product_obj.product_id_type = product_id_type_obj
            product_obj.color_map = color_map
            product_obj.color = color
            
            product_obj.material_type = material_type_obj
            product_obj.standard_price = standard_price
            product_obj.quantity = quantity
            
            product_obj.pfl_product_name = pfl_product_name
            product_obj.pfl_product_features = pfl_product_features

            product_obj.factory_notes = factory_notes
            
            product_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveProductAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchProductListAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchProductListAPI: %s", str(data))

            filter_parameters = json.loads(data['filter_parameters'])
            chip_data = json.loads(data['tags'])

            page = int(data['page'])
            
            search_list_base_product_objs = []
            search_list_product_objs = []

            product_objs_list = []
            base_product_objs_list = []

            base_product_objs_list = custom_permission_filter_base_products(request.user)
            product_objs_list = custom_permission_filter_products(request.user)

            if filter_parameters['verified']:
                product_objs_list = product_objs_list.filter(
                    verified=filter_parameters['verified']).order_by('-pk')
            else:
                product_objs_list = product_objs_list.order_by('-pk')

            if filter_parameters["start_date"] != "" and filter_parameters["end_date"] != "":
                start_date = datetime.datetime.strptime(
                    filter_parameters["start_date"], "%b %d, %Y")
                end_date = datetime.datetime.strptime(
                    filter_parameters["end_date"], "%b %d, %Y")
                base_product_objs_list = base_product_objs_list.filter(
                    created_date__gte=start_date).filter(created_date__lte=end_date)

            if filter_parameters["brand_name"] != "":
                brand_obj = Brand.objects.get(name=filter_parameters["brand_name"])
                base_product_objs_list = base_product_objs_list.filter(brand=brand_obj)

            if filter_parameters["min_price"] != "":
                product_objs_list = product_objs_list.filter(
                    standard_price__gte=int(filter_parameters["min_price"]))

            if filter_parameters["max_price"] != "":
                product_objs_list = product_objs_list.filter(
                    standard_price__lte=int(filter_parameters["max_price"]))

            if filter_parameters["has_image"] == "1":
                for product_obj in product_objs_list:
                    if has_atleast_one_image(product_obj)==False:
                        product_objs_list.exclude(pk=product_obj.pk)
            elif filter_parameters["has_image"] == "0":
                for product_obj in product_objs_list:
                    if has_atleast_one_image(product_obj)==True:
                        product_objs_list.exclude(pk=product_obj.pk)

            if len(chip_data) == 0:
                search_list_product_objs = product_objs_list
                for prod in product_objs_list:
                    search_list_base_product_objs.append(prod.base_product)
                    search_list_base_product_objs = list( dict.fromkeys(search_list_base_product_objs) )
            else:
                for tag in chip_data:
                    search = product_objs_list.filter(
                        Q(product_name__icontains=tag) |
                        Q(product_name_sap__icontains=tag) |
                        Q(product_id__icontains=tag) |
                        Q(base_product__seller_sku__icontains=tag)
                    )
                    logger.info(" Filtered Products %s",search_list_product_objs)
                    for prod in search:
                        search_list_product_objs.append(prod)
                        search_list_base_product_objs.append(prod.base_product)
                        search_list_base_product_objs = list( dict.fromkeys(search_list_base_product_objs) )

            products = []

            paginator = Paginator(search_list_base_product_objs, 20)
            base_product_objs = paginator.page(page)

            for base_product_obj in base_product_objs:
                temp_dict = {}
                temp_dict["base_product_pk"] = base_product_obj.pk
                temp_dict["product_name"] = base_product_obj.base_product_name
                temp_dict["manufacturer"] = base_product_obj.manufacturer
                temp_dict["manufacturer_part_number"] = base_product_obj.manufacturer_part_number
                
                if base_product_obj.brand != None:
                    temp_dict["brand_name"] = base_product_obj.brand.name
                else:
                    temp_dict["brand_name"] = "-"
                
                temp_dict["created_date"] = str(
                    base_product_obj.created_date.strftime("%d %b, %Y"))

                temp_dict["products"] = []
                temp_dict["channel_products"] = []
                temp_dict["dimensions"] = {}

                temp_dict["seller_sku"] = base_product_obj.seller_sku
                temp_dict["category"] = base_product_obj.category
                temp_dict["subtitle"] = base_product_obj.subtitle


                temp_dimensions_dict = {}
                temp_dimensions_dict["package_length"] = "" if base_product_obj.package_length == None else base_product_obj.package_length
                temp_dimensions_dict["package_length_metric"] = base_product_obj.package_length_metric
                temp_dimensions_dict["package_width"] = "" if base_product_obj.package_width == None else base_product_obj.package_width
                temp_dimensions_dict["package_width_metric"] = base_product_obj.package_width_metric
                temp_dimensions_dict["package_height"] = "" if base_product_obj.package_height == None else base_product_obj.package_height
                temp_dimensions_dict["package_height_metric"] = base_product_obj.package_height_metric
                temp_dimensions_dict["package_weight"] = "" if base_product_obj.package_weight == None else base_product_obj.package_weight
                temp_dimensions_dict["package_weight_metric"] = base_product_obj.package_weight_metric
                temp_dimensions_dict["package_quantity"] = "" if base_product_obj.package_quantity == None else base_product_obj.package_quantity
                
                temp_dimensions_dict["shipping_weight"] = "" if base_product_obj.shipping_weight == None else base_product_obj.shipping_weight
                temp_dimensions_dict["shipping_weight_metric"] = base_product_obj.shipping_weight_metric
                temp_dimensions_dict["item_display_weight"] = "" if base_product_obj.item_display_weight == None else base_product_obj.item_display_weight
                temp_dimensions_dict["item_display_weight_metric"] = base_product_obj.item_display_weight_metric
                temp_dimensions_dict["item_display_volume"] = "" if base_product_obj.item_display_volume == None else base_product_obj.item_display_volume
                temp_dimensions_dict["item_display_volume_metric"] = base_product_obj.item_display_volume_metric
                temp_dimensions_dict["item_display_length"] = "" if base_product_obj.item_display_length == None else base_product_obj.item_display_length
                temp_dimensions_dict["item_display_length_metric"] = base_product_obj.item_display_length_metric
                temp_dimensions_dict["item_weight"] = "" if base_product_obj.item_weight == None else base_product_obj.item_weight
                temp_dimensions_dict["item_weight_metric"] = base_product_obj.item_weight_metric
                temp_dimensions_dict["item_length"] = "" if base_product_obj.item_length == None else base_product_obj.item_length
                temp_dimensions_dict["item_length_metric"] = base_product_obj.item_length_metric
                temp_dimensions_dict["item_width"] = "" if base_product_obj.item_width == None else base_product_obj.item_width
                temp_dimensions_dict["item_width_metric"] = base_product_obj.item_width_metric
                temp_dimensions_dict["item_height"] = "" if base_product_obj.item_height == None else base_product_obj.item_height
                temp_dimensions_dict["item_height_metric"] = base_product_obj.item_height_metric
                temp_dimensions_dict["item_display_width"] = "" if base_product_obj.item_display_width == None else base_product_obj.item_display_width
                temp_dimensions_dict["item_display_width_metric"] = base_product_obj.item_display_width_metric
                temp_dimensions_dict["item_display_height"] = "" if base_product_obj.item_display_height == None else base_product_obj.item_display_height
                temp_dimensions_dict["item_display_height_metric"] = base_product_obj.item_display_height_metric

                temp_dict["dimensions"] = temp_dimensions_dict
                
                product_objs = search_list_product_objs.filter(base_product = base_product_obj)

                for product_obj in product_objs:
                    
                    temp_dict2 = {}
                    temp_dict2["product_pk"] = product_obj.pk
                    temp_dict2["product_id"] = product_obj.product_id
                    temp_dict2["product_name"] = product_obj.product_name
                    temp_dict2["status"] = product_obj.status

                    main_images_list = ImageBucket.objects.none()
                    main_images_objs = MainImages.objects.filter(product=product_obj)
                    for main_images_obj in main_images_objs:
                        main_images_list |= main_images_obj.main_images.all()

                    main_images_list = main_images_list.distinct()
                    
                    if main_images_list.filter(is_main_image=True).count() > 0:
                        try:
                            temp_dict2["main_image"] = main_images_list.filter(is_main_image=True)[
                                0].image.thumbnail.url
                        except Exception as e:
                            temp_dict2["main_image"] = Config.objects.all()[
                                0].product_404_image.image.url
                    else:
                        temp_dict2["main_image"] = Config.objects.all()[
                            0].product_404_image.image.url

                    temp_dict["products"].append(temp_dict2)

                    if product_obj.channel_product.is_noon_product_created == True:
                        
                        noon_product = json.loads(product_obj.channel_product.noon_product_json)
                        temp_dict3 = {}
                        temp_dict3["product_id"] = product_obj.product_id
                        temp_dict3["product_pk"] = product_obj.pk
                        temp_dict3["channel_product_name"] = noon_product["product_name"]
                        temp_dict3["channel_name"] = "Noon"
                        main_image_url = None
                        try:
                            main_images_obj = MainImages.objects.get(product = product, channel="Noon")
                            
                            if main_images_obj.main_images.filter(is_main_image=True).count() > 0:
                                main_image_obj = main_images_obj.main_images.filter(is_main_image=True)[0]
                                main_image_url = main_image_obj.image.image.url
                        except Exception as e:
                            pass
                        temp_dict3["image_url"] = main_image_url

                        temp_dict["channel_products"].append(temp_dict3)

                    if product_obj.channel_product.is_amazon_uk_product_created == True:
                        
                        amazon_uk_product = json.loads(product_obj.channel_product.amazon_uk_product_json)
                        temp_dict3 = {}
                        temp_dict3["product_id"] = product_obj.product_id
                        temp_dict3["product_pk"] = product_obj.pk
                        temp_dict3["channel_product_name"] = amazon_uk_product["product_name"]
                        temp_dict3["channel_name"] = "Amazon UK"
                        main_image_url = Config.objects.all()[0].product_404_image.image.url
                        try:
                            main_images_obj = MainImages.objects.get(product = product, channel="Amazon UK")
                            
                            if main_images_obj.main_images.filter(is_main_image=True).count() > 0:
                                main_image_obj = main_images_obj.main_images.filter(is_main_image=True)[0]
                                main_image_url = main_image_obj.image.image.url
                        except Exception as e:
                            pass
                        temp_dict3["image_url"] = main_image_url

                        temp_dict["channel_products"].append(temp_dict3)

                products.append(temp_dict)
            is_available = True
            if paginator.num_pages == page:
                is_available = False

            response["is_available"] = is_available
            response["total_products"] = len(search_list_base_product_objs)
            response["products"] = products
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchExportListAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchExportListAPI: %s", str(data))

            chip_data = json.loads(data.get('tags', '[]'))

            search_list_objs = []
            export_list_objs = []

            if data.get("start_date", "") != "" and data.get("end_date", "") != "":
                start_date = datetime.datetime.strptime(
                    data["start_date"], "%b %d, %Y")
                end_date = datetime.datetime.strptime(
                    data["end_date"], "%b %d, %Y")
                export_list_objs = ExportList.objects.filter(
                    created_date__gte=start_date).filter(created_date__lte=end_date).filter(user=request.user)
            else:
                export_list_objs = ExportList.objects.all().filter(user=request.user)

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
                temp_dict[
                    "product_count"] = export_list_obj.products.all().count()
                export_list.append(temp_dict)

            response["export_list"] = export_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchExportListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddToExportAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

            export_option = data["export_option"]
            export_title_pk = data["export_title_pk"]
            export_title = convert_to_ascii(data["export_title"])
            products = json.loads(data["products"])

            export_obj = None
            if export_option == "New":
                export_obj = ExportList.objects.create(
                    title=export_title, user=request.user)
            else:
                export_obj = ExportList.objects.get(pk=int(export_title_pk))

            for product_pk in products:
                product = Product.objects.get(pk=int(product_pk))
                export_obj.products.add(product)
                export_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddToExportAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchExportProductListAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchExportProductListAPI: %s", str(data))

            export_obj = ExportList.objects.get(pk=int(data["export_pk"]))
            products = export_obj.products.all()

            product_list = []
            for product in products:
                temp_dict = {}
                temp_dict["product_name"] = product.product_name
                temp_dict["product_name_sap"] = product.product_name_sap
                temp_dict["product_id"] = product.product_id
                temp_dict["product_pk"] = product.pk
                if product.main_images.filter(is_main_image=True).count() > 0:
                    temp_dict['product_image_url'] = product.main_images.filter(is_main_image=True)[
                        0].image.mid_image.url
                else:
                    temp_dict['product_image_url'] = Config.objects.all()[
                        0].product_404_image.image.url

                product_list.append(temp_dict)

            response["product_list"] = product_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchExportProductListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DownloadExportListAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DownloadExportListAPI: %s", str(data))

            export_format = data["export_format"]

            export_obj = ExportList.objects.get(pk=int(data["export_pk"]))
            products = export_obj.products.all()

            if export_format == "Amazon UK":
                success_products = export_amazon_uk(products)
                response["success_products"] = success_products
                response["total_products"] = products.count()
                response["file_path"] = "/files/csv/export-list-amazon-uk.xlsx"
            elif export_format == "Amazon UAE":
                export_amazon_uae(products)
                response["file_path"] = "/files/csv/export-list-amazon-uae.csv"
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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DownloadProductAPI: %s", str(data))

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

            product_obj = Product.objects.get(pk=int(data["product_pk"]))

            image_objs = []

            image_count = int(data["image_count"])
            for i in range(image_count):
                image_obj = Image.objects.create(image=data["image_"+str(i)])
                image_objs.append(image_obj)

            if data["image_category"] == "main_images":

                for image_obj in image_objs:
                    image_bucket_obj = ImageBucket.objects.create(
                        image=image_obj)
                    if data["channel"] == "" or data["channel"] == None:
                        main_images_obj , created = MainImages.objects.get_or_create(product=product_obj,is_sourced=True)
                    else:
                        channel_obj = Channel.objects.get(name=data["channel"])
                        main_images_obj , created = MainImages.objects.get_or_create(product=product_obj,channel=channel_obj)
                    
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

            elif data["image_category"] == "sub_images":
                index = 0
                if data["channel"] == "" or data["channel"] == None:
                    sub_images_obj , created = SubImages.objects.get_or_create(product=product_obj,is_sourced=True)
                else:
                    channel_obj = Channel.objects.get(name=data["channel"])
                    sub_images_obj , created = SubImages.objects.get_or_create(product=product_obj,channel=channel_obj)
                    
                sub_images = sub_images_obj.sub_images.all().order_by('-sub_image_index')
                if sub_images.count() > 0:
                    index = sub_images[0].sub_image_index
                for image_obj in image_objs:
                    index += 1
                    sub_image_index = 0
                    is_sub_image = False
                    if(index <= 8):
                        sub_image_index = index
                        is_sub_image = True
                    image_bucket_obj = ImageBucket.objects.create(image=image_obj,
                                                                  is_sub_image=is_sub_image,
                                                                  sub_image_index=sub_image_index)
                    sub_images_obj.sub_images.add(image_bucket_obj)
            elif data["image_category"] == "pfl_images":
                for image_obj in image_objs:
                    product_obj.pfl_images.add(image_obj)
            elif data["image_category"] == "white_background_images":
                for image_obj in image_objs:
                    product_obj.white_background_images.add(image_obj)
            elif data["image_category"] == "lifestyle_images":
                for image_obj in image_objs:
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
                    product_obj.unedited_images.add(image_obj)
            elif data["image_category"] == "transparent_images":
                for image_obj in image_objs:
                    product_obj.transparent_images.add(image_obj)

            product_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadProductImageAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UpdateMainImageAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

            product_obj = Product.objects.get(pk=int(data["product_pk"]))
            reset_main_images(product_obj)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

            product_obj = Product.objects.get(pk=int(data["product_pk"]))
            reset_sub_images(product_obj)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

            brand_obj = Brand.objects.get(pk=int(data["brand_pk"]))

            mode = data["mode"]

            flyer_obj = Flyer.objects.create(name=convert_to_ascii(data["name"]),
                                             template_data="{}",
                                             brand=brand_obj,
                                             mode=mode)

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
                "all-image-resizer": "100"
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
                            "warranty-display": False,
                            "image-resizer": "100",
                            "promo-resizer": "40",
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
                        path = "https://wig-wams-s3-bucket.s3.ap-south-1.amazonaws.com/"+path
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
                                if Product.objects.filter(product_id=search_id).exists():
                                    product_obj = Product.objects.filter(product_id=search_id)[0]
                                elif BaseProduct.objects.filter(seller_sku=search_id).exists():
                                    base_product_obj = BaseProduct.objects.get(seller_sku=search_id)
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
                                logger.error("product_id: %s , error: %s", str(dfs.iloc[i][0]), str(e))

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
                                "warranty-display": False,
                                "image-resizer": "100",
                                "promo-resizer": "40",
                                "price": str(product_price),
                                "strikeprice": str(product_strikeprice),
                                "title": str(product_title),
                                "description": str(product_description)
                            }
                            item_data.append(temp_dict)

                        template_data["item-data"] = item_data

                        logger.info("template_data: %s", str(template_data))

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchFlyerDetailsAPI: %s", str(data))

            flyer_obj = Flyer.objects.get(pk=int(data["pk"]))

            name = flyer_obj.name
            product_objs = flyer_obj.product_bucket.all()
            product_list = []
            images_dict = {}
            for product_obj in product_objs:
                temp_dict = {}
                temp_dict["product_bucket_name"] = product_obj.product_name_sap
                temp_dict["product_bucket_pk"] = product_obj.pk
                temp_dict["seller_sku"] = product_obj.seller_sku
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
                    product_obj.unedited_images.all())
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
                    temp_dict["high-res-url"] = external_images_bucket_obj.image.url
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

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFlyerDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CreatePFLAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

            pfl_obj = PFL.objects.create(name=convert_to_ascii(data["name"]))

            response["pfl_pk"] = pfl_obj.pk
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreatePFLAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchPFLDetailsAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchPFLDetailsAPI: %s", str(data))

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
                seller_sku = pfl_obj.product.seller_sku

            external_images_bucket_list = []
            external_images_bucket_objs = pfl_obj.external_images_bucket.all()
            for external_images_bucket_obj in external_images_bucket_objs:
                try:
                    temp_dict = {}
                    temp_dict["url"] = external_images_bucket_obj.mid_image.url
                    temp_dict["high-res-url"] = external_images_bucket_obj.image.url
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
                seller_sku = pfl_obj.product.seller_sku

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchProductListFlyerPFLAPI: %s", str(data))

            product_objs = custom_permission_filter_products(request.user)

            try:
                if "flyer_pk" in data:
                    brand_obj = Flyer.objects.get(
                        pk=int(data["flyer_pk"])).brand
                    product_objs = product_objs.filter(base_product__brand=brand_obj)
                    logger.info("Product Objects in FetchProductListFlyerPFLApi : %s", product_objs)
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
                    temp_dict["product_name_autocomplete"] = short_product_name + " | " + str(product_obj.product_id)
                    main_image_url = None
                    
                    try:

                        main_images_objs = MainImages.objects.filter(product = product_obj)
                        for main_images_obj in main_images_objs:
                            if main_images_obj.main_images.filter(is_main_image=True).count() > 0:
                                break

                        main_image_obj = main_images_obj.main_images.filter(is_main_image=True)[0]
                        
                        main_image_url = main_image_obj.image.image.url
                    
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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if request.user.has_perm('WAMSApp.change_flyer') == False:
                logger.warning("AddProductFlyerBucketAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("AddProductFlyerBucketAPI: %s", str(data))

            flyer_obj = Flyer.objects.get(pk=int(data["flyer_pk"]))

            product_id = data["product_name"].split("|")[-1].strip()
            product_obj = Product.objects.get(product_id=product_id)

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
                
                image_url = main_image_obj.image.image.urlrl
            
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
                product_obj.unedited_images.all())
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
            response["seller_sku"] = product_obj.seller_sku

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddProductFlyerBucketAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddProductPFLBucketAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if request.user.has_perm('WAMSApp.change_pfl') == False:
                logger.warning("AddProductPFLBucketAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("AddProductPFLBucketAPI: %s", str(data))

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchProductDetailsFlyerPFLAPI: %s", str(data))

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
                product_obj.unedited_images.all())
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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if request.user.has_perm('WAMSApp.change_flyer') == False:
                logger.warning("SaveFlyerTemplateAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("SaveFlyerTemplateAPI: %s", str(data))

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if request.user.has_perm('WAMSApp.change_pfl') == False:
                logger.warning("SavePFLTemplateAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UploadImageExternalBucketFlyerAPI: %s", str(data))

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UploadImageExternalBucketPFLAPI: %s", str(data))

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchPFLListAPI: %s", str(data))

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchFlyerListAPI: %s", str(data))

            page = int(data["page"])

            permissible_brands = custom_permission_filter_brands(request.user)
            flyer_objs = Flyer.objects.filter(brand__in=permissible_brands)

            chip_data = json.loads(data["tags"])

            if len(chip_data) > 0:
                flyer_objs = Flyer.objects.all()
                search_list_objs = []

                for flyer_obj in flyer_objs:
                    logger.info("flyer_obj %s", str(flyer_obj))
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
                            logger.info("Chip %s, product %s, flyer_obj %s", str(
                                chip), str(product), str(flyer_obj))

                            if (chip.lower() in product.product_name_sap.lower() or
                                    chip.lower() in product.product_name.lower() or
                                    chip.lower() in product.product_id.lower() or
                                    chip.lower() in product.seller_sku.lower()):
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
                    temp_dict["flyer_image"] = flyer_obj.flyer_image.image.url
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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if request.user.has_perm('WAMSApp.change_flyer') == False:
                logger.warning("UploadNewFlyerBGImageAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("UploadNewFlyerBGImageAPI: %s", str(data))

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


class DownloadImagesS3API(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DownloadImagesS3API: %s", str(data))

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
                    filename = urllib2.unquote(link["url"])
                    filename = "/".join(filename.split("/")[3:])
                    temp_dict = {}
                    temp_dict["key"] = link["key"]
                    temp_dict["url"] = "/files/images_s3/" + str(filename)
                    local_links.append(temp_dict)
                    logger.info("DownloadImagesS3API: url %s", str(temp_dict["url"]))
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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchBrandsAPI: %s", str(data))

            brand_objs = custom_permission_filter_brands(request.user)
            brand_list = []
            for brand_obj in brand_objs:
                temp_dict = {}
                temp_dict["name"] = brand_obj.name
                temp_dict["pk"] = brand_obj.pk
                brand_list.append(temp_dict)

            response["brand_list"] = brand_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchBrandsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchChannelsAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchChannelsAPI: %s", str(data))

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            #logger.info("SavePFLInBucketAPI: %s", str(data))

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            #logger.info("SavePFLInBucketAPI: %s", str(data))

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("VerifyProductAPI: %s", str(data))

            if request.user.username not in ["priyanka", "naveed", "ramees"]:
                logger.warning("VerifyProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            product_obj = Product.objects.get(pk=int(data["product_pk"]))
            verify = int(data["verify"])
            if verify == 1:
                product_obj.verified = True
                product_obj.status = "Verified"
            elif verify == 0:
                product_obj.verified = False
                product_obj.status = "Pending"

            product_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("VerifyProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DeleteImageAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

            image_type = data["image_type"]
            image_pk = int(data["image_pk"])
            if image_type == "other":
                Image.objects.get(pk=int(image_pk)).delete()
            elif image_type == "main_sub":
                ImageBucket.objects.get(pk=int(image_pk)).delete()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteImageAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class RemoveProductFromExportListAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if request.user.has_perm("WAMSApp.add_image") == False:
                logger.warning("UploadProductImageAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            #logger.info("UploadFlyerExternalImagesAPI: %s", str(data))

            flyer_obj = Flyer.objects.get(pk=int(data["flyer_pk"]))

            image_count = int(data["image_count"])
            external_images_bucket_list = []
            for i in range(image_count):
                try:
                    image_obj = Image.objects.create(image=data["image_"+str(i)])
                    flyer_obj.external_images_bucket.add(image_obj)
                    temp_dict = {}
                    temp_dict["url"] = image_obj.mid_image.url
                    temp_dict["high-res-url"] = image_obj.image.url
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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if request.user.has_perm("WAMSApp.add_image") == False:
                logger.warning("UploadProductImageAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            #logger.info("UploadFlyerExternalImagesAPI: %s", str(data))

            pfl_obj = PFL.objects.get(pk=int(data["pfl_pk"]))

            image_count = int(data["image_count"])
            external_images_bucket_list = []
            for i in range(image_count):
                try:
                    image_obj = Image.objects.create(image=data["image_"+str(i)])
                    pfl_obj.external_images_bucket.add(image_obj)
                    temp_dict = {}
                    temp_dict["url"] = image_obj.mid_image.url
                    temp_dict["high-res-url"] = image_obj.image.url
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




LoginSubmit = LoginSubmitAPI.as_view()

FetchConstantValues = FetchConstantValuesAPI.as_view()

CreateNewProduct = CreateNewProductAPI.as_view()

CreateNewBaseProduct = CreateNewBaseProductAPI.as_view()

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

DownloadImagesS3 = DownloadImagesS3API.as_view()

FetchBrands = FetchBrandsAPI.as_view()

SavePFLInBucket = SavePFLInBucketAPI.as_view()

SaveFlyerInBucket = SaveFlyerInBucketAPI.as_view()

VerifyProduct = VerifyProductAPI.as_view()

DeleteImage = DeleteImageAPI.as_view()

RemoveProductFromExportList = RemoveProductFromExportListAPI.as_view()

DownloadProduct = DownloadProductAPI.as_view()

UploadFlyerExternalImages = UploadFlyerExternalImagesAPI.as_view()

UploadPFLExternalImages = UploadPFLExternalImagesAPI.as_view()

SaveAmazonUKChannelProduct = SaveAmazonUKChannelProductAPI.as_view()

SaveAmazonUAEChannelProduct = SaveAmazonUAEChannelProductAPI.as_view()

SaveEbayChannelProduct = SaveEbayChannelProductAPI.as_view()

SaveNoonChannelProduct = SaveNoonChannelProductAPI.as_view()

FetchAmazonUKChannelProduct = FetchAmazonUKChannelProductAPI.as_view()

FetchAmazonUAEChannelProduct = FetchAmazonUAEChannelProductAPI.as_view()

FetchEbayChannelProduct = FetchEbayChannelProductAPI.as_view()

FetchNoonChannelProduct = FetchNoonChannelProductAPI.as_view()

SaveBaseProduct = SaveBaseProductAPI.as_view()

