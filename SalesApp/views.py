# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

from WAMSApp.models import *
from WAMSApp.constants import *
from SalesApp.models import *
from SalesApp.utils import *

from django.shortcuts import HttpResponse, get_object_or_404
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models import Count
from django.utils import timezone

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import AllowAny

import xmltodict
import requests
import random
import json
import os
import xlrd
import datetime
import uuid
import pandas as pd

logger = logging.getLogger(__name__)

ORGANIZATION = Organization.objects.get(name="WIG")

class CsrfExemptSessionAuthentication(SessionAuthentication):

    def enforce_csrf(self, request):
        return

class SalesAppLoginSubmitAPI(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("SalesAppLoginSubmitAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            email = data.get("email", "").strip()
            password = data.get("password", "").strip()
            fcm_id = data.get("fcm_id", "").strip()

            if email == "":
                response['message'] = "Email ID can't be empty"
                logger.warning("SalesAppLoginSubmitAPI : Email ID is Empty")
                return Response(data=response)

            if password == "":
                response['message'] = "Password can't be empty"
                logger.warning("SalesAppLoginSubmitAPI : Password is Empty")
                return Response(data=response)
            
            credentials = {
                "username": email,
                "password": password
            }
            
            r = requests.post(url=SERVER_IP+"/token-auth/", data=credentials, verify=False)
            response["token"] = ""

            if "token" in json.loads(r.content):
                
                token = json.loads(r.content)["token"]
                response["token"] = token

                response['status'] = 200
                response['message'] = "Successfully Logged In"

            else:
                response['status'] = 403
                response['message'] = "Incorrect Password or Email ID"
                logger.warning("SalesAppLoginSubmitAPI : Incorrect Password or Email ID")
            
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SalesAppLoginSubmitAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class SalesAppSignUpSubmitAPI(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("SalesAppSignUpSubmitAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            first_name = data.get("first_name", "").strip()
            last_name = data.get("last_name", "").strip()
            email = data.get("email", "").strip()
            contact_number = data.get("contact_number", "").strip()
            password = data.get("password", "").strip()
            country = data.get("country", "").strip()

            if email == "":
                response['message'] = "Email ID can't be empty"
                logger.warning("SalesAppSignUpSubmitAPI : Email ID is Empty")
                return Response(data=response)

            if password == "":
                response['message'] = "Password can't be empty"
                logger.warning("SalesAppSignUpSubmitAPI : Password is Empty")
                return Response(data=response)
            
            if SalesAppUser.objects.filter(username=email).exists():
                response['status'] = 403
                response['message'] = "Email ID alreay in use"
                logger.warning("SalesAppSignUpSubmitAPI : Email ID alreay in use")
                return Response(data=response)

            sales_user = SalesAppUser.objects.create(username=email,password=password)

            if first_name != "":
                sales_user.first_name = first_name
            
            if last_name != "":
                sales_user.last_name = last_name
            
            sales_user.email = email
            
            if contact_number != "":
                sales_user.contact_number = contact_number
            
            if country != "":
                sales_user.country = country

            sales_user.save()

            response['status'] = 200
            response['message'] = "Successfully Signed Up"
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SalesAppSignUpSubmitAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class SearchProductByBrandAPI(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("SearchProductByBrandAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            brand_name = data.get("brand_name", "")
            search_text = data.get("search_text", "")
            page = int(data.get('page', 1))

            product_objs = Product.objects.filter(base_product__brand__organization=ORGANIZATION)

            if search_text != "":
                product_objs = product_objs.filter(
                        Q(base_product__base_product_name__icontains=search_text) |
                        Q(product_name__icontains=search_text) |
                        Q(product_id__icontains=search_text) |
                        Q(base_product__seller_sku__icontains=search_text)
                    )

            if brand_name!="":
                brand_obj = Brand.objects.get(name=brand_name,organization=ORGANIZATION)
                product_objs = product_objs.filter(base_product__brand=brand_obj) 

            paginator = Paginator(product_objs, 20)
            total_pages = paginator.num_pages

            if page > total_pages:
                response['status'] = 404
                response['message'] = "Page number out of range"
                logger.warning("SearchProductByBrandAPI : Page number out of range")
                return Response(data=response)

            page_product_objs = paginator.page(page)

            product_list = []
            
            for product_obj in page_product_objs:
                
                try:
                    
                    temp_dict = {}
                    temp_dict["product_name"] = product_obj.product_name
                    temp_dict["image_url"] = product_obj.get_display_image_url()
                    temp_dict["product_description"] = product_obj.product_description
                    temp_dict["seller_sku"] = product_obj.base_product.seller_sku
                    temp_dict["product_id"] = "" if product_obj.product_id==None else str(product_obj.product_id)
                    
                    product_list.append(temp_dict)
                
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("SearchProductByBrandAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["product_list"] = product_list
            response["total_pages"] = total_pages
            response['status'] = 200
            response['message'] = "Successful"
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchProductByBrandAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class ProductChangeInFavouritesAPI(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("ProductChangeInFavouritesAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            seller_sku = data.get("seller_sku","")
            operation = data.get("operation","")
            
            try :
                sales_user_obj = SalesAppUser.objects.get(username=request.user.username)
            except Exception as e :
                response['status'] = 403
                response['message'] = "User not Logged In"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("ProductChangeInFavouritesAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            if seller_sku == "":
                response['message'] = "Seller SKU not found"
                return Response(data=response)

            if operation == "":
                response['message'] = "Operation Type not specified"
                return Response(data=response)

            if operation != "ADD" and operation != "REMOVE":
                response['message'] = "Operation Type not valid"
                return Response(data=response)
            
            if Product.objects.filter(base_product__brand__organization=ORGANIZATION,base_product__seller_sku=seller_sku).exists():

                product_obj = Product.objects.get(base_product__brand__organization=ORGANIZATION,base_product__seller_sku=seller_sku)

                if operation == "ADD":
                    sales_user_obj.favourite_products.add(product_obj)
                    response['message'] = "Successfully added to favourites"

                elif operation == "REMOVE":
                    sales_user_obj.favourite_products.remove(product_obj)
                    response['message'] = "Successfully removed to favourites"

                sales_user_obj.save()
                response['status'] = 200

            else:
                response['message'] = "Product Not Found"
                logger.warning("ProductChangeInFavouritesAPI : Product Not Found")

        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ProductChangeInFavouritesAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchFavouriteProductsAPI(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("FetchFavouriteProductsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            page = int(data.get('page', 1))

            try :
                sales_user_obj = SalesAppUser.objects.get(username=request.user.username)
            except Exception as e :
                response['status'] = 403
                response['message'] = "User not Logged In"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("FetchFavouriteProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            product_objs = sales_user_obj.favourite_products.all()

            paginator = Paginator(product_objs, 20)
            total_pages = paginator.num_pages
            
            if page > total_pages:
                response['status'] = 404
                response['message'] = "Page number out of range"
                logger.warning("FetchFavouriteProductsAPI : Page number out of range")
                return Response(data=response)

            page_product_objs = paginator.page(page)

            product_list = []
            
            for product_obj in page_product_objs:
                
                try:
                    
                    temp_dict = {}
                    temp_dict["product_name"] = product_obj.product_name
                    temp_dict["image_url"] = product_obj.get_display_image_url()
                    temp_dict["product_description"] = product_obj.product_description
                    temp_dict["seller_sku"] = product_obj.base_product.seller_sku
                    temp_dict["product_id"] = "" if product_obj.product_id==None else str(product_obj.product_id)
                    
                    product_list.append(temp_dict)
                
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchFavouriteProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["product_list"] = product_list
            response["total_pages"] = total_pages
            response['status'] = 200
            response['message'] = "Successful"
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFavouriteProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class CreateNotification(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("CreateNotification: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            title = data.get('title', "")
            subtitle = data.get('subtitle', "")
            body = data.get('body', "")
            expiry_date = data.get('expiry_date', "")

            if title == "":
                response['status'] = 403
                response['message'] = "Title is not present"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("CreateNotification: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            if body == "":
                response['status'] = 403
                response['message'] = "Body is not present"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("CreateNotification: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            if Notification.objects.filter(title=title).exists():
                response['status'] = 403
                response['message'] = "Duplicate title found"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("CreateNotification: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            if expiry_date != "":
                
                try :
                    
                    expiry_date = convert_to_datetime(expiry_date)

                except Exception as e:
                    response['status'] = 403
                    response['message'] = "Expiry Date Format Invalid"
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.warning("CreateNotification: %s at %s", e, str(exc_tb.tb_lineno))
                    return Response(data=response)

            notification_obj = Notification.objects.create(title=title,
                                                            body=body,
                                                            subtitle=subtitle,
                                                            expiry_date=expiry_date)

            response['status'] = 200
            response['message'] = "Successful"
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateNotification: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class GetNotificationDeatilsAPI(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("EditNotification: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            notification_id = data.get('notification_id', "")

            try :
                sales_user_obj = SalesAppUser.objects.get(username=request.user.username)
            except Exception as e :
                response['status'] = 403
                response['message'] = "User not Logged In"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("FetchFavouriteProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            product_objs = sales_user_obj.favourite_products.all()

            paginator = Paginator(product_objs, 20)
            total_pages = paginator.num_pages
            
            if page > total_pages:
                response['status'] = 404
                response['message'] = "Page number out of range"
                logger.warning("FetchFavouriteProductsAPI : Page number out of range")
                return Response(data=response)

            page_product_objs = paginator.page(page)

            product_list = []
            
            for product_obj in page_product_objs:
                
                try:
                    
                    temp_dict = {}
                    temp_dict["product_name"] = product_obj.product_name
                    temp_dict["image_url"] = product_obj.get_display_image_url()
                    temp_dict["product_description"] = product_obj.product_description
                    temp_dict["seller_sku"] = product_obj.base_product.seller_sku
                    temp_dict["product_id"] = "" if product_obj.product_id==None else str(product_obj.product_id)
                    
                    product_list.append(temp_dict)
                
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchFavouriteProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["product_list"] = product_list
            response["total_pages"] = total_pages
            response['status'] = 200
            response['message'] = "Successful"
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFavouriteProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchFavouriteProductsAPI(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("FetchFavouriteProductsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            page = int(data.get('page', 1))

            try :
                sales_user_obj = SalesAppUser.objects.get(username=request.user.username)
            except Exception as e :
                response['status'] = 403
                response['message'] = "User not Logged In"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("FetchFavouriteProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            product_objs = sales_user_obj.favourite_products.all()

            paginator = Paginator(product_objs, 20)
            total_pages = paginator.num_pages
            
            if page > total_pages:
                response['status'] = 404
                response['message'] = "Page number out of range"
                logger.warning("FetchFavouriteProductsAPI : Page number out of range")
                return Response(data=response)

            page_product_objs = paginator.page(page)

            product_list = []
            
            for product_obj in page_product_objs:
                
                try:
                    
                    temp_dict = {}
                    temp_dict["product_name"] = product_obj.product_name
                    temp_dict["image_url"] = product_obj.get_display_image_url()
                    temp_dict["product_description"] = product_obj.product_description
                    temp_dict["seller_sku"] = product_obj.base_product.seller_sku
                    temp_dict["product_id"] = "" if product_obj.product_id==None else str(product_obj.product_id)
                    
                    product_list.append(temp_dict)
                
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchFavouriteProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["product_list"] = product_list
            response["total_pages"] = total_pages
            response['status'] = 200
            response['message'] = "Successful"
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFavouriteProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchFavouriteProductsAPI(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("FetchFavouriteProductsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            page = int(data.get('page', 1))

            try :
                sales_user_obj = SalesAppUser.objects.get(username=request.user.username)
            except Exception as e :
                response['status'] = 403
                response['message'] = "User not Logged In"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("FetchFavouriteProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            product_objs = sales_user_obj.favourite_products.all()

            paginator = Paginator(product_objs, 20)
            total_pages = paginator.num_pages
            
            if page > total_pages:
                response['status'] = 404
                response['message'] = "Page number out of range"
                logger.warning("FetchFavouriteProductsAPI : Page number out of range")
                return Response(data=response)

            page_product_objs = paginator.page(page)

            product_list = []
            
            for product_obj in page_product_objs:
                
                try:
                    
                    temp_dict = {}
                    temp_dict["product_name"] = product_obj.product_name
                    temp_dict["image_url"] = product_obj.get_display_image_url()
                    temp_dict["product_description"] = product_obj.product_description
                    temp_dict["seller_sku"] = product_obj.base_product.seller_sku
                    temp_dict["product_id"] = "" if product_obj.product_id==None else str(product_obj.product_id)
                    
                    product_list.append(temp_dict)
                
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchFavouriteProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["product_list"] = product_list
            response["total_pages"] = total_pages
            response['status'] = 200
            response['message'] = "Successful"
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFavouriteProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

SalesAppLoginSubmit = SalesAppLoginSubmitAPI.as_view()

SalesAppSignUpSubmit = SalesAppSignUpSubmitAPI.as_view()

SearchProductByBrand = SearchProductByBrandAPI.as_view()

ProductChangeInFavourites = ProductChangeInFavouritesAPI.as_view()

FetchFavouriteProducts = FetchFavouriteProductsAPI.as_view()

CreateNotification = CreateNotificationAPI.as_view()

GetNotificationDeatils = GetNotificationDeatilsAPI.as_view()

EditNotification = EditNotificationAPI.as_view()

SendNotification = SendNotificationAPI.as_view()

FetchNotificationList = FetchNotificationListAPI.as_view()
