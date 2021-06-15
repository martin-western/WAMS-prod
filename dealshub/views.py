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
from dealshub.payments.network_global_integration import *
from dealshub.payments.hyperpay_integration import *
from dealshub.payments.network_global_android_integration import *
from dealshub.algolia.views import *

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
from django.db.models import Count, Avg, F

from copy import deepcopy

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

            dealshub_user_obj = None
            if request.user != None and str(request.user)!="AnonymousUser" and DealsHubUser.objects.filter(username=request.user.username).exists():
                logger.info("FetchProductDetailsAPI REQUEST USER: %s", str(request.user))
                dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            response["brand"] = dealshub_product_obj.get_brand(language_code)
            response["superCategory"] = dealshub_product_obj.get_super_category(language_code)
            response["category"] = dealshub_product_obj.get_category(language_code)
            response["subCategory"] = dealshub_product_obj.get_sub_category(language_code)
            response["uuid"] = data["uuid"]
            response["name"] = dealshub_product_obj.get_name(language_code)
            response["stock"] = dealshub_product_obj.stock
            response["moq"] = dealshub_product_obj.get_moq(dealshub_user_obj)
            response["allowedQty"] = dealshub_product_obj.get_allowed_qty()
            response["price"] = dealshub_product_obj.get_actual_price(dealshub_user_obj)
            response["wasPrice"] = dealshub_product_obj.get_was_price(dealshub_user_obj)
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

            product_promotion_details = get_product_promotion_details(dealshub_product_obj)
            for key in product_promotion_details.keys():
                response[key]=product_promotion_details[key]

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

                if dealshub_product_obj.location_group.name=="PARA JOHN - UAE":
                    aplus_content_image_objs = product_obj.aplus_content_images.all()
                    for aplus_content_image_obj in aplus_content_image_objs:
                        try:
                            temp_image = {}
                            temp_image["high-res"] = aplus_content_image_obj.image.url
                            temp_image["original"] = aplus_content_image_obj.mid_image.url
                            temp_image["thumbnail"] = aplus_content_image_obj.thumbnail.url
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
            
            dealshub_product_objs = DealsHubProduct.objects.filter(location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all(), is_published=True, is_on_sale=True).exclude(now_price=0).exclude(stock=0).order_by('-is_promotional').prefetch_related('promotion')

            is_user_authenticated = True
            dealshub_user_obj = None
            if location_group_obj.is_b2b==True:
                is_user_authenticated = False
                b2b_user_obj = None
                if request.user != None and str(request.user)!="AnonymousUser":
                    logger.info("FetchOnSaleProductsAPI REQUEST USER: %s", str(request.user))
                    dealshub_user_obj = DealsHubUser.objects.get(username = request.user.username)
                    b2b_user_obj = B2BUser.objects.get(username = request.user.username)
                is_user_authenticated = check_account_status(b2b_user_obj)

            page = int(data.get("page",1))
            paginator = Paginator(dealshub_product_objs, 50)
            dealshub_product_objs = paginator.page(page)

            products = []
            for dealshub_product_obj in dealshub_product_objs:
                if dealshub_product_obj.now_price == 0:
                    continue
                
                temp_dict2 = {}
                temp_dict2["name"] = dealshub_product_obj.get_name(language_code)
                temp_dict2["brand"] = dealshub_product_obj.get_brand(language_code)
                temp_dict2["now_price"] = dealshub_product_obj.get_now_price(dealshub_user_obj)
                temp_dict2["was_price"] = dealshub_product_obj.get_was_price(dealshub_user_obj)
                temp_dict2["promotional_price"] = dealshub_product_obj.get_promotional_price(dealshub_user_obj)
                temp_dict2["moq"] = dealshub_product_obj.get_moq(dealshub_user_obj)
                temp_dict2["stock"] = dealshub_product_obj.stock
                temp_dict2["allowedQty"] = dealshub_product_obj.get_allowed_qty()
                temp_dict2["isStockAvailable"] = dealshub_product_obj.stock>0
                product_promotion_details = get_product_promotion_details(dealshub_product_obj)
                for key in product_promotion_details.keys():
                    temp_dict2[key]=product_promotion_details[key]
                temp_dict2["currency"] = dealshub_product_obj.get_currency()
                temp_dict2["uuid"] = dealshub_product_obj.uuid
                temp_dict2["link"] = dealshub_product_obj.url
                temp_dict2["id"] = dealshub_product_obj.uuid
                temp_dict2["heroImageUrl"] = dealshub_product_obj.get_display_image_url()
                temp_dict2["is_new_arrival"] = dealshub_product_obj.is_new_arrival
                temp_dict2["is_on_sale"] = dealshub_product_obj.is_on_sale
                products.append(temp_dict2)
            
            is_available = True
            
            if int(paginator.num_pages) == int(page):
                is_available = False

            response["is_available"] = is_available
            response["totalPages"] = paginator.num_pages
            response["products"] = products
            response["is_user_authenticated"] = is_user_authenticated
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

            is_user_authenticated = True
            dealshub_user_obj = None
            if location_group_obj.is_b2b==True:
                is_user_authenticated = False
                b2b_user_obj = None
                if request.user != None and str(request.user)!="AnonymousUser":
                    logger.info("FetchNewArrivalProductsAPI REQUEST USER: %s", str(request.user))
                    dealshub_user_obj = DealsHubUser.objects.get(username = request.user.username)
                    b2b_user_obj = B2BUser.objects.get(username = request.user.username)
                is_user_authenticated = check_account_status(b2b_user_obj)

            page = int(data.get("page",1))
            paginator = Paginator(dealshub_product_objs, 50)
            dealshub_product_objs = paginator.page(page)

            products = []
            for dealshub_product_obj in dealshub_product_objs:
                if dealshub_product_obj.now_price == 0:
                    continue
                
                temp_dict2 = {}
                temp_dict2["name"] = dealshub_product_obj.get_name(language_code)
                temp_dict2["brand"] = dealshub_product_obj.get_brand(language_code)
                temp_dict2["now_price"] = dealshub_product_obj.get_now_price(dealshub_user_obj)
                temp_dict2["was_price"] = dealshub_product_obj.get_was_price(dealshub_user_obj)
                temp_dict2["promotional_price"] = dealshub_product_obj.get_promotional_price(dealshub_user_obj)
                temp_dict2["moq"] = dealshub_product_obj.get_moq(dealshub_user_obj)
                temp_dict2["stock"] = dealshub_product_obj.stock
                temp_dict2["allowedQty"] = dealshub_product_obj.get_allowed_qty()
                temp_dict2["isStockAvailable"] = dealshub_product_obj.stock>0
                temp_dict2["is_new_arrival"] = dealshub_product_obj.is_new_arrival
                temp_dict2["is_on_sale"] = dealshub_product_obj.is_on_sale
                product_promotion_details = get_product_promotion_details(dealshub_product_obj)
                for key in product_promotion_details.keys():
                    temp_dict2[key]=product_promotion_details[key]
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
            response["is_user_authenticated"] = is_user_authenticated
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
            
            brand_name = data.get("brand", "").strip()

            min_price = data.get("min_price","")
            max_price = data.get("max_price","")
            min_rating = data.get("rating",0)
            min_discount_percent = data.get("discount_percent",0)

            brand_filter = data.get("brand_filter", [])
            sort_filter = data.get("sort_filter", {})

            uuid = data["sectionUuid"]
            section_obj = Section.objects.get(uuid=uuid)

            is_user_authenticated = True
            if section_obj.location_group.is_b2b==True:
                b2b_user_obj = None
                if request.user != None and str(request.user)!="AnonymousUser":
                    logger.info("REQUEST USER: %s", str(request.user))
                    b2b_user_obj = B2BUser.objects.get(username = request.user.username)
                is_user_authenticated = check_account_status(b2b_user_obj)
            
            custom_product_section_objs = CustomProductSection.objects.filter(section=section_obj, product__is_published=True)
            custom_product_section_objs = custom_product_section_objs.exclude(product__now_price=0).exclude(product__stock=0)
            dealshub_product_uuid_list = list(custom_product_section_objs.order_by('order_index').values_list("product__uuid", flat=True).distinct())
            dealshub_product_objs = DealsHubProduct.objects.filter(uuid__in=dealshub_product_uuid_list)
            
            if min_price!="":
                dealshub_product_objs = dealshub_product_objs.filter(now_price__gte=int(min_price))
            if max_price!="":
                dealshub_product_objs = dealshub_product_objs.filter(now_price__lte=int(max_price))
            if min_rating!=0:
                dealshub_product_objs = dealshub_product_objs.exclude(review=None).annotate(product_avg_rating=Avg('review__rating')).filter(product_avg_rating__gte=float(min_rating))
            if min_discount_percent!=0:
                dealshub_product_objs = dealshub_product_objs.annotate(product_discount=((F('was_price')-F('now_price'))/F('was_price')*100)).filter(product_discount__gte=float(min_discount_percent))
            
            if brand_name!="":
                dealshub_product_objs = dealshub_product_objs.filter(Q(product__base_product__brand__name=brand_name) | Q(product__base_product__brand__name_ar=brand_name))

            brand_list = []
            try:
                brand_list = list(dealshub_product_objs.values_list('product__base_product__brand__name', flat=True).distinct())[:50]
                if language_code == "ar":
                    brand_list = list(dealshub_product_objs.values_list('product__base_product__brand__name_ar', flat=True).distinct())[:50]

                brand_list = list(set(brand_list))
                if len(brand_list)==1:
                    brand_list = []
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SearchAPI brand list: %s at %s", e, str(exc_tb.tb_lineno))

            if len(brand_filter)>0:
                dealshub_product_objs = dealshub_product_objs.filter(product__base_product__brand__name__in=brand_filter)      

            if sort_filter.get("price", "")=="high-to-low":
                dealshub_product_objs = dealshub_product_objs.order_by('-now_price')
            elif sort_filter.get("price", "")=="low-to-high":
                dealshub_product_objs = dealshub_product_objs.order_by('now_price')
            else:
                dealshub_product_objs = list(dealshub_product_objs)
                dealshub_product_objs.sort(key=lambda t: dealshub_product_uuid_list.index(t.uuid))
            
            temp_dict = {}
            temp_dict["sectionName"] = section_obj.name
            temp_dict["productsArray"] = []

            page = int(data.get("page",1))
            paginator = Paginator(dealshub_product_objs, 50)
            dealshub_product_objs = paginator.page(page)

            for dealshub_product_obj in dealshub_product_objs:
                if dealshub_product_obj.now_price==0:
                    continue
                temp_dict2 = {}
                temp_dict2["name"] = dealshub_product_obj.get_name(language_code)
                temp_dict2["brand"] = dealshub_product_obj.get_brand(language_code)
                temp_dict2["seller_sku"] = dealshub_product_obj.get_seller_sku()
                temp_dict2["now_price"] = dealshub_product_obj.now_price
                temp_dict2["was_price"] = dealshub_product_obj.was_price
                temp_dict2["promotional_price"] = dealshub_product_obj.promotional_price
                temp_dict2["moq"] = dealshub_product_obj.moq
                temp_dict2["stock"] = dealshub_product_obj.stock
                temp_dict2["is_new_arrival"] = dealshub_product_obj.is_new_arrival
                temp_dict2["is_on_sale"] = dealshub_product_obj.is_on_sale
                temp_dict2["allowedQty"] = dealshub_product_obj.get_allowed_qty()
                temp_dict2["isStockAvailable"] = dealshub_product_obj.stock>0
                product_promotion_details = get_product_promotion_details(dealshub_product_obj)
                for key in product_promotion_details.keys():
                    temp_dict2[key]=product_promotion_details[key]
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
            response["is_user_authenticated"] = is_user_authenticated

            response["brand_list"] = brand_list
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
                    if DealsHubProduct.objects.filter(is_published=True, category=category_obj, location_group__website_group=website_group_obj, product__base_product__brand__in=website_group_obj.brands.all()).exclude(now_price=0).exclude(stock=0).exists():
                        category_list.append(temp_dict2)
                temp_dict["category_list"] = category_list
                if len(category_list)>0:
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


class FetchCategoriesForNewUserAPI(APIView):

    def post(self,request,*args,**kwargs):

        response = {}
        response['status']=500
        try:
            data = request.data
            logger.info("FetchCategoriesForNewUserAPI: %s",str(data))

            website_group_name = data["websiteGroupName"]
            website_group_obj = WebsiteGroup.objects.get(name=website_group_name)
            category_objs = website_group_obj.categories.all()

            category_list = []
            for category_obj in category_objs:
                temp_dict = {}
                temp_dict["name"] = category_obj.get_name()
                temp_dict["uuid"] = category_obj.uuid
                category_list.append(temp_dict)

            b2b_user_obj = B2BUser.objects.get(username = request.user.username)
            conf = json.loads(b2b_user_obj.conf)

            response["isInterestedCategoriesSet"] = conf.get("isInterestedCategoriesSet", False)
            response['categoryList'] = category_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCategoriesForNewUserAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SetInterestedCategoriesForNewUserAPI(APIView):

    def post(self,request,*args,**kwargs):

        response = {}
        response['status'] = 500

        try:
            data = request.data
            logger.info("SetInterestedCategoriesForNewUserAPI: %s",str(data))

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group
            website_group_name = website_group_obj.name.lower()
            interested_categories = data["interestedCategories"]

            b2b_user_obj = B2BUser.objects.get(username = request.user.username)

            conf= json.loads(b2b_user_obj.conf)
            if conf.get("isInterestedCategoriesSet",False) == False:
                for interested_category in interested_categories:
                    interested_category_obj = Category.objects.get(uuid = interested_category['uuid'])
                    b2b_user_obj.interested_categories.add(interested_category_obj)

            conf["isInterestedCategoriesSet"] = True
            b2b_user_obj.conf = json.dumps(conf)
            b2b_user_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCategoriesForNewUserAPI: %s at %s", e, str(exc_tb.tb_lineno))

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

                    #cached_response = cache.get(location_group_uuid+"-"+str(category_obj.uuid), "has_expired")
                    # if cached_response!="has_expired":
                    #     if "subCategoryList" in json.loads(cached_response):
                    #         category_list.append(json.loads(cached_response))
                    #     continue

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
                    #cache.set(location_group_uuid+"-"+str(category_obj.uuid), json.dumps(temp_dict))
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

            dealshub_user_obj = None
            if request.user != None and str(request.user)!="AnonymousUser":
                logger.info("SearchWIGAPI REQUEST USER: %s", str(request.user))
                dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

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
                    temp_dict["now_price"] = dealshub_product_obj.get_now_price(dealshub_user_obj)
                    temp_dict["was_price"] = dealshub_product_obj.get_was_price(dealshub_user_obj)
                    temp_dict["promotional_price"] = dealshub_product_obj.get_promotional_price(dealshub_user_obj)
                    temp_dict["stock"] = dealshub_product_obj.stock
                    temp_dict["is_new_arrival"] = dealshub_product_obj.is_new_arrival
                    temp_dict["is_on_sale"] = dealshub_product_obj.is_on_sale
                    temp_dict["allowedQty"] = dealshub_product_obj.get_allowed_qty()
                    temp_dict["isStockAvailable"] = dealshub_product_obj.stock>0
                    product_promotion_details = get_product_promotion_details(dealshub_product_obj)
                    for key in product_promotion_details.keys():
                        temp_dict[key]=product_promotion_details[key]
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

            dealshub_user_obj = None
            is_user_authenticated = True
            if location_group_obj.is_b2b==True:
                b2b_user_obj = None
                logger.info("REQUEST USER::: %s", str(request.user))
                if request.user != None and str(request.user)!="AnonymousUser":
                    logger.info("REQUEST USER: %s", str(request.user))
                    b2b_user_obj = B2BUser.objects.get(username = request.user.username)
                    dealshub_user_obj = DealsHubUser.objects.get(username = request.user.username)
                is_user_authenticated = check_account_status(b2b_user_obj)

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
                available_dealshub_products = available_dealshub_products.filter(Q(product__base_product__base_product_name__icontains=search_string) | Q(product__product_name__icontains=search_string) | Q(product__product_name_sap__icontains=search_string) | Q(product__product_id__icontains=search_string) | Q(product__base_product__seller_sku__icontains=search_string))
                # search_string = remove_stopwords(search_string)
                # words = search_string.split(" ")
                # target_brand = None
                # for word in words:
                #     if website_group_obj.brands.filter(name=word).exists():
                #         target_brand = website_group_obj.brands.filter(name=word)[0]
                #         words.remove(word)
                #         break
                # if target_brand!=None:
                #     available_dealshub_products = available_dealshub_products.filter(product__base_product__brand=target_brand)
                # if len(words)==1:
                #     available_dealshub_products = available_dealshub_products.filter(Q(search_keywords__icontains=","+words[0]+","))
                # elif len(words)==2:
                #     if available_dealshub_products.filter(search_keywords__icontains=","+search_string+",").exists():
                #         available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+search_string+",")
                #     else:
                #         if available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",").exists():
                #             available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",")
                #         else:
                #             available_dealshub_products = available_dealshub_products.filter(Q(search_keywords__icontains=","+words[0]+",") | Q(search_keywords__icontains=","+words[1]+","))
                # elif len(words)==3:
                #     if available_dealshub_products.filter(search_keywords__icontains=","+search_string+",").exists():
                #         available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+search_string+",")
                #     else:
                #         if available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",").filter(search_keywords__icontains=","+words[2]+",").exists():
                #             available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",").filter(search_keywords__icontains=","+words[2]+",")
                #         else:
                #             temp_available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=words[0]).filter(search_keywords__icontains=words[1])
                #             temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[1]).filter(search_keywords__icontains=words[2])
                #             temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[0]).filter(search_keywords__icontains=words[2])
                #             if temp_available_dealshub_products.exists()==False:
                #                 temp_available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=words[0])
                #                 temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[1])
                #                 temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[2])
                #             available_dealshub_products = temp_available_dealshub_products.distinct()
                # else:
                #     if available_dealshub_products.filter(search_keywords__icontains=","+search_string+",").exists():
                #         available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+search_string+",")
                #     else:
                #         if len(words)>0:
                #             search_results = DealsHubProduct.objects.none()
                #             for word in words:
                #                 search_results |= available_dealshub_products.filter(search_keywords__icontains=","+word+",")
                #             available_dealshub_products = search_results.distinct()

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
                    if dealshub_product_obj.now_price==0:
                        continue
                    temp_dict = {}
                    temp_dict["name"] = dealshub_product_obj.get_name()
                    temp_dict["brand"] = dealshub_product_obj.get_brand()
                    temp_dict["seller_sku"] = dealshub_product_obj.get_seller_sku()
                    temp_dict["now_price"] = dealshub_product_obj.get_now_price(dealshub_user_obj)
                    temp_dict["was_price"] = dealshub_product_obj.get_was_price(dealshub_user_obj)
                    temp_dict["promotional_price"] = dealshub_product_obj.get_promotional_price(dealshub_user_obj)
                    temp_dict["moq"] = dealshub_product_obj.get_moq(dealshub_user_obj)
                    temp_dict["stock"] = dealshub_product_obj.stock
                    temp_dict["is_new_arrival"] = dealshub_product_obj.is_new_arrival
                    temp_dict["is_on_sale"] = dealshub_product_obj.is_on_sale
                    temp_dict["allowedQty"] = dealshub_product_obj.get_allowed_qty()
                    temp_dict["isStockAvailable"] = dealshub_product_obj.stock>0
                    product_promotion_details = get_product_promotion_details(dealshub_product_obj)
                    for key in product_promotion_details.keys():
                        temp_dict[key]=product_promotion_details[key]
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
            response["is_user_authenticated"] = is_user_authenticated
            logger.info("DEBUGGG : %s", str(is_user_authenticated))
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

            min_price = data.get("min_price","")
            max_price = data.get("max_price","")
            min_rating = data.get("rating",0)
            min_discount_percent = data.get("discount_percent",0)

            brand_filter = data.get("brand_filter", [])
            sort_filter = data.get("sort_filter", {})

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group

            page = data.get("page", 1)

            key_hash = "search-daycart-"+language_code+"-"+super_category_name+"-"+category_name+"-"+subcategory_name+"-"+brand_name+"-"+str(page)
            if brand_filter==[] and sort_filter=={"price":""} and search_string=="" and min_price=="" and max_price=="" and min_rating==0 and min_discount_percent==0:
                cached_value = cache.get(key_hash, "has_expired")
                if cached_value!="has_expired":
                    t2 = datetime.datetime.now()
                    logger.info("SearchDaycartAPI: HIT! time: %s", str((t2-t1).total_seconds()))
                    response = json.loads(cached_value)
                    return Response(data=response)

            search = {}

            available_dealshub_products = DealsHubProduct.objects.filter(location_group=location_group_obj, product__base_product__brand__in=website_group_obj.brands.all(), is_published=True).exclude(now_price=0).exclude(stock=0)

            if min_price!="":
                available_dealshub_products = available_dealshub_products.filter(now_price__gte=int(min_price))
            if max_price!="":
                available_dealshub_products = available_dealshub_products.filter(now_price__lte=int(max_price))
            if min_rating!=0:
                available_dealshub_products = available_dealshub_products.exclude(review=None).annotate(product_avg_rating=Avg('review__rating')).filter(product_avg_rating__gte=float(min_rating))
            if min_discount_percent!=0:
                available_dealshub_products = available_dealshub_products.annotate(product_discount=((F('was_price')-F('now_price'))/F('was_price')*100)).filter(product_discount__gte=float(min_discount_percent))
                       
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
                available_dealshub_products = available_dealshub_products.filter(Q(product_name_ar__icontains=search_string) | Q(product__base_product__base_product_name__icontains=search_string) | Q(product__product_name__icontains=search_string) | Q(product__product_name_sap__icontains=search_string) | Q(product__product_id__icontains=search_string) | Q(product__base_product__seller_sku__icontains=search_string))
                # search_string = remove_stopwords(search_string)
                # words = search_string.split(" ")
                # target_brand = None
                # for word in words:
                #     if website_group_obj.brands.filter(name=word).exists():
                #         target_brand = website_group_obj.brands.filter(name=word)[0]
                #         words.remove(word)
                #         break
                # if target_brand!=None:
                #     available_dealshub_products = available_dealshub_products.filter(product__base_product__brand=target_brand)
                # if len(words)==1:
                #     available_dealshub_products = available_dealshub_products.filter(Q(search_keywords__icontains=","+words[0]+","))
                # elif len(words)==2:
                #     if available_dealshub_products.filter(search_keywords__icontains=","+search_string+",").exists():
                #         available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+search_string+",")
                #     else:
                #         if available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",").exists():
                #             available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",")
                #         else:
                #             available_dealshub_products = available_dealshub_products.filter(Q(search_keywords__icontains=","+words[0]+",") | Q(search_keywords__icontains=","+words[1]+","))
                # elif len(words)==3:
                #     if available_dealshub_products.filter(search_keywords__icontains=","+search_string+",").exists():
                #         available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+search_string+",")
                #     else:
                #         if available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",").filter(search_keywords__icontains=","+words[2]+",").exists():
                #             available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",").filter(search_keywords__icontains=","+words[2]+",")
                #         else:
                #             temp_available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=words[0]).filter(search_keywords__icontains=words[1])
                #             temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[1]).filter(search_keywords__icontains=words[2])
                #             temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[0]).filter(search_keywords__icontains=words[2])
                #             if temp_available_dealshub_products.exists()==False:
                #                 temp_available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=words[0])
                #                 temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[1])
                #                 temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[2])
                #             available_dealshub_products = temp_available_dealshub_products.distinct()
                # else:
                #     if available_dealshub_products.filter(search_keywords__icontains=","+search_string+",").exists():
                #         available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+search_string+",")
                #     else:
                #         if len(words)>0:
                #             search_results = DealsHubProduct.objects.none()
                #             for word in words:
                #                 search_results |= available_dealshub_products.filter(search_keywords__icontains=","+word+",")
                #             available_dealshub_products = search_results.distinct()

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

                    # cached_response = cache.get(location_group_uuid+"-"+str(category_obj.uuid), "has_expired")
                    # if cached_response!="has_expired":
                    #     if "subCategoryList" in json.loads(cached_response):
                    #         category_list.append(json.loads(cached_response))
                    #     continue

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
                    #cache.set(location_group_uuid+"-"+str(category_obj.uuid), json.dumps(temp_dict))
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

            if brand_filter==[] and sort_filter=={"price":""} and search_string=="" and min_price=="" and max_price=="" and min_rating==0 and min_discount_percent==0:
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

                    if available_dealshub_products.exists():
                        super_category_obj = available_dealshub_products[0].category.super_category

                category_objs = Category.objects.filter(super_category=super_category_obj)
                for category_obj in category_objs:

                    # cached_response = cache.get(location_group_uuid+"-"+str(category_obj.uuid), "has_expired")
                    # if cached_response!="has_expired":
                    #     if "subCategoryList" in json.loads(cached_response):
                    #         category_list.append(json.loads(cached_response))
                    #     continue

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
                    #cache.set(location_group_uuid+"-"+str(category_obj.uuid), json.dumps(temp_dict))
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

#API with active log
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

            parent_banner_uuid = data.get("parent_banner_uuid","")

            data = data["sectionData"]

            name = data["name"]
            listing_type = data["listingType"]
            products = data["products"]
            
            order_index = Banner.objects.filter(location_group=location_group_obj).count()+Section.objects.filter(location_group=location_group_obj).count()+1

            if parent_banner_uuid!="":
                parent_banner_obj = Banner.objects.get(uuid=parent_banner_uuid)
                section_obj = Section.objects.create(location_group=location_group_obj, name=name, listing_type=listing_type, order_index=order_index, parent_banner=parent_banner_obj)
            else: 
                section_obj = Section.objects.create(location_group=location_group_obj, name=name, listing_type=listing_type, order_index=order_index)
            order_index = 0
            for product in products:
                dealshub_product_obj = DealsHubProduct.objects.get(uuid=product)
                CustomProductUnitBanner.objects.create(section=section_obj, product=dealshub_product_obj, order_index=order_index)
                order_index += 1

            response['uuid'] = str(section_obj.uuid)
            response['status'] = 200
            render_value = "Section " + section_obj.name + " created"
            activitylog(request.user, Section, "created", section_obj.uuid, None, section_obj, location_group_obj, render_value)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateAdminCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


#API with active log
class UpdateAdminCategoryAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateAdminCategoryAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UpdateAdminCategoryAPI Restricted Access!")
                return Response(data=response)

            data = data["sectionData"]

            uuid = data["uuid"]
            name = data["name"]
            listing_type = data["listingType"]
            is_published = data["isPublished"]
            is_promotional = data["is_promotional"]
            
            section_obj = Section.objects.get(uuid=uuid)
            prev_section_obj = deepcopy(section_obj)

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
                if dealshub_product_obj.is_promotional==False:
                    dealshub_product_obj.promotion = promotion_obj
                    dealshub_product_obj.save()
                else:
                    if promotion_obj!=None:
                        custom_product_section_obj.delete()                     

            section_obj.save()

            render_value = "Section " + section_obj.name + " updated"
            activitylog(request.user, Section, "updated", section_obj.uuid, prev_section_obj, section_obj, section_obj.location_group, render_value)
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateAdminCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log

class DeleteAdminCategoryAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("DeleteAdminCategoryAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("DeleteAdminCategoryAPI Restricted Access!")
                return Response(data=response)

            uuid = data["uuid"]
            
            section_obj = Section.objects.get(uuid=uuid)
            prev_section_obj = deepcopy(section_obj)
            dealshub_product_uuid_list = list(CustomProductSection.objects.filter(section=section_obj).order_by('order_index').values_list("product__uuid", flat=True).distinct())
            dealshub_product_objs = DealsHubProduct.objects.filter(uuid__in=dealshub_product_uuid_list)

            for dealshub_product_obj in dealshub_product_objs:
                dealshub_product_obj.promotion = None
                dealshub_product_obj.save()

            location_group_uuid = section_obj.location_group.uuid
            #cache.set(location_group_uuid, "has_expired")
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
                
            section_obj.delete()

            render_value = "Section " + prev_section_obj.name + " deleted"
            activitylog(request.user, Section, "deleted", section_obj.uuid, prev_section_obj, None, location_group_obj, render_value)      
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteAdminCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log

class PublishAdminCategoryAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("PublishAdminCategoryAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("PublishAdminCategoryAPI Restricted Access!")
                return Response(data=response)

            uuid = data["uuid"]
            
            section_obj = Section.objects.get(uuid=uuid)
            prev_section_obj = deepcopy(section_obj)
            section_obj.is_published = True
            section_obj.save()

            location_group_uuid = section_obj.location_group.uuid
            #cache.set(location_group_uuid, "has_expired")
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            render_value = "Section " + section_obj.name +" is published"
            activitylog(request.user, Section, "updated", section_obj.uuid, prev_section_obj, section_obj, location_group_obj, render_value)
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PublishAdminCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


#API with active log
class UnPublishAdminCategoryAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UnPublishAdminCategoryAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UnPublishAdminCategoryAPI Restricted Access!")
                return Response(data=response)

            uuid = data["uuid"]
            
            section_obj = Section.objects.get(uuid=uuid)
            prev_section_obj = deepcopy(section_obj)
            section_obj.is_published = False
            section_obj.save()

            location_group_uuid = section_obj.location_group.uuid
            #cache.set(location_group_uuid, "has_expired")
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            render_value = "Section " + section_obj.name + " is unpublished"
            activitylog(request.user, Section, "updated", section_obj.uuid, prev_section_obj, section_obj, location_group_obj, render_value)
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UnPublishAdminCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class SectionBulkUploadAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SectionBulkUploadAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("SectionBulkUploadAPI Restricted Access!")
                return Response(data=response)

            path = default_storage.save('tmp/temp-section.xlsx', data["import_file"])
            logger.info("PATH %s", str(path))
            path = "http://cdn.omnycomm.com.s3.amazonaws.com/"+path
            dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
            rows = len(dfs.iloc[:])

            uuid = data["uuid"]
            section_obj = Section.objects.get(uuid=uuid)
            prev_section_obj = deepcopy(section_obj)
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
                    
                    if dealshub_product_obj.is_promotional and check_valid_promotion(dealshub_product_obj.promotion)==False:
                        dealshub_product_obj.is_promotional = False
                        dealshub_product_obj.promotion = None
                        dealshub_product_obj.save()
                    
                    if section_obj.promotion!=None and dealshub_product_obj.is_promotional:
                        unsuccessful_count += 1
                        continue

                    if section_obj.promotion!=None:
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

                    if location_group_obj.is_b2b == True:
                        temp_dict["now_price_cohort1"] = dealshub_product_obj.now_price_cohort1
                        temp_dict["now_price_cohort2"] = dealshub_product_obj.now_price_cohort2
                        temp_dict["now_price_cohort3"] = dealshub_product_obj.now_price_cohort3
                        temp_dict["now_price_cohort4"] = dealshub_product_obj.now_price_cohort4
                        temp_dict["now_price_cohort5"] = dealshub_product_obj.now_price_cohort5

                        temp_dict["promotional_price_cohort1"] = dealshub_product_obj.promotional_price_cohort1
                        temp_dict["promotional_price_cohort2"] = dealshub_product_obj.promotional_price_cohort2
                        temp_dict["promotional_price_cohort3"] = dealshub_product_obj.promotional_price_cohort3
                        temp_dict["promotional_price_cohort4"] = dealshub_product_obj.promotional_price_cohort4
                        temp_dict["promotional_price_cohort5"] = dealshub_product_obj.promotional_price_cohort5

                    products.append(temp_dict)

                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.warning("SectionBulkUploadAPI: %s at %s", e, str(exc_tb.tb_lineno))
                    unsuccessful_count += 1
                    
            section_obj.save()

            response["products"] = products[:40]
            response["unsuccessful_count"] = unsuccessful_count
            response["filepath"] = path

            render_value = "Products bulk uploaded to section "+ section_obj.name
            activitylog(request.user, Section, "updated", section_obj.uuid, prev_section_obj, section_obj, location_group_obj, render_value)
            response['status'] = 200
            
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SectionBulkUploadAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class BannerBulkUploadAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("BannerBulkUploadAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("BannerBulkUploadAPI Restricted Access!")
                return Response(data=response)

            path = default_storage.save('tmp/temp-banner.xlsx', data["import_file"])
            path = "http://cdn.omnycomm.com.s3.amazonaws.com/"+path
            dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
            rows = len(dfs.iloc[:])

            uuid = data["uuid"]
            unit_banner_obj = UnitBannerImage.objects.get(uuid=uuid)
            prev_unit_banner_obj = deepcopy(unit_banner_obj)
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
            render_value = "Products bulk uploaded to banner " + unit_banner_obj.banner.name
            activitylog(request.user, UnitBannerImage, "updated", unit_banner_obj.uuid, prev_unit_banner_obj, unit_banner_obj, location_group_obj, render_value)

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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("SectionBulkDownloadAPI Restricted Access!")
                return Response(data=response)

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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("BannerBulkDownloadAPI Restricted Access!")
                return Response(data=response)

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


class FetchNestedBannersAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchNestedBannersAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchNestedBannersAPI Restricted Access!")
                return Response(data=response)

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            nested_banners = []

            for banner_obj in Banner.objects.filter(is_nested=True, location_group=location_group_obj):
                temp_dict = {}
                temp_dict["uuid"] = banner_obj.uuid
                temp_dict["name"] = banner_obj.name
                nested_banners.append(temp_dict)
            
            response['nested_banners'] = nested_banners
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchBannerTypesAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
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

#API with active log
class CreateBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("CreateBannerAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("CreateBannerAPI Restricted Access!")
                return Response(data=response)

            banner_type = data["bannerType"]
            location_group_uuid = data["locationGroupUuid"]
            name = data.get("name", "")
            is_nested = data.get("is_nested",False)
            parent_banner_uuid = data.get("parent_banner_uuid","")

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            banner_type_obj = BannerType.objects.get(name=banner_type, website_group=location_group_obj.website_group)

            if name=="":
                name = banner_type_obj.display_name

            order_index = Banner.objects.filter(location_group=location_group_obj).count()+Section.objects.filter(location_group=location_group_obj).count()+1

            if parent_banner_uuid!="":
                parent_banner_obj = Banner.objects.get(uuid=parent_banner_uuid)
                banner_obj = Banner.objects.create(name=name,location_group=location_group_obj, order_index=order_index, banner_type=banner_type_obj, parent=parent_banner_obj)
            else:
                banner_obj = Banner.objects.create(name=name, location_group=location_group_obj, order_index=order_index, banner_type=banner_type_obj, is_nested=is_nested)
            
            response['uuid'] = banner_obj.uuid
            response["limit"] = banner_type_obj.limit
            response['status'] = 200
            render_value = "Banner " + banner_obj.name + " is created"
            activitylog(request.user, Banner, "created", banner_obj.uuid, None, banner_obj, location_group_obj,render_value)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class UpdateBannerNameAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateBannerNameAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UpdateBannerNameAPI Restricted Access!")
                return Response(data=response)

            name = data["name"]
            uuid = data["uuid"]

            banner_obj = Banner.objects.get(uuid=uuid)
            prev_banner_obj = deepcopy(banner_obj)
            banner_obj.name = name
            banner_obj.save()
            
            response['status'] = 200
            render_value = "Banner " + banner_obj.name + " is updated"
            activitylog(request.user, Banner, "updated", banner_obj.uuid, prev_banner_obj, banner_obj, banner_obj.location_group, render_value)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateBannerNameAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class AddBannerImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddBannerImageAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("AddBannerImageAPI Restricted Access!")
                return Response(data=response)

            uuid = data["uuid"]
            banner_image = data["image"]

            banner_obj = Banner.objects.get(uuid=uuid)
            prev_banner_obj = deepcopy(banner_obj)
            image_obj = Image.objects.create(image=banner_image)
            unit_banner_image_obj = UnitBannerImage.objects.create(image=image_obj, banner=banner_obj)

            response['uuid'] = unit_banner_image_obj.uuid
            response["imageUrl"] = image_obj.image.url
            response['status'] = 200
            render_value = "Image " + image_obj.image.url + " added to banner "+ banner_obj.name
            activitylog(request.user, Banner, "updated", banner_obj.uuid, prev_banner_obj, banner_obj, banner_obj.location_group, render_value)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddBannerImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class UpdateBannerImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateBannerImageAPI: %s", str(data))
            language_code = data.get("language","en")

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UpdateBannerImageAPI Restricted Access!")
                return Response(data=response)

            uuid = data["uuid"]
            banner_image = data["image"]
            image_type = data.get("imageType", "mobile")

            unit_banner_image_obj = UnitBannerImage.objects.get(uuid=uuid)
            prev_unit_banner_image_obj = deepcopy(unit_banner_image_obj)
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
            render_value = "Image " + image_obj.image.url + " is updated in banner " + unit_banner_image_obj.banner.name
            activitylog(request.user, UnitBannerImage, "updated", unit_banner_image_obj.uuid, prev_unit_banner_image_obj, unit_banner_image_obj, unit_banner_image_obj.banner.location_group, render_value)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateBannerImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class DeleteBannerImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("DeleteBannerImageAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("DeleteBannerImageAPI Restricted Access!")
                return Response(data=response)

            uuid = data["uuid"]
            image_type = data["imageType"]

            language_code = data.get("language", "en")

            unit_banner_image_obj = UnitBannerImage.objects.get(uuid=uuid)
            prev_unit_banner_image_obj = deepcopy(unit_banner_image_obj)

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
            render_value = "Image deleted for banner " + unit_banner_image_obj.banner.name
            activitylog(request.user, UnitBannerImage, "updated", unit_banner_image_obj.uuid, prev_unit_banner_image_obj, unit_banner_image_obj, unit_banner_image_obj.banner.location_group, render_value)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteBannerImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class DeleteUnitBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("DeleteUnitBannerAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("DeleteUnitBannerAPI Restricted Access!")
                return Response(data=response)

            uuid = data["uuid"]

            unit_banner_obj = UnitBannerImage.objects.get(uuid=uuid)
            prev_unit_banner_obj = deepcopy(unit_banner_obj)

            dealshub_product_uuid_list = list(CustomProductUnitBanner.objects.filter(unit_banner=unit_banner_obj).order_by('order_index').values_list("product__uuid", flat=True).distinct())
            dealshub_product_objs = DealsHubProduct.objects.filter(uuid__in=dealshub_product_uuid_list)

            for dealshub_product_obj in dealshub_product_objs:
                dealshub_product_obj.promotion = None
                dealshub_product_obj.save()

            location_group_uuid = unit_banner_obj.banner.location_group.uuid
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            #cache.set(location_group_uuid, "has_expired")

            unit_banner_obj.delete()
            response['status'] = 200
            render_value = "Unit Banner " + prev_unit_banner_obj.banner.name + " deleted"
            activitylog(request.user, UnitBannerImage, "deleted", unit_banner_obj.uuid, prev_unit_banner_obj, None, location_group_obj,render_value)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteUnitBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class DeleteBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("DeleteBannerAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("DeleteBannerAPI Restricted Access!")
                return Response(data=response)

            uuid = data["uuid"]
            banner_obj = Banner.objects.get(uuid=uuid)
            prev_banner_obj = deepcopy(banner_obj)

            unit_banner_objs = UnitBannerImage.objects.filter(banner=banner_obj)

            for unit_banner_obj in unit_banner_objs:
                dealshub_product_uuid_list = list(CustomProductUnitBanner.objects.filter(unit_banner=unit_banner_obj).order_by('order_index').values_list("product__uuid", flat=True).distinct())
                dealshub_product_objs = DealsHubProduct.objects.filter(uuid__in=dealshub_product_uuid_list)
                for dealshub_product_obj in dealshub_product_objs:
                    dealshub_product_obj.promotion = None
                    dealshub_product_obj.save()

            location_group_uuid = banner_obj.location_group.uuid
            #cache.set(location_group_uuid, "has_expired")
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            banner_obj.delete()
            
            response['status'] = 200
            render_value = "Banner " + prev_banner_obj.name + " is deleted"
            activitylog(request.user, Banner, "deleted", "", prev_banner_obj, None, location_group_obj, render_value)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class PublishBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("PublishBannerAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("PublishBannerAPI Restricted Access!")
                return Response(data=response)

            uuid = data["uuid"]
            banner_obj = Banner.objects.get(uuid=uuid)
            prev_banner_obj = deepcopy(banner_obj)
            banner_obj.is_published = True
            banner_obj.save()

            location_group_uuid = banner_obj.location_group.uuid
            #cache.set(location_group_uuid, "has_expired")
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            response['uuid'] = banner_obj.uuid
            response['status'] = 200
            activitylog(request.user, Banner, "updated", banner_obj.uuid, prev_banner_obj, banner_obj, location_group_obj, "Banner {} is published".format(banner_obj.name))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PublishBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class UnPublishBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UnPublishBannerAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UnPublishBannerAPI Restricted Access!")
                return Response(data=response)

            uuid = data["uuid"]
            banner_obj = Banner.objects.get(uuid=uuid)
            prev_banner_obj = deepcopy(banner_obj)
            banner_obj.is_published = False
            banner_obj.save()

            location_group_uuid = banner_obj.location_group.uuid
            #cache.set(location_group_uuid, "has_expired")
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            
            response['uuid'] = banner_obj.uuid
            response['status'] = 200
            activitylog(request.user, Banner, "updated", banner_obj.uuid, prev_banner_obj, banner_obj, location_group_obj, "Banner {} is unpublished".format(banner_obj.name))
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UnPublishBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class PublishDealsHubProductAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("PublishDealsHubProductAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("PublishDealsHubProductAPI Restricted Access!")
                return Response(data=response)

            uuid = data["product_uuid"]
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=uuid)
            prev_product_obj = deepcopy(dealshub_product_obj)
            
            # if dealshub_product_obj.product.no_of_images_for_filter==0:
            #     response['status'] = 407
            #     response['message'] = 'product without images cannot be published'
            #     return Response(data=response)

            dealshub_product_obj.is_published = True
            dealshub_product_obj.save()

            response['status'] = 200
            render_value = dealshub_product_obj.get_seller_sku() + " is published on " + dealshub_product_obj.location_group.name
            activitylog(request.user, DealsHubProduct, "updated", dealshub_product_obj.uuid, prev_product_obj, dealshub_product_obj, dealshub_product_obj.location_group, render_value)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PublishDealsHubProductAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class UnPublishDealsHubProductAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UnPublishDealsHubProductAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("PublishAdminCategoryAPI Restricted Access!")
                return Response(data=response)

            uuid = data["product_uuid"]
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=uuid)
            prev_product_obj = deepcopy(dealshub_product_obj)
            dealshub_product_obj.is_published = False
            dealshub_product_obj.save()

            response['status'] = 200
            render_value = dealshub_product_obj.get_seller_sku() + " is unpublished on " + dealshub_product_obj.location_group.name
            activitylog(request.user, DealsHubProduct, "updated", dealshub_product_obj.uuid, prev_product_obj, dealshub_product_obj, dealshub_product_obj.location_group, render_value)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UnPublishDealsHubProductAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class ActivateCODDealsHubProductAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("ActivateCODDealsHubProductAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("ActivateCODDealsHubProductAPI Restricted Access!")
                return Response(data=response)

            uuid = data["product_uuid"]
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=uuid)
            prev_product_obj = deepcopy(dealshub_product_obj)
            dealshub_product_obj.is_cod_allowed = True
            dealshub_product_obj.save()

            response['status'] = 200
            render_value = "COD activated for " + dealshub_product_obj.get_seller_sku()
            activitylog(request.user, DealsHubProduct, "updated", dealshub_product_obj.uuid, prev_product_obj, dealshub_product_obj, dealshub_product_obj.location_group, render_value)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ActivateCODDealsHubProductAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class DeactivateCODDealsHubProductAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("DeactivateCODDealsHubProductAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("DeactivateCODDealsHubProductAPI Restricted Access!")
                return Response(data=response)

            uuid = data["product_uuid"]
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=uuid)
            prev_product_obj = deepcopy(dealshub_product_obj)
            dealshub_product_obj.is_cod_allowed = False
            dealshub_product_obj.save()

            response['status'] = 200
            render_value = "COD deactivated for " + dealshub_product_obj.get_seller_sku()
            activitylog(request.user, DealsHubProduct, "updated", dealshub_product_obj.uuid, prev_product_obj, dealshub_product_obj, dealshub_product_obj.location_group, render_value)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeactivateCODDealsHubProductAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class DeleteProductFromSectionAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("DeleteProductFromSectionAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("DeleteProductFromSectionAPI Restricted Access!")
                return Response(data=response)

            section_uuid = data["sectionUuid"]
            product_uuid = data["productUuid"]

            section_obj = Section.objects.get(uuid=section_uuid)
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=product_uuid)
            prev_product_obj = deepcopy(dealshub_product_obj)
            dealshub_product_obj.promotion = None
            dealshub_product_obj.save()
            
            custom_product_section_obj = CustomProductSection.objects.get(section=section_obj, product=dealshub_product_obj)
            custom_product_section_obj.delete()
            
            response['status'] = 200
            render_value = dealshub_product_obj.get_seller_sku() + " removed from " + section_obj.name + " on " + section_obj.location_group.name
            activitylog(request.user, DealsHubProduct, "updated", dealshub_product_obj.uuid, prev_product_obj, dealshub_product_obj, section_obj.location_group, render_value)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteProductFromSectionAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class PublishDealsHubProductsAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("PublishDealsHubProductsAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("PublishDealsHubProductsAPI Restricted Access!")
                return Response(data=response)

            product_uuid_list = data["product_uuid_list"]
            location_group_obj = None
            for uuid in product_uuid_list:
                dealshub_product_obj = DealsHubProduct.objects.get(uuid=uuid)
                dealshub_product_obj.is_published = True
                dealshub_product_obj.save()
                location_group_obj = dealshub_product_obj.location_group

            response['status'] = 200
            render_value = str(len(product_uuid_list)) + " products published on " + location_group_obj.name
            activitylog(request.user, DealsHubProduct, "updated", '', None, None, location_group_obj, render_value)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PublishDealsHubProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class UnPublishDealsHubProductsAPI(APIView):
    
    def post(self, request, *args, **kwargs):
        
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UnPublishDealsHubProductsAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UnPublishDealsHubProductsAPI Restricted Access!")
                return Response(data=response)

            product_uuid_list = data["product_uuid_list"]
            location_group_obj = None
            for uuid in product_uuid_list:
                dealshub_product_obj = DealsHubProduct.objects.get(uuid=uuid)
                dealshub_product_obj.is_published = False
                dealshub_product_obj.save()
                location_group_obj = dealshub_product_obj.location_group

            response['status'] = 200
            render_value = str(len(product_uuid_list)) + " products unpublished on " + location_group_obj.name
            activitylog(request.user, DealsHubProduct, "updated", '', None, None, location_group_obj, render_value)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UnPublishDealsHubProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchB2BDealshubAdminSectionsAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchB2BDealshubAdminSectionsAPI: %s", str(data))

            language_code = data.get("language","en")

            limit = data.get("limit", False)
            is_dealshub = data.get("isDealshub", False)

            is_bot = data.get("isBot", False)
            is_bot_cohort = data.get("isBotCohort","HIDE")

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            b2b_user_obj = None
            dealshub_user_obj = None
            if request.user != None and str(request.user)!="AnonymousUser":
                logger.info("REQUEST USER: %s", str(request.user))
                b2b_user_obj = B2BUser.objects.get(username = request.user.username)
                dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            is_user_authenticated = check_account_status(b2b_user_obj)

            resolution = data.get("resolution", "low")

            if is_bot:
                cache_key = is_bot_cohort+"-"+location_group_uuid
            else:
                cache_key = "HIDE"+"-"+location_group_uuid
                if is_user_authenticated:
                    cohort = b2b_user_obj.cohort
                    cache_key = "SHOW"+"-"+cohort+location_group_uuid
            if is_dealshub==True and is_bot==False:
                cached_value = cache.get(cache_key, "has_expired")
                if cached_value!="has_expired":
                    response["is_user_authenticated"] = is_user_authenticated
                    response["sections_list"] = json.loads(cached_value)
                    response["circular_category_index"] = location_group_obj.circular_category_index
                    response['status'] = 200
                    logger.info("true or false %s", is_user_authenticated)
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
                        temp_dict2["promotional_price"] = dealshub_product_obj.get_promotional_price(dealshub_user_obj)
                        temp_dict2["now_price"] = dealshub_product_obj.get_now_price(dealshub_user_obj)
                    else:
                        temp_dict2["now_price"] = dealshub_product_obj.now_price
                        temp_dict2["now_price_cohort1"] = dealshub_product_obj.now_price_cohort1
                        temp_dict2["now_price_cohort2"] = dealshub_product_obj.now_price_cohort2
                        temp_dict2["now_price_cohort3"] = dealshub_product_obj.now_price_cohort3
                        temp_dict2["now_price_cohort4"] = dealshub_product_obj.now_price_cohort4
                        temp_dict2["now_price_cohort5"] = dealshub_product_obj.now_price_cohort5

                        temp_dict2["promotional_price"] = dealshub_product_obj.promotional_price
                        temp_dict2["promotional_price_cohort1"] = dealshub_product_obj.promotional_price_cohort1
                        temp_dict2["promotional_price_cohort2"] = dealshub_product_obj.promotional_price_cohort2
                        temp_dict2["promotional_price_cohort3"] = dealshub_product_obj.promotional_price_cohort3
                        temp_dict2["promotional_price_cohort4"] = dealshub_product_obj.promotional_price_cohort4
                        temp_dict2["promotional_price_cohort5"] = dealshub_product_obj.promotional_price_cohort5

                    temp_dict2["was_price"] = dealshub_product_obj.get_was_price(dealshub_user_obj)
                    temp_dict2["moq"] = dealshub_product_obj.get_moq(dealshub_user_obj)
                    temp_dict2["stock"] = dealshub_product_obj.stock
                    temp_dict2["is_new_arrival"] = dealshub_product_obj.is_new_arrival
                    temp_dict2["is_on_sale"] = dealshub_product_obj.is_on_sale
                    if promotion_obj==None:
                        product_promotion_details = get_product_promotion_details(dealshub_product_obj)
                        for key in product_promotion_details.keys():
                            temp_dict2[key]=product_promotion_details[key]
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

                    try:
                        if unit_banner_image_obj.image!=None:
                            if resolution=="low":
                                temp_dict2["url"] = unit_banner_image_obj.image.mid_image.url
                                if unit_banner_image_obj.image_ar!=None:
                                    temp_dict2["url-ar"] = unit_banner_image_obj.image_ar.mid_image.url
                                else:
                                    temp_dict2["url-ar"] = unit_banner_image_obj.image.mid_image.url
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
                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        logger.error("FetchB2BDealshubAdminSectionsAPI: %s at %s with image %s", e, str(exc_tb.tb_lineno),  str(unit_banner_image_obj.uuid))

                    temp_dict2["mobileUrl"] = ""
                    temp_dict2["mobileUrl-ar"] = ""
                    if unit_banner_image_obj.mobile_image!=None:
                        if resolution=="low":
                            temp_dict2["mobileUrl"] = unit_banner_image_obj.mobile_image.mid_image.url
                            if unit_banner_image_obj.mobile_image_ar!=None:
                                temp_dict2["mobileUrl-ar"] = unit_banner_image_obj.mobile_image_ar.mid_image.url
                            else:
                                temp_dict2["mobileUrl-ar"] = unit_banner_image_obj.mobile_image.mid_image.url
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

            response["is_user_authenticated"] = is_user_authenticated
            response["sections_list"] = dealshub_admin_sections
            response["circular_category_index"] = location_group_obj.circular_category_index
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchB2BDealshubAdminSectionsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
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
            parent_banner_uuid = data.get("parent_banner_uuid","")
            parent_banner_obj = None
            if parent_banner_uuid!="":
                parent_banner_obj = Banner.objects.get(uuid=parent_banner_uuid)

            resolution = data.get("resolution", "low")

            cache_key = location_group_uuid + "-" + parent_banner_uuid + "-" + language_code
            if is_dealshub==True and is_bot==False:
                cached_value = cache.get(cache_key, "has_expired")
                if cached_value!="has_expired":
                    response["sections_list"] = json.loads(cached_value)["sections_list"]
                    response["circular_category_index"] = json.loads(cached_value)["circular_category_index"]
                    response['status'] = 200
                    return Response(data=response)


            section_objs = Section.objects.filter(location_group__uuid=location_group_uuid, parent_banner=parent_banner_obj).order_by('order_index')

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
            section_products_list = get_section_products(location_group_obj, is_dealshub, language_code, resolution, limit, section_objs)
            banner_objs = Banner.objects.filter(location_group__uuid=location_group_uuid, parent=parent_banner_obj).order_by('order_index')

            if is_dealshub==True:
                banner_objs = banner_objs.filter(is_published=True)
            
            banner_image_objs_list = get_banner_image_objects(is_dealshub, language_code, resolution, banner_objs)
            dealshub_admin_sections += section_products_list
            dealshub_admin_sections += banner_image_objs_list
            dealshub_admin_sections = sorted(dealshub_admin_sections, key = lambda i: int(i["orderIndex"]))

            response["circular_category_index"] = location_group_obj.circular_category_index

            try:
                if location_group_obj.name == "PARA JOHN - UAE" and is_dealshub == True:
                    temp_dict = {}
                    best_seller_product = []
                    dealshub_product_objs = DealsHubProduct.objects.filter(location_group = location_group_obj,is_published = True, is_bestseller=True).exclude(now_price=0).exclude(stock=0)[:3]
                    for dealshub_product_obj in dealshub_product_objs:
                        temp_dict2 = dealshub_product_detail_in_dict(location_group_obj,dealshub_product_obj)
                        best_seller_product.append(temp_dict2)

                    featured_products = []
                    dealshub_product_objs = DealsHubProduct.objects.filter(location_group = location_group_obj,is_published = True, is_featured=True).exclude(now_price=0).exclude(stock=0)[:3]
                    for dealshub_product_obj in dealshub_product_objs:
                        temp_dict2 = dealshub_product_detail_in_dict(location_group_obj,dealshub_product_obj)
                        featured_products.append(temp_dict2)

                    new_arrival_product = []
                    dealshub_product_objs = DealsHubProduct.objects.filter(location_group = location_group_obj,is_published = True, is_new_arrival=True).exclude(now_price=0).exclude(stock=0)[:3]
                    for dealshub_product_obj in dealshub_product_objs:
                        temp_dict2 = dealshub_product_detail_in_dict(location_group_obj,dealshub_product_obj)
                        new_arrival_product.append(temp_dict2)

                    #logger.info("Inside para john loop 2 - 14 products done")
                    temp_dict["type"] = "TiledProducts"
                    temp_dict["best_products"] = best_seller_product
                    temp_dict["featured_products"] = featured_products
                    temp_dict["new_arrival"] = new_arrival_product

                    tiled_product_index = location_group_obj.tiled_product_index
                    temp_dict["orderIndex"] = tiled_product_index
                            
                    for section in dealshub_admin_sections[tiled_product_index:]:
                        section["orderIndex"]+=1
                    dealshub_admin_sections.append(temp_dict)
                    dealshub_admin_sections = sorted(dealshub_admin_sections, key = lambda i: i["orderIndex"])

                    temp_dict_category = {}
                    temp_dict_category["category_tabs"] = []
                                    
                    website_group_obj = location_group_obj.website_group
                    category_objs = website_group_obj.categories.all()
                    
                    #logger.info("Inside para john loop 3 - before category loop")
                    for category_obj in category_objs:
                        temp_dict_category_products = []
                        dealshub_product_objs = DealsHubProduct.objects.filter(location_group = location_group_obj,is_published = True,category = category_obj).exclude(now_price=0).exclude(stock=0)[:14]
                        #logger.info("Inside para john loop 3 - in category loop iiiiii")
                        for dealshub_product_obj in dealshub_product_objs:
                            #logger.info("Inside para john loop 3 - in dealshub product loop!!!")
                            temp_dict4 = {}
                            temp_dict4 = dealshub_product_detail_in_dict(location_group_obj,dealshub_product_obj)
                            temp_dict_category_products.append(temp_dict4)
                        temp_dict_category["category_tabs"].append({"name":category_obj.get_name(),"products":temp_dict_category_products[:14]})

                    category_tab_product_index = location_group_obj.category_tab_product_index
                    temp_dict_category["orderIndex"] = category_tab_product_index
                    temp_dict_category["type"] = "CategoryTabProducts"    

                    for section in dealshub_admin_sections[category_tab_product_index:]:
                        section["orderIndex"]+=1 
                    dealshub_admin_sections.append(temp_dict_category)
                    dealshub_admin_sections = sorted(dealshub_admin_sections, key = lambda i: i["orderIndex"])
            
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("FetchDealshubAdminSectionsAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["sections_list"] = dealshub_admin_sections
            if is_dealshub==True:
                cache.set(cache_key, json.dumps(response))
            
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchDealshubAdminSectionsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


#API with active log
class SaveDealshubAdminSectionsOrderAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("SaveDealshubAdminSectionsOrderAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("SaveDealshubAdminSectionsOrderAPI Restricted Access!")
                return Response(data=response)

            dealshub_admin_sections = data["dealshubAdminSections"]

            cnt = 1
            location_group_obj = None
            for dealshub_admin_section in dealshub_admin_sections:
                if dealshub_admin_section["type"]=="Banner":
                    uuid = dealshub_admin_section["uuid"]
                    banner_obj = Banner.objects.get(uuid=uuid)
                    banner_obj.order_index = cnt
                    banner_obj.save()
                    location_group_obj = banner_obj.location_group
                elif dealshub_admin_section["type"]=="ProductListing":
                    uuid = dealshub_admin_section["uuid"]
                    section_obj = Section.objects.get(uuid=uuid)
                    section_obj.order_index = cnt
                    section_obj.save()
                    location_group_obj = section_obj.location_group
                
                cnt += 1

            response['status'] = 200
            render_value = "Section order changed on " + location_group_obj.name
            activitylog(request.user, Section, "updated", '', None, None, location_group_obj, render_value)
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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("SearchSectionProductsAutocompleteAPI Restricted Access!")
                return Response(data=response)

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
                available_dealshub_products = available_dealshub_products.filter(Q(product__base_product__base_product_name__icontains=search_string) | Q(product__product_name__icontains=search_string) | Q(product__product_name_sap__icontains=search_string) | Q(product__product_id__icontains=search_string) | Q(product__base_product__seller_sku__icontains=search_string))
                # search_string = remove_stopwords(search_string)
                # words = search_string.split(" ")
                # target_brand = None
                # for word in words:
                #     if website_group_obj.brands.filter(name=word).exists():
                #         target_brand = website_group_obj.brands.filter(name=word)[0]
                #         words.remove(word)
                #         break
                # if target_brand!=None:
                #     available_dealshub_products = available_dealshub_products.filter(product__base_product__brand=target_brand)
                # if len(words)==1:
                #     available_dealshub_products = available_dealshub_products.filter(Q(search_keywords__icontains=","+words[0]+","))
                # elif len(words)==2:
                #     if available_dealshub_products.filter(search_keywords__icontains=","+search_string+",").exists():
                #         available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+search_string+",")
                #     else:
                #         if available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",").exists():
                #             available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",")
                #         else:
                #             available_dealshub_products = available_dealshub_products.filter(Q(search_keywords__icontains=","+words[0]+",") | Q(search_keywords__icontains=","+words[1]+","))
                # elif len(words)==3:
                #     if available_dealshub_products.filter(search_keywords__icontains=","+search_string+",").exists():
                #         available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+search_string+",")
                #     else:
                #         if available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",").filter(search_keywords__icontains=","+words[2]+",").exists():
                #             available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+words[0]+",").filter(search_keywords__icontains=","+words[1]+",").filter(search_keywords__icontains=","+words[2]+",")
                #         else:
                #             temp_available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=words[0]).filter(search_keywords__icontains=words[1])
                #             temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[1]).filter(search_keywords__icontains=words[2])
                #             temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[0]).filter(search_keywords__icontains=words[2])
                #             if temp_available_dealshub_products.exists()==False:
                #                 temp_available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=words[0])
                #                 temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[1])
                #                 temp_available_dealshub_products |= available_dealshub_products.filter(search_keywords__icontains=words[2])
                #             available_dealshub_products = temp_available_dealshub_products.distinct()
                # else:
                #     if available_dealshub_products.filter(search_keywords__icontains=","+search_string+",").exists():
                #         available_dealshub_products = available_dealshub_products.filter(search_keywords__icontains=","+search_string+",")
                #     else:
                #         if len(words)>0:
                #             search_results = DealsHubProduct.objects.none()
                #             for word in words:
                #                 search_results |= available_dealshub_products.filter(search_keywords__icontains=","+word+",")
                #             available_dealshub_products = search_results.distinct()

            category_key_list = available_dealshub_products.values('category').annotate(dcount=Count('category')).order_by('-dcount')[:5]

            category_list = []
            product_list = []
            for category_key in category_key_list:
                try:
                    category_obj = Category.objects.get(pk=category_key["category"])
                    category_name = Category.objects.get(pk=category_key["category"]).name
                    category_list.append(category_name)
                    product_name = available_dealshub_products.filter(category=category_obj)[0].product_name 
                    product_list.append(product_name)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.warning("SearchProductsAutocomplete2API: %s at %s", e, str(exc_tb.tb_lineno))

            category_list = list(set(category_list))

            response["categoryList"] = category_list
            response["productList"] = product_list
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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("SearchProductsAPI Restricted Access!")
                return Response(data=response)

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
                
                temp_dict["logo_url"] = ""
                if location_group_obj.logo != None:
                    temp_dict["logo_url"] = location_group_obj.logo.image.url
                
                temp_dict["footer_logo_url"] = ""
                if location_group_obj.footer_logo != None:
                    temp_dict["footer_logo_url"] = location_group_obj.footer_logo.image.url
                location_info.append(temp_dict)

            company_data = {}
            location_group_obj = location_group_objs.first()
            company_data["name"] = location_group_obj.name
            company_data["contact_info"] = json.loads(location_group_obj.contact_info)
            company_data["whatsapp_info"] = location_group_obj.whatsapp_info
            company_data["email_info"] = location_group_obj.email_info
            company_data["address"] = location_group_obj.addressField
            company_data["primary_color"] = website_group_obj.primary_color
            company_data["secondary_color"] = website_group_obj.secondary_color
            company_data["navbar_text_color"] = website_group_obj.navbar_text_color
            company_data["facebook_link"] = location_group_obj.facebook_link
            company_data["twitter_link"] = location_group_obj.twitter_link
            company_data["instagram_link"] = location_group_obj.instagram_link
            company_data["youtube_link"] = location_group_obj.youtube_link
            company_data["linkedin_link"] = location_group_obj.linkedin_link
            company_data["crunchbase_link"] = location_group_obj.crunchbase_link
            company_data["color_scheme"] = json.loads(location_group_obj.color_scheme)
            
            company_data["logo_url"] = ""
            if location_group_obj.logo != None:
                company_data["logo_url"] = location_group_obj.logo.image.url

            company_data["footer_logo_url"] = ""
            if location_group_obj.footer_logo != None:
                company_data["footer_logo_url"] = location_group_obj.footer_logo.image.url

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

#API with active log
class AddProductToSectionAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddProductToSectionAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("AddProductToSectionAPI Restricted Access!")
                return Response(data=response)

            section_uuid = data["sectionUuid"]
            product_uuid = data["productUuid"]

            is_b2b = False
            location_group_uuid = data.get("locationGroupUuid","")
            location_group_obj = None
            if location_group_uuid != "":
                location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
                is_b2b = location_group_obj.is_b2b

            section_obj = Section.objects.get(uuid=section_uuid)
            prev_section_obj = section_obj
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=product_uuid)
            prev_product_obj = dealshub_product_obj
            
            response["thumbnailImageUrl"] = dealshub_product_obj.get_display_image_url()
            response["name"] = dealshub_product_obj.get_name()
            response["displayId"] = dealshub_product_obj.get_product_id()
            response["sellerSku"] = dealshub_product_obj.get_seller_sku()
            response["brand"] = dealshub_product_obj.get_brand()

            response["now_price"] = str(dealshub_product_obj.now_price)
            response["was_price"] = str(dealshub_product_obj.was_price)
            response["promotional_price"] = str(dealshub_product_obj.promotional_price)
            if is_b2b == True:
                response["now_price_cohort1"] = str(dealshub_product_obj.now_price_cohort1)
                response["now_price_cohort2"] = str(dealshub_product_obj.now_price_cohort2)
                response["now_price_cohort3"] = str(dealshub_product_obj.now_price_cohort3)
                response["now_price_cohort4"] = str(dealshub_product_obj.now_price_cohort4)
                response["now_price_cohort5"] = str(dealshub_product_obj.now_price_cohort5)

                response["promotional_price_cohort1"] = str(dealshub_product_obj.promotional_price_cohort1)
                response["promotional_price_cohort2"] = str(dealshub_product_obj.promotional_price_cohort2)
                response["promotional_price_cohort3"] = str(dealshub_product_obj.promotional_price_cohort3)
                response["promotional_price_cohort4"] = str(dealshub_product_obj.promotional_price_cohort4)
                response["promotional_price_cohort5"] = str(dealshub_product_obj.promotional_price_cohort5)

            response["stock"] = str(dealshub_product_obj.stock)
            response["allowedQty"] = str(dealshub_product_obj.get_allowed_qty())

            if dealshub_product_obj.is_promotional and check_valid_promotion(dealshub_product_obj.promotion)==False:
                dealshub_product_obj.is_promotional = False
                dealshub_product_obj.promotion = None
                dealshub_product_obj.save()

            response["is_product_promotional"] = dealshub_product_obj.is_promotional
            
            if section_obj.promotion!=None and dealshub_product_obj.is_promotional:
                logger.info("product is already in product promotion")
                response['status'] = 403
                return Response(data=response)
            if dealshub_product_obj.promotion!=None:
                logger.info("product is already promoted in other section")
                response['status'] = 405
                return Response(data=response)
            if section_obj.promotion!=None:
                dealshub_product_obj.promotion = section_obj.promotion
                dealshub_product_obj.save()

            if CustomProductSection.objects.filter(section=section_obj, product=dealshub_product_obj).exists()==False:
                order_index = 0
                if CustomProductSection.objects.filter(section=section_obj).count()>0:
                    order_index = CustomProductSection.objects.filter(section=section_obj).order_by("order_index").last().order_index+1
                CustomProductSection.objects.create(section=section_obj, product=dealshub_product_obj, order_index=order_index)
            
            response['status'] = 200
            render_value = dealshub_product_obj.get_seller_sku() + " added to " + section_obj.name + " on " + section_obj.location_group.name
            activitylog(request.user, Section, "updated", section_obj.uuid, prev_section_obj, section_obj, section_obj.location_group, render_value)

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

#API with active log
class AddProductToUnitBannerAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddProductToUnitBannerAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("AddProductToUnitBannerAPI Restricted Access!")
                return Response(data=response)

            unit_banner_image_uuid = data["unitBannerImageUuid"]
            product_uuid = data["productUuid"]

            unit_banner_image_obj = UnitBannerImage.objects.get(uuid=unit_banner_image_uuid)
            prev_unit_banner_image_obj = deepcopy(unit_banner_image_obj)
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
            render_value = dealshub_product_obj.get_seller_sku() + " added to " + unit_banner_image_obj.banner.name + " on " + unit_banner_image_obj.banner.location_group.name
            activitylog(request.user, UnitBannerImage, "updated", unit_banner_image_obj.uuid, prev_unit_banner_image_obj, unit_banner_image_obj, unit_banner_image_obj.banner.location_group, render_value)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddProductToUnitBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class DeleteProductFromUnitBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("DeleteProductFromUnitBannerAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("DeleteProductFromUnitBannerAPI Restricted Access!")
                return Response(data=response)

            unit_banner_image_uuid = data["unitBannerImageUuid"]
            product_uuid = data["productUuid"]

            unit_banner_image_obj = UnitBannerImage.objects.get(uuid=unit_banner_image_uuid)
            prev_unit_banner_image_obj = deepcopy(unit_banner_image_obj)
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=product_uuid)
            dealshub_product_obj.promotion = None
            dealshub_product_obj.save()

            
            custom_product_unit_banner_obj = CustomProductUnitBanner.objects.get(unit_banner=unit_banner_image_obj, product=dealshub_product_obj)
            custom_product_unit_banner_obj.delete()

            response['status'] = 200
            render_value = dealshub_product_obj.get_seller_sku() + " removed from " + unit_banner_image_obj.banner.name + " on " + dealshub_product_obj.location_group.name
            activitylog(request.user, UnitBannerImage, "updated", unit_banner_image_obj.uuid, prev_unit_banner_image_obj, unit_banner_image_obj, dealshub_product_obj.location_group, render_value)

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
                     
            brand_name = data.get("brand", "").strip()

            min_price = data.get("min_price","")
            max_price = data.get("max_price","")
            min_rating = data.get("rating",0)
            min_discount_percent = data.get("discount_percent",0)

            brand_filter = data.get("brand_filter", [])   
            sort_filter = data.get("sort_filter", {})

            unit_banner_image_uuid = data["unitBannerImageUuid"]
            
            unit_banner_image_obj = UnitBannerImage.objects.get(uuid=unit_banner_image_uuid)

            dealshub_user_obj = None
            if unit_banner_image_obj.banner.location_group.is_b2b==True:
                if request.user != None and str(request.user)!="AnonymousUser":
                    logger.info("REQUEST USER: %s", str(request.user))
                    dealshub_user_obj = DealsHubUser.objects.get(username = request.user.username)

            custom_product_unit_banner_objs = CustomProductUnitBanner.objects.filter(unit_banner=unit_banner_image_obj, product__is_published=True)
            custom_product_unit_banner_objs = custom_product_unit_banner_objs.exclude(product__now_price=0).exclude(product__stock=0)
            dealshub_product_uuid_list = list(custom_product_unit_banner_objs.order_by('order_index').values_list("product__uuid", flat=True).distinct())
            dealshub_product_objs = DealsHubProduct.objects.filter(uuid__in=dealshub_product_uuid_list)

            if min_price!="":
                dealshub_product_objs = dealshub_product_objs.filter(now_price__gte=int(min_price))
            if max_price!="":
                dealshub_product_objs = dealshub_product_objs.filter(now_price__lte=int(max_price))
            if min_rating!=0:
                dealshub_product_objs = dealshub_product_objs.exclude(review=None).annotate(product_avg_rating=Avg('review__rating')).filter(product_avg_rating__gte=float(min_rating))
            if min_discount_percent!=0:
                dealshub_product_objs = dealshub_product_objs.annotate(product_discount=((F('was_price')-F('now_price'))/F('was_price')*100)).filter(product_discount__gte=float(min_discount_percent))
            
            if brand_name!="":
                dealshub_product_objs = dealshub_product_objs.filter(Q(product__base_product__brand__name=brand_name) | Q(product__base_product__brand__name_ar=brand_name))

            brand_list = []
            try:
                brand_list = list(dealshub_product_objs.values_list('product__base_product__brand__name', flat=True).distinct())[:50]
                if language_code == "ar":
                    brand_list = list(dealshub_product_objs.values_list('product__base_product__brand__name_ar', flat=True).distinct())[:50]

                brand_list = list(set(brand_list))
                if len(brand_list)==1:
                    brand_list = []
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SearchAPI brand list: %s at %s", e, str(exc_tb.tb_lineno))
            
            if len(brand_filter)>0:
                dealshub_product_objs = dealshub_product_objs.filter(product__base_product__brand__name__in=brand_filter)      
            
            if sort_filter.get("price", "")=="high-to-low":
                dealshub_product_objs = dealshub_product_objs.order_by('-now_price')
            elif sort_filter.get("price", "")=="low-to-high":
                dealshub_product_objs = dealshub_product_objs.order_by('now_price')
            else:
                dealshub_product_objs = list(dealshub_product_objs)
                dealshub_product_objs.sort(key=lambda t: dealshub_product_uuid_list.index(t.uuid))

            page = int(data.get('page', 1))
            paginator = Paginator(dealshub_product_objs, 50)
            dealshub_product_objs = paginator.page(page)

            product_list = []
            for dealshub_product_obj in dealshub_product_objs:
                if dealshub_product_obj.now_price==0:
                    continue
                temp_dict = {}
                temp_dict["name"] = dealshub_product_obj.get_name(language_code)
                temp_dict["brand"] = dealshub_product_obj.get_brand(language_code)
                temp_dict["seller_sku"] = dealshub_product_obj.get_seller_sku()
                temp_dict["now_price"] = dealshub_product_obj.get_now_price(dealshub_user_obj)
                temp_dict["was_price"] = dealshub_product_obj.get_was_price(dealshub_user_obj)
                temp_dict["promotional_price"] = dealshub_product_obj.get_promotional_price(dealshub_user_obj)
                temp_dict["moq"] = dealshub_product_obj.get_moq(dealshub_user_obj)
                temp_dict["stock"] = dealshub_product_obj.stock
                temp_dict["is_new_arrival"] = dealshub_product_obj.is_new_arrival
                temp_dict["is_on_sale"] = dealshub_product_obj.is_on_sale
                temp_dict["allowedQty"] = dealshub_product_obj.get_allowed_qty()
                temp_dict["isStockAvailable"] = dealshub_product_obj.stock>0
                product_promotion_details = get_product_promotion_details(dealshub_product_obj)
                for key in product_promotion_details.keys():
                    temp_dict[key]=product_promotion_details[key]
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
            response["brand_list"] = brand_list
            response["productList"] = product_list
            #response["is_user_authenticated"] = is_user_authenticated
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchUnitBannerProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

#API with active log
class AddUnitBannerHoveringImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("AddUnitBannerHoveringImageAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("AddUnitBannerHoveringImageAPI Restricted Access!")
                return Response(data=response)

            uuid = data["uuid"]
            hovering_banner_image = data["image"]

            unit_banner_image_obj = UnitBannerImage.objects.get(uuid=uuid)
            prev_unit_banner_image_obj = deepcopy(unit_banner_image_obj)
            image_obj = Image.objects.create(image=hovering_banner_image)
            unit_banner_image_obj.hovering_banner_image = image_obj
            unit_banner_image_obj.save()

            response['uuid'] = image_obj.pk
            response['url'] = image_obj.image.url
            response['status'] = 200
            render_value = "Added banner hovering image for " + unit_banner_image_obj.banner.name + " on " + unit_banner_image_obj.banner.location_group.name
            activitylog(request.user, UnitBannerImage, "updated", unit_banner_image_obj.uuid, prev_unit_banner_image_obj, unit_banner_image_obj, unit_banner_image_obj.banner.location_group, render_value)
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

#API with active log
class AddSectionHoveringImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("AddSectionHoveringImageAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("AddSectionHoveringImageAPI Restricted Access!")
                return Response(data=response)

            uuid = data["uuid"]
            hovering_banner_image = data["image"]

            section_obj = Section.objects.get(uuid=uuid)
            prev_section_obj = deepcopy(section_obj)
            image_obj = Image.objects.create(image=hovering_banner_image)
            section_obj.hovering_banner_image = image_obj
            section_obj.save()

            response['uuid'] = image_obj.pk
            response['url'] = image_obj.image.url
            response['status'] = 200
            render_value = "Added section hovering image for " + section_obj.name + " on " + section_obj.location_group.name
            activitylog(request.user, Section, "updated", section_obj.uuid, prev_section_obj, section_obj, section_obj.location_group, render_value)

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

#API with active log
class DeleteHoveringImageAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteHoveringImageAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("DeleteHoveringImageAPI Restricted Access!")
                return Response(data=response)

            uuid = data["uuid"]

            Image.objects.get(pk=uuid).delete()

            response['status'] = 200
            render_value = "Hovering Image deleted"
            activitylog(request.user, Image, "deleted", "", None, None, None, render_value)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteHoveringImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class UpdateSuperCategoryImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UpdateSuperCategoryImageAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UpdateSuperCategoryImageAPI Restricted Access!")
                return Response(data=response)

            uuid = data["uuid"]
            image = data["image"]

            super_category_obj = SuperCategory.objects.get(uuid=uuid)
            prev_super_category_obj = deepcopy(super_category_obj)
            image_obj = Image.objects.create(image=image)
            super_category_obj.image = image_obj
            super_category_obj.save()

            response["imageUrl"] = image_obj.mid_image.url
            response['status'] = 200
            render_value = super_category_obj.name + " image updated"
            activitylog(request.user, SuperCategory, "updated", super_category_obj.uuid, prev_super_category_obj, super_category_obj, None, render_value)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateSuperCategoryImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class UpdateUnitBannerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateUnitBannerAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UpdateUnitBannerAPI Restricted Access!")
                return Response(data=response)

            uuid = data["uuid"]
            is_promotional = data["is_promotional"]
            
            unit_banner_obj = UnitBannerImage.objects.get(uuid=uuid)
            prev_banner_obj = unit_banner_obj

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
            activitylog(request.user, UnitBannerImage, "updated", unit_banner_obj.uuid, prev_banner_obj, unit_banner_obj, unit_banner_obj.banner.location_group, "Promotion in UnitBannerImage updated")

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateUnitBannerAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class CreateVoucherAPI(APIView):
    
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("CreateVoucherAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("CreateVoucherAPI Restricted Access!")
                return Response(data=response)

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
            render_value = "Voucher " + voucher_obj.voucher_code + " created on " + location_group_obj.name
            activitylog(request.user, Voucher, "created", voucher_obj.uuid, None, voucher_obj, location_group_obj, render_value)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateVoucherAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

#API with active log
class UpdateVoucherAPI(APIView):
    
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UpdateVoucherAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UpdateVoucherAPI Restricted Access!")
                return Response(data=response)

            voucher_uuid = data["voucher_uuid"]
            voucher_obj = Voucher.objects.get(uuid=voucher_uuid)
            prev_voucher_obj = deepcopy(voucher_obj)

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

            location_group_obj = voucher_obj.location_group

            response["status"] = 200
            render_value = "Voucher " + voucher_obj.voucher_code + " updated on " + location_group_obj.name
            activitylog(request.user, Voucher, "updated", voucher_obj.uuid, prev_voucher_obj, voucher_obj, location_group_obj, render_value)

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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchVouchersAPI Restricted Access!")
                return Response(data=response)

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

#API with active log
class DeleteVoucherAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteVoucherAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("DeleteVoucherAPI Restricted Access!")
                return Response(data=response)

            uuid = data["voucher_uuid"]
            voucher_obj = Voucher.objects.get(uuid=uuid)
            location_group_obj = voucher_obj.location_group
            voucher_obj.is_deleted = True
            voucher_obj.save()

            response["status"] = 200
            render_value = "Voucher " + voucher_obj.voucher_code + " deleted from " + location_group_obj.name
            activitylog(request.user, Voucher, "deleted", "", voucher_obj, None, location_group_obj, render_value)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteVoucherAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

#API with active log
class PublishVoucherAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("PublishVoucherAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("PublishVoucherAPI Restricted Access!")
                return Response(data=response)

            uuid = data["voucher_uuid"]
            voucher_obj = Voucher.objects.get(uuid=uuid)
            prev_voucher_obj = deepcopy(voucher_obj)
            voucher_obj.is_published = True
            voucher_obj.save()

            location_group_obj = voucher_obj.location_group

            response["status"] = 200
            render_value = "Voucher " + voucher_obj.voucher_code + " published on " + location_group_obj.name
            activitylog(request.user, Voucher, "updated", voucher_obj.uuid, prev_voucher_obj, voucher_obj, location_group_obj, render_value)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PublishVoucherAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

#API with active log
class UnPublishVoucherAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UnPublishVoucherAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UnPublishVoucherAPI Restricted Access!")
                return Response(data=response)

            uuid = data["voucher_uuid"]
            voucher_obj = Voucher.objects.get(uuid=uuid)
            prev_voucher_obj = deepcopy(voucher_obj)
            voucher_obj.is_published = False
            voucher_obj.save()

            location_group_obj = voucher_obj.location_group

            response["status"] = 200
            render_value = "Voucher " + voucher_obj.voucher_code + " unpublished on " + location_group_obj.name
            activitylog(request.user, Voucher, "updated", voucher_obj.uuid, prev_voucher_obj, voucher_obj, location_group_obj, render_value)

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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchPostaPlusDetailsAPI Restricted Access!")
                return Response(data=response)

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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UpdateUnitOrderQtyAdminAPI Restricted Access!")
                return Response(data=response)

            uuid = data["unitOrderUuid"]
            quantity = int(data["quantity"])

            unit_order_obj = UnitOrder.objects.get(uuid=uuid)
            order_obj = unit_order_obj.order
            omnycomm_user = OmnyCommUser.objects.get(username=request.user.username)

            if quantity==0:
                if UnitOrder.objects.filter(order=order_obj).count()==1:
                    response["message"] = "order cannot be empty"
                    return Response(data=response)
                else:
                    unit_order_cancel_information = {
                        "event" : "unit_order_delete",
                        "information" : {
                            "orderid":unit_order_obj.orderid,
                            "seller_sku": unit_order_obj.product.get_seller_sku(),
                            "qty": unit_order_obj.quantity
                        }
                    }

                    VersionOrder.objects.create(order=order_obj,
                                            user= omnycomm_user,
                                            change_information=json.dumps(unit_order_cancel_information))
                    unit_order_obj.delete()
            else:
                unit_order_update_information = {
                    "event" : "unit_order_update",
                    "information" : {
                        "orderid": unit_order_obj.orderid,
                        "seller_sku": unit_order_obj.product.get_seller_sku(),
                        "old_qty": unit_order_obj.quantity,
                        "new_qty": quantity
                    }
                }
                VersionOrder.objects.create(order=order_obj,
                                            user= omnycomm_user,
                                            change_information=json.dumps(unit_order_update_information))

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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UpdateOrderShippingAdminAPI Restricted Access!")
                return Response(data=response)

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

            omnycomm_user = OmnyCommUser.objects.get(username=request.user.username)
            old_address_lines = json.loads(order_obj.shipping_address.address_lines)
            address_change_info = {
                "event" : "address",
                "information" : {
                    "new_address" : {
                        "first_name" : first_name,
                        "last_name" : last_name,
                        "contact_number" : contact_number,
                        "line1" : line1,
                        "line2" : line2,
                        "emirates" : emirates
                    },
                    "old_address": {
                        "first_name" : order_obj.shipping_address.first_name,
                        "last_name" : order_obj.shipping_address.last_name,
                        "contact_number" : order_obj.shipping_address.contact_number,
                        "line1" : old_address_lines[0],
                        "line2" : old_address_lines[1],
                        "emirates" : order_obj.shipping_address.emirates
                    }
                }
            }

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

            order_version_obj = VersionOrder.objects.create(order= order_obj,
                                                            user= omnycomm_user,
                                                            change_information=json.dumps(address_change_info))

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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchSEOAdminAutocompleteAPI Restricted Access!")
                return Response(data=response)
            
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
                    temp_dict["uuid"] = seo_brand_obj.uuid
                    autocomplete_list.append(temp_dict)
            elif page_type=="product":
                dealshub_product_objs = DealsHubProduct.objects.filter(location_group=location_group_obj).filter(Q(product_name__icontains=search_string) | Q(product__base_product__seller_sku__icontains=search_string))[:5]
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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchSEOAdminDetailsAPI Restricted Access!")
                return Response(data=response)
            
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
                seo_brand_obj = SEOBrand.objects.get(uuid=uuid, brand__organization__name="WIG")
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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("SaveSEOAdminDetailsAPI Restricted Access!")
                return Response(data=response)
            
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
                seo_brand_obj = SEOBrand.objects.get(uuid=uuid, brand__organization__name="WIG")
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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchLocationGroupSettingsAPI Restricted Access!")
                return Response(data=response)
            
            location_group_uuid = data["locationGroupUuid"]

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            response["delivery_fee"] = location_group_obj.delivery_fee
            response["cod_charge"] = location_group_obj.cod_charge
            response["free_delivery_threshold"] = location_group_obj.free_delivery_threshold
            response["vat"] = location_group_obj.vat
            response["today_sales_target"] = location_group_obj.today_sales_target
            response["monthly_sales_target"] = location_group_obj.monthly_sales_target
            response["today_orders_target"] = location_group_obj.today_orders_target
            response["monthly_orders_target"] = location_group_obj.monthly_orders_target
            
            response["region_list"] = json.loads(location_group_obj.region_list)
            
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchLocationGroupSettingsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class UpdateLocationGroupSettingsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateLocationGroupSettingsAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UpdateLocationGroupSettingsAPI Restricted Access!")
                return Response(data=response)
            
            location_group_uuid = data["locationGroupUuid"]

            delivery_fee = float(data["delivery_fee"])
            cod_charge = float(data["cod_charge"])
            free_delivery_threshold = float(data["free_delivery_threshold"])
            vat = float(data.get("vat", 5))
            today_sales_target = float(data["today_sales_target"])
            monthly_sales_target = float(data["monthly_sales_target"])
            today_orders_target = float(data["today_orders_target"])
            monthly_orders_target = float(data["monthly_orders_target"])

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            prev_location_group_obj = deepcopy(location_group_obj)

            location_group_obj.delivery_fee = delivery_fee
            location_group_obj.cod_charge = cod_charge
            location_group_obj.free_delivery_threshold = free_delivery_threshold
            location_group_obj.vat = vat
            location_group_obj.today_sales_target = today_sales_target
            location_group_obj.monthly_sales_target = monthly_sales_target
            location_group_obj.today_orders_target = today_orders_target
            location_group_obj.monthly_orders_target = monthly_orders_target
            location_group_obj.save()
            
            response['status'] = 200
            render_value = location_group_obj.name + " settings updated"
            activitylog(request.user, LocationGroup, "updated", location_group_obj.uuid, prev_location_group_obj, location_group_obj, location_group_obj, render_value)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateLocationGroupSettingsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchSalesTargetsListAPI(APIView):
    
    def post(self, request, *args, **kwargs):
    
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchSalesExecutiveTargetsListAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchSalesExecutiveTargetsListAPI Restricted Access!")
                return Response(data=response)
            
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            sales_target_objs = SalesTarget.objects.filter(location_group=location_group_obj)

            sales_target_list = []
            for sales_target_obj in sales_target_objs:
                temp_dict = {}
                temp_dict["user_first_name"] = sales_target_obj.user.first_name
                temp_dict["user_username"] = sales_target_obj.user.username
                temp_dict["uuid"] = sales_target_obj.uuid
                temp_dict["today_sales_target"] = sales_target_obj.today_sales_target
                temp_dict["monthly_sales_target"] = sales_target_obj.monthly_sales_target
                temp_dict["today_orders_target"] = sales_target_obj.today_orders_target
                temp_dict["monthly_orders_target"] = sales_target_obj.monthly_orders_target
                sales_target_list.append(temp_dict)
            
            response["currency"] = location_group_obj.location.currency
            response["sales_target_list"] = sales_target_list
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSalesExecutiveTargetsListAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class UpdateSalesTargetAPI(APIView):

    def post(self, request, *args, **kwargs):
        
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateSalesTargetAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UpdateSalesTargetAPI Restricted Access!")
                return Response(data=response)
            
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            sales_target_uuid = data["sales_target_uuid"]
            sales_target_obj = SalesTarget.objects.get(uuid=sales_target_uuid, location_group=location_group_obj)
            prev_sales_target_obj = deepcopy(sales_target_obj)
            
            today_sales_target = float(data["today_sales_target"])
            monthly_sales_target = float(data["monthly_sales_target"])
            today_orders_target = float(data["today_orders_target"])
            monthly_orders_target = float(data["monthly_orders_target"])
            
            sales_target_obj.today_sales_target = today_sales_target
            sales_target_obj.monthly_sales_target = monthly_sales_target
            sales_target_obj.today_orders_target = today_orders_target
            sales_target_obj.monthly_orders_target = monthly_orders_target
            sales_target_obj.save()
            
            response['status'] = 200
            render_value = "Sales Target updated for " + sales_target_obj.user.username + " for " + location_group_obj.name
            activitylog(request.user, SalesTarget, "updated", sales_target_obj.uuid, prev_sales_target_obj, sales_target_obj, location_group_obj, render_value)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateSalesTargetAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class AddSalesTargetAPI(APIView):

    def post(self, request, *args, **kwargs):
            
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddSalesTargetAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("AddSalesTargetAPI Restricted Access!")
                return Response(data=response)
            
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            sales_person_obj = OmnyCommUser.objects.get(username=data["sales_person_username"])

            if SalesTarget.objects.filter(location_group=location_group_obj, user=sales_person_obj).exists():
                response['status'] = 409
                response['message'] = "Target already set for this user"
                return Response(data=response)

            sales_target_obj = SalesTarget.objects.create(location_group=location_group_obj,
                                                          user=sales_person_obj,
                                                          today_sales_target=data["today_sales_target"],
                                                          monthly_sales_target=data["monthly_sales_target"],
                                                          today_orders_target=data["today_orders_target"],
                                                          monthly_orders_target=data["monthly_orders_target"])
            
            response['status'] = 200
            render_value = "Sales Target created for " + sales_person_obj.username + " for " + location_group_obj.name
            activitylog(request.user, SalesTarget, "created", sales_target_obj.uuid, None, sales_target_obj, location_group_obj, render_value)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddSalesTargetAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class AddProductToOrderAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddProductToOrderAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("AddProductToOrderAPI Restricted Access!")
                return Response(data=response)

            product_uuid = data["productUuid"]
            order_uuid = data["orderUuid"]

            dealshub_product_obj = DealsHubProduct.objects.get(uuid=product_uuid)

            order_obj = Order.objects.get(uuid=order_uuid)

            if UnitOrder.objects.filter(order=order_obj,product=dealshub_product_obj).exists()==True:
                response["message"] = "Product Already Exists"
                logger.info("AddProductToOrderAPI: Product Already Exists")
                return Response(data=response)

            dealshub_user_obj = order_obj.owner
            deaslshub_product_price = dealshub_product_obj.get_actual_price(dealshub_user_obj)

            if deaslshub_product_price == 0.0:
                response["message"] = "Product Price is 0 for the user"
                logger.info("AddProductToOrderAPI: Product Price 0.0")
                return Response(data=response)

            unit_order_obj = UnitOrder.objects.create(order=order_obj, 
                                                      product=dealshub_product_obj, 
                                                      quantity=1,
                                                      price=deaslshub_product_price)
            UnitOrderStatus.objects.create(unit_order=unit_order_obj)

            omnycomm_user = OmnyCommUser.objects.get(username=request.user.username)
            unit_order_add_information = {
                "event" : "unit_order_add",
                "information" : {
                    "orderid": unit_order_obj.orderid,
                    "seller_sku": dealshub_product_obj.get_seller_sku()
                }
            }

            VersionOrder.objects.create(order=order_obj,
                                        user=omnycomm_user,
                                        change_information=json.dumps(unit_order_add_information))

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

#API with active log
class UpdateOrderChargesAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateOrderChargesAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UpdateOrderChargesAPI Restricted Access!")
                return Response(data=response)

            order_uuid = data["orderUuid"]
            offline_cod_charge = float(data["offline_cod_charge"])
            offline_delivery_fee = float(data["offline_delivery_fee"])

            omnycomm_user_obj = OmnyCommUser.objects.get(username=request.user.username)

            order_obj = Order.objects.get(uuid=order_uuid)
            if order_obj.is_order_offline==True:
                if order_obj.delivery_fee != offline_delivery_fee:
                    delivery_change_information = {
                        "event": "update_delivery_fee",
                        "information": {
                            "old_delivery_fee": order_obj.delivery_fee,
                            "new_delivery_fee": offline_delivery_fee
                        }
                    }
                    VersionOrder.objects.create(order=order_obj, user=omnycomm_user_obj, change_information=json.dumps(delivery_change_information))
                order_obj.delivery_fee = offline_delivery_fee
                if order_obj.cod_charge != offline_cod_charge:
                    cod_change_information = {
                        "event": "update_cod_charge",
                        "information": {
                            "old_cod_charge": order_obj.cod_charge,
                            "new_cod_charge": offline_cod_charge
                        }
                    }
                    VersionOrder.objects.create(order=order_obj, user=omnycomm_user_obj, change_information=json.dumps(cod_change_information))
                order_obj.cod_charge = offline_cod_charge
                order_obj.to_pay = order_obj.get_total_amount()
                order_obj.real_to_pay = order_obj.get_total_amount(is_real=True)
                order_obj.save()

            response["toPay"] = order_obj.to_pay
            response["vat"] = order_obj.get_vat(is_real=True)
            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateOrderChargesAPI: %s at %s", e, str(exc_tb.tb_lineno))

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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchLogixShippingStatusAPI Restricted Access!")
                return Response(data=response)

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


class AskProductReviewsCronAPI(APIView):
    
    authentication_classes = (CsrfExemptSessionAuthentication,) 
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AskProductReviewsCronAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            time_delta = datetime.timedelta(days=1)
            now_time = datetime.datetime.now()
            start_time = now_time - 10*time_delta
            end_time = now_time - 9*time_delta

            order_uuid_list = list(UnitOrderStatus.objects.filter(date_created__gte=start_time, date_created__lte=end_time, status_admin="delivered").values_list('unit_order__order__uuid').distinct())

            for order_uuid in order_uuid_list:

                unit_orders_for_mail = []
                order_obj = Order.objects.get(uuid=order_uuid[0])

                dh_user_obj = order_obj.owner
                if dh_user_obj.user_token == "":
                    dh_user_obj.user_token = str(uuid.uuid4())
                    dh_user_obj.save()
                user_token = dh_user_obj.user_token

                for unit_order_obj in UnitOrder.objects.filter(order=order_obj):
                    if UnitOrderStatus.objects.filter(unit_order=unit_order_obj, status_admin="delivered").exists():
                        if Review.objects.filter(dealshub_user=dh_user_obj,product=unit_order_obj.product).exists()==False:
                            unit_orders_for_mail.append(unit_order_obj)

                try:                   
                    p1 = threading.Thread(target=send_order_review_mail, args=(order_obj, unit_orders_for_mail,user_token))
                    p1.start()
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("AskProductReviewsCronAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AskProductReviewsCronAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchProductReviewMailAPI(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,) 
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchProductReviewMailAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            user_token = data["user_token"]
            order_uuid = data["order_uuid"]

            order_obj = Order.objects.get(uuid=order_uuid)
            unit_orders_for_mail = []
            
            dh_user_obj = DealsHubUser.objects.get(user_token=user_token)

            for unit_order_obj in UnitOrder.objects.filter(order=order_obj):
                if UnitOrderStatus.objects.filter(unit_order=unit_order_obj, status_admin="delivered").exists():
                    if Review.objects.filter(dealshub_user=dh_user_obj,product=unit_order_obj.product).exists()==False:
                        unit_orders_for_mail.append(unit_order_obj)

            products_for_review = []
            for unit_order_obj in unit_orders_for_mail:
                temp_dict = {}
                dh_product_obj = unit_order_obj.product
                if Review.objects.filter(product=dh_product_obj, dealshub_user=dh_user_obj).exists():
                    temp_dict['status'] = "invalid"
                    products_for_review.append(temp_dict)
                    continue

                temp_dict["product_name"] = dh_product_obj.get_name()
                temp_dict["product_id"] = dh_product_obj.get_product_id()
                temp_dict["seller_sku"] = dh_product_obj.get_seller_sku()
                temp_dict["product_image"] = dh_product_obj.get_main_image_url()
                temp_dict["product_uuid"] = dh_product_obj.uuid
                temp_dict["product_brand"] = dh_product_obj.get_brand()
                temp_dict["status"] = "valid"
                products_for_review.append(temp_dict)
            
            response["products"] = products_for_review
            response["username"] = dh_user_obj.username
            response["order_date"] = order_obj.get_date_created()
            response['order_id'] = order_obj.bundleid
            response["shipping_address"] = order_obj.shipping_address.get_shipping_address()
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductReviewMailAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)

class SubmitProductReviewMailAPI(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,) 
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SubmitProductReviewMailAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            rating = data["rating"]
            review_content = json.loads(data["review_content"])

            subject = str(review_content["subject"])
            content = str(review_content["content"])

            user_token = data["user_token"]
            product_uuid = data["product_uuid"]

            dh_product_obj = DealsHubProduct.objects.get(uuid=product_uuid)
            dh_user_obj = DealsHubUser.objects.get(user_token=user_token)

            review_obj = Review.objects.create(dealshub_user=dh_user_obj, product=dh_product_obj, rating=rating)
            review_content_obj = ReviewContent.objects.create(subject=subject, content=content)
            
            image_count = int(data.get("image_count", 0))
            for i in range(image_count):
                image_obj = Image.objects.create(image=data["image_"+str(i)])
                review_content_obj.images.add(image_obj)
            review_content_obj.save()

            review_obj.content = review_content_obj
            review_obj.save()
            response["uuid"] = review_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SubmitProductReviewMailAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)


FetchProductDetails = FetchProductDetailsAPI.as_view()

FetchSimilarProducts = FetchSimilarProductsAPI.as_view()

FetchNewArrivalProducts = FetchNewArrivalProductsAPI.as_view()

FetchOnSaleProducts = FetchOnSaleProductsAPI.as_view()

FetchSectionProducts = FetchSectionProductsAPI.as_view()

FetchSuperCategories = FetchSuperCategoriesAPI.as_view()

FetchHeadingCategories = FetchHeadingCategoriesAPI.as_view()

FetchCategoriesForNewUser = FetchCategoriesForNewUserAPI.as_view()

SetInterestedCategoriesForNewUser = SetInterestedCategoriesForNewUserAPI.as_view()

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

FetchNestedBanners = FetchNestedBannersAPI.as_view()

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

FetchB2BDealshubAdminSections = FetchB2BDealshubAdminSectionsAPI.as_view()

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

FetchSalesTargetsList = FetchSalesTargetsListAPI.as_view()

UpdateSalesTarget = UpdateSalesTargetAPI.as_view()

AddSalesTarget = AddSalesTargetAPI.as_view()

AddProductToOrder = AddProductToOrderAPI.as_view()

NotifyOrderStatus = NotifyOrderStatusAPI.as_view()

UpdateOrderCharges = UpdateOrderChargesAPI.as_view()

FetchLogixShippingStatus = FetchLogixShippingStatusAPI.as_view()

AskProductReviewsCron = AskProductReviewsCronAPI.as_view()

FetchProductReviewMail = FetchProductReviewMailAPI.as_view()

SubmitProductReviewMail = SubmitProductReviewMailAPI.as_view()
