from django.shortcuts import render
from django.contrib.auth import logout, authenticate, login
from django.http import HttpResponseRedirect

from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny

from dealshub.models import *
from dealshub.constants import *
from dealshub.utils import *
from WAMSApp.constants import *
from WAMSApp.utils import *
from WAMSApp.utils_SAP_Integration import *
from dealshub.network_global_integration import *
from dealshub.postaplus import *

from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

from datetime import datetime

from WAMSApp.utils_SAP_Integration import *

import sys
import logging
import json
import requests
import hashlib
import threading
import math
import random

logger = logging.getLogger(__name__)


class CsrfExemptSessionAuthentication(SessionAuthentication):

    def enforce_csrf(self, request):
        return


class AddToWishListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddToWishListAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            product_uuid = data["productUuid"]
            location_group_uuid = data["locationGroupUuid"]

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=product_uuid)

            if dealshub_product_obj.location_group!=location_group_obj:
                response["status"] = 403
                logger.error("AddToWishListAPI: Product does not exist in LocationGroup!")
                return Response(data=response)

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            wish_list_obj = WishList.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
            unit_wish_list_obj = None
            
            if UnitWishList.objects.filter(wish_list=wish_list_obj, product=dealshub_product_obj).exists()==False:
                unit_wish_list_obj = UnitWishList.objects.create(wish_list=wish_list_obj, product=dealshub_product_obj)
            else:
                unit_wish_list_obj = UnitWishList.objects.get(wish_list=wish_list_obj, product=dealshub_product_obj)

            response["unitWishListUuid"] = unit_wish_list_obj.uuid
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddToWishListAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class RemoveFromWishListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("RemoveFromWishListAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            unit_wish_list_uuid = data["unitWishListUuid"]
            
            unit_wish_list_obj = UnitWishList.objects.get(uuid=unit_wish_list_uuid)
            unit_wish_list_obj.delete()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("RemoveFromWishListAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchWishListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchWishListAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            wish_list_obj = WishList.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
            unit_wish_list_objs = UnitWishList.objects.filter(wish_list=wish_list_obj)
            unit_wish_list = []
            for unit_wish_list_obj in unit_wish_list_objs:
                temp_dict = {}
                temp_dict["uuid"] = unit_wish_list_obj.uuid
                temp_dict["price"] = unit_wish_list_obj.product.get_actual_price_for_customer(dealshub_user_obj)
                temp_dict["currency"] = unit_wish_list_obj.product.get_currency()
                temp_dict["dateCreated"] = unit_wish_list_obj.get_date_created()
                temp_dict["productName"] = unit_wish_list_obj.product.get_name()
                temp_dict["productImageUrl"] = unit_wish_list_obj.product.get_display_image_url()
                temp_dict["productUuid"] = unit_wish_list_obj.product.uuid
                temp_dict["brand"] = unit_wish_list_obj.product.get_brand()
                temp_dict["isStockAvailable"] = unit_wish_list_obj.product.stock > 0
                unit_wish_list.append(temp_dict)

            response["unitWishList"] = unit_wish_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchWishListAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchShippingAddressListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchShippingAddressListAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            user = request.user

            location_group_uuid = data["locationGroupUuid"]

            address_objs = Address.objects.filter(is_shipping=True, is_deleted=False, user=user, location_group__uuid=location_group_uuid)

            address_list = []
            for address_obj in address_objs:
                temp_dict = {}
                temp_dict['firstName'] = address_obj.first_name
                temp_dict['lastName'] = address_obj.last_name
                temp_dict['line1'] = json.loads(address_obj.address_lines)[0]
                temp_dict['line2'] = json.loads(address_obj.address_lines)[1]
                temp_dict['line3'] = json.loads(address_obj.address_lines)[2]
                temp_dict['line4'] = json.loads(address_obj.address_lines)[3]
                temp_dict['state'] = address_obj.state
                temp_dict['country'] = address_obj.get_country()
                temp_dict['postcode'] = address_obj.postcode
                temp_dict['contactNumber'] = str(address_obj.contact_number)
                temp_dict['tag'] = str(address_obj.tag)
                temp_dict['emirates'] = str(address_obj.emirates)
                temp_dict['uuid'] = str(address_obj.uuid)

                address_list.append(temp_dict)

            response['addressList'] = address_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchShippingAddressListAPI: %s at %s",e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class EditShippingAddressAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("EditAddressAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            uuid = data["uuid"]

            address_obj = Address.objects.get(uuid=uuid)
            address_lines = json.loads(address_obj.address_lines)

            first_name = data["firstName"]
            last_name = data.get("lastName", "")
            line1 = data["line1"]
            line2 = data["line2"]
                
            address_lines[0] = line1
            address_lines[1] = line2

            tag = data.get("tag", "Home")

            emirates = data.get("emirates", "")

            address_obj = Address.objects.get(uuid=uuid)
            address_obj.first_name = first_name
            address_obj.last_name = last_name
            address_obj.address_lines = json.dumps(address_lines)
            address_obj.tag = tag
            address_obj.emirates = emirates
            address_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("EditAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CreateShippingAddressAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("CreateShippingAddressAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            first_name = data["firstName"]
            last_name = data.get("lastName", "")
            line1 = data["line1"]
            line2 = data["line2"]
            line3 = ""
            line4 = location_group_obj.location.name
            address_lines = json.dumps([line1, line2, line3, line4])
            state = ""
            postcode = ""
            emirates = data.get("emirates", "")
            if postcode==None:
                postcode = ""
            contact_number = dealshub_user_obj.contact_number
            tag = data.get("tag", "")
            if tag==None:
                tag = ""

            if dealshub_user_obj.first_name=="":
                dealshub_user_obj.first_name = first_name
                dealshub_user_obj.last_name = last_name
                dealshub_user_obj.save()

            address_obj = Address.objects.create(first_name=first_name, last_name=last_name, address_lines=address_lines, state=state, postcode=postcode, contact_number=contact_number, user=dealshub_user_obj, tag=tag, location_group=location_group_obj, emirates=emirates)

            response["uuid"] = address_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateShippingAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CreateOfflineShippingAddressAPI(APIView):
    
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("CreateOfflineShippingAddressAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            username = data["username"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            if DealsHubUser.objects.filter(username=username).exists():

                dealshub_user_obj = DealsHubUser.objects.get(username=username)
                first_name = str(dealshub_user_obj.first_name)
                last_name = str(dealshub_user_obj.last_name)
                line1 = data["line1"]
                line2 = data["line2"]
                line3 = data["line3"]
                line4 = data["line4"]
                address_lines = json.dumps([line1, line2, line3, line4])
                state = data["state"]
                postcode = data["postcode"]
                emirates = data.get("emirates", "")
                if postcode==None:
                    postcode = ""
                contact_number = dealshub_user_obj.contact_number
                tag = data.get("tag", "")
                if tag==None:
                    tag = ""

                address_obj = Address.objects.create(user=dealshub_user_obj,first_name=first_name, last_name=last_name, address_lines=address_lines, state=state, postcode=postcode, contact_number=contact_number, tag=tag, location_group=location_group_obj, emirates=emirates)

                response["uuid"] = address_obj.uuid
                response['status'] = 200
            else:
                response["status"] = 409

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateOfflineShippingAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DeleteShippingAddressAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteShippingAddressAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            uuid = data["uuid"]

            address_obj = Address.objects.get(uuid=uuid)
            address_obj.is_deleted = True
            address_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteShippingAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddToCartAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddToCartAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            product_uuid = data["productUuid"]
            quantity = int(data["quantity"])

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            dealshub_product_obj = DealsHubProduct.objects.get(uuid=product_uuid)

            if dealshub_product_obj.location_group!=location_group_obj:
                response["status"] = 403
                logger.error("AddToCartAPI: Product does not exist in LocationGroup!")
                return Response(data=response)


            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
            unit_cart_obj = None
            if UnitCart.objects.filter(cart=cart_obj, product__uuid=product_uuid).exists()==True:
                unit_cart_obj = UnitCart.objects.get(cart=cart_obj, product__uuid=product_uuid)
                unit_cart_obj.quantity += quantity
                unit_cart_obj.save()
            else:
                unit_cart_obj = UnitCart.objects.create(cart=cart_obj, product=dealshub_product_obj, quantity=quantity)

            update_cart_bill(cart_obj)

            response["price"] = dealshub_product_obj.get_actual_price_for_customer(dealshub_user_obj)
            response["showNote"] = dealshub_product_obj.is_promo_restriction_note_required(dealshub_user_obj)

            subtotal = cart_obj.get_subtotal()
            
            delivery_fee = cart_obj.get_delivery_fee()
            total_amount = cart_obj.get_total_amount()
            vat = cart_obj.get_vat()

            delivery_fee_with_cod = cart_obj.get_delivery_fee(cod=True)
            total_amount_with_cod = cart_obj.get_total_amount(cod=True)
            vat_with_cod = cart_obj.get_vat(cod=True)


            is_voucher_applied = cart_obj.voucher!=None
            voucher_discount = 0
            voucher_code = ""
            if is_voucher_applied:
                voucher_discount = cart_obj.voucher.get_voucher_discount(subtotal)
                voucher_code = cart_obj.voucher.voucher_code
                if cart_obj.voucher.voucher_type=="SD":
                    delivery_fee = delivery_fee_with_cod
                    voucher_discount = delivery_fee


            response["currency"] = cart_obj.get_currency()
            response["subtotal"] = subtotal

            response["cardBill"] = {
                "vat": vat,
                "toPay": total_amount,
                "delivery_fee": delivery_fee,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }
            response["codBill"] = {
                "vat": vat_with_cod,
                "toPay": total_amount_with_cod,
                "delivery_fee": delivery_fee_with_cod,
                "codCharge": cart_obj.location_group.cod_charge,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }

            response["unitCartUuid"] = unit_cart_obj.uuid
            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddToCartAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class AddToFastCartAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddToFastCartAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            product_uuid = data["productUuid"]
            quantity = 1

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            dealshub_product_obj = DealsHubProduct.objects.get(uuid=product_uuid)

            if dealshub_product_obj.location_group!=location_group_obj:
                response["status"] = 403
                logger.error("AddToCartAPI: Product does not exist in LocationGroup!")
                return Response(data=response)


            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            fast_cart_obj = FastCart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
            
            fast_cart_obj.product = dealshub_product_obj
            fast_cart_obj.quantity = quantity
            fast_cart_obj.save()

            update_fast_cart_bill(fast_cart_obj)

            response["price"] = dealshub_product_obj.get_actual_price_for_customer(dealshub_user_obj)
            response["showNote"] = dealshub_product_obj.is_promo_restriction_note_required(dealshub_user_obj)

            subtotal = fast_cart_obj.get_subtotal()
            
            delivery_fee = fast_cart_obj.get_delivery_fee()
            total_amount = fast_cart_obj.get_total_amount()
            vat = fast_cart_obj.get_vat()

            delivery_fee_with_cod = fast_cart_obj.get_delivery_fee(cod=True)
            total_amount_with_cod = fast_cart_obj.get_total_amount(cod=True)
            vat_with_cod = fast_cart_obj.get_vat(cod=True)


            is_voucher_applied = fast_cart_obj.voucher!=None
            voucher_discount = 0
            voucher_code = ""
            if is_voucher_applied:
                voucher_discount = fast_cart_obj.voucher.get_voucher_discount(subtotal)
                voucher_code = fast_cart_obj.voucher.voucher_code
                if fast_cart_obj.voucher.voucher_type=="SD":
                    delivery_fee = delivery_fee_with_cod
                    voucher_discount = delivery_fee


            response["currency"] = fast_cart_obj.get_currency()
            response["subtotal"] = subtotal

            response["cardBill"] = {
                "vat": vat,
                "toPay": total_amount,
                "delivery_fee": delivery_fee,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }
            response["codBill"] = {
                "vat": vat_with_cod,
                "toPay": total_amount_with_cod,
                "delivery_fee": delivery_fee_with_cod,
                "codCharge": fast_cart_obj.location_group.cod_charge,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }

            response["unitCartUuid"] = fast_cart_obj.uuid
            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddToFastCartAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class AddToOfflineCartAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddToOfflineCartAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            product_uuid = data["productUuid"]
            quantity = int(data["quantity"])
            username = data["username"]

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            dealshub_product_obj = DealsHubProduct.objects.get(uuid=product_uuid)

            if dealshub_product_obj.location_group!=location_group_obj:
                response["status"] = 403
                logger.error("AddToOfflineCartAPI: Product does not exist in LocationGroup!")
                return Response(data=response)


            dealshub_user_obj = DealsHubUser.objects.get(username=username)
            cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
            unit_cart_obj = None
            if UnitCart.objects.filter(cart=cart_obj, product__uuid=product_uuid).exists()==True:
                unit_cart_obj = UnitCart.objects.get(cart=cart_obj, product__uuid=product_uuid)
                unit_cart_obj.quantity += quantity
                unit_cart_obj.save()
            else:
                unit_cart_obj = UnitCart.objects.create(cart=cart_obj, product=dealshub_product_obj, quantity=quantity)

            update_cart_bill(cart_obj)

            subtotal = cart_obj.get_subtotal()

            delivery_fee = cart_obj.get_delivery_fee()
            total_amount = cart_obj.get_total_amount()
            vat = cart_obj.get_vat()

            delivery_fee_with_cod = cart_obj.get_delivery_fee(cod=True, offline=True)
            total_amount_with_cod = cart_obj.get_total_amount(cod=True, offline=True)
            vat_with_cod = cart_obj.get_vat(cod=True, offline=True)


            is_voucher_applied = cart_obj.voucher!=None
            voucher_discount = 0
            voucher_code = ""
            if is_voucher_applied:
                voucher_discount = cart_obj.voucher.get_voucher_discount(subtotal)
                voucher_code = cart_obj.voucher.voucher_code
                if cart_obj.voucher.voucher_type=="SD":
                    delivery_fee = delivery_fee_with_cod
                    voucher_discount = delivery_fee


            response["currency"] = cart_obj.get_currency()
            response["subtotal"] = subtotal

            response["cardBill"] = {
                "vat": vat,
                "toPay": total_amount,
                "delivery_fee": delivery_fee,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }
            response["codBill"] = {
                "vat": vat_with_cod,
                "toPay": total_amount_with_cod,
                "delivery_fee": delivery_fee_with_cod,
                "codCharge": cart_obj.location_group.cod_charge,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }

            response["unitCartUuid"] = unit_cart_obj.uuid
            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddToOfflineCartAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchCartDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchCartDetailsAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
            unit_cart_objs = UnitCart.objects.filter(cart=cart_obj)
            unit_cart_list = []
            for unit_cart_obj in unit_cart_objs:
                temp_dict = {}
                temp_dict["uuid"] = unit_cart_obj.uuid
                temp_dict["quantity"] = unit_cart_obj.quantity
                temp_dict["price"] = unit_cart_obj.product.get_actual_price_for_customer(dealshub_user_obj)
                temp_dict["showNote"] = unit_cart_obj.product.is_promo_restriction_note_required(dealshub_user_obj)
                temp_dict["stock"] = unit_cart_obj.product.stock
                temp_dict["allowedQty"] = unit_cart_obj.product.get_allowed_qty()
                temp_dict["currency"] = unit_cart_obj.product.get_currency()
                temp_dict["dateCreated"] = unit_cart_obj.get_date_created()
                temp_dict["productName"] = unit_cart_obj.product.get_name()
                temp_dict["productImageUrl"] = unit_cart_obj.product.get_display_image_url()
                temp_dict["productUuid"] = unit_cart_obj.product.uuid
                temp_dict["brand"] = unit_cart_obj.product.get_brand()
                temp_dict["isStockAvailable"] = unit_cart_obj.product.stock > 0
                unit_cart_list.append(temp_dict)

            update_cart_bill(cart_obj)

            subtotal = cart_obj.get_subtotal()
            
            delivery_fee = cart_obj.get_delivery_fee()
            total_amount = cart_obj.get_total_amount()
            vat = cart_obj.get_vat()

            delivery_fee_with_cod = cart_obj.get_delivery_fee(cod=True)
            total_amount_with_cod = cart_obj.get_total_amount(cod=True)
            vat_with_cod = cart_obj.get_vat(cod=True)

            is_voucher_applied = cart_obj.voucher!=None
            voucher_discount = 0
            voucher_code = ""
            if is_voucher_applied:
                voucher_discount = cart_obj.voucher.get_voucher_discount(subtotal)
                voucher_code = cart_obj.voucher.voucher_code
                if cart_obj.voucher.voucher_type=="SD":
                    delivery_fee = delivery_fee_with_cod
                    voucher_discount = delivery_fee

            response["currency"] = cart_obj.get_currency()
            response["subtotal"] = subtotal

            response["cardBill"] = {
                "vat": vat,
                "toPay": total_amount,
                "delivery_fee": delivery_fee,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }
            response["codBill"] = {
                "vat": vat_with_cod,
                "toPay": total_amount_with_cod,
                "delivery_fee": delivery_fee_with_cod,
                "codCharge": cart_obj.location_group.cod_charge,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }
            
            response["unitCartList"] = unit_cart_list
            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchOfflineCartDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchOfflineCartDetailsAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            username = data["username"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            dealshub_user_obj = DealsHubUser.objects.get(username=username)
            cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
            unit_cart_objs = UnitCart.objects.filter(cart=cart_obj)
            unit_cart_list = []
            for unit_cart_obj in unit_cart_objs:
                temp_dict = {}
                temp_dict["uuid"] = unit_cart_obj.uuid
                temp_dict["quantity"] = unit_cart_obj.quantity
                temp_dict["price"] = unit_cart_obj.product.get_actual_price_for_customer(dealshub_user_obj)
                temp_dict["showNote"] = unit_cart_obj.product.is_promo_restriction_note_required(dealshub_user_obj)
                temp_dict["currency"] = unit_cart_obj.product.get_currency()
                temp_dict["dateCreated"] = unit_cart_obj.get_date_created()
                temp_dict["productName"] = unit_cart_obj.product.get_name()
                temp_dict["productImageUrl"] = unit_cart_obj.product.get_display_image_url()
                temp_dict["productUuid"] = unit_cart_obj.product.uuid
                temp_dict["brand"] = unit_cart_obj.product.get_brand()
                temp_dict["isStockAvailable"] = unit_cart_obj.product.stock > 0
                unit_cart_list.append(temp_dict)

            update_cart_bill(cart_obj)

            subtotal = cart_obj.get_subtotal()

            delivery_fee = cart_obj.get_delivery_fee()
            total_amount = cart_obj.get_total_amount()
            vat = cart_obj.get_vat()

            delivery_fee_with_cod = cart_obj.get_delivery_fee(cod=True, offline=True)
            total_amount_with_cod = cart_obj.get_total_amount(cod=True, offline=True)
            vat_with_cod = cart_obj.get_vat(cod=True, offline=True)

            is_voucher_applied = cart_obj.voucher!=None
            voucher_discount = 0
            voucher_code = ""
            if is_voucher_applied:
                voucher_discount = cart_obj.voucher.get_voucher_discount(subtotal)
                voucher_code = cart_obj.voucher.voucher_code
                if cart_obj.voucher.voucher_type=="SD":
                    delivery_fee = delivery_fee_with_cod
                    voucher_discount = delivery_fee

            response["currency"] = cart_obj.get_currency()
            response["subtotal"] = subtotal

            response["cardBill"] = {
                "vat": vat,
                "toPay": total_amount,
                "delivery_fee": delivery_fee,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }
            response["codBill"] = {
                "vat": vat_with_cod,
                "toPay": total_amount_with_cod,
                "delivery_fee": delivery_fee_with_cod,
                "codCharge": cart_obj.location_group.cod_charge,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }

            response["unitCartList"] = unit_cart_list
            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOfflineCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UpdateCartDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateCartDetailsAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            unit_cart_uuid = data["unitCartUuid"]
            quantity = int(data["quantity"])
            is_order_offline = data.get("is_order_offline", False)

            unit_cart_obj = UnitCart.objects.get(uuid=unit_cart_uuid)
            unit_cart_obj.quantity = quantity
            unit_cart_obj.save()

            update_cart_bill(unit_cart_obj.cart)

            cart_obj = unit_cart_obj.cart

            subtotal = cart_obj.get_subtotal()
            
            delivery_fee = cart_obj.get_delivery_fee()
            total_amount = cart_obj.get_total_amount()
            vat = cart_obj.get_vat()

            delivery_fee_with_cod = cart_obj.get_delivery_fee(cod=True, offline=is_order_offline)
            total_amount_with_cod = cart_obj.get_total_amount(cod=True, offline=is_order_offline)
            vat_with_cod = cart_obj.get_vat(cod=True, offline=is_order_offline)

            is_voucher_applied = cart_obj.voucher!=None
            voucher_discount = 0
            voucher_code = ""
            if is_voucher_applied:
                voucher_discount = cart_obj.voucher.get_voucher_discount(subtotal)
                voucher_code = cart_obj.voucher.voucher_code
                if cart_obj.voucher.voucher_type=="SD":
                    delivery_fee = delivery_fee_with_cod
                    voucher_discount = delivery_fee

            response["currency"] = cart_obj.get_currency()
            response["subtotal"] = subtotal

            response["cardBill"] = {
                "vat": vat,
                "toPay": total_amount,
                "delivery_fee": delivery_fee,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }
            response["codBill"] = {
                "vat": vat_with_cod,
                "toPay": total_amount_with_cod,
                "delivery_fee": delivery_fee_with_cod,
                "codCharge": cart_obj.location_group.cod_charge,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class BulkUpdateCartDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("BulkUpdateCartDetailsAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            unit_cart_list = data["unitCartList"]
            location_group_uuid = data["locationGroupUuid"]
            
            for unit_cart in unit_cart_list:
                unit_cart_obj = UnitCart.objects.get(uuid=unit_cart["uuid"])
                if int(unit_cart["quantity"])==0:
                    unit_cart_obj.delete()
                else:
                    unit_cart_obj.quantity = unit_cart["quantity"]
                    unit_cart_obj.save()            

            cart_obj = Cart.objects.get(owner__username=request.user.username, location_group__uuid=location_group_uuid)

            update_cart_bill(cart_obj)

            subtotal = cart_obj.get_subtotal()
            
            delivery_fee = cart_obj.get_delivery_fee()
            total_amount = cart_obj.get_total_amount()
            vat = cart_obj.get_vat()

            delivery_fee_with_cod = cart_obj.get_delivery_fee(cod=True, offline=False)
            total_amount_with_cod = cart_obj.get_total_amount(cod=True, offline=False)
            vat_with_cod = cart_obj.get_vat(cod=True, offline=False)

            is_voucher_applied = cart_obj.voucher!=None
            voucher_discount = 0
            voucher_code = ""
            if is_voucher_applied:
                voucher_discount = cart_obj.voucher.get_voucher_discount(subtotal)
                voucher_code = cart_obj.voucher.voucher_code
                if cart_obj.voucher.voucher_type=="SD":
                    delivery_fee = delivery_fee_with_cod
                    voucher_discount = delivery_fee

            response["currency"] = cart_obj.get_currency()
            response["subtotal"] = subtotal

            response["cardBill"] = {
                "vat": vat,
                "toPay": total_amount,
                "delivery_fee": delivery_fee,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }
            response["codBill"] = {
                "vat": vat_with_cod,
                "toPay": total_amount_with_cod,
                "delivery_fee": delivery_fee_with_cod,
                "codCharge": cart_obj.location_group.cod_charge,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("BulkUpdateCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class UpdateFastCartDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateFastCartDetailsAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            fast_cart_uuid = data["fastCartUuid"]
            quantity = int(data["quantity"])

            fast_cart_obj = FastCart.objects.get(uuid=fast_cart_uuid)
            fast_cart_obj.quantity = quantity
            fast_cart_obj.save()

            update_fast_cart_bill(fast_cart_obj)

            subtotal = fast_cart_obj.get_subtotal()
            
            delivery_fee = fast_cart_obj.get_delivery_fee()
            total_amount = fast_cart_obj.get_total_amount()
            vat = fast_cart_obj.get_vat()

            delivery_fee_with_cod = fast_cart_obj.get_delivery_fee(cod=True)
            total_amount_with_cod = fast_cart_obj.get_total_amount(cod=True)
            vat_with_cod = fast_cart_obj.get_vat(cod=True)

            is_voucher_applied = fast_cart_obj.voucher!=None
            voucher_discount = 0
            voucher_code = ""
            if is_voucher_applied:
                voucher_discount = fast_cart_obj.voucher.get_voucher_discount(subtotal)
                voucher_code = fast_cart_obj.voucher.voucher_code
                if fast_cart_obj.voucher.voucher_type=="SD":
                    delivery_fee = delivery_fee_with_cod
                    voucher_discount = delivery_fee

            response["currency"] = fast_cart_obj.get_currency()
            response["subtotal"] = subtotal

            response["cardBill"] = {
                "vat": vat,
                "toPay": total_amount,
                "delivery_fee": delivery_fee,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }
            response["codBill"] = {
                "vat": vat_with_cod,
                "toPay": total_amount_with_cod,
                "delivery_fee": delivery_fee_with_cod,
                "codCharge": fast_cart_obj.location_group.cod_charge,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateFastCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class RemoveFromCartAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("RemoveFromCartAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            unit_cart_uuid = data["unitCartUuid"]
            
            unit_cart_obj = UnitCart.objects.get(uuid=unit_cart_uuid)
            cart_obj = unit_cart_obj.cart
            unit_cart_obj.delete()

            update_cart_bill(cart_obj)

            subtotal = cart_obj.get_subtotal()
            
            delivery_fee = cart_obj.get_delivery_fee()
            total_amount = cart_obj.get_total_amount()
            vat = cart_obj.get_vat()

            delivery_fee_with_cod = cart_obj.get_delivery_fee(cod=True)
            total_amount_with_cod = cart_obj.get_total_amount(cod=True)
            vat_with_cod = cart_obj.get_vat(cod=True)

            is_voucher_applied = cart_obj.voucher!=None
            voucher_discount = 0
            voucher_code = ""
            if is_voucher_applied:
                voucher_discount = cart_obj.voucher.get_voucher_discount(subtotal)
                voucher_code = cart_obj.voucher.voucher_code
                if cart_obj.voucher.voucher_type=="SD":
                    delivery_fee = delivery_fee_with_cod
                    voucher_discount = delivery_fee

            response["currency"] = cart_obj.get_currency()
            response["subtotal"] = subtotal

            response["cardBill"] = {
                "vat": vat,
                "toPay": total_amount,
                "delivery_fee": delivery_fee,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }
            response["codBill"] = {
                "vat": vat_with_cod,
                "toPay": total_amount_with_cod,
                "delivery_fee": delivery_fee_with_cod,
                "codCharge": cart_obj.location_group.cod_charge,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("RemoveFromCartAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class SelectAddressAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SelectAddressAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            address_uuid = data["addressUuid"]

            address_obj = Address.objects.get(uuid=address_uuid)
            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            if data.get("is_fast_cart", False)==True:
                fast_cart_obj = FastCart.objects.get(owner=dealshub_user_obj, location_group=address_obj.location_group)
                fast_cart_obj.shipping_address = address_obj
                fast_cart_obj.save()
            else:
                cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=address_obj.location_group)
                cart_obj.shipping_address = address_obj
                cart_obj.save()

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SelectAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class SelectOfflineAddressAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SelectOfflineAddressAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            address_uuid = data["addressUuid"]
            username = data["username"]

            address_obj = Address.objects.get(uuid=address_uuid)
            dealshub_user_obj = DealsHubUser.objects.get(username=username)
            cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=address_obj.location_group)
            
            cart_obj.shipping_address = address_obj
            cart_obj.save()

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SelectOfflineAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class SelectPaymentModeAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SelectPaymentModeAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            payment_mode = data["paymentMode"]

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)

            cart_obj.payment_mode = payment_mode
            cart_obj.save()

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SelectPaymentModeAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchActiveOrderDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchActiveOrderDetailsAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)

            update_cart_bill(cart_obj)
            
            if cart_obj.shipping_address==None and Address.objects.filter(is_deleted=False, user=request.user, location_group=location_group_obj).count()>0:
                cart_obj.shipping_address = Address.objects.filter(is_deleted=False, user=request.user, location_group=location_group_obj)[0]
                cart_obj.save()

            address_obj = cart_obj.shipping_address
            payment_mode = cart_obj.payment_mode
            voucher_obj = cart_obj.voucher
            is_voucher_applied = voucher_obj is not None

            response["uuid"] = cart_obj.uuid
            response["paymentMode"] = payment_mode
            response["isVoucherApplied"] = is_voucher_applied
            if is_voucher_applied:
                response["voucherCode"] = voucher_obj.voucher_code

            if address_obj==None:
                response["shippingAddress"] = {}
            else:
                response["shippingAddress"] = {
                    "firstName": address_obj.first_name,
                    "lastName": address_obj.last_name,
                    "line1": json.loads(address_obj.address_lines)[0],
                    "line2": json.loads(address_obj.address_lines)[1],
                    "line3": json.loads(address_obj.address_lines)[2],
                    "line4": json.loads(address_obj.address_lines)[3],
                    "state": address_obj.state,
                    "country": address_obj.get_country(),
                    "postcode": address_obj.postcode,
                    "contactNumber": str(address_obj.contact_number),
                    "tag": str(address_obj.tag),
                    "uuid": str(address_obj.uuid)
                }

            unit_cart_list = []
            unit_cart_objs = UnitCart.objects.filter(cart=cart_obj)

            for unit_cart_obj in unit_cart_objs:
                temp_dict = {}
                temp_dict["uuid"] = unit_cart_obj.uuid
                temp_dict["quantity"] = unit_cart_obj.quantity
                temp_dict["price"] = unit_cart_obj.product.get_actual_price_for_customer(dealshub_user_obj)
                temp_dict["showNote"] = unit_cart_obj.product.is_promo_restriction_note_required(dealshub_user_obj)
                temp_dict["currency"] = unit_cart_obj.product.get_currency()
                temp_dict["dateCreated"] = unit_cart_obj.get_date_created()
                temp_dict["productName"] = unit_cart_obj.product.get_name()
                temp_dict["productImageUrl"] = unit_cart_obj.product.get_display_image_url()
                temp_dict["productUuid"] = unit_cart_obj.product.uuid
                temp_dict["isStockAvailable"] = unit_cart_obj.product.stock > 0
                unit_cart_list.append(temp_dict)

            is_cod_allowed = cart_obj.is_cod_allowed()
            delivery_fee = cart_obj.get_delivery_fee()
            total_amount = cart_obj.get_total_amount()
            vat = cart_obj.get_vat()

            response["deliveryFee"] = delivery_fee
            response["vat"] = vat
            response["toPay"] = total_amount

            response["unitCartList"] = unit_cart_list

            response["contactVerified"] = dealshub_user_obj.contact_verified
            response["contactNumber"] = dealshub_user_obj.contact_number
            response["emailId"] = dealshub_user_obj.email

            response["isCodAllowed"] = is_cod_allowed

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchActiveOrderDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class PlaceOrderAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("PlaceOrderAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]

            is_fast_cart = data.get("is_fast_cart", False)

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            order_obj = None
            if is_fast_cart==False:
                cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)

                try:
                    if cart_obj.shipping_address==None:
                        address_obj = Address.objects.filter(user=dealshub_user_obj)[0]
                        cart_obj.shipping_address = address_obj
                        cart_obj.save()
                except Exception as e:
                    pass

                if location_group_obj.is_voucher_allowed_on_cod==False:
                    cart_obj.voucher = None
                    cart_obj.save()

                update_cart_bill(cart_obj)

                unit_cart_objs = UnitCart.objects.filter(cart=cart_obj)

                # Check if COD is allowed
                is_cod_allowed = cart_obj.is_cod_allowed()
                if is_cod_allowed==False:
                    response["status"] = 403
                    logger.error("PlaceOrderAPI: COD not allowed!")
                    return Response(data=response)

                cart_obj.to_pay += cart_obj.location_group.cod_charge
                cart_obj.save()

                order_obj = Order.objects.create(owner=cart_obj.owner,
                                                 shipping_address=cart_obj.shipping_address,
                                                 to_pay=cart_obj.to_pay,
                                                 order_placed_date=timezone.now(),
                                                 voucher=cart_obj.voucher,
                                                 location_group=cart_obj.location_group,
                                                 delivery_fee=cart_obj.get_delivery_fee(),
                                                 cod_charge=cart_obj.location_group.cod_charge)

                for unit_cart_obj in unit_cart_objs:
                    unit_order_obj = UnitOrder.objects.create(order=order_obj,
                                                              product=unit_cart_obj.product,
                                                              quantity=unit_cart_obj.quantity,
                                                              price=unit_cart_obj.product.get_actual_price_for_customer(dealshub_user_obj))
                    UnitOrderStatus.objects.create(unit_order=unit_order_obj)

                # Cart gets empty
                for unit_cart_obj in unit_cart_objs:
                    unit_cart_obj.delete()

                # cart_obj points to None
                cart_obj.shipping_address = None
                cart_obj.voucher = None
                cart_obj.to_pay = 0
                cart_obj.merchant_reference = ""
                cart_obj.payment_info = "{}"
                cart_obj.save()
            else:
                fast_cart_obj = FastCart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)

                try:
                    if fast_cart_obj.shipping_address==None:
                        address_obj = Address.objects.filter(user=dealshub_user_obj)[0]
                        fast_cart_obj.shipping_address = address_obj
                        fast_cart_obj.save()
                except Exception as e:
                    pass

                if location_group_obj.is_voucher_allowed_on_cod==False:
                    fast_cart_obj.voucher = None
                    fast_cart_obj.save()

                update_fast_cart_bill(fast_cart_obj)

                # Check if COD is allowed
                is_cod_allowed = fast_cart_obj.is_cod_allowed()
                if is_cod_allowed==False:
                    response["status"] = 403
                    logger.error("PlaceOrderAPI: COD not allowed!")
                    return Response(data=response)

                fast_cart_obj.to_pay += fast_cart_obj.location_group.cod_charge
                fast_cart_obj.save()

                order_obj = Order.objects.create(owner=fast_cart_obj.owner,
                                                 shipping_address=fast_cart_obj.shipping_address,
                                                 to_pay=fast_cart_obj.to_pay,
                                                 order_placed_date=timezone.now(),
                                                 voucher=fast_cart_obj.voucher,
                                                 location_group=fast_cart_obj.location_group,
                                                 delivery_fee=fast_cart_obj.get_delivery_fee(),
                                                 cod_charge=fast_cart_obj.location_group.cod_charge)

                unit_order_obj = UnitOrder.objects.create(order=order_obj,
                                                          product=fast_cart_obj.product,
                                                          quantity=fast_cart_obj.quantity,
                                                          price=fast_cart_obj.product.get_actual_price_for_customer(dealshub_user_obj))
                UnitOrderStatus.objects.create(unit_order=unit_order_obj)

                # cart_obj points to None
                fast_cart_obj.shipping_address = None
                fast_cart_obj.voucher = None
                fast_cart_obj.to_pay = 0
                fast_cart_obj.merchant_reference = ""
                fast_cart_obj.payment_info = "{}"
                fast_cart_obj.product = None
                fast_cart_obj.save()


            # Trigger Email
            try:
                p1 = threading.Thread(target=send_order_confirmation_mail, args=(order_obj,))
                p1.start()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("PlaceOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))

            # Refresh Stock
            refresh_stock(order_obj)

            response["purchase"] = calculate_gtm(order_obj)

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PlaceOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class PlaceOfflineOrderAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("PlaceOfflineOrderAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            username = data["username"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            dealshub_user_obj = DealsHubUser.objects.get(username=username)
            cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)

            update_cart_bill(cart_obj)

            unit_cart_objs = UnitCart.objects.filter(cart=cart_obj)

            # Check if COD is allowed
            # is_cod_allowed = True
            # if is_cod_allowed==False:
            #     response["status"] = 403
            #     logger.error("PlaceOfflineOrderAPI: COD not allowed!")
            #     return Response(data=response)

            cart_obj.to_pay += cart_obj.location_group.cod_charge
            cart_obj.save()

            order_obj = Order.objects.create(owner=cart_obj.owner,
                                             shipping_address=cart_obj.shipping_address,
                                             to_pay=cart_obj.to_pay,
                                             order_placed_date=timezone.now(),
                                             voucher=cart_obj.voucher,
                                             is_order_offline = True,
                                             location_group=cart_obj.location_group,
                                             delivery_fee=cart_obj.get_delivery_fee(),
                                             cod_charge=cart_obj.location_group.cod_charge)

            for unit_cart_obj in unit_cart_objs:
                unit_order_obj = UnitOrder.objects.create(order=order_obj,
                                                          product=unit_cart_obj.product,
                                                          quantity=unit_cart_obj.quantity,
                                                          price=unit_cart_obj.product.get_actual_price_for_customer(dealshub_user_obj))
                UnitOrderStatus.objects.create(unit_order=unit_order_obj)

            # Cart gets empty
            for unit_cart_obj in unit_cart_objs:
                unit_cart_obj.delete()

            # cart_obj points to None
            cart_obj.shipping_address = None
            cart_obj.voucher = None
            cart_obj.to_pay = 0
            cart_obj.merchant_reference = ""
            cart_obj.payment_info = "{}"
            cart_obj.save()

            # Trigger Email
            try:
                p1 = threading.Thread(target=send_order_confirmation_mail, args=(order_obj,))
                p1.start()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("PlaceOfflineOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))

            # Refresh Stock
            refresh_stock(order_obj)

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PlaceOfflineOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CancelOrderAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("CancelOrderAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CancelOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class FetchOrderListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchOrderListAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            order_list = []
            order_objs = Order.objects.filter(owner=dealshub_user_obj).order_by('-pk')
            for order_obj in order_objs:
                try:
                    voucher_obj = order_obj.voucher
                    is_voucher_applied = voucher_obj is not None
                    temp_dict = {}
                    temp_dict["dateCreated"] = order_obj.get_date_created()
                    temp_dict["paymentMode"] = order_obj.payment_mode
                    temp_dict["paymentStatus"] = order_obj.payment_status
                    temp_dict["customerName"] = order_obj.owner.first_name
                    temp_dict["bundleId"] = order_obj.bundleid
                    temp_dict["uuid"] = order_obj.uuid
                    temp_dict["isVoucherApplied"] = is_voucher_applied
                    if is_voucher_applied:
                        temp_dict["voucherCode"] = voucher_obj.voucher_code
                    temp_dict["shippingAddress"] = order_obj.shipping_address.get_shipping_address()

                    unit_order_objs = UnitOrder.objects.filter(order=order_obj)
                    unit_order_list = []
                    for unit_order_obj in unit_order_objs:
                        temp_dict2 = {}
                        temp_dict2["orderId"] = unit_order_obj.orderid
                        temp_dict2["uuid"] = unit_order_obj.uuid
                        temp_dict2["currentStatus"] = unit_order_obj.current_status
                        temp_dict2["quantity"] = unit_order_obj.quantity
                        temp_dict2["price"] = unit_order_obj.price
                        temp_dict2["currency"] = unit_order_obj.product.get_currency()
                        temp_dict2["productName"] = unit_order_obj.product.get_name()
                        temp_dict2["productImageUrl"] = unit_order_obj.product.get_display_image_url()
                        unit_order_list.append(temp_dict2)
                    temp_dict["unitOrderList"] = unit_order_list
                    order_list.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchOrderListAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["orderList"] = order_list
            if len(order_list)==0:
                response["isOrderListEmpty"] = True
            else:
                response["isOrderListEmpty"] = False

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOrderListAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchOrderListAdminAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchOrderListAdminAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            page = data.get("page", 1)
            location_group_uuid = data["locationGroupUuid"]

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            order_objs = Order.objects.filter(location_group=location_group_obj).order_by('-pk')
            paginator = Paginator(order_objs, 20)
            total_orders = order_objs.count()
            order_objs = paginator.page(page)

            order_list = []
            
            for order_obj in order_objs:
                try:
                    voucher_obj = order_obj.voucher
                    is_voucher_applied = voucher_obj is not None
                    temp_dict = {}
                    temp_dict["dateCreated"] = order_obj.get_date_created()
                    temp_dict["paymentMode"] = order_obj.payment_mode
                    temp_dict["paymentStatus"] = order_obj.payment_status
                    temp_dict["customerName"] = order_obj.owner.first_name
                    temp_dict["bundleId"] = order_obj.bundleid
                    temp_dict["uuid"] = order_obj.uuid
                    temp_dict["isVoucherApplied"] = is_voucher_applied
                    if is_voucher_applied:
                        temp_dict["voucherCode"] = voucher_obj.voucher_code
                    temp_dict["shippingAddress"] = order_obj.shipping_address.get_shipping_address()

                    unit_order_objs = UnitOrder.objects.filter(order=order_obj)
                    unit_order_list = []
                    for unit_order_obj in unit_order_objs:
                        temp_dict2 = {}
                        temp_dict2["orderId"] = unit_order_obj.orderid
                        temp_dict2["uuid"] = unit_order_obj.uuid
                        temp_dict2["currentStatus"] = unit_order_obj.current_status
                        temp_dict2["quantity"] = unit_order_obj.quantity
                        temp_dict2["price"] = unit_order_obj.price
                        temp_dict2["currency"] = unit_order_obj.product.get_currency()
                        temp_dict2["productName"] = unit_order_obj.product.get_name()
                        temp_dict2["productImageUrl"] = unit_order_obj.product.get_display_image_url()
                        unit_order_list.append(temp_dict2)
                    temp_dict["unitOrderList"] = unit_order_list
                    order_list.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchOrderListAdminAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["orderList"] = order_list

            is_available = True

            if int(paginator.num_pages) == int(page):
                is_available = False

            response["is_available"] = is_available
            response["total_orders"] = unit_order_objs.count()
            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOrderListAdminAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchOrderDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchOrderDetailsAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            order_uuid = data["uuid"]

            order_obj = Order.objects.get(uuid=order_uuid)
            voucher_obj = order_obj.voucher
            is_voucher_applied = voucher_obj is not None

            unit_order_objs = UnitOrder.objects.filter(order=order_obj)

            enable_order_edit = False
            if order_obj.payment_status=="cod" and unit_order_objs.filter(current_status_admin="pending").exists():
                enable_order_edit = True

            response["enableOrderEdit"] = enable_order_edit
            response["bundleId"] = order_obj.bundleid 
            response["dateCreated"] = order_obj.get_date_created()
            response["paymentMode"] = order_obj.payment_mode
            response["paymentStatus"] = order_obj.payment_status
            response["customerName"] = order_obj.owner.first_name
            response["isVoucherApplied"] = is_voucher_applied
            if is_voucher_applied:
                response["voucherCode"] = voucher_obj.voucher_code
                response["voucherDiscount"] = voucher_obj.get_voucher_discount(order_obj.get_subtotal())

            address_obj = order_obj.shipping_address
            if address_obj==None:
                response["shippingAddress"] = {}
            else:
                response["shippingAddress"] = {
                    "firstName": address_obj.first_name,
                    "lastName": address_obj.last_name,
                    "line1": json.loads(address_obj.address_lines)[0],
                    "line2": json.loads(address_obj.address_lines)[1],
                    "line3": json.loads(address_obj.address_lines)[2],
                    "line4": json.loads(address_obj.address_lines)[3],
                    "emirates": address_obj.emirates,
                    "state": address_obj.state,
                    "country": address_obj.get_country(),
                    "postcode": address_obj.postcode,
                    "contactNumber": str(address_obj.contact_number),
                    "tag": str(address_obj.tag),
                    "uuid": str(address_obj.uuid)
                }

            unit_order_list = []
            for unit_order_obj in unit_order_objs:
                temp_dict = {}
                temp_dict["orderId"] = unit_order_obj.orderid
                temp_dict["uuid"] = unit_order_obj.uuid
                temp_dict["currentStatus"] = unit_order_obj.current_status
                temp_dict["quantity"] = unit_order_obj.quantity
                temp_dict["price"] = unit_order_obj.price
                temp_dict["currency"] = unit_order_obj.product.get_currency()
                temp_dict["productName"] = unit_order_obj.product.get_name()
                temp_dict["productImageUrl"] = unit_order_obj.product.get_display_image_url()
                temp_dict["sellerSku"] = unit_order_obj.product.get_seller_sku()
                temp_dict["productId"] = unit_order_obj.product.get_product_id()
                temp_dict["productUuid"] = unit_order_obj.product.uuid

                unit_order_status_list = []
                unit_order_status_objs = UnitOrderStatus.objects.filter(unit_order=unit_order_obj).order_by('date_created')
                for unit_order_status_obj in unit_order_status_objs:
                    temp_dict2 = {}
                    temp_dict2["customerStatus"] = unit_order_status_obj.status
                    temp_dict2["adminStatus"] = unit_order_status_obj.status_admin
                    temp_dict2["date"] = unit_order_status_obj.get_date_created()
                    temp_dict2["time"] = unit_order_status_obj.get_time_created()
                    temp_dict2["uuid"] = unit_order_status_obj.uuid
                    unit_order_status_list.append(temp_dict2)

                temp_dict["UnitOrderStatusList"] = unit_order_status_list
                unit_order_list.append(temp_dict)

            subtotal = order_obj.get_subtotal()
            delivery_fee = order_obj.get_delivery_fee()
            cod_fee = order_obj.get_cod_charge()
            to_pay = order_obj.to_pay
            vat = order_obj.get_vat()

            response["subtotal"] = str(subtotal)
            response["deliveryFee"] = str(delivery_fee)
            response["codFee"] = str(cod_fee)
            response["vat"] = str(vat)
            response["toPay"] = str(to_pay)

            response["unitOrderList"] = unit_order_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOrderDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

class CreateOfflineCustomerAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("CreateOfflineCustomerAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            contact_number = data["contact_number"]
            website_group_name = data["website_group_name"]
            first_name = data["first_name"]
            last_name = data.get("last_name", "")
            email = data["email"]

            digits = "0123456789"
            OTP = ""
            for i in range(6):
                OTP += digits[int(math.floor(random.random()*10))]

            website_group_obj = WebsiteGroup.objects.get(name=website_group_name)

            if DealsHubUser.objects.filter(username=contact_number+"-"+website_group_name).exists()==False:
                dealshub_user_obj = DealsHubUser.objects.create(username=contact_number+"-"+website_group_name, contact_number=contact_number, first_name=first_name, last_name=last_name, email=email, website_group=website_group_obj)
                dealshub_user_obj.set_password(OTP)
                dealshub_user_obj.verification_code = OTP
                dealshub_user_obj.save()

                for location_group_obj in LocationGroup.objects.filter(website_group=website_group_obj):
                    Cart.objects.create(owner=dealshub_user_obj, location_group=location_group_obj)
                    WishList.objects.create(owner=dealshub_user_obj, location_group=location_group_obj)
                    FastCart.objects.create(owner=dealshub_user_obj, location_group=location_group_obj)

                response["username"] = dealshub_user_obj.username
                response["status"] = 200
            else:
                response["status"] = 409

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateOfflineCustomerAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UpdateOfflineUserProfileAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateOfflineUserProfileAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            username = data["username"]
            email_id = data["emailId"]
            first_name = data["firstName"]
            last_name = data.get("lastName", "")
            contact_number = data["contactNumber"]

            if DealsHubUser.objects.filter(username=username).exists():
                dealshub_user_obj = DealsHubUser.objects.get(username=username)
                dealshub_user_obj.email = email_id
                dealshub_user_obj.first_name = first_name
                dealshub_user_obj.last_name = last_name
                dealshub_user_obj.contact_number = contact_number
                dealshub_user_obj.save()
                response['status'] = 200
            else:
                response['status'] = 404



        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateOfflineUserProfileAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SearchCustomerAutocompleteAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("SearchCustomerAutocompleteAPI: %s", str(data))

            search_string = data["searchString"]
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group

            user_objs = DealsHubUser.objects.filter(website_group=website_group_obj)

            user_objs = user_objs.filter(Q(first_name__icontains=search_string) | Q(contact_number__icontains=search_string))[:5]

            user_list = []
            for user_obj in user_objs:
                try:
                    temp_dict = {}
                    temp_dict["name"] = user_obj.first_name + " | " + user_obj.contact_number
                    temp_dict["username"] = user_obj.username
                    user_list.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.warning("SearchCustomerAutocompleteAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["userList"] = user_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchCustomerAutocompleteAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchOfflineUserProfileAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchOfflineUserProfileAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            username = data["username"]

            dealshub_user_obj = DealsHubUser.objects.get(username=username)

            response["firstName"] = dealshub_user_obj.first_name
            response["lastName"] = dealshub_user_obj.last_name
            response["emailId"] = dealshub_user_obj.email
            response["contactNumber"] = dealshub_user_obj.contact_number

            address_list = []
            if Address.objects.filter(user=dealshub_user_obj).exists():
                address_objs = Address.objects.filter(user=dealshub_user_obj)

                for address_obj in address_objs:
                    temp_dict = {}
                    temp_dict['firstName'] = address_obj.first_name
                    temp_dict['lastName'] = address_obj.last_name
                    temp_dict['line1'] = json.loads(address_obj.address_lines)[0]
                    temp_dict['line2'] = json.loads(address_obj.address_lines)[1]
                    temp_dict['line3'] = json.loads(address_obj.address_lines)[2]
                    temp_dict['line4'] = json.loads(address_obj.address_lines)[3]
                    temp_dict['state'] = address_obj.state
                    temp_dict['emirates'] = address_obj.emirates
                    temp_dict['country'] = address_obj.get_country()
                    temp_dict['postcode'] = address_obj.postcode
                    temp_dict['contactNumber'] = str(address_obj.contact_number)
                    temp_dict['tag'] = str(address_obj.tag)
                    temp_dict['uuid'] = str(address_obj.uuid)

                    address_list.append(temp_dict)

            response['addressList'] = address_list

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOfflineUserProfileAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchUserProfileAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchUserProfileAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            response["firstName"] = dealshub_user_obj.first_name
            response["lastName"] = dealshub_user_obj.last_name
            response["emailId"] = dealshub_user_obj.email
            response["contactNumber"] = dealshub_user_obj.contact_number

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchUserProfileAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UpdateUserProfileAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateUserProfileAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            email_id = data["emailId"]
            first_name = data["firstName"]
            last_name = data.get("lastName", "")
            contact_number = data["contactNumber"]

            dealshub_user = DealsHubUser.objects.get(email=email_id)
            dealshub_user.first_name = first_name
            dealshub_user.last_name = last_name
            dealshub_user.contact_number = contact_number
            dealshub_user.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateUserProfileAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchCustomerListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchCustomerListAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            search_list = data.get("search_list", [])

            website_group_name = data["websiteGroupName"]

            website_dealshub_user_objs = DealsHubUser.objects.filter(website_group__name=website_group_name)

            dealshub_user_objs = DealsHubUser.objects.none()
            if len(search_list)>0:
                for search_key in search_list:
                    dealshub_user_objs |= website_dealshub_user_objs.filter(Q(first_name__icontains=search_key)| Q(contact_number__icontains=search_key))
                dealshub_user_objs = dealshub_user_objs.distinct().order_by('-pk')
            else:
                dealshub_user_objs = website_dealshub_user_objs.order_by('-pk')

            filter_parameters = data.get("filter_parameters", {})

            if "is_feedback_available" in filter_parameters:
                if filter_parameters["is_feedback_available"]==True:
                    pass

            if "is_cart_empty" in filter_parameters:
                if filter_parameters["is_cart_empty"]==True:
                    cart_objs = UnitCart.objects.all().values("cart")
                    fast_cart_objs = FastCart.objects.exclude(product=None)
                    dealshub_user_objs =  dealshub_user_objs.exclude(cart__in=cart_objs).exclude(fastcart__in=fast_cart_objs)
                elif filter_parameters["is_cart_empty"]==False:
                    cart_objs = UnitCart.objects.all().values("cart")
                    fast_cart_objs = FastCart.objects.exclude(product=None)
                    dealshub_user_objs = dealshub_user_objs.filter(cart__in=cart_objs) | dealshub_user_objs.filter(fastcart__in=fast_cart_objs)
                    dealshub_user_objs = dealshub_user_objs.distinct()

            page = data.get("page", 1)
            total_customers = dealshub_user_objs.count()
            paginator = Paginator(dealshub_user_objs, 20)
            dealshub_user_objs = paginator.page(page)

            customer_list = []
            for dealshub_user_obj in dealshub_user_objs:
                try:
                    temp_dict = {}
                    temp_dict["name"] = dealshub_user_obj.first_name
                    temp_dict["emailId"] = dealshub_user_obj.email
                    temp_dict["contactNumber"] = dealshub_user_obj.contact_number
                    temp_dict["username"] = dealshub_user_obj.username
                    temp_dict["is_cart_empty"] = not (UnitCart.objects.filter(cart__owner=dealshub_user_obj).exists() or FastCart.objects.filter(owner=dealshub_user_obj).exclude(product=None).exists())
                    temp_dict["is_feedback_available"] = False
                    customer_list.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchCustomerListAPI: %s at %s", e, str(exc_tb.tb_lineno))

            is_available = True

            if int(paginator.num_pages) == int(page):
                is_available = False

            response["is_available"] = is_available

            response["customerList"] = customer_list
            response["total_customers"] = total_customers
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCustomerListAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchCustomerDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchCustomerDetailsAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            username = data["username"]

            dealshub_user_obj = DealsHubUser.objects.get(username=username)

            temp_dict = {}
            temp_dict["customerName"] = dealshub_user_obj.first_name
            temp_dict["emailId"] = dealshub_user_obj.email
            temp_dict["contactNumber"] = dealshub_user_obj.contact_number
            temp_dict["is_cart_empty"] = not (FastCart.objects.filter(owner=dealshub_user_obj).exclude(product=None).exists() or UnitCart.objects.filter(cart__owner=dealshub_user_obj).exists())
            try:
                if Cart.objects.filter(owner=dealshub_user_obj)[0].modified_date!=None:
                    temp_dict["cart_last_modified"] = str(timezone.localtime(Cart.objects.filter(owner=dealshub_user_obj)[0].modified_date).strftime("%d %b, %Y %H:%M"))
                else:
                    temp_dict["cart_last_modified"] = "NA"
            except Exception as e:
                temp_dict["cart_last_modified"] = "NA"
            temp_dict["is_feedback_available"] = False
            address_list = []
            for address_obj in Address.objects.filter(is_deleted=False, user__username=dealshub_user_obj.username):
                address_list.append(", ".join(json.loads(address_obj.address_lines)))
            temp_dict["addressList"] = address_list

            review_objs = Review.objects.filter(dealshub_user=dealshub_user_obj)
            
            unit_cart_list = []
            for unit_cart_obj in UnitCart.objects.filter(cart__owner=dealshub_user_obj):
                temp_dict2 = {}
                temp_dict2["uuid"] = unit_cart_obj.uuid
                temp_dict2["quantity"] = unit_cart_obj.quantity
                temp_dict2["price"] = unit_cart_obj.product.get_actual_price_for_customer(dealshub_user_obj)
                temp_dict2["showNote"] = unit_cart_obj.product.is_promo_restriction_note_required(dealshub_user_obj)
                temp_dict2["currency"] = unit_cart_obj.product.get_currency()
                temp_dict2["productName"] = unit_cart_obj.product.get_name()
                temp_dict2["productImageUrl"] = unit_cart_obj.product.get_main_image_url()
                unit_cart_list.append(temp_dict2)

            for unit_cart_obj in FastCart.objects.filter(owner=dealshub_user_obj).exclude(product=None):
                temp_dict2 = {}
                temp_dict2["uuid"] = unit_cart_obj.uuid
                temp_dict2["quantity"] = unit_cart_obj.quantity
                temp_dict2["price"] = unit_cart_obj.product.get_actual_price_for_customer(dealshub_user_obj)
                temp_dict2["showNote"] = unit_cart_obj.product.is_promo_restriction_note_required(dealshub_user_obj)
                temp_dict2["currency"] = unit_cart_obj.product.get_currency()
                temp_dict2["productName"] = unit_cart_obj.product.get_name()
                temp_dict2["productImageUrl"] = unit_cart_obj.product.get_main_image_url()
                unit_cart_list.append(temp_dict2)

            review_list = []
            for review_obj in review_objs:
                try:
                    temp_dict2 = {}
                    temp_dict2["uuid"] = review_obj.uuid
                    temp_dict2["sellerSku"] = review_obj.product.get_seller_sku()
                    temp_dict2["productImageUrl"] = review_obj.product.get_main_image_url()
                    temp_dict2["rating"] = review_obj.rating
                    temp_dict2["isReview"] = False
                    if review_obj.content!=None:
                        temp_dict2["isReview"] = True
                        temp_dict2["subject"] = review_obj.content.subject
                        temp_dict2["content"] = review_obj.content.content
                        temp_dict2["isReply"] = False
                        if review_obj.content.admin_comment!=None:
                            temp_dict2["isReply"] = True
                            temp_dict2["username"] = review_obj.content.admin_comment.user.username
                            temp_dict2["displayName"] = review_obj.content.admin_comment.first_name + " " + review_obj.content.admin_comment.last_name
                            temp_dict2["comment"] = review_obj.content.admin_comment.comment
                    review_list.append(temp_dict2)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchCustomerDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["customerDetails"] = temp_dict
            response["unitCartList"] = unit_cart_list
            response["reviewList"] = review_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCustomerDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchCustomerOrdersAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchCustomerOrdersAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            username = data["username"]
            page = data.get("page", 1)

            dealshub_user_obj = DealsHubUser.objects.get(username=username)

            order_objs = Order.objects.filter(owner=dealshub_user_obj).order_by('-pk')
            
            total_orders = order_objs.count()
            paginator = Paginator(order_objs, 10)
            order_objs = paginator.page(page)

            order_list = []
            for order_obj in order_objs:
                total_billing = 0
                temp_dict = {}
                temp_dict["datePlaced"] = order_obj.get_date_created()
                temp_dict["timePlaced"] = order_obj.get_time_created()
                temp_dict["bundleId"] = str(order_obj.bundleid)
                temp_dict["paymentMode"] = order_obj.payment_mode
                temp_dict["uuid"] = order_obj.uuid
                unit_order_list = []
                for unit_order_obj in UnitOrder.objects.filter(order=order_obj):
                    temp_dict2 = {}
                    temp_dict2["orderId"] = unit_order_obj.orderid
                    temp_dict2["uuid"] = unit_order_obj.uuid
                    temp_dict2["paymentStatus"] = order_obj.payment_status
                    temp_dict2["currentStatus"] = unit_order_obj.current_status
                    temp_dict2["quantity"] = unit_order_obj.quantity
                    temp_dict2["price"] = unit_order_obj.price
                    temp_dict2["currency"] = unit_order_obj.product.get_currency()
                    temp_dict2["productName"] = unit_order_obj.product.get_name()
                    temp_dict2["productImageUrl"] = unit_order_obj.product.get_main_image_url()
                    unit_order_list.append(temp_dict2)
                temp_dict["totalBilling"] = str(order_obj.to_pay) + " " + str(order_obj.location_group.location.currency)
                temp_dict["unitOrderList"] = unit_order_list
                order_list.append(temp_dict)

            is_available = True
            if int(paginator.num_pages) == int(page):
                is_available = False

            response["is_available"] = is_available
            response["total_orders"] = total_orders

            response["orderList"] = order_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCustomerOrdersAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchTokenRequestParametersAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data
            logger.info("FetchTokenRequestParametersAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            return_url = data["returnUrl"]
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            
            website_group_obj = location_group_obj.website_group
            payment_credentials = json.loads(website_group_obj.payment_credentials)

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            service_command = "TOKENIZATION"
            access_code = payment_credentials["access_code"]
            merchant_identifier = payment_credentials["merchant_identifier"]
            merchant_reference = str(uuid.uuid4())
            language = "en"
            PASS = payment_credentials["PASS"]

            is_fast_cart = data.get("is_fast_cart", False)
            if is_fast_cart==False:
                cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
                cart_obj.merchant_reference = merchant_reference
                cart_obj.save()
            else:
                fast_cart_obj = FastCart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
                fast_cart_obj.merchant_reference = merchant_reference
                fast_cart_obj.save()

            request_data = {
                "service_command": service_command,
                "access_code":access_code,
                "merchant_identifier":merchant_identifier,
                "merchant_reference":merchant_reference,
                "language":language,
                "return_url":return_url
            }

            keys = list(request_data.keys())
            keys.sort()
            if "is_fast_cart" in keys:
                keys.remove("is_fast_cart")
            signature_string = [PASS]
            for key in keys:
                signature_string.append(key+"="+request_data[key])
            signature_string.append(PASS)
            signature_string = "".join(signature_string)
            signature = hashlib.sha256(signature_string.encode('utf-8')).hexdigest()

            response["access_code"] = access_code
            response["merchant_identifier"] = merchant_identifier
            response["merchant_reference"] = merchant_reference
            response["signature"] = signature

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchTokenRequestParametersAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class MakePurchaseRequestAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data
            logger.info("MakePurchaseRequestAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            return_url = data["returnUrl"]
            merchant_reference = data["merchant_reference"]
            token_name = data["token_name"]
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            
            website_group_obj = location_group_obj.website_group
            payment_credentials = json.loads(website_group_obj.payment_credentials)

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            currency = location_group_obj.location.currency

            customer_ip = ""
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                customer_ip = x_forwarded_for.split(',')[0]
            else:
                customer_ip = request.META.get('REMOTE_ADDR')

            access_code = payment_credentials["access_code"]
            merchant_identifier = payment_credentials["merchant_identifier"]
            language = "en"
            PASS = payment_credentials["PASS"]

            command = "PURCHASE"

            

            customer_email = dealshub_user_obj.email

            cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
            amount = cart_obj.to_pay
            payfort_multiplier = int(cart_obj.location_group.location.payfort_multiplier)
            amount = str(int(float(amount)*payfort_multiplier))

            if data.get("is_fast_cart", False)==True:
                fast_cart_obj = FastCart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
                amount = fast_cart_obj.to_pay
                amount = str(int(float(amount)*payfort_multiplier))

            request_data = {
                "command":command,
                "access_code":access_code,
                "merchant_identifier":merchant_identifier,
                "merchant_reference":merchant_reference,
                "amount":amount,
                "currency":currency,
                "language":language,
                "customer_email":customer_email,
                "customer_ip":customer_ip,
                "token_name":token_name,
                "return_url":return_url
            }

            keys = list(request_data.keys())
            keys.sort()
            signature_string = [PASS]
            for key in keys:
                signature_string.append(key+"="+request_data[key])
            signature_string.append(PASS)
            signature_string = "".join(signature_string)
            signature = hashlib.sha256(signature_string.encode('utf-8')).hexdigest()

            request_data["signature"] = signature

            r = requests.post(url="https://sbpaymentservices.payfort.com/FortAPI/paymentApi", json=request_data)
            payment_response = json.loads(r.content)
            logger.info("payment_response %s", str(payment_response))

            if data.get("is_fast_cart", False)==False:
                cart_obj.payment_info = json.dumps(payment_response)
                cart_obj.merchant_reference = merchant_reference
                cart_obj.save()
            else:
                fast_cart_obj = FastCart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
                fast_cart_obj.payment_info = json.dumps(payment_response)
                fast_cart_obj.merchant_reference = merchant_reference
                fast_cart_obj.save()

            response["paymentResponse"] = payment_response
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("MakePurchaseRequestAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class PaymentTransactionAPI(APIView):
    
    permission_classes = (AllowAny,)
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("PaymentTransactionAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            merchant_reference = data["merchant_reference"]
            status = data["status"]

            PASS = "$2y$10$vdNwwmCDM"

            calc_signature = calc_response_signature(PASS, data)
            if calc_signature!=data["signature"]:
                logger.error("PaymentTransactionAPI: SIGNATURE DOES NOT MATCH!")
                return Response(data=response)


            if status=="14":
                order_obj = None
                if Cart.objects.filter(merchant_reference=merchant_reference).exists()==True:
                    cart_obj = Cart.objects.get(merchant_reference=merchant_reference)

                    try:
                        if cart_obj.shipping_address==None:
                            address_obj = Address.objects.filter(user=cart_obj.owner)[0]
                            cart_obj.shipping_address = address_obj
                            cart_obj.save()
                    except Exception as e:
                        pass

                    try:
                        voucher_obj = cart_obj.voucher
                        if voucher_obj!=None:
                            if voucher_obj.is_expired()==False and is_voucher_limt_exceeded_for_customer(cart_obj.owner, voucher_obj)==False:
                                voucher_obj.total_usage += 1
                                voucher_obj.save()
                            else:
                                cart_obj.voucher = None
                                cart_obj.save()
                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        logger.warning("PaymentTransactionAPI: voucher code not handled properly! %s at %s", e, str(exc_tb.tb_lineno))

                    order_obj = Order.objects.create(owner=cart_obj.owner, 
                                                     shipping_address=cart_obj.shipping_address,
                                                     to_pay=cart_obj.to_pay,
                                                     order_placed_date=timezone.now(),
                                                     voucher=cart_obj.voucher,
                                                     location_group=cart_obj.location_group,
                                                     payment_status="paid",
                                                     payment_info=json.dumps(data),
                                                     payment_mode=data.get("payment_option", "NA"),
                                                     merchant_reference=merchant_reference,
                                                     delivery_fee=cart_obj.get_delivery_fee(),
                                                     cod_charge=0)

                    unit_cart_objs = UnitCart.objects.filter(cart=cart_obj)
                    for unit_cart_obj in unit_cart_objs:
                        unit_order_obj = UnitOrder.objects.create(order=order_obj, 
                                                                  product=unit_cart_obj.product,
                                                                  quantity=unit_cart_obj.quantity,
                                                                  price=unit_cart_obj.product.get_actual_price_for_customer(cart_obj.owner))
                        UnitOrderStatus.objects.create(unit_order=unit_order_obj)

                    # Cart gets empty
                    for unit_cart_obj in unit_cart_objs:
                        unit_cart_obj.delete()

                    # cart_obj points to None
                    cart_obj.shipping_address = None
                    cart_obj.voucher = None
                    cart_obj.to_pay = 0
                    cart_obj.merchant_reference = ""
                    cart_obj.payment_info = "{}"
                    cart_obj.save()
                elif FastCart.objects.filter(merchant_reference=merchant_reference).exists()==True:
                    fast_cart_obj = FastCart.objects.get(merchant_reference=merchant_reference)

                    try:
                        if fast_cart_obj.shipping_address==None:
                            address_obj = Address.objects.filter(user=fast_cart_obj.owner)[0]
                            fast_cart_obj.shipping_address = address_obj
                            fast_cart_obj.save()
                    except Exception as e:
                        pass

                    try:
                        voucher_obj = fast_cart_obj.voucher
                        if voucher_obj!=None:
                            if voucher_obj.is_expired()==False and is_voucher_limt_exceeded_for_customer(fast_cart_obj.owner, voucher_obj)==False:
                                voucher_obj.total_usage += 1
                                voucher_obj.save()
                            else:
                                fast_cart_obj.voucher = None
                                fast_cart_obj.save()
                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        logger.warning("PaymentTransactionAPI: voucher code not handled properly! %s at %s", e, str(exc_tb.tb_lineno))

                    order_obj = Order.objects.create(owner=fast_cart_obj.owner, 
                                                     shipping_address=fast_cart_obj.shipping_address,
                                                     to_pay=fast_cart_obj.to_pay,
                                                     order_placed_date=timezone.now(),
                                                     voucher=fast_cart_obj.voucher,
                                                     location_group=fast_cart_obj.location_group,
                                                     payment_status="paid",
                                                     payment_info=json.dumps(data),
                                                     payment_mode=data.get("payment_option", "NA"),
                                                     merchant_reference=merchant_reference,
                                                     delivery_fee=fast_cart_obj.get_delivery_fee(),
                                                     cod_charge=0)

                    
                    unit_order_obj = UnitOrder.objects.create(order=order_obj, 
                                                              product=fast_cart_obj.product,
                                                              quantity=fast_cart_obj.quantity,
                                                              price=fast_cart_obj.product.get_actual_price_for_customer(fast_cart_obj.owner))
                    UnitOrderStatus.objects.create(unit_order=unit_order_obj)

                    # cart_obj points to None
                    fast_cart_obj.shipping_address = None
                    fast_cart_obj.voucher = None
                    fast_cart_obj.to_pay = 0
                    fast_cart_obj.merchant_reference = ""
                    fast_cart_obj.payment_info = "{}"
                    fast_cart_obj.product = None
                    fast_cart_obj.save()

                # Trigger Email
                try:
                    p1 = threading.Thread(target=send_order_confirmation_mail, args=(order_obj,))
                    p1.start()
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("PaymentTransactionAPI: %s at %s", e, str(exc_tb.tb_lineno))

                # Refresh Stock
                refresh_stock(order_obj)
            else:
                if Cart.objects.filter(merchant_reference=merchant_reference).exists()==True:
                    cart_obj = Cart.objects.get(merchant_reference=merchant_reference)
                    cart_obj.merchant_reference = ""
                    cart_obj.save()
                if FastCart.objects.filter(merchant_reference=merchant_reference).exists()==True:
                    fast_cart_obj = FastCart.objects.get(merchant_reference=merchant_reference)
                    fast_cart_obj.merchant_reference = ""
                    fast_cart_obj.save()
            
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PaymentTransactionAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class PaymentNotificationAPI(APIView):
    
    permission_classes = (AllowAny,)
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data

            logger.info("PaymentNotificationAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PaymentNotificationAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


# class FetchInstallmentPlansAPI(APIView):

#     def post(self, request, *args, **kwargs):

#         response = {}
#         response['status'] = 500
        
#         try:
#             data = request.data

#             logger.info("FetchInstallmentPlansAPI: %s", str(data))

#             if not isinstance(data, dict):
#                 data = json.loads(data)

#             website_group_name = data["websiteGroupName"]
#             currency = "AED"

#             payment_credentials = fetch_company_credentials(website_group_name)

#             access_code = payment_credentials["access_code"]
#             merchant_identifier = payment_credentials["merchant_identifier"]
#             language = "en"
#             PASS = payment_credentials["PASS"]

#             query_command = "GET_INSTALLMENTS_PLANS"

#             order_obj = Cart.objects.get(owner__username=request.user.username).order

#             amount = order_obj.to_pay
            
#             amount = str(int(float(amount)*100))

#             request_data = {
#                 "query_command":query_command,
#                 "access_code":access_code,
#                 "merchant_identifier":merchant_identifier,
#                 "amount":amount,
#                 "currency":currency,
#                 "language":language
#             }

#             keys = list(request_data.keys())
#             keys.sort()
#             signature_string = [PASS]
#             for key in keys:
#                 signature_string.append(key+"="+request_data[key])
#             signature_string.append(PASS)
#             signature_string = "".join(signature_string)
#             signature = hashlib.sha256(signature_string.encode('utf-8')).hexdigest()

#             request_data["signature"] = signature

#             r = requests.post(url="https://sbpaymentservices.payfort.com/FortAPI/paymentApi", json=request_data)
#             installment_plans = json.loads(r.content)

#             response["installmentPlans"] = installment_plans
#             response['status'] = 200
#         except Exception as e:
#             exc_type, exc_obj, exc_tb = sys.exc_info()
#             logger.error("FetchInstallmentPlansAPI: %s at %s", e, str(exc_tb.tb_lineno))

#         return Response(data=response)


# class MakePurchaseRequestInstallmentAPI(APIView):

#     def post(self, request, *args, **kwargs):

#         response = {}
#         response['status'] = 500
        
#         try:
#             data = request.data

#             logger.info("MakePurchaseRequestInstallmentAPI: %s", str(data))

#             if not isinstance(data, dict):
#                 data = json.loads(data)

#             website_group_name = data["websiteGroupName"]
#             return_url = data["returnUrl"]
#             merchant_reference = data["merchant_reference"]
#             token_name = data["token_name"]
#             issuer_code = data["issuer_code"]
#             plan_code = data["plan_code"]
#             #amount = data["amount"]
#             #currency = data["currency"]
#             currency = "AED"
#             installments = "HOSTED"

#             customer_ip = ""
#             x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
#             if x_forwarded_for:
#                 customer_ip = x_forwarded_for.split(',')[0]
#             else:
#                 customer_ip = request.META.get('REMOTE_ADDR')

#             payment_credentials = fetch_company_credentials(website_group_name)

#             access_code = payment_credentials["access_code"]
#             merchant_identifier = payment_credentials["merchant_identifier"]
#             language = "en"
#             PASS = payment_credentials["PASS"]

#             command = "PURCHASE"

#             order_obj = Order.objects.get(merchant_reference=merchant_reference)

#             amount = order_obj.to_pay
            
#             dealshub_user_obj = order_obj.owner

#             customer_email = dealshub_user_obj.email

#             amount = str(int(float(amount)*100))

#             request_data = {
#                 "command":command,
#                 "access_code":access_code,
#                 "merchant_identifier":merchant_identifier,
#                 "merchant_reference":merchant_reference,
#                 "amount":amount,
#                 "currency":currency,
#                 "language":language,
#                 "customer_email":customer_email,
#                 "customer_ip":customer_ip,
#                 "issuer_code":issuer_code,
#                 "plan_code":plan_code,
#                 "installments":installments,
#                 "token_name":token_name,
#                 "return_url":return_url
#             }

#             keys = list(request_data.keys())
#             keys.sort()
#             signature_string = [PASS]
#             for key in keys:
#                 signature_string.append(key+"="+request_data[key])
#             signature_string.append(PASS)
#             signature_string = "".join(signature_string)
#             signature = hashlib.sha256(signature_string.encode('utf-8')).hexdigest()

#             request_data["signature"] = signature

#             r = requests.post(url="https://sbpaymentservices.payfort.com/FortAPI/paymentApi", json=request_data)
#             payment_response = json.loads(r.content)
#             logger.info("payment_response %s", str(payment_response))

#             order_obj.payment_info = json.dumps(payment_response)
#             order_obj.save()


#             response["paymentResponse"] = payment_response
#             response['status'] = 200
#         except Exception as e:
#             exc_type, exc_obj, exc_tb = sys.exc_info()
#             logger.error("MakePurchaseRequestInstallmentAPI: %s at %s", e, str(exc_tb.tb_lineno))

#         return Response(data=response)


class CalculateSignatureAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data

            logger.info("CalculateSignatureAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            PASS = "$2y$10$vdNwwmCDM"
            #PASS = "$2y$10$tGrWU3XZ0"  # Prod

            calc_signature = calc_response_signature(PASS, data["payfortResponse"])


            response["signature"] = calc_signature
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CalculateSignatureAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class ContactUsSendEmailAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("ContactUsSendEmailAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)
            
            your_email = data["yourEmail"]
            message = data["message"]
            location_group_uuid = data["locationGroupUuid"]

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            to_email = location_group_obj.get_support_email_id()
            password = location_group_obj.get_support_email_password()

            # Trigger Email
            try:
                p1 = threading.Thread(target=contact_us_send_email, args=(your_email,message,to_email,password))
                p1.start()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("ContactUsSendEmail: %s at %s", e, str(exc_tb.tb_lineno))

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ContactUsSendEmailAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SendOTPSMSLoginAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SendOTPSMSLoginAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)
            
            contact_number = data["contactNumber"]
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group
            website_group_name = website_group_obj.name.lower()

            sms_country_info = json.loads(location_group_obj.sms_country_info)

            digits = "0123456789"
            OTP = ""
            for i in range(6):
                OTP += digits[int(math.floor(random.random()*10))]

            if contact_number in ["888888888", "940804016", "888888881", "702290032"]:
                OTP = "777777"

            is_new_user = False
            if DealsHubUser.objects.filter(username=contact_number+"-"+website_group_name).exists()==False:
                dealshub_user_obj = DealsHubUser.objects.create(username=contact_number+"-"+website_group_name, contact_number=contact_number, website_group=website_group_obj)
                dealshub_user_obj.set_password(OTP)
                dealshub_user_obj.verification_code = OTP
                dealshub_user_obj.save()
                is_new_user = True

                for location_group_obj in LocationGroup.objects.filter(website_group=website_group_obj):
                    Cart.objects.create(owner=dealshub_user_obj, location_group=location_group_obj)
                    WishList.objects.create(owner=dealshub_user_obj, location_group=location_group_obj)
                    FastCart.objects.create(owner=dealshub_user_obj, location_group=location_group_obj)

            else:
                dealshub_user_obj = DealsHubUser.objects.get(username=contact_number+"-"+website_group_name)
                dealshub_user_obj.set_password(OTP)
                dealshub_user_obj.verification_code = OTP
                dealshub_user_obj.save()

            message = "Login OTP is " + OTP

            # Trigger SMS
            prefix_code = sms_country_info["prefix_code"]
            user = sms_country_info["user"]
            pwd = sms_country_info["pwd"]

            contact_number = prefix_code+contact_number

            url = "http://www.smscountry.com/smscwebservice_bulk.aspx"
            req_data = {
                "user" : user,
                "passwd": pwd,
                "message": message,
                "mobilenumber": contact_number,
                "mtype":"N",
                "DR":"Y"
            }
            r = requests.post(url=url, data=req_data)

            response["isNewUser"] = is_new_user
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SendOTPSMSLoginAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CheckUserPinSetAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("CheckUserPinSetAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)
            
            contact_number = data["contactNumber"]
            location_group_uuid = data["locationGroupUuid"]

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group
            website_group_name = website_group_obj.name.lower()

            is_new_user = False
            dealshub_user_obj = None
            if DealsHubUser.objects.filter(username=contact_number+"-"+website_group_name).exists()==False:
                dealshub_user_obj = DealsHubUser.objects.create(username=contact_number+"-"+website_group_name, contact_number=contact_number, website_group=website_group_obj)
                dealshub_user_obj.set_password("97631")
                dealshub_user_obj.verification_code = "97631"
                dealshub_user_obj.save()
                is_new_user = True

                for location_group_obj in LocationGroup.objects.filter(website_group=website_group_obj):
                    Cart.objects.create(owner=dealshub_user_obj, location_group=location_group_obj)
                    WishList.objects.create(owner=dealshub_user_obj, location_group=location_group_obj)
                    FastCart.objects.create(owner=dealshub_user_obj, location_group=location_group_obj)
            else:
                dealshub_user_obj = DealsHubUser.objects.get(username=contact_number+"-"+website_group_name)
            
            response["is_pin_set"] = dealshub_user_obj.is_pin_set
            response["is_new_user"] = is_new_user
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CheckUserPinSetAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SetLoginPinAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SetLoginPinAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)
            
            contact_number = data["contactNumber"]
            location_group_uuid = data["locationGroupUuid"]
            pin = data["pin"]

            if len(pin)!=4:
                response["status"] = 403
                logger.warning("SetLoginPinAPI: Pin must be 4 digit long")
                return Response(data=response)

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group
            website_group_name = website_group_obj.name.lower()
            
            verified = False
            dealshub_user_obj = DealsHubUser.objects.get(username=contact_number+"-"+website_group_name)
            if dealshub_user_obj.is_pin_set==False:
                dealshub_user_obj.set_password(pin)
                dealshub_user_obj.verification_code = pin
                dealshub_user_obj.is_pin_set = True
                dealshub_user_obj.save()

                credentials = {
                    "username": contact_number+"-"+website_group_name,
                    "password": pin
                }
                if dealshub_user_obj.verification_code==pin:
                    r = requests.post(url=SERVER_IP+"/token-auth/", data=credentials, verify=False)
                    token = json.loads(r.content)["token"]
                    response["token"] = token
                    dealshub_user_obj.contact_verified = True
                    verified = True
                    dealshub_user_obj.save()
            else:
                response["status"] = 403
                logger.warning("SetLoginPinAPI: Pin already set!")
                return Response(data=response)

            response["verified"] = verified
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SetLoginPinAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class VerifyLoginPinAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("VerifyLoginPinAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)
            
            contact_number = data["contactNumber"]
            location_group_uuid = data["locationGroupUuid"]
            pin = data["pin"]

            if len(pin)!=4:
                response["status"] = 403
                logger.warning("VerifyLoginPinAPI: Pin must be 4 digit long")
                return Response(data=response)

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group
            website_group_name = website_group_obj.name.lower()
            
            verified = False
            dealshub_user_obj = DealsHubUser.objects.get(username=contact_number+"-"+website_group_name)
            if dealshub_user_obj.is_pin_set==True:
                credentials = {
                    "username": contact_number+"-"+website_group_name,
                    "password": pin
                }
                if dealshub_user_obj.verification_code==pin:
                    r = requests.post(url=SERVER_IP+"/token-auth/", data=credentials, verify=False)
                    token = json.loads(r.content)["token"]
                    response["token"] = token
                    dealshub_user_obj.contact_verified = True
                    verified = True
                    dealshub_user_obj.save()

            response["verified"] = verified
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SetLoginPinAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class ForgotLoginPinAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("ForgotLoginPinAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)
            
            contact_number = data["contactNumber"]
            location_group_uuid = data["locationGroupUuid"]

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group
            website_group_name = website_group_obj.name.lower()

            digits = "0123456789"
            pin = ""
            for i in range(4):
                pin += digits[int(math.floor(random.random()*10))]

            if contact_number in ["888888888", "940804016", "888888881"]:
                pin = "1234"

            message = "Your PIN has been reset. New PIN is " + pin

            dealshub_user_obj = DealsHubUser.objects.get(username=contact_number+"-"+website_group_name)
            dealshub_user_obj.set_password(pin)
            dealshub_user_obj.verification_code = pin
            dealshub_user_obj.save()

            # Trigger SMS
            if location_group_obj.website_group.name.lower()!="parajohn":
                mshastra_info = json.loads(location_group_obj.mshastra_info)
                prefix_code = mshastra_info["prefix_code"]
                sender_id = mshastra_info["sender_id"]
                user = mshastra_info["user"]
                pwd = mshastra_info["pwd"]
                contact_number = prefix_code+contact_number
                url = "http://mshastra.com/sendurlcomma.aspx?user="+user+"&pwd="+pwd+"&senderid="+sender_id+"&mobileno="+contact_number+"&msgtext="+message+"&priority=High&CountryCode=ALL"
                r = requests.get(url)
            else:
                contact_number = "971"+contact_number
                url = "https://retail.antwerp.alarislabs.com/rest/send_sms?from=PARA JOHN&to="+contact_number+"&message="+message+"&username=r8NyrDLI&password=GLeOC6HO"
                r = requests.get(url)

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ForgotLoginPinAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class VerifyOTPSMSLoginAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("VerifyOTPSMSLoginAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)
            
            contact_number = data["contactNumber"]
            otp = data["otp"]
            location_group_uuid = data["locationGroupUuid"].lower()
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group
            website_group_name = website_group_obj.name.lower()

            dealshub_user_obj = DealsHubUser.objects.get(username=contact_number+"-"+website_group_name)
            
            credentials = {
                "username": contact_number+"-"+website_group_name,
                "password": otp
            }

            verified = False
            if dealshub_user_obj.verification_code==otp:
                r = requests.post(url=SERVER_IP+"/token-auth/", data=credentials, verify=False)
                token = json.loads(r.content)["token"]
                response["token"] = token
                verified = True
                dealshub_user_obj.contact_verified = True
                dealshub_user_obj.save()

            response["verified"] = verified
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("VerifyOTPSMSLoginAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UpdateUserEmailAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateUserEmailAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)
            
            email_id = data["emailId"].strip()

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            
            dealshub_user_obj.email = email_id
            dealshub_user_obj.email_verified = True
            dealshub_user_obj.save()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateUserEmailAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddReviewAPI(APIView):

    def post(self, request, *arg, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddReviewAPI: %s", str(data))
            product_code = str(data["product_code"])
            rating = int(data["rating"])
            review_content = json.loads(data["review_content"])

            subject = str(review_content["subject"])
            content = str(review_content["content"])

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            dealshub_product_obj = DealsHubProduct.objects.get(uuid=product_code)

            #if UnitOrder.objects.filter(product=dealshub_product_obj, order__owner=dealshub_user_obj).exists():
            review_obj, created = Review.objects.get_or_create(dealshub_user=dealshub_user_obj, product=dealshub_product_obj)
            review_obj.rating = rating
            review_content_obj = review_obj.content
            if review_content_obj is None:
                review_content_obj = ReviewContent.objects.create(subject=subject, content=content)
            else:
                review_content_obj.subject = subject
                review_content_obj.content = content
                review_content_obj.save()
            
            image_count = int(data.get("image_count", 0))
            for i in range(image_count):
                image_obj = Image.objects.create(image=data["image_"+str(i)])
                review_content_obj.images.add(image_obj)
            review_content_obj.save()

            review_obj.content = review_content_obj
            review_obj.save()
            response["uuid"] = review_obj.uuid
            response["review_content_uuid"] = review_content_obj.uuid
            response["status"] = 200
            # else:
            #     response["status"] = 403

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddReviewAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddRatingAPI(APIView):

    def post(self, request, *arg, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddRatingAPI: %s", str(data))
            product_code = str(data["product_code"])
            rating = int(data["rating"])

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            dealshub_product_obj = DealsHubProduct.objects.get(uuid=product_code)

            if UnitOrder.objects.filter(product=dealshub_product_obj, order__owner=dealshub_user_obj).exists():
                review_obj = Review.objects.create(dealshub_user=dealshub_user_obj, product=dealshub_product_obj, rating=rating)
                response["uuid"] = review_obj.uuid
                response["status"] = 200
            else:
                response["status"] = 403

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddRatingAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class UpdateRatingAPI(APIView):

    def post(self, request, *arg, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateRatingAPI: %s", str(data))
            uuid = str(data["uuid"])
            rating = int(data["rating"])

            review_obj = Review.objects.get(uuid=uuid)
            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            if review_obj.dealshub_user == dealshub_user_obj:
                review_obj.rating = rating
                review_obj.save()
                response["status"] = 200
            else:
                response["status"] = 403

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateRatingAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddAdminCommentAPI(APIView):
    
    def post(self, request, *arg, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddAdminCommentAPI: %s", str(data))

            uuid = str(data["uuid"])
            username = str(data["username"])
            display_name = str(data["displayName"])
            comment = str(data["comment"])

            review_obj = Review.objects.get(uuid=uuid)

            omnycomm_user_obj = OmnyCommUser.objects.get(username=request.user)

            if review_obj.content==None:
                response["status"] = 403
                return Response(data=response)

            admin_comment_obj = None
            if review_obj.content.admin_comment!=None:
                admin_comment_obj = review_obj.content.admin_comment
                admin_comment_obj.comment = comment
                admin_comment_obj.save()
            else:
                admin_comment_obj = AdminReviewComment.objects.create(user=omnycomm_user_obj, comment=comment)
                review_content_obj = review_obj.content
                review_content_obj.admin_comment = admin_comment_obj
                review_content_obj.save()

            response["admin_comment_uuid"] = admin_comment_obj.uuid
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddAdminCommentAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UpdateAdminCommentAPI(APIView):
    
    def post(self, request, *arg, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateAdminCommentAPI: %s", str(data))
            uuid = str(data["admin_comment_uuid"])
            comment = str(data["comment"])

            admin_comment_obj = AdminReviewComment.objects.get(uuid=uuid)
            admin_comment_obj.comment = comment
            admin_comment_obj.save()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateAdminCommentAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddUpvoteAPI(APIView):

    def post(self, request, *arg, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddUpvoteAPI: %s", str(data))
            uuid = str(data["review_content_uuid"])

            review_content_obj = ReviewContent.objects.get(uuid=uuid)
            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            review_obj = Review.objects.get(content=review_content_obj)

            if review_obj.dealshub_user != dealshub_user_obj:
                review_obj.upvoted_users.add(dealshub_user_obj)
                review_obj.save()
                response["status"] = 200
            else:
                response["status"] = 403

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddUpvoteAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DeleteUpvoteAPI(APIView):

    def post(self, request, *arg, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("DeleteUpvoteAPI: %s", str(data))
            uuid = str(data["review_content_uuid"])

            review_content_obj = ReviewContent.objects.get(uuid=uuid)
            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            review_obj = Review.objects.get(content=review_content_obj)

            if review_obj.dealshub_user != dealshub_user_obj:
                review_obj.upvoted_users.remove(dealshub_user_obj)
                review_obj.save()
                response["status"] = 200
            else:
                response["status"] = 403

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteUpvoteAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchReviewAPI(APIView):

    def post(self, request, *arg, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchReviewAPI: %s", str(data))
            uuid = str(data["uuid"])

            review_obj = Review.objects.get(uuid=uuid)
            response["username"] = str(review_obj.dealshub_user.username)
            response["product_code"] = str(review_obj.product.product.uuid)
            response["rating"] = str(review_obj.rating)

            review_content_obj = review_obj.content
            admin_comment_obj = review_content_obj.admin_comment

            admin_comment = {
                "username" : str(admin_comment_obj.username),
                "display_name" : str(admin_comment_obj.user.first_name+" "+ admin_comment_obj.user.last_name),
                "comment" : str(admin_comment_obj.comment),
                "created_date" : str(admin_comment_obj.created_date),
                "modified_date" : str(admin_comment_obj.modified_date)
            }

            review_content = {
                "subject" : str(review_content_obj.subject),
                "content" : str(review_content_obj.content),
                "upvotes_count" : str(review_content_obj.upvoted_users.all().count()),
                "admin_comment" : admin_comment
            }

            response["review_content"] = review_content
            response["created_date"] = str(review_obj.created_date)
            response["modified_date"] = str(review_obj.modified_date)
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchReviewAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchProductReviewsAPI(APIView):

    permission_classes = [AllowAny]
    
    def post(self, request, *arg, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchProductReviewsAPI: %s", str(data))
            product_code = str(data["product_code"])

            product_reviews = []
            review_objs = Review.objects.filter(product__uuid=product_code)
            total_reviews = review_objs.count()

            total_rating = 0
            for review_obj in review_objs:
                temp_dict = {}

                temp_dict["username"] = str(review_obj.dealshub_user.username)
                temp_dict["display_name"] = str(review_obj.dealshub_user.first_name)
                temp_dict["rating"] = str(review_obj.rating)
                total_rating += int(review_obj.rating)

                review_content_obj = review_obj.content

                admin_comment_obj = None
                if review_content_obj!=None:
                    admin_comment_obj = review_content_obj.admin_comment
                admin_comment = None
                if admin_comment_obj is not None:
                    admin_comment = {
                        "username" : str(admin_comment_obj.username),
                        "display_name" : str(admin_comment_obj.user.first_name+" "+admin_comment_obj.user.last_name),
                        "comment" : str(admin_comment_obj.comment),
                        "created_date" : str(timezone.localtime(admin_comment_obj.created_date).strftime("%d %b, %Y")),
                        "modified_date" : str(timezone.localtime(admin_comment_obj.modified_date).strftime("%d %b, %Y"))
                    }

                review_content = None
                if review_content_obj is not None:
                    image_objs = review_content_obj.images.all()
                    image_url_list = []
                    for image_obj in image_objs:
                        try:
                            image_url_list.append(image_obj.mid_image.url)
                        except Exception as e:
                            exc_type, exc_obj, exc_tb = sys.exc_info()
                            logger.warning("FetchProductReviewsAPI: %s at %s", e, str(exc_tb.tb_lineno))
                    review_content = {
                        "subject" : str(review_content_obj.subject),
                        "content" : str(review_content_obj.content),
                        "upvotes_count" : str(review_content_obj.upvoted_users.count()),
                        "admin_comment" : admin_comment,
                        "image_url_list": image_url_list
                    }

                temp_dict["review_content"] = review_content
                temp_dict["created_date"] = str(timezone.localtime(review_obj.created_date).strftime("%d %b, %Y"))
                temp_dict["modified_date"] = str(timezone.localtime(review_obj.modified_date).strftime("%d %b, %Y"))

                product_reviews.append(temp_dict)

            average_rating = 0
            if total_reviews != 0:
                average_rating = round(float(total_rating)/float(total_reviews), 2)

            is_user_reviewed = False
            is_product_purchased = True
            if request.user!=None:

                if UnitOrder.objects.filter(product__uuid=product_code, order__owner__username=request.user.username).exists():
                    is_product_purchased = True

                if Review.objects.filter(product__uuid=product_code, dealshub_user__username=request.user.username).exists():
                    is_user_reviewed = True
                    review_obj = Review.objects.get(product__uuid=product_code, dealshub_user__username=request.user.username)
                    review_content = None
                    review_content_obj = review_obj.content
                    if review_content_obj is not None:
                        image_objs = review_content_obj.images.all()
                        image_url_list = []
                        for image_obj in image_objs:
                            try:
                                temp_dict = {
                                    "uuid": image_obj.pk, 
                                    "url": image_obj.mid_image.url
                                }
                                image_url_list.append(temp_dict)
                            except Exception as e:
                                exc_type, exc_obj, exc_tb = sys.exc_info()
                                logger.warning("FetchProductReviewsAPI: %s at %s", e, str(exc_tb.tb_lineno))
                        review_content = {
                            "subject" : str(review_content_obj.subject),
                            "content" : str(review_content_obj.content),
                            "upvotes_count" : str(review_content_obj.upvoted_users.count()),
                            "image_url_list": image_url_list
                        }
                    response["user_rating"] = str(review_obj.rating)
                    response["user_review_content"] = review_content
                    response["user_review_uuid"] = review_obj.uuid

            response["is_product_purchased"] = is_product_purchased
            response["is_user_reviewed"] = is_user_reviewed
            response["product_reviews"] = product_reviews
            response["average_rating"] = str(average_rating)
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductReviewsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DeleteUserReviewImageAPI(APIView):
    
    def post(self, request, *arg, **kwargs):
        
        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteUserReviewImageAPI: %s", str(data))
            
            image_uuid = int(data["image_uuid"])
            user_review_uuid = data["user_review_uuid"]

            review_obj = Review.objects.get(uuid=user_review_uuid)
            if review_obj.dealshub_user.username==request.user.username:
                review_content_obj = review_obj.content
                image_obj = Image.objects.get(pk=image_uuid)
                review_content_obj.images.remove(image_obj)
                review_content_obj.save()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteUserReviewImageAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DeleteUserReviewAPI(APIView):
    
    def post(self, request, *arg, **kwargs):
        
        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteUserReviewAPI: %s", str(data))
            uuid = str(data["uuid"])

            review_obj = Review.objects.get(uuid=uuid)
            if review_obj.dealshub_user.username==request.user.username:
                review_obj.delete()
                
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteUserReviewAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchOrdersForWarehouseManagerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchOrdersForWarehouseManagerAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            from_date = data.get("fromDate", "")
            to_date = data.get("toDate", "")
            payment_type_list = data.get("paymentTypeList", [])
            min_qty = data.get("minQty", "")
            max_qty = data.get("maxQty", "")
            min_price = data.get("minPrice", "")
            max_price = data.get("maxPrice", "")
            currency_list = data.get("currencyList", [])
            shipping_method_list = data.get("shippingMethodList", [])
            tracking_status_list = data.get("trackingStatusList", [])
            search_list = data.get("searchList", [])
            location_group_uuid = data["locationGroupUuid"]

            is_postaplus = data.get("isPostaplus", "")

            page = data.get("page", 1)

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            unit_order_objs = UnitOrder.objects.filter(order__location_group__uuid=location_group_uuid).order_by('-pk')

            if is_postaplus==True:
                unit_order_objs = unit_order_objs.filter(order__is_postaplus=True)                

            if from_date!="":
                from_date = from_date[:10]+"T00:00:00+04:00"
                unit_order_objs = unit_order_objs.filter(order__order_placed_date__gte=from_date)

            if to_date!="":
                to_date = to_date[:10]+"T23:59:59+04:00"
                unit_order_objs = unit_order_objs.filter(order__order_placed_date__lte=to_date)

            if len(payment_type_list)>0:
                if "COD" in payment_type_list and "Credit Card" not in payment_type_list:
                    unit_order_objs = unit_order_objs.filter(order__payment_mode="COD")
                if "COD" not in payment_type_list and "Credit Card" in payment_type_list:
                    unit_order_objs = unit_order_objs.exclude(order__payment_mode="COD")

            if len(shipping_method_list)>0:
                unit_order_objs = unit_order_objs.filter(shipping_method__in=shipping_method_list)

            if len(tracking_status_list)>0:
                unit_order_objs = unit_order_objs.filter(current_status_admin__in=tracking_status_list)

            if max_qty!="":
                unit_order_objs = unit_order_objs.filter(quantity__lte=int(max_qty))

            if min_qty!="":
                unit_order_objs = unit_order_objs.filter(quantity__gte=int(min_qty))

            if max_price!="":
                unit_order_objs = unit_order_objs.filter(price__lte=int(max_price))

            if min_price!="":
                unit_order_objs = unit_order_objs.filter(price__gte=int(min_price))


            if len(search_list)>0:
                temp_unit_order_objs = UnitOrder.objects.none()
                for search_string in search_list:
                    temp_unit_order_objs |= unit_order_objs.filter(Q(product__product__base_product__seller_sku__icontains=search_string) | Q(order__bundleid__icontains=search_string) | Q(orderid__icontains=search_string) | Q(order__owner__first_name__icontains=search_string) | Q(order__shipping_address__contact_number__icontains=search_string) | Q(order__merchant_reference__icontains=search_string))
                unit_order_objs = temp_unit_order_objs.distinct()


            order_objs = Order.objects.filter(location_group__uuid=location_group_uuid, unitorder__in=unit_order_objs).distinct().order_by("-order_placed_date")

            paginator = Paginator(order_objs, 20)
            total_orders = order_objs.count()
            order_objs = paginator.page(page)

            invoice_logo = location_group_obj.get_email_website_logo()
            website_group_name = location_group_obj.website_group.name.lower()
            trn_number = json.loads(location_group_obj.website_group.conf).get("trn_number", "NA")
            support_contact_number = json.loads(location_group_obj.website_group.conf).get("support_contact_number", "NA")
            footer_text = json.loads(location_group_obj.website_group.conf).get("footer_text", "NA")

            order_list = []
            for order_obj in order_objs:
                try:
                    voucher_obj = order_obj.voucher
                    is_voucher_applied = voucher_obj is not None

                    temp_dict = {}
                    temp_dict["dateCreated"] = order_obj.get_date_created()
                    temp_dict["time"] = order_obj.get_time_created()
                    temp_dict["paymentMode"] = order_obj.payment_mode
                    temp_dict["paymentStatus"] = order_obj.payment_status
                    temp_dict["merchant_reference"] = order_obj.merchant_reference
                    cancel_status = unit_order_objs.filter(order=order_obj, current_status_admin="cancelled").exists()
                    temp_dict["cancelStatus"] = cancel_status
                    if cancel_status==True:
                        cancelling_note = unit_order_objs.filter(order=order_obj, current_status_admin="cancelled")[0].cancelling_note
                        temp_dict["cancelling_note"] = cancelling_note

                    temp_dict["sap_final_billing_info"] = json.loads(order_obj.sap_final_billing_info)
                    temp_dict["sapStatus"] = order_obj.sap_status
                    temp_dict["isOrderOffline"] = order_obj.is_order_offline

                    address_obj = order_obj.shipping_address
                    
                    shipping_address = {
                        "firstName": address_obj.first_name,
                        "lastName": address_obj.last_name,
                        "line1": json.loads(address_obj.address_lines)[0],
                        "line2": json.loads(address_obj.address_lines)[1],
                        "line3": json.loads(address_obj.address_lines)[2],
                        "line4": json.loads(address_obj.address_lines)[3],
                        "state": address_obj.state,
                        "emirates": address_obj.emirates
                    }

                    customer_name = address_obj.first_name


                    temp_dict["customerName"] = customer_name
                    temp_dict["emailId"] = order_obj.owner.email
                    temp_dict["contactNumer"] = order_obj.owner.contact_number
                    temp_dict["shippingAddress"] = shipping_address

                    temp_dict["bundleId"] = order_obj.bundleid
                    temp_dict["uuid"] = order_obj.uuid
                    temp_dict["isVoucherApplied"] = is_voucher_applied
                    if is_voucher_applied:
                        temp_dict["voucherCode"] = voucher_obj.voucher_code
                        voucher_discount = voucher_obj.get_voucher_discount(order_obj.get_subtotal())
                        voucher_discount_vat = voucher_obj.get_voucher_discount_vat(voucher_discount)
                        voucher_discount_without_vat = voucher_obj.get_voucher_discount_without_vat(voucher_discount)
                        temp_dict["voucherDiscount"] = voucher_discount
                        temp_dict["voucherDiscountVat"] = voucher_discount_vat
                        temp_dict["voucherDiscountWithoutVat"] = voucher_discount_without_vat

                    unit_order_list = []
                    subtotal = 0
                    for unit_order_obj in unit_order_objs.filter(order=order_obj):
                        temp_dict2 = {}
                        temp_dict2["orderId"] = unit_order_obj.orderid
                        temp_dict2["shippingMethod"] = unit_order_obj.shipping_method
                        temp_dict2["uuid"] = unit_order_obj.uuid
                        temp_dict2["currentStatus"] = unit_order_obj.current_status_admin
                        temp_dict2["sapStatus"] = unit_order_obj.sap_status
                        temp_dict2["sap_intercompany_info"] = json.loads(unit_order_obj.sap_intercompany_info)
                        temp_dict2["quantity"] = unit_order_obj.quantity
                        temp_dict2["price"] = unit_order_obj.price
                        temp_dict2["price_without_vat"] = unit_order_obj.get_price_without_vat()
                        temp_dict2["vat"] = unit_order_obj.get_total_vat()
                        temp_dict2["totalPrice"] = unit_order_obj.get_subtotal()
                        temp_dict2["total_price_without_vat"] = unit_order_obj.get_subtotal_without_vat()
                        temp_dict2["currency"] = unit_order_obj.product.get_currency()
                        temp_dict2["productName"] = unit_order_obj.product.get_seller_sku() + " - " + unit_order_obj.product.get_name()
                        temp_dict2["productImageUrl"] = unit_order_obj.product.get_main_image_url()
                        temp_dict2["intercompany_order_id"] = unit_order_obj.get_sap_intercompany_order_id()
                        intercompany_qty = unit_order_obj.get_sap_intercompany_order_qty()
                        final_qty = unit_order_obj.get_sap_final_order_qty()

                        if intercompany_qty != "" and final_qty != "":
                            if intercompany_qty != final_qty:
                                order_obj.sap_status = "GRN Conflict"
                                unit_order_obj.sap_status = "GRN Conflict"
                                order_obj.save()
                                unit_order_obj.save()

                        temp_dict2["intercompany_qty"] = intercompany_qty
                        temp_dict2["final_qty"] = final_qty
                        unit_order_list.append(temp_dict2)
                    temp_dict["approved"] = UnitOrder.objects.filter(order=order_obj, current_status_admin="approved").count()
                    temp_dict["picked"] = UnitOrder.objects.filter(order=order_obj, current_status_admin="picked").count()
                    temp_dict["dispatched"] = UnitOrder.objects.filter(order=order_obj, current_status_admin="dispatched").count()
                    temp_dict["delivered"] = UnitOrder.objects.filter(order=order_obj, current_status_admin="delivered").count()
                    temp_dict["deliveryFailed"] = UnitOrder.objects.filter(order=order_obj, current_status_admin="delivery failed").count()

                    subtotal = order_obj.get_subtotal()
                    subtotal_vat = order_obj.get_subtotal_vat()
                    subtotal_without_vat = order_obj.get_subtotal_without_vat()
                    delivery_fee = order_obj.get_delivery_fee()
                    delivery_fee_vat = order_obj.get_delivery_fee_vat()
                    delivery_fee_without_vat = order_obj.get_delivery_fee_without_vat()
                    cod_fee = order_obj.get_cod_charge()
                    cod_fee_vat = order_obj.get_cod_charge_vat()
                    cod_fee_without_vat = order_obj.get_cod_charge_without_vat()

                    to_pay = order_obj.get_total_amount()
                    vat = order_obj.get_vat()
                    
                    temp_dict["subtotalWithoutVat"] = str(subtotal_without_vat)
                    temp_dict["subtotalVat"] = str(subtotal_vat)
                    temp_dict["subtotal"] = str(subtotal)

                    temp_dict["deliveryFeeWithoutVat"] = str(delivery_fee_without_vat)
                    temp_dict["deliveryFeeVat"] = str(delivery_fee_vat)
                    temp_dict["deliveryFee"] = str(delivery_fee)

                    temp_dict["codFeeWithoutVat"] = str(cod_fee_without_vat)
                    temp_dict["codFeeVat"] = str(cod_fee_vat)
                    temp_dict["codFee"] = str(cod_fee)

                    temp_dict["vat"] = str(vat)
                    temp_dict["toPay"] = str(to_pay)
                    temp_dict["toPayWithoutVat"] = str(round(to_pay-vat, 2))
                    temp_dict["currency"] = str(order_obj.get_currency())

                    temp_dict["unitOrderList"] = unit_order_list

                    temp_dict["invoice_logo"] = invoice_logo
                    temp_dict["website_group_name"] = website_group_name
                    temp_dict["trn_number"] = trn_number
                    temp_dict["support_contact_number"] = support_contact_number
                    temp_dict["footer_text"] = footer_text

                    order_list.append(temp_dict)

                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchOrdersForWarehouseManagerAPI: %s at %s", e, str(exc_tb.tb_lineno))

            is_available = True
            if int(paginator.num_pages) == int(page):
                is_available = False

            response["isAvailable"] = is_available
            response["totalOrders"] = total_orders
            response["orderList"] = order_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOrdersForWarehouseManagerAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchShippingMethodAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            
            data = request.data
            logger.info("FetchShippingMethodAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            shipping_methods = ["WIG Fleet", "P-Plus"]

            response["shippingMethods"] = shipping_methods
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchShippingMethodAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SetShippingMethodAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SetShippingMethodAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            shipping_method = data["shippingMethod"]
            unit_order_uuid_list = data["unitOrderUuidList"]

            order_obj = UnitOrder.objects.get(uuid=unit_order_uuid_list[0]).order

            # if shipping_method=="WIG Fleet":
            #     for unit_order_obj in UnitOrder.objects.filter(order=order_obj):
            #         set_shipping_method(unit_order_obj, shipping_method)
            # elif shipping_method=="Postaplus":
            #     if order_obj.is_postaplus==False:
            #         request_postaplus(order_obj)
            # else:
            #     logger.warning("SetShippingMethodAPI: No method set!")

            brand_company_dict = {
                
                "geepas": "1000",
                "baby plus": "5550",
                "royalford": "3000",
                "krypton": "2100",
                "olsenmark": "1100",
                "ken jardene": "5550",
                "younglife": "5000",
                "para john" : "6000",
                "delcasa": "3050"
            }

            sap_info_render = []
            
            wigme_website_group_obj = WebsiteGroup.objects.get(name="shopnesto")
            if order_obj.location_group.website_group==wigme_website_group_obj and UnitOrder.objects.filter(order=order_obj)[0].shipping_method != shipping_method:

                user_input_requirement = {}
                
                for unit_order_obj in UnitOrder.objects.filter(order=order_obj):
                    seller_sku = unit_order_obj.product.get_seller_sku()
                    brand_name = unit_order_obj.product.get_brand()
                    company_code = brand_company_dict[brand_name.lower()]
                    stock_price_information = fetch_prices_and_stock(seller_sku, company_code)

                    if stock_price_information["status"] == 500:
                        response["status"] = 403
                        response["message"] = stock_price_information["message"]
                        return Response(data=response)

                    user_input_requirement[seller_sku] = is_user_input_required_for_sap_punching(stock_price_information)

                user_input_sap = data.get("user_input_sap", None)
                
                if user_input_sap==None:
                    
                    modal_info_list = []
                    
                    for unit_order_obj in UnitOrder.objects.filter(order=order_obj):
                        seller_sku = unit_order_obj.product.get_seller_sku()
                        brand_name = unit_order_obj.product.get_brand()
                        company_code = brand_company_dict[brand_name.lower()]
                        
                        if user_input_requirement[seller_sku]==True:
                            result = fetch_prices_and_stock(seller_sku, company_code)
                            result["uuid"] = unit_order_obj.uuid
                            result["seller_sku"] = seller_sku
                            
                            modal_info_list.append(result)
                    
                    if len(modal_info_list)>0:
                        response["modal_info_list"] = modal_info_list
                        response["status"] = 200
                        return Response(data=response)

                error_flag = 0
                sap_info_render = []

                # [ List pf Querysets of (UnitOrder Objects grouped by Brand) ]

                unit_order_objs = UnitOrder.objects.filter(order=order_obj)

                if unit_order_objs.filter(grn_filename="").exists():

                    grouped_unit_orders = {} 

                    for unit_order_obj in unit_order_objs:
                        
                        brand_name = unit_order_obj.product.get_brand()
                        
                        if brand_name not in grouped_unit_orders:
                            grouped_unit_orders[brand_name] = []
                        
                        grouped_unit_orders[brand_name].append(unit_order_obj)
                    
                    for brand_name in grouped_unit_orders: 
                        
                        order_information = {}
                        company_code = brand_company_dict[brand_name.lower()]
                        order_information["order_id"] = order_obj.bundleid.replace("-","")
                        order_information["refrence_id"] = order_obj.bundleid.replace("-","&#8211;")
                        order_information["items"] = []
                        
                        for unit_order_obj in grouped_unit_orders[brand_name]:

                            seller_sku = unit_order_obj.product.get_seller_sku()
                            x_value = ""
                            
                            if user_input_requirement[seller_sku]==True:
                                x_value = user_input_sap[seller_sku]
                            
                            item =  fetch_order_information_for_sap_punching(seller_sku, company_code, x_value)
                            
                            item["seller_sku"] = seller_sku
                            qty = format(unit_order_obj.quantity,'.2f')
                            item["qty"] = qty
                            price = format(unit_order_obj.get_subtotal_without_vat(),'.2f')
                            item["price"] = price

                            order_information["items"].append(item)

                        orig_result_pre = create_intercompany_sales_order(company_code, order_information)

                        for item in order_information["items"]:
                            
                            temp_dict2 = {}
                            temp_dict2["seller_sku"] = item["seller_sku"]
                            temp_dict2["intercompany_sales_info"] = orig_result_pre
                            
                            sap_info_render.append(temp_dict2)
                            
                            unit_order_obj = UnitOrder.objects.get(product__product__base_product__seller_sku=item["seller_sku"],order=order_obj)
                            
                            result_pre = orig_result_pre["doc_list"]
                            do_exists = 0
                            so_exists = 0
                            do_id = ""
                            so_id = ""
                            
                            for k in result_pre:
                                if k["type"]=="DO":
                                    do_exists = 1
                                    do_id = k["id"]
                                elif k["type"]=="SO":
                                    so_exists = 1
                                    so_id = k["id"]
                            
                            if so_exists==0 or do_exists==0:
                                error_flag = 1
                                unit_order_obj.sap_status = "Failed"
                                unit_order_obj.sap_intercompany_info = json.dumps(orig_result_pre)
                                unit_order_obj.save()
                                continue
                            
                            unit_order_information = {}
                            unit_order_information["intercompany_sales_info"] = {}
                            item["order_id"] = str(order_information["order_id"])
                            unit_order_information["intercompany_sales_info"] = item
                            unit_order_obj.order_information = json.dumps(unit_order_information)
                            
                            unit_order_obj.grn_filename = str(do_id)
                            unit_order_obj.sap_intercompany_info = json.dumps(orig_result_pre)
                            unit_order_obj.sap_status = "In GRN"
                            unit_order_obj.save()
                        
            for unit_order_obj in UnitOrder.objects.filter(order=order_obj):
                set_shipping_method(unit_order_obj, shipping_method)

            response["sap_info_render"] = sap_info_render
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SetShippingMethodAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SetOrdersStatusAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SetOrdersStatusAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            order_status = data["orderStatus"]
            unit_order_uuid_list = data["unitOrderUuidList"]

            for unit_order_uuid in unit_order_uuid_list:
                unit_order_obj = UnitOrder.objects.get(uuid=unit_order_uuid)
                set_order_status(unit_order_obj, order_status)

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SetOrdersStatusAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CancelOrdersAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("CancelOrdersAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            unit_order_uuid_list = data["unitOrderUuidList"]
            cancelling_note = data["cancellingNote"]

            for unit_order_uuid in unit_order_uuid_list:
                unit_order_obj = UnitOrder.objects.get(uuid=unit_order_uuid)
                cancel_order_admin(unit_order_obj, cancelling_note)

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CancelOrdersAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DownloadOrdersAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("DownloadOrdersAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            from_date = data.get("fromDate", "")
            to_date = data.get("toDate", "")
            payment_type_list = data.get("paymentTypeList", [])
            min_qty = data.get("minQty", "")
            max_qty = data.get("maxQty", "")
            min_price = data.get("minPrice", "")
            max_price = data.get("maxPrice", "")
            currency_list = data.get("currencyList", [])
            shipping_method_list = data.get("shippingMethodList", [])
            tracking_status_list = data.get("trackingStatusList", [])
            location_group_uuid = data["locationGroupUuid"]

            report_type = data.get("reportType")

            unit_order_objs = UnitOrder.objects.filter(order__location_group__uuid=location_group_uuid).order_by('-pk')

            if from_date!="":
                from_date = from_date[:10]+"T00:00:00+04:00"
                unit_order_objs = unit_order_objs.filter(order__order_placed_date__gte=from_date)
            if to_date!="":
                to_date = to_date[:10]+"T23:59:59+04:00"
                unit_order_objs = unit_order_objs.filter(order__order_placed_date__lte=to_date)
            if len(payment_type_list)>0:
                unit_order_objs = unit_order_objs.filter(order__payment_mode__in=payment_type_list)
            if len(shipping_method_list)>0:
                unit_order_objs = unit_order_objs.filter(shipping_method__in=shipping_method_list)
            if len(tracking_status_list)>0:
                unit_order_objs = unit_order_objs.filter(current_status_admin__in=tracking_status_list)
            if max_qty!="":
                unit_order_objs = unit_order_objs.filter(quantity__lte=int(max_qty))
            if min_qty!="":
                unit_order_objs = unit_order_objs.filter(quantity__gte=int(min_qty))
            if max_price!="":
                unit_order_objs = unit_order_objs.filter(price__lte=int(max_price))
            if min_price!="":
                unit_order_objs = unit_order_objs.filter(price__gte=int(min_price))

            order_objs = Order.objects.filter(unitorder__in=unit_order_objs).distinct().order_by("-order_placed_date")

            unit_order_list = []
            for order_obj in order_objs[:500]:
                try:
                    address_obj = order_obj.shipping_address

                    shipping_address = address_obj.get_shipping_address()
                    customer_name = address_obj.first_name
                    area = json.loads(address_obj.address_lines)[2]

                    delivery_fee_with_vat = order_obj.get_delivery_fee()
                    delivery_fee_vat = order_obj.get_delivery_fee_vat()
                    delivery_fee_without_vat = order_obj.get_delivery_fee_without_vat()

                    cod_fee_with_vat = order_obj.get_cod_charge()
                    cod_fee_vat = order_obj.get_cod_charge_vat()
                    cod_fee_without_vat = order_obj.get_cod_charge_without_vat()

                    for unit_order_obj in unit_order_objs.filter(order=order_obj):

                        subtotal_with_vat = unit_order_obj.get_subtotal()
                        subtotal_vat = unit_order_obj.get_total_vat()
                        subtotal_without_vat = unit_order_obj.get_subtotal_without_vat()

                        tracking_status_time = str(timezone.localtime(UnitOrderStatus.objects.filter(unit_order=unit_order_obj).last().date_created).strftime("%d %b, %Y %I:%M %p"))

                        temp_dict = {
                            "orderPlacedDate": str(timezone.localtime(order_obj.order_placed_date).strftime("%d %b, %Y %I:%M %p")),
                            "bundleId": order_obj.bundleid,
                            "orderId": unit_order_obj.orderid,
                            "productUuid": unit_order_obj.product.uuid,
                            "quantity": str(unit_order_obj.quantity),
                            "price": str(unit_order_obj.price),
                            "deliveryFeeWithVat": str(delivery_fee_with_vat),
                            "deliveryFeeVat": str(delivery_fee_vat),
                            "deliveryFeeWithoutVat": str(delivery_fee_without_vat),
                            "codFeeWithVat": str(cod_fee_with_vat),
                            "codFeeVat": str(cod_fee_vat),
                            "codFeeWithoutVat": str(cod_fee_without_vat),
                            "subtotalWithVat": str(subtotal_with_vat),
                            "subtotalVat": str(subtotal_vat),
                            "subtotalWithoutVat": str(subtotal_without_vat),
                            "customerName": customer_name,
                            "customerEmail": order_obj.owner.email,
                            "customerContactNumber": str(order_obj.owner.contact_number),
                            "shippingAddress": shipping_address,
                            "paymentStatus": order_obj.payment_status,
                            "shippingMethod": unit_order_obj.shipping_method,
                            "trackingStatus": unit_order_obj.current_status_admin,
                            "trackingStatusTime": tracking_status_time,
                            "area": area,
                            "total": str(round(float(unit_order_obj.price)*float(unit_order_obj.quantity), 2))
                        }
                        unit_order_list.append(temp_dict)

                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("DownloadOrdersAPI: %s at %s", e, str(exc_tb.tb_lineno))

            if report_type=="sap":
                generate_sap_order_format(unit_order_list)
                response["filepath"] = SERVER_IP+"/files/csv/sap-order-format.xlsx?abc=1"
            else:
                generate_regular_order_format(unit_order_list)
                response["filepath"] = SERVER_IP+"/files/csv/regular-order-format.xlsx?abc=2"
            
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DownloadOrdersAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadOrdersAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UploadOrdersAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            path = default_storage.save('tmp/temp-orders.xlsx', data["import_file"])
            path = "http://cdn.omnycomm.com.s3.amazonaws.com/"+path
            dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
            rows = len(dfs.iloc[:])

            order_list = []
            for i in range(rows):
                success = 0
                total = rows
                try:
                    order_id = str(dfs.iloc[i][0]).strip()
                    order_status = str(dfs.iloc[i][1]).strip()
                    shipping_method = str(dfs.iloc[i][2]).strip()
                    description = str(dfs.iloc[i][3]).strip()

                    unit_order_obj = UnitOrder.objects.get(orderid=order_id)
                    if order_status in ["picked", "dispatched", "delivered", "delivery failed"]:
                        set_order_status(unit_order_obj, order_status)
                    elif order_status=="approved":
                        set_shipping_method(unit_order_obj, shipping_method)
                    elif order_status=="cancelled":
                        cancel_order_admin(unit_order_obj, description)
                    success += 1
                except Exception as e:
                    pass

            response["totalOrders"] = str(total)
            response["successOrders"] = str(success)
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadOrdersAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class ApplyVoucherCodeAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("ApplyVoucherCodeAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            voucher_code = data["voucher_code"]

            is_fast_cart = data.get("is_fast_cart", False)

            if Voucher.objects.filter(is_deleted=False, is_published=True, voucher_code=voucher_code, location_group=location_group_obj).exists()==False:
                response["error_message"] = "INVALID CODE"
                response["voucher_success"] = False
                response["status"] = 200
                return Response(data=response)

            voucher_obj = Voucher.objects.get(is_deleted=False, is_published=True, voucher_code=voucher_code, location_group=location_group_obj)
            if voucher_obj.is_expired()==True:
                response["error_message"] = "EXPIRED"
                response["voucher_success"] = False
                response["status"] = 200
                return Response(data=response)

            subtotal = 0
            owner = None
            cart_obj = None
            fast_cart_obj = None
            if is_fast_cart==False:
                cart_obj = Cart.objects.get(location_group=location_group_obj, owner__username=request.user.username)
                subtotal = cart_obj.get_subtotal()
                owner = cart_obj.owner
            else:
                fast_cart_obj = FastCart.objects.get(location_group=location_group_obj, owner__username=request.user.username)
                subtotal = fast_cart_obj.get_subtotal()
                owner = fast_cart_obj.owner

            if voucher_obj.is_eligible(subtotal)==False:
                response["error_message"] = "NOT APPLICABLE"
                response["voucher_success"] = False
                response["status"] = 200
                return Response(data=response)

            if is_voucher_limt_exceeded_for_customer(owner, voucher_obj)==True:
                response["error_message"] = "LIMIT EXCEEDED"
                response["voucher_success"] = False
                response["status"] = 200
                return Response(data=response)
            
            if is_fast_cart==False:
                cart_obj.voucher = voucher_obj
                cart_obj.save()

                update_cart_bill(cart_obj)

                subtotal = cart_obj.get_subtotal()
                
                delivery_fee = cart_obj.get_delivery_fee()
                total_amount = cart_obj.get_total_amount()
                vat = cart_obj.get_vat()

                delivery_fee_with_cod = cart_obj.get_delivery_fee(cod=True)
                total_amount_with_cod = cart_obj.get_total_amount(cod=True)
                vat_with_cod = cart_obj.get_vat(cod=True)

                is_voucher_applied = cart_obj.voucher!=None
                voucher_discount = 0
                voucher_code = ""
                if is_voucher_applied:
                    voucher_discount = cart_obj.voucher.get_voucher_discount(subtotal)
                    voucher_code = cart_obj.voucher.voucher_code
                    if cart_obj.voucher.voucher_type=="SD":
                        delivery_fee = delivery_fee_with_cod
                        voucher_discount = delivery_fee

                response["currency"] = cart_obj.get_currency()
                response["subtotal"] = subtotal

                response["cardBill"] = {
                    "vat": vat,
                    "toPay": total_amount,
                    "delivery_fee": delivery_fee,
                    "is_voucher_applied": is_voucher_applied,
                    "voucher_discount": voucher_discount,
                    "voucher_code": voucher_code
                }
                response["codBill"] = {
                    "vat": vat_with_cod,
                    "toPay": total_amount_with_cod,
                    "delivery_fee": delivery_fee_with_cod,
                    "codCharge": location_group_obj.cod_charge,
                    "is_voucher_applied": is_voucher_applied,
                    "voucher_discount": voucher_discount,
                    "voucher_code": voucher_code
                }
            else:
                fast_cart_obj.voucher = voucher_obj
                fast_cart_obj.save()

                update_fast_cart_bill(fast_cart_obj)

                subtotal = fast_cart_obj.get_subtotal()
                
                delivery_fee = fast_cart_obj.get_delivery_fee()
                total_amount = fast_cart_obj.get_total_amount()
                vat = fast_cart_obj.get_vat()

                delivery_fee_with_cod = fast_cart_obj.get_delivery_fee(cod=True)
                total_amount_with_cod = fast_cart_obj.get_total_amount(cod=True)
                vat_with_cod = fast_cart_obj.get_vat(cod=True)

                is_voucher_applied = fast_cart_obj.voucher!=None
                voucher_discount = 0
                voucher_code = ""
                if is_voucher_applied:
                    voucher_discount = fast_cart_obj.voucher.get_voucher_discount(subtotal)
                    voucher_code = fast_cart_obj.voucher.voucher_code
                    if fast_cart_obj.voucher.voucher_type=="SD":
                        delivery_fee = delivery_fee_with_cod
                        voucher_discount = delivery_fee


                response["currency"] = fast_cart_obj.get_currency()
                response["subtotal"] = subtotal

                response["cardBill"] = {
                    "vat": vat,
                    "toPay": total_amount,
                    "delivery_fee": delivery_fee,
                    "is_voucher_applied": is_voucher_applied,
                    "voucher_discount": voucher_discount,
                    "voucher_code": voucher_code
                }
                response["codBill"] = {
                    "vat": vat_with_cod,
                    "toPay": total_amount_with_cod,
                    "delivery_fee": delivery_fee_with_cod,
                    "codCharge": location_group_obj.cod_charge,
                    "is_voucher_applied": is_voucher_applied,
                    "voucher_discount": voucher_discount,
                    "voucher_code": voucher_code
                }

            response["voucher_success"] = True
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ApplyVoucherCodeAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class RemoveVoucherCodeAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("RemoveVoucherCodeAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            is_fast_cart = data.get("is_fast_cart", False)

            if is_fast_cart==False:
                cart_obj = Cart.objects.get(location_group=location_group_obj, owner__username=request.user.username)
                cart_obj.voucher = None
                cart_obj.save()

                update_cart_bill(cart_obj)

                subtotal = cart_obj.get_subtotal()
                
                delivery_fee = cart_obj.get_delivery_fee()
                total_amount = cart_obj.get_total_amount()
                vat = cart_obj.get_vat()

                delivery_fee_with_cod = cart_obj.get_delivery_fee(cod=True)
                total_amount_with_cod = cart_obj.get_total_amount(cod=True)
                vat_with_cod = cart_obj.get_vat(cod=True)

                is_voucher_applied = cart_obj.voucher!=None
                voucher_discount = 0
                voucher_code = ""
                if is_voucher_applied:
                    voucher_discount = cart_obj.voucher.get_voucher_discount(subtotal)
                    voucher_code = cart_obj.voucher.voucher_code
                    if cart_obj.voucher.voucher_type=="SD":
                        delivery_fee = delivery_fee_with_cod
                        voucher_discount = delivery_fee

                response["currency"] = cart_obj.get_currency()
                response["subtotal"] = subtotal

                response["cardBill"] = {
                    "vat": vat,
                    "toPay": total_amount,
                    "delivery_fee": delivery_fee,
                    "is_voucher_applied": is_voucher_applied,
                    "voucher_discount": voucher_discount,
                    "voucher_code": voucher_code
                }
                response["codBill"] = {
                    "vat": vat_with_cod,
                    "toPay": total_amount_with_cod,
                    "delivery_fee": delivery_fee_with_cod,
                    "codCharge": location_group_obj.cod_charge,
                    "is_voucher_applied": is_voucher_applied,
                    "voucher_discount": voucher_discount,
                    "voucher_code": voucher_code
                }
            else:
                fast_cart_obj = FastCart.objects.get(location_group=location_group_obj, owner__username=request.user.username)
                fast_cart_obj.voucher = None
                fast_cart_obj.save()

                update_fast_cart_bill(fast_cart_obj)

                subtotal = fast_cart_obj.get_subtotal()
                
                delivery_fee = fast_cart_obj.get_delivery_fee()
                total_amount = fast_cart_obj.get_total_amount()
                vat = fast_cart_obj.get_vat()

                delivery_fee_with_cod = fast_cart_obj.get_delivery_fee(cod=True)
                total_amount_with_cod = fast_cart_obj.get_total_amount(cod=True)
                vat_with_cod = fast_cart_obj.get_vat(cod=True)

                is_voucher_applied = fast_cart_obj.voucher!=None
                voucher_discount = 0
                voucher_code = ""
                if is_voucher_applied:
                    voucher_discount = fast_cart_obj.voucher.get_voucher_discount(subtotal)
                    voucher_code = fast_cart_obj.voucher.voucher_code
                    if fast_cart_obj.voucher.voucher_type=="SD":
                        delivery_fee = delivery_fee_with_cod
                        voucher_discount = delivery_fee

                response["currency"] = fast_cart_obj.get_currency()
                response["subtotal"] = subtotal

                response["cardBill"] = {
                    "vat": vat,
                    "toPay": total_amount,
                    "delivery_fee": delivery_fee,
                    "is_voucher_applied": is_voucher_applied,
                    "voucher_discount": voucher_discount,
                    "voucher_code": voucher_code
                }
                response["codBill"] = {
                    "vat": vat_with_cod,
                    "toPay": total_amount_with_cod,
                    "delivery_fee": delivery_fee_with_cod,
                    "codCharge": location_group_obj.cod_charge,
                    "is_voucher_applied": is_voucher_applied,
                    "voucher_discount": voucher_discount,
                    "voucher_code": voucher_code
                }
            response["voucher_success"] = True
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("RemoveVoucherCodeAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class ApplyOfflineVoucherCodeAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("ApplyOfflineVoucherCodeAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            voucher_code = data["voucher_code"]

            username = data["username"]

            if Voucher.objects.filter(is_deleted=False, is_published=True, voucher_code=voucher_code, location_group=location_group_obj).exists()==False:
                response["error_message"] = "INVALID CODE"
                response["voucher_success"] = False
                response["status"] = 200
                return Response(data=response)

            voucher_obj = Voucher.objects.get(is_deleted=False, is_published=True, voucher_code=voucher_code, location_group=location_group_obj)
            if voucher_obj.is_expired()==True:
                response["error_message"] = "EXPIRED"
                response["voucher_success"] = False
                response["status"] = 200
                return Response(data=response)

            cart_obj = Cart.objects.get(location_group=location_group_obj, owner__username=username)

            if voucher_obj.is_eligible(cart_obj.get_subtotal())==False:
                response["error_message"] = "NOT APPLICABLE"
                response["voucher_success"] = False
                response["status"] = 200
                return Response(data=response)

            if is_voucher_limt_exceeded_for_customer(cart_obj.owner, voucher_obj)==True:
                response["error_message"] = "LIMIT EXCEEDED"
                response["voucher_success"] = False
                response["status"] = 200
                return Response(data=response)
            
            cart_obj.voucher = voucher_obj
            cart_obj.save()

            update_cart_bill(cart_obj)

            subtotal = cart_obj.get_subtotal()
            
            delivery_fee = cart_obj.get_delivery_fee()
            total_amount = cart_obj.get_total_amount()
            vat = cart_obj.get_vat()

            delivery_fee_with_cod = cart_obj.get_delivery_fee(cod=True, offline=True)
            total_amount_with_cod = cart_obj.get_total_amount(cod=True, offline=True)
            vat_with_cod = cart_obj.get_vat(cod=True, offline=True)

            is_voucher_applied = cart_obj.voucher!=None
            voucher_discount = 0
            voucher_code = ""
            if is_voucher_applied:
                voucher_discount = cart_obj.voucher.get_voucher_discount(subtotal)
                voucher_code = cart_obj.voucher.voucher_code
                if cart_obj.voucher.voucher_type=="SD":
                    delivery_fee = delivery_fee_with_cod
                    voucher_discount = delivery_fee

            response["currency"] = cart_obj.get_currency()
            response["subtotal"] = subtotal

            response["cardBill"] = {
                "vat": vat,
                "toPay": total_amount,
                "delivery_fee": delivery_fee,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }
            response["codBill"] = {
                "vat": vat_with_cod,
                "toPay": total_amount_with_cod,
                "delivery_fee": delivery_fee_with_cod,
                "codCharge": cart_obj.location_group.cod_charge,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }
            response["voucher_success"] = True
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ApplyOfflineVoucherCodeAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class RemoveOfflineVoucherCodeAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("RemoveOfflineVoucherCodeAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            username = data["username"]

            cart_obj = Cart.objects.get(location_group=location_group_obj, owner__username=username)
            cart_obj.voucher = None
            cart_obj.save()

            update_cart_bill(cart_obj)

            subtotal = cart_obj.get_subtotal()
            
            delivery_fee = cart_obj.get_delivery_fee()
            total_amount = cart_obj.get_total_amount()
            vat = cart_obj.get_vat()

            delivery_fee_with_cod = cart_obj.get_delivery_fee(cod=True, offline=True)
            total_amount_with_cod = cart_obj.get_total_amount(cod=True, offline=True)
            vat_with_cod = cart_obj.get_vat(cod=True, offline=True)

            is_voucher_applied = cart_obj.voucher!=None
            voucher_discount = 0
            voucher_code = ""
            if is_voucher_applied:
                voucher_discount = cart_obj.voucher.get_voucher_discount(subtotal)
                voucher_code = cart_obj.voucher.voucher_code
                if cart_obj.voucher.voucher_type=="SD":
                    delivery_fee = delivery_fee_with_cod
                    voucher_discount = delivery_fee

            response["currency"] = cart_obj.get_currency()
            response["subtotal"] = subtotal

            response["cardBill"] = {
                "vat": vat,
                "toPay": total_amount,
                "delivery_fee": delivery_fee,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }
            response["codBill"] = {
                "vat": vat_with_cod,
                "toPay": total_amount_with_cod,
                "delivery_fee": delivery_fee_with_cod,
                "codCharge": cart_obj.location_group.cod_charge,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }
            response["voucher_success"] = True
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("RemoveOfflineVoucherCodeAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchOrderAnalyticsParamsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchOrderAnalyticsParamsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            import time
            time.sleep(2)

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            order_obj = Order.objects.filter(location_group__uuid=location_group_uuid, owner__username=request.user.username).order_by('-pk')[0]

            gtm_params = calculate_gtm(order_obj)

            response["order_summary"] = gtm_params["actionField"]
            response["order_products"] = gtm_params["products"]

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOrderAnalyticsParamsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class PlaceOnlineOrderAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("PlaceOnlineOrderAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            merchant_reference = data["merchant_reference"]

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            is_fast_cart = data.get("is_fast_cart", False)

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            order_obj = None

            if check_order_status_from_network_global(merchant_reference, location_group_obj)==False:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("PlaceOnlineOrderAPI: NETWORK GLOBAL STATUS MISMATCH! %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            if is_fast_cart==False:

                cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)

                update_cart_bill(cart_obj)

                unit_cart_objs = UnitCart.objects.filter(cart=cart_obj)

                try:
                    voucher_obj = cart_obj.voucher
                    if voucher_obj!=None:
                        if voucher_obj.is_expired()==False and is_voucher_limt_exceeded_for_customer(cart_obj.owner, voucher_obj)==False:
                            voucher_obj.total_usage += 1
                            voucher_obj.save()
                        else:
                            cart_obj.voucher = None
                            cart_obj.save()
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.warning("PlaceOnlineOrderAPI: voucher code not handled properly! %s at %s", e, str(exc_tb.tb_lineno))

                payment_info = "NA"
                payment_mode = "NA"
                try:
                    payment_info = data["paymentMethod"]
                    payment_mode = data["paymentMethod"]["name"]
                except Exception as e:
                    pass

                order_obj = Order.objects.create(owner=cart_obj.owner,
                                                 shipping_address=cart_obj.shipping_address,
                                                 to_pay=cart_obj.to_pay,
                                                 order_placed_date=timezone.now(),
                                                 voucher=cart_obj.voucher,
                                                 location_group=cart_obj.location_group,
                                                 payment_status="paid",
                                                 payment_info=payment_info,
                                                 payment_mode=payment_mode,
                                                 merchant_reference=merchant_reference,
                                                 delivery_fee=cart_obj.get_delivery_fee(),
                                                 cod_charge=0)

                for unit_cart_obj in unit_cart_objs:
                    unit_order_obj = UnitOrder.objects.create(order=order_obj,
                                                              product=unit_cart_obj.product,
                                                              quantity=unit_cart_obj.quantity,
                                                              price=unit_cart_obj.product.get_actual_price_for_customer(dealshub_user_obj))
                    UnitOrderStatus.objects.create(unit_order=unit_order_obj)

                # Cart gets empty
                for unit_cart_obj in unit_cart_objs:
                    unit_cart_obj.delete()

                # cart_obj points to None
                cart_obj.shipping_address = None
                cart_obj.voucher = None
                cart_obj.to_pay = 0
                cart_obj.merchant_reference = ""
                cart_obj.payment_info = "{}"
                cart_obj.save()
            else:
                fast_cart_obj = FastCart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)

                try:
                    if fast_cart_obj.shipping_address==None:
                        address_obj = Address.objects.filter(user=dealshub_user_obj)[0]
                        fast_cart_obj.shipping_address = address_obj
                        fast_cart_obj.save()
                except Exception as e:
                    pass

                update_fast_cart_bill(fast_cart_obj)

                try:
                    voucher_obj = cart_obj.voucher
                    if voucher_obj!=None:
                        if voucher_obj.is_expired()==False and is_voucher_limt_exceeded_for_customer(cart_obj.owner, voucher_obj)==False:
                            voucher_obj.total_usage += 1
                            voucher_obj.save()
                        else:
                            cart_obj.voucher = None
                            cart_obj.save()
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.warning("PlaceOnlineOrderAPI: voucher code not handled properly! %s at %s", e, str(exc_tb.tb_lineno))

                payment_info = "NA"
                payment_mode = "NA"
                try:
                    payment_info = data["paymentMethod"]
                    payment_mode = data["paymentMethod"]["name"]
                except Exception as e:
                    pass

                order_obj = Order.objects.create(owner=fast_cart_obj.owner,
                                                 shipping_address=fast_cart_obj.shipping_address,
                                                 to_pay=fast_cart_obj.to_pay,
                                                 order_placed_date=timezone.now(),
                                                 voucher=fast_cart_obj.voucher,
                                                 location_group=fast_cart_obj.location_group,
                                                 payment_status="paid",
                                                 payment_info=payment_info,
                                                 payment_mode=payment_mode,
                                                 merchant_reference=merchant_reference,
                                                 delivery_fee=fast_cart_obj.get_delivery_fee(),
                                                 cod_charge=0)

                unit_order_obj = UnitOrder.objects.create(order=order_obj,
                                                          product=fast_cart_obj.product,
                                                          quantity=fast_cart_obj.quantity,
                                                          price=fast_cart_obj.product.get_actual_price_for_customer(dealshub_user_obj))
                UnitOrderStatus.objects.create(unit_order=unit_order_obj)

                # cart_obj points to None
                fast_cart_obj.shipping_address = None
                fast_cart_obj.voucher = None
                fast_cart_obj.to_pay = 0
                fast_cart_obj.merchant_reference = ""
                fast_cart_obj.payment_info = "{}"
                fast_cart_obj.product = None
                fast_cart_obj.save()

            # Trigger Email
            try:
                p1 = threading.Thread(target=send_order_confirmation_mail, args=(order_obj,))
                p1.start()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("PlaceOnlineOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))

            # Refresh Stock
            refresh_stock(order_obj)

            response["purchase"] = calculate_gtm(order_obj)

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PlaceOnlineOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchPostaPlusTrackingAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchPostaPlusTrackingAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            order_uuid = data["uuid"]

            awb_number = json.loads(Order.objects.get(uuid=order_uuid).postaplus_info)["awb_number"]

            postaplus_tracking_response = fetch_postaplus_tracking(awb_number)

            response["tracking_data"] = postaplus_tracking_response
            response["awb_number"] = awb_number
            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchPostaPlusTrackingAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchFastCartDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchFastCartDetailsAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            fast_cart_obj = FastCart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
            
            cart_details = {}
            cart_details["uuid"] = fast_cart_obj.uuid
            cart_details["quantity"] = fast_cart_obj.quantity
            cart_details["price"] = fast_cart_obj.product.get_actual_price_for_customer(dealshub_user_obj)
            cart_details["showNote"] = fast_cart_obj.product.is_promo_restriction_note_required(dealshub_user_obj)
            cart_details["stock"] = fast_cart_obj.product.stock
            cart_details["allowedQty"] = fast_cart_obj.product.get_allowed_qty()
            cart_details["currency"] = fast_cart_obj.product.get_currency()
            cart_details["productName"] = fast_cart_obj.product.get_name()
            cart_details["productImageUrl"] = fast_cart_obj.product.get_display_image_url()
            cart_details["productUuid"] = fast_cart_obj.product.uuid
            cart_details["brand"] = fast_cart_obj.product.get_brand()
            cart_details["isStockAvailable"] = fast_cart_obj.product.stock > 0

            update_fast_cart_bill(fast_cart_obj)

            subtotal = fast_cart_obj.get_subtotal()
            
            delivery_fee = fast_cart_obj.get_delivery_fee()
            total_amount = fast_cart_obj.get_total_amount()
            vat = fast_cart_obj.get_vat()

            delivery_fee_with_cod = fast_cart_obj.get_delivery_fee(cod=True)
            total_amount_with_cod = fast_cart_obj.get_total_amount(cod=True)
            vat_with_cod = fast_cart_obj.get_vat(cod=True)

            is_voucher_applied = fast_cart_obj.voucher!=None
            voucher_discount = 0
            voucher_code = ""
            if is_voucher_applied:
                voucher_discount = fast_cart_obj.voucher.get_voucher_discount(subtotal)
                voucher_code = fast_cart_obj.voucher.voucher_code
                if fast_cart_obj.voucher.voucher_type=="SD":
                    delivery_fee = delivery_fee_with_cod
                    voucher_discount = delivery_fee

            response["currency"] = fast_cart_obj.get_currency()
            response["subtotal"] = subtotal

            response["cardBill"] = {
                "vat": vat,
                "toPay": total_amount,
                "delivery_fee": delivery_fee,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }
            response["codBill"] = {
                "vat": vat_with_cod,
                "toPay": total_amount_with_cod,
                "delivery_fee": delivery_fee_with_cod,
                "codCharge": fast_cart_obj.location_group.cod_charge,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }
            
            response["cartDetails"] = cart_details
            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFastCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class GRNProcessingCronAPI(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("GRNProcessingCronAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            from ftplib import FTP
            ftp=FTP()
            ftp.connect('geepasftp.selfip.com', 2221)
            ftp.login('mapftpdev','western')
            files = []
            files = ftp.nlst(GRN_FOLDER_NAME)

            for f in files:
                search_file = f.split("_")[0]
                if UnitOrder.objects.filter(grn_filename=search_file).exclude(sap_status="GRN Done").exclude(sap_status="GRN Conflict").exists():
                    
                    unit_order_objs = UnitOrder.objects.filter(grn_filename=search_file)
                    
                    ftp.cwd('/'+GRN_FOLDER_NAME)
                    with open(f, "wb") as file:
                        # use FTP's RETR command to download the file
                        ftp.retrbinary(f"RETR {f}", file.write)

                    fp = open(f, 'rb')
                    GRN_File = fp.read().decode('utf-8')

                    GRN_products = GRN_File.split('\n')
                    GRN_products = GRN_products[:-1]

                    GRN_information_dict = {}

                    for product in GRN_products:
                        info = product.split(';')
                        temp_dict = {}
                        seller_sku = info[1]
                        temp_dict["seller_sku"] = seller_sku
                        temp_dict["location"] = info[2]
                        temp_dict["batch"] = info[3]
                        temp_dict["qty"] = info[4]
                        temp_dict["uom"] = info[5]
                        GRN_information_dict[seller_sku] = temp_dict

                    for unit_order_obj in unit_order_objs:
                        
                        unit_order_information = json.loads(unit_order_obj.order_information)
                        unit_order_information["final_billing_info"] = {}

                        seller_sku = unit_order_obj.product.get_seller_sku()
                        GRN_info = GRN_information_dict.get(seller_sku,None)

                        if GRN_info != None:
                            GRN_info["from_holding"] = unit_order_information["intercompany_sales_info"]["from_holding"]
                            GRN_info["price"] = unit_order_information["intercompany_sales_info"]["price"]
                            unit_order_information["final_billing_info"] = GRN_info
                        
                        unit_order_obj.order_information = json.dumps(unit_order_information)
                        unit_order_obj.grn_filename_exists = True
                        unit_order_obj.sap_status = "GRN Done"
                        unit_order_obj.save()

                    try :
                        ftp.delete(f)
                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        logger.error("GRNProcessingCronAPI FTP delete error for %s: %s at %s", f,e, str(exc_tb.tb_lineno))
                        pass

                    order_obj = unit_order_objs[0].order
                    unit_order_objs = UnitOrder.objects.filter(order=order_obj,grn_filename_exists=False)

                    if unit_order_objs.count() == 0:
                    
                        order_information = {}

                        if order_obj.payment_status=="paid":
                            order_information["order_type"] = "ZJCR"
                        else:
                            order_information["order_type"] = "ZJCD"

                        order_information["city"] = str(order_obj.location_group.location.name)
                        order_information["customer_name"] = order_obj.get_customer_full_name()
                        order_information["order_id"] = order_obj.bundleid.replace("-","")
                        order_information["refrence_id"] = order_obj.bundleid.replace("-","&#8211;")
                        order_information["charges"] = get_all_the_charges(order_obj)
                        order_information["customer_id"] = order_obj.get_customer_id_for_final_sap_billing()

                        unit_order_information_list = []

                        for unit_order_obj in UnitOrder.objects.filter(order=order_obj):

                            unit_order_final_billing_information = json.loads(unit_order_obj.order_information)["final_billing_info"]
                            
                            if unit_order_final_billing_information != {}:
                                unit_order_information_list.append(unit_order_final_billing_information)
                        
                        order_information["unit_order_information_list"] = unit_order_information_list

                        result = create_final_order(WIGME_COMPANY_CODE, order_information)
                        
                        doc_list = result["doc_list"]
                        do_exists = 0
                        so_exists = 0
                        inv_exists = 0
                        
                        for k in doc_list:
                            if k["message_type"] == "S":
                                if k["type"]=="DO":
                                    do_exists+=1
                                elif k["type"]=="SO":
                                    so_exists+=1
                                elif k["type"]=="INV":
                                    inv_exists+=1

                        if do_exists==2 and so_exists==1 and inv_exists==1:
                            order_obj.sap_status = "Success"
                        else:
                            order_obj.sap_status = "Failed"

                        order_obj.sap_final_billing_info = json.dumps(result)
                        order_obj.order_information = json.dumps(order_information)
                        order_obj.save()

                        refresh_stock(order_obj)

                    # Remove file from ftp - TBD

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("GRNProcessingCronAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class UpdateUserNameAndEmailAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateUserNameAndEmailAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            contact_number = data["contactNumber"]
            location_group_uuid = data["locationGroupUuid"]
            first_name = data["firstName"]
            email = data["email"]

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group
            website_group_name = website_group_obj.name.lower()

            dealshub_user_obj = DealsHubUser.objects.get(username=contact_number+"-"+website_group_name)
            
            dealshub_user_obj.first_name = first_name
            dealshub_user_obj.email = email
            dealshub_user_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateUserNameAndEmailAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


FetchShippingAddressList = FetchShippingAddressListAPI.as_view()

EditShippingAddress = EditShippingAddressAPI.as_view()

CreateShippingAddress = CreateShippingAddressAPI.as_view()

CreateOfflineShippingAddress = CreateOfflineShippingAddressAPI.as_view()

DeleteShippingAddress = DeleteShippingAddressAPI.as_view()

AddToCart = AddToCartAPI.as_view()

AddToFastCart = AddToFastCartAPI.as_view()

AddToOfflineCart = AddToOfflineCartAPI.as_view()

FetchCartDetails = FetchCartDetailsAPI.as_view()

FetchOfflineCartDetails = FetchOfflineCartDetailsAPI.as_view()

UpdateCartDetails = UpdateCartDetailsAPI.as_view()

RemoveFromCart = RemoveFromCartAPI.as_view()

SelectAddress = SelectAddressAPI.as_view()

SelectOfflineAddress = SelectOfflineAddressAPI.as_view()

SelectPaymentMode = SelectPaymentModeAPI.as_view()

FetchActiveOrderDetails = FetchActiveOrderDetailsAPI.as_view()

PlaceOrder = PlaceOrderAPI.as_view()

PlaceOfflineOrder = PlaceOfflineOrderAPI.as_view()

CancelOrder = CancelOrderAPI.as_view()

FetchOrderList = FetchOrderListAPI.as_view()

FetchOrderListAdmin = FetchOrderListAdminAPI.as_view()

FetchOrderDetails = FetchOrderDetailsAPI.as_view()

CreateOfflineCustomer = CreateOfflineCustomerAPI.as_view()

UpdateOfflineUserProfile = UpdateOfflineUserProfileAPI.as_view()

SearchCustomerAutocomplete = SearchCustomerAutocompleteAPI.as_view()

FetchOfflineUserProfile = FetchOfflineUserProfileAPI.as_view()

FetchUserProfile = FetchUserProfileAPI.as_view()

UpdateUserProfile = UpdateUserProfileAPI.as_view()

FetchCustomerList = FetchCustomerListAPI.as_view()

FetchCustomerDetails = FetchCustomerDetailsAPI.as_view()

FetchCustomerOrders = FetchCustomerOrdersAPI.as_view()

FetchTokenRequestParameters = FetchTokenRequestParametersAPI.as_view()

MakePurchaseRequest = MakePurchaseRequestAPI.as_view()

PaymentTransaction = PaymentTransactionAPI.as_view()

PaymentNotification = PaymentNotificationAPI.as_view()

# FetchInstallmentPlans = FetchInstallmentPlansAPI.as_view()

# MakePurchaseRequestInstallment = MakePurchaseRequestInstallmentAPI.as_view()

CalculateSignature = CalculateSignatureAPI.as_view()

ContactUsSendEmail = ContactUsSendEmailAPI.as_view()

SendOTPSMSLogin = SendOTPSMSLoginAPI.as_view()

VerifyOTPSMSLogin = VerifyOTPSMSLoginAPI.as_view()

CheckUserPinSet = CheckUserPinSetAPI.as_view()

SetLoginPin = SetLoginPinAPI.as_view()

VerifyLoginPin = VerifyLoginPinAPI.as_view()

ForgotLoginPin = ForgotLoginPinAPI.as_view()

UpdateUserEmail = UpdateUserEmailAPI.as_view()

AddReview = AddReviewAPI.as_view()

AddRating = AddRatingAPI.as_view()

UpdateRating = UpdateRatingAPI.as_view()

AddAdminComment = AddAdminCommentAPI.as_view()

UpdateAdminComment = UpdateAdminCommentAPI.as_view()

AddUpvote = AddUpvoteAPI.as_view()

DeleteUpvote = DeleteUpvoteAPI.as_view()

FetchReview = FetchReviewAPI.as_view()

FetchProductReviews = FetchProductReviewsAPI.as_view()

DeleteUserReviewImage = DeleteUserReviewImageAPI.as_view()

DeleteUserReview = DeleteUserReviewAPI.as_view()

FetchOrdersForWarehouseManager = FetchOrdersForWarehouseManagerAPI.as_view()

FetchShippingMethod = FetchShippingMethodAPI.as_view()

SetShippingMethod = SetShippingMethodAPI.as_view()

SetOrdersStatus = SetOrdersStatusAPI.as_view()

CancelOrders = CancelOrdersAPI.as_view()

DownloadOrders = DownloadOrdersAPI.as_view()

UploadOrders = UploadOrdersAPI.as_view()

ApplyVoucherCode = ApplyVoucherCodeAPI.as_view()

RemoveVoucherCode = RemoveVoucherCodeAPI.as_view()

ApplyOfflineVoucherCode = ApplyOfflineVoucherCodeAPI.as_view()

RemoveOfflineVoucherCode = RemoveOfflineVoucherCodeAPI.as_view()

FetchOrderAnalyticsParams = FetchOrderAnalyticsParamsAPI.as_view()

PlaceOnlineOrder = PlaceOnlineOrderAPI.as_view()

FetchPostaPlusTracking = FetchPostaPlusTrackingAPI.as_view()

AddToWishList = AddToWishListAPI.as_view()

RemoveFromWishList = RemoveFromWishListAPI.as_view()

FetchWishList = FetchWishListAPI.as_view()

FetchFastCartDetails = FetchFastCartDetailsAPI.as_view()

BulkUpdateCartDetails = BulkUpdateCartDetailsAPI.as_view()

UpdateFastCartDetails = UpdateFastCartDetailsAPI.as_view()

GRNProcessingCron = GRNProcessingCronAPI.as_view()

UpdateUserNameAndEmail = UpdateUserNameAndEmailAPI.as_view()