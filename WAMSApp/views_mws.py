from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

from WAMSApp.models import *
from WAMSApp.utils import *
from WAMSApp.utils_sourcing import *

from MWS import mws,APIs

from django.shortcuts import render, HttpResponse, get_object_or_404
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models import Count
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

import requests
import json
import os
import pytz
import csv
import uuid
import logging
import sys
import xlrd
import zipfile


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

            channel_name = data["channel_name"]

            permissible_channels = custom_permission_filter_channels(
                request.user)
            channel_obj = Channel.objects.get(name=channel_name)

            if channel_obj not in permissible_channels:
                logger.warning(
                    "GetMatchingProductsAmazonUKMWSAPI Restricted Access of Noon Channel!")
                response['status'] = 403
                return Response(data=response)

            products_api = APIs.Products(MWS_ACCESS_KEY,SECRET_KEY,SELLER_ID, 
                                        region='UK')

            marketplace_id = mws.Marketplaces["UK"].marketplace_id

            product_id_type = data["product_id_type"]
            ProductIDType = product_id_type.objects.get(name=product_id_type)


            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("GetMatchingProductsAmazonUKMWSAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class GetMatchingProductsAmazonUAEMWSAPI(APIView):

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

            channel_name = data["channel_name"]

            permissible_channels = custom_permission_filter_channels(
                request.user)
            channel_obj = Channel.objects.get(name=channel_name)

            if channel_obj not in permissible_channels:
                logger.warning(
                    "GetMatchingProductsAmazonUKMWSAPI Restricted Access of Noon Channel!")
                response['status'] = 403
                return Response(data=response)

            product_id_type = data["product_id_type"]
            ProductIDType = product_id_type.objects.get(name=product_id_type)

            products_api = APIs.Products(MWS_PARAMS["MWS_ACCESS_KEY"], 
                                        MWS_PARAMS["SECRET_KEY"],
                                        MWS_PARAMS["SELLER_ID"], region='UK')

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("GetMatchingProductsAmazonUKMWSAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

GetMatchingProductsAmazonUKMWS = GetMatchingProductsAmazonUKMWSAPI.as_view()

GetMatchingProductsAmazonUAEMWS = GetMatchingProductsAmazonUAEMWSAPI.as_view()