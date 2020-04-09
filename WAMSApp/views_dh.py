from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

from WAMSApp.models import *

from auditlog.models import *
from dealshub.models import DealsHubProduct
from WAMSApp.utils import *
from WAMSApp.serializers import UserSerializer, UserSerializerWithToken
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
import pandas as pd


logger = logging.getLogger(__name__)


class FetchOrdersForAccountManagerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            
            data = request.data
            logger.info("FetchOrdersForAccountManagerAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            api_access = "5a72db78-b0f2-41ff-b09e-6af02c5b4c77"

            filterStatus = data["filterStatus"]
            page = data.get("page", 1)

            r = requests.post("https://"+DEALSHUB_IP+"/api/dealshub/v1.0/fetch-orders-for-account-manager/", data={"filterStatus": filterStatus, "page":page, "api_access":api_access}, verify=False)
            response = json.loads(r.content)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOrdersForAccountManagerAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchOrdersForWarehouseManagerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            
            data = request.data
            logger.info("FetchOrdersForWarehouseManagerAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            api_access = "5a72db78-b0f2-41ff-b09e-6af02c5b4c77"

            filterStatus = data["filterStatus"]
            page = data.get("page", 1)

            r = requests.post("https://"+DEALSHUB_IP+"/api/dealshub/v1.0/fetch-orders-for-warehouse-manager/", data={"filterStatus": filterStatus, "page":page, "api_access":api_access}, verify=False)
            response = json.loads(r.content)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOrdersForWarehouseManagerAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchShippingMethodAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            
            data = request.data
            logger.info("FetchShippingMethodAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            shipping_methods = ["WIG Fleet", "TFM"]

            response["shippingMethods"] = shipping_methods
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchShippingMethodAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SetShippingMethodAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            
            data = request.data
            logger.info("SetShippingMethodAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            api_access = "5a72db78-b0f2-41ff-b09e-6af02c5b4c77"

            shipping_method = data["shippingMethod"]
            unit_order_uuid_list = data["unitOrderUuidList"]

            r = requests.post("https://"+DEALSHUB_IP+"/api/dealshub/v1.0/set-shipping-method/", data={"shippingMethod": shippingMethod, "unitOrderUuidList": json.dumps(unitOrderUuidList), "api_access":api_access}, verify=False)
            response = json.loads(r.content)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SetShippingMethodAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SetOrdersStatusAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            
            data = request.data
            logger.info("SetOrdersStatusAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            api_access = "5a72db78-b0f2-41ff-b09e-6af02c5b4c77"

            order_status = data["orderStatus"]
            unit_order_uuid_list = data["unitOrderUuidList"]

            r = requests.post("https://"+DEALSHUB_IP+"/api/dealshub/v1.0/set-shipping-method/", data={"orderStatus": order_status, "unitOrderUuidList": json.dumps(unitOrderUuidList), "api_access":api_access}, verify=False)
            response = json.loads(r.content)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SetOrdersStatusAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SetOrdersStatusAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            
            data = request.data
            logger.info("SetOrdersStatusAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            api_access = "5a72db78-b0f2-41ff-b09e-6af02c5b4c77"

            order_status = data["orderStatus"]
            unit_order_uuid_list = data["unitOrderUuidList"]

            r = requests.post("https://"+DEALSHUB_IP+"/api/dealshub/v1.0/set-orders-status/", data={"orderStatus": order_status, "unitOrderUuidList": json.dumps(unitOrderUuidList), "api_access":api_access}, verify=False)
            response = json.loads(r.content)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SetOrdersStatusAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CancelOrdersAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            
            data = request.data
            logger.info("CancelOrdersAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            api_access = "5a72db78-b0f2-41ff-b09e-6af02c5b4c77"

            order_status = data["orderStatus"]
            unit_order_uuid_list = data["unitOrderUuidList"]
            cancelling_note = data["cancellingNote"]

            r = requests.post("https://"+DEALSHUB_IP+"/api/dealshub/v1.0/cancel-orders/", data={"cancellingNote": cancelling_note, "unitOrderUuidList": json.dumps(unit_order_uuid_list), "api_access":api_access}, verify=False)
            response = json.loads(r.content)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CancelOrdersAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


FetchOrdersForAccountManager = FetchOrdersForAccountManagerAPI.as_view()

FetchOrdersForWarehouseManager = FetchOrdersForWarehouseManagerAPI.as_view()

FetchShippingMethod = FetchShippingMethodAPI.as_view()

SetShippingMethod = SetShippingMethodAPI.as_view()

SetOrdersStatus = SetOrdersStatusAPI.as_view()

CancelOrders = CancelOrdersAPI.as_view()