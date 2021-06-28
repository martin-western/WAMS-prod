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
NETWORK_URL = "https://credimax.gateway.mastercard.com/api/rest/version/60/merchant"


class MakePaymentCredimaxGatewayAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response["status"] = 500
        response["error"] = ""
        
        try:
            
            data = request.data
            logger.info("MakePaymentCredimaxGatewayAPI: %s", str(data))

            # is_fast_cart = data.get("is_fast_cart", False)

            # location_group_uuid = data["location_group_uuid"]

            # location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            # website_group_obj = location_group_obj.website_group
            # currency = location_group_obj.location.currency
            # dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            # amount = 0
            # shipping_address = None

            # order_prefix = json.loads(location_group_obj.website_group.conf)["order_prefix"]
            # order_cnt = Order.objects.filter(location_group=location_group_obj).count()+1
            # merchant_reference = order_prefix + "-"+str(order_cnt)+"-"+str(uuid.uuid4())[:5]

            # if is_fast_cart==False:
            #     cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
            #     amount = cart_obj.to_pay
            #     shipping_address = cart_obj.shipping_address
            #     cart_obj.merchant_reference = merchant_reference
            #     cart_obj.save()
            # else:
            #     fast_cart_obj = FastCart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
            #     amount = fast_cart_obj.to_pay
            #     shipping_address = fast_cart_obj.shipping_address
            #     fast_cart_obj.merchant_reference = merchant_reference
            #     fast_cart_obj.save()

            # first_name = shipping_address.first_name
            # last_name = shipping_address.last_name
            # address = json.loads(shipping_address.address_lines)[0]
            # city = location_group_obj.location.name
            # country_code = "UAE"

            # if amount == 0.0:
            #     response["error"] = "Cart Amount is ZERO!"
            #     response["status"] = 403
            #     logger.warning("MakePaymentNetworkGlobalAndroidAPI Cart Amount Zero!")
            #     return Response(data=response)

            # payfort_multiplier = int(location_group_obj.location.payfort_multiplier)
            # amount = str(int(float(amount)*payfort_multiplier))
            
            API_KEY = "bWVyY2hhbnQuRTE2OTA2OTUwOmVjNjEyNzc1MTUxMzZiNGUyZWQ0ZTFkZWIzMDVkZTBk"
            
            headers = {
                "Content-Type": "application/vnd.ni-identity.v1+json", 
                "Authorization": "Basic "+API_KEY
            }
            body = {
                "session":{
                    "authenticationLimit":25
                }
            }
            network_global_android_response = requests.post("https://credimax.gateway.mastercard.com/api/rest/version/60/merchant/E16906950/session/", headers=headers,data=json.dumps(body))

            network_global_android_response_dict = json.loads(network_global_android_response.content)
            session_id = network_global_android_response_dict["session"]["id"]

            headers = {
                "Authorization": "Basic "+API_KEY,
                "Content-Type": "application/vnd.ni-payment.v2+json", 
                "Accept": "application/vnd.ni-payment.v2+json" 
            }

            body = {
                "order": { 
                    "currency": "AED", 
                    "amount": 1
                },
                # "merchantOrderReference": merchant_reference,
                # "merchantAttributes": {
                #     "redirectUrl": redirectUrl
                # },
                # "emailAddress": dealshub_user_obj.email,
                # "billing": {
                #     "address": {},
                #     "lastName": last_name,
                #     "address1": address,
                #     "city": city,
                #     "countryCode": country_code
                # }
            }
            API_URL = "https://credimax.gateway.mastercard.com/api/rest/version/60/merchant/E16906950/session/" + session_id
            
            payment_response = requests.put(API_URL, data=json.dumps(body),headers=headers)
            
            response["session_id"] = session_id
            response["payment_response"] = json.loads(payment_response.content)
            response["error"] = "Payment Success"
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("MakePaymentCredimaxGatewayAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


# def check_order_status_from_network_global_android(merchant_reference, location_group_obj):
#     try:
#         payment_credentials = json.loads(location_group_obj.website_group.payment_credentials)

#         #  have to add api key and outlet data in payment credentials

#         # API_KEY = payment_credentials["network_global_android"]["API_KEY"]
#         # OUTLET_REF = payment_credentials["network_global_android"]["OUTLET_REF"]

#         API_KEY = "ZTkzNmY2NGMtY2M1Yi00OWZiLWE5ZjQtNDhhOWJiMGZhZWJiOmQ1MDAxYjc5LTVkMmYtNDRkYi1iYmU0LWNhMGJmYTI3MTcxYw=="
#         OUTLET_REF = "7f40fd1d-c382-4b51-9dab-6650d1097179"
        
#         headers = {
#             "Content-Type": "application/vnd.ni-identity.v1+json", 
#             "Authorization": "Basic "+API_KEY
#         }
#         response = requests.post(NETWORK_URL+"/identity/auth/access-token", headers=headers)

#         response_dict = json.loads(response.content)
#         access_token = response_dict["access_token"]

#         headers = {
#             "Authorization": "Bearer " + access_token ,
#             "Content-Type": "application/vnd.ni-payment.v2+json", 
#             "Accept": "application/vnd.ni-payment.v2+json" 
#         }

#         url = NETWORK_URL+"/transactions/outlets/"+OUTLET_REF+"/orders/"+merchant_reference
#         r = requests.get(url=url, headers=headers)

#         content = json.loads(r.content)
#         state = content["_embedded"]["payment"][0]["state"]
#         if state=="CAPTURED" or state=="AUTHORISED":
#             return True
#         return False
#     except Exception as e:
#         exc_type, exc_obj, exc_tb = sys.exc_info()
#         logger.error("check_order_status_from_network_global_android: %s at %s", e, str(exc_tb.tb_lineno))        
#     return False





# class MakeB2BPaymentNetworkGlobalAndroidAPI(APIView):

#     def post(self, request, *args, **kwargs):

#         response = {}
#         response["status"] = 500
#         response["error"] = ""

#         try:

#             data = request.data
#             logger.info("MakeB2BPaymentNetworkGlobalAPI: %s", str(data))

#             location_group_uuid = data["location_group_uuid"]
#             location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
#             website_group_obj = location_group_obj.website_group
#             order_request_obj = OrderRequest.objects.get(uuid = data["OrderRequestUuid"])

#             try:
#                 if location_group_obj.is_b2b == False:
#                     response["message"] = "!b2b"
#                     logger.warning("MakeB2BPaymentNetworkGlobalAPI: Not a B2B LocationGroup %s at %s", e, str(exc_tb.tb_lineno))
#                     return Response(data=response)
#             except Exception as e:
#                 exc_type, exc_obj, exc_tb = sys.exc_info()
#                 logger.warning("MakeB2BPaymentNetworkGlobalAPI: location group not handled properly%s at %s", e, str(exc_tb.tb_lineno))

#             payment_credentials = json.loads(website_group_obj.payment_credentials)
#             currency = location_group_obj.location.currency
#             dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

#             amount = 0
#             shipping_address = None

#             order_prefix = json.loads(location_group_obj.website_group.conf)["order_prefix"]
#             order_cnt = Order.objects.filter(location_group=location_group_obj).count()+1
#             # merchant_reference = order_prefix + "-"+str(order_cnt)+"-"+str(uuid.uuid4())[:5]
#             # while retriving order status n_genious only support order_reference. I tried to get state using merchantOrderReference but got error as:-
#             # state:- {'message': 'Not Found', 'code': 404, 'errors': [{'message': 'Entity not found', 'localizedMessage': '{error.processing.invalidOrderReference}', 'errorCode': 'invalidOrderReference', 'domain': 'processing'}]}
#             # Hence saving order_reference in above merchant_reference
 
#             if order_request_obj.request_status == "Approved":
#                 amount = order_request_obj.to_pay
#                 shipping_address = order_request_obj.shipping_address

#             first_name = shipping_address.first_name
#             last_name = shipping_address.last_name
#             address = json.loads(shipping_address.address_lines)[0]
#             city = location_group_obj.location.name
#             country_code = "UAE"

#             if amount == 0.0:
#                 response["error"] = "Cart Amount is ZERO!"
#                 response["status"] = 403
#                 logger.warning("MakeB2BPaymentNetworkGlobalAPI Cart Amount Zero!")
#                 return Response(data=response)

#             payfort_multiplier = int(location_group_obj.location.payfort_multiplier)
#             amount = str(int(float(amount)*payfort_multiplier))
            
#             API_KEY = "ZTkzNmY2NGMtY2M1Yi00OWZiLWE5ZjQtNDhhOWJiMGZhZWJiOmQ1MDAxYjc5LTVkMmYtNDRkYi1iYmU0LWNhMGJmYTI3MTcxYw=="
#             OUTLET_REF = "7f40fd1d-c382-4b51-9dab-6650d1097179"
            
#             headers = {
#                 "Content-Type": "application/vnd.ni-identity.v1+json", 
#                 "Authorization": "Basic "+API_KEY
#             }
            
#             network_global_android_response = requests.post(NETWORK_URL+"/identity/auth/access-token", headers=headers)

#             network_global_android_response_dict = json.loads(network_global_android_response.content)
#             access_token = network_global_android_response_dict["access_token"]
#             # redirectUrl = data["redirectUrl"]

#             headers = {
#                 "Authorization": "Bearer " + access_token ,
#                 "Content-Type": "application/vnd.ni-payment.v2+json", 
#                 "Accept": "application/vnd.ni-payment.v2+json" 
#             }

#             body = {
#                 "action": "SALE",
#                 "amount": { 
#                     "currencyCode": currency, 
#                     "value": amount
#                 },
#                 # "merchantOrderReference": merchant_reference,
#                 # "merchantAttributes": {
#                 #     "redirectUrl": redirectUrl
#                 # },
#                 "emailAddress": dealshub_user_obj.email,
#                 "billingAddress": {
#                     "firstName": first_name,
#                     "lastName": last_name,
#                     "address1": address,
#                     "city": city,
#                     "countryCode": country_code
#                 }
#             }

#             first_name = ""
#             last_name = ""
#             address = ""
#             city = ""
#             country_code = ""

#             API_URL = NETWORK_URL+"/transactions/outlets/"+OUTLET_REF +"/orders"
            
#             payment_response = requests.post(API_URL, data=json.dumps(body),headers=headers)
#             payment_response_content = json.loads(payment_response.content)
#             merchant_reference = payment_response_content["_embedded"]["payment"][0]["orderReference"]

#             if order_request_obj.request_status == "Approved":
#                 order_request_obj.merchant_reference = merchant_reference
#                 order_request_obj.save()
            
#             response["payment_response"] = payment_response_content
#             response["error"] = "Payment Success"
#             response["status"] = 200

#         except Exception as e:
#             exc_type, exc_obj, exc_tb = sys.exc_info()
#             logger.error("MakeB2BPaymentNetworkGlobalAPI: %s at %s", e, str(exc_tb.tb_lineno))

#         return Response(data=response)



MakePaymentCredimaxGateway = MakePaymentCredimaxGatewayAPI.as_view()