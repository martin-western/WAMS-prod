from django.db.models import Count

from WAMSApp.models import *

from auditlog.models import *
from dealshub.models import DealsHubProduct
from WAMSApp.utils import *
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
from WAMSApp.views_mws_report import *
from WAMSApp.views_mws_amazon_uk import *
from WAMSApp.views_mws_amazon_uae import *
from WAMSApp.views_dh import *
from WAMSApp.oc_reports import *

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
import urllib.request, urllib.error, urllib.parse
import pandas as pd
import threading

logger = logging.getLogger(__name__)

class UpdatedFetchProductListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data

            logger.info("UpdatedFetchProductListAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            filter_parameters = data["filter_parameters"]
            chip_data = data["tags"]

            page = int(data['page'])  

            search_list_product_objs = Product.objects.none()

            search_list_product_objs = custom_permission_filter_products(request.user)

            if filter_parameters['verified']:
                search_list_product_objs = search_list_product_objs.filter(
                    verified=filter_parameters['verified']).order_by('-pk')
            else:
                search_list_product_objs = search_list_product_objs.order_by('-pk')

            # if filter_parameters["start_date"] != "" and filter_parameters["end_date"] != "":
            #     start_date = datetime.datetime.strptime(
            #         filter_parameters["start_date"], "%b %d, %Y")
            #     end_date = datetime.datetime.strptime(
            #         filter_parameters["end_date"], "%b %d, %Y")
            #     base_product_objs_list = base_product_objs_list.filter(
            #         created_date__gte=start_date).filter(created_date__lte=end_date)

            if filter_parameters["brand_name"] != "":
                brand_obj = Brand.objects.get(name=filter_parameters["brand_name"])
                search_list_product_objs = search_list_product_objs.filter(base_product__brand=brand_obj)

            # if filter_parameters["min_price"] != "":
            #     product_objs_list = product_objs_list.filter(
            #         standard_price__gte=int(filter_parameters["min_price"]))

            # if filter_parameters["max_price"] != "":
            #     product_objs_list = product_objs_list.filter(
            #         standard_price__lte=int(filter_parameters["max_price"]))

        

            without_images = 0
            
            # Images - Yes
            if filter_parameters["images"] == "1":  
                search_list_product_objs = search_list_product_objs.exclude(no_of_images_for_filter=0)

            # Images - No
            elif filter_parameters["images"] == "0":
                without_images = 1
                search_list_product_objs = search_list_product_objs.filter(no_of_images_for_filter=0)

            # Unedited Images - Yes
            elif filter_parameters["unedited_images"] == "1":
                search_list_product_objs = search_list_product_objs.annotate(c=Count('base_product__unedited_images')).filter(c__gt=0)

            # Unedited Images - No
            elif filter_parameters["unedited_images"] == "0":
                search_list_product_objs = search_list_product_objs.annotate(c=Count('base_product__unedited_images')).filter(c=0)

            # Product Description - Yes            
            elif filter_parameters["product_description"] == "1":
                search_list_product_objs = search_list_product_objs.exclude(product_description=None).exclude(product_description="")

            # Product Description - No   
            elif filter_parameters["product_description"] == "0":
                search_list_product_objs = search_list_product_objs.filter(Q(product_description=None) | Q(product_description=""))

            # Product ID - Yes   
            elif filter_parameters["product_id"] == "1":
                search_list_product_objs = search_list_product_objs.exclude(product_id=None).exclude(product_id="")

            # Product ID - No
            elif filter_parameters["product_id"] == "0":
                search_list_product_objs = search_list_product_objs.filter(Q(product_id=None) | Q(product_id=""))

            # Verified Yes
            elif filter_parameters["is_verified"] == "1":  
                search_list_product_objs = search_list_product_objs.filter(verified=True)

            # Verified No
            elif filter_parameters["is_verified"] == "0":  
                search_list_product_objs = search_list_product_objs.filter(verified=False)

            # Main Image Yes
            elif filter_parameters["main_image"] == "1":  
                search_list_product_objs = search_list_product_objs.filter(mainimages__in=MainImages.objects.annotate(num_main_images=Count('main_images')).filter(product__in=search_list_product_objs,is_sourced=True,num_main_images__gt=0))

            # Main Image No
            elif filter_parameters["main_image"] == "0": 
                search_list_product_obj_copy = search_list_product_objs 
                search_list_product_objs = search_list_product_objs.filter(mainimages__in=MainImages.objects.annotate(num_main_images=Count('main_images')).filter(product__in=search_list_product_objs).exclude(is_sourced=True,num_main_images__gt=0))
                search_list_product_objs |= search_list_product_obj_copy.exclude(mainimages__product__in=search_list_product_obj_copy)

            # Sub Images Yes
            elif filter_parameters["sub_image"] == "1":  
                search_list_product_objs = search_list_product_objs.filter(product__in=SubImages.objects.annotate(num_sub_images=Count('sub_images')).filter(product__in=search_list_product_objs,is_sourced=True,num_sub_images__gt=0))

            # Sub Images No
            elif filter_parameters["sub_image"] == "0":  
                search_list_product_obj_copy = search_list_product_objs 
                search_list_product_objs =  search_list_product_objs.filter(product__in=SubImages.objects.annotate(num_sub_images=Count('sub_images')).filter(product__in=search_list_product_objs,is_sourced=True,num_sub_images=0))
                search_list_product_objs |= search_list_product_obj_copy.exclude(product__product__in=search_list_product_obj_copy)

            # PFL Product Features Yes
            elif filter_parameters["pfl_product_features"] == "1": 
                search_list_product_objs = search_list_product_objs.exclude(pfl_product_features="[]").exclude(pfl_product_features="")

            # PFL Product Features No
            elif filter_parameters["pfl_product_features"] == "0": 
                search_list_product_objs = search_list_product_objs.filter(Q(pfl_product_features="[]") | Q(pfl_product_features=""))

            # White  background Image Yes
            elif filter_parameters["white_background_images"] == "1": 
                search_list_product_objs = search_list_product_objs.annotate(num_white_background_images=Count('white_background_images')).filter(num_white_background_images__gt=0)
            
            # White  background Image No
            elif filter_parameters["white_background_images"] == "0": 
                search_list_product_objs = search_list_product_objs.annotate(num_white_background_images=Count('white_background_images')).filter(num_white_background_images=0)
            
            # Lifestyle  Image Yes
            elif filter_parameters["lifestyle_images"] == "1": 
                search_list_product_objs = search_list_product_objs.annotate(num_lifestyle_images=Count('lifestyle_images')).filter(num_lifestyle_images__gt=0)
            
            # Lifestyle  Image No
            elif filter_parameters["lifestyle_images"] == "0": 
                search_list_product_objs = search_list_product_objs.annotate(num_lifestyle_images=Count('lifestyle_images')).filter(num_lifestyle_images=0)
            
            # Giftbox Image Yes
            elif filter_parameters["giftbox_images"] == "1": 
                search_list_product_objs = search_list_product_objs.annotate(num_giftbox_images=Count('giftbox_images')).filter(num_giftbox_images__gt=0)
            
            # Giftbox Image No
            elif filter_parameters["giftbox_images"] == "0": 
                search_list_product_objs = search_list_product_objs.annotate(num_giftbox_images=Count('giftbox_images')).filter(num_giftbox_images=0)
            
            # Transparent Image Yes
            elif filter_parameters["transparent_images"] == "1": 
                search_list_product_objs = search_list_product_objs.annotate(num_transparent_images=Count('transparent_images')).filter(num_transparent_images__gt=0)
            
            #  Transparent Image No
            elif filter_parameters["transparent_images"] == "0": 
                search_list_product_objs = search_list_product_objs.annotate(num_transparent_images=Count('transparent_images')).filter(num_transparent_images=0)
            
            # Product Dimension Yes 
            elif filter_parameters["product_dimension"] == "1" or filter_parameters["product_dimension"] == "0":

                search_list_product_objs_yes = Product.objects.none()

                search_list_product_objs_no = Product.objects.none()

                for product_obj in search_list_product_objs:

                        dimensions_json = json.loads(product_obj.base_product.dimensions)

                        if(dimensions_json["product_dimension_l"]!="" and dimensions_json["product_dimension_b"]!="" and dimensions_json["product_dimension_h"]!=""):
                            search_list_product_objs_yes |= Product.objects.filter(pk=product_obj.pk)

                        else:
                            search_list_product_objs_no |= Product.objects.filter(pk=product_obj.pk)

                if(filter_parameters["product_dimension"] == "1"):
                    search_list_product_objs = search_list_product_objs_yes
                else:
                    search_list_product_objs = search_list_product_objs_no

            # Giftbox Dimension Yes 
            elif filter_parameters["giftbox_dimension"] == "1" or filter_parameters["giftbox_dimension"] == "0":

                search_list_product_objs_yes = Product.objects.none()

                search_list_product_objs_no = Product.objects.none()

                print(type)

                for product_obj in search_list_product_objs:

                        dimensions_json = json.loads(product_obj.base_product.dimensions)

                        if(dimensions_json["giftbox_l"]!="" and dimensions_json["giftbox_b"]!="" and dimensions_json["giftbox_h"]!=""):
                            search_list_product_objs_yes |= Product.objects.filter(pk=product_obj.pk)

                        else:
                            search_list_product_objs_no |= Product.objects.filter(pk=product_obj.pk)

                if(filter_parameters["giftbox_dimension"] == "1"):
                    search_list_product_objs = search_list_product_objs_yes
                else:
                    search_list_product_objs = search_list_product_objs_no

            # Product Name Yes
            elif filter_parameters["product_name"] == "1": 
                search_list_product_objs = search_list_product_objs.exclude(product_name=None).exclude(product_name="")
            
            #  Product Name No
            elif filter_parameters["product_name"] == "0": 
                search_list_product_objs = search_list_product_objs.filter(Q(product_name=None) | Q(product_name=""))
            
            # Sub Image 1 Yes
            elif filter_parameters["sub_image_1"] == "1": 
                search_list_product_objs = search_list_product_objs.filter(product__in=SubImages.objects.annotate(num_sub_images=Count('sub_images')).filter(product__in=search_list_product_objs,is_sourced=True,num_sub_images=1))

            # Sub Image 1 No
            elif filter_parameters["sub_image_1"] == "0": 
                search_list_product_obj_copy = search_list_product_objs 
                search_list_product_objs = search_list_product_objs.filter(product__in=SubImages.objects.annotate(num_sub_images=Count('sub_images')).filter(product__in=search_list_product_objs,is_sourced=True).exclude(num_sub_images=1))
                search_list_product_objs |= search_list_product_obj_copy.exclude(product__product__in=search_list_product_obj_copy)

            # Sub Image 2 Yes
            elif filter_parameters["sub_image_2"] == "1": 
                search_list_product_objs = search_list_product_objs.filter(product__in=SubImages.objects.annotate(num_sub_images=Count('sub_images')).filter(product__in=search_list_product_objs,is_sourced=True,num_sub_images=2))

            # Sub Image 2 No
            elif filter_parameters["sub_image_2"] == "0": 
                search_list_product_obj_copy = search_list_product_objs 
                search_list_product_objs = search_list_product_objs.filter(product__in=SubImages.objects.annotate(num_sub_images=Count('sub_images')).filter(product__in=search_list_product_objs,is_sourced=True).exclude(num_sub_images=2))
                search_list_product_objs |= search_list_product_obj_copy.exclude(product__product__in=search_list_product_obj_copy)

            # Sub Image 3 Yes
            elif filter_parameters["sub_image_3"] == "1": 
                search_list_product_objs = search_list_product_objs.filter(product__in=SubImages.objects.annotate(num_sub_images=Count('sub_images')).filter(product__in=search_list_product_objs,is_sourced=True,num_sub_images=3))

            # Sub Image 3 No
            elif filter_parameters["sub_image_3"] == "0": 
                search_list_product_obj_copy = search_list_product_objs 
                search_list_product_objs = search_list_product_objs.filter(product__in=SubImages.objects.annotate(num_sub_images=Count('sub_images')).filter(product__in=search_list_product_objs,is_sourced=True).exclude(num_sub_images=3))
                search_list_product_objs |= search_list_product_obj_copy.exclude(product__product__in=search_list_product_obj_copy)

            # White Background Image 1 Yes
            elif filter_parameters["white_background_image_1"] == "1": 
                search_list_product_objs = search_list_product_objs.annotate(num_white_background_images=Count('white_background_images')).filter(num_white_background_images=1)
           
            # White Background Image 1 No
            elif filter_parameters["white_background_image_1"] == "0": 
                search_list_product_objs = search_list_product_objs.annotate(num_white_background_images=Count('white_background_images')).exclude(num_white_background_images=1)

            # White Background Image 2 Yes
            elif filter_parameters["white_background_image_2"] == "1": 
                search_list_product_objs = search_list_product_objs.annotate(num_white_background_images=Count('white_background_images')).filter(num_white_background_images=2)
           
            # White Background Image 2 No
            elif filter_parameters["white_background_image_2"] == "0": 
                search_list_product_objs = search_list_product_objs.annotate(num_white_background_images=Count('white_background_images')).exclude(num_white_background_images=2)

            # Lifestyle Image 1 Yes
            elif filter_parameters["lifestyle_image_1"] == "1": 
                search_list_product_objs = search_list_product_objs.annotate(num_lifestyle_images=Count('lifestyle_images')).filter(num_lifestyle_images=1)
            
            # Lifestyle Image 1 No
            elif filter_parameters["lifestyle_image_1"] == "0": 
                search_list_product_objs = search_list_product_objs.annotate(num_lifestyle_images=Count('lifestyle_images')).exclude(num_lifestyle_images=1)
            
            # Lifestyle Image 2 Yes
            elif filter_parameters["lifestyle_image_2"] == "1": 
                search_list_product_objs = search_list_product_objs.annotate(num_lifestyle_images=Count('lifestyle_images')).filter(num_lifestyle_images=2)
            
            # Lifestyle Image 2 No
            elif filter_parameters["lifestyle_image_2"] == "0": 
                search_list_product_objs = search_list_product_objs.annotate(num_lifestyle_images=Count('lifestyle_images')).exclude(num_lifestyle_images=2)
            
                    
            if len(chip_data) != 0:
                search_list_product_lookup = Product.objects.none()
                for tag in chip_data:
                    search_list_product_lookup |= search_list_product_objs.filter(
                        Q(base_product__base_product_name__icontains=tag) |
                        Q(product_name__icontains=tag) |
                        Q(product_name_sap__icontains=tag) |
                        Q(product_id__icontains=tag) |
                        Q(base_product__seller_sku__icontains=tag)
                    )
                
                search_list_product_objs = search_list_product_lookup.distinct()
            
            search_list_base_product_objs = search_list_product_objs.values_list('base_product',flat=True).order_by('-pk')

            search_list_base_product_objs = list(dict.fromkeys(search_list_base_product_objs))
            products = []

            paginator = Paginator(search_list_base_product_objs, 20)
            base_product_objs = paginator.page(page)

            for base_product_pk in base_product_objs:
                base_product_obj = BaseProduct.objects.get(pk=base_product_pk)
                temp_dict = {}
                temp_dict["base_product_pk"] = base_product_pk
                temp_dict["product_name"] = base_product_obj.base_product_name
                temp_dict["manufacturer"] = base_product_obj.manufacturer
                temp_dict["manufacturer_part_number"] = base_product_obj.manufacturer_part_number
                temp_dict["base_main_images"] = []

                if base_product_obj.brand != None:
                    temp_dict["brand_name"] = base_product_obj.brand.name
                else:
                    temp_dict["brand_name"] = "-"
                
                temp_dict["created_date"] = str(
                    base_product_obj.created_date.strftime("%d %b, %Y"))

                temp_dict["products"] = []
                temp_dict["channel_products"] = []
                temp_dict["dimensions"] = {}

                temp_dict["seller_sku"] = base_product_obj.seller_sku
                temp_dict["category"] = "" if base_product_obj.category==None else str(base_product_obj.category)
                temp_dict["sub_category"] = "" if base_product_obj.sub_category==None else str(base_product_obj.sub_category)
                temp_dict["dimensions"] = json.dumps(base_product_obj.dimensions)
                
                product_objs = search_list_product_objs.filter(base_product = base_product_obj)

                for product_obj in product_objs:
                    
                    temp_dict2 = {}
                    temp_dict2["product_pk"] = product_obj.pk
                    temp_dict2["product_id"] = product_obj.product_id
                    temp_dict2["product_name"] = product_obj.product_name
                    temp_dict2["brand_name"] = str(product_obj.base_product.brand)
                    temp_dict2["sub_category"] = "" if base_product_obj.sub_category==None else str(base_product_obj.sub_category)
                    temp_dict2["category"] = "" if base_product_obj.category==None else str(base_product_obj.category)
                    temp_dict2["product_price"] = product_obj.standard_price
                    if temp_dict2["product_price"]==None:
                        temp_dict2["product_price"] = "-"
                    temp_dict2["status"] = product_obj.status
                    
                    temp_dict2["main_images"] = []
                    temp_dict["base_main_images"] = []

                    if without_images == 0:

                        main_images_list = ImageBucket.objects.none()
                        main_images_objs = MainImages.objects.filter(product=product_obj)
                        for main_images_obj in main_images_objs:
                            main_images_list |= main_images_obj.main_images.all()

                        main_images_list = main_images_list.distinct()

                        try:
                            main_images = create_response_images_main(main_images_list)
                            temp_dict2["main_images"] = main_images
                            for main_image in main_images:
                                temp_dict["base_main_images"].append(main_image)
                        except Exception as e:
                            pass
                        # elif without_images==0:
                        #     main_images = create_response_images_main(main_images_list)
                        #     temp_dict2["main_images"].append(main_images[0])
                        #     temp_dict["base_main_images"].append(main_images[0])

                    channels_of_prod =0
                    active_channels = 0

                    if product_obj.channel_product.is_noon_product_created == True:
                        
                        channels_of_prod +=1
                        noon_product = json.loads(product_obj.channel_product.noon_product_json)
                        if noon_product["status"] == "Active":
                            active_channels +=1

                    if product_obj.channel_product.is_amazon_uk_product_created == True:
                        
                        channels_of_prod +=1
                        amazon_uk_product = json.loads(product_obj.channel_product.amazon_uk_product_json)
                        if amazon_uk_product["status"] == "Active":
                            active_channels +=1

                    if product_obj.channel_product.is_amazon_uae_product_created == True:
                        
                        channels_of_prod +=1
                        amazon_uae_product = json.loads(product_obj.channel_product.amazon_uae_product_json)
                        if amazon_uae_product["status"] == "Active":
                            active_channels +=1

                    if product_obj.channel_product.is_ebay_product_created == True:
                        
                        channels_of_prod +=1
                        ebay_product = json.loads(product_obj.channel_product.ebay_product_json)
                        if ebay_product["status"] == "Active":
                            active_channels +=1

                    temp_dict2["channels_of_prod"] = channels_of_prod
                    temp_dict2["active_channels"] = active_channels
                    temp_dict2["inactive_channels"] = channels_of_prod - active_channels
                    temp_dict["products"].append(temp_dict2)

                products.append(temp_dict)

            price_type = custom_permission_price(request.user, "price_type")

            is_available = True
            
            if paginator.num_pages == page:
                is_available = False

            response["is_available"] = is_available
            response["total_products"] = len(search_list_base_product_objs)
            response["products"] = products
            response["price_type"] = price_type

            response['status'] = 200
            print("Finished API")

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdatedFetchProductListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
            print(e)

        return Response(data=response)


UpdatedFetchProductList = UpdatedFetchProductListAPI.as_view()


class FetchStatisticsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data

            page = int(data["page"])
           
            permissible_brands = custom_permission_filter_brands(request.user)
            permissible_brands = permissible_brands.annotate(num_products=Count('baseproduct')).order_by('-num_products')

            paginator = Paginator(permissible_brands, 20)
            brand_objs = paginator.page(page)

            brand_list = []
            for brand_obj in brand_objs:

                product_objs_list = Product.objects.filter(base_product__brand=brand_obj)
                baseproduct_objs_list = BaseProduct.objects.filter(brand=brand_obj)
                total_products = product_objs_list.count()
                total_baseproducts = baseproduct_objs_list.count()

                attribute_list = []
                result_dict = {}


                yes = product_objs_list.exclude(product_description=None).exclude(product_description="").count()
                no = total_products - yes
                key = "Product Description"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.exclude(product_id=None).exclude(product_id="").count()
                no = total_products - yes
                key = "Product ID"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.filter(verified=True).count()
                no = total_products - yes
                key = "Product Verified"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.filter(channel_product__is_amazon_uae_product_created=True).count()
                no = total_products - yes
                key = "Amazon UAE Product"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.filter(channel_product__is_amazon_uk_product_created=True).count()
                no = total_products - yes
                key = "Amazon UK Product"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.filter(channel_product__is_noon_product_created=True).count()
                no = total_products - yes
                key = "Noon Product"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.filter(channel_product__is_ebay_product_created=True).count()
                no = total_products - yes
                key = "Ebay Product"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = MainImages.objects.annotate(num_main_images=Count('main_images')).filter(product__in=product_objs_list,is_sourced=True,num_main_images__gt=0).count()
                no = total_products - yes
                key = "Main Images"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = SubImages.objects.annotate(num_sub_images=Count('sub_images')).filter(product__in=product_objs_list,is_sourced=True,num_sub_images__gt=0).count()
                no = total_products - yes
                key = "Sub Images > 0"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.exclude(pfl_product_features="[]").exclude(pfl_product_features="").count()
                no = total_products - yes
                key = "Product Features"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.annotate(num_white_background_images=Count('white_background_images')).filter(num_white_background_images__gt=0).count()
                no = total_products - yes
                key = "White Backgound Images > 0"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": product_id_yes,
                    "no": product_id_no
                }

                yes = product_objs_list.annotate(num_lifestyle_images=Count('lifestyle_images')).filter(num_lifestyle_images__gt=0).count()                   
                no = total_products - yes
                key = "Lifestyle Images > 0"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.annotate(num_giftbox_images=Count('giftbox_images')).filter(num_giftbox_images__gt=0).count()
                no = total_products - yes
                key = "Giftbox Images > 0"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.annotate(num_transparent_images=Count('transparent_images')).filter(num_transparent_images__gt=0).count()                   
                no = total_products - yes
                key = "Transparent Images > 0"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }


                # product_dimension_yes = 0

                # for baseproduct_obj in baseproduct_objs_list:
                #     dimensions_json = json.loads(baseproduct_obj.dimensions)
                #     if(dimensions_json["product_dimension_l"]!="" and dimensions_json["product_dimension_b"]!="" and dimensions_json["product_dimension_h"]!=""):
                #         product_dimension_yes += 1
                #     else:
                #         product_dimension_no += 1
                #     if(dimensions_json["giftbox_l"]!="" and dimensions_json["giftbox_b"]!="" and dimensions_json["giftbox_h"]!=""):
                #         giftbox_dimension_yes += 1
                #     else:
                #         giftbox_dimension_no += 1 


                yes = product_objs_list.exclude(product_name=None).exclude(product_name="").count()
                no = total_products - yes
                key = "Product Name"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = SubImages.objects.annotate(num_sub_images=Count('sub_images')).filter(product__in=product_objs_list,is_sourced=True,num_sub_images=1).count()
                no = total_products - yes
                key = "SubImages 1"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = SubImages.objects.annotate(num_sub_images=Count('sub_images')).filter(product__in=product_objs_list,is_sourced=True,num_sub_images=2).count()
                no = total_products - yes
                key = "SubImages 2"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = SubImages.objects.annotate(num_sub_images=Count('sub_images')).filter(product__in=product_objs_list,is_sourced=True,num_sub_images=3).count()
                no = total_products - yes
                key = "SubImages 3"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.annotate(num_white_background_images=Count('white_background_images')).filter(num_white_background_images=1).count()
                no = total_products - yes
                key = "White Background Images 1"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.annotate(num_white_background_images=Count('white_background_images')).filter(num_white_background_images=2).count()
                no = total_products - yes
                key = "White Background Images 2"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.annotate(num_white_background_images=Count('white_background_images')).filter(num_white_background_images=3).count()
                no = total_products - yes
                key = "White Background Images 3"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.annotate(num_lifestyle_images=Count('lifestyle_images')).filter(num_lifestyle_images=1).count()
                no = total_products - yes
                key = "Lifestyle Images 1"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.annotate(num_lifestyle_images=Count('lifestyle_images')).filter(num_lifestyle_images=2).count()
                no = total_products - yes
                key = "Lifestyle Images 2"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                yes = product_objs_list.annotate(num_lifestyle_images=Count('lifestyle_images')).filter(num_lifestyle_images=3).count()
                no = total_products - yes
                key = "Lifestyle Images 3"
                attribute_list.append(key)
                result_dict[key] = {
                    "yes": yes,
                    "no": no
                }

                temp_dict = {}
                temp_dict["brand_name"] = brand_obj.name
                temp_dict["keys"] = attribute_list
                temp_dict["values"] = result_dict
                brand_list.append(temp_dict)

            response["brand_list"] = brand_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchStasticsAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data=response)

FetchStatistics = FetchStatisticsAPI.as_view()