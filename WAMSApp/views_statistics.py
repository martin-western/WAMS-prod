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

from WAMSApp.sourcing.views_sourcing import *
from WAMSApp.mws.views_mws_report import *
from WAMSApp.mws.views_mws_amazon_uk import *
from WAMSApp.mws.views_mws_amazon_uae import *
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
            logger.info("FetchStatisticsAPI: %s", str(data))

            page = int(data["page"])
            brand_name = data.get("brand_name","")

            filter_parameters = data["filter_parameters"]
           
            permissible_brands = custom_permission_filter_brands(request.user)

            if(brand_name != ""):
                permissible_brands = permissible_brands.filter(name=brand_name)

            permissible_brands = permissible_brands.annotate(num_products=Count('baseproduct')).order_by('-num_products')

            paginator = Paginator(permissible_brands, 5)
            brand_objs = paginator.page(page)

            brand_list = []
            for brand_obj in brand_objs:

                search_list_product_objs = Product.objects.filter(base_product__brand=brand_obj)
                total_products = search_list_product_objs.count()

                search_list_product_objs = content_health_filtered_list(filter_parameters,search_list_product_objs)


                temp_dict = {}
                temp_dict["brand_name"] = brand_obj.name
                temp_dict["value"] = search_list_product_objs.count()
                temp_dict["total_products"] = total_products

                brand_list.append(temp_dict)

            attribute_list = [
                "Product Description",
                "Product Name",
                "Product ID",
                "Product Verified",
                "Amazon UK Product",
                "Amazon UAE Product",
                "Noon Product",
                "Ebay Product",
                "Product Features",
                "White Background Images > 0",
                "White Background Images > 1",
                "White Background Images > 2",
                "Lifestyle Images > 0",
                "Lifestyle Images > 1",
                "Lifestyle Images > 2",
                "Giftbox Images > 0",
                "Giftbox Images > 1",
                "Giftbox Images > 2",
                "Transparent Images > 0",
                "Transparent Images > 1",
                "Transparent Images > 2",
                "Main Images",
                "Sub Images > 0",
                "Sub Images > 1",
                "Sub Images > 2"]

            is_available = True

            if paginator.num_pages == page:
                is_available = False

            response["is_available"] = is_available
            response["keys"] = attribute_list
            response["brand_list"] = brand_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchStasticsAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)

FetchStatistics = FetchStatisticsAPI.as_view()