# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render

# Create your views here.


from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

from WAMSApp.models import *
from WAMSApp.utils import *
from WAMSApp.constants import *
from dealshub.models import *
from dealshub.utils import *
from dealshub.serializers import *

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

import sys
import logging
import json
import requests
import hashlib
import threading
import math
import random

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


@api_view(['GET'])
def current_user(request):

    serializer = UserSerializer(request.user)
    return Response(serializer.data)

## NO LONGER USED
class UserList(APIView):

    permission_classes = (AllowAny,)

    def post(self, request, format=None):
        serializer = UserSerializerWithToken(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FetchShippingAddressListAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchShippingAddressListAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)
            
            user = request.user
            address_objs = Address.objects.filter(is_shipping=True, is_deleted=False, user=user)

            address_list = []
            for address_obj in address_objs:
                temp_dict = {}
                temp_dict['firstName'] = address_obj.first_name
                temp_dict['lastName'] = address_obj.last_name
                temp_dict['line1'] = json.loads(address_obj.address_lines)[0]
                temp_dict['line2'] = json.loads(address_obj.address_lines)[1]
                temp_dict['line3'] = json.loads(address_obj.address_lines)[2]
                temp_dict['line4'] = json.loads(address_obj.address_lines)[3]
                temp_dict['state'] = address_obj.state
                temp_dict['postcode'] = address_obj.postcode
                temp_dict['contactNumber'] = str(address_obj.contact_number)
                temp_dict['tag'] = str(address_obj.tag)
                temp_dict['uuid'] = str(address_obj.uuid)

                address_list.append(temp_dict)

            response['addressList'] = address_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchShippingAddressListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class EditShippingAddressAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("EditAddressAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            uuid = data["uuid"]
            first_name = data["firstName"]
            last_name = data["lastName"]
            line1 = data["line1"]
            line2 = data["line2"]
            line3 = data["line3"]
            line4 = data["line4"]
            address_lines = [line1, line2, line3, line4]
            state = data["state"]
            postcode = data["postcode"]
            contact_number = data["contactNumber"]
            tag = data.get("tag", "Home")

            address_obj = Address.objects.get(uuid=uuid)
            address_obj.first_name = first_name
            address_obj.last_name = last_name
            address_obj.address_lines = json.dumps(address_lines)
            address_obj.state = state
            address_obj.postcode = postcode
            address_obj.contact_number = contact_number
            address_obj.tag = tag
            address_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("EditAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CreateShippingAddressAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("CreateShippingAddressAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            user_obj = User.objects.get(username=request.user.username)

            first_name = data["firstName"]
            last_name = data["lastName"]
            line1 = data["line1"]
            line2 = data["line2"]
            line3 = data["line3"]
            line4 = data["line4"]
            address_lines = json.dumps([line1, line2, line3, line4])
            state = data["state"]
            postcode = data["postcode"]
            if postcode==None:
                postcode = ""
            contact_number = data["contactNumber"]
            tag = data.get("tag", "")
            if tag==None:
                tag = ""

            if user_obj.first_name=="":
                user_obj.first_name = first_name
                user_obj.last_name = last_name
                user_obj.save()

            address_obj = Address.objects.create(first_name=first_name, last_name=last_name, address_lines=address_lines, state=state, postcode=postcode, contact_number=contact_number, user=user_obj, tag=tag)

            response["uuid"] = address_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateShippingAddressAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DeleteShippingAddressAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteShippingAddressAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            uuid = data["uuid"]

            address_obj = Address.objects.get(uuid=uuid)
            address_obj.is_deleted = True
            address_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteShippingAddressAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SignUpAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("SignUpAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            email_id = data["emailId"]
            password = data["password"]
            confirm_password = data["confirmPassword"]
            first_name = data["firstName"]
            last_name = data["lastName"]
            contact_number = data["contactNumber"]

            if confirm_password==password and DealsHubUser.objects.filter(email=email_id).exists()==False:
                dealshub_user = DealsHubUser.objects.create(username=email_id, email=email_id, first_name=first_name, last_name=last_name, contact_number=contact_number)
                dealshub_user.set_password(password)
                dealshub_user.save()
                response['status'] = 200

                credentials = {
                    "username": email_id,
                    "password": password
                }
                ## DOUBT
                r = requests.post(url=DEALSHUB_IP+"/token-auth/", data=credentials, verify=False)
                token = json.loads(r.content)["token"]
                response["token"] = token
            else:
                response['status'] = 409

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SignUpAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

# ## SAME API AVAILABLE
# class FetchProductFromOCAPI(APIView):
#     """
#         API for fetching the product details from OC
#     """
#     permission_classes = [AllowAny]

#     def post(self, request, *args, **kwargs):
#         response = {}
#         response['status'] = 500
#         try:
#             data = request.data
#             logger.info("FetchProductFromOCAPI: %s", str(data))
#             if not isinstance(data, dict):
#                 data = json.loads(data)

#             uuid = data["id"]

#             logger.info("uuid: %s", str(uuid))
#             r = requests.post(OMNYCOMM_IP+"/dealshub/fetch-product-details/",
#                               data={"uuid": uuid}, verify=False)
#             logger.info("FetchProductFromOCAPI %s", str(r.text))
#             response = json.loads(r.text)

#         except Exception as e:
#             exc_type, exc_obj, exc_tb = sys.exc_info()
#             logger.error("FetchProductFromOCAPI: %s at %s",
#                          e, str(exc_tb.tb_lineno))
#         return Response(data=response)

# ### DEPRECATED
# class FetchCategoryGridBannerCardsAPI(APIView):
#     """
#         API for fetching the product details from OC
#     """
#     permission_classes = [AllowAny]

#     def post(self, request, *args, **kwargs):
#         response = {}
#         response['status'] = 500
#         try:
#             data = request.data
#             logger.info("FetchCategoryGridBannerCardsAPI: %s", str(data))
#             if not isinstance(data, dict):
#                 data = json.loads(data)

#             r = requests.post(OMNYCOMM_IP+"/dealshub/fetch-category-grid-banner-cards/",
#                               data=data, verify=False)

#             response = json.loads(r.text)

#         except Exception as e:
#             exc_type, exc_obj, exc_tb = sys.exc_info()
#             logger.error("FetchCategoryGridBannerCardsAPI: %s at %s",
#                          e, str(exc_tb.tb_lineno))
#         return Response(data=response)

# ## SAME API AVAILABLE
# class FetchAdminCategoriesAPI(APIView):

#     permission_classes = [AllowAny]

#     def post(self, request, *args, **kwargs):
#         response = {}
#         response['status'] = 500
#         try:
#             data = request.data
#             logger.info("FetchCategoriesAPI: %s", str(data))
#             if not isinstance(data, dict):
#                 data = json.loads(data)

#             r = requests.get(url=OMNYCOMM_IP+"/dealshub/fetch-admin-categories/", data=data, verify=False)

#             logger.info("Response %s", str(r.content))

#             response = json.loads(r.text)

#         except Exception as e:
#             exc_type, exc_obj, exc_tb = sys.exc_info()
#             logger.error("FetchCategoriesAPI: %s at %s",
#                          e, str(exc_tb.tb_lineno))
#         return Response(data=response)

# ### DEPRECATED
# class FetchDashboardBannerDetailsAPI(APIView):

#     permission_classes = [AllowAny]

#     def post(self, request, *args, **kwargs):
#         response = {}
#         response['status'] = 500
#         response['status_msg'] = "Fetch dashboard banner failed"
#         try:
#             data = request.data
#             logger.info("FetchDashboardBannerDetailsAPI: %s", str(data))
#             if not isinstance(data, dict):
#                 data = json.loads(data)

#             r = requests.post(OMNYCOMM_IP+"/dealshub/fetch-dashboard-banner-details/",
#                               data=data, verify=False)

#             response = json.loads(r.text)

#         except Exception as e:
#             exc_type, exc_obj, exc_tb = sys.exc_info()
#             logger.error("FetchDashboardBannerDetailsAPI: %s at %s",
#                          e, str(exc_tb.tb_lineno))
#         return Response(data=response)


# class FetchBannerDealsAPI(APIView):

#     permission_classes = [AllowAny]

#     def post(self, request, *args, **kwargs):
#         response = {}
#         response['status'] = 500
#         response['status_msg'] = "Fetch banner deals failed"
#         try:
#             data = request.data
#             logger.info("FetchBannerDealsAPI: %s", str(data))
#             if not isinstance(data, dict):
#                 data = json.loads(data)

#             r = requests.post(OMNYCOMM_IP+"/dealshub/fetch-banner-deals/",
#                               data=data, verify=False)

#             response = json.loads(r.text)

#         except Exception as e:
#             exc_type, exc_obj, exc_tb = sys.exc_info()
#             logger.error("FetchBannerDealsAPI: %s at %s",
#                          e, str(exc_tb.tb_lineno))
#         return Response(data=response)

# ### DEPRECATED
# class FetchBatchDiscountDealsAPI(APIView):

#     permission_classes = [AllowAny]

#     def post(self, request, *args, **kwargs):
#         response = {}
#         response['status'] = 500
#         try:
#             data = request.data
#             logger.info("FetchBatchDiscountDealsAPI: %s", str(data))
#             if not isinstance(data, dict):
#                 data = json.loads(data)

#             r = requests.post(OMNYCOMM_IP+"/dealshub/fetch-batch-discount-deals/",
#                               data=data, verify=False)

#             response = json.loads(r.text)

#         except Exception as e:
#             exc_type, exc_obj, exc_tb = sys.exc_info()
#             logger.error("FetchBatchDiscountDealsAPI: %s at %s",
#                          e, str(exc_tb.tb_lineno))
#         return Response(data=response)

# ### DEPRECATED
# class FetchSpecialDiscountProductAPI(APIView):

#     permission_classes = [AllowAny]

#     def post(self, request, *args, **kwargs):
#         response = {}
#         response['status'] = 500
#         try:
#             data = request.data
#             logger.info("FetchSpecialDiscountProductAPI: %s", str(data))
#             if not isinstance(data, dict):
#                 data = json.loads(data)

#             r = requests.post(OMNYCOMM_IP+"/dealshub/fetch-special-discount-product/",
#                               data=data, verify=False)

#             response = json.loads(r.text)

#         except Exception as e:
#             exc_type, exc_obj, exc_tb = sys.exc_info()
#             logger.error("FetchSpecialDiscountProductAPI: %s at %s",
#                          e, str(exc_tb.tb_lineno))
#         return Response(data=response)

# ### DEPRECATED
# class FetchFeaturedProductsAPI(APIView):

#     permission_classes = [AllowAny]

#     def post(self, request, *args, **kwargs):
#         response = {}
#         response['status'] = 500
#         try:
#             data = request.data
#             logger.info("FetchFeaturedProductsAPI: %s", str(data))
#             if not isinstance(data, dict):
#                 data = json.loads(data)

#             r = requests.post(OMNYCOMM_IP+"/dealshub/fetch-featured-products/",
#                               data=data, verify=False)

#             response = json.loads(r.text)

#         except Exception as e:
#             exc_type, exc_obj, exc_tb = sys.exc_info()
#             logger.error("FetchSchedularProductsAPI: %s at %s",
#                          e, str(exc_tb.tb_lineno))
#         return Response(data=response)

# ### DEPRECATED
# class FetchOnSaleProductsAPI(APIView):

#     permission_classes = [AllowAny]

#     def post(self, request, *args, **kwargs):
#         response = {}
#         response['status'] = 500
#         try:
#             data = request.data
#             logger.info("FetchOnSaleProductsAPI: %s", str(data))
#             if not isinstance(data, dict):
#                 data = json.loads(data)

#             r = requests.post(OMNYCOMM_IP+"/dealshub/fetch-on-sale-products/",
#                               data=data, verify=False)

#             response = json.loads(r.text)

#         except Exception as e:
#             exc_type, exc_obj, exc_tb = sys.exc_info()
#             logger.error("FetchOnSaleProductsAPI: %s at %s",
#                          e, str(exc_tb.tb_lineno))
#         return Response(data=response)

# ### DEPRECATED
# class FetchTopRatedProductsAPI(APIView):

#     permission_classes = [AllowAny]

#     def post(self, request, *args, **kwargs):
#         response = {}
#         response['status'] = 500
#         try:
#             data = request.data
#             logger.info("FetchTopRatedProductsAPI: %s", str(data))
#             if not isinstance(data, dict):
#                 data = json.loads(data)

#             r = requests.post(OMNYCOMM_IP+"/dealshub/fetch-top-rated-products/",
#                               data=data, verify=False)

#             response = json.loads(r.text)

#         except Exception as e:
#             exc_type, exc_obj, exc_tb = sys.exc_info()
#             logger.error("FetchTopRatedProductsAPI: %s at %s",
#                          e, str(exc_tb.tb_lineno))
#         return Response(data=response)

# ##SAME API AVAILABLE
# class SearchAPI(APIView):

#     permission_classes = [AllowAny]

#     def post(self, request, *args, **kwargs):
#         response = {}
#         response['status'] = 500
#         try:
#             data = request.data
#             logger.info("SearchAPI: %s", str(data))
#             if not isinstance(data, dict):
#                 data = json.loads(data)

#             # name = data.get("name", "")
#             # category = data.get("category", "")
#             # organization_name = data.get("organizationName", "")
#             # page = data.get("page", 1)
#             r = requests.post(OMNYCOMM_IP+"/dealshub/search/", data=data, verify=False)

#             response = json.loads(r.text)
            
#             response['status'] = 200

#         except Exception as e:
#             exc_type, exc_obj, exc_tb = sys.exc_info()
#             logger.error("SearchAPI: %s at %s",
#                          e, str(exc_tb.tb_lineno))
#         return Response(data=response)

# ## SAME API AVAILABLE
# class FetchSectionsProductsAPI(APIView):
#     """
#         API for fetching the product details from OC
#     """
#     permission_classes = [AllowAny]

#     def post(self, request, *args, **kwargs):
#         response = {}
#         response['status'] = 500
#         try:
#             data = request.data
#             logger.info("FetchSectionsProductsAPI: %s", str(data))
#             if not isinstance(data, dict):
#                 data = json.loads(data)

#             r = requests.get(OMNYCOMM_IP+"/dealshub/fetch-sections-products/",
#                               data=data, verify=False)

#             response = json.loads(r.text)

#         except Exception as e:
#             exc_type, exc_obj, exc_tb = sys.exc_info()
#             logger.error("FetchSectionsProductsAPI: %s at %s",
#                          e, str(exc_tb.tb_lineno))
#         return Response(data=response)

# ## SAME API AVILABLE
# class FetchCategoriesAPI(APIView):

#     permission_classes = [AllowAny]

#     def post(self, request, *args, **kwargs):
#         response = {}
#         response['status'] = 500
#         try:
#             data = request.data
#             logger.info("FetchCategoriesAPI: %s", str(data))
#             if not isinstance(data, dict):
#                 data = json.loads(data)

#             r = requests.post(OMNYCOMM_IP+"/dealshub/fetch-categories/",
#                               data=data, verify=False)

#             response = json.loads(r.text)

#         except Exception as e:
#             exc_type, exc_obj, exc_tb = sys.exc_info()
#             logger.error("FetchCategoriesAPI: %s at %s",
#                          e, str(exc_tb.tb_lineno))
#         return Response(data=response)

# ## DEPRECATED
# class FetchSchedularProductsAPI(APIView):

#     permission_classes = [AllowAny]

#     def post(self, request, *args, **kwargs):
#         response = {}
#         response['status'] = 500
#         try:
#             data = request.data
#             logger.info("FetchSchedularProductsAPI: %s", str(data))
#             if not isinstance(data, dict):
#                 data = json.loads(data)

#             r = requests.post(OMNYCOMM_IP+"/dealshub/fetch-schedular-products/",
#                               data=data, verify=False)

#             response = json.loads(r.text)

#         except Exception as e:
#             exc_type, exc_obj, exc_tb = sys.exc_info()
#             logger.error("FetchSchedularProductsAPI: %s at %s",
#                          e, str(exc_tb.tb_lineno))
#         return Response(data=response)

# ## DEPRECATED
# class FetchBrandsCarouselAPI(APIView):

#     permission_classes = [AllowAny]

#     def post(self, request, *args, **kwargs):
#         response = {}
#         response['status'] = 500
#         try:
#             data = request.data
#             logger.info("FetchBannerDealsAPI: %s", str(data))
#             if not isinstance(data, dict):
#                 data = json.loads(data)

#             r = requests.post(OMNYCOMM_IP+"/dealshub/fetch-brands-carousel/",
#                               data=data, verify=False)

#             response = json.loads(r.text)

#         except Exception as e:
#             exc_type, exc_obj, exc_tb = sys.exc_info()
#             logger.error("FetchBrandsCarouselAPI: %s at %s",
#                          e, str(exc_tb.tb_lineno))
#         return Response(data=response)


class FetchUserRatingsAPI(APIView):

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchUserRatingsAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            response = {
                "status": 200,
                "total": "278",
                "final": "4.5",
                "overall": [
                  {
                    "id": "1",
                    "rating": "23"
                  },
                  {
                    "id": "2",
                    "rating": "56"
                  },
                  {
                    "id": "3",
                    "rating": "83"
                  },
                  {
                    "id": "4",
                    "rating": "49"
                  },
                  {
                    "id": "5",
                    "rating": "67"
                  }
                ]
            }

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchUserRatingsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchUserReviewsAPI(APIView):

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchUserReviewsAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            response = {
                "status": 200,
                "reviews": [
                    {
                        "id": "1",
                        "name": "John Doe",
                        "review": "Fusce vitae nibh mi. Integer posuere, libero et ullamcorper facilisis, enim eros tincidunt orci, eget vestibulum sapien nisi ut leo. Cras finibus vel est ut mollis. Donec luctus condimentum ante et euismod.",
                        "date": "June 18, 2019",
                        "rating": "3"
                    },
                    {
                        "id": "2",
                        "name": "Anna Kowalsky",
                        "review": "Fusce vitae nibh mi. Integer posuere, libero et ullamcorper facilisis, enim eros tincidunt orci, eget vestibulum sapien nisi ut leo. Cras finibus vel est ut mollis. Donec luctus condimentum ante et euismod.",
                        "date": "August 3, 2018",
                        "rating": "2"
                    },
                    {
                        "id": "3",
                        "name": "Peter Wargner",
                        "review": "Fusce vitae nibh mi. Integer posuere, libero et ullamcorper facilisis, enim eros tincidunt orci, eget vestibulum sapien nisi ut leo. Cras finibus vel est ut mollis. Donec luctus condimentum ante et euismod.",
                        "date": "July 3, 2018",
                        "rating": "5"
                    }]
            }

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchUserReviewsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class AddToCartAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddToCartAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            product_uuid = data["productUuid"]
            quantity = int(data["quantity"])
            price = float(data["price"])

            dealshub_user = DealsHubUser.objects.get(username=request.user.username)
            cart_obj, created = Cart.objects.get_or_create(owner=dealshub_user)
            unit_cart_obj = None
            if UnitCart.objects.filter(cart=cart_obj, product_code=product_uuid, cart_type="active").exists()==True:
                unit_cart_obj = UnitCart.objects.get(cart=cart_obj, product_code=product_uuid, cart_type="active")
                unit_cart_obj.quantity += quantity
                unit_cart_obj.save()
            else:
                unit_cart_obj = UnitCart.objects.create(cart=cart_obj, product_code=product_uuid, cart_type="active", quantity=quantity, price=price)

            update_cart_bill(cart_obj)

            response["unitCartUuid"] = unit_cart_obj.uuid
            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddToCartAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchCartDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchCartDetailsAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            dealshub_user = DealsHubUser.objects.get(username=request.user.username)
            cart_obj, created = Cart.objects.get_or_create(owner=dealshub_user)
            unit_cart_objs = UnitCart.objects.filter(cart=cart_obj, cart_type="active")
            unit_cart_list = []
            total_amount = 0
            for unit_cart_obj in unit_cart_objs:
                temp_dict = {}
                temp_dict["uuid"] = unit_cart_obj.uuid
                temp_dict["quantity"] = unit_cart_obj.quantity
                temp_dict["price"] = unit_cart_obj.price
                temp_dict["currency"] = unit_cart_obj.currency
                temp_dict["dateCreated"] = str(timezone.localtime(unit_cart_obj.date_created).strftime("%d %b, %Y"))
                product_obj = unit_cart_obj.product.product
                temp_dict["productName"] = product_obj.product_name
                try:
                    lifestyle_image_obj = product_obj.lifestyle_images.all()[0]
                    temp_dict["productImageUrl"] = lifestyle_image_obj.thumbnail.url
                except Exception as e:
                    temp_dict["productImageUrl"] = ""
                temp_dict["productUuid"] = unit_cart_obj.product_code
                temp_dict["isStockAvailable"] = unit_cart_obj.product.stock > 0
                total_amount += float(unit_cart_obj.price)*float(unit_cart_obj.quantity)

                unit_cart_list.append(temp_dict)

            delivery_fee = 0
            if total_amount<100 and total_amount>0:
                delivery_fee = 15

            total_amount += delivery_fee
            total_amount = round(total_amount, 2)

            vat = round((total_amount - total_amount/1.05), 2)

            response["deliveryFee"] = delivery_fee
            response["vat"] = vat
            response["toPay"] = total_amount
            response["unitCartList"] = unit_cart_list
            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCartDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UpdateCartDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateCartDetailsAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            unit_cart_uuid = data["unitCartUuid"]
            quantity = int(data["quantity"])

            dealshub_user = DealsHubUser.objects.get(username=request.user.username)
            cart_obj, created = Cart.objects.get_or_create(owner=dealshub_user)
            unit_cart_obj = UnitCart.objects.get(cart=cart_obj, uuid=unit_cart_uuid)
            unit_cart_obj.quantity = quantity
            unit_cart_obj.save()

            update_cart_bill(cart_obj)

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateCartDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class RemoveFromCartAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("RemoveFromCartAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            unit_cart_uuid = data["unitCartUuid"]
            
            dealshub_user = DealsHubUser.objects.get(username=request.user.username)
            cart_obj = Cart.objects.get(owner=dealshub_user)
            UnitCart.objects.get(cart=cart_obj, uuid=unit_cart_uuid).delete()

            update_cart_bill(cart_obj)

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("RemoveFromCartAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)



class AddToWishlistAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddToWishlistAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            product_uuid = data["productUuid"]
            quantity = 0
            price = None

            dealshub_user = DealsHubUser.objects.get(username=request.user.username)
            cart_obj, created = Cart.objects.get_or_create(owner=dealshub_user)
            if UnitCart.objects.filter(cart=cart_obj, product_code=product_uuid, cart_type="wishlist").exists()==False:
                unit_cart_obj = UnitCart.objects.create(cart=cart_obj, product_code=product_uuid, cart_type="wishlist", quantity=quantity, price=price)

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddToWishlistAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchWishlistDetailsAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchWishlistDetailsAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            dealshub_user = DealsHubUser.objects.get(username=request.user.username)
            cart_obj, created = Cart.objects.get_or_create(owner=dealshub_user)
            unit_cart_objs = UnitCart.objects.filter(cart=cart_obj, cart_type="wishlist")
            unit_cart_list = []
            for unit_cart_obj in unit_cart_objs:
                temp_dict = {}
                temp_dict["uuid"] = unit_cart_obj.uuid
                temp_dict["dateCreated"] = str(timezone.localtime(unit_cart_obj.date_created).strftime("%d %b, %Y"))
                product_obj = unit_cart_obj.product.product
                temp_dict["productName"] = product_obj.product_name
                try:
                    lifestyle_image_obj = product_obj.lifestyle_images.all()[0]
                    temp_dict["productImageUrl"] = lifestyle_image_obj.thumbnail.url
                except Exception as e:
                    temp_dict["productImageUrl"] = ""

                temp_dict["productUuid"] = unit_cart_obj.product_code
                unit_cart_list.append(temp_dict)

            response["unitCartList"] = unit_cart_list
            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchWishlistDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class RemoveFromWishlistAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("RemoveFromWishlistAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            unit_cart_uuid = data["unitCartUuid"]
            
            dealshub_user = DealsHubUser.objects.get(username=request.user.username)
            cart_obj = Cart.objects.get(owner=dealshub_user)
            UnitCart.objects.get(cart=cart_obj, uuid=unit_cart_uuid).delete()

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("RemoveFromWishlistAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)



class SelectAddressAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SelectAddressAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            address_uuid = data["addressUuid"]
            order_uuid = data["orderUuid"]

            address_obj = Address.objects.get(uuid=address_uuid)
            order_obj = Order.objects.get(uuid=order_uuid)
            order_obj.shipping_address = address_obj
            order_obj.save()

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SelectAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class SelectPaymentModeAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SelectPaymentModeAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            payment_mode = data["paymentMode"]
            order_uuid = data["orderUuid"]

            order_obj = Order.objects.get(uuid=order_uuid)
            order_obj.payment_mode = payment_mode
            order_obj.save()

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SelectPaymentModeAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchActiveOrderDetailsAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchActiveOrderDetailsAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            dealshub_user = DealsHubUser.objects.get(username=request.user.username)
            cart_obj = Cart.objects.get(owner=dealshub_user)

            order_obj = cart_obj.order
            if order_obj == None:
                order_obj = Order.objects.create(owner=dealshub_user)
                cart_obj.order = order_obj
                cart_obj.save()
            
            if order_obj.shipping_address==None and Address.objects.filter(is_deleted=False, user=request.user).count()>0:
                order_obj.shipping_address = Address.objects.filter(is_deleted=False, user=request.user)[0]
                order_obj.save()


            address_obj = order_obj.shipping_address
            payment_mode = order_obj.payment_mode
            voucher_obj = order_obj.voucher
            is_voucher_applied = voucher_obj is not None

            response["uuid"] = order_obj.uuid
            response["dateCreated"] = str(timezone.localtime(order_obj.date_created).strftime("%d %b, %Y"))
            response["paymentMode"] = str(payment_mode)
            response["isVoucherApplied"] = is_voucher_applied
            if is_voucher_applied:
                response["voucherCode"] = voucher_obj.voucher_code

            if address_obj==None:
                response["shippingAddress"] = {}
            else:
                response["shippingAddress"] = {
                    "firstName": address_obj.first_name,
                    "lastName": address_obj.last_name,
                    "line1": json.loads(address_obj.address_lines)[0],
                    "line2": json.loads(address_obj.address_lines)[1],
                    "line3": json.loads(address_obj.address_lines)[2],
                    "line4": json.loads(address_obj.address_lines)[3],
                    "state": address_obj.state,
                    "postcode": address_obj.postcode,
                    "contactNumber": str(address_obj.contact_number),
                    "tag": str(address_obj.tag),
                    "uuid": str(address_obj.uuid)
                }

            unit_cart_list = []
            unit_cart_objs = UnitCart.objects.filter(cart_type="active", cart__owner=dealshub_user)

            total_amount = 0
            is_cod_allowed = True
            for unit_cart_obj in unit_cart_objs:
                temp_dict = {}
                temp_dict["uuid"] = unit_cart_obj.uuid
                temp_dict["quantity"] = unit_cart_obj.quantity
                temp_dict["price"] = unit_cart_obj.price
                temp_dict["currency"] = unit_cart_obj.currency
                temp_dict["dateCreated"] = str(timezone.localtime(unit_cart_obj.date_created).strftime("%d %b, %Y"))
                product_obj = unit_cart_obj.product.product
                temp_dict["productName"] = product_obj.product_name
                try:
                    lifestyle_image_obj = product_obj.lifestyle_images.all()[0]
                    temp_dict["productImageUrl"] = lifestyle_image_obj.thumbnail.url
                except Exception as e:
                    temp_dict["productImageUrl"] = ""
                total_amount += float(unit_cart_obj.price)*float(unit_cart_obj.quantity)
                is_cod_allowed = unit_cart_obj.product.is_cod_allowed
                unit_cart_list.append(temp_dict)

            delivery_fee = 0
            if total_amount<100 and total_amount>0:
                delivery_fee = 15

            total_amount += delivery_fee
            total_amount = round(total_amount, 2)

            vat = round((total_amount - total_amount/1.05), 2)

            response["deliveryFee"] = delivery_fee
            response["vat"] = vat
            response["toPay"] = total_amount

            response["unitCartList"] = unit_cart_list

            response["contactVerified"] = dealshub_user.contact_verified
            response["contactNumber"] = dealshub_user.contact_number
            response["emailId"] = dealshub_user.email

            response["isCodAllowed"] = is_cod_allowed

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchActiveOrderDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class PlaceOrderAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("PlaceOrderAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            dealshub_user = DealsHubUser.objects.get(username=request.user.username)
            cart_obj = Cart.objects.get(owner=dealshub_user)

            unit_cart_objs = UnitCart.objects.filter(cart_type="active", cart__owner=dealshub_user)

            # Check if COD is allowed
            for unit_cart_obj in unit_cart_objs:
                is_cod_allowed = unit_cart_obj.product.is_cod_allowed
                if is_cod_allowed==False:
                    response["status"] = 403
                    logger.error("PlaceOrderAPI: COD not allowed!")
                    return Response(data=response)


            order_obj = cart_obj.order
            order_obj.to_pay += 5 # Extra for COD

            # Unit Cart gets converted to Unit Order
            for unit_cart_obj in unit_cart_objs:
                unit_order_obj = UnitOrder.objects.create(order=order_obj, 
                                                          product_code=unit_cart_obj.product_code,
                                                          quantity=unit_cart_obj.quantity, 
                                                          price=unit_cart_obj.price, 
                                                          currency=unit_cart_obj.currency)
                UnitOrderStatus.objects.create(unit_order=unit_order_obj)

            # Cart gets empty
            for unit_cart_obj in unit_cart_objs:
                unit_cart_obj.delete()

            # cart_obj points to None
            cart_obj.order = None
            cart_obj.save()
            order_obj.order_type = "placedorder"
            order_obj.order_placed_date = timezone.now()
            order_obj.save()

            # Trigger Email
            try:
                p1 = threading.Thread(target=send_order_confirmation_mail, args=(order_obj,))
                p1.start()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("PlaceOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))

            # Refresh Stock
            refresh_stock(order_obj)

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PlaceOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)



class CancelOrderAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("CancelOrderAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CancelOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchOrderListAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchOrderListAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            dealshub_user = DealsHubUser.objects.get(username=request.user.username)

            unit_order_objs = UnitOrder.objects.filter(order__owner=dealshub_user, order__order_type="placedorder").order_by('-pk')
            unit_order_list = []            

            uuid_list = []
            for unit_order_obj in unit_order_objs:
                uuid_list.append(unit_order_obj.product_code)

            productInfo = fetch_bulk_product_info(json.dumps(uuid_list))

            order_list = []
            order_objs = Order.objects.filter(owner=dealshub_user, order_type="placedorder").order_by('-pk')
            for order_obj in order_objs:
                voucher_obj = order_obj.voucher
                is_voucher_applied = voucher_obj is not None
                temp_dict = {}
                temp_dict["dateCreated"] = str(timezone.localtime(order_obj.date_created).strftime("%d %b, %Y"))
                temp_dict["paymentMode"] = order_obj.payment_mode
                temp_dict["paymentStatus"] = order_obj.payment_status
                temp_dict["customerName"] = order_obj.owner.first_name+" "+order_obj.owner.last_name
                temp_dict["bundleId"] = order_obj.bundleid
                temp_dict["uuid"] = order_obj.uuid
                temp_dict["isVoucherApplied"] = is_voucher_applied
                if is_voucher_applied:
                    temp_dict["voucherCode"] = voucher_obj.voucher_code

                address_obj = order_obj.shipping_address

                shipping_address = address_obj.first_name + " " + address_obj.last_name + "\n" + json.loads(address_obj.address_lines)[0] + "\n"+json.loads(address_obj.address_lines)[1] + "\n"+json.loads(address_obj.address_lines)[2] + "\n"+json.loads(address_obj.address_lines)[3] + "\n"+address_obj.state
                temp_dict["shippingAddress"] = shipping_address

                unit_order_objs = UnitOrder.objects.filter(order=order_obj)
                unit_order_list = []
                for unit_order_obj in unit_order_objs:
                    temp_dict2 = {}
                    temp_dict2["orderId"] = unit_order_obj.orderid
                    temp_dict2["uuid"] = unit_order_obj.uuid
                    temp_dict2["currentStatus"] = unit_order_obj.current_status
                    temp_dict2["quantity"] = unit_order_obj.quantity
                    temp_dict2["price"] = unit_order_obj.price
                    temp_dict2["currency"] = unit_order_obj.currency           
                    temp_dict2["productName"] = productInfo[unit_order_obj.product_code]["productName"]
                    temp_dict2["productImageUrl"] = productInfo[unit_order_obj.product_code]["productImageUrl"]
                    unit_order_list.append(temp_dict2)
                temp_dict["unitOrderList"] = unit_order_list
                order_list.append(temp_dict)

            response["orderList"] = order_list
            if len(order_list)==0:
                response["isOrderListEmpty"] = True
            else:
                response["isOrderListEmpty"] = False

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOrderListAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)



class FetchOrderListAdminAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchOrderListAdminAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            page = data.get("page", 1)

            unit_order_objs = UnitOrder.objects.filter(order__order_type="placedorder").order_by('-pk')
            response["total_orders"] = unit_order_objs.count()
            paginator = Paginator(unit_order_objs, 20)
            unit_order_objs = paginator.page(page)

            uuid_list = []
            for unit_order_obj in unit_order_objs:
                uuid_list.append(unit_order_obj.product_code)

            productInfo = fetch_bulk_product_info(json.dumps(uuid_list))

            order_list = []
            order_objs = Order.objects.filter(order_type="placedorder").order_by('-pk')
            for order_obj in order_objs:
                try:
                    voucher_obj = order_obj.voucher
                    is_voucher_applied = voucher_obj is not None
                    temp_dict = {}
                    temp_dict["dateCreated"] = str(timezone.localtime(order_obj.date_created).strftime("%d %b, %Y"))
                    temp_dict["paymentMode"] = order_obj.payment_mode
                    temp_dict["paymentStatus"] = order_obj.payment_status
                    temp_dict["customerName"] = order_obj.owner.first_name+" "+order_obj.owner.last_name
                    temp_dict["bundleId"] = order_obj.bundleid
                    temp_dict["uuid"] = order_obj.uuid
                    temp_dict["isVoucherApplied"] = is_voucher_applied
                    if is_voucher_applied:
                        temp_dict["voucherCode"] = voucher_obj.voucher_code
                    unit_order_objs = UnitOrder.objects.filter(order=order_obj)
                    unit_order_list = []
                    for unit_order_obj in unit_order_objs:
                        temp_dict2 = {}
                        temp_dict2["orderId"] = unit_order_obj.orderid
                        temp_dict2["uuid"] = unit_order_obj.uuid
                        temp_dict2["currentStatus"] = unit_order_obj.current_status
                        temp_dict2["quantity"] = unit_order_obj.quantity
                        temp_dict2["price"] = unit_order_obj.price
                        temp_dict2["currency"] = unit_order_obj.currency
                        temp_dict2["productName"] = productInfo[unit_order_obj.product_code]["productName"]
                        temp_dict2["productImageUrl"] = productInfo[unit_order_obj.product_code]["productImageUrl"]
                        unit_order_list.append(temp_dict2)
                    temp_dict["unit_order_list"] = unit_order_list
                    order_list.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchOrderListAdminAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["orderList"] = order_list

            is_available = True
            
            if int(paginator.num_pages) == int(page):
                is_available = False

            response["is_available"] = is_available

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOrderListAdminAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)



class FetchOrderDetailsAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchOrderDetailsAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            order_uuid = data["uuid"]

            order_obj = Order.objects.get(uuid=order_uuid)
            voucher_obj = order_obj.voucher
            is_voucher_applied = voucher_obj is not None

            unit_order_objs = UnitOrder.objects.filter(order=order_obj)

            response["bundleId"] = order_obj.bundleid 
            response["dateCreated"] = str(timezone.localtime(order_obj.date_created).strftime("%d %b, %Y"))
            response["paymentMode"] = order_obj.payment_mode
            response["paymentStatus"] = order_obj.payment_status
            response["customerName"] = order_obj.owner.first_name + " " + order_obj.owner.last_name
            response["isVoucherApplied"] = is_voucher_applied
            if is_voucher_applied:
                response["voucherCode"] = voucher_obj.voucher_code

            address_obj = order_obj.shipping_address
            if address_obj==None:
                response["shippingAddress"] = {}
            else:
                response["shippingAddress"] = {
                    "firstName": address_obj.first_name,
                    "lastName": address_obj.last_name,
                    "line1": json.loads(address_obj.address_lines)[0],
                    "line2": json.loads(address_obj.address_lines)[1],
                    "line3": json.loads(address_obj.address_lines)[2],
                    "line4": json.loads(address_obj.address_lines)[3],
                    "state": address_obj.state,
                    "postcode": address_obj.postcode,
                    "contactNumber": str(address_obj.contact_number),
                    "tag": str(address_obj.tag),
                    "uuid": str(address_obj.uuid)
                }

            uuid_list = []
            for unit_order_obj in unit_order_objs:
                uuid_list.append(unit_order_obj.product_code)

            productInfo = fetch_bulk_product_info(json.dumps(uuid_list))


            subtotal = 0
            unit_order_list = []
            for unit_order_obj in unit_order_objs:
            
                temp_dict = {}
                temp_dict["orderId"] = unit_order_obj.orderid
                temp_dict["uuid"] = unit_order_obj.uuid
                temp_dict["currentStatus"] = unit_order_obj.current_status
                temp_dict["quantity"] = unit_order_obj.quantity
                temp_dict["price"] = unit_order_obj.price
                temp_dict["currency"] = unit_order_obj.currency
                
                temp_dict["productName"] = productInfo[unit_order_obj.product_code]["productName"]
                temp_dict["productImageUrl"] = productInfo[unit_order_obj.product_code]["productImageUrl"]
                temp_dict["sellerSku"] = productInfo[unit_order_obj.product_code]["sellerSku"]
                temp_dict["productId"] = productInfo[unit_order_obj.product_code]["productId"]

                unit_order_status_list = []
                unit_order_status_objs = UnitOrderStatus.objects.filter(unit_order=unit_order_obj).order_by('date_created')
                for unit_order_status_obj in unit_order_status_objs:
                    temp_dict2 = {}
                    temp_dict2["customerStatus"] = unit_order_status_obj.status
                    temp_dict2["adminStatus"] = unit_order_status_obj.status_admin
                    temp_dict2["date"] = str(timezone.localtime(unit_order_status_obj.date_created).strftime("%d %b, %Y"))
                    temp_dict2["time"] = str(timezone.localtime(unit_order_status_obj.date_created).strftime("%I:%M %p"))
                    temp_dict2["uuid"] = unit_order_status_obj.uuid
                    unit_order_status_list.append(temp_dict2)
                
                temp_dict["UnitOrderStatusList"] = unit_order_status_list

                subtotal += float(unit_order_obj.price)*float(unit_order_obj.quantity)
                unit_order_list.append(temp_dict)

            subtotal = round(subtotal, 2)
            delivery_fee = 0
            if subtotal<100 and subtotal>0:
                delivery_fee = 15

            cod_fee = 0
            if order_obj.payment_mode=="COD":
                cod_fee = 5
            
            to_pay = subtotal + delivery_fee + cod_fee

            vat = round((to_pay - to_pay/1.05), 2)

            response["subtotal"] = str(subtotal)
            response["deliveryFee"] = str(delivery_fee)
            response["codFee"] = str(cod_fee)
            response["vat"] = str(vat)
            response["toPay"] = str(to_pay)

            response["unitOrderList"] = unit_order_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOrderDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchUserProfileAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchUserProfileAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            dealshub_user = DealsHubUser.objects.get(username=request.user.username)

            response["firstName"] = dealshub_user.first_name
            response["lastName"] = dealshub_user.last_name
            response["emailId"] = dealshub_user.email
            response["contactNumber"] = dealshub_user.contact_number

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchUserProfileAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UpdateUserProfileAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UpdateUserProfileAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)
            
            email_id = data["emailId"]
            first_name = data["firstName"]
            last_name = data["lastName"]
            contact_number = data["contactNumber"]

            dealshub_user = DealsHubUser.objects.get(email=email_id)
            dealshub_user.first_name = first_name
            dealshub_user.last_name = last_name
            dealshub_user.contact_number = contact_number
            dealshub_user.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateUserProfileAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchCustomerListAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchCustomerListAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            search_list = data.get("search_list", [])

            dealshub_user_objs = DealsHubUser.objects.none()
            if len(search_list)>0:
                for search_key in search_list:
                    dealshub_user_objs |= DealsHubUser.objects.filter(Q(first_name__icontains=search_key) | Q(last_name__icontains=search_key))
                dealshub_user_objs = dealshub_user_objs.distinct().order_by('-pk')
            else:
                dealshub_user_objs = DealsHubUser.objects.all().order_by('-pk')

            filter_parameters = data.get("filter_parameters", {})

            if "is_feedback_available" in filter_parameters:
                if filter_parameters["is_feedback_available"]==True:
                    pass

            if "is_cart_empty" in filter_parameters:
                if filter_parameters["is_cart_empty"]==True:
                    cart_objs = UnitCart.objects.all().values("cart")
                    dealshub_user_objs = dealshub_user_objs.filter(cart=None) | dealshub_user_objs.exclude(cart__in=cart_objs)
                    dealshub_user_objs.distinct()
                elif filter_parameters["is_cart_empty"]==False:
                    cart_objs = UnitCart.objects.all().values("cart")
                    dealshub_user_objs = dealshub_user_objs.filter(cart__in=cart_objs)

            page = data.get("page", 1)
            response["total_customers"] = dealshub_user_objs.count()
            paginator = Paginator(dealshub_user_objs, 20)
            dealshub_user_objs = paginator.page(page)

            customer_list = []
            for dealshub_user_obj in dealshub_user_objs:
                try:
                    temp_dict = {}
                    temp_dict["name"] = dealshub_user_obj.first_name + " " + dealshub_user_obj.last_name
                    temp_dict["emailId"] = dealshub_user_obj.email
                    temp_dict["contactNumber"] = dealshub_user_obj.contact_number
                    temp_dict["username"] = dealshub_user_obj.username
                    temp_dict["is_cart_empty"] = not UnitCart.objects.filter(cart__owner=dealshub_user_obj).exists()
                    temp_dict["is_feedback_available"] = False
                    customer_list.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchCustomerListAPI: %s at %s", e, str(exc_tb.tb_lineno))

            is_available = True

            if int(paginator.num_pages) == int(page):
                is_available = False

            response["is_available"] = is_available

            response["customerList"] = customer_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCustomerListAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


FetchShippingAddressList = FetchShippingAddressListAPI.as_view()

EditShippingAddress = EditShippingAddressAPI.as_view()

CreateShippingAddress = CreateShippingAddressAPI.as_view()

DeleteShippingAddress = DeleteShippingAddressAPI.as_view()

SignUp = SignUpAPI.as_view()

# FetchProductFromOC = FetchProductFromOCAPI.as_view()

# FetchSectionsProducts = FetchSectionsProductsAPI.as_view()

# FetchCategoryGridBannerCards = FetchCategoryGridBannerCardsAPI.as_view()

# FetchCategories = FetchCategoriesAPI.as_view()

# FetchDashboardBannerDetails = FetchDashboardBannerDetailsAPI.as_view()

# FetchBannerDeals = FetchBannerDealsAPI.as_view()

# FetchBatchDiscountDeals = FetchBatchDiscountDealsAPI.as_view()

# FetchSpecialDiscountProduct = FetchSpecialDiscountProductAPI.as_view()

# FetchSchedularProducts = FetchSchedularProductsAPI.as_view()

# FetchFeaturedProducts = FetchFeaturedProductsAPI.as_view()

# FetchOnSaleProducts = FetchOnSaleProductsAPI.as_view()

# FetchTopRatedProducts = FetchTopRatedProductsAPI.as_view()

# Search = SearchAPI.as_view()

# FetchAdminCategories = FetchAdminCategoriesAPI.as_view()

# FetchBrandsCarousel = FetchBrandsCarouselAPI.as_view()

FetchUserRatings = FetchUserRatingsAPI.as_view()

FetchUserReviews = FetchUserReviewsAPI.as_view()

AddToCart = AddToCartAPI.as_view()

FetchCartDetails = FetchCartDetailsAPI.as_view()

UpdateCartDetails = UpdateCartDetailsAPI.as_view()

RemoveFromCart = RemoveFromCartAPI.as_view()

AddToWishlist = AddToWishlistAPI.as_view()

FetchWishlistDetails = FetchWishlistDetailsAPI.as_view()

RemoveFromWishlist = RemoveFromWishlistAPI.as_view()

SelectAddress = SelectAddressAPI.as_view()

SelectPaymentMode = SelectPaymentModeAPI.as_view()

FetchActiveOrderDetails = FetchActiveOrderDetailsAPI.as_view()

PlaceOrder = PlaceOrderAPI.as_view()

CancelOrder = CancelOrderAPI.as_view()

FetchOrderList = FetchOrderListAPI.as_view()

FetchOrderListAdmin = FetchOrderListAdminAPI.as_view()

FetchOrderDetails = FetchOrderDetailsAPI.as_view()

FetchUserProfile = FetchUserProfileAPI.as_view()

UpdateUserProfile = UpdateUserProfileAPI.as_view()

FetchCustomerList = FetchCustomerListAPI.as_view()