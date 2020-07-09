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
from WAMSApp.views_mws_amazon_uk import *
from WAMSApp.views_mws_amazon_uae import *
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


class FetchStatisticsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data

            page = int(data["page"])
           
            permissible_brands = custom_permission_filter_brands(request.user)
            permissible_brands = permissible_brands.annotate(num_products=Count('baseproduct')).order_by('-num_products')

            paginator = Paginator(permissible_brands, 20)
            brand_objs = paginator.page(page)

            brand_list = []
            for brand_obj in brand_objs:

                product_objs_list = Product.objects.filter(base_product__brand=brand_obj)
                baseproduct_objs_list = BaseProduct.objects.filter(brand=brand_obj)
                total_products = product_objs_list.count()
                total_baseproducts = baseproduct_objs_list.count()

                attribute_list = []
                result_dict = {}


                yes = product_objs_list.exclude(product_description=None).exclude(product_description="").count()
                no = total_products - yes
                key = "Product Description"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.exclude(product_id=None).exclude(product_id="").count()
                no = total_products - yes
                key = "Product ID"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.filter(verified=True).count()
                no = total_products - yes
                key = "Product Verified"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.filter(channel_product__is_amazon_uae_product_created=True).count()
                no = total_products - yes
                key = "Amazon UAE Product"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.filter(channel_product__is_amazon_uk_product_created=True).count()
                no = total_products - yes
                key = "Amazon UK Product"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.filter(channel_product__is_noon_product_created=True).count()
                no = total_products - yes
                key = "Noon Product"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.filter(channel_product__is_ebay_product_created=True).count()
                no = total_products - yes
                key = "Ebay Product"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = MainImages.objects.annotate(num_main_images=Count('main_images')).filter(product__in=product_objs_list,is_sourced=True,num_main_images__gt=0).count()
                no = total_products - yes
                key = "Main Images"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = SubImages.objects.annotate(num_sub_images=Count('sub_images')).filter(product__in=product_objs_list,is_sourced=True,num_sub_images__gt=0).count()
                no = total_products - yes
                key = "Sub Images > 0"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = SubImages.objects.annotate(num_sub_images=Count('sub_images')).filter(product__in=product_objs_list,is_sourced=True,num_sub_images__gt=1).count()
                no = total_products - yes
                key = "Sub Images > 1"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = SubImages.objects.annotate(num_sub_images=Count('sub_images')).filter(product__in=product_objs_list,is_sourced=True,num_sub_images__gt=2).count()
                no = total_products - yes
                key = "Sub Images > 2"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.exclude(pfl_product_features="[]").exclude(pfl_product_features="").count()
                no = total_products - yes
                key = "Product Features"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.annotate(num_white_background_images=Count('white_background_images')).filter(num_white_background_images__gt=0).count()
                no = total_products - yes
                key = "White Backgound Images > 0"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.annotate(num_white_background_images=Count('white_background_images')).filter(num_white_background_images__gt=1).count()
                no = total_products - yes
                key = "White Background Images > 1"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.annotate(num_white_background_images=Count('white_background_images')).filter(num_white_background_images__gt=2).count()
                no = total_products - yes
                key = "White Background Images > 2"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.annotate(num_lifestyle_images=Count('lifestyle_images')).filter(num_lifestyle_images__gt=0).count()                   
                no = total_products - yes
                key = "Lifestyle Images > 0"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.annotate(num_lifestyle_images=Count('lifestyle_images')).filter(num_lifestyle_images__gt=1).count()
                no = total_products - yes
                key = "Lifestyle Images > 1"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.annotate(num_lifestyle_images=Count('lifestyle_images')).filter(num_lifestyle_images__gt=2).count()
                no = total_products - yes
                key = "Lifestyle Images > 2"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.annotate(num_giftbox_images=Count('giftbox_images')).filter(num_giftbox_images__gt=0).count()
                no = total_products - yes
                key = "Giftbox Images > 0"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.annotate(num_giftbox_images=Count('giftbox_images')).filter(num_giftbox_images__gt=1).count()
                no = total_products - yes
                key = "Giftbox Images > 1"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.annotate(num_giftbox_images=Count('giftbox_images')).filter(num_giftbox_images__gt=2).count()
                no = total_products - yes
                key = "Giftbox Images > 2"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.annotate(num_transparent_images=Count('transparent_images')).filter(num_transparent_images__gt=0).count()                   
                no = total_products - yes
                key = "Transparent Images > 0"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.annotate(num_transparent_images=Count('transparent_images')).filter(num_transparent_images__gt=1).count()                   
                no = total_products - yes
                key = "Transparent Images > 1"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.annotate(num_transparent_images=Count('transparent_images')).filter(num_transparent_images__gt=2).count()                   
                no = total_products - yes
                key = "Transparent Images > 2"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.exclude(product_name=None).exclude(product_name="").count()
                no = total_products - yes
                key = "Product Name"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                temp_dict = {}
                temp_dict["brand_name"] = brand_obj.name
                temp_dict["keys"] = attribute_list
                temp_dict["values"] = result_dict
                brand_list.append(temp_dict)

            response["brand_list"] = brand_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchStasticsAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)

FetchStatistics = FetchStatisticsAPI.as_view()