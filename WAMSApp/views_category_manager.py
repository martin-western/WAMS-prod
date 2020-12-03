from WAMSApp.models import *

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from django.core.paginator import Paginator

import requests
import json
import pytz
import logging
import sys
import xlrd
import re

logger = logging.getLogger(__name__)


class FetchCategoryListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("FetchCategoryListAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            super_categories = SapSuperCategory.objects.all()
            super_category_list = []

            for super_category in super_categories:
                
                temp_dict = {}
                temp_dict['pk'] = super_category.pk
                temp_dict['name'] = super_category.super_category
                categories = SapCategory.objects.filter(super_category=super_category)
                
                category_list = []
                for category in categories:
                    temp_dict_category = {}
                    temp_dict_category['pk'] = category.pk
                    temp_dict_category['name'] = category.category
                    sub_categories = SapSubCategory.objects.filter(category=category)
                    
                    sub_category_list = []
                    for sub_category in sub_categories:
                        temp_dict_sub_category = {}
                        temp_dict_sub_category['pk'] = sub_category.pk
                        temp_dict_sub_category['name'] = sub_category.sub_category
                        
                        category_mapping = CategoryMapping.objects.get(sap_sub_category=sub_category)
                        
                        temp_dict_category_mapping = {}
                        temp_dict_category_mapping['pk'] = category_mapping.pk
                        temp_dict_category_mapping['atp_thresold'] = category_mapping.atp_threshold
                        temp_dict_category_mapping['holding_thresold'] = category_mapping.holding_threshold
                        temp_dict_category_mapping['recommended_browse_node'] = category_mapping.recommended_browse_node
                        
                        temp_dict_sub_category['category_mapping'] = temp_dict_category_mapping
                        
                        sub_category_list.append(temp_dict_sub_category)
                    
                    temp_dict_category['sub_category'] = sub_category_list
                    category_list.append(temp_dict_category)
                
                temp_dict['category'] = category_list
                super_category_list.append(temp_dict)

            response['super_category_list'] = super_category_list

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCategoryListAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class UpdateCategoryMappingAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("UpdateCategoryListAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            pk = int(data.get("pk",0))

            if pk == 0:
                response['status'] = 404
                logger.error("UpdateCategoryMappingAPI PK of CategoryMapping not Passed")
                return Response(data=response)

            category_mapping_obj = CategoryMapping.objects.get(pk=pk)

            if "atp_thresold" in data:
                atp_thresold = float(data["atp_thresold"])
                category_mapping_obj.atp_threshold = atp_thresold
            if "holding_thresold" in data:
                holding_thresold = float(data["holding_thresold"])
                category_mapping_obj.holding_threshold = holding_thresold
            if "recommended_browse_node" in data:
                recommended_browse_node = str(data["recommended_browse_node"])
                category_mapping_obj.recommended_browse_node = recommended_browse_node

            category_mapping_obj.save()
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateCategoryMappingAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchSuperCategoriesAPI(APIView):

    def post(self, request, *args, **kwargs):
    
        response = {}
        response['status'] = 500

        try:

            data = request.data
            logger.info("FetchSuperCategoriesAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            super_category_objs = SuperCategory.objects.all().order_by('-pk')
            super_category_list = []

            for super_category_obj in super_category_objs:
                temp_dict = {}
                temp_dict["uuid"] = super_category_obj.uuid
                temp_dict["name"] = super_category_obj.name
                temp_dict["image"] = super_category_obj.image.image.url
                super_category_list.append(temp_dict)
            
            response["superCategoryList"] = super_category_list
            response['status'] = 200 

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSuperCategoriesAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchCategoriesAPI(APIView):
    
    def post(self, request, *args, **kwargs):
    
        response = {}
        response['status'] = 500

        try:

            data = request.data
            logger.info("FetchCategoriesAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            super_category_uuid = data["super_category_uuid"]

            category_objs = Category.objects.filter(super_category__uuid=super_category_uuid).order_by('-pk')
            category_list = []

            for category_obj in category_objs:
                temp_dict = {}
                temp_dict["uuid"] = category_obj.uuid
                temp_dict["name"] = category_obj.name
                temp_dict["image"] = category_obj.image.image.url
                category_list.append(temp_dict)
            
            response["CategoryList"] = category_list            
            response['status'] = 200 

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCategoriesAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchSubCategoriesAPI(APIView):
    
    def post(self, request, *args, **kwargs):
    
        response = {}
        response['status'] = 500

        try:

            data = request.data
            logger.info("FetchSubCategoriesAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            category_uuid = data["category_uuid"]

            sub_category_objs = SubCategory.objects.filter(category__uuid=category_uuid).order_by('-pk')
            sub_category_list = []

            for sub_category_obj in sub_category_objs:
                temp_dict = {}
                temp_dict["uuid"] = sub_category_obj.uuid
                temp_dict["name"] = sub_category_obj.name
                temp_dict["image"] = sub_category_obj.image.image.url
                sub_category_list.append(temp_dict)
            
            response["CategoryList"] = sub_category_list   
            response['status'] = 200 

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSubCategoriesAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

    

class UpdateSuperCategoryDetailsAPI(APIView):
    
    def post(self, request, *args, **kwargs):
    
        response = {}
        response['status'] = 500

        try:

            data = request.data
            logger.info("UpdateSuperCategoryDetailsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            super_category_uuid = data["super_category_uuid"]
            name = data.get("name","")
            image = data.get("image",None)

            super_category_obj = SuperCategory.objects.get(uuid=super_category_uuid)
            
            if name!="":
                super_category_obj.name = name
            
            if image!=None:
                image_obj = Image.objects.create(image=image)
                super_category_obj.image = image_obj

            super_category_obj.save()
            response['status'] = 200 

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateSuperCategoryDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UpdateCategoryDetailsAPI(APIView):
    
    def post(self, request, *args, **kwargs):
    
        response = {}
        response['status'] = 500

        try:

            data = request.data
            logger.info("UpdateCategoryDetailsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            category_uuid = data["category_uuid"]
            name = data.get("name","")
            image = data.get("image",None)

            category_obj = Category.objects.get(uuid=category_uuid)
            
            if name!="":
                category_obj.name = name
            
            if image!=None:
                image_obj = Image.objects.create(image=image)
                category_obj.image = image_obj

            category_obj.save()
            response['status'] = 200 

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateCategoryDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UpdateSubCategoryDetailsAPI(APIView):
    
    def post(self, request, *args, **kwargs):
    
        response = {}
        response['status'] = 500

        try:

            data = request.data
            logger.info("UpdateSubCategoryDetailsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            sub_category_uuid = data["sub_category_uuid"]
            name = data.get("name","")
            image = data.get("image",None)

            sub_category_obj = SubCategory.objects.get(uuid=sub_category_uuid)
            
            if name!="":
                sub_category_obj.name = name
            
            if image!=None:
                image_obj = Image.objects.create(image=image)
                sub_category_obj.image = image_obj

            sub_category_obj.save()        
            response['status'] = 200 

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateSubCategoryDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddNewSuperCategoryAPI(APIView):
    
    def post(self, request, *args, **kwargs):
    
        response = {}
        response['status'] = 500

        try:

            data = request.data
            logger.info("AddNewSuperCategoryAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            name = data["name"]
            image = data["image"]
            image_obj = Image.objects.create(image=image)

            SuperCategory.objects.create(name=name,
                                        image=image_obj)
            
            response['status'] = 200 

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddNewSuperCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddNewCategoryAPI(APIView):
    
    def post(self, request, *args, **kwargs):
    
        response = {}
        response['status'] = 500

        try:

            data = request.data
            logger.info("AddNewCategoryAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            name = data["name"]
            image = data["image"]
            image_obj = Image.objects.create(image=image)

            super_category_uuid = data["super_category_uuid"]
            super_category_obj = SuperCategory.objects.get(uuid=super_category_uuid)

            Category.objects.create(name=name,
                                    image=image_obj,
                                    super_category=super_category_obj)
            
            response['status'] = 200 

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddNewCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddNewSubCategoryAPI(APIView):
    
    def post(self, request, *args, **kwargs):
    
        response = {}
        response['status'] = 500

        try:

            data = request.data
            logger.info("AddNewSubCategoryAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            name = data["name"]
            image = data["image"]
            image_obj = Image.objects.create(image=image)

            category_uuid = data["category_uuid"]
            category_obj = Category.objects.get(uuid=category_uuid)

            SubCategory.objects.create(name=name,
                                    image=image_obj,
                                    category=category_obj)
            
            response['status'] = 200 

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddNewSubCategoryAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


FetchCategoryList = FetchCategoryListAPI.as_view()

UpdateCategoryMapping = UpdateCategoryMappingAPI.as_view()

FetchSuperCategories = FetchSuperCategoriesAPI.as_view()

FetchCategories = FetchCategoriesAPI.as_view()

FetchSubCategories = FetchSubCategoriesAPI.as_view()

UpdateSuperCategoryDetails = UpdateSuperCategoryDetailsAPI.as_view()

UpdateCategoryDetails = UpdateCategoryDetailsAPI.as_view()

UpdateSubCategoryDetails = UpdateSubCategoryDetailsAPI.as_view()

AddNewSuperCategory = AddNewSuperCategoryAPI.as_view()

AddNewCategory = AddNewCategoryAPI.as_view()

AddNewSubCategory = AddNewSubCategoryAPI.as_view()
