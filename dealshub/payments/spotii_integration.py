import requests
import json
import logging

from rest_framework.response import Response
from rest_framework.views import APIView

from dealshub.models import *
from dealshub.constants import *

logger = logging.getLogger(__name__)


class MakePaymentSpotiiAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response["status"] = 500
        response["message"] = ""
        
        try:
            data = request.data
            logger.info("MakePaymentSpotiiAPI: %s", str(data))

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            is_fast_cart = data.get("is_fast_cart", False)
            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            if is_fast_cart==True:
                fast_cart_obj = FastCart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
            else:
                cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
            
            amount_to_pay = fast_cart_obj.get_total_amount() if is_fast_cart else cart_obj.get_total_amount()

            if float(amount_to_pay) < 200.0:
                response["status"] = 403
                response["message"] = "Cannot use this method for less than 200 valued order"
                return Response(data=response)
            
            order_prefix = json.loads(location_group_obj.website_group.conf)["order_prefix"]
            order_cnt = Order.objects.filter(location_group=location_group_obj).count()+1
            reference = order_prefix + "-"+str(order_cnt)+"-"+str(uuid.uuid4())[:3]

            if is_fast_cart==True:
                fast_cart_obj.merchant_reference = reference
                fast_cart_obj.save()
            else:
                cart_obj.merchant_reference = reference
                cart_obj.save()

            links = process_order_checkout(generic_cart_obj = fast_cart_obj if is_fast_cart else cart_obj, is_fast_cart=is_fast_cart, reference=reference)
           
            response["links"] = links
            response["status"] = 200
            response["message"] = "sucessfull creation of checkout into spotii"
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("MakePaymentSpotiiAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


def get_auth_token():
    try:
        auth_key_info = {
            "public_key": "Qlegb7n2MSUb0pp8GCp7OR8Phj4TWZXF",
            "private_key": "Gt01506Xko46NYjJgYhbw8ICb3tpdzRKbfmqGrVBwzps5soDRWa3K2ZMhqTRevIv"
        }
        headers = { 
            "Content-Type": "application/json", 
            "Accept": "application/json; indent=4" 
        }
        spotii_url = SPOTII_AUTH_IP+"/api/v1.0/merchant/authentication/"

        third_party_api_record_obj = ThirdPartyAPIRecord.objects.none()
        try:
            third_party_api_record_obj = ThirdPartyAPIRecord.objects.create(url=spotii_url,
                                            caller="Spotii get_auth_token",
                                            request_body=json.dumps(auth_key_info),
                                        )
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ThirdPartyAPIRecord in Spotii get_auth_token: %s at %s", e, str(exc_tb.tb_lineno))

        resp = requests.post(url=spotii_url,data=json.dumps(auth_key_info),headers=headers, timeout=10)
        
        try:
            third_party_api_record_obj.is_response_received = True
            third_party_api_record_obj.response_body=resp.json()
            third_party_api_record_obj.save()
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ThirdPartyAPIRecord in Spotii get_auth_token: %s at %s", e, str(exc_tb.tb_lineno))

        token = resp.json()["token"]
        return token
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Spotii get_auth_token: %s at %s", e, str(exc_tb.tb_lineno))


def process_order_checkout(generic_cart_obj, is_fast_cart, reference):
    try:

        address_info = {}
        if generic_cart_obj.shipping_address!=None:
            address_obj = generic_cart_obj.shipping_address
            address_info["first_name"] = address_obj.first_name
            address_info["last_name"] = address_obj.last_name
            address_info["line1"] = json.loads(address_obj.address_lines)[0]
            address_info["line2"] = json.loads(address_obj.address_lines)[1]
            address_info["line3"] = json.loads(address_obj.address_lines)[2]
            address_info["line4"] = json.loads(address_obj.address_lines)[3]
            address_info["state"] = address_obj.state
            address_info["postcode"] = address_obj.postcode
            address_info["country"] = "AE"
            address_info["phone"] = address_obj.contact_number

        generic_unit_cart_list_info = []
        if is_fast_cart==True:
            temp_dict = {}
            dealshub_product_obj = generic_cart_obj.product
            temp_dict["sku"] = dealshub_product_obj.get_seller_sku()
            temp_dict["reference"] = generic_cart_obj.uuid
            temp_dict["title"] = dealshub_product_obj.get_name()
            temp_dict["upc"] = ""
            temp_dict["quantity"] = float(generic_cart_obj.quantity)
            temp_dict["price"] = float(dealshub_product_obj.get_actual_price_for_customer(generic_cart_obj.owner))
            temp_dict["currency"] = dealshub_product_obj.get_currency()
            temp_dict["image_url"] = dealshub_product_obj.get_display_image_url()
            generic_unit_cart_list_info.append(temp_dict)
        else:
            for unit_cart_obj in UnitCart.objects.filter(cart=generic_cart_obj):
                temp_dict = {}
                temp_dict["sku"] = unit_cart_obj.product.get_seller_sku()
                temp_dict["reference"] = unit_cart_obj.uuid
                temp_dict["title"] = unit_cart_obj.product.get_name()
                temp_dict["upc"] = ""
                temp_dict["quantity"] = float(unit_cart_obj.quantity)
                temp_dict["price"] = float(unit_cart_obj.product.get_actual_price_for_customer(generic_cart_obj.owner))
                temp_dict["currency"] = unit_cart_obj.product.get_currency()
                temp_dict["image_url"] = unit_cart_obj.product.get_display_image_url()
                generic_unit_cart_list_info.append(temp_dict)

        order_info = {
            "reference" : reference,
            "display_reference" : reference,
            "description" : "Cart #"+ str(reference),
            "total": float(generic_cart_obj.get_total_amount()),
            "currency": generic_cart_obj.get_currency(),
            "confirm_callback_url": WIGME_IP+"/transaction-processing/?reference="+reference,
            "reject_callback_url": WIGME_IP+"/transaction-processing/?orderFailed=true",
            "order": {
                "tax_amount": 0,
                "shipping_amount": generic_cart_obj.get_delivery_fee(),
                "discount": 0,
                "customer": {
                    "first_name": generic_cart_obj.owner.first_name,
                    "last_name": generic_cart_obj.owner.last_name,
                    "email": generic_cart_obj.owner.email,
                    "phone": generic_cart_obj.owner.contact_number
                },
                "billing_address": address_info,
                "shipping_address": address_info,
                "lines": generic_unit_cart_list_info
            }
        }

        headers = {
            "Content-Type" : "application/json",
            "Accept" : "application/json; indent=4",
            "Authorization" : "Bearer " + str(get_auth_token())
        }
        logger.info(order_info)

        spotii_url = SPOTII_IP+"/api/v1.0/checkouts/"

        third_party_api_record_obj = ThirdPartyAPIRecord.objects.none()
        try:
            third_party_api_record_obj = ThirdPartyAPIRecord.objects.create(url=spotii_url,
                                            caller="Spotii process_order_checkout",
                                            request_body=json.dumps(order_info),
                                        )
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ThirdPartyAPIRecord in Spotii process_order_checkout: %s at %s", e, str(exc_tb.tb_lineno))

        resp = requests.post(url=spotii_url, data=json.dumps(order_info), headers=headers, timeout=10)
        
        try:
            third_party_api_record_obj.is_response_received = True
            third_party_api_record_obj.response_body=resp.json()
            third_party_api_record_obj.save()
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ThirdPartyAPIRecord in Spotii process_order_checkout: %s at %s", e, str(exc_tb.tb_lineno))

        resp = resp.json()

        logger.info(resp)
        
        checkout_result_urls = {
            "confirm_callback_url" : resp["confirm_callback_url"],
            "reject_callback_url" : resp["reject_callback_url"],
            "checkout_url" : resp["checkout_url"]
        }
        return checkout_result_urls   

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Spotii process_order_checkout: %s at %s", e, str(exc_tb.tb_lineno))


def on_approve_capture_order(order_reference):
    try:
        headers = {
            "Content-Type" : "application/json",
            "Accept" : "application/json; indent=4",
            "Authorization" : "Bearer " + str(get_auth_token())
        }
        spotii_url = SPOTII_IP+"/api/v1.0/orders/"+order_reference+"/capture/"

        third_party_api_record_obj = ThirdPartyAPIRecord.objects.none()
        try:
            third_party_api_record_obj = ThirdPartyAPIRecord.objects.create(url=spotii_url,
                                            caller="Spotii on_approve_capture_order",
                                            request_body=json.dumps({}),
                                        )
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ThirdPartyAPIRecord in Spotii on_approve_capture_order: %s at %s", e, str(exc_tb.tb_lineno))

        resp = requests.post(url=spotii_url, data={}, headers=headers, timeout=10)
        
        try:
            third_party_api_record_obj.is_response_received = True
            third_party_api_record_obj.response_body=resp.json()
            third_party_api_record_obj.save()
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ThirdPartyAPIRecord in Spotii on_approve_capture_order: %s at %s", e, str(exc_tb.tb_lineno))

        resp = resp.json()
        if resp["status"]=="SUCCESS":
            logger.info("Spotii ref id : ",resp["order_id"])
            return True
        return False
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Spotii on_approve_capture_order: %s at %s", e, str(exc_tb.tb_lineno))


MakePaymentSpotii = MakePaymentSpotiiAPI.as_view()