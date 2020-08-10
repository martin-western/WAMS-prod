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
        response["error"] = ""
        
        try:
            
            data = request.data
            logger.info("MakePaymentNetworkGlobalAPI: %s", str(data))

            try :
                session_id = data["session_id"]
            except Exception as e:
                response["error"] = "Session ID not passed!"
                response["status"] = 404
                logger.warning("MakePaymentNetworkGlobalAPI Session ID not passed!")
                return Response(data=response)

            try :
                location_group_uuid = data["location_group_uuid"]
            except Exception as e:
                response["error"] = "Location Group UUID not passed!"
                response["status"] = 404
                logger.warning("MakePaymentNetworkGlobalAPI Location Group UUID not passed!")
                return Response(data=response)

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            currency = location_group_obj.location.currency
            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
            amount = cart_obj.to_pay

            if amount == 0.0:
                response["error"] = "Cart Amount is ZERO!"
                response["status"] = 403
                logger.warning("MakePaymentNetworkGlobalAPI Cart Amount Zero!")
                return Response(data=response)

            payfort_multiplier = int(cart_obj.location_group.location.payfort_multiplier)
            amount = str(int(float(amount)*payfort_multiplier))
            
            API_KEY = "NDVlNzFjOTAtYjk1ZS00YmE4LWJlZGMtOWI2YjlhMTBhYmE1OmMwODc2OTBjLTM4ZmQtNGZlMS04YjFiLWUzOWQ1ODdiMDhjYg=="
            
            headers = {
                "Content-Type": "application/vnd.ni-identity.v1+json", 
                "Authorization": "Basic "+API_KEY
            }
            
            network_global_response = requests.post("https://api-gateway.sandbox.ngenius-payments.com/identity/auth/access-token", headers=headers)

            network_global_response_dict = json.loads(network_global_response.content)
            access_token = response_dict["access_token"]

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
                }
            }

            OUTLET_REF = "e209b88c-9fb6-4be8-ab4b-e4b977ad0e0d"
            API_URL = "https://api-gateway.sandbox.ngenius-payments.com/transactions/outlets/"+OUTLET_REF +"/payment/hosted-session/"+session_id
            
            payment_response = requests.post(API_URL, data=json.dumps(body),headers=headers)
            
            response["payment_response"] = json.loads(payment_response)
            response["error"] = "Payment Success"
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("MakePaymentNetworkGlobalAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

MakePaymentNetworkGlobal = MakePaymentNetworkGlobalAPI.as_view()