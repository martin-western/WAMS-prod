from WAMSApp.models import *
from WAMSApp.utils import *
from dealshub.constants import *

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


class RequestHyperpayCheckoutAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response["status"] = 500
        response["error"] = ""
        
        try:
            
            data = request.data
            logger.info("RequestHyperpayCheckoutAPI: %s", str(data))

            is_fast_cart = data.get("is_fast_cart", False)

            location_group_uuid = data["location_group_uuid"]
            payment_method = data.get("paymentMethod","VISA")

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group
            payment_credentials = json.loads(website_group_obj.payment_credentials)
            currency = location_group_obj.location.currency
            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            amount = 0
            shipping_address = None

            if is_fast_cart==False:
                cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
                amount = cart_obj.to_pay
                shipping_address = cart_obj.shipping_address 
            else:
                fast_cart_obj = FastCart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
                amount = fast_cart_obj.to_pay
                shipping_address = fast_cart_obj.shipping_address

            if amount == 0.0:
                response["error"] = "Cart Amount is ZERO!"
                response["status"] = 403
                logger.warning("RequestHyperpayCheckoutAPI Cart Amount Zero!")
                return Response(data=response)
            
            HEADERS = payment_credentials["headers"]
            API_URL = payment_credentials["hyperpay"]["url"]

            ENTITY_ID = payment_credentials["hyperpay"]["entity_id"][payment_method]
            API_KEY = payment_credentials["hyperpay"]["API_KEY"] # "NDVlNzFjOTAtYjk1ZS00YmE4LWJlZGMtOWI2YjlhMTBhYmE1OmMwODc2OTBjLTM4ZmQtNGZlMS04YjFiLWUzOWQ1ODdiMDhjYg=="
            
            headers = {
                "Authorization": "Basic "+API_KEY
            }

            data = {
                "entityId" : ENTITY_ID,
                "amount" : amount,
                "currency" : "SAR",
                "paymentType" : "DB"
            }

            payment_response = requests.post(url=API_URL, data=data, headers=headers)
            
            response["checkout_id"] = json.loads(payment_response.content)
            response["error"] = "checkout Success"
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("RequestHyperpayCheckoutAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)
        

def check_order_status_from_hyperpay(checkout_id, location_group_obj):
    try:
        payment_credentials = json.loads(location_group_obj.website_group.payment_credentials)

        HEADERS = payment_credentials["headers"]

        ENTITY_ID = payment_credentials["hyperpay"]["entity_id"][payment_method]
        API_KEY = payment_credentials["hyperpay"]["API_KEY"] 

        headers = {
            "Authorization": "Bearer "+API_KEY
        }

        API_URL = payment_credentials["hyperpay"]["url"] + checkout_id + "/payment?entityId="+entity_id
        r = requests.post(url=API_URL, headers=headers)

        content = json.loads(r.content)
        result_code = content["result"]["code"]
        if result_code == "000.000.000":
            return True
        return False
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("check_order_status_from_hyperpay: %s at %s", e, str(exc_tb.tb_lineno))        
    return False

RequestHyperpayCheckout = RequestHyperpayCheckoutAPI.as_view()