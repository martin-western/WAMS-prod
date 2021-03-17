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
        "Authorization" : "Bearer " + "sk_test_aZxbfAKFzM2RwdhGmXc1Quq4",
        "content-type" : "application/json"
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

def get_charge_status(charge_id):
    try:
        logger.info("get charge status start")
        r = requests.get(url=TAP_IP+"/charges/"+charge_id,headers=header_for_requests())
        result = r.json()
        return result["status"]
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("TAP get_charge_status: %s at %s", e, str(exc_tb.tb_lineno)) 

def complete_payment_charges(generic_cart_obj, reference, token_id):
    try:
        logger.info("TAP payment initiated")
        input_data = {}
        input_data["amount"] = generic_cart_obj.to_pay
        input_data["currency"] = generic_cart_obj.get_currency()
        if token_id == "src_kw.knet"
            input_data["currency"] = "KWD"
        input_data["reference"] = {}
        input_data["reference"]["order"] = reference
        customer_details = {}
        customer_details["first_name"] = generic_cart_obj.owner.first_name
        customer_details["last_name"] = generic_cart_obj.owner.last_name
        customer_details["email"] = generic_cart_obj.owner.email
        customer_details["phone"] = {}
        customer_details["phone"]["country_code"] = 965
        customer_details["phone"]["number"] = generic_cart_obj.owner.contact_number
        input_data["customer"] = customer_details
        input_data["source"] = {}
        input_data["source"]["id"] = token_id
        input_data["redirect"] = {}
        input_data["redirect"]["url"] = WIGME_IP+"/transaction-processing/"
        logger.info("fmd input data: %s",str(input_data))
        r = requests.post(url=TAP_IP+"/charges",data=json.dumps(input_data),headers=header_for_requests())
        result = r.json()
        logger.info("charges resp : %s", result)
        return result
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("TAP complete_payment_charges: %s at %s", e, str(exc_tb.tb_lineno))

class MakePaymentOnlineTAPAPI(APIView):

    def post(self, request, *args, **kwargs):
    
        response = {}
        response["status"] = 500
        response["message"] = ""
        
        try:
            data = request.data
            logger.info("MakePaymentOnlineTAPAPI: %s", str(data))

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            is_fast_cart = data.get("is_fast_cart", False)
            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            if is_fast_cart==True:
                fast_cart_obj = FastCart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
            else:
                cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
            
            amount_to_pay = fast_cart_obj.get_total_amount() if is_fast_cart else cart_obj.get_total_amount()

            order_prefix = json.loads(location_group_obj.website_group.conf)["order_prefix"]
            order_cnt = Order.objects.filter(location_group=location_group_obj).count()+1
            reference = order_prefix + "-"+str(order_cnt)+"-"+str(uuid.uuid4())[:5]

            if is_fast_cart==True:
                fast_cart_obj.merchant_reference = reference
                fast_cart_obj.save()
            else:
                cart_obj.merchant_reference = reference
                cart_obj.save()
            
            order_result = complete_payment_charges(generic_cart_obj = fast_cart_obj if is_fast_cart else cart_obj, reference=reference, token_id=data["token_id"])

            if data["token_id"] == "src_kw.knet":
                response["knet_url"] = order_result["transaction"]["url"]
            if response["threeDSecure"] == True:
                response["redirect_url"] = order_result["transaction"]["url"]
            response["charge_id"] = order_result["id"]
            response["merchant_reference"] = reference
            response["charge_status"] = order_result["status"]
            response["status"] = 200
            response["message"] = "sucessfull creation of checkout into spotii"
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("MakePaymentOnlineTAPAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


MakePaymentOnlineTAP = MakePaymentOnlineTAPAPI.as_view()
