# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from WAMSApp.models import *
from WAMSApp.utils import *
from WAMSApp.constants import *
from dealshub.models import *
from dealshub.utils import *
from dealshub.serializers import *

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import AllowAny

from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models import Count
from django.conf import settings

import xlrd
import datetime
import uuid
import sys
import logging
import json
import hashlib
import threading
import random

import pandas as pd

logger = logging.getLogger(__name__)

class FetchOrdersForAccountManagerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchOrdersForAccountManagerAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            page = data.get("page", 1)

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
            logger.error("FetchOrdersForAccountManagerAPI: %s at %s", e, str(exc_tb.tb_lineno))

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

            unit_order_objs = UnitOrder.objects.filter(order__owner__website_group=website_group_name).order_by('-pk')

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

            response["unitOrderList"] = unit_order_list
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

            order_list = json.loads(data["orderList"])

            success = 0
            total = len(order_list)
            for order in order_list:
                try:
                    unit_order_obj = UnitOrder.objects.get(orderid=order["orderId"])
                    order_status = order["orderStatus"]
                    if order_status in ["picked", "dispatched", "delivered", "delivery failed"]:
                        set_order_status(unit_order_obj, order_status)
                    elif order_status=="approved":
                        set_shipping_method(unit_order_obj, order["shippingMethod"])
                    elif order_status=="cancelled":
                        cancel_order_admin(unit_order_obj, order["description"])
                    success += 1
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("UploadOrdersAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["totalOrders"] = str(total)
            response["successOrders"] = str(success)
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadOrdersAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


FetchOrdersForAccountManager = FetchOrdersForAccountManagerAPI.as_view()

FetchOrdersForWarehouseManager = FetchOrdersForWarehouseManagerAPI.as_view()

SetShippingMethod = SetShippingMethodAPI.as_view()

SetOrdersStatus = SetOrdersStatusAPI.as_view()

CancelOrders = CancelOrdersAPI.as_view()

DownloadOrders = DownloadOrdersAPI.as_view()

UploadOrders = UploadOrdersAPI.as_view()