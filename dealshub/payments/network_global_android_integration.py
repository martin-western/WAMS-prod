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

logger = logging.getLogger(__name__)
NETWORK_URL = "https://api-gateway.sandbox.ngenius-payments.com"


class MakePaymentNetworkGlobalAndroidAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response["status"] = 500
        response["error"] = ""
        
        try:
            
            data = request.data
            logger.info("MakePaymentNetworkGlobalAndroidAPI: %s", str(data))

            is_fast_cart = data.get("is_fast_cart", False)

            location_group_uuid = data["location_group_uuid"]

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group
            payment_credentials = json.loads(website_group_obj.payment_credentials)
            currency = location_group_obj.location.currency
            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            amount = 0
            shipping_address = None

            order_prefix = json.loads(location_group_obj.website_group.conf)["order_prefix"]
            order_cnt = Order.objects.filter(location_group=location_group_obj).count()+1
            merchant_reference = order_prefix + "-"+str(order_cnt)+"-"+str(uuid.uuid4())[:5]

            if is_fast_cart==False:
                cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
                amount = cart_obj.to_pay
                shipping_address = cart_obj.shipping_address
                cart_obj.merchant_reference = merchant_reference
                cart_obj.save()
            else:
                fast_cart_obj = FastCart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
                amount = fast_cart_obj.to_pay
                shipping_address = fast_cart_obj.shipping_address
                fast_cart_obj.merchant_reference = merchant_reference
                fast_cart_obj.save()

            first_name = shipping_address.first_name
            last_name = shipping_address.last_name
            address = json.loads(shipping_address.address_lines)[0]
            city = location_group_obj.location.name
            country_code = "UAE"

            if amount == 0.0:
                response["error"] = "Cart Amount is ZERO!"
                response["status"] = 403
                logger.warning("MakePaymentNetworkGlobalAndroidAPI Cart Amount Zero!")
                return Response(data=response)

            payfort_multiplier = int(location_group_obj.location.payfort_multiplier)
            amount = str(int(float(amount)*payfort_multiplier))
            
            # API_KEY = payment_credentials["network_global_android"]["API_KEY"] 
            # OUTLET_REF = payment_credentials["network_global_android"]["OUTLET_REF"]
            
            API_KEY = "ZTkzNmY2NGMtY2M1Yi00OWZiLWE5ZjQtNDhhOWJiMGZhZWJiOmQ1MDAxYjc5LTVkMmYtNDRkYi1iYmU0LWNhMGJmYTI3MTcxYw=="
            OUTLET_REF = "7f40fd1d-c382-4b51-9dab-6650d1097179"
            
            headers = {
                "Content-Type": "application/vnd.ni-identity.v1+json", 
                "Authorization": "Basic "+API_KEY
            }
            
            network_global_android_response = requests.post(NETWORK_URL+"/identity/auth/access-token", headers=headers)

            network_global_android_response_dict = json.loads(network_global_android_response.content)
            access_token = network_global_android_response_dict["access_token"]
            # redirectUrl = data["redirectUrl"]

            headers = {
                "Authorization": "Bearer " + access_token ,
                "Content-Type": "application/vnd.ni-payment.v2+json", 
                "Accept": "application/vnd.ni-payment.v2+json" 
            }

            body = {
                "action": "SALE",
                "amount": { 
                    "currencyCode": currency, 
                    "value": amount
                },
                "merchantOrderReference": merchant_reference,
                # "merchantAttributes": {
                #     "redirectUrl": redirectUrl
                # },
                "emailAddress": dealshub_user_obj.email,
                "billingAddress": {
                    "firstName": first_name,
                    "lastName": last_name,
                    "address1": address,
                    "city": city,
                    "countryCode": country_code
                }
            }

            first_name = ""
            last_name = ""
            address = ""
            city = ""
            country_code = ""

            API_URL = NETWORK_URL+"/transactions/outlets/"+OUTLET_REF +"/orders"
            
            payment_response = requests.post(API_URL, data=json.dumps(body),headers=headers)
            
            response["payment_response"] = json.loads(payment_response.content)
            response["error"] = "Payment Success"
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("MakePaymentNetworkGlobalAndroidAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class MakeB2BPaymentNetworkGlobalAndroidAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response["status"] = 500
        response["error"] = ""

        try:

            data = request.data
            logger.info("MakeB2BPaymentNetworkGlobalAPI: %s", str(data))

            location_group_uuid = data["location_group_uuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group
            order_request_obj = OrderRequest.objects.get(uuid = data["OrderRequestUuid"])

            try:
                if location_group_obj.is_b2b == False:
                    response["message"] = "!b2b"
                    logger.warning("MakeB2BPaymentNetworkGlobalAPI: Not a B2B LocationGroup %s at %s", e, str(exc_tb.tb_lineno))
                    return Response(data=response)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("MakeB2BPaymentNetworkGlobalAPI: location group not handled properly%s at %s", e, str(exc_tb.tb_lineno))

            payment_credentials = json.loads(website_group_obj.payment_credentials)
            currency = location_group_obj.location.currency
            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            amount = 0
            shipping_address = None

            order_prefix = json.loads(location_group_obj.website_group.conf)["order_prefix"]
            order_cnt = Order.objects.filter(location_group=location_group_obj).count()+1
            merchant_reference = order_prefix + "-"+str(order_cnt)+"-"+str(uuid.uuid4())[:5]

            if order_request_obj.request_status == "Approved":
                amount = order_request_obj.to_pay
                shipping_address = order_request_obj.shipping_address
                order_request_obj.merchant_reference = merchant_reference
                order_request_obj.save()

            first_name = shipping_address.first_name
            last_name = shipping_address.last_name
            address = json.loads(shipping_address.address_lines)[0]
            city = location_group_obj.location.name
            country_code = "UAE"

            if amount == 0.0:
                response["error"] = "Cart Amount is ZERO!"
                response["status"] = 403
                logger.warning("MakeB2BPaymentNetworkGlobalAPI Cart Amount Zero!")
                return Response(data=response)

            payfort_multiplier = int(location_group_obj.location.payfort_multiplier)
            amount = str(int(float(amount)*payfort_multiplier))
            
            API_KEY = "ZTkzNmY2NGMtY2M1Yi00OWZiLWE5ZjQtNDhhOWJiMGZhZWJiOmQ1MDAxYjc5LTVkMmYtNDRkYi1iYmU0LWNhMGJmYTI3MTcxYw=="
            OUTLET_REF = "7f40fd1d-c382-4b51-9dab-6650d1097179"
            
            headers = {
                "Content-Type": "application/vnd.ni-identity.v1+json", 
                "Authorization": "Basic "+API_KEY
            }
            
            network_global_android_response = requests.post(NETWORK_URL+"/identity/auth/access-token", headers=headers)

            network_global_android_response_dict = json.loads(network_global_android_response.content)
            access_token = network_global_android_response_dict["access_token"]
            # redirectUrl = data["redirectUrl"]

            headers = {
                "Authorization": "Bearer " + access_token ,
                "Content-Type": "application/vnd.ni-payment.v2+json", 
                "Accept": "application/vnd.ni-payment.v2+json" 
            }

            body = {
                "action": "SALE",
                "amount": { 
                    "currencyCode": currency, 
                    "value": amount
                },
                "merchantOrderReference": merchant_reference,
                # "merchantAttributes": {
                #     "redirectUrl": redirectUrl
                # },
                "emailAddress": dealshub_user_obj.email,
                "billingAddress": {
                    "firstName": first_name,
                    "lastName": last_name,
                    "address1": address,
                    "city": city,
                    "countryCode": country_code
                }
            }

            first_name = ""
            last_name = ""
            address = ""
            city = ""
            country_code = ""

            API_URL = NETWORK_URL+"/transactions/outlets/"+OUTLET_REF +"/orders"
            
            payment_response = requests.post(API_URL, data=json.dumps(body),headers=headers)
            
            response["payment_response"] = json.loads(payment_response.content)
            response["error"] = "Payment Success"
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("MakeB2BPaymentNetworkGlobalAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


def check_order_status_from_network_global_android(merchant_reference, location_group_obj):
    try:
        payment_credentials = json.loads(location_group_obj.website_group.payment_credentials)

        #  have to add api key and outlet data in payment credentials

        # API_KEY = payment_credentials["network_global_android"]["API_KEY"]
        # OUTLET_REF = payment_credentials["network_global_android"]["OUTLET_REF"]

        API_KEY = "ZTkzNmY2NGMtY2M1Yi00OWZiLWE5ZjQtNDhhOWJiMGZhZWJiOmQ1MDAxYjc5LTVkMmYtNDRkYi1iYmU0LWNhMGJmYTI3MTcxYw=="
        OUTLET_REF = "7f40fd1d-c382-4b51-9dab-6650d1097179"
        
        headers = {
            "Content-Type": "application/vnd.ni-identity.v1+json", 
            "Authorization": "Basic "+API_KEY
        }
        response = requests.post(NETWORK_URL+"/identity/auth/access-token", headers=headers)

        response_dict = json.loads(response.content)
        access_token = response_dict["access_token"]

        headers = {
            "Authorization": "Bearer " + access_token ,
            "Content-Type": "application/vnd.ni-payment.v2+json", 
            "Accept": "application/vnd.ni-payment.v2+json" 
        }

        url = NETWORK_URL+"/transactions/outlets/"+OUTLET_REF+"/orders/"+merchant_reference
        r = requests.get(url=url, headers=headers)

        content = json.loads(r.content)
        logger.info("check_order_status_from_network_global_android: state:- %s",str(content))
        state = content["_embedded"]["payment"][0]["state"]
        logger.info("check_order_status_from_network_global_android: state:- %s",str(state))
        if state=="CAPTURED" or state=="AUTHORISED":
            return True
        return False
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("check_order_status_from_network_global_android: %s at %s", e, str(exc_tb.tb_lineno))        
    return False

MakePaymentNetworkGlobalAndroid = MakePaymentNetworkGlobalAndroidAPI.as_view()
MakeB2BPaymentNetworkGlobalAndroid = MakeB2BPaymentNetworkGlobalAndroidAPI.as_view()