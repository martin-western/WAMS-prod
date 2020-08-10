from WAMSApp.models import *
from WAMSApp.utils import *

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

class MakePaymentNetworkGlobalAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response["status"] = 500
        
        try:
            
            data = request.data
            logger.info("MakePaymentNetworkGlobalAPI: %s", str(data))

            try :
                session_id = data["session_id"]
            except Exception as e:
                response["status"] = 404
                logger.warning("MakePaymentNetworkGlobalAPI session id not passed!")
                return Response(data=response)

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("MakePaymentNetworkGlobalAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

MakePaymentNetworkGlobal = MakePaymentNetworkGlobalAPI.as_view()