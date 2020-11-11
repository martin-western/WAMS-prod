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

class CreateNotificationAPI(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("CreateNotificationAPI: %s", str(data))

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
                logger.warning("CreateNotificationAPI: Title is not present at %s",str(exc_tb.tb_lineno))
                return Response(data=response)

            if body == "":
                response['status'] = 403
                response['message'] = "Body is not present"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("CreateNotificationAPI: Body is not present at %s",str(exc_tb.tb_lineno))
                return Response(data=response)

            if Notification.objects.filter(title=title).exists():
                response['status'] = 403
                response['message'] = "Duplicate title found"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("CreateNotificationAPI: Duplicate title found at %s",str(exc_tb.tb_lineno))
                return Response(data=response)

            if expiry_date != "":
                
                try :
                    
                    expiry_date = convert_to_datetime(expiry_date)

                except Exception as e:
                    response['status'] = 403
                    response['message'] = "Expiry Date Format Invalid"
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.warning("CreateNotificationAPI: Expiry Date Format Invalid at %s", str(exc_tb.tb_lineno))
                    return Response(data=response)

            notification_obj = Notification.objects.create(title=title,
                                                            body=body,
                                                            subtitle=subtitle)

            if expiry_date != "":
                notification_obj.expiry_date=expiry_date
                notification_obj.save()

            response['status'] = 200
            response['message'] = "Successful"
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateNotificationAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class GetNotificationDeatilsAPI(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("GetNotificationDeatilsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            notification_id = data.get('notification_id', "")

            if notification_id == "":
                response['status'] = 403
                response['message'] = "Notification Id not sent"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("GetNotificationDeatilsAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            try :
                notification_obj = Notification.objects.get(notification_id=notification_id)
            except Exception as e :
                response['status'] = 403
                response['message'] = "Notification Id not valid"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("GetNotificationDeatilsAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            response["title"] = notification_obj.title
            response["subtitle"] = notification_obj.subtitle
            response["body"] = notification_obj.body
            response["image"] = notification_obj.get_image_url()
            response["expiry_date"] = notification_obj.get_expiry_date()
            response["notification_id"] = notification_obj.notification_id
            response["notification_status"] = notification_obj.status
            
            response['status'] = 200
            response['message'] = "Successful"
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFavouriteProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class UploadNotificationImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("UploadNotificationImageAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            notification_id = data.get('notification_id', "")
            image_url = data.get('image_url', "")

            if notification_id == "":
                response['status'] = 403
                response['message'] = "Notification Id not sent"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("UploadNotificationImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            if image_url == "":
                response['status'] = 403
                response['message'] = "Image URL not sent"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("UploadNotificationImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            try :
                notification_obj = Notification.objects.get(notification_id=notification_id)
            except Exception as e :
                response['status'] = 403
                response['message'] = "Notification Id not valid"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("UploadNotificationImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            
            image_obj = Image.objects.create(image_url)
            notification_obj.image = image_obj

            notification_obj.save()

            response['status'] = 200
            response['message'] = "Successful"

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadNotificationImageAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class DeleteNotificationImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:

            data = request.data
            logger.info("DeleteNotificationImageAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            notification_id = data.get('notification_id', "")
            image_pk = int(data.get('image_pk', 0))

            image_pk = int(data["image_pk"])
            notification_id = data["product_pk"]

            if notification_id == "":
                response['status'] = 403
                response['message'] = "Notification Id not sent"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("DeleteNotificationImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            if image_pk == 0:
                response['status'] = 403
                response['message'] = "Image PK not sent"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("DeleteNotificationImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            try :
                notification_obj = Notification.objects.get(notification_id=notification_id)
            except Exception as e :
                response['status'] = 403
                response['message'] = "Notification Id not valid"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("DeleteNotificationImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            notification_obj.image = None
            notification_obj.save()

            Image.objects.get(pk=image_pk).delete()
            
            response['status'] = 200
            response['message'] = "Successful"

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteNotificationImageAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class SaveNotificationAPI(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("SaveNotificationAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            title = data.get('title', "")
            subtitle = data.get('subtitle', "")
            body = data.get('body', "")
            expiry_date = data.get('expiry_date', "")
            notification_id = data.get('notification_id', "")

            if notification_id == "":
                response['status'] = 403
                response['message'] = "Notification Id not sent"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("SaveNotificationAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            try :
                notification_obj = Notification.objects.get(notification_id=notification_id)
            except Exception as e :
                response['status'] = 403
                response['message'] = "Notification Id not valid"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("SaveNotificationAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            if Notification.objects.filter(title=title).exclude(notification_id=notification_id).exists():
                response['status'] = 403
                response['message'] = "Duplicate title found"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("SaveNotificationAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            notification_obj.title=title
            notification_obj.body=body
            notification_obj.subtitle=subtitle
            notification_obj.expiry_date=expiry_date
            notification_obj.save()
                                                            
            response['status'] = 200
            response['message'] = "Successful"
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveNotificationAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchNotificationListAPI(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("FetchNotificationListAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            page = int(data.get('page', 1))

            try :
                sales_user_obj = SalesAppUser.objects.get(username=request.user.username)
            except Exception as e :
                response['status'] = 403
                response['message'] = "User not Logged In"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("FetchNotificationListAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            notification_objs = Notification.objects.filter(Q(expiry_date=None) | Q(expiry_date__gte=timezone.now()))

            paginator = Paginator(notification_objs, 20)
            total_pages = paginator.num_pages
            
            if page > total_pages:
                response['status'] = 404
                response['message'] = "Page number out of range"
                logger.warning("FetchNotificationListAPI : Page number out of range")
                return Response(data=response)

            page_notification_objs = paginator.page(page)

            notification_list = []
            
            for notification_obj in page_notification_objs:
                
                try:
                    
                    temp_dict = {}
                    temp_dict["title"] = notification_obj.title
                    temp_dict["subtitle"] = notification_obj.subtitle
                    temp_dict["body"] = notification_obj.body
                    temp_dict["image"] = notification_obj.get_image_url()
                    temp_dict["expiry_date"] = notification_obj.get_expiry_date()
                    temp_dict["notification_id"] = notification_obj.notification_id
                    temp_dict["notification_status"] = notification_obj.status
                    
                    notification_list.append(temp_dict)
                
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchNotificationListAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["notification_list"] = notification_list
            response["total_pages"] = total_pages
            response['status'] = 200
            response['message'] = "Successful"
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchNotificationListAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class SendNotificationAPI(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("SendNotificationAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            notification_id = data.get('notification_id', "")

            if notification_id == "":
                response['status'] = 403
                response['message'] = "Notification Id not sent"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("SendNotificationAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            try :
                notification_obj = Notification.objects.get(notification_id=notification_id)
            except Exception as e :
                response['status'] = 403
                response['message'] = "Notification Id not valid"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("SendNotificationAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            fcm_ids = SalesAppUser.objects.values_list('fcm_id',flat=True)

            notification_info = {}
            notification_info["title"] = notification_obj.title
            notification_info["subtitle"] = notification_obj.subtitle
            notification_info["body"] = notification_obj.body
            notification_info["image"] = notification_obj.get_image_url()

            try:
                result = send_firebase_notifications(fcm_ids,notification_info)
            except Exception as e:
                response['status'] = 403
                response['message'] = "Firebase API error"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("SendNotificationAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            if result.status_code == 200 :
                notification_obj.status = "Sent"
                result = result.json()
                response["success_notifications"] = result["success"]
                response["failure_notifications"] = result["failure"]

            else:
                notification_obj.status = "Failed"

            notification_obj.save()

            response['status'] = 200
            response['message'] = "Successful"
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SendNotificationAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchProductListByCategoryForSalesAppAPI(APIView):

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        response['message'] = ""
        
        try:
            
            data = request.data
            logger.info("FetchProductListByCategoryForSalesAppAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            category_id = data.get("category_id","")
            brand_name = data.get("brand_name", None)
            page = int(data.get('page', 1))

            if category_id == "":
                response['status'] = 404
                response['message'] = "Category Id is Null"
                logger.warning("FetchProductListByCategoryForSalesAppAPI: Category ID is Null")
                return Response(data=response)
            
            try :
                product_objs = Product.objects.filter(base_product__category__uuid=category_id)
            except Exception as e:
                response['status'] = 404
                response['message'] = "Category Id is Invalid"
                logger.warning("FetchProductListByCategoryForSalesAppAPI: Category ID is Invalid")
                return Response(data=response)

            if brand_name!=None:
                product_objs = product_objs.filter(base_product__brand__name=brand_name)

            sales_user_obj = None
            favourite_product_objs = Product.objects.none()  

            try :
                sales_user_obj = SalesAppUser.objects.get(username=request.user.username)
                favourite_product_objs = sales_user_obj.favourite_products.all()
            except Exception as e :
                pass

            paginator = Paginator(product_objs, 20)
            product_objs = paginator.page(page)
            total_pages = paginator.num_pages

            product_list = []
            for product_obj in product_objs:
                
                try:
                    
                    temp_dict = {}
                    temp_dict["product_name"] = product_obj.product_name
                    temp_dict["product_description"] = product_obj.product_description
                    temp_dict["seller_sku"] = product_obj.base_product.seller_sku
                    temp_dict["product_id"] = "" if product_obj.product_id==None else str(product_obj.product_id)
                    temp_dict["is_favourite"] = False
                    if product_obj in favourite_product_objs:
                        temp_dict["is_favourite"] = True

                    product_list.append(temp_dict)
                
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchProductListByCategoryForSalesAppAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["product_list"] = product_list
            response["total_pages"] = total_pages
            response['status'] = 200
            response['message'] = "Successful"
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductListByCategoryForSalesAppAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

SalesAppLoginSubmit = SalesAppLoginSubmitAPI.as_view()

SalesAppSignUpSubmit = SalesAppSignUpSubmitAPI.as_view()

SearchProductByBrand = SearchProductByBrandAPI.as_view()

ProductChangeInFavourites = ProductChangeInFavouritesAPI.as_view()

FetchFavouriteProducts = FetchFavouriteProductsAPI.as_view()

################# Notification APIs ######################

CreateNotification = CreateNotificationAPI.as_view()

GetNotificationDeatils = GetNotificationDeatilsAPI.as_view()

SaveNotification = SaveNotificationAPI.as_view()

UploadNotificationImage = UploadNotificationImageAPI.as_view()

DeleteNotificationImage = DeleteNotificationImageAPI.as_view()

SendNotification = SendNotificationAPI.as_view()

FetchNotificationList = FetchNotificationListAPI.as_view()

FetchProductListByCategoryForSalesApp = FetchProductListByCategoryForSalesAppAPI.as_view()