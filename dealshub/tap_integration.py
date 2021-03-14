import requests
import json
import logging

from rest_framework.response import Response
from rest_framework.views import APIView

from dealshub.models import *
from dealshub.constants import *

logger = logging.getLogger(__name__)

def header_for_requests():
    headers = {
        "Authorization" : "Bearer " + "sk_test_aZxbfAKFzM2RwdhGmXc1Quq4"
    }
    return headers

def get_token_id(card_details):
    try:
        logger.info("get token start")
        r = requests.post(url=TAP_IP+"/tokens",data=card_details,headers=header_for_requests())
        result = r.json()
        return result
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("TAP get_token_id: %s at %s", e, str(exc_tb.tb_lineno))

def complete_payment_charges(order_info, token_id):
    try:
        logger.info("TAP payment initiated")
        input_data = {

        }
        r = requests.post(url=TAP_IP+"/charges",data=input_data,headers=header_for_requests())
        result = r.json()
        return result
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("TAP get_token_id: %s at %s", e, str(exc_tb.tb_lineno))
