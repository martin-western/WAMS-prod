from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

from WAMSApp.models import *
from WAMSApp.utils import *
from WAMSApp.sourcing.utils_sourcing import *

from django.shortcuts import render, HttpResponse, get_object_or_404
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models import Count
from django.db.models import Sum
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone


import requests
import json
import os
import pytz
import csv
import uuid
import logging
import sys
import xlrd
import zipfile
import inflect
import boto3
import urllib.request, urllib.error, urllib.parse

from datetime import datetime
from django.utils import timezone
from django.core.files import File

logger = logging.getLogger(__name__)


class CreateFactoryProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("CreateFactoryProductAPI: %s", str(data))

            print(data)

            if not isinstance(data, dict):
                data = json.loads(data)

            factory_obj = Factory.objects.none() 

            try:
                factory_user = FactoryUser.objects.get(username=request.user.username)
                factory_obj = factory_user.factory
            except:
                response["status"] = 403
                logger.warning("CreateFactoryProductAPI: Not a Factory User")
                return Response(data=response)

            brand_name = data['brand_name']
            category_uuid = data['category_uuid']
            sub_category_uuid = data['sub_category_uuid']
            material_type_name = data["material_type"]

            brand_obj = None
            try:
                brand_obj = Brand.objects.get(name=brand_name)
            except Exception as e:
                logger.warning("CreateFactoryProductAPI: Brand does not exist")

            category_obj = None
            try:
                category_obj = Category.objects.get(uuid=category_uuid)
            except Exception as e:
                logger.warning("CreateFactoryProductAPI: Category does not exist")

            sub_category_obj = None
            try:
                sub_category_obj = SubCategory.objects.get(uuid=sub_category_uuid)
            except Exception as e:
                logger.warning("CreateFactoryProductAPI: SubCategory does not exist")


            material_type_obj = None
            try:
                material_type_obj, created = MaterialType.objects.get_or_create(name=material_type_name)
            except Exception as e:
                logger.warning("CreateFactoryProductAPI: MaterialType does not exist")

            product_name = data["product_name"]
            product_description = data["product_description"]
            manufacturer_part_number = data["manufacturer_part_number"]
            manufacturer = data["manufacturer"]
            color_map = data["color_map"]
            color = data["color"]
            moq = data["moq"]
            factory_notes = data["factory_notes"]
            features = json.dumps(data["features"])
            dimensions = json.dumps(data["dimensions"])

            factory_product_obj = FactoryProduct.objects.create(
                product_name=product_name,
                product_description=product_description,
                factory=factory_obj,
                manufacturer_part_number=manufacturer_part_number,
                brand=brand_obj,
                manufacturer=manufacturer,
                category=category_obj,
                sub_category=sub_category_obj,
                color_map=color_map,
                color=color,
                material_type=material_type_obj,
                moq=moq,
                factory_notes=factory_notes,
                features=features,
                dimensions=dimensions
            )

            # images_count = int(data["images_count"])

            # for i in range(images_count):
            #     image_obj = Image.objects.create(image=data["image_"+str(i)])
            #     factory_product_obj.images.add(image_obj)

            factory_product_obj.save()

            response["uuid"] = factory_product_obj.uuid
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateFactoryProductAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchFactoryProductListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchFactoryProductListAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            factory_obj = None
            if OmnyCommUser.objects.filter(username=request.user.username).exists():

                page_list = get_custom_permission_page_list(request.user)

                if("Factory" not in page_list):
                    response["status"] = 403
                    logger.warning("FetchFactoryProductListAPI: Restricted Access!")
                    Response(data=response)

                factory_uuid = data.get("factory_uuid", None)
                if factory_uuid!=None:
                    factory_obj = Factory.objects.get(uuid=factory_uuid)
            elif FactoryUser.objects.filter(username=request.user.username).exists():
                factory_obj = FactoryUser.objects.get(username=request.user.username).factory
            else:
                response["status"] = 403
                logger.error("FetchFactoryProductListAPI Restricted Access")
                return Response(data=response)

            factory_product_objs = FactoryProduct.objects.all()

            if factory_obj!=None:
                factory_product_objs = factory_product_objs.filter(factory=factory_obj)

            filter_parameters = data.get("filter_parameters",{})
            filter_brand = filter_parameters.get("brand",None)

            if(filter_brand!=None):
                factory_product_objs = factory_product_objs.filter(brand__name=filter_brand)

            chip_data = data.get("tags", [])

            if len(chip_data) != 0:
                search_list_product_lookup = FactoryProduct.objects.none()
                for tag in chip_data:
                    search_list_product_lookup |= factory_product_objs.filter(
                        Q(manufacturer_part_number__icontains=tag) |
                        Q(product_name__icontains=tag)
                    )
                factory_product_objs = search_list_product_lookup.distinct()

            page = int(data.get('page', 1))
            paginator = Paginator(factory_product_objs, 20)
            total_products = factory_product_objs.count()
            factory_product_objs = paginator.page(page)

            factory_product_list = []
            for factory_product_obj in factory_product_objs:
                temp_dict = {}
                temp_dict["product_name"] = factory_product_obj.product_name
                temp_dict["manufacturer_part_number"] = factory_product_obj.manufacturer_part_number
                temp_dict["moq"] = factory_product_obj.moq

                if factory_product_obj.category!=None:
                    temp_dict["category"] = str(factory_product_obj.category)
                else:
                    temp_dict["category"] = ""
                
                if factory_product_obj.sub_category!=None:
                    temp_dict["sub_category"] = str(factory_product_obj.sub_category)
                else:
                    temp_dict["sub_category"] = ""

                if factory_product_obj.brand==None:
                    temp_dict["brand"] = ""
                else:
                    temp_dict["brand"] = str(factory_product_obj.brand)
                temp_dict["uuid"] = str(factory_product_obj.uuid)
                try:
                    temp_dict["image"] = factory_product_obj.images.all()[0].mid_image.url
                except:
                    temp_dict["image"] = Config.objects.all()[0].product_404_image.image.url

                factory_product_list.append(temp_dict)

            is_available = True
            
            if paginator.num_pages == page:
                is_available = False

            if factory_obj!=None:
                response["factory_name"] = factory_obj.name
            else:
                response["factory_name"] = "ALL"

            response["is_available"] = is_available
            response["total_products"] = total_products

            response["factory_product_list"]  = factory_product_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFactoryProductListAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchFactoryProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchFactoryProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            factory_product_uuid = data["factory_product_uuid"]

            factory_product_obj = FactoryProduct.objects.none()
            try:
                factory_product_obj = FactoryProduct.objects.get(uuid=factory_product_uuid)
            except Exception as e:
                response["status"] = 404
                logger.error("FetchFactoryProductAPI Factory Product does not exist")
                return Response(data=response)

            response["product_name"] = factory_product_obj.product_name
            response["manufacturer_part_number"] = factory_product_obj.manufacturer_part_number
            response["product_description"] = factory_product_obj.product_description
            response["factory"] = factory_product_obj.factory.name
            if factory_product_obj.brand==None:
                response["brand"] = ""
            else:
                response["brand"] = str(factory_product_obj.brand)

            response["manufacturer"] = factory_product_obj.manufacturer
            if factory_product_obj.category==None:
                response["category"] = ""
                response["category_uuid"] = ""
            else:
                response["category"] = str(factory_product_obj.category)
                response["category_uuid"] = str(factory_product_obj.category.uuid)

            if factory_product_obj.category==None:
                response["sub_category"] = ""
                response["sub_category_uuid"] = ""
            else:
                response["sub_category"] = str(factory_product_obj.sub_category)
                response["sub_category_uuid"] = str(factory_product_obj.sub_category.uuid)

            response["color_map"] = factory_product_obj.color_map
            response["color"] = factory_product_obj.color

            if factory_product_obj.material_type==None:
                response["material_type"] = ""
            else:
                response["material_type"] = str(factory_product_obj.material_type)

            response["moq"] = str(factory_product_obj.moq)
            response["factory_notes"] = factory_product_obj.factory_notes
            response["dimensions"] = json.loads(factory_product_obj.dimensions)
            response["features"] = json.loads(factory_product_obj.features)

            images = []
            image_objs = factory_product_obj.images.all()
            for image_obj in image_objs:
                try:
                    temp_dict = {
                        "url": image_obj.mid_image.url,
                        "pk": image_obj.pk
                    }
                    images.append(temp_dict)
                except:
                    pass

            response["images"] = images
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFactoryProductAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchFactoryListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchFactoryListAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            page_list = get_custom_permission_page_list(request.user)

            if("Factory" not in page_list):
                response["status"] = 403
                logger.warning("FetchFactoryListAPI: Restricted Access!")
                Response(data=response)


            factory_objs = Factory.objects.all()

            chip_data = data.get('tags', [])
            if len(chip_data)>0:
                factory_objs = Factory.objects.none()
                for chip in chip_data:
                    factory_objs |= Factory.objects.filter(Q(name__icontains=chip) | Q(code__icontains=chip))
                factory_objs = factory_objs.distinct()

            factory_list = []

            for factory_obj in factory_objs:

                temp_dict = {}
                temp_dict["name"] = factory_obj.name
                temp_dict["code"] = factory_obj.code
                temp_dict["address"] = factory_obj.address
                temp_dict["uuid"] = factory_obj.uuid
                try:
                    temp_dict["image"] = factory_obj.image.mid_image.url
                except:
                    temp_dict["image"] = Config.objects.all()[0].product_404_image.image.url

                factory_list.append(temp_dict)

            response["factory_list"] = factory_list
            response["status"] = 200 

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFactoryListAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadFactoryProductImagesAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UploadFactoryProductImagesAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if request.user.has_perm('WAMSApp.add_image') == False:
                logger.warning("UploadFactoryProductImagesAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            factory_product_uuid = data["factory_product_uuid"]

            factory_product_obj = FactoryProduct.objects.none()
            try:
                factory_product_obj = FactoryProduct.objects.get(uuid=factory_product_uuid)
            except Exception as e:
                response["status"] = 404
                logger.error("UploadFactoryProductImagesAPI: Factory Product does not exist")
                return Response(data=response)

            user = FactoryUser.objects.get(username=request.user.username)
            if(factory_product_obj.factory != user.factory):
                response["status"] = 403
                logger.warning("UploadFactoryProductImagesAPI: Restricted Access!")
                return Response(data=response)

            images_count = int(data["images_count"])

            for i in range(images_count):
                image_obj = Image.objects.create(image=data["image_"+str(i)])
                factory_product_obj.images.add(image_obj)

            factory_product_obj.save()
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadFactoryProductImagesAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DeleteFactoryProductImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("DeleteFactoryProductImageAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if request.user.has_perm('WAMSApp.delete_image') == False:
                logger.warning("DeleteFactoryProductImageAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            factory_product_uuid = data["factory_product_uuid"]
            image_pk = int(data["image_pk"])

            factory_product_obj = FactoryProduct.objects.get(uuid=factory_product_uuid)
            if factory_product_obj.images.filter(pk=image_pk).exists():
                Image.objects.get(pk=image_pk).delete()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteFactoryProductImageAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveFactoryProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SaveFactoryProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            brand_name = data['brand_name']
            category_uuid = data['category_uuid']
            sub_category_uuid = data['sub_category_uuid']
            material_type_name = data["material_type"]

            factory_product_uuid = data["factory_product_uuid"]

            factory_product_obj = FactoryProduct.objects.none()
            try:
                factory_product_obj = FactoryProduct.objects.get(uuid=factory_product_uuid)
            except Exception as e:
                response["status"] = 404
                logger.error("SaveFactoryProductAPI: Factory Product does not exist")
                return Response(data=response)

            factory_obj = FactoryUser.objects.get(username=request.user.username).factory

            brand_obj = None
            try:
                brand_obj = Brand.objects.get(name=brand_name)
            except Exception as e:
                logger.error("SaveFactoryProductAPI: Brand does not exist")

            category_obj = None
            try:
                category_obj = Category.objects.get(uuid=category_uuid)
            except Exception as e:
                logger.error("SaveFactoryProductAPI: Category does not exist")

            sub_category_obj = None
            try:
                sub_category_obj = SubCategory.objects.get(uuid=sub_category_uuid)
            except Exception as e:
                logger.error("SaveFactoryProductAPI: SubCategory does not exist")

            material_type_obj = None
            try:
                material_type_obj, created = MaterialType.objects.get_or_create(name=material_type_name)
            except Exception as e:
                logger.error("SaveFactoryProductAPI: MaterialType does not exists")

            product_name = data["product_name"]
            product_description = data["product_description"]
            manufacturer_part_number = data["manufacturer_part_number"]
            manufacturer = data["manufacturer"]
            color_map = data["color_map"]
            color = data["color"]
            moq = data["moq"]
            factory_notes = data["factory_notes"]
            features = json.dumps(data["features"])
            dimensions = json.dumps(data["dimensions"])

            factory_product_obj.product_name=product_name
            factory_product_obj.product_description=product_description
            factory_product_obj.factory=factory_obj
            factory_product_obj.manufacturer_part_number=manufacturer_part_number
            factory_product_obj.brand=brand_obj
            factory_product_obj.manufacturer=manufacturer
            factory_product_obj.category=category_obj
            factory_product_obj.sub_category=sub_category_obj
            factory_product_obj.color_map=color_map
            factory_product_obj.color=color
            factory_product_obj.material_type=material_type_obj
            factory_product_obj.moq=moq
            factory_product_obj.factory_notes=factory_notes
            factory_product_obj.features=features
            factory_product_obj.dimensions=dimensions
                
            factory_product_obj.save()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveFactoryProductAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CheckFactoryUserAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("CheckFactoryUserAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            factory_user = FactoryUser.objects.filter(username=request.user.username)

            response["factory_user"] = factory_user.exists()
            if(factory_user.exists()==True):
                response["factory_uuid"] = factory_user[0].factory.uuid

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CheckFactoryUserAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

FetchFactoryProduct = FetchFactoryProductAPI.as_view()

CreateFactoryProduct = CreateFactoryProductAPI.as_view()

SaveFactoryProduct = SaveFactoryProductAPI.as_view()

UploadFactoryProductImages = UploadFactoryProductImagesAPI.as_view()

DeleteFactoryProductImage = DeleteFactoryProductImageAPI.as_view()

FetchFactoryList = FetchFactoryListAPI.as_view()

CheckFactoryUser = CheckFactoryUserAPI.as_view()

FetchFactoryProductList = FetchFactoryProductListAPI.as_view()