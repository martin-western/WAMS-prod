# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

from WAMSApp.models import *
from SalesApp.utils import *
from SalesApp.constants import *

from django.shortcuts import HttpResponse, get_object_or_404
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models import Count

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

class LoginSubmitAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("LoginSubmitAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            email = data.get("email", "")
            password = data.get("password", "")
            fcm_id = data.get("fcm_id", "")
            
            user = authenticate(username=email, password=password)

            if user == None:
                response['status'] = 403
                response['status'] = "Incorrect Password or Email ID"
            else :
                
                login(request,user)

                response['status'] = 200
                response['status'] = "Successfully Logged In"
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("LoginSubmitAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class SignUpSubmitAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("SignUpSubmitAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            first_name = data.get("first_name", "")
            last_name = data.get("last_name", "")
            email = data.get("email", "")
            phone = data.get("phone", "")
            password = data.get("password", "")
            country = data.get("country", "")
            
            if SalesAppUser.objects.filter(username=email).exists():
                response['status'] = 403
                response['message'] = "Email ID alreay in use"
                logger.warning("SignUpSubmitAPI : Email ID alreay in use")
                return Response(data=response)

            sales_user = SalesAppUser.objects.create(username=email,password=password)

            sales_user.first_name = first_name
            sales_user.last_name = last_name
            sales_user.email = email
            sales_user.contact_number = phone
            sales_user.country = country

            sales_user.save()

            response['status'] = 200
            response['message'] = "Successfully Signed Up"
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SignUpSubmitAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class SearchProductByBrandAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("SearchProductByBrandAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            brand_name = data.get("brand_name", None)
            search_text = data.get("search_text", "")
            page = int(data.get('page', 1))

            if search_text != "":
                product_objs = Product.objects.filter(
                        Q(base_product__base_product_name__icontains=search_text) |
                        Q(product_name__icontains=search_text) |
                        Q(product_id__icontains=search_text) |
                        Q(base_product__seller_sku__icontains=search_text)
                    )

            if brand_name!=None:
                brand_obj = Brand.objects.get(name=brand_name,organization=ORGANIZATION)
                product_objs = product_objs.filter(base_product__brand=brand_obj) 

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
                    
                    product_list.append(temp_dict)
                
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("SearchProductByBrandAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["product_list"] = product_list
            response["total_pages"] = total_pages
            response['status'] = 200
            response['message'] = "Successfull"
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchProductByBrandAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class ProductChangeInFavouritesAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("ProductChangeInFavouritesAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            brand_name = data.get("brand_name", None)
            seller_sku = data.get("seller_sku",None)
            operation = data.get("operation",None)
            customer_id = data.get("customer_id",None)

            if customer_id != None:
                sales_user_obj = SalesAppUser.objects.get(customer_id=customer_id)
            else :
                response['status'] = 403
                response['message'] = "User not Found with that customer ID"
                return Response(data=response)

            if seller_sku == None:
                
                response['status'] = 403
                response['message'] = "Seller SKU not found"

                return Response(data=response)

            if operation == None:
                
                response['status'] = 403
                response['message'] = "Operation Type not specified"

                return Response(data=response)

            if operation != "ADD" or operation != "REMOVE":
                
                response['status'] = 403
                response['message'] = "Operation Type not valid"

                return Response(data=response)

            if brand_name != None:
                
                if Brand.objects.filter(name=brand_name,organization=ORGANIZATION).exists():
                    brand_obj = Brand.objects.get(name=brand_name,organization=ORGANIZATION)

                else:
                    response['status'] = 403
                    response['message'] = "Brand not found"

                    return Response(data=response)
            
            if Product.objects.filter(base_product__brand=brand_obj,base_product__seller_sku=seller_sku).exists():

                product_obj = Product.objects.get(base_product__brand=brand_obj,base_product__seller_sku=seller_sku)

                if operation == "ADD":
                    sales_user_obj.favourite_products.add(product_obj)
                    response['message'] = "Successfully added to favourites"

                elif operation == "REMOVE":
                    sales_user_obj.favourite_products.remove(product_obj)
                    response['message'] = "Successfully removed to favourites"

                sales_user_obj.save()
                response['status'] = 200

            else:

                response['status'] = 200
                response['message'] = "Product Not Found"
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ProductChangeInFavouritesAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchFavouriteProductsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("FetchFavouriteProductsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            brand_name = data.get("brand_name", None)
            customer_id = data.get("customer_id", None)
            page = int(data.get('page', 1))

            if customer_id != None:
                sales_user_obj = SalesAppUser.objects.get(customer_id=customer_id)
            else :
                response['status'] = 403
                response['message'] = "User not Found with that customer ID"
                return Response(data=response)

            product_objs = sales_user_obj.favourite_products

            if brand_name!=None:
                brand_obj = Brand.objects.get(name=brand_name,organization=ORGANIZATION)
                product_objs = product_objs.filter(base_product__brand=brand_obj) 

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
                    
                    product_list.append(temp_dict)
                
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchFavouriteProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["product_list"] = product_list
            response["total_pages"] = total_pages
            response['status'] = 200
            response['message'] = "Successfull"
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFavouriteProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

LoginSubmit = LoginSubmitAPI.as_view()

SignUpSubmit = SignUpSubmitAPI.as_view()

SearchProductByBrand = SearchProductByBrandAPI.as_view()

ProductChangeInFavourites = ProductChangeInFavouritesAPI.as_view()

FetchFavouriteProducts = FetchFavouriteProductsAPI.as_view()