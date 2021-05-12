from WAMSApp.models import *
from WAMSApp.utils import *

from MWS import mws,APIs

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Count
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

import requests
import json
import pytz
import csv
import logging
import sys
import xlrd
import time


from datetime import datetime
from django.utils import timezone
from django.core.files import File

logger = logging.getLogger(__name__)

MWS_PARAMS = settings.MWS_PARAMS

MWS_ACCESS_KEY = MWS_PARAMS["MWS_ACCESS_KEY"] 
MWS_SECRET_KEY = MWS_PARAMS["MWS_SECRET_KEY"]
SELLER_ID = MWS_PARAMS["SELLER_ID"]

class FetchReportListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            if custom_permission_mws_functions(request.user,"get_reports_from_amazon") == False:
                logger.warning("FetchReportListAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("FetchReportListAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            chip_data = data.get('tags', '[]')
            filter_parameters = data["filter_parameters"]

            search_list_objs = []
            report_objs = []

            if filter_parameters.get("start_date", "") != "" and filter_parameters.get("end_date", "") != "":
                start_date = filter_parameters["start_date"]
                end_date = filter_parameters["end_date"]
                report_objs = Report.objects.filter(
                    created_date__gte=start_date).filter(created_date__lte=end_date).filter(user=request.user).order_by('-pk')
            else:
                report_objs = Report.objects.all().filter(user=request.user).order_by('-pk')

            if filter_parameters.get("channel_name", "") != "" :
                channel_obj = Channel.objects.get(name=filter_parameters["channel_name"])
                report_objs = report_objs.filter(channel=channel_obj)
            
            if filter_parameters.get("operation_type", "") != "" :
                report_objs = report_objs.filter(operation_type=filter_parameters["operation_type"])

            if filter_parameters.get("status", "") != "" :
                report_objs = report_objs.filter(status=filter_parameters["status"])

            if filter_parameters.get("is_read", "") != "" :
                if(filter_parameters["is_read"]==True):
                    report_objs = report_objs.filter(is_read=True)
                else:
                    report_objs = report_objs.filter(is_read=False)

            if len(chip_data) == 0:
                search_list_objs = report_objs
            else:
                for report_obj in report_objs:
                    flag=0

                    for chip in chip_data:
                        if chip.lower() in report_obj.feed_submission_id.lower():
                            search_list_objs.append(report_obj)
                            flag = 1
                            break
                            
                    if flag == 1:
                        break

            page = int(data['page'])
            paginator = Paginator(search_list_objs, 9)
            search_list_report_objs = paginator.page(page)

            report_list = []
            for report_obj in search_list_report_objs:
                temp_dict = {}
                temp_dict["pk"] = report_obj.pk
                temp_dict["feed_submission_id"] = report_obj.feed_submission_id
                temp_dict["operation_type"] = report_obj.operation_type
                temp_dict["report_status"] = report_obj.status
                temp_dict["is_read"] = report_obj.is_read
                temp_dict["created_date"] = str(report_obj.created_date.strftime("%d %b, %Y : %H %M %p"))
                temp_dict["product_count"] = report_obj.products.all().count()
                temp_dict["user"] = str(report_obj.user.username)
                report_list.append(temp_dict)

            is_available = True
            
            if paginator.num_pages == page:
                is_available = False

            response["is_available"] = is_available
            response["report_list"] = report_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchReportListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchReportDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchReportDetailsAPI: %s", str(data))

            report_obj = Report.objects.get(pk=int(data["report_pk"]))

            feed_submission_id = report_obj.feed_submission_id

            if(report_obj.channel.name=="Amazon UAE"):
                region="AE"
            else:
                region="UK"

            products = report_obj.products.all()

            feeds_api = APIs.Feeds(MWS_ACCESS_KEY,MWS_SECRET_KEY,SELLER_ID, 
                                        region=region)

            response["errors"] = []
            response["success"] = []

            product_pk_hash_list = {}
            
            try :
                response_feed_submission_result = feeds_api.get_feed_submission_result(feed_submission_id)

                feed_submission_result = response_feed_submission_result.parsed
                report_obj.is_read = True
                report_obj.status = "Done"
                report_obj.save()

                try :
                    result = feed_submission_result["ProcessingReport"]["Result"]

                    if isinstance(result,list):

                        for i in range(len(result)):
                            temp_dict = {}
                            temp_dict["product_pk"] = result[i]["MessageID"]["value"]
                            temp_dict["error_type"] = result[i]["ResultCode"]["value"]
                            temp_dict["error_code"] = result[i]["ResultMessageCode"]["value"]
                            temp_dict["error_message"] = result[i]["ResultDescription"]["value"]

                            temp_dict["product_name"] = Product.objects.get(pk=int(temp_dict["product_pk"])).product_name

                            product_pk_hash_list[temp_dict["product_pk"]] = "1"
                            response["errors"].append(temp_dict)

                    else:
                        temp_dict = {}
                        temp_dict["product_pk"] = result["MessageID"]["value"]
                        temp_dict["error_type"] = result["ResultCode"]["value"]
                        temp_dict["error_code"] = result["ResultMessageCode"]["value"]
                        temp_dict["error_message"] = result["ResultDescription"]["value"]

                        temp_dict["product_name"] = Product.objects.get(pk=int(temp_dict["product_pk"])).product_name
                        
                        product_pk_hash_list[temp_dict["product_pk"]] = "1"
                        response["errors"].append(temp_dict)

                    
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.info("GetPushProductsResultAmazonUAEAPI: %s at %s",
                             e, str(exc_tb.tb_lineno))

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.info("GetPushProductsResultAmazonUAEAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

            for product_obj in products:

                if product_obj.pk not in product_pk_hash_list.keys():

                    temp_dict = {}
                    temp_dict["product_pk"] = product_obj.pk
                    temp_dict["product_name"] = product_obj.product_name

                    if report_obj.operation_type == "Price":
                        channel_product = product_obj.channel_product
                        amazon_uae_product = json.loads(channel_product.amazon_uae_product_json)
                        temp_dict["now_price"] = amazon_uae_product["now_price"]
                        temp_dict["was_price"] = amazon_uae_product["was_price"]

                    if report_obj.operation_type == "Inventory":
                        channel_product = product_obj.channel_product
                        amazon_uae_product = json.loads(channel_product.amazon_uae_product_json)
                        temp_dict["stock"] = amazon_uae_product["stock"]
                    
                    response["success"].append(temp_dict)

            response["report_pk"] = report_obj.pk
            response["feed_submission_id"] = report_obj.feed_submission_id
            response["operation_type"] = report_obj.operation_type
            response["report_status"] = report_obj.status
            response["is_read"] = report_obj.is_read
            response["created_date"] = str(timezone.localtime(report_obj.created_date).strftime("%d %b, %Y"))
            response["product_count"] = report_obj.products.all().count()
            response["user"] = str(report_obj.user.username)
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchExportProductListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class RefreshReportStatusAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("RefreshReportStatusAPI: %s", str(data))

            report_obj = Report.objects.get(pk=int(data["report_pk"]))

            feed_submission_id = report_obj.feed_submission_id

            if(report_obj.channel.name=="Amazon UAE"):
                region="AE"
            else:
                region="UK"

            products = report_obj.products.all()

            feeds_api = APIs.Feeds(MWS_ACCESS_KEY,MWS_SECRET_KEY,SELLER_ID, 
                                        region=region)
            
            try :

                response_feed_submission_result = feeds_api.get_feed_submission_result(feed_submission_id)

                feed_submission_result = response_feed_submission_result.parsed
                report_obj.status = "Done"
                report_obj.save()

                
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.info("RefreshReportStatusAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

            response["report_status"] = report_obj.status
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("RefreshReportStatusAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


FetchReportList = FetchReportListAPI.as_view()

FetchReportDetails = FetchReportDetailsAPI.as_view()

RefreshReportStatus = RefreshReportStatusAPI.as_view()