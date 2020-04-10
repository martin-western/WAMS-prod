from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

from WAMSApp.models import *
from WAMSApp.utils import *
from WAMSApp.utils_sourcing import *

from MWS import APIs

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


from datetime import datetime
from django.utils import timezone
from django.core.files import File


logger = logging.getLogger(__name__)

MWS_PARAMS = settings.MWS_PARAMS

class GetMatchingProductsMWSAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if request.user.has_perm('WAMSApp.push_product_on_amazon') == False:
                logger.warning("GetMatchingProductsMWSAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("GetMatchingProductsMWSAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            channel_name = data["channel_name"]

            permissible_channels = custom_permission_filter_channels(
                request.user)
            channel_obj = Channel.objects.get(name=channel_name)

            if channel_obj not in permissible_channels:
                logger.warning(
                    "SaveNoonChannelProductAPI Restricted Access of Noon Channel!")
                response['status'] = 403
                return Response(data=response)

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("GetMatchingProductsMWSAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

GetMatchingProductsMWS = GetMatchingProductsMWSAPI.as_view()