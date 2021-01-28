from WAMSApp.models import *
from WAMSApp.utils import *
from dealshub.constants import *

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

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
        
        try:
            
            data = request.data
            logger.info("RequestHyperpayCheckoutAPI: %s", str(data))

            is_fast_cart = data.get("is_fast_cart", False)

            location_group_uuid = data["location_group_uuid"]

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group
            payment_credentials = website_group_obj.payment_credentials
            if not isinstance(payment_credentials, dict):
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
                response["status"] = 403
                logger.warning("RequestHyperpayCheckoutAPI Cart Amount Zero!")
                return Response(data=response)

            API_URL = payment_credentials["hyperpay"]["url"]
            ENTITY_ID = payment_credentials["hyperpay"]["entity_id"]
            API_KEY = payment_credentials["hyperpay"]["API_KEY"]

            amount = "{:.2f}".format(amount)
            
            headers = {
                "Authorization": "Bearer "+ API_KEY
            }

            data = {
                "entityId" : ENTITY_ID,
                "amount" : amount,
                "currency" : "SAR",
                "paymentType" : "DB"
            }

            payment_response = requests.post(url=API_URL, data=data, headers=headers)
            logger.info("payment_response from hyperpay: %s", str(payment_response.content))
            response["checkout_id"] = json.loads(payment_response.content)["ndc"]
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("RequestHyperpayCheckoutAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)
        

def get_order_info_from_hyperpay(checkout_id, location_group_obj):
    order_info = {}

    try:
        payment_credentials = json.loads(location_group_obj.website_group.payment_credentials)

        ENTITY_ID = payment_credentials["hyperpay"]["entity_id"]
        API_KEY = payment_credentials["hyperpay"]["API_KEY"]

        headers = {
            "Authorization": "Bearer "+API_KEY
        }
        API_URL = payment_credentials["hyperpay"]["url"] + checkout_id + "/payment?entityId="+ENTITY_ID
        r = requests.post(url=API_URL, headers=headers)

        content = json.loads(r.content)
        payment_info = {}
        try:
            payment_info = {
                "paymentBrand": content["paymentBrand"],
                "descriptor": content["descriptor"],
                "result": content["result"],
                "amount": content["amount"],
                "currency": content["currency"],
                "timestamp": content["timestamp"],
                "paymentType": content["paymentType"],
                "risk": content["risk"],
            }
        except:
            pass

        order_info["payment_info"] = payment_info

        result_code = content["result"]["code"]
        order_info["result"] = False
        if result_code == "000.100.110":
            order_info["result"] = True

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("get_order_info_from_hyperpay: %s at %s", e, str(exc_tb.tb_lineno))

    return order_info


RequestHyperpayCheckout = RequestHyperpayCheckoutAPI.as_view()