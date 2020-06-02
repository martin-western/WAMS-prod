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

            data = request.data
            logger.info("FetchReportListAPI: %s", str(data))

            chip_data = json.loads(data.get('tags', '[]'))

            search_list_objs = []
            report_objs = []

            if data.get("start_date", "") != "" and data.get("end_date", "") != "":
                start_date = datetime.datetime.strptime(data["start_date"], "%b %d, %Y")
                end_date = datetime.datetime.strptime(data["end_date"], "%b %d, %Y")
                report_objs = Report.objects.filter(
                    created_date__gte=start_date).filter(created_date__lte=end_date).filter(user=request.user).order_by('-pk')
            else:
                report_objs = Report.objects.all().filter(user=request.user).order_by('-pk')

            if data.get("channel_name", "") != "" :
                channel_obj = Channel.objects.get(name=data["channel_name"])
                report_objs = Report.objects.filter(channel=channel_obj)
            
            if data.get("operation_type", "") != "" :
                report_objs = Report.objects.filter(operation_type=data["operation_type"])

            if data.get("status", "") != "" :
                report_objs = Report.objects.filter(status=data["status"])

            if data.get("is_read", "") != "" :
                if(data["is_read"]=="true"):
                    report_objs = Report.objects.filter(is_read=True)
                else:
                    report_objs = Report.objects.filter(is_read=False)

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

            report_list = []
            for report_obj in search_list_objs:
                temp_dict = {}
                temp_dict["pk"] = report_obj.pk
                temp_dict["feed_submission_id"] = report_obj.feed_submission_id
                temp_dict["operation_type"] = report_obj.operation_type
                temp_dict["status"] = report_obj.status
                temp_dict["is_read"] = report_obj.is_read
                temp_dict["created_date"] = str(report_obj.created_date.strftime("%d %b, %Y"))
                temp_dict["product_count"] = report_obj.products.all().count()
                temp_dict["user"] = str(report_obj.user.username)
                report_list.append(temp_dict)

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
            
            try :
                response_feed_submission_result = feeds_api.get_feed_submission_result(feed_submission_id)

                feed_submission_result = response_feed_submission_result.parsed

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

                            response["errors"].append(temp_dict)

                    else:
                        temp_dict = {}
                        temp_dict["product_pk"] = result["MessageID"]["value"]
                        temp_dict["error_type"] = result["ResultCode"]["value"]
                        temp_dict["error_code"] = result["ResultMessageCode"]["value"]
                        temp_dict["error_message"] = result["ResultDescription"]["value"]

                        temp_dict["product_name"] = Product.objects.get(pk=int(temp_dict["product_pk"])).product_name
                        
                        response["errors"].append(temp_dict)

                    response["result_status"] = "Done"
                    
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.info("GetPushProductsResultAmazonUAEAPI: %s at %s",
                             e, str(exc_tb.tb_lineno))
                    response["result_status"] = "Done"

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.info("GetPushProductsResultAmazonUAEAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
                response["result_status"] = "In Progress"

            response["report_pk"] = report_obj.pk
            response["feed_submission_id"] = report_obj.feed_submission_id
            response["operation_type"] = report_obj.operation_type
            response["status"] = report_obj.status
            response["is_read"] = report_obj.is_read
            response["created_date"] = str(report_obj.created_date.strftime("%d %b, %Y"))
            response["product_count"] = report_obj.products.all().count()
            response["user"] = str(report_obj.user.username)
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchExportProductListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


FetchReportList = FetchReportListAPI.as_view()

FetchReportDetails = FetchReportDetailsAPI.as_view()