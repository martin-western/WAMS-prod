# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

from WAMSApp.models import *
from SalesApp.utils import *
from SalesApp.constants import *

from django.shortcuts import HttpResponse, get_object_or_404
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models import Count

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import AllowAny

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

class LoginSubmitAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("LoginSubmitAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            category_uuid = data["category_uuid"]
            image_type = data.get("image_type", "")
            
            category_obj = Category.objects.get(uuid=category_uuid)

            image_obj = Image.objects.create(image=data["image"])

            if image_type.lower()=="detailed":
                category_obj.mobile_app_image_detailed = image_obj
            else:
                category_obj.mobile_app_image = image_obj
            category_obj.save()

            response['status'] = 200
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("LoginSubmitAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

LoginSubmit = LoginSubmitAPI.as_view()