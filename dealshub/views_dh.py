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

from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

from datetime import datetime

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
            first_name = data["firstName"]
            last_name = data["lastName"]
            line1 = data["line1"]
            line2 = data["line2"]
            line3 = data["line3"]
            line4 = data["line4"]
            address_lines = [line1, line2, line3, line4]
            state = data["state"]
            postcode = data["postcode"]
            contact_number = data["contactNumber"]
            tag = data.get("tag", "Home")

            address_obj = Address.objects.get(uuid=uuid)
            address_obj.first_name = first_name
            address_obj.last_name = last_name
            address_obj.address_lines = json.dumps(address_lines)
            address_obj.state = state
            address_obj.postcode = postcode
            address_obj.contact_number = contact_number
            address_obj.tag = tag
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
            last_name = data["lastName"]
            line1 = data["line1"]
            line2 = data["line2"]
            line3 = data["line3"]
            line4 = data["line4"]
            address_lines = json.dumps([line1, line2, line3, line4])
            state = data["state"]
            postcode = data["postcode"]
            if postcode==None:
                postcode = ""
            contact_number = data["contactNumber"]
            tag = data.get("tag", "")
            if tag==None:
                tag = ""

            if dealshub_user_obj.first_name=="":
                dealshub_user_obj.first_name = first_name
                dealshub_user_obj.last_name = last_name
                dealshub_user_obj.save()

            address_obj = Address.objects.create(first_name=first_name, last_name=last_name, address_lines=address_lines, state=state, postcode=postcode, contact_number=contact_number, user=dealshub_user_obj, tag=tag, location_group=location_group_obj)

            response["uuid"] = address_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateShippingAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))

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
            cart_obj, created = Cart.objects.get_or_create(owner=dealshub_user_obj, location_group=location_group_obj)
            unit_cart_obj = None
            if UnitCart.objects.filter(cart=cart_obj, product__uuid=product_uuid).exists()==True:
                unit_cart_obj = UnitCart.objects.get(cart=cart_obj, product__uuid=product_uuid)
                unit_cart_obj.quantity += quantity
                unit_cart_obj.save()
            else:
                unit_cart_obj = UnitCart.objects.create(cart=cart_obj, product=dealshub_product_obj, quantity=quantity)

            update_cart_bill(cart_obj)

            delivery_fee = cart_obj.get_delivery_fee()
            subtotal = cart_obj.get_subtotal()
            total_amount = cart_obj.get_total_amount()
            vat = cart_obj.get_vat()
            vat_with_cod = cart_obj.get_vat_with_cod()

            response["deliveryFee"] = delivery_fee
            response["currency"] = cart_obj.get_currency()
            response["subtotal"] = subtotal

            response["cardBill"] = {
                "vat": vat,
                "toPay": total_amount
            }
            response["codBill"] = {
                "vat": vat_with_cod,
                "toPay": total_amount + cart_obj.location_group.cod_charge,
                "codCharge": cart_obj.location_group.cod_charge
            }

            response["unitCartUuid"] = unit_cart_obj.uuid
            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddToCartAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
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
            cart_obj, created = Cart.objects.get_or_create(owner=dealshub_user_obj, location_group=location_group_obj)
            unit_cart_objs = UnitCart.objects.filter(cart=cart_obj)
            unit_cart_list = []
            for unit_cart_obj in unit_cart_objs:
                temp_dict = {}
                temp_dict["uuid"] = unit_cart_obj.uuid
                temp_dict["quantity"] = unit_cart_obj.quantity
                temp_dict["price"] = unit_cart_obj.product.get_actual_price()
                temp_dict["currency"] = unit_cart_obj.product.get_currency()
                temp_dict["dateCreated"] = unit_cart_obj.get_date_created()
                temp_dict["productName"] = unit_cart_obj.product.get_name()
                temp_dict["productImageUrl"] = unit_cart_obj.product.get_display_image_url()
                temp_dict["productUuid"] = unit_cart_obj.product.uuid
                temp_dict["isStockAvailable"] = unit_cart_obj.product.stock > 0
                unit_cart_list.append(temp_dict)

            delivery_fee = cart_obj.get_delivery_fee()
            subtotal = cart_obj.get_subtotal()
            total_amount = cart_obj.get_total_amount()
            vat = cart_obj.get_vat()
            vat_with_cod = cart_obj.get_vat_with_cod()

            response["deliveryFee"] = delivery_fee
            response["currency"] = cart_obj.get_currency()
            response["subtotal"] = subtotal

            response["cardBill"] = {
                "vat": vat,
                "toPay": total_amount
            }
            response["codBill"] = {
                "vat": vat_with_cod,
                "toPay": total_amount + cart_obj.location_group.cod_charge,
                "codCharge": cart_obj.location_group.cod_charge
            }
            response["unitCartList"] = unit_cart_list
            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
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

            unit_cart_obj = UnitCart.objects.get(uuid=unit_cart_uuid)
            unit_cart_obj.quantity = quantity
            unit_cart_obj.save()

            update_cart_bill(unit_cart_obj.cart)

            cart_obj = unit_cart_obj.cart

            delivery_fee = cart_obj.get_delivery_fee()
            subtotal = cart_obj.get_subtotal()
            total_amount = cart_obj.get_total_amount()
            vat = cart_obj.get_vat()
            vat_with_cod = cart_obj.get_vat_with_cod()

            response["deliveryFee"] = delivery_fee
            response["currency"] = cart_obj.get_currency()
            response["subtotal"] = subtotal

            response["cardBill"] = {
                "vat": vat,
                "toPay": total_amount
            }
            response["codBill"] = {
                "vat": vat_with_cod,
                "toPay": total_amount + cart_obj.location_group.cod_charge,
                "codCharge": cart_obj.location_group.cod_charge
            }

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
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

            delivery_fee = cart_obj.get_delivery_fee()
            subtotal = cart_obj.get_subtotal()
            total_amount = cart_obj.get_total_amount()
            vat = cart_obj.get_vat()
            vat_with_cod = cart_obj.get_vat_with_cod()

            response["deliveryFee"] = delivery_fee
            response["currency"] = cart_obj.get_currency()
            response["subtotal"] = subtotal

            response["cardBill"] = {
                "vat": vat,
                "toPay": total_amount
            }
            response["codBill"] = {
                "vat": vat_with_cod,
                "toPay": total_amount + cart_obj.location_group.cod_charge,
                "codCharge": cart_obj.location_group.cod_charge
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
            cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=address_obj.location_group)
            
            cart_obj.shipping_address = address_obj
            cart_obj.save()

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SelectAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
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
                temp_dict["price"] = unit_cart_obj.product.get_actual_price()
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
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)

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
                                             location_group=cart_obj.location_group)

            for unit_cart_obj in unit_cart_objs:
                unit_order_obj = UnitOrder.objects.create(order=order_obj, 
                                                          product=unit_cart_obj.product,
                                                          quantity=unit_cart_obj.quantity,
                                                          price=unit_cart_obj.product.get_actual_price())
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
                logger.error("PlaceOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))

            # Refresh Stock
            refresh_stock(order_obj)

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PlaceOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
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
                voucher_obj = order_obj.voucher
                is_voucher_applied = voucher_obj is not None
                temp_dict = {}
                temp_dict["dateCreated"] = order_obj.get_date_created()
                temp_dict["paymentMode"] = order_obj.payment_mode
                temp_dict["paymentStatus"] = order_obj.payment_status
                temp_dict["customerName"] = order_obj.owner.first_name+" "+order_obj.owner.last_name
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
                    temp_dict["customerName"] = order_obj.owner.first_name+" "+order_obj.owner.last_name
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

            response["bundleId"] = order_obj.bundleid 
            response["dateCreated"] = order_obj.get_date_created()
            response["paymentMode"] = order_obj.payment_mode
            response["paymentStatus"] = order_obj.payment_status
            response["customerName"] = order_obj.owner.first_name + " " + order_obj.owner.last_name
            response["isVoucherApplied"] = is_voucher_applied
            if is_voucher_applied:
                response["voucherCode"] = voucher_obj.voucher_code

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
                temp_dict["currency"] = unit_order_obj.currency
                temp_dict["productName"] = unit_order_obj.product.get_name()
                temp_dict["productImageUrl"] = unit_order_obj.product.get_display_image_url()
                temp_dict["sellerSku"] = unit_order_obj.product.get_seller_sku()
                temp_dict["productId"] = unit_order_obj.product.get_product_id()

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


class FetchUserProfileAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchUserProfileAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            dealshub_user = DealsHubUser.objects.get(username=request.user.username)

            response["firstName"] = dealshub_user.first_name
            response["lastName"] = dealshub_user.last_name
            response["emailId"] = dealshub_user.email
            response["contactNumber"] = dealshub_user.contact_number

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
            last_name = data["lastName"]
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

            dealshub_user_objs = DealsHubUser.objects.none()
            if len(search_list)>0:
                for search_key in search_list:
                    dealshub_user_objs |= DealsHubUser.objects.filter(Q(first_name__icontains=search_key) | Q(last_name__icontains=search_key) | Q(contact_number__icontains=search_key))
                dealshub_user_objs = dealshub_user_objs.distinct().order_by('-pk')
            else:
                dealshub_user_objs = DealsHubUser.objects.all().order_by('-pk')

            filter_parameters = data.get("filter_parameters", {})

            if "is_feedback_available" in filter_parameters:
                if filter_parameters["is_feedback_available"]==True:
                    pass

            if "is_cart_empty" in filter_parameters:
                if filter_parameters["is_cart_empty"]==True:
                    cart_objs = UnitCart.objects.all().values("cart")
                    dealshub_user_objs = dealshub_user_objs.filter(cart=None) | dealshub_user_objs.exclude(cart__in=cart_objs)
                    dealshub_user_objs.distinct()
                elif filter_parameters["is_cart_empty"]==False:
                    cart_objs = UnitCart.objects.all().values("cart")
                    dealshub_user_objs = dealshub_user_objs.filter(cart__in=cart_objs)

            page = data.get("page", 1)
            total_customers = dealshub_user_objs.count()
            paginator = Paginator(dealshub_user_objs, 20)
            dealshub_user_objs = paginator.page(page)

            customer_list = []
            for dealshub_user_obj in dealshub_user_objs:
                try:
                    temp_dict = {}
                    temp_dict["name"] = dealshub_user_obj.first_name + " " + dealshub_user_obj.last_name
                    temp_dict["emailId"] = dealshub_user_obj.email
                    temp_dict["contactNumber"] = dealshub_user_obj.contact_number
                    temp_dict["username"] = dealshub_user_obj.username
                    temp_dict["is_cart_empty"] = not UnitCart.objects.filter(cart__owner=dealshub_user_obj).exists()
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
            temp_dict["customerName"] = dealshub_user_obj.first_name+" "+dealshub_user_obj.last_name
            temp_dict["emailId"] = dealshub_user_obj.email
            temp_dict["contactNumber"] = dealshub_user_obj.contact_number
            temp_dict["is_cart_empty"] = not UnitCart.objects.filter(cart__owner=dealshub_user_obj).exists()
            temp_dict["is_feedback_available"] = False
            address_list = []
            for address_obj in Address.objects.filter(user__username=dealshub_user_obj.username):
                address_list.append(", ".join(json.loads(address_obj.address_lines)))
            temp_dict["addressList"] = address_list

            review_objs = Review.objects.filter(dealshub_user=dealshub_user_obj)
            
            unit_cart_list = []
            for unit_cart_obj in UnitCart.objects.filter(cart__owner=dealshub_user_obj):
                temp_dict2 = {}
                temp_dict2["uuid"] = unit_cart_obj.uuid
                temp_dict2["quantity"] = unit_cart_obj.quantity
                temp_dict2["price"] = unit_cart_obj.product.get_actual_price()
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
                temp_dict["totalBilling"] = str(order_obj.to_pay) + " " + str(order_obj.location_group.currency)
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

            cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
            cart_obj.merchant_reference = merchant_reference
            cart_obj.save()

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

            cart_obj.payment_info = json.dumps(payment_response)
            cart_obj.save()

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
                cart_obj = Cart.objects.get(merchant_reference=merchant_reference)

                order_obj = Order.objects.create(owner=cart_obj.owner, 
                                                 shipping_address=cart_obj.shipping_address,
                                                 to_pay=cart_obj.to_pay,
                                                 order_placed_date=timezone.now(),
                                                 voucher=cart_obj.voucher,
                                                 location_group=cart_obj.location_group,
                                                 payment_status="paid",
                                                 payment_info=json.dumps(data),
                                                 payment_mode=data.get("payment_option", "NA"))

                unit_cart_objs = UnitCart.objects.filter(cart=cart_obj)
                for unit_cart_obj in unit_cart_objs:
                    unit_order_obj = UnitOrder.objects.create(order=order_obj, 
                                                              product=unit_cart_obj.product,
                                                              quantity=unit_cart_obj.quantity,
                                                              price=unit_cart_obj.product.get_actual_price())
                    UnitOrderStatus.objects.create(unit_order=unit_order_obj)

                # Cart gets empty
                for unit_cart_obj in unit_cart_objs:
                    unit_cart_obj.delete()

                # Trigger Email
                try:
                    p1 = threading.Thread(target=send_order_confirmation_mail, args=(order_obj,))
                    p1.start()
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("PaymentTransactionAPI: %s at %s", e, str(exc_tb.tb_lineno))

                # cart_obj points to None
                cart_obj.shipping_address = None
                cart_obj.voucher = None
                cart_obj.to_pay = 0
                cart_obj.merchant_reference = ""
                cart_obj.payment_info = "{}"
                cart_obj.save()

                # Refresh Stock
                refresh_stock(order_obj)
            
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

            mshastra_info = json.loads(location_group_obj.mshastra_info)

            digits = "0123456789"
            OTP = "" 
            for i in range(6):
                OTP += digits[int(math.floor(random.random()*10))]

            if DealsHubUser.objects.filter(username=contact_number+"-"+website_group_name).exists()==False:
                dealshub_user_obj = DealsHubUser.objects.create(username=contact_number+"-"+website_group_name, contact_number=contact_number, website_group=website_group_obj)
                dealshub_user_obj.set_password(OTP)
                dealshub_user_obj.verification_code = OTP
                dealshub_user_obj.save()
            else:
                dealshub_user_obj = DealsHubUser.objects.get(username=contact_number+"-"+website_group_name)
                dealshub_user_obj.set_password(OTP)
                dealshub_user_obj.verification_code = OTP
                dealshub_user_obj.save()

            message = "Login OTP is " + OTP

            # Trigger SMS
            prefix_code = mshastra_info["prefix_code"]
            sender_id = mshastra_info["sender_id"]
            user = mshastra_info["user"]
            pwd = mshastra_info["pwd"]

            contact_number = prefix_code+contact_number
            url = "http://mshastra.com/sendurlcomma.aspx?user="+user+"&pwd="+pwd+"&senderid="+sender_id+"&mobileno="+contact_number+"&msgtext="+message+"&priority=High&CountryCode=ALL"
            r = requests.get(url)

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SendOTPSMSLoginAPI: %s at %s", e, str(exc_tb.tb_lineno))

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
            
            email_id = data["emailId"]

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
            review_content = data["review_content"]

            subject = str(review_content["subject"])
            content = str(review_content["content"])

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            dealshub_product_obj = DealsHubProduct.objects.get(uuid=product_code)

            if UnitOrder.objects.filter(product=dealshub_product_obj, order__owner=dealshub_user_obj).exists():
                review_obj, created = Review.objects.get_or_create(dealshub_user=dealshub_user_obj, product=dealshub_product_obj)
                review_obj.rating = rating
                review_content_obj = review_obj.content
                if review_content_obj is None:
                    review_content_obj = ReviewContent.objects.create(subject=subject, content=content)
                else:
                    review_content_obj.subject = subject
                    review_content_obj.content = content
                    review_content_obj.save()
                review_obj.content = review_content_obj
                review_obj.save()
                response["uuid"] = review_obj.uuid
                response["review_content_uuid"] = review_content_obj.uuid
                response["status"] = 200
            else:
                response["status"] = 403

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
                temp_dict["display_name"] = str(review_obj.dealshub_user.first_name)+" "+str(review_obj.dealshub_user.last_name)
                temp_dict["rating"] = str(review_obj.rating)
                total_rating += int(review_obj.rating)

                review_content_obj = review_obj.content
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
                    review_content = {
                        "subject" : str(review_content_obj.subject),
                        "content" : str(review_content_obj.content),
                        "upvotes_count" : str(review_content_obj.upvoted_users.count()),
                        "admin_comment" : admin_comment
                    }

                temp_dict["review_content"] = review_content
                temp_dict["created_date"] = str(timezone.localtime(review_obj.created_date).strftime("%d %b, %Y"))
                temp_dict["modified_date"] = str(timezone.localtime(review_obj.modified_date).strftime("%d %b, %Y"))

                product_reviews.append(temp_dict)

            average_rating = 0
            if total_reviews != 0:
                average_rating = float(total_rating)/float(total_reviews)

            is_user_reviewed = False
            is_product_purchased = False
            if request.user!=None:

                if UnitOrder.objects.filter(product__uuid=product_code, order__owner__username=request.user.username).exists():
                    is_product_purchased = True

                if Review.objects.filter(product__uuid=product_code, dealshub_user__username=request.user.username).exists():
                    is_user_reviewed = True
                    review_obj = Review.objects.get(product__uuid=product_code, dealshub_user__username=request.user.username)
                    review_content = None
                    review_content_obj = review_obj.content
                    if review_content_obj is not None:
                        review_content = {
                            "subject" : str(review_content_obj.subject),
                            "content" : str(review_content_obj.content),
                            "upvotes_count" : str(review_content_obj.upvoted_users.count())
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


class FetchOrdersForAccountManagerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            
            data = request.data
            logger.info("FetchOrdersForAccountManagerAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            api_access = "5a72db78-b0f2-41ff-b09e-6af02c5b4c77"

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
            website_group_name = data.get("website_group_name", "").lower()

            page = data.get("page", 1)

            request_data = {
                "fromDate":from_date,
                "toDate":to_date,
                "paymentTypeList":json.dumps(payment_type_list),
                "minQty":min_qty,
                "maxQty":max_qty,
                "minPrice":min_price,
                "maxPrice":max_price,
                "currencyList":json.dumps(currency_list),
                "shippingMethodList":json.dumps(shipping_method_list),
                "trackingStatusList":json.dumps(tracking_status_list),
                "searchList":json.dumps(search_list),
                "website_group_name": website_group_name,
                "page":page, 
                "api_access":api_access
            }

            r = requests.post(url=SERVER_IP+"/api/dealshub/v1.0/fetch-orders-for-account-manager/", data=request_data, verify=False)
            response = json.loads(r.content)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOrdersForAccountManagerAPI: %s at %s", e, str(exc_tb.tb_lineno))

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

            page = data.get("page", 1)


            unit_order_objs = UnitOrder.objects.filter(order__location_group__uuid=location_group_uuid).order_by('-pk')

            if from_date!="":
                unit_order_objs = unit_order_objs.filter(order__order_placed_date__gte=from_date)

            if to_date!="":
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


            if len(search_list)>0:
                temp_unit_order_objs = UnitOrder.objects.none()
                for search_string in search_list:
                    temp_unit_order_objs |= unit_order_objs.filter(Q(order__bundleid__icontains=search_string) | Q(orderid__icontains=search_string) | Q(order__owner__first_name__icontains=search_string) | Q(order__owner__last_name__icontains=search_string) | Q(order__shipping_address__contact_number__icontains=search_string) | Q(order__merchant_reference__icontains=search_string))
                unit_order_objs = temp_unit_order_objs.distinct()


            order_objs = Order.objects.filter(location_group__uuid=location_group_uuid, unitorder__in=unit_order_objs).distinct().order_by("-order_placed_date")

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
                    temp_dict["time"] = order_obj.get_time_created()
                    temp_dict["paymentMode"] = order_obj.payment_mode
                    temp_dict["paymentStatus"] = order_obj.payment_status

                    address_obj = order_obj.shipping_address

                    shipping_address = {
                        "firstName": address_obj.first_name,
                        "lastName": address_obj.last_name,
                        "line1": json.loads(address_obj.address_lines)[0],
                        "line2": json.loads(address_obj.address_lines)[1],
                        "line3": json.loads(address_obj.address_lines)[2],
                        "line4": json.loads(address_obj.address_lines)[3],
                        "state": address_obj.state
                    }
                    customer_name = address_obj.first_name + " " + address_obj.last_name


                    temp_dict["customerName"] = customer_name
                    temp_dict["emailId"] = order_obj.owner.email
                    temp_dict["contactNumer"] = order_obj.owner.contact_number
                    temp_dict["shippingAddress"] = shipping_address

                    temp_dict["bundleId"] = order_obj.bundleid
                    temp_dict["uuid"] = order_obj.uuid
                    temp_dict["isVoucherApplied"] = is_voucher_applied
                    if is_voucher_applied:
                        temp_dict["voucherCode"] = voucher_obj.voucher_code
                    unit_order_list = []
                    subtotal = 0
                    for unit_order_obj in unit_order_objs.filter(order=order_obj):
                        temp_dict2 = {}
                        temp_dict2["orderId"] = unit_order_obj.orderid
                        temp_dict2["shippingMethod"] = unit_order_obj.shipping_method
                        temp_dict2["uuid"] = unit_order_obj.uuid
                        temp_dict2["currentStatus"] = unit_order_obj.current_status_admin
                        temp_dict2["quantity"] = unit_order_obj.quantity
                        temp_dict2["price"] = unit_order_obj.price
                        temp_total = float(unit_order_obj.price)*float(unit_order_obj.quantity)
                        temp_dict2["price_without_vat"] = round(unit_order_obj.price/1.05, 2)
                        temp_dict2["vat"] = round(temp_total - temp_total/1.05, 2)
                        temp_dict2["totalPrice"] = str(temp_total)
                        temp_dict2["currency"] = unit_order_obj.product.get_currency()
                        temp_dict2["productName"] = unit_order_obj.product.get_name()
                        temp_dict2["productImageUrl"] = unit_order_obj.product.get_main_image_url()
                        unit_order_list.append(temp_dict2)
                    temp_dict["approved"] = UnitOrder.objects.filter(order=order_obj, current_status_admin="approved").count()
                    temp_dict["picked"] = UnitOrder.objects.filter(order=order_obj, current_status_admin="picked").count()
                    temp_dict["dispatched"] = UnitOrder.objects.filter(order=order_obj, current_status_admin="dispatched").count()
                    temp_dict["delivered"] = UnitOrder.objects.filter(order=order_obj, current_status_admin="delivered").count()
                    temp_dict["deliveryFailed"] = UnitOrder.objects.filter(order=order_obj, current_status_admin="delivery failed").count()

                    subtotal = order_obj.get_subtotal()
                    subtotal_vat = round(subtotal - subtotal/1.05, 2)
                    delivery_fee = order_obj.get_delivery_fee()
                    delivery_fee_vat = round(delivery_fee - delivery_fee/1.05, 2)
                    cod_fee = order_obj.get_cod_charge()
                    cod_fee_vat = round(cod_fee - cod_fee/1.05, 2)

                    to_pay = subtotal + delivery_fee + cod_fee
                    vat = round(to_pay - to_pay/1.05, 2)
                    
                    temp_dict["subtotalWithoutVat"] = str(round(subtotal/1.05,2))
                    temp_dict["subtotalVat"] = str(subtotal_vat)
                    temp_dict["subtotal"] = str(subtotal)

                    temp_dict["deliveryFeeWithoutVat"] = str(round(delivery_fee/1.05,2))
                    temp_dict["deliveryFeeVat"] = str(delivery_fee_vat)
                    temp_dict["deliveryFee"] = str(delivery_fee)

                    temp_dict["codFeeWithoutVat"] = str(round(cod_fee/1.05, 2))
                    temp_dict["codFeeVat"] = str(cod_fee_vat)
                    temp_dict["codFee"] = str(cod_fee)

                    temp_dict["vat"] = str(vat)
                    temp_dict["toPay"] = str(to_pay)

                    temp_dict["unitOrderList"] = unit_order_list
                    order_list.append(temp_dict)

                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchOrdersForAccountManagerAPI: %s at %s", e, str(exc_tb.tb_lineno))

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
            
            shipping_methods = ["WIG Fleet", "TFM"]

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

            for unit_order_uuid in unit_order_uuid_list:
                unit_order_obj = UnitOrder.objects.get(uuid=unit_order_uuid)
                set_shipping_method(unit_order_obj, shipping_method)

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
                unit_order_objs = unit_order_objs.filter(order__order_placed_date__gte=from_date)
            if to_date!="":
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
            for order_obj in order_objs:
                try:
                    address_obj = order_obj.shipping_address

                    shipping_address = address_obj.get_shipping_address()
                    customer_name = address_obj.first_name + " " + address_obj.last_name
                    area = json.loads(address_obj.address_lines)[2]

                    subtotal = order_obj.get_subtotal()
                    delivery_fee = order_obj.get_delivery_fee()

                    for unit_order_obj in unit_order_objs.filter(order=order_obj):
                        temp_dict = {
                            "orderPlacedDate": str(timezone.localtime(order_obj.order_placed_date).strftime("%d %b, %Y %I:%M %p")),
                            "bundleId": order_obj.bundleid,
                            "orderId": unit_order_obj.orderid,
                            "productUuid": unit_order_obj.product.uuid,
                            "quantity": str(unit_order_obj.quantity),
                            "price": str(unit_order_obj.price),
                            "deliveryFee": str(delivery_fee),
                            "customerName": customer_name,
                            "customerEmail": order_obj.owner.email,
                            "customerContactNumber": str(order_obj.owner.contact_number),
                            "shippingAddress": shipping_address,
                            "paymentStatus": order_obj.payment_status,
                            "shippingMethod": unit_order_obj.shipping_method,
                            "trackingStatus": unit_order_obj.current_status_admin,
                            "area": area,
                            "total": str(round(float(unit_order_obj.price)*float(unit_order_obj.quantity), 2))
                        }
                        unit_order_list.append(temp_dict)

                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("DownloadOrdersAPI: %s at %s", e, str(exc_tb.tb_lineno))

            if report_type=="sap":
                generate_sap_order_format(unit_order_list)
                response["filepath"] = SERVER_IP+"/files/csv/sap-order-format.xlsx"
            else:
                generate_regular_order_format(unit_order_list)
                response["filepath"] = SERVER_IP+"/files/csv/regular-order-format.xlsx"
            
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
            path = "https://wig-wams-s3-bucket.s3.ap-south-1.amazonaws.com/"+path
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


FetchShippingAddressList = FetchShippingAddressListAPI.as_view()

EditShippingAddress = EditShippingAddressAPI.as_view()

CreateShippingAddress = CreateShippingAddressAPI.as_view()

DeleteShippingAddress = DeleteShippingAddressAPI.as_view()

AddToCart = AddToCartAPI.as_view()

FetchCartDetails = FetchCartDetailsAPI.as_view()

UpdateCartDetails = UpdateCartDetailsAPI.as_view()

RemoveFromCart = RemoveFromCartAPI.as_view()

SelectAddress = SelectAddressAPI.as_view()

SelectPaymentMode = SelectPaymentModeAPI.as_view()

FetchActiveOrderDetails = FetchActiveOrderDetailsAPI.as_view()

PlaceOrder = PlaceOrderAPI.as_view()

CancelOrder = CancelOrderAPI.as_view()

FetchOrderList = FetchOrderListAPI.as_view()

FetchOrderListAdmin = FetchOrderListAdminAPI.as_view()

FetchOrderDetails = FetchOrderDetailsAPI.as_view()

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

DeleteUserReview = DeleteUserReviewAPI.as_view()

FetchOrdersForAccountManager = FetchOrdersForAccountManagerAPI.as_view()

FetchOrdersForWarehouseManager = FetchOrdersForWarehouseManagerAPI.as_view()

FetchShippingMethod = FetchShippingMethodAPI.as_view()

SetShippingMethod = SetShippingMethodAPI.as_view()

SetOrdersStatus = SetOrdersStatusAPI.as_view()

CancelOrders = CancelOrdersAPI.as_view()

DownloadOrders = DownloadOrdersAPI.as_view()

UploadOrders = UploadOrdersAPI.as_view()