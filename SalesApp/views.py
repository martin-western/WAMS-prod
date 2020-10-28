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
                logger.warning("CreateNotificationAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            if body == "":
                response['status'] = 403
                response['message'] = "Body is not present"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("CreateNotificationAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            if Notification.objects.filter(title=title).exists():
                response['status'] = 403
                response['message'] = "Duplicate title found"
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("CreateNotificationAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            if expiry_date != "":
                
                try :
                    
                    expiry_date = convert_to_datetime(expiry_date)

                except Exception as e:
                    response['status'] = 403
                    response['message'] = "Expiry Date Format Invalid"
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.warning("CreateNotificationAPI: %s at %s", e, str(exc_tb.tb_lineno))
                    return Response(data=response)

            notification_obj = Notification.objects.create(title=title,
                                                            body=body,
                                                            subtitle=subtitle,
                                                            expiry_date=expiry_date)

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

################# Notification APIs ######################

CreateNotification = CreateNotificationAPI.as_view()

GetNotificationDeatils = GetNotificationDeatilsAPI.as_view()

SaveNotification = SaveNotificationAPI.as_view()

UploadNotificationImage = UploadNotificationImageAPI.as_view()

SendNotification = SendNotificationAPI.as_view()

FetchNotificationList = FetchNotificationListAPI.as_view()
