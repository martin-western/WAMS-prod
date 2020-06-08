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

from . import utils

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


class FetchProductDetailsAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,) 
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchProductDetailsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            dealshub_product_obj = DealsHubProduct.objects.get(product__uuid=data["uuid"])
            product_obj = dealshub_product_obj.product
            base_product_obj = product_obj.base_product

            response["category"] = "" if base_product_obj.category==None else str(base_product_obj.category)
            response["subCategory"] = "" if base_product_obj.sub_category==None else str(base_product_obj.sub_category)
            response["uuid"] = data["uuid"]
            response["name"] = product_obj.product_name
            response["price"] = dealshub_product_obj.now_price
            response["wasPrice"] = dealshub_product_obj.was_price
            response["currency"] = "AED"
            response["warranty"] = product_obj.warranty

            response["isStockAvailable"] = False
            if dealshub_product_obj.stock>0:
                response["isStockAvailable"] = True

            response["productDispDetails"] = product_obj.product_description 
            try:
                response["specifications"] = json.loads(product_obj.dynamic_form_attributes)
            except Exception as e:
                response["specifications"] = {}

            try:
                response["features"] = json.loads(product_obj.pfl_product_features)
            except Exception as e:
                response["features"] = []


            image_list = []
            lifestyle_image_objs = product_obj.lifestyle_images.all()
            for lifestyle_image_obj in lifestyle_image_objs:
                try:
                    temp_image = {}
                    temp_image["original"] = lifestyle_image_obj.mid_image.url
                    temp_image["thumbnail"] = lifestyle_image_obj.thumbnail.url
                    image_list.append(temp_image)
                except Exception as e:
                    pass

            main_images_list = ImageBucket.objects.none()
            main_images_objs = MainImages.objects.filter(product=product_obj)
            for main_images_obj in main_images_objs:
                main_images_list |= main_images_obj.main_images.all()
            main_images_list = main_images_list.distinct()
            main_images = create_response_images_main(main_images_list)
            for main_image in main_images:
                try:
                    temp_image = {}
                    temp_image["original"] = main_image["midimage_url"]
                    temp_image["thumbnail"] = main_image["thumbnail_url"]
                    image_list.append(temp_image)
                except Exception as e:
                    pass

            sub_images_list = ImageBucket.objects.none()
            sub_images_objs = SubImages.objects.filter(product=product_obj)
            for sub_images_obj in sub_images_objs:
                sub_images_list |= sub_images_obj.sub_images.all()
            sub_images_list = sub_images_list.distinct()
            sub_images = create_response_images_sub(sub_images_list)
            for sub_image in sub_images:
                try:
                    temp_image = {}
                    temp_image["original"] = sub_image["midimage_url"]
                    temp_image["thumbnail"] = sub_image["thumbnail_url"]
                    image_list.append(temp_image)
                except Exception as e:
                    pass

            try:
                response["heroImageUrl"] = image_list[0]["original"]
            except Exception as e:
                response["heroImageUrl"] = Config.objects.all()[0].product_404_image.image.url

            response["productImagesUrl"] = image_list

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductDetailsAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)


FetchProductDetails = FetchProductDetailsAPI.as_view()


class FetchSectionsProductsAPI(APIView):
    
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchSectionsProductsAPI: %s", str(data))

            website_group_name = data["websiteGroupName"]

            section_objs = Section.objects.filter(website_group__name=website_group_name, is_published=True)

            section_list =  []

            for section_obj in section_objs:
                product_objs = section_obj.products.all()
                temp_dict = {}
                temp_dict["sectionName"] = section_obj.name
                temp_dict["uid"] = section_obj.uuid
                temp_dict["productsArray"] = []
                for product_obj in product_objs:
                    temp_dict2 = {}
                    temp_dict2["productName"] = product_obj.product_name
                    temp_dict2["productCategory"] = "" if product_obj.base_product.category==None else str(product_obj.base_product.category)
                    temp_dict2["productSubCategory"] = "" if product_obj.base_product.sub_category==None else str(product_obj.base_product.sub_category)
                    temp_dict2["brand"] = str(product_obj.base_product.brand)
                    
                    if(product.base_product.brand.name=="Geepas"):
                        temp_dict2["price"] = "0"
                    else:
                        temp_dict2["price"] = product.standard_price

                    temp_dict2["prevPrice"] = temp_dict2["price"]
                    temp_dict2["currency"] = "AED"
                    temp_dict2["rating"] = "0"
                    temp_dict2["totalRatings"] = "0"
                    temp_dict2["id"] = str(product_obj.uuid)
                    main_images_list = ImageBucket.objects.none()
                    main_images_objs = MainImages.objects.filter(product=product_obj)
                    for main_images_obj in main_images_objs:
                        main_images_list |= main_images_obj.main_images.all()
                    main_images_list = main_images_list.distinct()
                    try:
                        temp_dict2["heroImage"] = main_images_list.all()[0].image.mid_image.url
                    except Exception as e:
                        temp_dict2["heroImage"] = Config.objects.all()[0].product_404_image.image.url

                    temp_dict["productsArray"].append(temp_dict2)
                section_list.append(temp_dict)

            response['section_list'] = section_list
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSectionsProductsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)

FetchSectionsProducts = FetchSectionsProductsAPI.as_view()


class FetchSectionsProductsLimitAPI(APIView):
    
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchSectionsProductsLimitAPI: %s", str(data))

            website_group_name = data["websiteGroupName"]

            section_objs = Section.objects.filter(website_group__name=website_group_name, is_published=True)

            section_list =  []

            for section_obj in section_objs:
                product_objs = section_obj.products.all()
                temp_dict = {}
                temp_dict["sectionName"] = section_obj.name
                temp_dict["uid"] = section_obj.uuid
                temp_dict["productsArray"] = []
                for product_obj in product_objs[:12]:
                    temp_dict2 = {}
                    temp_dict2["productName"] = product_obj.product_name
                    temp_dict2["productCategory"] = "" if product_obj.base_product.category==None else str(product_obj.base_product.category)
                    temp_dict2["productSubCategory"] = "" if product_obj.base_product.sub_category==None else str(product_obj.base_product.sub_category)
                    temp_dict2["brand"] = str(product_obj.base_product.brand)

                    if(product_obj.base_product.brand.name=="Geepas"):
                        temp_dict2["price"] = "0"
                    else:
                        temp_dict2["price"] = product_obj.standard_price
                    temp_dict2["prevPrice"] = temp_dict2["price"]
                    temp_dict2["currency"] = "AED"
                    temp_dict2["discount"] = "0"
                    temp_dict2["rating"] = "4.5"
                    temp_dict2["totalRatings"] = "5,372"
                    temp_dict2["id"] = str(product_obj.uuid)
                    main_images_list = ImageBucket.objects.none()
                    main_images_objs = MainImages.objects.filter(product=product_obj)
                    for main_images_obj in main_images_objs:
                        main_images_list |= main_images_obj.main_images.all()
                    main_images_list = main_images_list.distinct()
                    if main_images_list.filter(is_main_image=True).count() > 0:
                        try:
                            temp_dict2["heroImage"] = main_images_list.filter(is_main_image=True)[
                                0].image.mid_image.url
                        except Exception as e:
                            temp_dict2["heroImage"] = Config.objects.all()[
                                0].product_404_image.image.url
                    else:
                        temp_dict2["heroImage"] = Config.objects.all()[
                            0].product_404_image.image.url


                    temp_dict["productsArray"].append(temp_dict2)
                section_list.append(temp_dict)

            response['section_list'] = section_list
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSectionsProductsLimitAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)

FetchSectionsProductsLimit = FetchSectionsProductsLimitAPI.as_view()


class FetchSectionProductsAPI(APIView):
    
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchSectionProductsAPI: %s", str(data))

            uuid = data["sectionUuid"]
            section_obj = Section.objects.get(uuid=uuid)
            product_objs = section_obj.products.all()
            temp_dict = {}
            temp_dict["sectionName"] = section_obj.name
            temp_dict["productsArray"] = []
            for product_obj in product_objs:
                temp_dict2 = {}
                temp_dict2["name"] = product_obj.product_name
                temp_dict2["brand"] = str(product_obj.base_product.brand)
                temp_dict2["price"] = "0"
                temp_dict2["prevPrice"] = temp_dict2["price"]
                temp_dict2["currency"] = "AED"
                #temp_dict2["discount"] = "10%"
                temp_dict2["rating"] = "0"
                temp_dict2["totalRatings"] = "0"
                temp_dict2["uuid"] = str(product_obj.uuid)
                temp_dict2["id"] = str(product_obj.uuid)
                main_images_list = ImageBucket.objects.none()
                main_images_objs = MainImages.objects.filter(product=product_obj)
                for main_images_obj in main_images_objs:
                    main_images_list |= main_images_obj.main_images.all()
                main_images_list = main_images_list.distinct()
                
                try:
                    temp_dict2["heroImageUrl"] = main_images_list.all()[
                        0].image.mid_image.url
                except Exception as e:
                    temp_dict2["heroImageUrl"] = Config.objects.all()[
                        0].product_404_image.image.url


                temp_dict["productsArray"].append(temp_dict2)

            response['sectionData'] = temp_dict
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSectionProductsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)

FetchSectionProducts = FetchSectionProductsAPI.as_view()



class FetchSuperCategoriesAPI(APIView):
    
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchSuperCategoriesAPI: %s", str(data))
            website_group_name = data["websiteGroupName"]

            super_category_objs = SuperCategory.objects.all()

            super_category_list = []
            for super_category_obj in super_category_objs:
                temp_dict = {}
                temp_dict["name"] = super_category_obj.name
                temp_dict["uuid"] = super_category_obj.uuid
                temp_dict["imageUrl"] = ""
                if super_category_obj.image!=None:
                    temp_dict["imageUrl"] = super_category_obj.image.thumbnail.url
                super_category_list.append(temp_dict)

            response['superCategoryList'] = super_category_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSuperCategoriesAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


FetchSuperCategories = FetchSuperCategoriesAPI.as_view()


class FetchCategoriesAPI(APIView):
    
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchCategoriesAPI: %s", str(data))
            website_group_name = data["websiteGroupName"]

            category_objs = WebsiteGroup.objects.get(name=website_group_name).categories.all()

            category_list = []
            for category_obj in category_objs:
                temp_dict = {}
                temp_dict["name"] = category_obj.name
                temp_dict["uuid"] = category_obj.uuid
                temp_dict["imageUrl"] = ""
                if category_obj.image!=None:
                    temp_dict["imageUrl"] = category_obj.image.thumbnail.url
                category_list.append(temp_dict)

            response['categoryList'] = category_list

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCategoriesAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


FetchCategories = FetchCategoriesAPI.as_view()


class SearchAPI(APIView):
    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SearchAPI: %s", str(data))
            
            product_name = data.get("name", "").strip()
            super_category_name = data.get("superCategory", "").strip()
            category_name = data.get("category", "").strip()
            subcategory_name = data.get("subcategory", "").strip()
            brand_name = data.get("brand", "").strip()

            filter_list = data.get("filters", "[]")
            filter_list = json.loads(filter_list)

            website_group_name = data["websiteGroupName"]
            website_group_obj = WebsiteGroup.objects.get(name=website_group_name)

            page = data.get("page", 1)
            search = {}            

            available_dealshub_products = DealsHubProduct.objects.filter(product__base_product__brand__in=website_group_obj.brands.all(), is_published=True)
            if brand_name!="":
                available_dealshub_products = available_dealshub_products.filter(product__base_product__brand__name=brand_name)

            if super_category_name!="":
                available_dealshub_products = available_dealshub_products.filter(product__base_product__category__super_category__name=super_category_name)

            if category_name!="ALL" and category_name!="":
                available_dealshub_products = available_dealshub_products.filter(product__base_product__category__name=category_name)

            if subcategory_name!="":
                available_dealshub_products = available_dealshub_products.filter(product__base_product__sub_category__name=subcategory_name)
            
            if product_name!="":
                available_dealshub_products = available_dealshub_products.filter(product__product_name__icontains=product_name)

            filtered_products = DealsHubProduct.objects.none()
            try:
                if len(filter_list)>0:
                    for filter_metric in filter_list:
                        for filter_value in filter_metric["values"]:
                            filtered_products |= available_dealshub_products.filter(product__dynamic_form_attributes__icontains='"value": "'+filter_value+'"')
                    filtered_products = filtered_products.distinct()
                else:
                    filtered_products = available_dealshub_products
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SearchAPI: %s at %s", e, str(exc_tb.tb_lineno))


            paginator = Paginator(filtered_products, 20)
            dealshub_product_list = paginator.page(page)            
            products = []
            for dealshub_product in dealshub_product_list:
                try:
                    product = dealshub_product.product
                    temp_dict = {}
                    temp_dict["name"] = product.product_name
                    temp_dict["brand"] = str(product.base_product.brand)
                    temp_dict["price"] = str(dealshub_product.now_price)
                    temp_dict["wasPrice"] = str(dealshub_product.was_price)
                    temp_dict["currency"] = "AED"
                    temp_dict["rating"] = "0"
                    temp_dict["totalRatings"] = "0"
                    temp_dict["uuid"] = product.uuid
                    temp_dict["id"] = product.uuid
                    
                    main_images_list = ImageBucket.objects.none()
                    main_images_objs = MainImages.objects.filter(product=product)
                    for main_images_obj in main_images_objs:
                        main_images_list |= main_images_obj.main_images.all()
                    main_images_list = main_images_list.distinct()

                    try:
                        temp_dict["heroImageUrl"] = main_images_list.all()[0].image.mid_image.url
                    except Exception as e:
                        temp_dict["heroImageUrl"] = Config.objects.all()[0].product_404_image.image.url
                    
                    products.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("SearchAPI: %s at %s", e, str(exc_tb.tb_lineno))

            filters = []
            try:
                if category_name!="ALL":
                    category_obj = Category.objects.get(name = category_name)
                    property_data = json.loads(category_obj.property_data)
                    for p_data in property_data:
                        temp_dict = {}
                        temp_dict["key"] = p_data["key"]
                        temp_dict["values"] = p_data["values"]
                        filters.append(temp_dict)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SearchAPI filter creation: %s at %s", e, str(exc_tb.tb_lineno))

            is_super_category_available = False
            category_list = []
            try:
                super_category_obj = None
                if super_category_name!="":
                    is_super_category_available = True
                    super_category_obj = SuperCategory.objects.get(name=super_category_name)

                if category_name!="" and category_name!="ALL":
                    super_category_obj = Category.objects.filter(name=category_name)[0].super_category

                category_objs = Category.objects.filter(super_category=super_category_obj)
                for category_obj in category_objs:
                    temp_dict = {}
                    temp_dict["name"] = category_obj.name
                    temp_dict["uuid"] = category_obj.uuid
                    sub_category_objs = SubCategory.objects.filter(category=category_obj)
                    sub_category_list = []
                    for sub_category_obj in sub_category_objs:
                        temp_dict2 = {}
                        temp_dict2["name"] = sub_category_obj.name
                        temp_dict2["uuid"] = sub_category_obj.uuid
                        sub_category_list.append(temp_dict2)
                    temp_dict["subCategoryList"] = sub_category_list
                    category_list.append(temp_dict)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SearchAPI filter creation: %s at %s", e, str(exc_tb.tb_lineno))

            response["isSuperCategoryAvailable"] = is_super_category_available
            response["categoryList"] = category_list

            is_available = True
            
            if int(paginator.num_pages) == int(page):
                is_available = False

            response["is_available"] = is_available
            response["total_products"] = len(filtered_products)

            search['filters'] = filters
            search['category'] = category_name
            search['products'] = products
            response['search'] = search
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


Search = SearchAPI.as_view()


class CreateAdminCategoryAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("CreateAdminCategoryAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            website_group_name = data["websiteGroupName"]
            website_group_obj = WebsiteGroup.objects.get(name=website_group_name)

            data = data["sectionData"]

            name = data["name"]
            listing_type = data["listingType"]
            products = data["products"]
            is_promotional = data["is_promotional"]
            
            order_index = Banner.objects.filter(website_group=website_group_obj).count()+Section.objects.filter(website_group=website_group_obj).count()+1

            section_obj = Section.objects.create(website_group=website_group_obj, name=name, listing_type=listing_type, order_index=order_index)
            for product in products:
                product_obj = Product.objects.get(uuid=product)
                section_obj.products.add(product_obj)

            section_obj.save()

            response['uuid'] = str(section_obj.uuid)
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateAdminCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchAdminCategoriesAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchAdminCategoriesAPI: %s", str(data))

            website_group_name = data["websiteGroupName"]

            website_group_obj = WebsiteGroup.objects.get(name=website_group_name)

            section_objs = Section.objects.filter(website_group=website_group_obj)

            section_list = []
            
            for section_obj in section_objs:
                temp_dict = {}
                temp_dict["uuid"] = str(section_obj.uuid)
                temp_dict["name"] = str(section_obj.name)
                temp_dict["listingType"] = str(section_obj.listing_type)
                temp_dict["createdBy"] = str(section_obj.created_by)
                temp_dict["modifiedBy"] = str(section_obj.modified_by)
                temp_dict["createdOn"] = str(section_obj.created_date)
                temp_dict["modifiedOn"] = str(section_obj.modified_date)
                temp_dict["type"] = "ProductListing"
                temp_products = []
                for prod in section_obj.products.all():
                    temp_dict2 = {}

                    main_images_list = ImageBucket.objects.none()
                    try:
                        main_images_obj = MainImages.objects.get(
                            product=prod, is_sourced=True)
                        main_images_list |= main_images_obj.main_images.all()
                        main_images_list = main_images_list.distinct()
                        images = create_response_images_main(main_images_list)
                        temp_dict2["thumbnailImageUrl"] = images[0]["thumbnail_url"]
                    except Exception as e:
                        temp_dict2["thumbnailImageUrl"] = ""

                    
                    temp_dict2["name"] = str(prod.product_name)
                    temp_dict2["displayId"] = str(prod.product_id)
                    temp_dict2["uuid"] = str(prod.uuid)
                    temp_products.append(temp_dict2)
                temp_dict["products"] = temp_products
                temp_dict["isPublished"] = section_obj.is_published
                section_list.append(temp_dict)

            response['section_list'] = section_list
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchAdminCategoriesAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UpdateAdminCategoryAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateAdminCategoryAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            data = data["sectionData"]

            uuid = data["uuid"]
            name = data["name"]
            listing_type = data["listingType"]
            is_published = data["isPublished"]
            products = data["products"]
            is_promotional = data["is_promotional"]
            
            promotion_obj = None
            if is_promotional:
                promotion = data["promotion"]
                start_date = promotion["start_date"]
                end_date = promotion["end_promotion"]
                promotional_tag = promotion["promotional_tag"]
                promotion_obj = Promotion.objects.create(promotion_tag=promotional_tag, start_time=start_date, end_date=end_date)
            
            section_obj = Section.objects.get(uuid=uuid)
            section_obj.name = name
            section_obj.listing_type = listing_type
            section_obj.is_published = is_published
            section_obj.modified_by = None
            section_obj.promotion = promotion_obj
            section_obj.products.clear()
            for product in products:
                product_obj = Product.objects.get(uuid=product)
                if is_promotional:
                    product_obj.promotion = promotion_obj
                    product_obj.save()
                section_obj.products.add(product_obj)

            section_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateAdminCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class DeleteAdminCategoryAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("DeleteAdminCategoryAPI: %s", str(data))

            uuid = data["uuid"]
            
            section_obj = Section.objects.get(uuid=uuid)
            products = section_obj.products

            for product in products:
                product_obj = Product.objects.get(uuid=product)
                product_obj.promotion = None
                product_obj.save()
                
            section_obj.delete()
            
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteAdminCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class PublishAdminCategoryAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("PublishAdminCategoryAPI: %s", str(data))

            uuid = data["uuid"]
            
            section_obj = Section.objects.get(uuid=uuid)
            section_obj.is_published = True
            section_obj.save()
            
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PublishAdminCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UnPublishAdminCategoryAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UnPublishAdminCategoryAPI: %s", str(data))

            uuid = data["uuid"]
            
            section_obj = Section.objects.get(uuid=uuid)
            section_obj.is_published = False
            section_obj.save()
            
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UnPublishAdminCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class SectionBulkUploadAPI(APIView):
    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("SectionBulkUploadAPI: %s", str(data))

            path = default_storage.save('tmp/temp-section.xlsx', data["import_file"])
            path = "https://wig-wams-s3-bucket.s3.ap-south-1.amazonaws.com/"+path
            dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
            rows = len(dfs.iloc[:])

            uuid = data["uuid"]
            section_obj = Section.objects.get(uuid=uuid)

            products = []
            unsuccessful_count = 0
            for i in range(rows):
                try:
                    product_id = dfs.iloc[i][0]
                    product_obj = Product.objects.get(product_id=product_id)
                    if DealsHubProduct.objects.get(product=product_obj).is_published==False:
                        continue
                    section_obj.products.add(product_obj)

                    temp_dict2 = {}

                    main_images_list = ImageBucket.objects.none()
                    try:
                        main_images_obj = MainImages.objects.get(
                            product=product_obj, is_sourced=True)
                        main_images_list |= main_images_obj.main_images.all()
                        main_images_list = main_images_list.distinct()
                        images = create_response_images_main(main_images_list)
                        temp_dict2["thumbnailImageUrl"] = images[0]["thumbnail_url"]
                    except Exception as e:
                        temp_dict2["thumbnailImageUrl"] = ""

                    temp_dict2["name"] = str(product_obj.product_name)
                    temp_dict2["displayId"] = str(product_obj.product_id)
                    temp_dict2["uuid"] = str(product_obj.uuid)
                    products.append(temp_dict2)

                except Exception as e:
                    unsuccessful_count += 1
                    
            section_obj.save()

            response["products"] = products
            response["unsuccessful_count"] = unsuccessful_count
            response["filepath"] = path 
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SectionBulkUploadAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)



class FetchBannerTypesAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchBannerTypesAPI: %s", str(data))

            website_group_name = data["websiteGroupName"]

            banner_type_objs = BannerType.objects.filter(website_group__name=website_group_name)

            banner_types = []
            for banner_type_obj in banner_type_objs:
                temp_dict = {}
                temp_dict["type"] = banner_type_obj.name
                temp_dict["name"] = banner_type_obj.display_name
                temp_dict["limit"] = banner_type_obj.limit
                banner_types.append(temp_dict)

            response['bannerTypes'] = banner_types
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchBannerTypesAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)



class CreateBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("CreateBannerAPI: %s", str(data))

            banner_type = data["bannerType"]
            website_group_name = data["websiteGroupName"]
            name = data.get("name", "")

            website_group_obj = WebsiteGroup.objects.get(name=website_group_name)

            banner_type_obj = BannerType.objects.get(name=banner_type, website_group=website_group_obj)

            if name=="":
                name = banner_type_obj.display_name

            order_index = Banner.objects.filter(website_group=website_group_obj).count()+Section.objects.filter(website_group=website_group_obj).count()+1

            banner_obj = Banner.objects.create(name=name, website_group=website_group_obj, order_index=order_index, banner_type=banner_type_obj)
            
            response['uuid'] = banner_obj.uuid
            response["limit"] = banner_type_obj.limit
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UpdateBannerNameAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UpdateBannerNameAPI: %s", str(data))

            name = data["name"]
            uuid = data["uuid"]

            banner_obj = Banner.objects.get(uuid=uuid)
            banner_obj.name = name
            banner_obj.save()
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateBannerNameAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class AddBannerImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("AddBannerImageAPI: %s", str(data))

            uuid = data["uuid"]
            banner_image = data["image"]
            is_promotional = data["is_promotional"]

            promotion_obj = None
            if is_promotional:
                promotion = data["promotion"]
                start_date = promotion["start_date"]
                end_date = promotion["end_promotion"]
                promotional_tag = promotion["promotional_tag"]
                promotion_obj = Promotion.objects.create(promotion_tag=promotional_tag, start_time=start_date, end_date=end_date)

            banner_obj = Banner.objects.get(uuid=uuid)
            image_obj = Image.objects.create(image=banner_image)
            unit_banner_image_obj = UnitBannerImage.objects.create(image=image_obj, banner=banner_obj, promotion=promotion_obj)

            response['uuid'] = unit_banner_image_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddBannerImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UpdateBannerImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UpdateBannerImageAPI: %s", str(data))

            uuid = data["uuid"]
            banner_image = data["image"]
            image_type = data.get("imageType", "mobile")

            unit_banner_image_obj = UnitBannerImage.objects.get(uuid=uuid)
            image_obj = Image.objects.create(image=banner_image)
            
            if image_type=="mobile":
                unit_banner_image_obj.mobile_image = image_obj
            else:
                unit_banner_image_obj.image = image_obj

            unit_banner_image_obj.save()

            response['uuid'] = unit_banner_image_obj.uuid
            response['url'] = image_obj.mid_image.url
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateBannerImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class DeleteBannerImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteBannerImageAPI: %s", str(data))

            uuid = data["uuid"]
            image_type = data["imageType"]

            unit_banner_image_obj = UnitBannerImage.objects.get(uuid=uuid)

            if image_type=="mobile":
                unit_banner_image_obj.mobile_image = None
            else:
                unit_banner_image_obj.image = None

            unit_banner_image_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteBannerImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class DeleteUnitBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteUnitBannerAPI: %s", str(data))

            uuid = data["uuid"]

            unit_banner_obj = UnitBannerImage.objects.get(uuid=uuid)
            products = unit_banner_obj.products

            for product in products:
                product_obj = Product.objects.get(uuid=product)
                product_obj.promotion = None
                product_obj.save()

            unit_banner_obj.delete()
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteUnitBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)



class FetchBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchBannerAPI: %s", str(data))

            resolution = data.get("resolution", "low")
            banner_uuid = data["uuid"]

            banner_obj = Banner.objects.get(uuid=banner_uuid)
            unit_banner_image_objs = UnitBannerImage.objects.filter(banner=banner_obj)

            banner_images = []

            for unit_banner_image_obj in unit_banner_image_objs:
                try:
                    temp_dict = {}
                    temp_dict["uid"] = unit_banner_image_obj.uuid
                    temp_dict["httpLink"] = unit_banner_image_obj.http_link
                    temp_dict["url"] = ""
                    if unit_banner_image_obj.image!=None:
                        if resolution=="low":
                            temp_dict["url"] = unit_banner_image_obj.image.thumbnail.url
                        else:
                            temp_dict["url"] = unit_banner_image_obj.image.image.url

                    temp_dict["mobileUrl"] = ""
                    if unit_banner_image_obj.mobile_image!=None:
                        if resolution=="low":
                            temp_dict["mobileUrl"] = unit_banner_image_obj.mobile_image.thumbnail.url
                        else:
                            temp_dict["mobileUrl"] = unit_banner_image_obj.mobile_image.image.url
                        

                    banner_images.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
            
            response["bannerImages"] = banner_images
            response["limit"] = banner_obj.banner_type.limit
            response["type"] = banner_obj.banner_type.name
            response["name"] = banner_obj.name
            response["is_published"] = banner_obj.is_published
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchDealsBannerAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class DeleteBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteBannerAPI: %s", str(data))

            uuid = data["uuid"]
            Banner.objects.get(uuid=uuid).delete()
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class PublishBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("PublishBannerAPI: %s", str(data))

            uuid = data["uuid"]
            banner_obj = Banner.objects.get(uuid=uuid)
            banner_obj.is_published = True
            banner_obj.save()
            
            response['uuid'] = banner_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PublishBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UnPublishBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UnPublishBannerAPI: %s", str(data))

            uuid = data["uuid"]
            banner_obj = Banner.objects.get(uuid=uuid)
            banner_obj.is_published = False
            banner_obj.save()
            
            response['uuid'] = banner_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UnPublishBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class PublishDealsHubProductAPI(APIView):
    
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("PublishDealsHubProductAPI: %s", str(data))
            product_pk = data["product_pk"]
            product_obj = Product.objects.get(pk=product_pk)
            dealshub_product_obj = DealsHubProduct.objects.get(product=product_obj)
            dealshub_product_obj.is_published = True
            dealshub_product_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PublishDealsHubProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UnPublishDealsHubProductAPI(APIView):
    
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UnPublishDealsHubProductAPI: %s", str(data))
            product_pk = data["product_pk"]
            product_obj = Product.objects.get(pk=product_pk)
            dealshub_product_obj = DealsHubProduct.objects.get(product=product_obj)
            dealshub_product_obj.is_published = False
            dealshub_product_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UnPublishDealsHubProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class DeleteProductFromSectionAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteProductFromSectionAPI: %s", str(data))

            section_uuid = data["sectionUuid"]
            product_uuid = data["productUuid"]

            section_obj = Section.objects.get(uuid=section_uuid)
            product_obj = Product.objects.get(uuid=product_uuid)
            product_obj.promotion = None
            product_obj.save()
            section_obj.products.remove(product_obj)
            section_obj.save()
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteProductFromSectionAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class PublishDealsHubProductsAPI(APIView):
    
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("PublishDealsHubProductsAPI: %s", str(data))
            product_pk_list = data["product_pk_list"]
            for product_pk in product_pk_list:
                product_obj = Product.objects.get(pk=product_pk)
                dealshub_product_obj = DealsHubProduct.objects.get(product=product_obj)
                dealshub_product_obj.is_published = True
                dealshub_product_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PublishDealsHubProductsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UnPublishDealsHubProductsAPI(APIView):
    
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UnPublishDealsHubProductsAPI: %s", str(data))
            product_pk_list = data["product_pk_list"]
            for product_pk in product_pk_list:
                product_obj = Product.objects.get(pk=product_pk)
                dealshub_product_obj = DealsHubProduct.objects.get(product=product_obj)
                dealshub_product_obj.is_published = False
                dealshub_product_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UnPublishDealsHubProductsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UpdateLinkBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UpdateLinkBannerAPI: %s", str(data))

            http_link = data["httpLink"]
            uuid = data["uuid"]

            unit_banner_image_obj = UnitBannerImage.objects.get(uuid=uuid)
            unit_banner_image_obj.http_link = http_link
            unit_banner_image_obj.save()
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateLinkBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchHeadingDataAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchHeadingDataAPI: %s", str(data))

            website_group_name = data["websiteGroupName"]

            included_category_dict = {}

            dealshub_heading_objs = DealsHubHeading.objects.filter(website_group__name=website_group_name)
            heading_list = []
            for dealshub_heading_obj in dealshub_heading_objs:
                temp_dict = {}
                temp_dict["headingName"] = dealshub_heading_obj.name
                category_list = []
                category_objs = dealshub_heading_obj.categories.all()
                for category_obj in category_objs:
                    included_category_dict[category_obj.pk] = 1
                    temp_dict2 = {}
                    temp_dict2["categoryName"] = category_obj.name
                    sub_category_list = []
                    sub_category_objs = SubCategory.objects.filter(category=category_obj)
                    for sub_category_obj in sub_category_objs:
                        temp_dict3 = {}
                        temp_dict3["subcategoryName"] = sub_category_obj.name
                        sub_category_list.append(temp_dict3)
                    temp_dict2["subcategoryList"] = sub_category_list
                    category_list.append(temp_dict2)
                temp_dict["categoryList"] = category_list
                
                image_list = []
                image_link_objs = dealshub_heading_obj.image_links.all()
                for image_link_obj in image_link_objs:
                    temp_dict4 = {}
                    temp_dict4["imageUrl"] = image_link_obj.image.image.url
                    temp_dict4["httpLink"] = image_link_obj.http_link
                    image_list.append(temp_dict4)
                temp_dict["imageList"] = image_list

                heading_list.append(temp_dict)

            temp_dict = {}
            other_category_list = []
            temp_dict["headingName"] = "Others"
            category_objs = WebsiteGroup.objects.get(name=website_group_name).categories.all()
            for category_obj in category_objs:
                if category_obj.pk not in included_category_dict:
                    temp_dict2 = {}
                    temp_dict2["categoryName"] = category_obj.name
                    sub_category_list = []
                    sub_category_objs = SubCategory.objects.filter(category=category_obj)
                    for sub_category_obj in sub_category_objs:
                        temp_dict3 = {}
                        temp_dict3["subcategoryName"] = sub_category_obj.name
                        sub_category_list.append(temp_dict3)
                    temp_dict2["subcategoryList"] = sub_category_list
                    other_category_list.append(temp_dict2)
            temp_dict["categoryList"] = other_category_list
            temp_dict["imageList"] = []
            if len(other_category_list)>0:
                heading_list.append(temp_dict)

            response["headingList"] = heading_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchHeadingDataAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchHeadingDataAdminAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchHeadingDataAdminAPI: %s", str(data))

            website_group_name = data["websiteGroupName"]

            dealshub_heading_objs = DealsHubHeading.objects.filter(website_group__name=website_group_name)
            heading_list = []
            for dealshub_heading_obj in dealshub_heading_objs:
                temp_dict = {}
                temp_dict["headingName"] = dealshub_heading_obj.name
                temp_dict["uuid"] = dealshub_heading_obj.uuid
                category_list = []
                category_objs = dealshub_heading_obj.categories.all()
                for category_obj in category_objs:
                    temp_dict2 = {}
                    temp_dict2["key"] = category_obj.uuid+"|"+category_obj.name

                    category_list.append(temp_dict2)
                temp_dict["categoryList"] = category_list
                
                image_list = []
                image_link_objs = dealshub_heading_obj.image_links.all()
                for image_link_obj in image_link_objs:
                    temp_dict4 = {}
                    temp_dict4["url"] = image_link_obj.image.image.url
                    temp_dict4["httpLink"] = image_link_obj.http_link
                    temp_dict4["uid"] = image_link_obj.uuid
                    image_list.append(temp_dict4)
                temp_dict["imageList"] = image_list

                heading_list.append(temp_dict)

            response["headingList"] = heading_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchHeadingDataAdminAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchHeadingCategoryListAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchHeadingCategoryListAPI: %s", str(data))

            website_group_name = data["websiteGroupName"]
            
            category_list = []
            category_objs = WebsiteGroup.objects.get(name=website_group_name).categories.all()
            for category_obj in category_objs:
                temp_dict = {}
                temp_dict["name"] = category_obj.name
                temp_dict["uuid"] = category_obj.uuid+"|"+category_obj.name
                category_list.append(temp_dict)
            
            response["categoryList"] = category_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchHeadingCategoryListAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class DeleteHeadingAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteHeadingAPI: %s", str(data))

            uuid = data["uuid"]
            
            DealsHubHeading.objects.get(uuid=uuid).delete()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteHeadingAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class CreateHeadingDataAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("CreateHeadingDataAPI: %s", str(data))

            website_group_name = data["websiteGroupName"]
            website_group_obj = WebsiteGroup.objects.get(name=website_group_name)

            heading_name = data["headingName"]
            
            uuid1 = str(uuid.uuid4())
            dealshub_heading_obj = DealsHubHeading.objects.create(website_group=website_group_obj, name=heading_name, uuid=uuid1)

            response["uuid"] = dealshub_heading_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateHeadingDataAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class SaveHeadingDataAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("SaveHeadingDataAPI: %s", str(data))

            data = data["dataObj"]

            uuid1 = data["uuid"]

            dealshub_heading_obj = DealsHubHeading.objects.get(uuid=uuid1)

            heading_name = data["headingName"]

            category_list = data["categoryList"]

            dealshub_heading_obj.categories.clear()            
            dealshub_heading_obj.name = heading_name
            for category in category_list:
                category_obj = Category.objects.get(uuid=category["key"].split("|")[0])
                dealshub_heading_obj.categories.add(category_obj)

            dealshub_heading_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveHeadingDataAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UploadImageHeadingAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UploadImageHeadingAPI: %s", str(data))

            uuid1 = data["uuid"]
            image = data["image"]

            if image=="" or image=="undefined" or image==None:
                return Response(data=response)

            dealshub_heading_obj = DealsHubHeading.objects.get(uuid=uuid1)

            image_obj = Image.objects.create(image=image)
            url = image_obj.image.url
            image_link_obj = ImageLink.objects.create(image=image_obj, uuid=str(uuid.uuid4()))
            dealshub_heading_obj.image_links.add(image_link_obj)
            dealshub_heading_obj.save()


            dataObj = {
                "uid": image_link_obj.uuid,
                "url": url,
                "httpLink": ""
            }
            response["dataObj"] = dataObj
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadImageHeadingAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UpdateImageHeadingLinkAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UpdateImageHeadingLinkAPI: %s", str(data))

            uuid = data["uuid"]
            http_link = data["httpLink"]

            image_link_obj = ImageLink.objects.get(uuid=uuid)
            image_link_obj.http_link = http_link
            image_link_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateImageHeadingLinkAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class DeleteImageHeadingAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteImageHeadingAPI: %s", str(data))

            uuid = data["uuid"]

            ImageLink.objects.get(uuid=uuid).delete()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteImageHeadingAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchUserWebsiteGroupAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchUserWebsiteGroupAPI: %s", str(data))

            website_group_name = ""
            try:
                website_group_name = OmnyCommUser.objects.get(username=request.user.username).website_group.name
            except Exception as e:
                pass
            
            response["websiteGroupName"] = website_group_name
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchUserWebsiteGroupAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchDealshubAdminSectionsAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchDealshubAdminSectionsAPI: %s", str(data))

            limit = data.get("limit", False)
            is_dealshub = data.get("isDealshub", False)

            website_group_name = data["websiteGroupName"]
            resolution = data.get("resolution", "low")

            section_objs = Section.objects.filter(website_group__name=website_group_name).order_by('order_index')

            if is_dealshub==True:
                section_objs = section_objs.filter(is_published=True)
                for section_obj in section_objs:
                    promotion = section_obj.promotion
                    if promotion is not None:
                        if utils.check_valid_promotion(datetime.now(),promotion):
                            section_objs = section_objs.filter(uuid=section_obj).delete()       
                                
            dealshub_admin_sections = []
            for section_obj in section_objs:
                temp_dict = {}
                temp_dict["orderIndex"] = section_obj.order_index
                temp_dict["type"] = "ProductListing"
                temp_dict["uuid"] = str(section_obj.uuid)
                temp_dict["name"] = str(section_obj.name)
                temp_dict["listingType"] = str(section_obj.listing_type)
                temp_dict["createdOn"] = str(datetime.datetime.strftime(section_obj.created_date, "%d %b, %Y"))
                temp_dict["modifiedOn"] = str(datetime.datetime.strftime(section_obj.modified_date, "%d %b, %Y"))
                temp_dict["createdBy"] = str(section_obj.created_by)
                temp_dict["modifiedBy"] = str(section_obj.modified_by)
                temp_dict["isPublished"] = section_obj.is_published

                section_promotion = section_obj.promotion
                if section_promotion is None:
                    temp_dict["is_promotional"] = False
                else:
                    temp_dict["is_promotional"] = True
                    temp_dict["start_time"] = str(section_promotion.start_time)
                    temp_dict["end_time"] = str(section_promotion.end_time)
                    temp_dict["promotion_tag"] = str(section_promotion.promotion_tag)

                temp_products = []

                section_products = section_obj.products.all()
                if limit==True:
                    if section_obj.listing_type=="Carousel":
                        section_products = section_products[:14]
                    elif section_obj.listing_type=="Grid Stack":
                        section_products = section_products[:14]

                for prod in section_products:
                    temp_dict2 = {}
                    prod.promotion = section_promotion
                    prod.save()

                    main_images_list = ImageBucket.objects.none()
                    try:
                        main_images_obj = MainImages.objects.get(product=prod, is_sourced=True)
                        main_images_list |= main_images_obj.main_images.all()
                        main_images_list = main_images_list.distinct()
                        images = create_response_images_main(main_images_list)
                        temp_dict2["thumbnailImageUrl"] = images[0]["midimage_url"]
                    except Exception as e:
                        temp_dict2["thumbnailImageUrl"] = Config.objects.all()[0].product_404_image.image.url

                    
                    temp_dict2["name"] = str(prod.product_name)
                    temp_dict2["displayId"] = str(prod.product_id)
                    temp_dict2["uuid"] = str(prod.uuid)

                    if is_dealshub==True:
                        temp_dict2["category"] = "" if prod.base_product.category==None else str(prod.base_product.category)
                        temp_dict2["currency"] = "AED"

                    product_promotion = prod.promotion
                    if product_promotion is not None:
                        temp_dict2["promotional_price"] = str(prod.promotional_price)  
                        temp_dict2["now_price"] = str(prod.now_price)
                        temp_dict2["was_price"] = str(prod.was_price)
                        temp_dict2["stock"] = str(prod.stock) 

                    temp_products.append(temp_dict2)
                temp_dict["products"] = temp_products

                dealshub_admin_sections.append(temp_dict)

            banner_objs = Banner.objects.filter(website_group__name=website_group_name).order_by('order_index')

            if is_dealshub==True:
                banner_objs = banner_objs.filter(is_published=True)

            for banner_obj in banner_objs:
                unit_banner_image_objs = UnitBannerImage.objects.filter(banner=banner_obj)

                if is_dealshub:
                   for unit_banner_image_obj in unit_banner_image_objs:
                       unit_banner_promotion = unit_banner_image_obj.promotion
                       if unit_banner_promotion is not None:
                           if utils.check_valid_promotion(datetime.now(),unit_banner_promotion):
                               unit_banner_image_objs.filter(uuid=unit_banner_image_objs).delete()

                banner_images = []
                temp_dict = {}
                temp_dict["orderIndex"] = banner_obj.order_index
                temp_dict["type"] = "Banner"
                temp_dict["uuid"] = banner_obj.uuid
                temp_dict["name"] = banner_obj.name
                temp_dict["bannerType"] = banner_obj.banner_type.name
                temp_dict["limit"] = banner_obj.banner_type.limit
                for unit_banner_image_obj in unit_banner_image_objs:
                    temp_dict2 = {}
                    temp_dict2["uid"] = unit_banner_image_obj.uuid
                    temp_dict2["httpLink"] = unit_banner_image_obj.http_link
                    temp_dict2["url"] = ""
                    if unit_banner_image_obj.image!=None:
                        if resolution=="low":
                            temp_dict2["url"] = unit_banner_image_obj.image.mid_image.url
                        else:
                            temp_dict2["url"] = unit_banner_image_obj.image.image.url

                    temp_dict2["mobileUrl"] = ""
                    if unit_banner_image_obj.mobile_image!=None:
                        if resolution=="low":
                            temp_dict2["mobileUrl"] = unit_banner_image_obj.mobile_image.mid_image.url
                        else:
                            temp_dict2["mobileUrl"] = unit_banner_image_obj.mobile_image.image.url

                    unit_banner_promotion = unit_banner_image_obj.promotion
                    if unit_banner_promotion is None:
                        temp_dict2["is_promotional"] = False
                    else:
                        temp_dict2["is_promotional"] = True
                        temp_dict2["start_time"] = str(unit_banner_promotion.start_time)
                        temp_dict2["end_time"] = str(unit_banner_promotion.end_time)
                        temp_dict2["promotion_tag"] = str(unit_banner_promotion.promotion_tag)


                    unit_banner_products = unit_banner_image_obj.products.all()

                    temp_products = []
                    for prod in unit_banner_products:
                        temp_dict3 = {}

                        main_images_list = ImageBucket.objects.none()
                        try:
                            main_images_obj = MainImages.objects.get(product=prod, is_sourced=True)
                            main_images_list |= main_images_obj.main_images.all()
                            main_images_list = main_images_list.distinct()
                            images = create_response_images_main(main_images_list)
                            temp_dict3["thumbnailImageUrl"] = images[0]["midimage_url"]
                        except Exception as e:
                            temp_dict3["thumbnailImageUrl"] = Config.objects.all()[0].product_404_image.image.url
                        
                        temp_dict3["name"] = str(prod.product_name)
                        temp_dict3["displayId"] = str(prod.product_id)
                        temp_dict3["uuid"] = str(prod.uuid)

                        product_promotion = prod.promotion
                        if product_promotion is not None:
                            temp_dict3["promotional_price"] = str(prod.promotional_price)  
                            temp_dict3["now_price"] = str(prod.now_price)
                            temp_dict3["was_price"] = str(prod.was_price)
                            temp_dict3["stock"] = str(prod.stock)

                        temp_products.append(temp_dict3)
                    temp_dict2["products"] = temp_products

                    banner_images.append(temp_dict2)

                
                temp_dict["bannerImages"] = banner_images
                temp_dict["isPublished"] = banner_obj.is_published

                dealshub_admin_sections.append(temp_dict)

            dealshub_admin_sections = sorted(dealshub_admin_sections, key = lambda i: i["orderIndex"]) 

            response["sections_list"] = dealshub_admin_sections
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchDealshubAdminSectionsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class SaveDealshubAdminSectionsOrderAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("SaveDealshubAdminSectionsOrderAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            dealshub_admin_sections = data["dealshubAdminSections"]

            cnt = 1
            for dealshub_admin_section in dealshub_admin_sections:
                if dealshub_admin_section["type"]=="Banner":
                    uuid = dealshub_admin_section["uuid"]
                    banner_obj = Banner.objects.get(uuid=uuid)
                    banner_obj.order_index = cnt
                    banner_obj.save()
                elif dealshub_admin_section["type"]=="ProductListing":
                    uuid = dealshub_admin_section["uuid"]
                    section_obj = Section.objects.get(uuid=uuid)
                    section_obj.order_index = cnt
                    section_obj.save()
                
                cnt += 1

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveDealshubAdminSectionsOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class SearchSectionProductsAutocompleteAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("SearchSectionProductsAutocompleteAPI: %s", str(data))

            search_string = data["searchString"]
            website_group_name = data["websiteGroupName"]
            website_group_obj = WebsiteGroup.objects.get(name=website_group_name)

            dealshub_products = DealsHubProduct.objects.filter(is_published=True, product__base_product__brand__in=website_group_obj.brands.all())

            dealshub_products = dealshub_products.filter(Q(product__base_product__seller_sku__icontains=search_string) | Q(product__product_name__icontains=search_string))[:10]

            dealshub_products_list = []
            for dealshub_product in dealshub_products:
                temp_dict = {}
                temp_dict["name"] = dealshub_product.product.product_name
                temp_dict["uuid"] = dealshub_product.product.uuid
                dealshub_products_list.append(temp_dict)

            response["productList"] = dealshub_products_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchSectionProductsAutocompleteAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class SearchProductsAutocompleteAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("SearchProductsAutocompleteAPI: %s", str(data))

            search_string = data["searchString"]
            website_group_name = data["websiteGroupName"]
            website_group_obj = WebsiteGroup.objects.get(name=website_group_name)

            category_key_list = DealsHubProduct.objects.filter(is_published=True, product__base_product__brand__in=website_group_obj.brands.all(), product__product_name__icontains=search_string).values('product__base_product__category').annotate(dcount=Count('product__base_product__category')).order_by('-dcount')[:5]

            category_list = []
            for category_key in category_key_list:
                try:
                    category_name = Category.objects.get(pk=category_key["product__base_product__category"]).name
                    category_list.append(category_name)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.warning("SearchProductsAutocompleteAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["categoryList"] = category_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchProductsAutocompleteAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchDealshubPriceAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchDealshubPriceAPI: %s", str(data))

            uuid1 = data["uuid"]
            company_code = data["companyCode"]

            price = 0
            was_price = 0
            is_stock_available = False
            if company_code in ["shopnesto"]:
                dealshub_product_obj = DealsHubProduct.objects.get(product__uuid=uuid1)
                # if str(dealshub_product_obj.product.base_product.brand).lower()=="geepas":
                #     price = fetch_prices_dealshub(uuid1, "1000")
                #     was_price = price
                # else:
                #     price = dealshub_product_obj.now_price
                #     was_price = dealshub_product_obj.was_price
                price = dealshub_product_obj.now_price
                was_price = dealshub_product_obj.was_price
                if dealshub_product_obj.stock>0:
                    is_stock_available = True
                
                is_promotional = False
                promotion = dealshub_product_obj.promotion
                if promotion is not None:
                    is_promotional = True
                    if utils.check_valid_promotion(datetime.now(),promotion):
                        price = dealshub_product_obj.promotional_price

            elif company_code in ["1000", "1070"]:
                price = fetch_prices_dealshub(uuid1, company_code)

            response["price"] = str(price)
            response["wasPrice"] = str(was_price)
            response["is_promotional"] = is_promotional
            response["isStockAvailable"] = is_stock_available
            response["uuid"] = uuid1
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchDealshubPriceAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchCompanyProfileDealshubAPI(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data

            logger.info("FetchCompanyProfileDealshubAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            website_group_obj = WebsiteGroup.objects.get(name=data["websiteGroupName"])

            company_data = {}
            company_data["name"] = website_group_obj.name
            company_data["contact_info"] = website_group_obj.contact_info
            company_data["address"] = website_group_obj.address
            company_data["primary_color"] = website_group_obj.primary_color
            company_data["secondary_color"] = website_group_obj.secondary_color
            company_data["facebook_link"] = website_group_obj.facebook_link
            company_data["twitter_link"] = website_group_obj.twitter_link
            company_data["instagram_link"] = website_group_obj.instagram_link
            company_data["youtube_link"] = website_group_obj.youtube_link

            company_data["logo_url"] = ""
            if website_group_obj.logo != None:
                company_data["logo_url"] = website_group_obj.logo.image.url


            response["company_data"] = company_data
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCompanyProfileDealshubAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddProductToSectionAPI(APIView):
    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("AddProductToSectionAPI: %s", str(data))

            section_uuid = data["sectionUuid"]
            product_uuid = data["productUuid"]

            section_obj = Section.objects.get(uuid=section_uuid)
            product_obj = Product.objects.get(uuid=product_uuid)

            is_promotional = section_obj.promotion is not None
            if is_promotional:
                product_obj.promotion = section_obj.promotion
                product_obj.save()
            
            temp_dict = {}    
            
            main_images_list = ImageBucket.objects.none()
            try:
                main_images_obj = MainImages.objects.get(product=product_obj, is_sourced=True)
                main_images_list |= main_images_obj.main_images.all()
                main_images_list = main_images_list.distinct()
                images = create_response_images_main(main_images_list)
                response["thumbnailImageUrl"] = images[0]["midimage_url"]
            except Exception as e:
                response["thumbnailImageUrl"] = ""

            
            response["name"] = str(product_obj.product_name)
            response["displayId"] = str(product_obj.product_id)

            section_obj.products.add(product_obj)
            section_obj.save()
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddProductToSectionAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchBulkProductInfoAPI(APIView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchBulkProductInfoAPI: %s", str(data))

            uuidList = json.loads(data["uuidList"])

            productInfo = {}
            for uuid in uuidList:
                product_obj = Product.objects.get(uuid=uuid)

                main_image_url = Config.objects.all()[0].product_404_image.image.url
                try:
                    main_images_obj = MainImages.objects.get(product=product_obj, is_sourced=True)
                    main_images_list = main_images_obj.main_images.all()
                    main_image_url = main_images_list.all()[0].image.mid_image.url
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchBulkProductInfoAPI: %s at %s", e, str(exc_tb.tb_lineno))

                temp_dict = {
                    "productName": product_obj.product_name,
                    "productImageUrl": main_image_url,
                    "sellerSku": product_obj.base_product.seller_sku,
                    "productId": product_obj.product_id
                }

                productInfo[uuid] = temp_dict
            
            response["productInfo"] = productInfo
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchBulkProductInfoAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchWebsiteGroupBrandsAPI(APIView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchWebsiteGroupBrandsAPI: %s", str(data))

            website_group_name = data["websiteGroupName"]
            website_group_obj = WebsiteGroup.objects.get(name=website_group_name)

            brand_objs = website_group_obj.brands.all()[:100]
            brand_list = []
            for brand_obj in brand_objs:
                temp_dict = {}
                temp_dict["name"] = brand_obj.name
                brand_list.append(temp_dict)

            response["brandList"] = brand_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchWebsiteGroupBrandsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class GenerateStockPriceReportAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("GenerateStockPriceReportAPI: %s", str(data))

            dp_objs = DealsHubProduct.objects.filter(product__base_product__brand__organization__name="nesto")

            generate_stock_price_report(dp_objs)        

            response["filepath"] = "https://"+SERVER_IP+"/files/csv/stock-price-report.xlsx"
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("GenerateStockPriceReportAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class AddProductToUnitBannerAPI(APIView):
    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("AddProductToUnitBannerAPI: %s", str(data))

            unit_banner_image_uuid = data["unitBannerImageUuid"]
            product_uuid = data["productUuid"]

            unit_banner_image_obj = UnitBannerImage.objects.get(uuid=unit_banner_image_uuid)
            product_obj = Product.objects.get(uuid=product_uuid)

            is_promotional = unit_banner_image_obj.promotion is not None
            if is_promotional:
                product_obj.promotion = unit_banner_image_obj.promotion
                product_obj.save()

            temp_dict = {}

            main_images_list = ImageBucket.objects.none()
            try:
                main_images_obj = MainImages.objects.get(product=product_obj, is_sourced=True)
                main_images_list |= main_images_obj.main_images.all()
                main_images_list = main_images_list.distinct()
                images = create_response_images_main(main_images_list)
                response["thumbnailImageUrl"] = images[0]["midimage_url"]
            except Exception as e:
                response["thumbnailImageUrl"] = ""

            
            response["name"] = str(product_obj.product_name)
            response["displayId"] = str(product_obj.product_id)

            unit_banner_image_obj.products.add(product_obj)
            unit_banner_image_obj.save()
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddProductToUnitBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class DeleteProductFromUnitBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteProductFromUnitBannerAPI: %s", str(data))

            unit_banner_image_uuid = data["unitBannerImageUuid"]
            product_uuid = data["productUuid"]

            unit_banner_image_obj = UnitBannerImage.objects.get(uuid=unit_banner_image_uuid)
            product_obj = Product.objects.get(uuid=product_uuid)
            product_obj.promotion = None
            product_obj.save()

            unit_banner_image_obj.products.remove(product_obj)
            unit_banner_image_obj.save()
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteProductFromUnitBannerAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchUnitBannerProductsAPI(APIView):

    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchUnitBannerProductsAPI: %s", str(data))

            unit_banner_image_uuid = data["unitBannerImageUuid"]
            
            unit_banner_image_obj = UnitBannerImage.objects.get(uuid=unit_banner_image_uuid)

            product_objs = unit_banner_image_obj.products.all()
            product_list = []
            for product_obj in product_objs:
                temp_dict = {}
                temp_dict["name"] = product_obj.product_name
                temp_dict["brand"] = str(product_obj.base_product.brand)
                temp_dict["price"] = "0"
                temp_dict["prevPrice"] = "0"
                temp_dict["currency"] = "AED"
                temp_dict["rating"] = "0"
                temp_dict["totalRatings"] = "0"
                temp_dict["uuid"] = str(product_obj.uuid)
                temp_dict["id"] = str(product_obj.uuid)
                main_images_list = ImageBucket.objects.none()
                main_images_objs = MainImages.objects.filter(product=product_obj)
                for main_images_obj in main_images_objs:
                    main_images_list |= main_images_obj.main_images.all()
                main_images_list = main_images_list.distinct()
                
                try:
                    temp_dict["heroImageUrl"] = main_images_list.all()[0].image.mid_image.url
                except Exception as e:
                    temp_dict["heroImageUrl"] = Config.objects.all()[0].product_404_image.image.url
                
                product_list.append(temp_dict)

            response["productList"] = product_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchUnitBannerProductsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        return Response(data=response)


class SearchCategoryAutocompleteAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("SearchCategoryAutocompleteAPI: %s", str(data))

            search_string = data["searchString"]

            category_objs = Category.objects.filter(name__icontains=search_string)[:10]

            category_list = []
            for category_obj in category_objs:
                temp_dict = {}
                temp_dict["name"] = category_obj.name
                temp_dict["uuid"] = category_obj.uuid
                category_list.append(temp_dict)

            response["categoryList"] = category_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchCategoryAutocompleteAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class AddCategoryToWebsiteGroupAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("AddCategoryToWebsiteGroupAPI: %s", str(data))

            category_uuid = data["categoryUuid"]
            website_group_name = data["websiteGroupName"]

            category_obj = Category.objects.get(uuid=category_uuid)
            website_group_obj = WebsiteGroup.objects.get(name=website_group_name)

            website_group_obj.categories.add(category_obj)
            website_group_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddCategoryToWebsiteGroupAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class RemoveCategoryFromWebsiteGroupAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("RemoveCategoryFromWebsiteGroupAPI: %s", str(data))

            category_uuid = data["categoryUuid"]
            website_group_name = data["websiteGroupName"]

            category_obj = Category.objects.get(uuid=category_uuid)
            website_group_obj = WebsiteGroup.objects.get(name=website_group_name)

            website_group_obj.categories.remove(category_obj)
            website_group_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("RemoveCategoryFromWebsiteGroupAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UpdateCategoryImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UpdateCategoryImageAPI: %s", str(data))

            uuid = data["uuid"]
            image = data["image"]

            category_obj = Category.objects.get(uuid=uuid)
            image_obj = Image.objects.create(image=image)
            category_obj.image = image_obj
            category_obj.save()

            response["imageUrl"] = image_obj.mid_image.url
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateCategoryImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class UpdateSuperCategoryImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UpdateSuperCategoryImageAPI: %s", str(data))

            uuid = data["uuid"]
            image = data["image"]

            super_category_obj = SuperCategory.objects.get(uuid=uuid)
            image_obj = Image.objects.create(image=image)
            super_category_obj.image = image_obj
            super_category_obj.save()

            response["imageUrl"] = image_obj.mid_image.url
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateSuperCategoryImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)

class UpdatePromotionalPrice(APIView):

    permision_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UpdatePromotionalPrice: %s", str(data))

            uuid = data["uuid"]
            price = data["price"]

            product = DealsHubProduct.objects.get(uuid=uuid)
            product.promotional_price = float(price)
            product.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdatePromotionalPrice: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)   


class RefreshStockAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("RefreshStockAPI: %s", str(data))

            uuid_list = json.loads(data["uuidList"])
            
            for uuid in uuid_list:
                dealshub_product_obj = DealsHubProduct.objects.get(product__uuid=uuid)
                brand = str(dealshub_product_obj.product.base_product.brand).lower()
                seller_sku = str(dealshub_product_obj.product.base_product.seller_sku)
                stock = 0
                if "wigme" in seller_sku.lower():
                    continue
                if brand=="geepas":
                    stock1 = fetch_refresh_stock(seller_sku, "1070", "TG01")
                    stock2 = fetch_refresh_stock(seller_sku, "1000", "AFS1")
                    stock = max(stock1, stock2)
                elif brand=="baby plus":
                    stock = fetch_refresh_stock(seller_sku, "5550", "AFS1")
                elif brand=="royalford":
                    stock = fetch_refresh_stock(seller_sku, "3000", "AFS1")
                elif brand=="krypton":
                    stock = fetch_refresh_stock(seller_sku, "2100", "TG01")
                elif brand=="olsenmark":
                    stock = fetch_refresh_stock(seller_sku, "1100", "AFS1")
                elif brand=="ken jardene":
                    stock = fetch_refresh_stock(seller_sku, "5550", "AFS1") # 
                elif brand=="younglife":
                    stock = fetch_refresh_stock(seller_sku, "5000", "AFS1")

                if stock > 10:
                    dealshub_product_obj.stock = 5
                else:
                    dealshub_product_obj.stock = 0

                dealshub_product_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("RefreshStockAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


CreateAdminCategory = CreateAdminCategoryAPI.as_view()

FetchAdminCategories = FetchAdminCategoriesAPI.as_view()

UpdateAdminCategory = UpdateAdminCategoryAPI.as_view()

DeleteAdminCategory = DeleteAdminCategoryAPI.as_view()

PublishAdminCategory = PublishAdminCategoryAPI.as_view()

UnPublishAdminCategory = UnPublishAdminCategoryAPI.as_view()

SectionBulkUpload = SectionBulkUploadAPI.as_view()


FetchBannerTypes = FetchBannerTypesAPI.as_view()

CreateBanner = CreateBannerAPI.as_view()

UpdateBannerName = UpdateBannerNameAPI.as_view()

FetchBanner = FetchBannerAPI.as_view()

DeleteBanner = DeleteBannerAPI.as_view()

PublishBanner = PublishBannerAPI.as_view()

UnPublishBanner = UnPublishBannerAPI.as_view()

UpdateLinkBanner = UpdateLinkBannerAPI.as_view()

AddBannerImage = AddBannerImageAPI.as_view()

UpdateBannerImage = UpdateBannerImageAPI.as_view()

DeleteBannerImage = DeleteBannerImageAPI.as_view()

DeleteUnitBanner = DeleteUnitBannerAPI.as_view()

PublishDealsHubProduct = PublishDealsHubProductAPI.as_view()

UnPublishDealsHubProduct = UnPublishDealsHubProductAPI.as_view()

PublishDealsHubProducts = PublishDealsHubProductsAPI.as_view()

UnPublishDealsHubProducts = UnPublishDealsHubProductsAPI.as_view()

DeleteProductFromSection = DeleteProductFromSectionAPI.as_view()


FetchHeadingData = FetchHeadingDataAPI.as_view()

FetchHeadingDataAdmin = FetchHeadingDataAdminAPI.as_view()

FetchHeadingCategoryList = FetchHeadingCategoryListAPI.as_view()

DeleteHeading = DeleteHeadingAPI.as_view()

CreateHeadingData = CreateHeadingDataAPI.as_view()

SaveHeadingData = SaveHeadingDataAPI.as_view()

UploadImageHeading = UploadImageHeadingAPI.as_view()

UpdateImageHeadingLink = UpdateImageHeadingLinkAPI.as_view()

DeleteImageHeading = DeleteImageHeadingAPI.as_view()


FetchUserWebsiteGroup = FetchUserWebsiteGroupAPI.as_view()

FetchDealshubAdminSections = FetchDealshubAdminSectionsAPI.as_view()

SaveDealshubAdminSectionsOrder = SaveDealshubAdminSectionsOrderAPI.as_view() 

SearchSectionProductsAutocomplete = SearchSectionProductsAutocompleteAPI.as_view()

SearchProductsAutocomplete = SearchProductsAutocompleteAPI.as_view()

FetchDealshubPrice = FetchDealshubPriceAPI.as_view()

FetchCompanyProfileDealshub = FetchCompanyProfileDealshubAPI.as_view()

AddProductToSection = AddProductToSectionAPI.as_view()

FetchBulkProductInfo = FetchBulkProductInfoAPI.as_view()

FetchWebsiteGroupBrands = FetchWebsiteGroupBrandsAPI.as_view()

GenerateStockPriceReport = GenerateStockPriceReportAPI.as_view()

AddProductToUnitBanner = AddProductToUnitBannerAPI.as_view()

DeleteProductFromUnitBanner = DeleteProductFromUnitBannerAPI.as_view()

FetchUnitBannerProducts = FetchUnitBannerProductsAPI.as_view()

SearchCategoryAutocomplete = SearchCategoryAutocompleteAPI.as_view()

AddCategoryToWebsiteGroup = AddCategoryToWebsiteGroupAPI.as_view()

RemoveCategoryFromWebsiteGroup = RemoveCategoryFromWebsiteGroupAPI.as_view()

UpdateCategoryImage = UpdateCategoryImageAPI.as_view()

UpdateSuperCategoryImage = UpdateSuperCategoryImageAPI.as_view()

RefreshStock = RefreshStockAPI.as_view()