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

class GithubWebhookAPI(APIView):

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data
            logger.info("GithubWebhookAPI: %s", str(data))

            ref = str(data["ref"])
            branch = ref.split("/")[2:]
            branch = ''.join(branch)
            if(branch == "uat"):
                os.system("git pull origin uat")
                os.system("sudo systemctl restart gunicorn-5")
                os.system("sudo systemctl restart gunicorn-6")
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("GithubWebhookAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)