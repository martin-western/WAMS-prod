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

            pk = int(data.get("pk",0).strip())

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

UpdateCategoryMapping = UpdateCategoryMappingAPI.as_view()

FetchCategoryList = FetchCategoryListAPI.as_view()