# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

from WAMSApp.models import *
from WAMSApp.utils import *
from WAMSApp.constants import *
from dealshub.models import *
from dealshub.utils import *
from dealshub.views_dh import *

from django.shortcuts import HttpResponse, get_object_or_404
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.cache import cache

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import AllowAny

from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models import Count

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

            dealshub_product_obj = DealsHubProduct.objects.get(uuid=data["uuid"])
            product_obj = dealshub_product_obj.product
            base_product_obj = product_obj.base_product

            response["category"] = dealshub_product_obj.get_category()
            response["subCategory"] = dealshub_product_obj.get_sub_category()
            response["uuid"] = data["uuid"]
            response["name"] = dealshub_product_obj.get_name()
            response["price"] = dealshub_product_obj.get_actual_price()
            response["wasPrice"] = dealshub_product_obj.was_price
            response["currency"] = dealshub_product_obj.get_currency()
            response["warranty"] = dealshub_product_obj.get_warranty()
            response["is_cod_allowed"] = dealshub_product_obj.is_cod_allowed

            promotion_obj = dealshub_product_obj.promotion
            if promotion_obj is None:
                response["is_promotional"] = False
                response["start_time"] = None
                response["end_time"] = None
                response["promotion_tag"] = None
            else:
                response["is_promotional"] = True
                response["start_time"] = str(promotion_obj.start_time)[:19]
                response["end_time"] = str(promotion_obj.end_time)[:19]
                response["promotion_tag"] = str(promotion_obj.promotion_tag)

            response["isStockAvailable"] = False
            if dealshub_product_obj.stock>0:
                response["isStockAvailable"] = True

            response["productDispDetails"] = product_obj.product_description 
            try:
                specifications = json.loads(product_obj.dynamic_form_attributes)
                new_specifications = {}
                for key in specifications:
                    if specifications[key]["value"]!="":
                        new_specifications[key] = specifications[key]
                response["specifications"] = new_specifications
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
            main_images_objs = MainImages.objects.filter(product=product_obj, is_sourced=True)
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
            sub_images_objs = SubImages.objects.filter(product=product_obj, is_sourced=True)
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
                temp_image = {}
                temp_image["original"] = Config.objects.all()[0].product_404_image.image.url
                temp_image["thumbnail"] = Config.objects.all()[0].product_404_image.image.url
                image_list.append(temp_image)
                response["heroImageUrl"] = Config.objects.all()[0].product_404_image.image.url

            response["productImagesUrl"] = image_list


            location_group_obj = dealshub_product_obj.location_group

            similar_category_products = []
            category_obj = dealshub_product_obj.category
            brand_obj = dealshub_product_obj.product.base_product.brand

            dealshub_product_objs = DealsHubProduct.objects.filter(is_published=True, location_group=location_group_obj, category=category_obj).exclude(now_price=0).exclude(stock=0)
            similar_category_products = get_recommended_products(dealshub_product_objs)

            dealshub_product_objs = DealsHubProduct.objects.filter(is_published=True, location_group=location_group_obj, product__base_product__brand=brand_obj).exclude(now_price=0).exclude(stock=0)
            similar_brand_products = get_recommended_products(dealshub_product_objs)

            response["similar_category_products"] = similar_category_products
            response["similar_brand_products"] = similar_brand_products
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductDetailsAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)


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
            dealshub_product_objs = section_obj.products.all()
            dealshub_product_objs = dealshub_product_objs.exclude(now_price=0).exclude(stock=0)
            temp_dict = {}
            temp_dict["sectionName"] = section_obj.name
            temp_dict["productsArray"] = []

            page = int(data.get("page",1))
            paginator = Paginator(dealshub_product_objs, 20)
            dealshub_product_objs = paginator.page(page)

            for dealshub_product_obj in dealshub_product_objs:
                if dealshub_product_obj.get_actual_price()==0:
                    continue
                temp_dict2 = {}
                temp_dict2["name"] = dealshub_product_obj.get_name()
                temp_dict2["brand"] = dealshub_product_obj.get_brand()
                temp_dict2["now_price"] = dealshub_product_obj.now_price
                temp_dict2["was_price"] = dealshub_product_obj.was_price
                temp_dict2["promotional_price"] = dealshub_product_obj.promotional_price
                temp_dict2["stock"] = dealshub_product_obj.stock
                temp_dict2["isStockAvailable"] = dealshub_product_obj.stock>0
                temp_dict2["is_promotional"] = dealshub_product_obj.promotion!=None
                if dealshub_product_obj.promotion!=None:
                    temp_dict2["promotion_tag"] = dealshub_product_obj.promotion.promotion_tag
                else:
                    temp_dict2["promotion_tag"] = None
                temp_dict2["currency"] = dealshub_product_obj.get_currency()
                temp_dict2["uuid"] = dealshub_product_obj.uuid
                temp_dict2["id"] = dealshub_product_obj.uuid
                temp_dict2["heroImageUrl"] = dealshub_product_obj.get_display_image_url()

                temp_dict["productsArray"].append(temp_dict2)

            is_available = True
            
            if int(paginator.num_pages) == int(page):
                is_available = False

            response["is_available"] = is_available

            response['sectionData'] = temp_dict
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSectionProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


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

            website_group_obj = WebsiteGroup.objects.get(name=website_group_name)

            super_category_objs = website_group_obj.super_categories.all()

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


class FetchHeadingCategoriesAPI(APIView):
    
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchHeadingCategoriesAPI: %s", str(data))
            website_group_name = data["websiteGroupName"]

            website_group_obj = WebsiteGroup.objects.get(name=website_group_name)

            category_objs = website_group_obj.categories.all()

            category_list = []
            for category_obj in category_objs:
                temp_dict = {}
                temp_dict["name"] = category_obj.name
                temp_dict["uuid"] = category_obj.uuid
                temp_dict["imageUrl"] = ""
                if category_obj.image!=None:
                    temp_dict["imageUrl"] = category_obj.image.mid_image.url
                sub_category_list = []
                sub_category_objs = SubCategory.objects.filter(category=category_obj)
                for sub_category_obj in sub_category_objs:
                    temp_dict2 = {}
                    temp_dict2["name"] = sub_category_obj.name
                    temp_dict2["uuid"] = sub_category_obj.uuid
                    sub_category_list.append(temp_dict2)
                temp_dict["subCategoryList"] = sub_category_list
                category_list.append(temp_dict)

            response['categoryList'] = category_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchHeadingCategoriesAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


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

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group

            page = data.get("page", 1)
            search = {}            

            available_dealshub_products = DealsHubProduct.objects.filter(location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all(), is_published=True).exclude(now_price=0).exclude(stock=0)
            if brand_name!="":
                available_dealshub_products = available_dealshub_products.filter(product__base_product__brand__name=brand_name)

            if super_category_name!="":
                available_dealshub_products = available_dealshub_products.filter(category__super_category__name=super_category_name)

            if category_name!="ALL" and category_name!="":
                available_dealshub_products = available_dealshub_products.filter(category__name=category_name)

            if subcategory_name!="":
                available_dealshub_products = available_dealshub_products.filter(sub_category__name=subcategory_name)
            
            if product_name!="":
                available_dealshub_products = available_dealshub_products.filter(Q(product__product_name__icontains=product_name) | Q(product__base_product__brand__name__icontains=product_name) | Q(product__base_product__seller_sku__icontains=product_name))

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
            dealshub_product_objs = paginator.page(page)            
            products = []
            for dealshub_product_obj in dealshub_product_objs:
                try:
                    if dealshub_product_obj.get_actual_price()==0:
                        continue
                    temp_dict = {}
                    temp_dict["name"] = dealshub_product_obj.get_name()
                    temp_dict["brand"] = dealshub_product_obj.get_brand()
                    temp_dict["now_price"] = dealshub_product_obj.now_price
                    temp_dict["was_price"] = dealshub_product_obj.was_price
                    temp_dict["promotional_price"] = dealshub_product_obj.promotional_price
                    temp_dict["stock"] = dealshub_product_obj.stock
                    temp_dict["isStockAvailable"] = dealshub_product_obj.stock>0
                    temp_dict["is_promotional"] = dealshub_product_obj.promotion!=None
                    if dealshub_product_obj.promotion!=None:
                        temp_dict["promotion_tag"] = dealshub_product_obj.promotion.promotion_tag
                    else:
                        temp_dict["promotion_tag"] = None
                    temp_dict["currency"] = dealshub_product_obj.get_currency()
                    temp_dict["uuid"] = dealshub_product_obj.uuid
                    temp_dict["id"] = dealshub_product_obj.uuid
                    temp_dict["heroImageUrl"] = dealshub_product_obj.get_display_image_url()
                    
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


            sub_category_list2 = []
            try:
                category_obj = website_group_obj.categories.get(name=category_name)
                sub_category_objs = SubCategory.objects.filter(category=category_obj)
                for sub_category_obj in sub_category_objs:
                    temp_dict2 = {}
                    temp_dict2["name"] = sub_category_obj.name
                    temp_dict2["uuid"] = sub_category_obj.uuid
                    sub_category_list2.append(temp_dict2)

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
                    if DealsHubProduct.objects.filter(is_published=True, category=category_obj).exclude(now_price=0).exclude(stock=0).exists()==False:
                        continue
                    temp_dict = {}
                    temp_dict["name"] = category_obj.name
                    temp_dict["uuid"] = category_obj.uuid
                    sub_category_objs = SubCategory.objects.filter(category=category_obj)
                    sub_category_list = []
                    for sub_category_obj in sub_category_objs:
                        if DealsHubProduct.objects.filter(is_published=True, sub_category=sub_category_obj, location_group=location_group_obj).exclude(now_price=0).exclude(stock=0).exists()==False:
                            continue
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
            response["subCategoryList"] = sub_category_list2

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
            logger.error("SearchAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class CreateAdminCategoryAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("CreateAdminCategoryAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            data = data["sectionData"]

            name = data["name"]
            listing_type = data["listingType"]
            products = data["products"]
            
            order_index = Banner.objects.filter(location_group=location_group_obj).count()+Section.objects.filter(location_group=location_group_obj).count()+1

            section_obj = Section.objects.create(location_group=location_group_obj, name=name, listing_type=listing_type, order_index=order_index)
            for product in products:
                dealshub_product_obj = DealsHubProduct.objects.get(uuid=product)
                section_obj.products.add(dealshub_product_obj)

            section_obj.save()

            response['uuid'] = str(section_obj.uuid)
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateAdminCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class UpdateAdminCategoryAPI(APIView):

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
            
            section_obj = Section.objects.get(uuid=uuid)

            promotion_obj = section_obj.promotion
            if is_promotional:
                promotion = data["promotion"]
                start_date = convert_to_datetime(promotion["start_date"])
                end_date = convert_to_datetime(promotion["end_date"])
                promotional_tag = promotion["promotional_tag"]
                if promotion_obj==None:
                    promotion_obj = Promotion.objects.create(promotion_tag=promotional_tag, start_time=start_date, end_time=end_date)
                else:
                    promotion_obj.promotion_tag = promotional_tag
                    promotion_obj.start_time = start_date
                    promotion_obj.end_time = end_date
                    promotion_obj.save()
            else:
                promotion_obj = None

            section_obj.name = name
            section_obj.listing_type = listing_type
            section_obj.is_published = is_published
            section_obj.modified_by = None
            section_obj.promotion = promotion_obj
            section_obj.products.clear()
            for product in products:
                dealshub_product_obj = DealsHubProduct.objects.get(uuid=product)
                dealshub_product_obj.promotion = promotion_obj
                dealshub_product_obj.save()
                section_obj.products.add(dealshub_product_obj)

            section_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateAdminCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class DeleteAdminCategoryAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("DeleteAdminCategoryAPI: %s", str(data))

            uuid = data["uuid"]
            
            section_obj = Section.objects.get(uuid=uuid)
            dealshub_product_objs = section_obj.products.all()

            for dealshub_product_obj in dealshub_product_objs:
                dealshub_product_obj.promotion = None
                dealshub_product_obj.save()

            location_group_uuid = section_obj.location_group.uuid
            cache.set(location_group_uuid, "has_expired")
                
            section_obj.delete()
            
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteAdminCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class PublishAdminCategoryAPI(APIView):

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

            location_group_uuid = section_obj.location_group.uuid
            cache.set(location_group_uuid, "has_expired")
            
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PublishAdminCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class UnPublishAdminCategoryAPI(APIView):

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

            location_group_uuid = section_obj.location_group.uuid
            cache.set(location_group_uuid, "has_expired")
            
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UnPublishAdminCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class SectionBulkUploadAPI(APIView):
    
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
            location_group_obj = section_obj.location_group

            products = []
            unsuccessful_count = 0
            for i in range(rows):
                try:
                    product_id = dfs.iloc[i][0]
                    dealshub_product_obj = DealsHubProduct.objects.get(location_group=location_group_obj, product__product_id=product_id)
                    section_obj.products.add(dealshub_product_obj)

                    temp_dict = {}
                    temp_dict["thumbnailImageUrl"] = dealshub_product_obj.get_display_image_url()
                    temp_dict["name"] = dealshub_product_obj.get_name()
                    temp_dict["displayId"] = dealshub_product_obj.get_product_id()
                    temp_dict["uuid"] = dealshub_product_obj.uuid
                    products.append(temp_dict)

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

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group

            banner_type_objs = BannerType.objects.filter(website_group=website_group_obj)

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
            location_group_uuid = data["locationGroupUuid"]
            name = data.get("name", "")

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            banner_type_obj = BannerType.objects.get(name=banner_type, website_group=location_group_obj.website_group)

            if name=="":
                name = banner_type_obj.display_name

            order_index = Banner.objects.filter(location_group=location_group_obj).count()+Section.objects.filter(location_group=location_group_obj).count()+1

            banner_obj = Banner.objects.create(name=name, location_group=location_group_obj, order_index=order_index, banner_type=banner_type_obj)
            
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

            banner_obj = Banner.objects.get(uuid=uuid)
            image_obj = Image.objects.create(image=banner_image)
            unit_banner_image_obj = UnitBannerImage.objects.create(image=image_obj, banner=banner_obj)

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
            dealshub_product_objs = unit_banner_obj.products.all()

            for dealshub_product_obj in dealshub_product_objs:
                dealshub_product_obj.promotion = None
                dealshub_product_obj.save()

            location_group_uuid = unit_banner_obj.banner.location_group.uuid
            cache.set(location_group_uuid, "has_expired")

            unit_banner_obj.delete()
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteUnitBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class DeleteBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("DeleteBannerAPI: %s", str(data))

            uuid = data["uuid"]
            banner_obj = Banner.objects.get(uuid=uuid)

            unit_banner_objs = UnitBannerImage.objects.filter(banner=banner_obj)

            for unit_banner_obj in unit_banner_objs:
                dealshub_product_objs = unit_banner_obj.products.all()
                for dealshub_product_obj in dealshub_product_objs:
                    dealshub_product_obj.promotion = None
                    dealshub_product_obj.save()

            location_group_uuid = banner_obj.location_group.uuid
            cache.set(location_group_uuid, "has_expired")

            banner_obj.delete()
            
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

            location_group_uuid = banner_obj.location_group.uuid
            cache.set(location_group_uuid, "has_expired")
            
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

            location_group_uuid = banner_obj.location_group.uuid
            cache.set(location_group_uuid, "has_expired")
            
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

            uuid = data["product_uuid"]
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=uuid)
            dealshub_product_obj.is_published = True
            dealshub_product_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PublishDealsHubProductAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class UnPublishDealsHubProductAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UnPublishDealsHubProductAPI: %s", str(data))

            uuid = data["product_uuid"]
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=uuid)
            dealshub_product_obj.is_published = False
            dealshub_product_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UnPublishDealsHubProductAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class ActivateCODDealsHubProductAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("ActivateCODDealsHubProductAPI: %s", str(data))

            uuid = data["product_uuid"]
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=uuid)
            dealshub_product_obj.is_cod_allowed = True
            dealshub_product_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ActivateCODDealsHubProductAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class DeactivateCODDealsHubProductAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("DeactivateCODDealsHubProductAPI: %s", str(data))

            uuid = data["product_uuid"]
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=uuid)
            dealshub_product_obj.is_cod_allowed = False
            dealshub_product_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeactivateCODDealsHubProductAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
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
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=product_uuid)

            dealshub_product_obj.promotion = None
            dealshub_product_obj.save()
            
            section_obj.products.remove(dealshub_product_obj)
            section_obj.save()
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteProductFromSectionAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class PublishDealsHubProductsAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("PublishDealsHubProductsAPI: %s", str(data))

            product_uuid_list = data["product_uuid_list"]
            for uuid in product_uuid_list:
                dealshub_product_obj = DealsHubProduct.objects.get(uuid=uuid)
                dealshub_product_obj.is_published = True
                dealshub_product_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PublishDealsHubProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class UnPublishDealsHubProductsAPI(APIView):
    
    def post(self, request, *args, **kwargs):
        
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UnPublishDealsHubProductsAPI: %s", str(data))

            product_uuid_list = data["product_uuid_list"]
            for uuid in product_uuid_list:
                dealshub_product_obj = DealsHubProduct.objects.get(uuid=uuid)
                dealshub_product_obj.is_published = False
                dealshub_product_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UnPublishDealsHubProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
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

            location_group_uuid = data["locationGroupUuid"]
            resolution = data.get("resolution", "low")

            if is_dealshub==True:
                cached_value = cache.get(location_group_uuid, "has_expired")
                if cached_value!="has_expired":
                    response["sections_list"] = json.loads(cached_value)
                    response['status'] = 200
                    return Response(data=response)


            section_objs = Section.objects.filter(location_group__uuid=location_group_uuid).order_by('order_index')

            if is_dealshub==True:
                section_objs = section_objs.filter(is_published=True)
                valid_section_objs = Section.objects.none()
                for section_obj in section_objs:
                    promotion_obj = section_obj.promotion
                    if promotion_obj is not None:
                        if check_valid_promotion(promotion_obj):
                            valid_section_objs |= Section.objects.filter(pk=section_obj.pk)
                    else:
                        valid_section_objs |= Section.objects.filter(pk=section_obj.pk)
                section_objs = valid_section_objs
                                
            dealshub_admin_sections = []
            for section_obj in section_objs:
                if is_dealshub==True and section_obj.products.exclude(now_price=0).exclude(stock=0).exists()==False:
                    continue
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

                promotion_obj = section_obj.promotion
                if promotion_obj is None:
                    temp_dict["is_promotional"] = False
                    temp_dict["start_time"] = None
                    temp_dict["end_time"] = None
                    temp_dict["promotion_tag"] = None
                else:
                    temp_dict["is_promotional"] = True
                    temp_dict["start_time"] = str(promotion_obj.start_time)[:19]
                    temp_dict["end_time"] = str(promotion_obj.end_time)[:19]
                    temp_dict["promotion_tag"] = str(promotion_obj.promotion_tag)

                hovering_banner_img = section_obj.hovering_banner_image
                if hovering_banner_img is not None:
                    temp_dict["hoveringBannerUuid"] = section_obj.hovering_banner_image.pk
                    if resolution=="low":
                        temp_dict["hoveringBannerUrl"] = section_obj.hovering_banner_image.mid_image.url
                    else:
                        temp_dict["hoveringBannerUrl"] = section_obj.hovering_banner_image.image.url
                else:
                    temp_dict["hoveringBannerUrl"] = ""
                    temp_dict["hoveringBannerUuid"] = ""

                temp_products = []

                section_products = section_obj.products.all()
                if is_dealshub==True:
                    section_products = section_products.exclude(now_price=0).exclude(stock=0)

                if limit==True:
                    if section_obj.listing_type=="Carousel":
                        section_products = section_products[:14]
                    elif section_obj.listing_type=="Grid Stack":
                        section_products = section_products[:14]

                for dealshub_product_obj in section_products:
                    if dealshub_product_obj.now_price==0:
                        continue
                    temp_dict2 = {}

                    temp_dict2["thumbnailImageUrl"] = dealshub_product_obj.get_display_image_url()
                    temp_dict2["name"] = dealshub_product_obj.get_name()
                    temp_dict2["sellerSku"] = dealshub_product_obj.get_seller_sku()
                    temp_dict2["brand"] = dealshub_product_obj.get_brand()
                    temp_dict2["displayId"] = dealshub_product_obj.get_product_id()
                    temp_dict2["uuid"] = dealshub_product_obj.uuid

                    if is_dealshub==True:
                        temp_dict2["category"] = dealshub_product_obj.get_category()
                        temp_dict2["currency"] = dealshub_product_obj.get_currency()

                    promotion_obj = dealshub_product_obj.promotion
                    
                    temp_dict2["promotional_price"] = dealshub_product_obj.promotional_price
                    temp_dict2["now_price"] = dealshub_product_obj.now_price
                    temp_dict2["was_price"] = dealshub_product_obj.was_price
                    temp_dict2["stock"] = dealshub_product_obj.stock 
                    if dealshub_product_obj.stock>0:
                        temp_dict2["isStockAvailable"] = True
                    else:
                        temp_dict2["isStockAvailable"] = False

                    temp_products.append(temp_dict2)
                temp_dict["products"] = temp_products

                dealshub_admin_sections.append(temp_dict)

            banner_objs = Banner.objects.filter(location_group__uuid=location_group_uuid).order_by('order_index')

            if is_dealshub==True:
                banner_objs = banner_objs.filter(is_published=True)

            for banner_obj in banner_objs:
                unit_banner_image_objs = UnitBannerImage.objects.filter(banner=banner_obj)

                if is_dealshub:
                    valid_unit_banner_image_objs = UnitBannerImage.objects.none()
                    for unit_banner_image_obj in unit_banner_image_objs:
                        promotion_obj = unit_banner_image_obj.promotion
                        if promotion_obj is not None:
                            if check_valid_promotion(promotion_obj):
                                valid_unit_banner_image_objs |= UnitBannerImage.objects.filter(pk=unit_banner_image_obj.pk)
                        else:
                            valid_unit_banner_image_objs |= UnitBannerImage.objects.filter(pk=unit_banner_image_obj.pk)
                    unit_banner_image_objs = valid_unit_banner_image_objs

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

                    hovering_banner_img = unit_banner_image_obj.hovering_banner_image
                    if hovering_banner_img is not None:
                        temp_dict2["hoveringBannerUuid"] = unit_banner_image_obj.hovering_banner_image.pk
                        if resolution=="low":
                            temp_dict2["hoveringBannerUrl"] = unit_banner_image_obj.hovering_banner_image.mid_image.url
                        else:
                            temp_dict2["hoveringBannerUrl"] = unit_banner_image_obj.hovering_banner_image.image.url
                    else:
                        temp_dict2["hoveringBannerUrl"] = ""
                        temp_dict2["hoveringBannerUuid"] = ""

                    promotion_obj = unit_banner_image_obj.promotion
                    if promotion_obj is None:
                        temp_dict2["is_promotional"] = False
                        temp_dict2["start_time"] = None
                        temp_dict2["end_time"] = None
                        temp_dict2["promotion_tag"] = None
                    else:
                        temp_dict2["is_promotional"] = True
                        temp_dict2["start_time"] = str(promotion_obj.start_time)[:19]
                        temp_dict2["end_time"] = str(promotion_obj.end_time)[:19]
                        temp_dict2["promotion_tag"] = str(promotion_obj.promotion_tag)


                    unit_banner_products = unit_banner_image_obj.products.all()
                    if is_dealshub==True:
                        unit_banner_products = unit_banner_products.exclude(now_price=0).exclude(stock=0)

                    if is_dealshub==False :
                        temp_products = []
                        for dealshub_product_obj in unit_banner_products:
                            if dealshub_product_obj.now_price==0:
                                continue
                            temp_dict3 = {}

                            temp_dict3["thumbnailImageUrl"] = dealshub_product_obj.get_display_image_url()
                            temp_dict3["name"] = dealshub_product_obj.get_name()
                            temp_dict3["displayId"] = dealshub_product_obj.get_product_id()
                            temp_dict3["sellerSku"] = dealshub_product_obj.get_seller_sku()
                            temp_dict3["brand"] = dealshub_product_obj.get_brand()
                            temp_dict3["uuid"] = dealshub_product_obj.uuid

                            promotion_obj = dealshub_product_obj.promotion
                            
                            temp_dict3["promotional_price"] = dealshub_product_obj.promotional_price
                            temp_dict3["now_price"] = dealshub_product_obj.now_price
                            temp_dict3["was_price"] = dealshub_product_obj.was_price
                            temp_dict3["stock"] = dealshub_product_obj.stock
                            if dealshub_product_obj.stock>0:
                                temp_dict3["isStockAvailable"] = True
                            else:
                                temp_dict3["isStockAvailable"] = False

                            temp_products.append(temp_dict3)    # No need to Send all
                        temp_dict2["products"] = temp_products
                    
                    temp_dict2["has_products"] = unit_banner_products.count()>0
                    banner_images.append(temp_dict2)

                temp_dict["bannerImages"] = banner_images
                temp_dict["isPublished"] = banner_obj.is_published

                dealshub_admin_sections.append(temp_dict)

            dealshub_admin_sections = sorted(dealshub_admin_sections, key = lambda i: i["orderIndex"])

            if is_dealshub==True:
                cache.set(location_group_uuid, json.dumps(dealshub_admin_sections))

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
            location_group_uuid = data["locationGroupUuid"]
            section_uuid = data["sectionUuid"]
            type = data["type"]

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group

            dealshub_product_objs = DealsHubProduct.objects.filter(is_published=True, location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all()).exclude(now_price=0).exclude(stock=0)

            dealshub_product_objs = dealshub_product_objs.filter(Q(product__base_product__seller_sku__icontains=search_string) | Q(product__product_name__icontains=search_string))

            if type=="ProductListing":
                section_obj = Section.objects.get(uuid=section_uuid)
                dealshub_product_objs = dealshub_product_objs.exclude(id__in=section_obj.products.all())[:10]
            elif type=="Banner":
                unit_banner_image_obj = UnitBannerImage.objects.get(uuid=section_uuid)
                dealshub_product_objs = dealshub_product_objs.exclude(id__in=unit_banner_image_obj.products.all())[:10]
            else:
                dealshub_products = dealshub_products[:10]


            dealshub_product_list = []
            for dealshub_product_obj in dealshub_product_objs:
                temp_dict = {}
                temp_dict["name"] = dealshub_product_obj.get_name()
                temp_dict["uuid"] = dealshub_product_obj.uuid
                dealshub_product_list.append(temp_dict)

            response["productList"] = dealshub_product_list
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
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group

            category_key_list = DealsHubProduct.objects.filter(is_published=True, product__base_product__brand__in=website_group_obj.brands.all()).filter(Q(product__product_name__icontains=search_string) | Q(product__base_product__seller_sku__icontains=search_string) | Q(product__base_product__brand__name__icontains=search_string)).exclude(now_price=0).exclude(stock=0).values('category').annotate(dcount=Count('category')).order_by('-dcount')[:5]

            category_list = []
            for category_key in category_key_list:
                try:
                    category_name = Category.objects.get(pk=category_key["category"]).name
                    category_list.append(category_name)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.warning("SearchProductsAutocompleteAPI: %s at %s", e, str(exc_tb.tb_lineno))

            category_list = list(set(category_list))

            response["categoryList"] = category_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchProductsAutocompleteAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class SearchProductsAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("SearchProductsAPI: %s", str(data))

            search_string = data["searchString"]
            location_group_uuid = data["locationGroupUuid"]

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group

            dealshub_product_objs = DealsHubProduct.objects.filter(is_published=True, location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all()).exclude(now_price=0).exclude(stock=0)

            dealshub_product_objs = dealshub_product_objs.filter(Q(product__base_product__seller_sku__icontains=search_string) | Q(product__product_name__icontains=search_string))

            dealshub_product_objs = dealshub_product_objs[:10]

            dealshub_product_list = []
            for dealshub_product_obj in dealshub_product_objs:
                temp_dict = {}
                temp_dict["name"] = dealshub_product_obj.get_name()
                temp_dict["uuid"] = dealshub_product_obj.uuid
                dealshub_product_list.append(temp_dict)

            response["productList"] = dealshub_product_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))

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
            is_promotional = False
            promotional_tag = None
            
            dealshub_product_obj = DealsHubProduct.objects.get(product__uuid=uuid1)
            price = get_actual_price(dealshub_product_obj)
            is_promotional = dealshub_product_obj.promotion!=None
            was_price = dealshub_product_obj.was_price
            if dealshub_product_obj.stock>0:
                is_stock_available = True
            if is_promotional:
                promotional_tag = dealshub_product_obj.promotion.promotion_tag

            response["price"] = str(price)
            response["wasPrice"] = str(was_price)
            response["is_promotional"] = is_promotional
            response["isStockAvailable"] = is_stock_available
            response["promotional_tag"] = promotional_tag
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

            location_group_objs = LocationGroup.objects.filter(website_group=website_group_obj)
            location_info = []
            for location_group_obj in location_group_objs:
                temp_dict = {}
                temp_dict["name"] = location_group_obj.location.name
                temp_dict["uuid"] = location_group_obj.uuid
                temp_dict["currency"] = location_group_obj.location.currency
                temp_dict["delivery_fee"] = location_group_obj.delivery_fee
                temp_dict["free_delivery_threshold"] = location_group_obj.free_delivery_threshold
                temp_dict["cod_charge"] = location_group_obj.cod_charge
                location_info.append(temp_dict)


            company_data = {}
            company_data["name"] = website_group_obj.name
            company_data["contact_info"] = website_group_obj.contact_info
            company_data["email_info"] = website_group_obj.email_info
            company_data["address"] = website_group_obj.address
            company_data["primary_color"] = website_group_obj.primary_color
            company_data["secondary_color"] = website_group_obj.secondary_color
            company_data["navbar_text_color"] = website_group_obj.navbar_text_color
            company_data["facebook_link"] = website_group_obj.facebook_link
            company_data["twitter_link"] = website_group_obj.twitter_link
            company_data["instagram_link"] = website_group_obj.instagram_link
            company_data["youtube_link"] = website_group_obj.youtube_link
            company_data["linkedin_link"] = website_group_obj.linkedin_link
            company_data["crunchbase_link"] = website_group_obj.crunchbase_link


            company_data["logo_url"] = ""
            if website_group_obj.logo != None:
                company_data["logo_url"] = website_group_obj.logo.image.url

            company_data["footer_logo_url"] = ""
            if website_group_obj.footer_logo != None:
                company_data["footer_logo_url"] = website_group_obj.footer_logo.image.url

            response["company_data"] = company_data
            response["location_info"] = location_info
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCompanyProfileDealshubAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddProductToSectionAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddProductToSectionAPI: %s", str(data))

            section_uuid = data["sectionUuid"]
            product_uuid = data["productUuid"]

            section_obj = Section.objects.get(uuid=section_uuid)
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=product_uuid)

            dealshub_product_obj.promotion = section_obj.promotion
            dealshub_product_obj.save()
            
            response["thumbnailImageUrl"] = dealshub_product_obj.get_display_image_url()
            response["name"] = dealshub_product_obj.get_name()
            response["displayId"] = dealshub_product_obj.get_product_id()
            response["sellerSku"] = dealshub_product_obj.get_seller_sku()
            response["brand"] = dealshub_product_obj.get_brand()

            response["now_price"] = str(dealshub_product_obj.now_price)
            response["was_price"] = str(dealshub_product_obj.was_price)
            response["promotional_price"] = str(dealshub_product_obj.promotional_price)
            response["stock"] = str(dealshub_product_obj.stock)

            section_obj.products.add(dealshub_product_obj)
            section_obj.save()
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddProductToSectionAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchWebsiteGroupBrandsAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)
    
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


class AddProductToUnitBannerAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddProductToUnitBannerAPI: %s", str(data))

            unit_banner_image_uuid = data["unitBannerImageUuid"]
            product_uuid = data["productUuid"]

            unit_banner_image_obj = UnitBannerImage.objects.get(uuid=unit_banner_image_uuid)
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=product_uuid)

            dealshub_product_obj.promotion = unit_banner_image_obj.promotion
            dealshub_product_obj.save()


            response["thumbnailImageUrl"] = dealshub_product_obj.get_display_image_url()            
            response["name"] = dealshub_product_obj.get_name()
            response["displayId"] = dealshub_product_obj.get_product_id()
            response["sellerSku"] = dealshub_product_obj.get_seller_sku()
            response["brand"] = dealshub_product_obj.get_brand()

            response["now_price"] = str(dealshub_product_obj.now_price)
            response["was_price"] = str(dealshub_product_obj.was_price)
            response["promotional_price"] = str(dealshub_product_obj.promotional_price)
            response["stock"] = str(dealshub_product_obj.stock)

            unit_banner_image_obj.products.add(dealshub_product_obj)
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
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=product_uuid)
            dealshub_product_obj.promotion = None
            dealshub_product_obj.save()

            unit_banner_image_obj.products.remove(dealshub_product_obj)
            unit_banner_image_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteProductFromUnitBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchUnitBannerProductsAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchUnitBannerProductsAPI: %s", str(data))

            unit_banner_image_uuid = data["unitBannerImageUuid"]
            
            unit_banner_image_obj = UnitBannerImage.objects.get(uuid=unit_banner_image_uuid)

            dealshub_product_objs = unit_banner_image_obj.products.all()
            dealshub_product_objs = dealshub_product_objs.exclude(now_price=0).exclude(stock=0)

            page = int(data.get('page', 1))
            paginator = Paginator(dealshub_product_objs, 20)
            dealshub_product_objs = paginator.page(page)

            product_list = []
            for dealshub_product_obj in dealshub_product_objs:
                if dealshub_product_obj.get_actual_price()==0:
                    continue
                temp_dict = {}
                temp_dict["name"] = dealshub_product_obj.get_name()
                temp_dict["brand"] = dealshub_product_obj.get_brand()
                temp_dict["now_price"] = dealshub_product_obj.now_price
                temp_dict["was_price"] = dealshub_product_obj.was_price
                temp_dict["promotional_price"] = dealshub_product_obj.promotional_price
                temp_dict["stock"] = dealshub_product_obj.stock
                temp_dict["isStockAvailable"] = dealshub_product_obj.stock>0
                temp_dict["is_promotional"] = dealshub_product_obj.promotion!=None
                if dealshub_product_obj.promotion!=None:
                    temp_dict["promotion_tag"] = dealshub_product_obj.promotion.promotion_tag
                else:
                    temp_dict["promotion_tag"] = None
                temp_dict["currency"] = dealshub_product_obj.get_currency()
                temp_dict["uuid"] = dealshub_product_obj.uuid
                temp_dict["id"] = dealshub_product_obj.uuid
                temp_dict["heroImageUrl"] = dealshub_product_obj.get_display_image_url()
                
                product_list.append(temp_dict)

            is_available = True
            if paginator.num_pages == page:
                is_available = False

            response["is_available"] = is_available
            response["productList"] = product_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchUnitBannerProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddUnitBannerHoveringImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("AddUnitBannerHoveringImageAPI: %s", str(data))

            uuid = data["uuid"]
            hovering_banner_image = data["image"]

            unit_banner_image_obj = UnitBannerImage.objects.get(uuid=uuid)
            image_obj = Image.objects.create(image=hovering_banner_image)
            unit_banner_image_obj.hovering_banner_image = image_obj
            unit_banner_image_obj.save()

            response['uuid'] = image_obj.pk
            response['url'] = image_obj.image.url
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddUnitBannerHoveringImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchUnitBannerHoveringImageAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchUnitBannerHoveringImageAPI: %s", str(data))
            uuid = data["uuid"]

            unit_banner_image_obj = UnitBannerImage.objects.get(uuid=uuid)

            if unit_banner_image_obj.hovering_banner_image is not None:
                response["url"] = unit_banner_image_obj.hovering_banner_image.image.url
            else:
                response["url"] = ""

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchUnitBannerHoveringImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class AddSectionHoveringImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("AddSectionHoveringImageAPI: %s", str(data))

            uuid = data["uuid"]
            hovering_banner_image = data["image"]

            section_obj = Section.objects.get(uuid=uuid)
            image_obj = Image.objects.create(image=hovering_banner_image)
            section_obj.hovering_banner_image = image_obj
            section_obj.save()

            response['uuid'] = image_obj.pk
            response['url'] = image_obj.image.url
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddSectionHoveringImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchSectionHoveringImageAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchSectionHoveringImageAPI: %s", str(data))
            uuid = data["uuid"]

            section_obj = Section.objects.get(uuid=uuid)

            if section_obj.hovering_banner_image is not None:
                response["url"] = section_obj.hovering_banner_image.image.url
            else:
                response["url"] = ""

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSectionHoveringImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class DeleteHoveringImageAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteHoveringImageAPI: %s", str(data))

            uuid = data["uuid"]

            Image.objects.get(pk=uuid).delete()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteHoveringImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
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


class UpdateUnitBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateUnitBannerAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            uuid = data["uuid"]
            is_promotional = data["is_promotional"]
            
            unit_banner_obj = UnitBannerImage.objects.get(uuid=uuid)

            promotion_obj = unit_banner_obj.promotion
            if is_promotional:
                promotion = data["promotion"]
                start_date = convert_to_datetime(promotion["start_date"])
                end_date = convert_to_datetime(promotion["end_date"])
                promotional_tag = promotion["promotional_tag"]
                if promotion_obj==None:
                    promotion_obj = Promotion.objects.create(promotion_tag=promotional_tag, start_time=start_date, end_time=end_date)
                else:
                    promotion_obj.promotion_tag = promotional_tag
                    promotion_obj.start_time = start_date
                    promotion_obj.end_time = end_date
                    promotion_obj.save()
            else:
                promotion_obj = None
            
            
            unit_banner_obj.promotion = promotion_obj
            dealshub_product_objs = unit_banner_obj.products.all()
            for dealshub_product_obj in dealshub_product_objs:
                dealshub_product_obj.promotion = promotion_obj
                dealshub_product_obj.save()

            unit_banner_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateUnitBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class CreateVoucherAPI(APIView):
    
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("CreateVoucherAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            voucher_code = data.get("voucher_code", "VOUCHER")
            voucher_type = data.get("voucher_type", "FD")
            percent_discount = 0
            fixed_discount = 0
            maximum_discount = 0
            minimum_purchase_amount = 0
            customer_usage_limit = 1
            maximum_usage_limit = 0

            voucher_obj = Voucher.objects.create(voucher_code=voucher_code,
                                                 voucher_type=voucher_type,
                                                 percent_discount=percent_discount,
                                                 fixed_discount=fixed_discount,
                                                 maximum_discount=maximum_discount, 
                                                 minimum_purchase_amount=minimum_purchase_amount,
                                                 customer_usage_limit=customer_usage_limit, 
                                                 maximum_usage_limit=maximum_usage_limit,
                                                 location_group=location_group_obj)

            response["uuid"] = str(voucher_obj.uuid)
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateVoucherAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UpdateVoucherAPI(APIView):
    
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UpdateVoucherAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            voucher_uuid = data["voucher_uuid"]
            voucher_obj = Voucher.objects.get(uuid=voucher_uuid)

            voucher_obj.voucher_code = data["voucher_code"]
            voucher_obj.start_time = data["start_time"]
            voucher_obj.end_time = data["end_time"]
            voucher_obj.voucher_type = data["voucher_type"]

            if voucher_obj.voucher_type == "PD":
                voucher_obj.percent_discount = float(data["percent_discount"])
            elif voucher_obj.voucher_type == "FD":
                voucher_obj.fixed_discount = float(data["fixed_discount"])

            voucher_obj.maximum_discount = float(data["maximum_discount"])
            voucher_obj.minimum_purchase_amount = float(data["minimum_purchase_amount"])
            voucher_obj.customer_usage_limit = int(data["customer_usage_limit"])
            voucher_obj.maximum_usage_limit = int(data["maximum_usage_limit"])
            voucher_obj.save()
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateVoucherAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchVouchersAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchVouchersAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            voucher_objs = Voucher.objects.filter(is_deleted=False, location_group__uuid=location_group_uuid)
            
            voucher_list = []
            for voucher_obj in voucher_objs:
                temp_dict = {}
                temp_dict["uuid"] = voucher_obj.uuid
                temp_dict["is_published"] = voucher_obj.is_published
                temp_dict["voucher_code"] = voucher_obj.voucher_code
                temp_dict["start_time"] = voucher_obj.start_time
                temp_dict["end_time"] = voucher_obj.end_time
                temp_dict["voucher_type"] = voucher_obj.voucher_type

                if voucher_obj.voucher_type == "PD":
                    temp_dict["percent_discount"] = float(voucher_obj.percent_discount)
                elif voucher_obj.voucher_type == "FD":
                    temp_dict["fixed_discount"] = float(voucher_obj.fixed_discount)

                temp_dict["maximum_discount"] = float(voucher_obj.maximum_discount)
                temp_dict["minimum_purchase_amount"] = float(voucher_obj.minimum_purchase_amount)
                temp_dict["customer_usage_limit"] = int(voucher_obj.customer_usage_limit)
                temp_dict["maximum_usage_limit"] = int(voucher_obj.maximum_usage_limit)

                voucher_list.append(temp_dict)

            response["voucher_list"] = voucher_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchVouchersAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DeleteVoucherAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteVoucherAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            uuid = data["voucher_uuid"]
            voucher_obj = Voucher.objects.get(uuid=uuid)
            voucher_obj.is_deleted = True
            voucher_obj.save()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteVoucherAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class PublishVoucherAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("PublishVoucherAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            uuid = data["voucher_uuid"]
            voucher_obj = Voucher.objects.get(uuid=uuid)
            voucher_obj.is_published = True
            voucher_obj.save()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PublishVoucherAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UnPublishVoucherAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UnPublishVoucherAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            uuid = data["voucher_uuid"]
            voucher_obj = Voucher.objects.get(uuid=uuid)
            voucher_obj.is_published = False
            voucher_obj.save()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UnPublishVoucherAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


FetchProductDetails = FetchProductDetailsAPI.as_view()

FetchSectionProducts = FetchSectionProductsAPI.as_view()

FetchSuperCategories = FetchSuperCategoriesAPI.as_view()

FetchHeadingCategories = FetchHeadingCategoriesAPI.as_view()

Search = SearchAPI.as_view()

CreateAdminCategory = CreateAdminCategoryAPI.as_view()

UpdateAdminCategory = UpdateAdminCategoryAPI.as_view()

DeleteAdminCategory = DeleteAdminCategoryAPI.as_view()

PublishAdminCategory = PublishAdminCategoryAPI.as_view()

UnPublishAdminCategory = UnPublishAdminCategoryAPI.as_view()

SectionBulkUpload = SectionBulkUploadAPI.as_view()

FetchBannerTypes = FetchBannerTypesAPI.as_view()

CreateBanner = CreateBannerAPI.as_view()

UpdateBannerName = UpdateBannerNameAPI.as_view()

DeleteBanner = DeleteBannerAPI.as_view()

PublishBanner = PublishBannerAPI.as_view()

UnPublishBanner = UnPublishBannerAPI.as_view()

AddBannerImage = AddBannerImageAPI.as_view()

UpdateBannerImage = UpdateBannerImageAPI.as_view()

DeleteBannerImage = DeleteBannerImageAPI.as_view()

DeleteUnitBanner = DeleteUnitBannerAPI.as_view()

PublishDealsHubProduct = PublishDealsHubProductAPI.as_view()

UnPublishDealsHubProduct = UnPublishDealsHubProductAPI.as_view()

PublishDealsHubProducts = PublishDealsHubProductsAPI.as_view()

UnPublishDealsHubProducts = UnPublishDealsHubProductsAPI.as_view()

ActivateCODDealsHubProduct = ActivateCODDealsHubProductAPI.as_view()

DeactivateCODDealsHubProduct = DeactivateCODDealsHubProductAPI.as_view()

DeleteProductFromSection = DeleteProductFromSectionAPI.as_view()

FetchDealshubAdminSections = FetchDealshubAdminSectionsAPI.as_view()

SaveDealshubAdminSectionsOrder = SaveDealshubAdminSectionsOrderAPI.as_view() 

SearchSectionProductsAutocomplete = SearchSectionProductsAutocompleteAPI.as_view()

SearchProductsAutocomplete = SearchProductsAutocompleteAPI.as_view()

SearchProducts = SearchProductsAPI.as_view()

FetchDealshubPrice = FetchDealshubPriceAPI.as_view()

FetchCompanyProfileDealshub = FetchCompanyProfileDealshubAPI.as_view()

AddProductToSection = AddProductToSectionAPI.as_view()

FetchWebsiteGroupBrands = FetchWebsiteGroupBrandsAPI.as_view()

AddProductToUnitBanner = AddProductToUnitBannerAPI.as_view()

DeleteProductFromUnitBanner = DeleteProductFromUnitBannerAPI.as_view()

FetchUnitBannerProducts = FetchUnitBannerProductsAPI.as_view()

AddUnitBannerHoveringImage = AddUnitBannerHoveringImageAPI.as_view()

FetchUnitBannerHoveringImage = FetchUnitBannerHoveringImageAPI.as_view()

AddSectionHoveringImage = AddSectionHoveringImageAPI.as_view()

FetchSectionHoveringImage = FetchSectionHoveringImageAPI.as_view()

DeleteHoveringImage = DeleteHoveringImageAPI.as_view()

UpdateSuperCategoryImage = UpdateSuperCategoryImageAPI.as_view()

UpdateUnitBanner = UpdateUnitBannerAPI.as_view()

CreateVoucher = CreateVoucherAPI.as_view()

UpdateVoucher = UpdateVoucherAPI.as_view()

FetchVouchers = FetchVouchersAPI.as_view()

DeleteVoucher = DeleteVoucherAPI.as_view()

PublishVoucher = PublishVoucherAPI.as_view()

UnPublishVoucher = UnPublishVoucherAPI.as_view()