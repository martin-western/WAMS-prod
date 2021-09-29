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
import uuid

from datetime import datetime
from django.utils import timezone
from django.core.files import File

logger = logging.getLogger(__name__)


class MakePaymentCredimaxGatewayAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response["status"] = 500
        response["error"] = ""
        
        try:
            
            data = request.data
            logger.info("MakePaymentCredimaxGatewayAPI: %s", str(data))

            is_fast_cart = data.get("is_fast_cart", False)

            location_group_uuid = data["location_group_uuid"]

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group
            currency = location_group_obj.location.currency
            country_code = location_group_obj.location.name
            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            amount = 0
            shipping_address = None
            order_id = str(uuid.uuid4())

            if is_fast_cart==False:
                cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
                amount = cart_obj.to_pay
                shipping_address = cart_obj.shipping_address
            else:
                fast_cart_obj = FastCart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
                amount = fast_cart_obj.to_pay
                shipping_address = fast_cart_obj.shipping_address

            address_lines = json.loads(shipping_address.address_lines)
            emirates = shipping_address.emirates
            neighbourhood = shipping_address.neighbourhood
            postcode = shipping_address.postcode
            first_name = shipping_address.first_name
            last_name = shipping_address.last_name
            contact_number = shipping_address.contact_number

            if amount == 0:
                response["error"] = "Cart Amount is ZERO!"
                response["status"] = 403
                logger.warning("MakePaymentCredimaxGatewayAPI Cart Amount Zero!")
                return Response(data=response)

            merchant_id = "E16906950"
            API_KEY = "bWVyY2hhbnQuRTE2OTA2OTUwOmVjNjEyNzc1MTUxMzZiNGUyZWQ0ZTFkZWIzMDVkZTBk"

            headers = {
                "Authorization": "Basic "+API_KEY,
                "Content-Type": "application/json", 
                "Accept": "application/json" 
            }

            body = {
                "apiOperation": "CREATE_CHECKOUT_SESSION",
                "interaction":{
                    "operation": "PURCHASE",
                    "returnUrl": "https://bahrain.wigme.com/transaction-processing/",
                },
                "order":{
                    "id": str(order_id),
                    "amount": amount,
                    "currency": currency,
                },
            }

            credimax_url = 'https://credimax.gateway.mastercard.com/api/rest/version/60/merchant/'+merchant_id+'/session'
            credimax_gateway_response = requests.post(url=credimax_url,headers=headers, data=json.dumps(body), timeout=10)
            try:
                ThirdPartyAPIRecord.objects.create(url=credimax_url,
                                                caller="MakePaymentCredimaxGatewayAPI",
                                                request_body=json.dumps(body),
                                                response_body=credimax_gateway_response.content,
                                                is_response_received=True
                                            )
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("ThirdPartyAPIRecord in MakePaymentCredimaxGatewayAPI: %s at %s", e, str(exc_tb.tb_lineno))
            credimax_gateway_response_dict = json.loads(credimax_gateway_response.content)
            logger.info("INFOOMakePaymentCredimaxGatewayAPI: %s",credimax_gateway_response_dict)
            session_id = credimax_gateway_response_dict["session"]["id"]
            success_indicator = credimax_gateway_response_dict["successIndicator"]
            logger.error("MakePaymentCredimaxGatewayAPI: %s at %s",session_id,success_indicator)

            if is_fast_cart==False:
                cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
                cart_obj.merchant_reference = success_indicator
                cart_obj.save()
                logger.error(cart_obj.merchant_reference)
            else:
                fast_cart_obj = FastCart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
                fast_cart_obj.merchant_reference = success_indicator
                fast_cart_obj.save()
            response["transactionData"] = {
                "sessionId":session_id,
                "order": { 
                    "currency": currency, 
                    "amount": amount,
                    "id": order_id,
                },
                "billing": {
                    "address": {
                        "street": address_lines[0] + "\n" + address_lines[1] + "\n",
                        "street2":address_lines[2] + "\n" + address_lines[3] + "\n",
                        "city":emirates,
                        "postcodeZip":postcode,
                        "country_code": country_code,
                    },
                },
            }
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("MakePaymentCredimaxGatewayAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


def check_order_status_from_credimax_gateway(merchant_reference, location_group_obj):
    try:

        if Cart.objects.filter(merchant_reference=merchant_reference,location_group=location_group_obj).exists():
            return True
        
        if FastCart.objects.filter(merchant_reference=merchant_reference,location_group=location_group_obj).exists():
            return True

        return False
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("check_order_status_from_credimax_gateway: %s at %s", e, str(exc_tb.tb_lineno))        
    return False


MakePaymentCredimaxGateway = MakePaymentCredimaxGatewayAPI.as_view()
