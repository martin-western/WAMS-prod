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
from dealshub.network_global_integration import *

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

            language_code = data.get("language","en")
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=data["uuid"])
            product_obj = dealshub_product_obj.product
            base_product_obj = product_obj.base_product

            response["brand"] = dealshub_product_obj.get_brand(language_code)
            response["superCategory"] = dealshub_product_obj.get_super_category(language_code)
            response["category"] = dealshub_product_obj.get_category(language_code)
            response["subCategory"] = dealshub_product_obj.get_sub_category(language_code)
            response["uuid"] = data["uuid"]
            response["name"] = dealshub_product_obj.get_name(language_code)
            response["stock"] = dealshub_product_obj.stock
            response["allowedQty"] = dealshub_product_obj.get_allowed_qty()
            response["price"] = dealshub_product_obj.get_actual_price()
            response["wasPrice"] = dealshub_product_obj.was_price
            response["currency"] = dealshub_product_obj.get_currency()
            response["warranty"] = dealshub_product_obj.get_warranty()

            response["is_new_arrival"] = dealshub_product_obj.is_new_arrival
            response["is_on_sale"] = dealshub_product_obj.is_on_sale

            response["dimensions"] = dealshub_product_obj.get_dimensions()
            response["color"] = dealshub_product_obj.get_color()
            if dealshub_product_obj.get_weight()==0.0:
                response["weight"] = "NA"
            else:
                response["weight"] = str(dealshub_product_obj.get_weight())+" kg"
            response["size"] = dealshub_product_obj.get_size()
            response["capacity"] = dealshub_product_obj.get_capacity()
            response["target_age_range"] = dealshub_product_obj.get_target_age_range()
            response["material"] = dealshub_product_obj.get_material()
            response["sellerSku"] = dealshub_product_obj.get_seller_sku()
            response["faqs"] = dealshub_product_obj.get_faqs()
            response["how_to_use"] = dealshub_product_obj.get_how_to_use()


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

            try:
                variant_list = []
                dealshub_product_objs = DealsHubProduct.objects.filter(location_group=dealshub_product_obj.location_group, product__base_product=product_obj.base_product, is_published=True).exclude(now_price=0).exclude(stock=0)
                for dealshub_product_obj in dealshub_product_objs:
                    temp_dict = {}
                    temp_dict["product_name"] = dealshub_product_obj.get_name(language_code) 
                    temp_dict["image_url"] = dealshub_product_obj.get_display_image_url()
                    temp_dict["uuid"] = dealshub_product_obj.uuid
                    variant_list.append(temp_dict)

                response["variant_list"] = variant_list
            except Exception as e:
                response["variant_list"] = []

            response["isStockAvailable"] = False
            if dealshub_product_obj.stock>0:
                response["isStockAvailable"] = True

            #response["productDispDetails"] = product_obj.product_description
            response["productDispDetails"] = dealshub_product_obj.get_description(language_code)
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
                if language_code == "ar":
                    response["features"] = json.loads(product_obj.pfl_product_features_ar)
            except Exception as e:
                response["features"] = []


            image_list = []

            cached_url_list = cache.get("image_url_list_"+product_obj.uuid, "has_expired")
            if cached_url_list!="has_expired":
                image_list = json.loads(cached_url_list)
            else:
                lifestyle_image_objs = product_obj.lifestyle_images.all()
                for lifestyle_image_obj in lifestyle_image_objs:
                    try:
                        temp_image = {}
                        temp_image["high-res"] = lifestyle_image_obj.image.url
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
                        temp_image["high-res"] = main_image["main_url"]
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
                        temp_image["high-res"] = sub_image["main_url"]
                        temp_image["original"] = sub_image["midimage_url"]
                        temp_image["thumbnail"] = sub_image["thumbnail_url"]
                        image_list.append(temp_image)
                    except Exception as e:
                        pass
                cache.set("image_url_list_"+product_obj.uuid, json.dumps(image_list))
            
            try:
                response["heroImageUrl"] = image_list[0]["original"]
            except Exception as e:
                temp_image = {}
                temp_image["high-res"] = Config.objects.all()[0].product_404_image.image.url
                temp_image["original"] = Config.objects.all()[0].product_404_image.image.url
                temp_image["thumbnail"] = Config.objects.all()[0].product_404_image.image.url
                image_list.append(temp_image)
                response["heroImageUrl"] = Config.objects.all()[0].product_404_image.image.url

            response["productImagesUrl"] = image_list

            try:
                page_description = dealshub_product_obj.page_description
                seo_title = dealshub_product_obj.seo_title
                seo_keywords = dealshub_product_obj.seo_keywords
                seo_description = dealshub_product_obj.seo_description
                response["page_description"] = page_description
                response["seo_title"] = seo_title
                response["seo_keywords"] = seo_description
                response["seo_description"] = seo_description
            except Exception as e:
                response["page_description"] = ""
                response["seo_title"] = ""
                response["seo_keywords"] = ""
                response["seo_description"] = ""


            location_group_obj = dealshub_product_obj.location_group

            # similar_category_products = []
            # category_obj = dealshub_product_obj.category
            # brand_obj = dealshub_product_obj.product.base_product.brand

            # dealshub_product_objs = DealsHubProduct.objects.filter(is_published=True, location_group=location_group_obj, category=category_obj, product__base_product__brand__in=dealshub_product_obj.location_group.website_group.brands.all(), product__no_of_images_for_filter__gte=1).exclude(now_price=0).exclude(stock=0)
            # similar_category_products = get_recommended_products(dealshub_product_objs)

            # dealshub_product_objs = DealsHubProduct.objects.filter(is_published=True, location_group=location_group_obj, product__base_product__brand=brand_obj, product__no_of_images_for_filter__gte=1).exclude(now_price=0).exclude(stock=0)
            # similar_brand_products = get_recommended_products(dealshub_product_objs)

            # response["similar_category_products"] = similar_category_products
            # response["similar_brand_products"] = similar_brand_products
            response["similar_category_products"] = []
            response["similar_brand_products"] = []
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductDetailsAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchSimilarProductsAPI(APIView):
    
    authentication_classes = (CsrfExemptSessionAuthentication,) 
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchSimilarProductsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            language_code = data.get("language","en")

            dealshub_product_obj = DealsHubProduct.objects.get(uuid=data["uuid"])

            location_group_obj = dealshub_product_obj.location_group

            similar_category_products = []
            category_obj = dealshub_product_obj.category
            brand_obj = dealshub_product_obj.product.base_product.brand

            dealshub_product_objs = DealsHubProduct.objects.filter(is_published=True, location_group=location_group_obj, category=category_obj, product__base_product__brand__in=dealshub_product_obj.location_group.website_group.brands.all(), product__no_of_images_for_filter__gte=1).exclude(now_price=0).exclude(stock=0)
            similar_category_products = get_recommended_products(dealshub_product_objs,language_code)

            dealshub_product_objs = DealsHubProduct.objects.filter(is_published=True, location_group=location_group_obj, product__base_product__brand=brand_obj, product__no_of_images_for_filter__gte=1).exclude(now_price=0).exclude(stock=0)
            similar_brand_products = get_recommended_products(dealshub_product_objs,language_code)

            response["similar_category_products"] = similar_category_products
            response["similar_brand_products"] = similar_brand_products
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSimilarProductsAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchOnSaleProductsAPI(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
    
        response = {}
        response["status"] = 500
        try:
            data = request.data
            logger.info("FetchOnSaleProductsAPI: %s", str(data))
            language_code = data.get("language","en")

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group
            
            dealshub_product_objs = DealsHubProduct.objects.filter(location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all(), is_published=True, is_on_sale=True).exclude(now_price=0).exclude(stock=0).prefetch_related('promotion')

            page = int(data.get("page",1))
            paginator = Paginator(dealshub_product_objs, 50)
            dealshub_product_objs = paginator.page(page)

            products = []
            for dealshub_product_obj in dealshub_product_objs:
                if dealshub_product_obj.get_actual_price()==0:
                    continue
                
                temp_dict2 = {}
                temp_dict2["name"] = dealshub_product_obj.get_name(language_code)
                temp_dict2["brand"] = dealshub_product_obj.get_brand(language_code)
                temp_dict2["now_price"] = dealshub_product_obj.now_price
                temp_dict2["was_price"] = dealshub_product_obj.was_price
                temp_dict2["promotional_price"] = dealshub_product_obj.promotional_price
                temp_dict2["stock"] = dealshub_product_obj.stock
                temp_dict2["allowedQty"] = dealshub_product_obj.get_allowed_qty()
                temp_dict2["isStockAvailable"] = dealshub_product_obj.stock>0
                temp_dict2["is_promotional"] = dealshub_product_obj.promotion!=None
                if dealshub_product_obj.promotion!=None:
                    temp_dict2["promotion_tag"] = dealshub_product_obj.promotion.promotion_tag
                else:
                    temp_dict2["promotion_tag"] = None
                temp_dict2["currency"] = dealshub_product_obj.get_currency()
                temp_dict2["uuid"] = dealshub_product_obj.uuid
                temp_dict2["link"] = dealshub_product_obj.url
                temp_dict2["id"] = dealshub_product_obj.uuid
                temp_dict2["heroImageUrl"] = dealshub_product_obj.get_display_image_url()
                products.append(temp_dict2)
            
            is_available = True
            
            if int(paginator.num_pages) == int(page):
                is_available = False

            response["is_available"] = is_available
            response["totalPages"] = paginator.num_pages
            response["products"] = products
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOnSaleProductsAPI: %s at %s", e, str(exc_tb.tb_lineno)) 

        return Response(data=response)


class FetchNewArrivalProductsAPI(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response["status"] = 500
        try:
            data = request.data
            logger.info("FetchNewArrivalProductsAPI: %s", str(data))
            language_code = data.get("language","en")

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group
            
            dealshub_product_objs = DealsHubProduct.objects.filter(location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all(), is_published=True, is_new_arrival=True).exclude(now_price=0).exclude(stock=0).order_by('-product__created_date').prefetch_related('promotion')

            page = int(data.get("page",1))
            paginator = Paginator(dealshub_product_objs, 50)
            dealshub_product_objs = paginator.page(page)

            products = []
            for dealshub_product_obj in dealshub_product_objs:
                if dealshub_product_obj.get_actual_price()==0:
                    continue
                
                temp_dict2 = {}
                temp_dict2["name"] = dealshub_product_obj.get_name(language_code)
                temp_dict2["brand"] = dealshub_product_obj.get_brand(language_code)
                temp_dict2["now_price"] = dealshub_product_obj.now_price
                temp_dict2["was_price"] = dealshub_product_obj.was_price
                temp_dict2["promotional_price"] = dealshub_product_obj.promotional_price
                temp_dict2["stock"] = dealshub_product_obj.stock
                temp_dict2["allowedQty"] = dealshub_product_obj.get_allowed_qty()
                temp_dict2["isStockAvailable"] = dealshub_product_obj.stock>0
                temp_dict2["is_new_arrival"] = dealshub_product_obj.is_new_arrival
                temp_dict2["is_on_sale"] = dealshub_product_obj.is_on_sale
                temp_dict2["is_promotional"] = dealshub_product_obj.promotion!=None
                if dealshub_product_obj.promotion!=None:
                    temp_dict2["promotion_tag"] = dealshub_product_obj.promotion.promotion_tag
                else:
                    temp_dict2["promotion_tag"] = None
                temp_dict2["currency"] = dealshub_product_obj.get_currency()
                temp_dict2["uuid"] = dealshub_product_obj.uuid
                temp_dict2["id"] = dealshub_product_obj.uuid
                temp_dict2["heroImageUrl"] = dealshub_product_obj.get_display_image_url()

                products.append(temp_dict2)
            
            is_available = True
            
            if int(paginator.num_pages) == int(page):
                is_available = False

            response["is_available"] = is_available
            response["totalPages"] = paginator.num_pages
            response["products"] = products
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchNewArrivalProductsAPI: %s at %s", e, str(exc_tb.tb_lineno)) 

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
            language_code = data.get("language","en")

            uuid = data["sectionUuid"]
            section_obj = Section.objects.get(uuid=uuid)
            
            custom_product_section_objs = CustomProductSection.objects.filter(section=section_obj, product__is_published=True)
            custom_product_section_objs = custom_product_section_objs.exclude(product__now_price=0).exclude(product__stock=0)
            dealshub_product_uuid_list = list(custom_product_section_objs.order_by('order_index').values_list("product__uuid", flat=True).distinct())
            dealshub_product_objs = DealsHubProduct.objects.filter(uuid__in=dealshub_product_uuid_list)            
            dealshub_product_objs = list(dealshub_product_objs)
            dealshub_product_objs.sort(key=lambda t: dealshub_product_uuid_list.index(t.uuid))

            temp_dict = {}
            temp_dict["sectionName"] = section_obj.name
            if section_obj.get_promo_slider_image(language_code)!=None:
                temp_dict["promoSliderImage"] = section_obj.get_promo_slider_image(language_code).image.url
            temp_dict["productsArray"] = []

            page = int(data.get("page",1))
            paginator = Paginator(dealshub_product_objs, 50)
            dealshub_product_objs = paginator.page(page)

            for dealshub_product_obj in dealshub_product_objs:
                if dealshub_product_obj.get_actual_price()==0:
                    continue
                temp_dict2 = {}
                temp_dict2["name"] = dealshub_product_obj.get_name(language_code)
                temp_dict2["brand"] = dealshub_product_obj.get_brand(language_code)
                temp_dict2["now_price"] = dealshub_product_obj.now_price
                temp_dict2["was_price"] = dealshub_product_obj.was_price
                temp_dict2["promotional_price"] = dealshub_product_obj.promotional_price
                temp_dict2["stock"] = dealshub_product_obj.stock
                temp_dict2["is_new_arrival"] = dealshub_product_obj.is_new_arrival
                temp_dict2["is_on_sale"] = dealshub_product_obj.is_on_sale
                temp_dict2["allowedQty"] = dealshub_product_obj.get_allowed_qty()
                temp_dict2["isStockAvailable"] = dealshub_product_obj.stock>0
                temp_dict2["is_promotional"] = dealshub_product_obj.promotion!=None
                if dealshub_product_obj.promotion!=None:
                    temp_dict2["promotion_tag"] = dealshub_product_obj.promotion.promotion_tag
                else:
                    temp_dict2["promotion_tag"] = None
                temp_dict2["currency"] = dealshub_product_obj.get_currency()
                temp_dict2["uuid"] = dealshub_product_obj.uuid
                temp_dict2["link"] = dealshub_product_obj.url
                temp_dict2["id"] = dealshub_product_obj.uuid
                temp_dict2["heroImageUrl"] = dealshub_product_obj.get_display_image_url()

                temp_dict["productsArray"].append(temp_dict2)

            is_available = True
            
            if int(paginator.num_pages) == int(page):
                is_available = False

            response["is_available"] = is_available
            response["totalPages"] = paginator.num_pages

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
            language_code = data.get("language","en")
            logger.info("FetchSuperCategoriesAPI: %s", str(data))
            website_group_name = data["websiteGroupName"]

            cached_value = cache.get("sc-list-"+website_group_name+"-"+language_code, "has_expired")
            if cached_value!="has_expired":
                response["superCategoryList"] = json.loads(cached_value)
                response['status'] = 200
                return Response(data=response)

            website_group_obj = WebsiteGroup.objects.get(name=website_group_name)

            super_category_objs = website_group_obj.super_categories.all()

            super_category_list = []
            for super_category_obj in super_category_objs:
                temp_dict = {}
                temp_dict["name"] = super_category_obj.get_name(language_code)
                temp_dict["name_en"] = super_category_obj.get_name("en")
                temp_dict["uuid"] = super_category_obj.uuid
                temp_dict["imageUrl"] = ""
                if super_category_obj.image!=None:
                    temp_dict["imageUrl"] = super_category_obj.image.thumbnail.url
                category_list = []
                category_objs = Category.objects.filter(super_category=super_category_obj)[:30]
                for category_obj in category_objs:
                    temp_dict2 = {}
                    temp_dict2["category_name"] = category_obj.get_name(language_code)
                    temp_dict2["category_name_en"] = category_obj.get_name("en")
                    category_list.append(temp_dict2)
                temp_dict["category_list"] = category_list
                super_category_list.append(temp_dict)

            cache.set("sc-list-"+website_group_name+"-"+language_code, json.dumps(super_category_list))

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
            language_code = data.get("language","en")
            logger.info("FetchHeadingCategoriesAPI: %s", str(data))
            website_group_name = data["websiteGroupName"]

            website_group_obj = WebsiteGroup.objects.get(name=website_group_name)

            category_objs = website_group_obj.categories.all()

            category_list = []
            for category_obj in category_objs:
                temp_dict = {}
                temp_dict["name"] = category_obj.get_name(language_code)
                temp_dict["uuid"] = category_obj.uuid
                temp_dict["imageUrl"] = ""
                if category_obj.image!=None:
                    temp_dict["imageUrl"] = category_obj.image.mid_image.url
                sub_category_list = []
                sub_category_objs = SubCategory.objects.filter(category=category_obj)
                for sub_category_obj in sub_category_objs:
                    temp_dict2 = {}
                    temp_dict2["name"] = sub_category_obj.get_name(language_code)
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
            language_code = data.get("language","en")
            
            product_name = data.get("name", "").strip()
            super_category_name = data.get("superCategory", "").strip()
            category_name = data.get("category", "").strip()
            subcategory_name = data.get("subcategory", "").strip()
            brand_name = data.get("brand", "").strip()

            page_description = ""
            seo_title = ""
            seo_keywords = ""
            seo_description = ""

            try:
                if subcategory_name!="":
                    sub_category_obj = SubCategory.objects.filter(Q(name=subcategory_name) | Q(name_ar=subcategory_name))[0]
                    page_description = sub_category_obj.page_description
                    seo_title = sub_category_obj.seo_title
                    seo_keywords = sub_category_obj.seo_keywords
                    seo_description = sub_category_obj.seo_description
                elif category_name!="":
                    category_obj = Category.objects.filter(Q(name=category_name) | Q(name_ar=category_name))[0]
                    page_description = category_obj.page_description
                    seo_title = category_obj.seo_title
                    seo_keywords = category_obj.seo_keywords
                    seo_description = category_obj.seo_description
                elif super_category_name!="":
                    super_category_obj = SuperCategory.objects.filter(Q(name=super_category_name) | Q(name_ar=super_category_name))[0]
                    page_description = super_category_obj.page_description
                    seo_title = super_category_obj.seo_title
                    seo_keywords = super_category_obj.seo_keywords
                    seo_description = super_category_obj.seo_description
                elif brand_name!="":
                    brand_obj = Brand.objects.get((Q(name=brand_name) | Q(name_ar=brand_name)), organization__name="WIG")
                    page_description = brand_obj.page_description
                    seo_title = brand_obj.seo_title
                    seo_keywords = brand_obj.seo_keywords
                    seo_description = brand_obj.seo_description
                response["page_description"] = page_description
                response["seo_title"] = seo_title
                response["seo_keywords"] = seo_keywords
                response["seo_description"] = seo_description
            except Exception as e:
                response["page_description"] = ""
                response["seo_title"] = ""
                response["seo_keywords"] = ""
                response["seo_description"] = ""

            # filter_list = data.get("filters", "[]")
            # filter_list = json.loads(filter_list)

            brand_filter = data.get("brand_filter", [])
            sort_filter = data.get("sort_filter", {})

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group

            page = data.get("page", 1)
            search = {}

            if product_name!="":
                SearchKeyword.objects.create(word=product_name, location_group=location_group_obj)

            available_dealshub_products = DealsHubProduct.objects.filter(location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all(), is_published=True).exclude(now_price=0).exclude(stock=0)

            # Filters
            if sort_filter.get("price", "")=="high-to-low":
                available_dealshub_products = available_dealshub_products.order_by('-now_price')
            if sort_filter.get("price", "")=="low-to-high":
                available_dealshub_products = available_dealshub_products.order_by('now_price')

            if brand_name!="":
                available_dealshub_products = available_dealshub_products.filter(Q(product__base_product__brand__name=brand_name) | Q(product__base_product__brand__name_ar=brand_name))

            if super_category_name!="":
                available_dealshub_products = available_dealshub_products.filter(Q(category__super_category__name=super_category_name) | Q(category__super_category__name_ar=super_category_name))

            if category_name!="ALL" and category_name!="":
                available_dealshub_products = available_dealshub_products.filter(Q(category__name=category_name) | Q(category__name_ar=category_name))

            if subcategory_name!="":
                available_dealshub_products = available_dealshub_products.filter(Q(sub_category__name=subcategory_name) | Q(sub_category__name_ar=subcategory_name))
            
            if product_name!="":
                if available_dealshub_products.filter(Q(product__product_name__icontains=product_name) | Q(product_name_ar__icontains=product_name) | Q(product__base_product__brand__name__icontains=product_name) | Q(product__base_product__brand__name_ar__icontains=product_name) | Q(product__base_product__seller_sku__icontains=product_name)).exists():
                    available_dealshub_products = available_dealshub_products = available_dealshub_products.filter(Q(product_name_ar__icontains=product_name) | Q(product__product_name__icontains=product_name) | Q(product__base_product__brand__name__icontains=product_name)  | Q(product__base_product__brand__name_ar__icontains=product_name) | Q(product__base_product__seller_sku__icontains=product_name))
                else:
                    search_tags = product_name.split(" ")
                    target_brand = None
                    for search_tag in search_tags:
                        if website_group_obj.brands.filter(Q(name=search_tag) | Q(name_ar=search_tag)).exists():
                            target_brand = website_group_obj.brands.filter(Q(name=search_tag) | Q(name_ar=search_tag))[0]
                            search_tags.remove(search_tag)
                            break
                    if target_brand!=None:
                        available_dealshub_products = available_dealshub_products.filter(product__base_product__brand=target_brand)

                    if len(search_tags)>0:
                        search_results = DealsHubProduct.objects.none()
                        for search_tag in search_tags:
                            search_results |= available_dealshub_products.filter(Q(product_name_ar__icontains=search_tag) | Q(product__product_name__icontains=search_tag) | Q(product__base_product__seller_sku__icontains=search_tag))
                        available_dealshub_products = search_results.distinct()


            brand_list = []
            try:
                brand_list = list(available_dealshub_products.values_list('product__base_product__brand__name', flat=True).distinct())[:50]
                if language_code == "ar":
                    brand_list = list(available_dealshub_products.values_list('product__base_product__brand__name_ar', flat=True).distinct())[:50]

                brand_list = list(set(brand_list))
                if len(brand_list)==1:
                    brand_list = []
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SearchAPI brand list: %s at %s", e, str(exc_tb.tb_lineno))

            if len(brand_filter)>0:
                available_dealshub_products = available_dealshub_products.filter(product__base_product__brand__name__in=brand_filter)

            # filtered_products = DealsHubProduct.objects.none()
            # try:
            #     if len(filter_list)>0:
            #         for filter_metric in filter_list:
            #             for filter_value in filter_metric["values"]:
            #                 filtered_products |= available_dealshub_products.filter(product__dynamic_form_attributes__icontains='"value": "'+filter_value+'"')
            #         filtered_products = filtered_products.distinct()
            #     else:
            #         filtered_products = available_dealshub_products
            # except Exception as e:
            #     exc_type, exc_obj, exc_tb = sys.exc_info()
            #     logger.error("SearchAPI: %s at %s", e, str(exc_tb.tb_lineno))

            paginator = Paginator(available_dealshub_products, 50)
            dealshub_product_objs = paginator.page(page)            
            products = []
            currency = location_group_obj.location.currency
            for dealshub_product_obj in dealshub_product_objs:
                try:
                    if dealshub_product_obj.get_actual_price()==0:
                        continue
                    temp_dict = {}
                    temp_dict["name"] = dealshub_product_obj.get_name(language_code)
                    temp_dict["brand"] = dealshub_product_obj.get_brand(language_code)
                    temp_dict["seller_sku"] = dealshub_product_obj.get_seller_sku()
                    temp_dict["now_price"] = dealshub_product_obj.now_price
                    temp_dict["was_price"] = dealshub_product_obj.was_price
                    temp_dict["promotional_price"] = dealshub_product_obj.promotional_price
                    temp_dict["stock"] = dealshub_product_obj.stock
                    temp_dict["is_new_arrival"] = dealshub_product_obj.is_new_arrival
                    temp_dict["is_on_sale"] = dealshub_product_obj.is_on_sale
                    temp_dict["allowedQty"] = dealshub_product_obj.get_allowed_qty()
                    temp_dict["isStockAvailable"] = dealshub_product_obj.stock>0
                    temp_dict["is_promotional"] = dealshub_product_obj.promotion!=None
                    if dealshub_product_obj.promotion!=None:
                        temp_dict["promotion_tag"] = dealshub_product_obj.promotion.promotion_tag
                    else:
                        temp_dict["promotion_tag"] = None
                    temp_dict["currency"] = currency
                    temp_dict["uuid"] = dealshub_product_obj.uuid
                    temp_dict["link"] = dealshub_product_obj.url
                    temp_dict["id"] = dealshub_product_obj.uuid
                    temp_dict["heroImageUrl"] = dealshub_product_obj.get_display_image_url()
                    
                    products.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("SearchAPI: %s at %s", e, str(exc_tb.tb_lineno))

            filters = []
            try:
                if category_name!="ALL":
                    category_obj = Category.objects.get(Q(name=category_name) | Q(name_ar=category_name))
                    property_data = json.loads(category_obj.property_data)
                    for p_data in property_data:
                        temp_dict = {}
                        temp_dict["key"] = p_data["key"]
                        temp_dict["values"] = p_data["values"]
                        filters.append(temp_dict)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("SearchAPI filter creation: %s at %s", e, str(exc_tb.tb_lineno))


            sub_category_list2 = []
            try:
                category_obj = website_group_obj.categories.get(Q(name=category_name) | Q(name_ar=category_name))
                sub_category_objs = SubCategory.objects.filter(category=category_obj)
                for sub_category_obj in sub_category_objs:
                    temp_dict2 = {}
                    temp_dict2["name"] = sub_category_obj.get_name(language_code)
                    temp_dict2["uuid"] = sub_category_obj.uuid
                    temp_dict2["productCount"] = DealsHubProduct.objects.filter(is_published=True, sub_category=sub_category_obj, location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all()).exclude(now_price=0).exclude(stock=0).count()
                    sub_category_list2.append(temp_dict2)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("SearchAPI filter creation: %s at %s", e, str(exc_tb.tb_lineno))

            is_super_category_available = False
            category_list = []
            try:
                super_category_obj = None
                if super_category_name!="":
                    is_super_category_available = True
                    super_category_obj = SuperCategory.objects.get(Q(name=super_category_name) | Q(name_ar=super_category_name))

                if category_name!="" and category_name!="ALL":
                    super_category_obj = Category.objects.filter(Q(name=category_name) | Q(name_ar=category_name))[0].super_category

                category_objs = Category.objects.filter(super_category=super_category_obj)

                if super_category_obj==None:
                    category_ids = available_dealshub_products.values_list('category', flat=True).distinct()
                    category_objs = Category.objects.filter(id__in=category_ids)

                for category_obj in category_objs:

                    cached_response = cache.get(location_group_uuid+"-"+str(category_obj.uuid), "has_expired")
                    if cached_response!="has_expired":
                        if "subCategoryList" in json.loads(cached_response):
                            category_list.append(json.loads(cached_response))
                        continue

                    if DealsHubProduct.objects.filter(is_published=True, category=category_obj, location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all()).exclude(now_price=0).exclude(stock=0).exists()==False:
                        continue
                    temp_dict = {}
                    temp_dict["name"] = category_obj.get_name(language_code)
                    temp_dict["name_en"] = category_obj.get_name("en")
                    temp_dict["uuid"] = category_obj.uuid
                    temp_dict["productCount"] = DealsHubProduct.objects.filter(is_published=True, category=category_obj, location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all()).exclude(now_price=0).exclude(stock=0).count()
                    sub_category_objs = SubCategory.objects.filter(category=category_obj)
                    sub_category_list = []
                    for sub_category_obj in sub_category_objs:
                        if DealsHubProduct.objects.filter(is_published=True, sub_category=sub_category_obj, location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all()).exclude(now_price=0).exclude(stock=0).exists()==False:
                            continue
                        temp_dict2 = {}
                        temp_dict2["name"] = sub_category_obj.get_name(language_code)
                        temp_dict2["name_en"] = sub_category_obj.get_name("en")
                        temp_dict2["uuid"] = sub_category_obj.uuid
                        temp_dict2["productCount"] = DealsHubProduct.objects.filter(is_published=True, sub_category=sub_category_obj, location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all()).exclude(now_price=0).exclude(stock=0).count()
                        sub_category_list.append(temp_dict2)
                    if len(sub_category_list)>0:
                        temp_dict["subCategoryList"] = sub_category_list
                        category_list.append(temp_dict)
                    cache.set(location_group_uuid+"-"+str(category_obj.uuid), json.dumps(temp_dict))
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("SearchAPI filter creation: %s at %s", e, str(exc_tb.tb_lineno))


            response["isSuperCategoryAvailable"] = is_super_category_available
            response["categoryList"] = category_list
            response["subCategoryList"] = sub_category_list2
            response["brand_list"] = brand_list

            is_available = True
            if int(paginator.num_pages) == int(page):
                is_available = False

            response["is_available"] = is_available
            response["totalPages"] = paginator.num_pages
            response["total_products"] = len(available_dealshub_products)

            search['filters'] = filters
            search['category'] = category_name
            search['products'] = products
            response['search'] = search
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class SearchWIGAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SearchWIGAPI: %s", str(data))
            language_code = data.get("language","en")

            search_string = data.get("name", "").strip()
            super_category_name = data.get("superCategory", "").strip()
            category_name = data.get("category", "").strip()
            subcategory_name = data.get("subcategory", "").strip()
            brand_name = data.get("brand", "").strip()
            page_type = data.get("page_type", "").strip()

            page_description = ""
            seo_title = ""
            seo_keywords = ""
            seo_description = ""
            short_description = ""
            long_description = ""

            try:
                if page_type=="super_category":
                    super_category_obj = SuperCategory.objects.filter(Q(name=super_category_name) | Q(name_ar=super_category_name))[0]
                    page_description = super_category_obj.page_description
                    seo_title = super_category_obj.seo_title
                    seo_keywords = super_category_obj.seo_keywords
                    seo_description = super_category_obj.seo_description
                    short_description = super_category_obj.short_description
                    long_description = super_category_obj.long_description
                elif page_type=="category":
                    category_obj = Category.objects.filter(Q(name=category_name) | Q(name_ar=category_name))[0]
                    page_description = category_obj.page_description
                    seo_title = category_obj.seo_title
                    seo_keywords = category_obj.seo_keywords
                    seo_description = category_obj.seo_description
                    short_description = category_obj.short_description
                    long_description = category_obj.long_description
                elif page_type=="sub_category":
                    sub_category_obj = SubCategory.objects.filter(Q(name=subcategory_name) | Q(name_ar=subcategory_name))[0]
                    page_description = sub_category_obj.page_description
                    seo_title = sub_category_obj.seo_title
                    seo_keywords = sub_category_obj.seo_keywords
                    seo_description = sub_category_obj.seo_description
                    short_description = sub_category_obj.short_description
                    long_description = sub_category_obj.long_description
                elif page_type=="brand":
                    brand_obj = Brand.objects.filter((Q(name=brand_name) | Q(name_ar=brand_name)), organization__name="WIG")[0]
                    page_description = brand_obj.page_description
                    seo_title = brand_obj.seo_title
                    seo_keywords = brand_obj.seo_keywords
                    seo_description = brand_obj.seo_description
                    short_description = brand_obj.short_description
                    long_description = brand_obj.long_description
                elif page_type=="brand_super_category":
                    brand_obj = Brand.objects.filter((Q(name=brand_name) | Q(name_ar=brand_name)), organization__name="WIG")[0]
                    super_category_obj = SuperCategory.objects.get(Q(name=super_category_name) |Q(name_ar=super_category_name))[0]
                    brand_super_category_obj = BrandSuperCategory.objects.get(brand=brand_obj, super_category=super_category_obj)
                    page_description = brand_super_category_obj.page_description
                    seo_title = brand_super_category_obj.seo_title
                    seo_keywords = brand_super_category_obj.seo_keywords
                    seo_description = brand_super_category_obj.seo_description
                    short_description = brand_super_category_obj.short_description
                    long_description = brand_super_category_obj.long_description
                elif page_type=="brand_category":
                    brand_obj = Brand.objects.filter((Q(name=brand_name) | Q(name_ar=brand_name)), organization__name="WIG")[0]
                    category_obj = Category.objects.filter(Q(name=category_name) | Q(name_ar=category_name))[0]
                    brand_category_obj = BrandCategory.objects.get(brand=brand_obj, category=category_obj)
                    page_description = brand_category_obj.page_description
                    seo_title = brand_category_obj.seo_title
                    seo_keywords = brand_category_obj.seo_keywords
                    seo_description = brand_category_obj.seo_description
                    short_description = brand_category_obj.short_description
                    long_description = brand_category_obj.long_description
                elif page_type=="brand_sub_category":
                    brand_obj = Brand.objects.get((Q(name=brand_name) | Q(name_ar=brand_name)), organization__name="WIG")
                    sub_category_name = data["sub_category_name"]
                    sub_category_obj = SubCategory.objects.filter(Q(name=sub_category_name) | Q(name_ar=sub_category_name))[0]
                    brand_sub_category_obj = BrandSubCategory.objects.get(brand=brand_obj, sub_category=sub_category_obj)
                    page_description = brand_sub_category_obj.page_description
                    seo_title = brand_sub_category_obj.seo_title
                    seo_keywords = brand_sub_category_obj.seo_keywords
                    seo_description = brand_sub_category_obj.seo_description
                    short_description = brand_sub_category_obj.short_description
                    long_description = brand_sub_category_obj.long_description

                response["page_description"] = page_description
                response["seo_title"] = seo_title
                response["seo_keywords"] = seo_keywords
                response["seo_description"] = seo_description
                response["short_description"] = short_description
                response["long_description"] = long_description
            except Exception as e:
                response["page_description"] = ""
                response["seo_title"] = ""
                response["seo_keywords"] = ""
                response["seo_description"] = ""
                response["short_description"] = ""
                response["long_description"] = ""


            brand_filter = data.get("brand_filter", [])
            sort_filter = data.get("sort_filter", {})
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group
            page = data.get("page", 1)
            search = {}
            available_dealshub_products = DealsHubProduct.objects.filter(location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all(), is_published=True).exclude(now_price=0).exclude(stock=0)
            # Filters
            if sort_filter.get("price", "")=="high-to-low":
                available_dealshub_products = available_dealshub_products.order_by('-now_price')
            if sort_filter.get("price", "")=="low-to-high":
                available_dealshub_products = available_dealshub_products.order_by('now_price')
            if brand_name!="":
                available_dealshub_products = available_dealshub_products.filter(Q(product__base_product__brand__name=brand_name) | Q(product__base_product__brand__name_ar=brand_name))
            if super_category_name!="":
                available_dealshub_products = available_dealshub_products.filter(Q(category__super_category__name=super_category_name) | Q(category__super_category__name_ar=super_category_name))
            if category_name!="ALL" and category_name!="":
                available_dealshub_products = available_dealshub_products.filter(Q(category__name=category_name) | Q(category__name_ar=category_name))
            if subcategory_name!="":
                available_dealshub_products = available_dealshub_products.filter(Q(sub_category__name=subcategory_name) | Q(sub_category__name_ar=subcategory_name))
            if search_string!="":
                search_string = remove_stopwords(search_string)
                words = search_string.split(" ")
                target_brand = None
                for word in words:
                    if website_group_obj.brands.filter(Q(name=word) | Q(name_ar=word)).exists():
                        target_brand = website_group_obj.brands.filter(Q(name=word) | Q(name_ar=word))[0]
                        words.remove(word)
                        break
                if target_brand!=None:
                    available_dealshub_products = available_dealshub_products.filter(product__base_product__brand=target_brand)

                if len(words)==1:
                    available_dealshub_products = available_dealshub_products.filter(Q(product__product_name__icontains=words[0]) | Q(product_name_ar__icontains = words[0]) | Q(product__base_product__seller_sku__icontains=words[0]))
                elif len(words)==2:
                    if available_dealshub_products.filter(Q(product__product_name__icontains=search_string) | Q(product_name_ar__icontains=search_string)).exists():
                        available_dealshub_products = available_dealshub_products.filter(Q(product__product_name__icontains=search_string) | Q(product_name_ar__icontains=search_string))
                    else:
                        if available_dealshub_products.filter(Q(product__product_name__icontains=words[0]) | Q(product_name_ar__icontains=words[0])).filter(Q(product__product_name__icontains=words[1]) | Q(product_name_ar__icontains=words[1])).exists():
                            available_dealshub_products = available_dealshub_products.filter(product__product_name__icontains=words[0] | Q(product_name_ar__icontains=words[0])).filter(product__product_name__icontains=words[1] | Q(product_name_ar__icontains=words[1]))
                        else:
                            available_dealshub_products = available_dealshub_products.filter(Q(product__product_name__icontains=words[0]) | Q(product_name_ar__icontains=words[0]) | Q(product__product_name__icontains=words[1]) | Q(product_name_ar__icontains=words[1]))
                elif len(words)==3:
                    if available_dealshub_products.filter(Q(product__product_name__icontains=search_string) | Q(product_name_ar__icontains=search_string)).exists():
                        available_dealshub_products = available_dealshub_products.filter(Q(product__product_name__icontains=search_string) | Q(product_name_ar__icontains=search_string))
                    else:
                        if available_dealshub_products.filter(Q(product__product_name__icontains=words[0]) | Q(product_name_ar__icontains=words[0])).filter(Q(product__product_name__icontains=words[1]) | Q(product_name_ar__icontains=words[1])).filter(Q(product__product_name__icontains=words[2]) | Q(product_name_ar__icontains=words[2])).exists():
                            available_dealshub_products = available_dealshub_products.filter(product__product_name__icontains=words[0] | Q(product_name_ar__icontains=words[0])).filter(product__product_name__icontains=words[1] | Q(product_name_ar__icontains=words[1])).filter(product__product_name__icontains=words[2] | Q(product_name_ar__icontains=words[2]))
                        else:
                            temp_available_dealshub_products = available_dealshub_products.filter(Q(product__product_name__icontains=words[0]) | Q(product_name_ar__icontains=words[0])).filter(Q(product__product_name__icontains=words[1]) | Q(product_name_ar__icontains=words[1]))
                            temp_available_dealshub_products |= available_dealshub_products.filter(Q(product__product_name__icontains=words[1]) | Q(product_name_ar__icontains=words[1])).filter(Q(product__product_name__icontains=words[2]) | Q(product_name_ar__icontains=words[2]))
                            temp_available_dealshub_products |= available_dealshub_products.filter(Q(product__product_name__icontains=words[0]) | Q(product_name_ar__icontains=words[0])).filter(Q(product__product_name__icontains=words[2]) | Q(product_name_ar__icontains=words[2]))
                            if temp_available_dealshub_products.exists()==False:
                                temp_available_dealshub_products = available_dealshub_products.filter(Q(product__product_name__icontains=words[0]) | Q(product_name_ar__icontains=words[0]))
                                temp_available_dealshub_products |= available_dealshub_products.filter(Q(product__product_name__icontains=words[1]) | Q(product_name_ar__icontains=words[1]))
                                temp_available_dealshub_products |= available_dealshub_products.filter(Q(product__product_name__icontains=words[2]) | Q(product_name_ar__icontains=words[2]))
                            available_dealshub_products = temp_available_dealshub_products
                else:
                    if available_dealshub_products.filter(Q(product__product_name__icontains=search_string) | Q(product_name_ar__icontains=search_string)).exists():
                        available_dealshub_products = available_dealshub_products.filter(Q(product__product_name__icontains=search_string) | Q(product_name_ar__icontains=search_string))
                    else:
                        if len(words)>0:
                            search_results = DealsHubProduct.objects.none()
                            for word in words:
                                search_results |= available_dealshub_products.filter(Q(product__product_name__icontains=word) | Q(product_name_ar__icontains=word) | Q(product__base_product__seller_sku__icontains=word))
                            available_dealshub_products = search_results.distinct()

            if len(brand_filter)>0:
                available_dealshub_products = available_dealshub_products.filter(product__base_product__brand__name__in=brand_filter)
            paginator = Paginator(available_dealshub_products, 50)
            dealshub_product_objs = paginator.page(page)
            temp_pk_list = []
            for dealshub_product_obj in dealshub_product_objs:
                temp_pk_list.append(dealshub_product_obj.pk)
            dealshub_product_objs = DealsHubProduct.objects.filter(pk__in=temp_pk_list).prefetch_related('product').prefetch_related('product__base_product').prefetch_related('promotion')
            if sort_filter.get("price", "")=="high-to-low":
                dealshub_product_objs = dealshub_product_objs.order_by('-now_price')
            if sort_filter.get("price", "")=="low-to-high":
                dealshub_product_objs = dealshub_product_objs.order_by('now_price')
            products = []
            currency = location_group_obj.location.currency
            for dealshub_product_obj in dealshub_product_objs:
                try:
                    if dealshub_product_obj.get_actual_price()==0:
                        continue
                    temp_dict = {}
                    temp_dict["name"] = dealshub_product_obj.get_name(language_code)
                    temp_dict["brand"] = dealshub_product_obj.get_brand(language_code)
                    temp_dict["seller_sku"] = dealshub_product_obj.get_seller_sku()
                    temp_dict["now_price"] = dealshub_product_obj.now_price
                    temp_dict["was_price"] = dealshub_product_obj.was_price
                    temp_dict["promotional_price"] = dealshub_product_obj.promotional_price
                    temp_dict["stock"] = dealshub_product_obj.stock
                    temp_dict["is_new_arrival"] = dealshub_product_obj.is_new_arrival
                    temp_dict["is_on_sale"] = dealshub_product_obj.is_on_sale
                    temp_dict["allowedQty"] = dealshub_product_obj.get_allowed_qty()
                    temp_dict["isStockAvailable"] = dealshub_product_obj.stock>0
                    temp_dict["is_promotional"] = False
                    if dealshub_product_obj.promotion!=None and check_valid_promotion(dealshub_product_obj.promotion)==True:
                        temp_dict["is_promotional"] = True
                    if dealshub_product_obj.promotion!=None:
                        temp_dict["promotion_tag"] = dealshub_product_obj.promotion.promotion_tag
                    else:
                        temp_dict["promotion_tag"] = None
                    temp_dict["currency"] = currency
                    temp_dict["uuid"] = dealshub_product_obj.uuid
                    temp_dict["link"] = dealshub_product_obj.url
                    temp_dict["id"] = dealshub_product_obj.uuid
                    temp_dict["heroImageUrl"] = dealshub_product_obj.get_display_image_url()
                    products.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("SearchWIGAPI: %s at %s", e, str(exc_tb.tb_lineno))
            is_available = True
            if int(paginator.num_pages) == int(page):
                is_available = False
            response["is_available"] = is_available
            response["totalPages"] = paginator.num_pages
            response["total_products"] = len(available_dealshub_products)
            search['products'] = products
            response['search'] = search
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchWIGAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class SearchWIG2API(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SearchWIG2API: %s", str(data))

            search_string = data.get("name", "").strip()
            super_category_name = data.get("superCategory", "").strip()
            category_name = data.get("category", "").strip()
            subcategory_name = data.get("subcategory", "").strip()
            brand_name = data.get("brand", "").strip()
            page_type = data.get("page_type", "").strip()
            
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group

            page_description = ""
            seo_title = ""
            seo_keywords = ""
            seo_description = ""
            short_description = ""
            long_description = ""

            try:
                if page_type=="super_category":
                    seo_super_category_obj = SEOSuperCategory.objects.get(super_category__name=super_category_name, location_group=location_group_obj)
                    page_description = seo_super_category_obj.page_description
                    seo_title = seo_super_category_obj.seo_title
                    seo_keywords = seo_super_category_obj.seo_keywords
                    seo_description = seo_super_category_obj.seo_description
                    short_description = seo_super_category_obj.short_description
                    long_description = seo_super_category_obj.long_description
                elif page_type=="category":
                    seo_category_obj = SEOCategory.objects.filter(category__name=category_name, location_group=location_group_obj)[0]
                    page_description = seo_category_obj.page_description
                    seo_title = seo_category_obj.seo_title
                    seo_keywords = seo_category_obj.seo_keywords
                    seo_description = seo_category_obj.seo_description
                    short_description = seo_category_obj.short_description
                    long_description = seo_category_obj.long_description
                elif page_type=="sub_category":
                    seo_sub_category_obj = SEOSubCategory.objects.filter(sub_category__name=subcategory_name, location_group=location_group_obj)[0]
                    page_description = seo_sub_category_obj.page_description
                    seo_title = seo_sub_category_obj.seo_title
                    seo_keywords = seo_sub_category_obj.seo_keywords
                    seo_description = seo_sub_category_obj.seo_description
                    short_description = seo_sub_category_obj.short_description
                    long_description = seo_sub_category_obj.long_description
                elif page_type=="brand":
                    seo_brand_obj = SEOBrand.objects.get(brand__name=brand_name, location_group=location_group_obj, brand__organization__name="WIG")
                    page_description = seo_brand_obj.page_description
                    seo_title = seo_brand_obj.seo_title
                    seo_keywords = seo_brand_obj.seo_keywords
                    seo_description = seo_brand_obj.seo_description
                    short_description = seo_brand_obj.short_description
                    long_description = seo_brand_obj.long_description
                elif page_type=="brand_super_category":
                    brand_obj = Brand.objects.get(name=brand_name, organization__name="WIG")
                    super_category_obj = SuperCategory.objects.get(name=super_category_name)
                    brand_super_category_obj = BrandSuperCategory.objects.get(brand=brand_obj, super_category=super_category_obj, location_group=location_group_obj)
                    page_description = brand_super_category_obj.page_description
                    seo_title = brand_super_category_obj.seo_title
                    seo_keywords = brand_super_category_obj.seo_keywords
                    seo_description = brand_super_category_obj.seo_description
                    short_description = brand_super_category_obj.short_description
                    long_description = brand_super_category_obj.long_description
                elif page_type=="brand_category":
                    brand_obj = Brand.objects.get(name=brand_name, organization__name="WIG")
                    category_obj = Category.objects.get(name=category_name)
                    brand_category_obj = BrandCategory.objects.get(brand=brand_obj, category=category_obj, location_group=location_group_obj)
                    page_description = brand_category_obj.page_description
                    seo_title = brand_category_obj.seo_title
                    seo_keywords = brand_category_obj.seo_keywords
                    seo_description = brand_category_obj.seo_description
                    short_description = brand_category_obj.short_description
                    long_description = brand_category_obj.long_description
                elif page_type=="brand_sub_category":
                    brand_obj = Brand.objects.get(name=brand_name, organization__name="WIG")
                    sub_category_obj = SubCategory.objects.get(name=subcategory_name)
                    brand_sub_category_obj = BrandSubCategory.objects.get(brand=brand_obj, sub_category=sub_category_obj, location_group=location_group_obj)
                    page_description = brand_sub_category_obj.page_description
                    seo_title = brand_sub_category_obj.seo_title
                    seo_keywords = brand_sub_category_obj.seo_keywords
                    seo_description = brand_sub_category_obj.seo_description
                    short_description = brand_sub_category_obj.short_description
                    long_description = brand_sub_category_obj.long_description

                response["page_description"] = page_description
                response["seo_title"] = seo_title
                response["seo_keywords"] = seo_keywords
                response["seo_description"] = seo_description
                response["short_description"] = short_description
                response["long_description"] = long_description
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SearchWIG2API: %s at %s", e, str(exc_tb.tb_lineno))
                response["page_description"] = ""
                response["seo_title"] = ""
                response["seo_keywords"] = ""
                response["seo_description"] = ""
                response["short_description"] = ""
                response["long_description"] = ""


            brand_filter = data.get("brand_filter", [])
            sort_filter = data.get("sort_filter", {})
            page = data.get("page", 1)
            search = {}
            available_dealshub_products = DealsHubProduct.objects.filter(location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all(), is_published=True).exclude(now_price=0).exclude(stock=0)
            # Filters
            if sort_filter.get("price", "")=="high-to-low":
                available_dealshub_products = available_dealshub_products.order_by('-now_price')
            if sort_filter.get("price", "")=="low-to-high":
                available_dealshub_products = available_dealshub_products.order_by('now_price')
            if brand_name!="":
                available_dealshub_products = available_dealshub_products.filter(product__base_product__brand__name=brand_name)
            if super_category_name!="":
                available_dealshub_products = available_dealshub_products.filter(category__super_category__name=super_category_name)
            if category_name!="ALL" and category_name!="":
                available_dealshub_products = available_dealshub_products.filter(category__name=category_name)
            if subcategory_name!="":
                available_dealshub_products = available_dealshub_products.filter(sub_category__name=subcategory_name)
            if search_string!="":
                search_string = remove_stopwords(search_string)
                words = search_string.split(" ")
                target_brand = None
                for word in words:
                    if website_group_obj.brands.filter(name=word).exists():
                        target_brand = website_group_obj.brands.filter(name=word)[0]
                        words.remove(word)
                        break
                if target_brand!=None:
                    available_dealshub_products = available_dealshub_products.filter(product__base_product__brand=target_brand)
                if len(words)==1:
                    available_dealshub_products = available_dealshub_products.filter(Q(search_keywords__icontains=","+words[0]+","))
                elif len(words)==2:
                    if available_dealshub_products.filter(search_keywords__icontains=","+search_string+",").exists():
                        available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+search_string+",")
                    else:
                        if available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",").exists():
                            available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",")
                        else:
                            available_dealshub_products = available_dealshub_products.filter(Q(search_keywords__icontains=","+words[0]+",") | Q(search_keywords__icontains=","+words[1]+","))
                elif len(words)==3:
                    if available_dealshub_products.filter(search_keywords__icontains=","+search_string+",").exists():
                        available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+search_string+",")
                    else:
                        if available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",").filter(search_keywords__icontains=","+words[2]+",").exists():
                            available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",").filter(search_keywords__icontains=","+words[2]+",")
                        else:
                            temp_available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=words[0]).filter(search_keywords__icontains=words[1])
                            temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[1]).filter(search_keywords__icontains=words[2])
                            temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[0]).filter(search_keywords__icontains=words[2])
                            if temp_available_dealshub_products.exists()==False:
                                temp_available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=words[0])
                                temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[1])
                                temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[2])
                            available_dealshub_products = temp_available_dealshub_products.distinct()
                else:
                    if available_dealshub_products.filter(search_keywords__icontains=","+search_string+",").exists():
                        available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+search_string+",")
                    else:
                        if len(words)>0:
                            search_results = DealsHubProduct.objects.none()
                            for word in words:
                                search_results |= available_dealshub_products.filter(search_keywords__icontains=","+word+",")
                            available_dealshub_products = search_results.distinct()

            if len(brand_filter)>0:
                available_dealshub_products = available_dealshub_products.filter(product__base_product__brand__name__in=brand_filter)
            paginator = Paginator(available_dealshub_products, 50)
            dealshub_product_objs = paginator.page(page)
            temp_pk_list = []
            for dealshub_product_obj in dealshub_product_objs:
                temp_pk_list.append(dealshub_product_obj.pk)
            dealshub_product_objs = DealsHubProduct.objects.filter(pk__in=temp_pk_list).prefetch_related('product').prefetch_related('product__base_product').prefetch_related('promotion')
            if sort_filter.get("price", "")=="high-to-low":
                dealshub_product_objs = dealshub_product_objs.order_by('-now_price')
            if sort_filter.get("price", "")=="low-to-high":
                dealshub_product_objs = dealshub_product_objs.order_by('now_price')
            products = []
            currency = location_group_obj.location.currency
            for dealshub_product_obj in dealshub_product_objs:
                try:
                    if dealshub_product_obj.get_actual_price()==0:
                        continue
                    temp_dict = {}
                    temp_dict["name"] = dealshub_product_obj.get_name()
                    temp_dict["brand"] = dealshub_product_obj.get_brand()
                    temp_dict["seller_sku"] = dealshub_product_obj.get_seller_sku()
                    temp_dict["now_price"] = dealshub_product_obj.now_price
                    temp_dict["was_price"] = dealshub_product_obj.was_price
                    temp_dict["promotional_price"] = dealshub_product_obj.promotional_price
                    temp_dict["stock"] = dealshub_product_obj.stock
                    temp_dict["is_new_arrival"] = dealshub_product_obj.is_new_arrival
                    temp_dict["is_on_sale"] = dealshub_product_obj.is_on_sale
                    temp_dict["allowedQty"] = dealshub_product_obj.get_allowed_qty()
                    temp_dict["isStockAvailable"] = dealshub_product_obj.stock>0
                    temp_dict["is_promotional"] = False
                    if dealshub_product_obj.promotion!=None and check_valid_promotion(dealshub_product_obj.promotion)==True:
                        temp_dict["is_promotional"] = True
                    if dealshub_product_obj.promotion!=None:
                        temp_dict["promotion_tag"] = dealshub_product_obj.promotion.promotion_tag
                    else:
                        temp_dict["promotion_tag"] = None
                    temp_dict["currency"] = currency
                    temp_dict["uuid"] = dealshub_product_obj.uuid
                    temp_dict["link"] = dealshub_product_obj.url
                    temp_dict["id"] = dealshub_product_obj.uuid
                    temp_dict["heroImageUrl"] = dealshub_product_obj.get_display_image_url()
                    products.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("SearchWIG2API: %s at %s", e, str(exc_tb.tb_lineno))
            is_available = True
            if int(paginator.num_pages) == int(page):
                is_available = False
            response["is_available"] = is_available
            response["totalPages"] = paginator.num_pages
            response["total_products"] = len(available_dealshub_products)
            search['products'] = products
            response['search'] = search
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchWIG2API: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class SearchDaycartAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SearchDaycartAPI: %s", str(data))
            t1 = datetime.datetime.now()
            language_code = data.get("language","en")
            
            search_string = data.get("name", "").strip()
            super_category_name = data.get("superCategory", "").strip()
            category_name = data.get("category", "").strip()
            subcategory_name = data.get("subcategory", "").strip()
            brand_name = data.get("brand", "").strip()

            brand_filter = data.get("brand_filter", [])
            sort_filter = data.get("sort_filter", {})

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group

            page = data.get("page", 1)

            key_hash = "search-daycart-"+language_code+"-"+super_category_name+"-"+category_name+"-"+subcategory_name+"-"+brand_name+"-"+str(page)
            if brand_filter==[] and sort_filter=={"price":""} and search_string=="":
                cached_value = cache.get(key_hash, "has_expired")
                if cached_value!="has_expired":
                    t2 = datetime.datetime.now()
                    logger.info("SearchDaycartAPI: HIT! time: %s", str((t2-t1).total_seconds()))
                    response = json.loads(cached_value)
                    return Response(data=response)

            search = {}

            available_dealshub_products = DealsHubProduct.objects.filter(location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all(), is_published=True).exclude(now_price=0).exclude(stock=0)

            # Filters
            if sort_filter.get("price", "")=="high-to-low":
                available_dealshub_products = available_dealshub_products.order_by('-now_price')
            if sort_filter.get("price", "")=="low-to-high":
                available_dealshub_products = available_dealshub_products.order_by('now_price')

            if brand_name!="":
                available_dealshub_products = available_dealshub_products.filter(Q(product__base_product__brand__name=brand_name) | Q(product__base_product__brand__name_ar=brand_name))

            if super_category_name!="":
                available_dealshub_products = available_dealshub_products.filter(Q(category__super_category__name=super_category_name) | Q(category__super_category__name_ar=super_category_name))

            if category_name!="ALL" and category_name!="":
                available_dealshub_products = available_dealshub_products.filter(Q(category__name=category_name) | Q(category__name_ar=category_name))

            if subcategory_name!="":
                available_dealshub_products = available_dealshub_products.filter(Q(sub_category__name=subcategory_name) | Q(sub_category__name_ar=subcategory_name))
            
            if search_string!="":
                search_string = remove_stopwords(search_string)
                words = search_string.split(" ")
                target_brand = None
                for word in words:
                    if website_group_obj.brands.filter(name=word).exists():
                        target_brand = website_group_obj.brands.filter(name=word)[0]
                        words.remove(word)
                        break
                if target_brand!=None:
                    available_dealshub_products = available_dealshub_products.filter(product__base_product__brand=target_brand)
                if len(words)==1:
                    available_dealshub_products = available_dealshub_products.filter(Q(search_keywords__icontains=","+words[0]+","))
                elif len(words)==2:
                    if available_dealshub_products.filter(search_keywords__icontains=","+search_string+",").exists():
                        available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+search_string+",")
                    else:
                        if available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",").exists():
                            available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",")
                        else:
                            available_dealshub_products = available_dealshub_products.filter(Q(search_keywords__icontains=","+words[0]+",") | Q(search_keywords__icontains=","+words[1]+","))
                elif len(words)==3:
                    if available_dealshub_products.filter(search_keywords__icontains=","+search_string+",").exists():
                        available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+search_string+",")
                    else:
                        if available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",").filter(search_keywords__icontains=","+words[2]+",").exists():
                            available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",").filter(search_keywords__icontains=","+words[2]+",")
                        else:
                            temp_available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=words[0]).filter(search_keywords__icontains=words[1])
                            temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[1]).filter(search_keywords__icontains=words[2])
                            temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[0]).filter(search_keywords__icontains=words[2])
                            if temp_available_dealshub_products.exists()==False:
                                temp_available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=words[0])
                                temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[1])
                                temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[2])
                            available_dealshub_products = temp_available_dealshub_products.distinct()
                else:
                    if available_dealshub_products.filter(search_keywords__icontains=","+search_string+",").exists():
                        available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+search_string+",")
                    else:
                        if len(words)>0:
                            search_results = DealsHubProduct.objects.none()
                            for word in words:
                                search_results |= available_dealshub_products.filter(search_keywords__icontains=","+word+",")
                            available_dealshub_products = search_results.distinct()

            brand_list = []
            try:
                brand_list = list(available_dealshub_products.values_list('product__base_product__brand__name', flat=True).distinct())[:50]
                if language_code == "ar":
                    brand_list = list(available_dealshub_products.values_list('product__base_product__brand__name_ar', flat=True).distinct())[:50]

                brand_list = list(set(brand_list))
                if len(brand_list)==1:
                    brand_list = []
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SearchAPI brand list: %s at %s", e, str(exc_tb.tb_lineno))

            if len(brand_filter)>0:
                available_dealshub_products = available_dealshub_products.filter(product__base_product__brand__name__in=brand_filter)

            paginator = Paginator(available_dealshub_products, 50)
            dealshub_product_objs = paginator.page(page)            
            products = []
            currency = location_group_obj.location.currency
            for dealshub_product_obj in dealshub_product_objs:
                try:
                    if dealshub_product_obj.get_actual_price()==0:
                        continue
                    temp_dict = {}
                    temp_dict["name"] = dealshub_product_obj.get_name(language_code)
                    temp_dict["brand"] = dealshub_product_obj.get_brand(language_code)
                    temp_dict["seller_sku"] = dealshub_product_obj.get_seller_sku()
                    temp_dict["now_price"] = dealshub_product_obj.now_price
                    temp_dict["was_price"] = dealshub_product_obj.was_price
                    temp_dict["promotional_price"] = dealshub_product_obj.promotional_price
                    temp_dict["stock"] = dealshub_product_obj.stock
                    temp_dict["is_new_arrival"] = dealshub_product_obj.is_new_arrival
                    temp_dict["is_on_sale"] = dealshub_product_obj.is_on_sale
                    temp_dict["allowedQty"] = dealshub_product_obj.get_allowed_qty()
                    temp_dict["isStockAvailable"] = dealshub_product_obj.stock>0
                    temp_dict["is_promotional"] = dealshub_product_obj.promotion!=None
                    if dealshub_product_obj.promotion!=None:
                        temp_dict["promotion_tag"] = dealshub_product_obj.promotion.promotion_tag
                    else:
                        temp_dict["promotion_tag"] = None
                    temp_dict["currency"] = currency
                    temp_dict["uuid"] = dealshub_product_obj.uuid
                    temp_dict["link"] = dealshub_product_obj.url
                    temp_dict["id"] = dealshub_product_obj.uuid
                    temp_dict["heroImageUrl"] = dealshub_product_obj.get_display_image_url()
                    
                    products.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("SearchAPI: %s at %s", e, str(exc_tb.tb_lineno))

            is_super_category_available = False
            category_list = []
            try:
                super_category_obj = None
                if super_category_name!="":
                    is_super_category_available = True
                    super_category_obj = SuperCategory.objects.get(Q(name=super_category_name) | Q(name_ar=super_category_name))

                if category_name!="" and category_name!="ALL":
                    super_category_obj = Category.objects.filter(Q(name=category_name) | Q(name_ar=category_name))[0].super_category

                category_objs = Category.objects.filter(super_category=super_category_obj)

                if super_category_obj==None:
                    category_ids = available_dealshub_products.values_list('category', flat=True).distinct()
                    category_objs = Category.objects.filter(id__in=category_ids)

                for category_obj in category_objs:

                    cached_response = cache.get(location_group_uuid+"-"+str(category_obj.uuid), "has_expired")
                    if cached_response!="has_expired":
                        if "subCategoryList" in json.loads(cached_response):
                            category_list.append(json.loads(cached_response))
                        continue

                    if DealsHubProduct.objects.filter(is_published=True, category=category_obj, location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all()).exclude(now_price=0).exclude(stock=0).exists()==False:
                        continue
                    temp_dict = {}
                    temp_dict["name"] = category_obj.get_name(language_code)
                    temp_dict["name_en"] = category_obj.get_name("en")
                    temp_dict["name_ar"] = category_obj.get_name("ar")
                    temp_dict["uuid"] = category_obj.uuid
                    temp_dict["productCount"] = DealsHubProduct.objects.filter(is_published=True, category=category_obj, location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all()).exclude(now_price=0).exclude(stock=0).count()
                    sub_category_objs = SubCategory.objects.filter(category=category_obj)
                    sub_category_list = []
                    for sub_category_obj in sub_category_objs:
                        if DealsHubProduct.objects.filter(is_published=True, sub_category=sub_category_obj, location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all()).exclude(now_price=0).exclude(stock=0).exists()==False:
                            continue
                        temp_dict2 = {}
                        temp_dict2["name"] = sub_category_obj.get_name(language_code)
                        temp_dict2["name_en"] = sub_category_obj.get_name("en")
                        temp_dict2["name_ar"] = sub_category_obj.get_name("ar")
                        temp_dict2["uuid"] = sub_category_obj.uuid
                        temp_dict2["productCount"] = DealsHubProduct.objects.filter(is_published=True, sub_category=sub_category_obj, location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all()).exclude(now_price=0).exclude(stock=0).count()
                        sub_category_list.append(temp_dict2)
                    if len(sub_category_list)>0:
                        temp_dict["subCategoryList"] = sub_category_list
                        category_list.append(temp_dict)
                    cache.set(location_group_uuid+"-"+str(category_obj.uuid), json.dumps(temp_dict))
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("SearchAPI filter creation: %s at %s", e, str(exc_tb.tb_lineno))


            response["isSuperCategoryAvailable"] = is_super_category_available
            response["categoryList"] = category_list
            response["brand_list"] = brand_list

            is_available = True
            if int(paginator.num_pages) == int(page):
                is_available = False

            response["is_available"] = is_available
            response["totalPages"] = paginator.num_pages
            response["total_products"] = len(available_dealshub_products)

            search['category'] = category_name
            search['products'] = products
            response['search'] = search
            response['status'] = 200

            if brand_filter==[] and sort_filter=={"price":""} and search_string=="":
                cache.set(key_hash, json.dumps(response))

            t2 = datetime.datetime.now()
            logger.info("SearchDaycartAPI: MISS! time: %s", str((t2-t1).total_seconds()))
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchDaycartAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchWIGCategoriesAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            language_code = data.get("language","en")
            logger.info("FetchWIGCategoriesAPI: %s", str(data))
            
            search_string = data.get("name", "").strip()

            super_category_name = data.get("superCategory", "").strip()
            category_name = data.get("category", "").strip()
            subcategory_name = data.get("subCategory", "").strip()

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group

            page = data.get("page", 1)
            search = {}

            brand_list = []
            try:
                if language_code == "en":
                    brand_list = website_group_obj.brands.all().values_list("name", flat=True)
                else:
                    brand_list = website_group_obj.brands.all().values_list("name_ar", flat=True)
                brand_list = list(set(brand_list))
                if len(brand_list)==1:
                    brand_list = []
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SearchAPI brand list: %s at %s", e, str(exc_tb.tb_lineno))

            is_super_category_available = False
            category_list = []
            try:
                super_category_obj = None
                if super_category_name!="":
                    is_super_category_available = True
                    super_category_obj = SuperCategory.objects.get(Q(name=super_category_name) | Q(name_ar=super_category_name))
                elif category_name!="" and category_name.lower()!="all":
                    super_category_obj = Category.objects.filter(Q(name=category_name) | Q(name_ar=category_name))[0].super_category
                elif subcategory_name!="":
                    super_category_obj = SubCategory.objects.filter(Q(name=subcategory_name) | Q(name_ar=subcategory_name))[0].category.super_category
                else:
                    super_category_obj = website_group_obj.super_categories.all()[0]

                if category_name.lower()=="all":
                    available_dealshub_products = DealsHubProduct.objects.filter(location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all(), is_published=True).exclude(category=None).exclude(now_price=0).exclude(stock=0)
                    search_string = remove_stopwords(search_string)
                    words = search_string.split(" ")
                    target_brand = None
                    for word in words:
                        if website_group_obj.brands.filter(Q(name=word) | Q(name_ar=word)).exists():
                            target_brand = website_group_obj.brands.filter(Q(name=word) | Q(name_ar=word))[0]
                            words.remove(word)
                            break
                    if target_brand!=None:
                        available_dealshub_products = available_dealshub_products.filter(product__base_product__brand=target_brand)

                    if len(words)==1:
                        available_dealshub_products = available_dealshub_products.filter(Q(product__product_name__icontains=words[0]) | Q(product_name_ar__icontains = words[0]) | Q(product__base_product__seller_sku__icontains=words[0]))
                    elif len(words)==2:
                        if available_dealshub_products.filter(q(product__product_name__icontains=search_string) | Q(product_name_ar__icontains=search_string)).exists():
                            available_dealshub_products = available_dealshub_products.filter(Q(product__product_name__icontains=search_string) | Q(product_name_ar__icontains=search_string))
                        else:
                            if available_dealshub_products.filter(Q(product__product_name__icontains=words[0]) | Q(product_name_ar__icontains=words[0])).filter(Q(product__product_name__icontains=words[1]) | Q(product_name_ar__icontains=words[1])).exists():
                                available_dealshub_products = available_dealshub_products.filter(product__product_name__icontains=words[0] | Q(product_name_ar__icontains=words[0])).filter(product__product_name__icontains=words[1] | Q(product_name_ar__icontains=words[1]))
                            else:
                                available_dealshub_products = available_dealshub_products.filter(Q(product__product_name__icontains=words[0]) | Q(product_name_ar__icontains=words[0]) | Q(product__product_name__icontains=words[1]) | Q(product_name_ar__icontains=words[1]))
                    elif len(words)==3:
                        if available_dealshub_products.filter(Q(product__product_name__icontains=search_string) | Q(product_name_ar__icontains=search_string)).exists():
                            available_dealshub_products = available_dealshub_products.filter(Q(product__product_name__icontains=search_string) | Q(product_name_ar__icontains=search_string))
                        else:
                            if available_dealshub_products.filter(Q(product__product_name__icontains=words[0]) | Q(product_name_ar__icontains=words[0])).filter(Q(product__product_name__icontains=words[1]) | Q(product_name_ar__icontains=words[1])).filter(Q(product__product_name__icontains=words[2]) | Q(product_name_ar__icontains=words[2])).exists():
                                available_dealshub_products = available_dealshub_products.filter(product__product_name__icontains=words[0] | Q(product_name_ar__icontains=words[0])).filter(product__product_name__icontains=words[1] | Q(product_name_ar__icontains=words[1])).filter(product__product_name__icontains=words[2] | Q(product_name_ar__icontains=words[2]))
                            else:
                                temp_available_dealshub_products = available_dealshub_products.filter(Q(product__product_name__icontains=words[0]) | Q(product_name_ar__icontains=words[0])).filter(Q(product__product_name__icontains=words[1]) | Q(product_name_ar__icontains=words[1]))
                                temp_available_dealshub_products |= available_dealshub_products.filter(Q(product__product_name__icontains=words[1]) | Q(product_name_ar__icontains=words[1])).filter(Q(product__product_name__icontains=words[2]) | Q(product_name_ar__icontains=words[2]))
                                temp_available_dealshub_products |= available_dealshub_products.filter(Q(product__product_name__icontains=words[0]) | Q(product_name_ar__icontains=words[0])).filter(Q(product__product_name__icontains=words[2]) | Q(product_name_ar__icontains=words[2]))
                                if temp_available_dealshub_products.exists()==False:
                                    temp_available_dealshub_products = available_dealshub_products.filter(Q(product__product_name__icontains=words[0]) | Q(product_name_ar__icontains=words[0]))
                                    temp_available_dealshub_products |= available_dealshub_products.filter(Q(product__product_name__icontains=words[1]) | Q(product_name_ar__icontains=words[1]))
                                    temp_available_dealshub_products |= available_dealshub_products.filter(Q(product__product_name__icontains=words[2]) | Q(product_name_ar__icontains=words[2]))
                                available_dealshub_products = temp_available_dealshub_products
                    else:
                        if available_dealshub_products.filter(Q(product__product_name__icontains=search_string) | Q(product_name_ar__icontains=search_string)).exists():
                            available_dealshub_products = available_dealshub_products.filter(Q(product__product_name__icontains=search_string) | Q(product_name_ar__icontains=search_string))
                        else:
                            if len(words)>0:
                                search_results = DealsHubProduct.objects.none()
                                for word in words:
                                    search_results |= available_dealshub_products.filter(Q(product__product_name__icontains=word) | Q(product_name_ar__icontains=word) | Q(product__base_product__seller_sku__icontains=word))
                                available_dealshub_products = search_results.distinct()

                    if available_dealshub_products.exists():
                        super_category_obj = available_dealshub_products[0].category.super_category

                category_objs = Category.objects.filter(super_category=super_category_obj)
                for category_obj in category_objs:

                    cached_response = cache.get(location_group_uuid+"-"+str(category_obj.uuid), "has_expired")
                    if cached_response!="has_expired":
                        if "subCategoryList" in json.loads(cached_response):
                            category_list.append(json.loads(cached_response))
                        continue

                    if DealsHubProduct.objects.filter(is_published=True, category=category_obj, location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all()).exclude(now_price=0).exclude(stock=0).exists()==False:
                        continue
                    temp_dict = {}
                    temp_dict["name"] = category_obj.get_name(language_code)
                    temp_dict["uuid"] = category_obj.uuid
                    temp_dict["productCount"] = DealsHubProduct.objects.filter(is_published=True, category=category_obj, location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all()).exclude(now_price=0).exclude(stock=0).count()
                    sub_category_objs = SubCategory.objects.filter(category=category_obj)
                    sub_category_list = []
                    for sub_category_obj in sub_category_objs:
                        if DealsHubProduct.objects.filter(is_published=True, sub_category=sub_category_obj, location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all()).exclude(now_price=0).exclude(stock=0).exists()==False:
                            continue
                        temp_dict2 = {}
                        temp_dict2["name"] = sub_category_obj.get_name(language_code)
                        temp_dict2["uuid"] = sub_category_obj.uuid
                        temp_dict2["productCount"] = DealsHubProduct.objects.filter(is_published=True, sub_category=sub_category_obj, location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all()).exclude(now_price=0).exclude(stock=0).count()
                        sub_category_list.append(temp_dict2)
                    if len(sub_category_list)>0:
                        temp_dict["subCategoryList"] = sub_category_list
                        category_list.append(temp_dict)
                    cache.set(location_group_uuid+"-"+str(category_obj.uuid), json.dumps(temp_dict))
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("SearchAPI filter creation: %s at %s", e, str(exc_tb.tb_lineno))

            response["categoryList"] = category_list
            response["brand_list"] = brand_list
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchWIGCategoriesAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchParajohnCategoriesAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchParajohnCategoriesAPI: %s", str(data))
            
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group

            category_list = []
            try:
                category_objs = website_group_obj.categories.all()
                for category_obj in category_objs:
                    temp_dict = {}
                    temp_dict["name"] = category_obj.name
                    temp_dict["uuid"] = category_obj.uuid
                    temp_dict["image"] = category_obj.get_image()
                    sub_category_objs = SubCategory.objects.filter(category=category_obj)
                    sub_category_list = []
                    for sub_category_obj in sub_category_objs:
                        temp_dict2 = {}
                        temp_dict2["name"] = sub_category_obj.name
                        temp_dict2["uuid"] = sub_category_obj.uuid
                        temp_dict2["image"] = sub_category_obj.get_image()
                        sub_category_list.append(temp_dict2)
                    temp_dict["subCategoryList"] = sub_category_list
                    category_list.append(temp_dict)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("FetchParajohnCategoriesAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["categoryList"] = category_list
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchParajohnCategoriesAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
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
            order_index = 0
            for product in products:
                dealshub_product_obj = DealsHubProduct.objects.get(uuid=product)
                CustomProductUnitBanner.objects.create(section=section_obj, product=dealshub_product_obj, order_index=order_index)
                order_index += 1

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
            custom_product_section_objs = CustomProductSection.objects.filter(section=section_obj)
            for custom_product_section_obj in custom_product_section_objs:
                dealshub_product_obj = custom_product_section_obj.product
                dealshub_product_obj.promotion = promotion_obj
                dealshub_product_obj.save()

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
            dealshub_product_uuid_list = list(CustomProductSection.objects.filter(section=section_obj).order_by('order_index').values_list("product__uuid", flat=True).distinct())
            dealshub_product_objs = DealsHubProduct.objects.filter(uuid__in=dealshub_product_uuid_list)

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
            logger.info("PATH %s", str(path))
            path = "http://cdn.omnycomm.com.s3.amazonaws.com/"+path
            dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
            rows = len(dfs.iloc[:])

            uuid = data["uuid"]
            section_obj = Section.objects.get(uuid=uuid)
            location_group_obj = section_obj.location_group

            products = []
            unsuccessful_count = 0

            dealshub_product_uuid_list = list(CustomProductSection.objects.filter(section=section_obj).order_by('order_index').values_list("product__uuid", flat=True).distinct())
            dealshub_product_objs = DealsHubProduct.objects.filter(uuid__in=dealshub_product_uuid_list)
            dealshub_product_objs.update(promotion=None)

            CustomProductSection.objects.filter(section=section_obj).delete()

            for i in range(rows):
                try:
                    product_id = str(dfs.iloc[i][0]).strip()
                    product_id = product_id.split(".")[0]
                    dealshub_product_obj = DealsHubProduct.objects.get(location_group=location_group_obj, product__product_id=product_id, is_published=True)
                    dealshub_product_obj.promotion = section_obj.promotion

                    promotional_price = dealshub_product_obj.now_price
                    try:
                        promotional_price = float(dfs.iloc[i][1])
                    except Exception as e:
                        pass
                    if section_obj.promotion!=None:
                        dealshub_product_obj.promotional_price = promotional_price
                    dealshub_product_obj.save()

                    CustomProductSection.objects.create(section=section_obj, product=dealshub_product_obj, order_index=i)

                    temp_dict = {}
                    temp_dict["thumbnailImageUrl"] = dealshub_product_obj.get_display_image_url()
                    temp_dict["name"] = dealshub_product_obj.get_name()
                    temp_dict["displayId"] = dealshub_product_obj.get_product_id()
                    temp_dict["sellerSku"] = dealshub_product_obj.get_seller_sku()
                    temp_dict["uuid"] = dealshub_product_obj.uuid

                    promotion_obj = dealshub_product_obj.promotion
                    
                    temp_dict["promotional_price"] = dealshub_product_obj.promotional_price
                    temp_dict["now_price"] = dealshub_product_obj.now_price
                    temp_dict["was_price"] = dealshub_product_obj.was_price
                    temp_dict["stock"] = dealshub_product_obj.stock

                    products.append(temp_dict)

                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.warning("SectionBulkUploadAPI: %s at %s", e, str(exc_tb.tb_lineno))
                    unsuccessful_count += 1
                    
            section_obj.save()

            response["products"] = products[:40]
            response["unsuccessful_count"] = unsuccessful_count
            response["filepath"] = path
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SectionBulkUploadAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class BannerBulkUploadAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("BannerBulkUploadAPI: %s", str(data))

            path = default_storage.save('tmp/temp-banner.xlsx', data["import_file"])
            path = "http://cdn.omnycomm.com.s3.amazonaws.com/"+path
            dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
            rows = len(dfs.iloc[:])

            uuid = data["uuid"]
            unit_banner_obj = UnitBannerImage.objects.get(uuid=uuid)
            location_group_obj = unit_banner_obj.banner.location_group


            dealshub_product_uuid_list = list(CustomProductUnitBanner.objects.filter(unit_banner=unit_banner_obj).order_by('order_index').values_list("product__uuid", flat=True).distinct())
            dealshub_product_objs = DealsHubProduct.objects.filter(uuid__in=dealshub_product_uuid_list)
            dealshub_product_objs.update(promotion=None)

            CustomProductUnitBanner.objects.filter(unit_banner=unit_banner_obj).delete()

            products = []
            unsuccessful_count = 0
            
            for i in range(rows):
                try:
                    product_id = str(dfs.iloc[i][0]).strip()
                    product_id = product_id.split(".")[0]
                    dealshub_product_obj = DealsHubProduct.objects.get(location_group=location_group_obj, product__product_id=product_id, is_published=True)
                    CustomProductUnitBanner.objects.create(unit_banner=unit_banner_obj, product=dealshub_product_obj, order_index=i)
                    dealshub_product_obj.promotion = unit_banner_obj.promotion

                    promotional_price = dealshub_product_obj.now_price
                    try:
                        promotional_price = float(dfs.iloc[i][1])
                    except Exception as e:
                        pass
                    if unit_banner_obj.promotion!=None:
                        dealshub_product_obj.promotional_price = promotional_price
                    dealshub_product_obj.save()

                    temp_dict = {}
                    temp_dict["thumbnailImageUrl"] = dealshub_product_obj.get_display_image_url()
                    temp_dict["name"] = dealshub_product_obj.get_name()
                    temp_dict["displayId"] = dealshub_product_obj.get_product_id()
                    temp_dict["sellerSku"] = dealshub_product_obj.get_seller_sku()
                    temp_dict["uuid"] = dealshub_product_obj.uuid

                    promotion_obj = dealshub_product_obj.promotion
                    
                    temp_dict["promotional_price"] = dealshub_product_obj.promotional_price
                    temp_dict["now_price"] = dealshub_product_obj.now_price
                    temp_dict["was_price"] = dealshub_product_obj.was_price
                    temp_dict["stock"] = dealshub_product_obj.stock

                    products.append(temp_dict)

                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.warning("BannerBulkUploadAPI: %s at %s", e, str(exc_tb.tb_lineno))
                    unsuccessful_count += 1
                    
            unit_banner_obj.save()

            response["products"] = products[:40]
            response["unsuccessful_count"] = unsuccessful_count
            response["filepath"] = path
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("BannerBulkUploadAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class SectionBulkDownloadAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SectionBulkDownloadAPI: %s", str(data))

            uuid = data["uuid"]
            section_obj = Section.objects.get(uuid=uuid)

            custom_product_section_objs = CustomProductSection.objects.filter(section=section_obj)
            dealshub_product_uuid_list = list(custom_product_section_objs.order_by('order_index').values_list("product__uuid", flat=True).distinct())
            dealshub_product_objs = DealsHubProduct.objects.filter(uuid__in=dealshub_product_uuid_list)
            dealshub_product_objs = list(dealshub_product_objs)
            dealshub_product_objs.sort(key=lambda t: dealshub_product_uuid_list.index(t.uuid))

            filename = "files/reports/section-products-"+section_obj.name+".xlsx"
            create_section_banner_product_report(dealshub_product_objs, filename)

            response["filepath"] = SERVER_IP+"/"+filename
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SectionBulkDownloadAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class BannerBulkDownloadAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("BannerBulkDownloadAPI: %s", str(data))

            uuid = data["uuid"]
            unit_banner_obj = UnitBannerImage.objects.get(uuid=uuid)

            custom_product_unit_banner_objs = CustomProductUnitBanner.objects.filter(unit_banner=unit_banner_obj)
            dealshub_product_uuid_list = list(custom_product_unit_banner_objs.order_by('order_index').values_list("product__uuid", flat=True).distinct())
            dealshub_product_objs = DealsHubProduct.objects.filter(uuid__in=dealshub_product_uuid_list)
            dealshub_product_objs = list(dealshub_product_objs)
            dealshub_product_objs.sort(key=lambda t: dealshub_product_uuid_list.index(t.uuid))


            filename = "files/reports/banner-products-"+unit_banner_obj.banner.name+".xlsx"
            create_section_banner_product_report(dealshub_product_objs, filename)

            response["filepath"] = SERVER_IP+"/"+filename
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("BannerBulkDownloadAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
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
            language_code = data.get("language","en")

            uuid = data["uuid"]
            banner_image = data["image"]
            image_type = data.get("imageType", "mobile")

            unit_banner_image_obj = UnitBannerImage.objects.get(uuid=uuid)
            image_obj = Image.objects.create(image=banner_image)
            
            if image_type=="mobile":
                if language_code == "en":
                    unit_banner_image_obj.mobile_image = image_obj
                else:
                    unit_banner_image_obj.mobile_image_ar = image_obj
            else:
                if language_code == "en":
                    unit_banner_image_obj.image = image_obj
                else:
                    unit_banner_image_obj.image_ar = image_obj
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

            language_code = data.get("language", "en")

            unit_banner_image_obj = UnitBannerImage.objects.get(uuid=uuid)

            if image_type=="mobile":
                if language_code == "en":
                    unit_banner_image_obj.mobile_image = None
                else:
                    unit_banner_image_obj.mobile_image_ar = None
            else:
                if language_code == "en":
                    unit_banner_image_obj.image = None
                else:
                    unit_banner_image_obj.image_ar = None

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

            dealshub_product_uuid_list = list(CustomProductUnitBanner.objects.filter(unit_banner=unit_banner_obj).order_by('order_index').values_list("product__uuid", flat=True).distinct())
            dealshub_product_objs = DealsHubProduct.objects.filter(uuid__in=dealshub_product_uuid_list)

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
                dealshub_product_uuid_list = list(CustomProductUnitBanner.objects.filter(unit_banner=unit_banner_obj).order_by('order_index').values_list("product__uuid", flat=True).distinct())
                dealshub_product_objs = DealsHubProduct.objects.filter(uuid__in=dealshub_product_uuid_list)
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
            
            custom_product_section_obj = CustomProductSection.objects.get(section=section_obj, product=dealshub_product_obj)
            custom_product_section_obj.delete()
            
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
            language_code = data.get("language","en")
            logger.info("FetchDealshubAdminSectionsAPI: %s", str(data))

            limit = data.get("limit", False)
            is_dealshub = data.get("isDealshub", False)

            is_bot = data.get("isBot", False)

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            resolution = data.get("resolution", "low")

            cache_key = location_group_uuid + "-" + language_code
            if is_dealshub==True and is_bot==False:
                cached_value = cache.get(cache_key, "has_expired")
                if cached_value!="has_expired":
                    response["sections_list"] = json.loads(cached_value)
                    response["circular_category_index"] = location_group_obj.circular_category_index
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
                custom_product_section_objs = CustomProductSection.objects.filter(section=section_obj)
                if is_dealshub==True and custom_product_section_objs.exclude(product__now_price=0).exclude(product__stock=0).exists()==False:
                    continue
                temp_dict = {}
                temp_dict["orderIndex"] = section_obj.order_index
                temp_dict["type"] = "ProductListing"
                temp_dict["uuid"] = str(section_obj.uuid)
                temp_dict["name"] = str(section_obj.get_name(language_code))
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
                    temp_dict["remaining_time"] = None
                else:
                    temp_dict["is_promotional"] = True
                    temp_dict["start_time"] = str(timezone.localtime(promotion_obj.start_time))[:19]
                    temp_dict["end_time"] = str(timezone.localtime(promotion_obj.end_time))[:19]
                    now_time = datetime.datetime.now()
                    total_seconds = (timezone.localtime(promotion_obj.end_time).replace(tzinfo=None) - now_time).total_seconds()
                    temp_dict["remaining_time"] = {
                        "days": int(total_seconds/(3600*24)),
                        "hours": int(total_seconds/3600)%24,
                        "minutes": int(total_seconds/60)%60,
                        "seconds": int(total_seconds)%60
                    }
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

                promo_slider_img = section_obj.get_promo_slider_image(language_code)
                if promo_slider_img is not None:
                    temp_dict["promoSliderUuid"] = promo_slider_img.pk
                    temp_dict["promoSliderUrl"] = promo_slider_img.image.url

                temp_products = []

                custom_product_section_objs = CustomProductSection.objects.filter(section=section_obj)
                if is_dealshub==True:
                    custom_product_section_objs = custom_product_section_objs.exclude(product__now_price=0).exclude(product__stock=0)

                dealshub_product_uuid_list = list(custom_product_section_objs.order_by('order_index').values_list("product__uuid", flat=True).distinct())
                
                section_products = DealsHubProduct.objects.filter(uuid__in=dealshub_product_uuid_list)
                
                section_products = list(section_products)
                section_products.sort(key=lambda t: dealshub_product_uuid_list.index(t.uuid))
                
                section_products = section_products[:40]
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
                    temp_dict2["optimizedThumbnailImageUrl"] = dealshub_product_obj.get_optimized_display_image_url()
                    temp_dict2["name"] = dealshub_product_obj.get_name(language_code)
                    temp_dict2["sellerSku"] = dealshub_product_obj.get_seller_sku()
                    temp_dict2["brand"] = dealshub_product_obj.get_brand(language_code)
                    temp_dict2["displayId"] = dealshub_product_obj.get_product_id()
                    temp_dict2["uuid"] = dealshub_product_obj.uuid
                    temp_dict2["link"] = dealshub_product_obj.url

                    if is_dealshub==True:
                        temp_dict2["category"] = dealshub_product_obj.get_category(language_code)
                        temp_dict2["currency"] = dealshub_product_obj.get_currency()

                    promotion_obj = dealshub_product_obj.promotion
                    
                    temp_dict2["promotional_price"] = dealshub_product_obj.promotional_price
                    temp_dict2["now_price"] = dealshub_product_obj.now_price
                    temp_dict2["was_price"] = dealshub_product_obj.was_price
                    temp_dict2["stock"] = dealshub_product_obj.stock
                    temp_dict2["is_new_arrival"] = dealshub_product_obj.is_new_arrival
                    temp_dict2["is_on_sale"] = dealshub_product_obj.is_on_sale
                    temp_dict2["allowedQty"] = dealshub_product_obj.get_allowed_qty()
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
                    temp_dict2["url-ar"] = ""
                    if unit_banner_image_obj.image!=None:
                        if resolution=="low":
                            temp_dict2["url"] = unit_banner_image_obj.image.mid_image.url
                            if unit_banner_image_obj.image_ar!=None:
                                temp_dict2["url-ar"] = unit_banner_image_obj.image_ar.mid_image.url
                            else:
                                temp_dict2["url-ar"] = ""
                        else:
                            temp_dict2["url-jpg"] = unit_banner_image_obj.image.image.url
                            temp_dict2["url"] = unit_banner_image_obj.image.image.url
                            temp_dict2["urlWebp"] = unit_banner_image_obj.image.webp_image.url
                            if unit_banner_image_obj.image_ar!=None:
                                temp_dict2["url-jpg-ar"] = unit_banner_image_obj.image_ar.image.url
                                temp_dict2["url-ar"] = unit_banner_image_obj.image_ar.image.url
                                temp_dict2["urlWebp-ar"] = unit_banner_image_obj.image_ar.webp_image.url
                            else:
                                temp_dict2["url-jpg-ar"] = unit_banner_image_obj.image.image.url
                                temp_dict2["url-ar"] = unit_banner_image_obj.image.image.url
                                temp_dict2["urlWebp-ar"] = unit_banner_image_obj.image.webp_image.url


                    temp_dict2["mobileUrl"] = ""
                    temp_dict2["mobileUrl-ar"] = ""
                    if unit_banner_image_obj.mobile_image!=None:
                        if resolution=="low":
                            temp_dict2["mobileUrl"] = unit_banner_image_obj.mobile_image.mid_image.url
                            if unit_banner_image_obj.mobile_image_ar!=None:
                                temp_dict2["mobileUrl-ar"] = unit_banner_image_obj.mobile_image_ar.mid_image.url
                            else:
                                temp_dict2["mobileUrl-ar"] = ""
                        else:
                            temp_dict2["mobileUrl-jpg"] = unit_banner_image_obj.mobile_image.image.url
                            temp_dict2["mobileUrl"] = unit_banner_image_obj.mobile_image.image.url
                            temp_dict2["mobileUrlWebp"] = unit_banner_image_obj.mobile_image.webp_image.url
                            if unit_banner_image_obj.mobile_image_ar!=None:
                                temp_dict2["mobileUrl-jpg-ar"] = unit_banner_image_obj.mobile_image_ar.image.url
                                temp_dict2["mobileUrl-ar"] = unit_banner_image_obj.mobile_image_ar.image.url
                                temp_dict2["mobileUrlWebp-ar"] = unit_banner_image_obj.mobile_image_ar.webp_image.url
                            else:
                                temp_dict2["mobileUrl-jpg-ar"] = unit_banner_image_obj.mobile_image.image.url
                                temp_dict2["mobileUrl-ar"] = unit_banner_image_obj.mobile_image.image.url
                                temp_dict2["mobileUrlWebp-ar"] = unit_banner_image_obj.mobile_image.webp_image.url

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
                        temp_dict2["start_time"] = str(timezone.localtime(promotion_obj.start_time))[:19]
                        temp_dict2["end_time"] = str(timezone.localtime(promotion_obj.end_time))[:19]
                        temp_dict2["promotion_tag"] = str(promotion_obj.promotion_tag)


                    custom_product_unit_banner_objs = CustomProductUnitBanner.objects.filter(unit_banner=unit_banner_image_obj)
                    if is_dealshub==True:
                        custom_product_unit_banner_objs = custom_product_unit_banner_objs.exclude(product__now_price=0).exclude(product__stock=0)

                    dealshub_product_uuid_list = list(custom_product_unit_banner_objs.order_by('order_index').values_list("product__uuid", flat=True).distinct())
                    unit_banner_products = DealsHubProduct.objects.filter(uuid__in=dealshub_product_uuid_list)

                    unit_banner_products = list(unit_banner_products)
                    unit_banner_products.sort(key=lambda t: dealshub_product_uuid_list.index(t.uuid))

                    if is_dealshub==False :
                        temp_products = []
                        for dealshub_product_obj in unit_banner_products[:40]:
                            if dealshub_product_obj.now_price==0:
                                continue
                            temp_dict3 = {}

                            temp_dict3["thumbnailImageUrl"] = dealshub_product_obj.get_display_image_url()
                            temp_dict3["optimizedThumbnailImageUrl"] = dealshub_product_obj.get_optimized_display_image_url()
                            temp_dict3["name"] = dealshub_product_obj.get_name(language_code)
                            temp_dict3["displayId"] = dealshub_product_obj.get_product_id()
                            temp_dict3["sellerSku"] = dealshub_product_obj.get_seller_sku()
                            temp_dict3["brand"] = dealshub_product_obj.get_brand(language_code)
                            temp_dict3["uuid"] = dealshub_product_obj.uuid
                            temp_dict3["link"] = dealshub_product_obj.url

                            promotion_obj = dealshub_product_obj.promotion
                            
                            temp_dict3["promotional_price"] = dealshub_product_obj.promotional_price
                            temp_dict3["now_price"] = dealshub_product_obj.now_price
                            temp_dict3["was_price"] = dealshub_product_obj.was_price
                            temp_dict3["stock"] = dealshub_product_obj.stock
                            temp_dict3["allowedQty"] = dealshub_product_obj.get_allowed_qty()
                            if dealshub_product_obj.stock>0:
                                temp_dict3["isStockAvailable"] = True
                            else:
                                temp_dict3["isStockAvailable"] = False

                            temp_products.append(temp_dict3)    # No need to Send all
                        temp_dict2["products"] = temp_products
                    
                    temp_dict2["has_products"] = len(unit_banner_products)>0
                    banner_images.append(temp_dict2)

                temp_dict["bannerImages"] = banner_images
                temp_dict["isPublished"] = banner_obj.is_published

                dealshub_admin_sections.append(temp_dict)

            dealshub_admin_sections = sorted(dealshub_admin_sections, key = lambda i: i["orderIndex"])

            if is_dealshub==True:
                cache.set(cache_key, json.dumps(dealshub_admin_sections))

            response["sections_list"] = dealshub_admin_sections
            response["circular_category_index"] = location_group_obj.circular_category_index
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
                dealshub_product_uuid_list = list(CustomProductSection.objects.filter(section=section_obj).order_by("order_index").values_list("product__uuid", flat=True).distinct())
                dealshub_product_objs = dealshub_product_objs.exclude(uuid__in=dealshub_product_uuid_list)[:10]
            elif type=="Banner":
                unit_banner_image_obj = UnitBannerImage.objects.get(uuid=section_uuid)
                dealshub_product_uuid_list = list(CustomProductUnitBanner.objects.filter(unit_banner=unit_banner_image_obj).order_by("order_index").values_list("product__uuid", flat=True).distinct())
                dealshub_product_objs = dealshub_product_objs.exclude(uuid__in=dealshub_product_uuid_list)[:10]
            else:
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
            language_code = data.get("language","en")
            logger.info("SearchProductsAutocompleteAPI: %s", str(data))

            search_string = data["searchString"]
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group

            available_dealshub_products = DealsHubProduct.objects.filter(location_group=location_group_obj, is_published=True, product__base_product__brand__in=website_group_obj.brands.all()).exclude(now_price=0).exclude(stock=0)

            search_tags = search_string.split(" ")
            target_brand = None
            for search_tag in search_tags:
                if website_group_obj.brands.filter(Q(name=search_tag) | Q(name_ar=search_tag)).exists():
                    target_brand = website_group_obj.brands.filter(Q(name=search_tag) | Q(name_ar=search_tag))[0]
                    search_tags.remove(search_tag)
                    break
            if target_brand!=None:
                available_dealshub_products = available_dealshub_products.filter(product__base_product__brand=target_brand)

            if len(search_tags)>0:
                search_string = remove_stopwords(search_string)
                words = search_string.split(" ")

                if len(words)==1:
                    available_dealshub_products = available_dealshub_products.filter(Q(product__product_name__icontains=words[0]) | Q(product__base_product__seller_sku__icontains=words[0]))
                elif len(words)==2:
                    if available_dealshub_products.filter(product__product_name__icontains=search_string).exists():
                        available_dealshub_products = available_dealshub_products.filter(product__product_name__icontains=search_string)
                    else:
                        if available_dealshub_products.filter(product__product_name__icontains=words[0]).filter(product__product_name__icontains=words[1]).exists():
                            available_dealshub_products = available_dealshub_products.filter(product__product_name__icontains=words[0]).filter(product__product_name__icontains=words[1])
                        else:
                            available_dealshub_products = available_dealshub_products.filter(Q(product__product_name__icontains=words[0]) | Q(product__product_name__icontains=words[1]))
                elif len(words)==3:
                    if available_dealshub_products.filter(product__product_name__icontains=search_string).exists():
                        available_dealshub_products = available_dealshub_products.filter(product__product_name__icontains=search_string)
                    else:
                        if available_dealshub_products.filter(product__product_name__icontains=words[0]).filter(product__product_name__icontains=words[1]).filter(product__product_name__icontains=words[2]).exists():
                            available_dealshub_products = available_dealshub_products.filter(product__product_name__icontains=words[0]).filter(product__product_name__icontains=words[1]).filter(product__product_name__icontains=words[2])
                        else:
                            temp_available_dealshub_products = available_dealshub_products.filter(product__product_name__icontains=words[0]).filter(product__product_name__icontains=words[1])
                            temp_available_dealshub_products |= available_dealshub_products.filter(product__product_name__icontains=words[1]).filter(product__product_name__icontains=words[2])
                            temp_available_dealshub_products |= available_dealshub_products.filter(product__product_name__icontains=words[0]).filter(product__product_name__icontains=words[2])
                            if temp_available_dealshub_products.exists()==False:
                                temp_available_dealshub_products = available_dealshub_products.filter(product__product_name__icontains=words[0])
                                temp_available_dealshub_products |= available_dealshub_products.filter(product__product_name__icontains=words[1])
                                temp_available_dealshub_products |= available_dealshub_products.filter(product__product_name__icontains=words[2])
                            available_dealshub_products = temp_available_dealshub_products
                else:
                    if available_dealshub_products.filter(product__product_name__icontains=search_string).exists():
                        available_dealshub_products = available_dealshub_products.filter(product__product_name__icontains=search_string)
                    else:
                        if len(words)>0:
                            search_results = DealsHubProduct.objects.none()
                            for word in words:
                                search_results |= available_dealshub_products.filter(Q(product__product_name__icontains=word) | Q(product__base_product__seller_sku__icontains=word))
                            available_dealshub_products = search_results.distinct()

                # search_results = DealsHubProduct.objects.none()
                # for search_tag in search_tags:
                #     search_results |= available_dealshub_products.filter(Q(product__product_name__icontains=search_tag) | Q(product__base_product__seller_sku__icontains=search_tag))
                # available_dealshub_products = search_results.distinct()

            category_key_list = available_dealshub_products.values('category').annotate(dcount=Count('category')).order_by('-dcount')[:5]

            category_list = []
            category_list_en = []
            for category_key in category_key_list:
                try:
                    category_obj = Category.objects.get(pk=category_key["category"])
                    category_name = category_obj.get_name(language_code)
                    category_list.append(category_name)
                    category_name_en = category_obj.get_name("en")
                    category_list_en.append(category_name_en)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.warning("SearchProductsAutocompleteAPI: %s at %s", e, str(exc_tb.tb_lineno))

            category_list = list(set(category_list))
            category_list_en = list(set(category_list_en))

            response["categoryList"] = category_list
            response["categoryListEn"] = category_list_en
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchProductsAutocompleteAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class SearchProductsAutocomplete2API(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("SearchProductsAutocomplete2API: %s", str(data))

            search_string = data["searchString"]
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group

            available_dealshub_products = DealsHubProduct.objects.filter(location_group=location_group_obj, is_published=True, product__base_product__brand__in=website_group_obj.brands.all()).exclude(now_price=0).exclude(stock=0)

            if search_string!="":
                search_string = remove_stopwords(search_string)
                words = search_string.split(" ")
                target_brand = None
                for word in words:
                    if website_group_obj.brands.filter(name=word).exists():
                        target_brand = website_group_obj.brands.filter(name=word)[0]
                        words.remove(word)
                        break
                if target_brand!=None:
                    available_dealshub_products = available_dealshub_products.filter(product__base_product__brand=target_brand)
                if len(words)==1:
                    available_dealshub_products = available_dealshub_products.filter(Q(search_keywords__icontains=","+words[0]+","))
                elif len(words)==2:
                    if available_dealshub_products.filter(search_keywords__icontains=","+search_string+",").exists():
                        available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+search_string+",")
                    else:
                        if available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",").exists():
                            available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",")
                        else:
                            available_dealshub_products = available_dealshub_products.filter(Q(search_keywords__icontains=","+words[0]+",") | Q(search_keywords__icontains=","+words[1]+","))
                elif len(words)==3:
                    if available_dealshub_products.filter(search_keywords__icontains=","+search_string+",").exists():
                        available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+search_string+",")
                    else:
                        if available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",").filter(search_keywords__icontains=","+words[2]+",").exists():
                            available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",").filter(search_keywords__icontains=","+words[2]+",")
                        else:
                            temp_available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=words[0]).filter(search_keywords__icontains=words[1])
                            temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[1]).filter(search_keywords__icontains=words[2])
                            temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[0]).filter(search_keywords__icontains=words[2])
                            if temp_available_dealshub_products.exists()==False:
                                temp_available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=words[0])
                                temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[1])
                                temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[2])
                            available_dealshub_products = temp_available_dealshub_products.distinct()
                else:
                    if available_dealshub_products.filter(search_keywords__icontains=","+search_string+",").exists():
                        available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+search_string+",")
                    else:
                        if len(words)>0:
                            search_results = DealsHubProduct.objects.none()
                            for word in words:
                                search_results |= available_dealshub_products.filter(search_keywords__icontains=","+word+",")
                            available_dealshub_products = search_results.distinct()

            category_key_list = available_dealshub_products.values('category').annotate(dcount=Count('category')).order_by('-dcount')[:5]

            category_list = []
            for category_key in category_key_list:
                try:
                    category_name = Category.objects.get(pk=category_key["category"]).name
                    category_list.append(category_name)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.warning("SearchProductsAutocomplete2API: %s at %s", e, str(exc_tb.tb_lineno))

            category_list = list(set(category_list))

            response["categoryList"] = category_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchProductsAutocomplete2API: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class SearchProductsAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("SearchProductsAPI: %s", str(data))

            language_code = data.get("language","en")
            search_string = data["searchString"]
            location_group_uuid = data["locationGroupUuid"]

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group

            dealshub_product_objs = DealsHubProduct.objects.filter(is_published=True, location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all()).exclude(now_price=0).exclude(stock=0)

            dealshub_product_objs = dealshub_product_objs.filter(Q(product__base_product__seller_sku__icontains=search_string) | Q(product__product_name__icontains=search_string) | Q(product_name_ar__icontains=search_string))

            dealshub_product_objs = dealshub_product_objs[:10]

            dealshub_product_list = []
            for dealshub_product_obj in dealshub_product_objs:
                temp_dict = {}
                temp_dict["name"] = dealshub_product_obj.get_name(language_code)
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
            company_data["contact_info"] = json.loads(website_group_obj.contact_info)
            company_data["whatsapp_info"] = website_group_obj.whatsapp_info
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

            company_data["color_scheme"] = json.loads(website_group_obj.color_scheme)


            company_data["logo_url"] = ""
            if website_group_obj.logo != None:
                company_data["logo_url"] = website_group_obj.logo.image.url

            company_data["footer_logo_url"] = ""
            if website_group_obj.footer_logo != None:
                company_data["footer_logo_url"] = website_group_obj.footer_logo.image.url

            company_data["logo_ar_url"] = ""
            if website_group_obj.logo_ar != None:
                company_data["logo_ar_url"] = website_group_obj.logo_ar.image.url

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
            response["allowedQty"] = str(dealshub_product_obj.get_allowed_qty())

            if CustomProductSection.objects.filter(section=section_obj, product=dealshub_product_obj).exists()==False:
                order_index = 0
                if CustomProductSection.objects.filter(section=section_obj).count()>0:
                    order_index = CustomProductSection.objects.filter(section=section_obj).order_by("order_index").last().order_index+1
                CustomProductSection.objects.create(section=section_obj, product=dealshub_product_obj, order_index=order_index)
            
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
            language_code = data.get("language","en")
            logger.info("FetchWebsiteGroupBrandsAPI: %s", str(data))

            website_group_name = data["websiteGroupName"]
            website_group_obj = WebsiteGroup.objects.get(name=website_group_name)

            brand_objs = website_group_obj.brands.all()[:100]
            brand_list = []
            for brand_obj in brand_objs:
                temp_dict = {}
                temp_dict["name"] = brand_obj.get_name(language_code)
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
            response["allowedQty"] = str(dealshub_product_obj.get_allowed_qty())

            if CustomProductUnitBanner.objects.filter(unit_banner=unit_banner_image_obj, product=dealshub_product_obj).exists()==False:
                order_index = 0
                if CustomProductUnitBanner.objects.filter(unit_banner=unit_banner_image_obj).count()>0:
                    order_index = CustomProductUnitBanner.objects.filter(unit_banner=unit_banner_image_obj).order_by("order_index").last().order_index+1
                CustomProductUnitBanner.objects.create(unit_banner=unit_banner_image_obj, product=dealshub_product_obj, order_index=order_index)
            
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

            
            custom_product_unit_banner_obj = CustomProductUnitBanner.objects.get(unit_banner=unit_banner_image_obj, product=dealshub_product_obj)
            custom_product_unit_banner_obj.delete()

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
            language_code = data.get("language","en")
            unit_banner_image_uuid = data["unitBannerImageUuid"]
            
            unit_banner_image_obj = UnitBannerImage.objects.get(uuid=unit_banner_image_uuid)

            custom_product_unit_banner_objs = CustomProductUnitBanner.objects.filter(unit_banner=unit_banner_image_obj, product__is_published=True)
            custom_product_unit_banner_objs = custom_product_unit_banner_objs.exclude(product__now_price=0).exclude(product__stock=0)
            dealshub_product_uuid_list = list(custom_product_unit_banner_objs.order_by('order_index').values_list("product__uuid", flat=True).distinct())
            dealshub_product_objs = DealsHubProduct.objects.filter(uuid__in=dealshub_product_uuid_list)
            dealshub_product_objs = list(dealshub_product_objs)
            dealshub_product_objs.sort(key=lambda t: dealshub_product_uuid_list.index(t.uuid))


            page = int(data.get('page', 1))
            paginator = Paginator(dealshub_product_objs, 50)
            dealshub_product_objs = paginator.page(page)

            product_list = []
            for dealshub_product_obj in dealshub_product_objs:
                if dealshub_product_obj.get_actual_price()==0:
                    continue
                temp_dict = {}
                temp_dict["name"] = dealshub_product_obj.get_name(language_code)
                temp_dict["brand"] = dealshub_product_obj.get_brand(language_code)
                temp_dict["seller_sku"] = dealshub_product_obj.get_seller_sku()
                temp_dict["now_price"] = dealshub_product_obj.now_price
                temp_dict["was_price"] = dealshub_product_obj.was_price
                temp_dict["promotional_price"] = dealshub_product_obj.promotional_price
                temp_dict["stock"] = dealshub_product_obj.stock
                temp_dict["is_new_arrival"] = dealshub_product_obj.is_new_arrival
                temp_dict["is_on_sale"] = dealshub_product_obj.is_on_sale
                temp_dict["allowedQty"] = dealshub_product_obj.get_allowed_qty()
                temp_dict["isStockAvailable"] = dealshub_product_obj.stock>0
                temp_dict["is_promotional"] = dealshub_product_obj.promotion!=None
                if dealshub_product_obj.promotion!=None:
                    temp_dict["promotion_tag"] = dealshub_product_obj.promotion.promotion_tag
                else:
                    temp_dict["promotion_tag"] = None
                temp_dict["currency"] = dealshub_product_obj.get_currency()
                temp_dict["uuid"] = dealshub_product_obj.uuid
                temp_dict["link"] = dealshub_product_obj.url
                temp_dict["id"] = dealshub_product_obj.uuid
                temp_dict["heroImageUrl"] = dealshub_product_obj.get_display_image_url()
                
                product_list.append(temp_dict)

            is_available = True
            if paginator.num_pages == page:
                is_available = False

            response["is_available"] = is_available
            response["totalPages"] = paginator.num_pages
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


class AddSectionPromoSliderImageAPI(APIView):

    def post(self, request, *args, **kwargs):
    
        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("AddSectionPromoSliderImageAPI: %s", str(data))

            uuid = data["uuid"]
            promo_slider_image = data["image"]
            language_code = data.get("language","en")

            section_obj = Section.objects.get(uuid=uuid)
            image_obj = Image.objects.create(image=promo_slider_image)
            if language_code == "ar":
                section_obj.promo_slider_image_ar = image_obj
            else:
                section_obj.promo_slider_image = image_obj
            section_obj.save()

            response['uuid'] = image_obj.pk
            response['url'] = image_obj.image.url
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddSectionPromoSliderImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchSectionPromoSliderImageAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchSectionPromoSliderImageAPI: %s", str(data))
            uuid = data["uuid"]
            language_code = data.get("language","en")

            section_obj = Section.objects.get(uuid=uuid)

            if section_obj.get_promo_slider_image(language_code) is not None:
                response["url"] = section_obj.get_promo_slider_image(language_code).image.url
            else:
                response["url"] = ""

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSectionPromoSliderImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
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
            
            dealshub_product_uuid_list = list(CustomProductUnitBanner.objects.filter(unit_banner=unit_banner_obj).order_by("order_index").values_list("product__uuid", flat=True).distinct())
            dealshub_product_objs = DealsHubProduct.objects.filter(uuid__in=dealshub_product_uuid_list)

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
            description = data.get("description", "")
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
                                                 location_group=location_group_obj,
                                                 description=description)

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
            voucher_obj.description = data["description"]

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
                temp_dict["description"] = voucher_obj.description

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


class FetchPostaPlusDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchPostaPlusDetailsAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            uuid = data["orderUuid"]
            order_obj = Order.objects.get(uuid=uuid)

            ship_date = str(datetime.datetime.strftime(order_obj.order_placed_date, "%d-%b-%Y"))

            postaplus_info = json.loads(order_obj.location_group.postaplus_info)
            consignee_from_address = postaplus_info["consignee_from_address"]+"\n"+postaplus_info["consignee_from_mobile"]
            consignee_from_address = consignee_from_address.replace("\n", "<br/>")
            consignee_to_address = order_obj.shipping_address.get_shipping_address()
            consignee_to_address = consignee_to_address.replace("\n", "<br/>")

            total_pieces = 0
            description = ""
            total_weight = 0
            for unit_order_obj in UnitOrder.objects.filter(order=order_obj):
                total_weight += unit_order_obj.product.get_weight()
                description += unit_order_obj.product.get_seller_sku()+" ("+str(unit_order_obj.quantity)+"), "
                total_pieces += unit_order_obj.quantity
            total_weight = max(total_weight, 0.5)

            cod_currency = order_obj.get_currency()
            cod_amt = 0
            if order_obj.payment_mode=="COD":
                cod_amt = order_obj.to_pay

            reference2 = order_obj.bundleid
            shipper = postaplus_info["consignee_company"]

            response["ship_date"] = ship_date 
            response["consignee_from_address"] = consignee_from_address 
            response["consignee_to_address"] = consignee_to_address
            response["weight"] = str(total_weight)
            response["total_pieces"] = str(total_pieces)
            response["cod_amt"] = str(cod_amt)
            response["cod_currency"] = cod_currency
            response["description"] = description
            response["reference2"] = reference2
            response["shipper"] = shipper
            response["awb_number"] = json.loads(order_obj.postaplus_info)["awb_number"]

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchPostaPlusDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UpdateUnitOrderQtyAdminAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UpdateUnitOrderQtyAdminAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            uuid = data["unitOrderUuid"]
            quantity = int(data["quantity"])

            unit_order_obj = UnitOrder.objects.get(uuid=uuid)
            order_obj = unit_order_obj.order

            if quantity==0:
                if UnitOrder.objects.filter(order=order_obj).count()==1:
                    response["message"] = "order cannot be empty"
                    return Response(data=response)
                else:
                    unit_order_obj.delete()
            else:
                unit_order_obj.quantity = quantity
                unit_order_obj.save()

            update_order_bill(order_obj)

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateUnitOrderQtyAdminAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UpdateOrderShippingAdminAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UpdateOrderShippingAdminAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            uuid = data["orderUuid"]

            order_obj = Order.objects.get(uuid=uuid)

            location_group_obj = order_obj.location_group
            dealshub_user_obj = order_obj.owner

            first_name = data["firstName"]
            last_name = data.get("lastName", "")
            line1 = data["line1"]
            line2 = data["line2"]
            line3 = ""
            line4 = location_group_obj.location.name
            address_lines = json.dumps([line1, line2, line3, line4])
            state = ""
            postcode = ""
            contact_number = data["contact_number"]
            tag = "Home"
            emirates = data.get("emirates", "")

            address_obj = Address.objects.create(first_name=first_name, 
                                                 last_name=last_name, 
                                                 address_lines=address_lines, 
                                                 state=state, 
                                                 postcode=postcode, 
                                                 contact_number=contact_number, 
                                                 user=dealshub_user_obj, 
                                                 tag=tag, 
                                                 location_group=location_group_obj,
                                                 emirates=emirates)
            order_obj.shipping_address = address_obj
            order_obj.save()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateOrderShippingAdminAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchSEODetailsAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchSEODetailsAPI: %s", str(data))
            
            page_type = data["page_type"]
            name = data["name"]
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            page_description = ""
            seo_title = ""
            seo_keywords = ""
            seo_description = ""

            if page_type=="super_category":
                seo_super_category_obj = SEOSuperCategory.objects.get(super_category__name=name, location_group=location_group_obj)
                page_description = seo_super_category_obj.page_description
                seo_title = seo_super_category_obj.seo_title
                seo_keywords = seo_super_category_obj.seo_keywords
                seo_description = seo_super_category_obj.seo_description
            elif page_type=="category":
                seo_category_obj = SEOCategory.objects.filter(category__name=name, location_group=location_group_obj)[0]
                page_description = seo_category_obj.page_description
                seo_title = seo_category_obj.seo_title
                seo_keywords = seo_category_obj.seo_keywords
                seo_description = seo_category_obj.seo_description
            elif page_type=="sub_category":
                seo_sub_category_obj = SEOSubCategory.objects.filter(sub_category__name=name, location_group=location_group_obj)[0]
                page_description = seo_sub_category_obj.page_description
                seo_title = seo_sub_category_obj.seo_title
                seo_keywords = seo_sub_category_obj.seo_keywords
                seo_description = seo_sub_category_obj.seo_description
            elif page_type=="brand":
                seo_brand_obj = SEOBrand.objects.get(brand__name=name, location_group=location_group_obj, brand__organization__name="WIG")
                page_description = seo_brand_obj.page_description
                seo_title = seo_brand_obj.seo_title
                seo_keywords = seo_brand_obj.seo_keywords
                seo_description = seo_brand_obj.seo_description
            elif page_type=="product":
                dealshub_product_obj = DealsHubProduct.objects.get(uuid=name)
                page_description = dealshub_product_obj.page_description
                seo_title = dealshub_product_obj.seo_title
                seo_keywords = dealshub_product_obj.seo_keywords
                seo_description = dealshub_product_obj.seo_description
            elif page_type=="brand_super_category":
                brand_obj = Brand.objects.get(name=name, organization__name="WIG")
                super_category_name = data["super_category_name"]
                super_category_obj = SuperCategory.objects.get(name=super_category_name)
                brand_super_category_obj = BrandSuperCategory.objects.get(brand=brand_obj, super_category=super_category_obj, location_group=location_group_obj)
                page_description = brand_super_category_obj.page_description
                seo_title = brand_super_category_obj.seo_title
                seo_keywords = brand_super_category_obj.seo_keywords
                seo_description = brand_super_category_obj.seo_description
            elif page_type=="brand_category":
                brand_obj = Brand.objects.get(name=name, organization__name="WIG")
                category_name = data["category_name"]
                category_obj = Category.objects.get(name=category_name)
                brand_category_obj = BrandCategory.objects.get(brand=brand_obj, category=category_obj, location_group=location_group_obj)
                page_description = brand_category_obj.page_description
                seo_title = brand_category_obj.seo_title
                seo_keywords = brand_category_obj.seo_keywords
                seo_description = brand_category_obj.seo_description
            elif page_type=="brand_sub_category":
                brand_obj = Brand.objects.get(name=name, organization__name="WIG")
                sub_category_name = data["sub_category_name"]
                sub_category_obj = SubCategory.objects.get(name=sub_category_name)
                brand_sub_category_obj = BrandSubCategory.objects.get(brand=brand_obj, sub_category=sub_category_obj, location_group=location_group_obj)
                page_description = brand_sub_category_obj.page_description
                seo_title = brand_sub_category_obj.seo_title
                seo_keywords = brand_sub_category_obj.seo_keywords
                seo_description = brand_sub_category_obj.seo_description


            response["page_description"] = page_description
            response["seo_title"] = seo_title
            response["seo_keywords"] = seo_keywords
            response["seo_description"] = seo_description
            
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSEODetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchSEOAdminAutocompleteAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchSEOAdminAutocompleteAPI: %s", str(data))
            
            page_type = data["page_type"]
            search_string = data["search_string"]
            location_group_uuid = data["locationGroupUuid"]

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            autocomplete_list = []
            if page_type=="super_category":
                seo_super_category_objs = SEOSuperCategory.objects.filter(super_category__name__icontains=search_string, location_group=location_group_obj)[:5]
                for seo_super_category_obj in seo_super_category_objs:
                    temp_dict = {}
                    temp_dict["name"] = seo_super_category_obj.super_category.name
                    temp_dict["uuid"] = seo_super_category_obj.uuid
                    autocomplete_list.append(temp_dict)
            elif page_type=="category":
                seo_category_objs = SEOCategory.objects.filter(category__name__icontains=search_string, location_group=location_group_obj)[:5]
                for seo_category_obj in seo_category_objs:
                    temp_dict = {}
                    temp_dict["name"] = seo_category_obj.category.name
                    temp_dict["uuid"] = seo_category_obj.uuid
                    autocomplete_list.append(temp_dict)
            elif page_type=="sub_category":
                seo_sub_category_objs = SEOSubCategory.objects.filter(sub_category__name__icontains=search_string, location_group=location_group_obj)[:5]
                for seo_sub_category_obj in seo_sub_category_objs:
                    temp_dict = {}
                    temp_dict["name"] = seo_sub_category_obj.sub_category.name
                    temp_dict["uuid"] = seo_sub_category_obj.uuid
                    autocomplete_list.append(temp_dict)
            elif page_type=="brand":
                seo_brand_objs = SEOBrand.objects.filter(brand__name__icontains=search_string, location_group=location_group_obj, brand__organization__name="WIG")
                for seo_brand_obj in seo_brand_objs:
                    temp_dict = {}
                    temp_dict["name"] = seo_brand_obj.brand.name
                    temp_dict["uuid"] = seo_brand_obj.brand.name
                    autocomplete_list.append(temp_dict)
            elif page_type=="product":
                dealshub_product_objs = DealsHubProduct.objects.filter(product_name__icontains=search_string, location_group=location_group_obj)[:5]
                for dealshub_product_obj in dealshub_product_objs:
                    temp_dict = {}
                    temp_dict["name"] = dealshub_product_obj.get_name()
                    temp_dict["uuid"] = dealshub_product_obj.uuid
                    autocomplete_list.append(temp_dict)
            elif page_type=="brand_super_category":
                brand_name = data["brand_name"]
                brand_super_category_objs = BrandSuperCategory.objects.filter(brand__name__icontains=brand_name, super_category__name__icontains=search_string, location_group=location_group_obj, brand__organization__name="WIG")[:5]
                for brand_super_category_obj in brand_super_category_objs:
                    temp_dict = {}
                    temp_dict["name"] = brand_super_category_obj.super_category.name
                    temp_dict["uuid"] = brand_super_category_obj.uuid
                    autocomplete_list.append(temp_dict)
            elif page_type=="brand_category":
                brand_name = data["brand_name"]
                brand_category_objs = BrandCategory.objects.filter(brand__name__icontains=brand_name, category__name__icontains=search_string, location_group=location_group_obj, brand__organization__name="WIG")[:5]
                for brand_category_obj in brand_category_objs:
                    temp_dict = {}
                    temp_dict["name"] = brand_category_obj.category.name
                    temp_dict["uuid"] = brand_category_obj.uuid
                    autocomplete_list.append(temp_dict)
            elif page_type=="brand_sub_category":
                brand_name = data["brand_name"]
                brand_sub_category_objs = BrandSubCategory.objects.filter(brand__name__icontains=brand_name, sub_category__name__icontains=search_string, location_group=location_group_obj, brand__organization__name="WIG")[:5]
                for brand_sub_category_obj in brand_sub_category_objs:
                    temp_dict = {}
                    temp_dict["name"] = brand_sub_category_obj.sub_category.name
                    temp_dict["uuid"] = brand_sub_category_obj.uuid
                    autocomplete_list.append(temp_dict)

            response["autocomplete_list"] = autocomplete_list
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSEOAdminAutocompleteAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchSEOAdminDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchSEOAdminDetailsAPI: %s", str(data))
            
            page_type = data["page_type"]
            uuid = data["uuid"]

            page_description = ""
            seo_title = ""
            seo_keywords = ""
            seo_description = ""
            short_description = ""
            long_description = ""

            if page_type=="super_category":
                seo_super_category_obj = SEOSuperCategory.objects.get(uuid=uuid)
                page_description = seo_super_category_obj.page_description
                seo_title = seo_super_category_obj.seo_title
                seo_keywords = seo_super_category_obj.seo_keywords
                seo_description = seo_super_category_obj.seo_description
                short_description = seo_super_category_obj.short_description
                long_description = seo_super_category_obj.long_description
            elif page_type=="category":
                seo_category_obj = SEOCategory.objects.get(uuid=uuid)
                page_description = seo_category_obj.page_description
                seo_title = seo_category_obj.seo_title
                seo_keywords = seo_category_obj.seo_keywords
                seo_description = seo_category_obj.seo_description
                short_description = seo_category_obj.short_description
                long_description = seo_category_obj.long_description
            elif page_type=="sub_category":
                seo_sub_category_obj = SEOSubCategory.objects.get(uuid=uuid)
                page_description = seo_sub_category_obj.page_description
                seo_title = seo_sub_category_obj.seo_title
                seo_keywords = seo_sub_category_obj.seo_keywords
                seo_description = seo_sub_category_obj.seo_description
                short_description = seo_sub_category_obj.short_description
                long_description = seo_sub_category_obj.long_description
            elif page_type=="brand":
                seo_brand_obj = SEOBrand.objects.get(brand__name=uuid, brand__organization__name="WIG")
                page_description = seo_brand_obj.page_description
                seo_title = seo_brand_obj.seo_title
                seo_keywords = seo_brand_obj.seo_keywords
                seo_description = seo_brand_obj.seo_description
                short_description = seo_brand_obj.short_description
                long_description = seo_brand_obj.long_description
            elif page_type=="product":
                product_obj = DealsHubProduct.objects.get(uuid=uuid)
                page_description = product_obj.page_description
                seo_title = product_obj.seo_title
                seo_keywords = product_obj.seo_keywords
                seo_description = product_obj.seo_description
            elif page_type=="brand_super_category":
                brand_super_category_obj = BrandSuperCategory.objects.get(uuid=uuid)
                page_description = brand_super_category_obj.page_description
                seo_title = brand_super_category_obj.seo_title
                seo_keywords = brand_super_category_obj.seo_keywords
                seo_description = brand_super_category_obj.seo_description
                short_description = brand_super_category_obj.short_description
                long_description = brand_super_category_obj.long_description
            elif page_type=="brand_category":
                brand_category_obj = BrandCategory.objects.get(uuid=uuid)
                page_description = brand_category_obj.page_description
                seo_title = brand_category_obj.seo_title
                seo_keywords = brand_category_obj.seo_keywords
                seo_description = brand_category_obj.seo_description
                short_description = brand_category_obj.short_description
                long_description = brand_category_obj.long_description
            elif page_type=="brand_sub_category":
                brand_sub_category_obj = BrandSubCategory.objects.get(uuid=uuid)
                page_description = brand_sub_category_obj.page_description
                seo_title = brand_sub_category_obj.seo_title
                seo_keywords = brand_sub_category_obj.seo_keywords
                seo_description = brand_sub_category_obj.seo_description
                short_description = brand_sub_category_obj.short_description
                long_description = brand_sub_category_obj.long_description

            response["page_description"] = page_description
            response["seo_title"] = seo_title
            response["seo_keywords"] = seo_keywords
            response["seo_description"] = seo_description
            response["short_description"] = short_description
            response["long_description"] = long_description
            
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSEOAdminDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class SaveSEOAdminDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SaveSEOAdminDetailsAPI: %s", str(data))
            
            page_type = data["page_type"]
            uuid = data["uuid"]

            page_description = data["page_description"]
            seo_title = data["seo_title"]
            seo_keywords = data["seo_keywords"]
            seo_description = data["seo_description"]
            short_description = data.get("short_description")
            long_description = data.get("long_description")

            if page_type=="super_category":
                seo_super_category_obj = SEOSuperCategory.objects.get(uuid=uuid)
                seo_super_category_obj.page_description = page_description
                seo_super_category_obj.seo_title = seo_title
                seo_super_category_obj.seo_keywords = seo_keywords
                seo_super_category_obj.seo_description = seo_description
                seo_super_category_obj.short_description = short_description
                seo_super_category_obj.long_description = long_description
                seo_super_category_obj.save()
            elif page_type=="category":
                seo_category_obj = SEOCategory.objects.get(uuid=uuid)
                seo_category_obj.page_description = page_description
                seo_category_obj.seo_title = seo_title
                seo_category_obj.seo_keywords = seo_keywords
                seo_category_obj.seo_description = seo_description
                seo_category_obj.short_description = short_description
                seo_category_obj.long_description = long_description
                seo_category_obj.save()
            elif page_type=="sub_category":
                seo_sub_category_obj = SEOSubCategory.objects.get(uuid=uuid)
                seo_sub_category_obj.page_description = page_description
                seo_sub_category_obj.seo_title = seo_title
                seo_sub_category_obj.seo_keywords = seo_keywords
                seo_sub_category_obj.seo_description = seo_description
                seo_sub_category_obj.short_description = short_description
                seo_sub_category_obj.long_description = long_description
                seo_sub_category_obj.save()
            elif page_type=="brand":
                seo_brand_obj = SEOBrand.objects.get(brand__name=uuid, brand__organization__name="WIG")
                seo_brand_obj.page_description = page_description
                seo_brand_obj.seo_title = seo_title
                seo_brand_obj.seo_keywords = seo_keywords
                seo_brand_obj.seo_description = seo_description
                seo_brand_obj.short_description = short_description
                seo_brand_obj.long_description = long_description
                seo_brand_obj.save()
            elif page_type=="product":
                product_obj = DealsHubProduct.objects.get(uuid=uuid)
                product_obj.page_description = page_description
                product_obj.seo_title = seo_title
                product_obj.seo_keywords = seo_keywords
                product_obj.seo_description = seo_description
                product_obj.save()
            elif page_type=="brand_super_category":
                brand_super_category_obj = BrandSuperCategory.objects.get(uuid=uuid)
                brand_super_category_obj.page_description = page_description
                brand_super_category_obj.seo_title = seo_title
                brand_super_category_obj.seo_keywords = seo_keywords
                brand_super_category_obj.seo_description = seo_description
                brand_super_category_obj.short_description = short_description
                brand_super_category_obj.long_description = long_description
                brand_super_category_obj.save()
            elif page_type=="brand_category":
                brand_category_obj = BrandCategory.objects.get(uuid=uuid)
                brand_category_obj.page_description = page_description
                brand_category_obj.seo_title = seo_title
                brand_category_obj.seo_keywords = seo_keywords
                brand_category_obj.seo_description = seo_description
                brand_category_obj.short_description = short_description
                brand_category_obj.long_description = long_description
                brand_category_obj.save()
            elif page_type=="brand_sub_category":
                brand_sub_category_obj = BrandSubCategory.objects.get(uuid=uuid)
                brand_sub_category_obj.page_description = page_description
                brand_sub_category_obj.seo_title = seo_title
                brand_sub_category_obj.seo_keywords = seo_keywords
                brand_sub_category_obj.seo_description = seo_description
                brand_sub_category_obj.short_description = short_description
                brand_sub_category_obj.long_description = long_description
                brand_sub_category_obj.save()
            
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveSEOAdminDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchLocationGroupSettingsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchLocationGroupSettingsAPI: %s", str(data))
            
            location_group_uuid = data["locationGroupUuid"]

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            response["delivery_fee"] = location_group_obj.delivery_fee
            response["cod_charge"] = location_group_obj.cod_charge
            response["free_delivery_threshold"] = location_group_obj.free_delivery_threshold
            response["vat"] = location_group_obj.vat
            
            response["region_list"] = json.loads(location_group_obj.region_list)
            
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchLocationGroupSettingsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class UpdateLocationGroupSettingsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateLocationGroupSettingsAPI: %s", str(data))
            
            location_group_uuid = data["locationGroupUuid"]

            delivery_fee = float(data["delivery_fee"])
            cod_charge = float(data["cod_charge"])
            free_delivery_threshold = float(data["free_delivery_threshold"])
            vat = float(data.get("vat", 5))

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            location_group_obj.delivery_fee = delivery_fee
            location_group_obj.cod_charge = cod_charge
            location_group_obj.free_delivery_threshold = free_delivery_threshold
            location_group_obj.vat = vat
            location_group_obj.save()
            
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateLocationGroupSettingsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class AddProductToOrderAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddProductToOrderAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            product_uuid = data["productUuid"]
            order_uuid = data["orderUuid"]

            dealshub_product_obj = DealsHubProduct.objects.get(uuid=product_uuid)

            order_obj = Order.objects.get(uuid=order_uuid)

            unit_order_obj = UnitOrder.objects.create(order=order_obj, 
                                                      product=dealshub_product_obj, 
                                                      quantity=1,
                                                      price=dealshub_product_obj.get_actual_price())
            UnitOrderStatus.objects.create(unit_order=unit_order_obj)

            update_order_bill(order_obj)

            voucher_obj = order_obj.voucher
            is_voucher_applied = voucher_obj is not None
            unit_order_objs = UnitOrder.objects.filter(order=order_obj)

            response["isVoucherApplied"] = is_voucher_applied
            if is_voucher_applied:
                response["voucherCode"] = voucher_obj.voucher_code
                response["voucherDiscount"] = voucher_obj.get_voucher_discount(order_obj.get_subtotal())

            
            temp_dict = {}
            temp_dict["orderId"] = unit_order_obj.orderid
            temp_dict["uuid"] = unit_order_obj.uuid
            temp_dict["currentStatus"] = unit_order_obj.current_status
            temp_dict["quantity"] = unit_order_obj.quantity
            temp_dict["price"] = unit_order_obj.price
            temp_dict["currency"] = unit_order_obj.product.get_currency()
            temp_dict["productName"] = unit_order_obj.product.get_name()
            temp_dict["productImageUrl"] = unit_order_obj.product.get_display_image_url()
            temp_dict["sellerSku"] = unit_order_obj.product.get_seller_sku()
            temp_dict["productId"] = unit_order_obj.product.get_product_id()
            temp_dict["productUuid"] = unit_order_obj.product.uuid

            unit_order_status_list = []
            unit_order_status_objs = UnitOrderStatus.objects.filter(unit_order=unit_order_obj).order_by('date_created')
            for unit_order_status_obj in unit_order_status_objs:
                temp_dict2 = {}
                temp_dict2["customerStatus"] = unit_order_status_obj.status
                temp_dict2["adminStatus"] = unit_order_status_obj.status_admin
                temp_dict2["date"] = unit_order_status_obj.get_date_created()
                temp_dict2["time"] = unit_order_status_obj.get_time_created()
                temp_dict2["uuid"] = unit_order_status_obj.uuid
                unit_order_status_list.append(temp_dict2)

            temp_dict["UnitOrderStatusList"] = unit_order_status_list

            subtotal = order_obj.get_subtotal()
            delivery_fee = order_obj.get_delivery_fee()
            cod_fee = order_obj.get_cod_charge()
            to_pay = order_obj.to_pay
            vat = order_obj.get_vat()

            response["subtotal"] = str(subtotal)
            response["deliveryFee"] = str(delivery_fee)
            response["codFee"] = str(cod_fee)
            response["vat"] = str(vat)
            response["toPay"] = str(to_pay)

            response["newUnitOrder"] = temp_dict

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddProductToOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchLogixShippingStatusAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchLogixShippingStatusAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            order_uuid  = data["orderUuid"]

            order_obj = Order.objects.get(uuid=order_uuid)
            tracking_reference = str(order_obj.logix_tracking_reference).strip()

            if tracking_reference=="":
                logger.warning("FetchLogixShippingStatusAPI: tracking_reference is empty!")
                return Response(data=response)
            
            headers = {
                    'content-type': 'application/json',
                    'Client-Service': 'logix',
                    'Auth-Key': 'trackapi',
                    'token': 'bf6c7d89b71732b9362aa0e7b51b4d92',
                    'User-ID': '1'
            }
            resp = requests.get(url="https://qzolve-erp.com/logix2020/track/order/status/"+tracking_reference, headers=headers)
            status_data = resp.json()

            response["shipping_status"] = status_data['shipping_status']
            response['status'] = 200
            
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchLogixShippingStatusAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)
      

class NotifyOrderStatusAPI(APIView):
    
    authentication_classes = (CsrfExemptSessionAuthentication,) 
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("NotifyOrderStatusAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            tracking_reference = data["tracking-reference"].strip()
            shipping_status = data["shipping-status"].strip().lower()

            if tracking_reference=="":
                logger.warning("NotifyOrderStatusAPI: tracking_reference is empty!")
                return Response(data=response)

            unit_order_objs = UnitOrder.objects.filter(order__logix_tracking_reference=tracking_reference)
            for unit_order_obj in unit_order_objs:
                if shipping_status in ["dispatched", "delivered"]:
                    set_order_status(unit_order_obj, shipping_status)

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("NotifyOrderStatusAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)


FetchProductDetails = FetchProductDetailsAPI.as_view()

FetchSimilarProducts = FetchSimilarProductsAPI.as_view()

FetchNewArrivalProducts = FetchNewArrivalProductsAPI.as_view()

FetchOnSaleProducts = FetchOnSaleProductsAPI.as_view()

FetchSectionProducts = FetchSectionProductsAPI.as_view()

FetchSuperCategories = FetchSuperCategoriesAPI.as_view()

FetchHeadingCategories = FetchHeadingCategoriesAPI.as_view()

Search = SearchAPI.as_view()

SearchWIG = SearchWIGAPI.as_view()

SearchWIG2 = SearchWIG2API.as_view()

SearchDaycart = SearchDaycartAPI.as_view()

FetchWIGCategories = FetchWIGCategoriesAPI.as_view()

FetchParajohnCategories = FetchParajohnCategoriesAPI.as_view()

CreateAdminCategory = CreateAdminCategoryAPI.as_view()

UpdateAdminCategory = UpdateAdminCategoryAPI.as_view()

DeleteAdminCategory = DeleteAdminCategoryAPI.as_view()

PublishAdminCategory = PublishAdminCategoryAPI.as_view()

UnPublishAdminCategory = UnPublishAdminCategoryAPI.as_view()

SectionBulkUpload = SectionBulkUploadAPI.as_view()

BannerBulkUpload = BannerBulkUploadAPI.as_view()

SectionBulkDownload = SectionBulkDownloadAPI.as_view()

BannerBulkDownload = BannerBulkDownloadAPI.as_view()

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

SearchProductsAutocomplete2 = SearchProductsAutocomplete2API.as_view()

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

AddSectionPromoSliderImage = AddSectionPromoSliderImageAPI.as_view()

FetchSectionPromoSliderImage = FetchSectionPromoSliderImageAPI.as_view()

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

FetchPostaPlusDetails = FetchPostaPlusDetailsAPI.as_view()

UpdateUnitOrderQtyAdmin = UpdateUnitOrderQtyAdminAPI.as_view()

UpdateOrderShippingAdmin = UpdateOrderShippingAdminAPI.as_view()

FetchSEODetails = FetchSEODetailsAPI.as_view()

FetchSEOAdminAutocomplete = FetchSEOAdminAutocompleteAPI.as_view()

FetchSEOAdminDetails = FetchSEOAdminDetailsAPI.as_view()

SaveSEOAdminDetails = SaveSEOAdminDetailsAPI.as_view()

FetchLocationGroupSettings = FetchLocationGroupSettingsAPI.as_view()

UpdateLocationGroupSettings = UpdateLocationGroupSettingsAPI.as_view()

AddProductToOrder = AddProductToOrderAPI.as_view()

NotifyOrderStatus = NotifyOrderStatusAPI.as_view()

FetchLogixShippingStatus = FetchLogixShippingStatusAPI.as_view()