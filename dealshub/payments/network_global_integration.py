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

class MakePaymentNetworkGlobalAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response["status"] = 500
        response["error"] = ""
        
        try:
            
            data = request.data
            logger.info("MakePaymentNetworkGlobalAPI: %s", str(data))

            is_fast_cart = data.get("is_fast_cart", False)

            session_id = data["session_id"]
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
                logger.warning("MakePaymentNetworkGlobalAPI Cart Amount Zero!")
                return Response(data=response)

            payfort_multiplier = int(location_group_obj.location.payfort_multiplier)
            amount = str(int(float(amount)*payfort_multiplier))
            
            API_KEY = payment_credentials["network_global"]["API_KEY"] # "NDVlNzFjOTAtYjk1ZS00YmE4LWJlZGMtOWI2YjlhMTBhYmE1OmMwODc2OTBjLTM4ZmQtNGZlMS04YjFiLWUzOWQ1ODdiMDhjYg=="
            OUTLET_REF = payment_credentials["network_global"]["OUTLET_REF"] #"e209b88c-9fb6-4be8-ab4b-e4b977ad0e0d"
            
            headers = {
                "Content-Type": "application/vnd.ni-identity.v1+json", 
                "Authorization": "Basic "+API_KEY
            }
            
            net_url = NETWORK_URL+"/identity/auth/access-token"
            network_global_response = requests.post(url=net_url, headers=headers, timeout=10)
            ThirdPartyAPIRecord.objects.create(url=net_url,
                                        caller="MakePaymentNetworkGlobalAPI",
                                        request_body="",
                                        response_body=network_global_response.content,
                                        is_response_received=True
                                    )
            network_global_response_dict = json.loads(network_global_response.content)
            access_token = network_global_response_dict["access_token"]

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

            API_URL = NETWORK_URL+"/transactions/outlets/"+OUTLET_REF +"/payment/hosted-session/"+session_id
            
            payment_response = requests.post(API_URL, data=json.dumps(body),headers=headers, timeout=10)
            ThirdPartyAPIRecord.objects.create(url=API_URL,
                                        caller="MakePaymentNetworkGlobalAPI",
                                        request_body=json.dumps(body),
                                        response_body=payment_response.content,
                                        is_response_received=True
                                    )
            response["payment_response"] = json.loads(payment_response.content)
            response["error"] = "Payment Success"
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("MakePaymentNetworkGlobalAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class MakeB2BPaymentNetworkGlobalAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response["status"] = 500
        response["error"] = ""

        try:

            data = request.data
            logger.info("MakeB2BPaymentNetworkGlobalAPI: %s", str(data))

            session_id = data["session_id"]
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

            API_KEY = payment_credentials["network_global"]["API_KEY"] # "NDVlNzFjOTAtYjk1ZS00YmE4LWJlZGMtOWI2YjlhMTBhYmE1OmMwODc2OTBjLTM4ZmQtNGZlMS04YjFiLWUzOWQ1ODdiMDhjYg=="
            OUTLET_REF = payment_credentials["network_global"]["OUTLET_REF"] #"e209b88c-9fb6-4be8-ab4b-e4b977ad0e0d"

            headers = {
                "Content-Type": "application/vnd.ni-identity.v1+json",
                "Authorization": "Basic "+API_KEY
            }

            net_url = NETWORK_URL+"/identity/auth/access-token"
            network_global_response = requests.post(net_url, headers=headers, timeout=10)
            ThirdPartyAPIRecord.objects.create(url=net_url,
                                            caller="MakeB2BPaymentNetworkGlobalAPI",
                                            request_body="",
                                            response_body=network_global_response.content,
                                            is_response_received=True
                                        )
            network_global_response_dict = json.loads(network_global_response.content)
            access_token = network_global_response_dict["access_token"]

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

            API_URL = NETWORK_URL+"/transactions/outlets/"+OUTLET_REF +"/payment/hosted-session/"+session_id

            payment_response = requests.post(API_URL, data=json.dumps(body),headers=headers, timeout=10)
            ThirdPartyAPIRecord.objects.create(url=API_URL,
                                            caller="MakeB2BPaymentNetworkGlobalAPI",
                                            request_body=json.dumps(body),
                                            response_body=payment_response.content,
                                            is_response_received=True
                                        )
            response["payment_response"] = json.loads(payment_response.content)
            response["error"] = "Payment Success"
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("MakeB2BPaymentNetworkGlobalAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


def check_order_status_from_network_global(merchant_reference, location_group_obj):
    try:
        payment_credentials = json.loads(location_group_obj.website_group.payment_credentials)
        
        API_KEY = payment_credentials["network_global"]["API_KEY"]
        OUTLET_REF = payment_credentials["network_global"]["OUTLET_REF"]

        headers = {
            "Content-Type": "application/vnd.ni-identity.v1+json", 
            "Authorization": "Basic "+API_KEY
        }
        net_url = NETWORK_URL+"/identity/auth/access-token"
        response = requests.post(net_url, headers=headers, timeout=10)
        ThirdPartyAPIRecord.objects.create(url=net_url,
                                            caller="check_order_status_from_network_global",
                                            request_body="",
                                            response_body=response.content,
                                            is_response_received=True
                                        )
        response_dict = json.loads(response.content)
        access_token = response_dict["access_token"]

        headers = {
            "Authorization": "Bearer " + access_token ,
            "Content-Type": "application/vnd.ni-payment.v2+json", 
            "Accept": "application/vnd.ni-payment.v2+json" 
        }

        url = NETWORK_URL+"/transactions/outlets/"+OUTLET_REF+"/orders/"+merchant_reference
        r = requests.get(url=url, headers=headers, timeout=10)

        ThirdPartyAPIRecord.objects.create(url=url,
                                        caller="check_order_status_from_network_global",
                                        request_body="",
                                        response_body=r.content,
                                        is_response_received=True
                                    )
        content = json.loads(r.content)
        state = content["_embedded"]["payment"][0]["state"]
        if state=="CAPTURED" or state=="AUTHORISED":
            return True
        return False
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("check_order_status_from_network_global: %s at %s", e, str(exc_tb.tb_lineno))        
    return False

MakePaymentNetworkGlobal = MakePaymentNetworkGlobalAPI.as_view()

MakeB2BPaymentNetworkGlobal = MakeB2BPaymentNetworkGlobalAPI.as_view()