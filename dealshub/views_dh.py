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
from WAMSApp.sap.utils_SAP_Integration import *
from dealshub.payments.network_global_integration import *
from dealshub.payments.hyperpay_integration import *
from dealshub.payments.spotii_integration import *
from dealshub.payments.tap_integration import *
from dealshub.payments.network_global_android_integration import *
from dealshub.payments.credimax_gateway_integration import *
from dealshub.postaplus import *
from dealshub.views_blog import *

from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models import Sum
from django.utils import timezone

#from datetime import datetime
import datetime

from WAMSApp.sap.utils_SAP_Integration import *

from facebook_business.adobjects.serverside.content import Content
from facebook_business.adobjects.serverside.custom_data import CustomData
import africastalking

import sys
import logging
import json
import requests
import hashlib
import threading
import math
import random
import os
import pandas as pd
from copy import deepcopy

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
            logger.info(request.user)
            wish_list_obj = WishList.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
            unit_wish_list_obj = None
            
            if UnitWishList.objects.filter(wish_list=wish_list_obj, product=dealshub_product_obj).exists()==False:
                unit_wish_list_obj = UnitWishList.objects.create(wish_list=wish_list_obj, product=dealshub_product_obj)
            else:
                unit_wish_list_obj = UnitWishList.objects.get(wish_list=wish_list_obj, product=dealshub_product_obj)

            response["unitWishListUuid"] = unit_wish_list_obj.uuid
            response["status"] = 200
            try:
                custom_data = []
                custom_data.append(CustomData(
                    content_type="product",
                    value= dealshub_product_obj.now_price,
                    currency=dealshub_product_obj.get_currency(),
                    content_name=dealshub_product_obj.get_name(),
                    content_category=dealshub_product_obj.get_category(),
                    contents=[Content(product_id=dealshub_product_obj.get_product_id(), quantity=dealshub_product_obj.stock, item_price=dealshub_product_obj.now_price)],
                ))
                dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
                calling_facebook_api(event_name="AddToWishlist",user=dealshub_user_obj,request=request,custom_data=custom_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("AddToWishlistAPI: %s at %s", e, str(exc_tb.tb_lineno))

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
            language_code = data.get("language","en")
            logger.info("FetchWishListAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            wish_list_obj = WishList.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
            unit_wish_list_objs = UnitWishList.objects.filter(wish_list=wish_list_obj)
            unit_wish_list = []
            custom_data = []
            for unit_wish_list_obj in unit_wish_list_objs:
                temp_dict = {}
                temp_dict["uuid"] = unit_wish_list_obj.uuid
                temp_dict["price"] = unit_wish_list_obj.product.get_actual_price_for_customer(dealshub_user_obj)
                temp_dict["currency"] = unit_wish_list_obj.product.get_currency()
                temp_dict["moq"] = unit_wish_list_obj.product.get_moq(dealshub_user_obj)
                temp_dict["dateCreated"] = unit_wish_list_obj.get_date_created()
                temp_dict["productName"] = unit_wish_list_obj.product.get_name(language_code)
                temp_dict["productImageUrl"] = unit_wish_list_obj.product.get_display_image_url()
                temp_dict["productUuid"] = unit_wish_list_obj.product.uuid
                temp_dict["link"] = unit_wish_list_obj.product.url
                temp_dict["brand"] = unit_wish_list_obj.product.get_brand(language_code)
                temp_dict["isStockAvailable"] = unit_wish_list_obj.product.stock > 0
                temp_dict["category"] = unit_wish_list_obj.product.get_category(language_code)
                unit_wish_list.append(temp_dict)
                try:
                    custom_data.append(CustomData(
                        content_type="product",
                        value=unit_wish_list_obj.product.get_actual_price_for_customer(dealshub_user_obj),
                        currency=unit_wish_list_obj.product.get_currency(),
                        content_name=unit_wish_list_obj.product.get_name(),
                        content_category=unit_wish_list_obj.product.get_category(),
                        contents=[Content(product_id=unit_wish_list_obj.product.get_product_id(), quantity=unit_wish_list_obj.product.stock, item_price=unit_wish_list_obj.product.now_price)],
                    ))
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchWishListAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["unitWishList"] = unit_wish_list
            response["status"] = 200

            try:
                dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
                calling_facebook_api(event_name="ViewContent",user=dealshub_user_obj,request=request,custom_data=custom_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("FetchWishListAPI: %s at %s", e, str(exc_tb.tb_lineno))

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
                address_list.append(get_address_dict(address_obj))

            response['addressList'] = address_list
            response['status'] = 200

            try:
                dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
                calling_facebook_api(event_name="FindLocation",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("FetchShippingAddressListAPI: %s at %s", e, str(exc_tb.tb_lineno))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchShippingAddressListAPI: %s at %s",e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchBillingAddressListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchBillingAddressListAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            user = request.user
            location_group_uuid = data["locationGroupUuid"]
            address_objs = Address.objects.filter(is_billing=True, is_deleted=False, user=user, location_group__uuid=location_group_uuid)
            
            billing_address_list = []
            for address_obj in address_objs:
                billing_address_list.append(get_address_dict(address_obj))

            dealshub_user_obj = DealsHubUser.objects.get(username=user.username)
            response['billingAddressList'] = billing_address_list
            response['primeBillingAddress'] = get_address_dict(dealshub_user_obj.prime_billing_address)
            response['status'] = 200

            try:
                dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
                calling_facebook_api(event_name="FindLocation",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("FetchBillingAddressListAPI: %s at %s", e, str(exc_tb.tb_lineno))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchBillingAddressListAPI: %s at %s",e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with activity log
class EditShippingAddressAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("EditShippingAddressAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            uuid = data["uuid"]

            address_obj = Address.objects.get(uuid=uuid)
            address_lines = json.loads(address_obj.address_lines)

            first_name = data["firstName"]
            last_name = data.get("lastName", "")
            line1 = data["line1"]
            line2 = data["line2"]
            line3 = data.get("line3", "")
            line4 = data.get("line4", "")
            
            city = data.get("city","")
            region = data.get("region","")
            geo_coordinates = data.get("geoCoordinates","")
            state = data.get("state", "")
            neighbourhood = data.get("neighbourhood", "")

            address_lines[0] = line1
            address_lines[1] = line2
            address_lines[2] = line3
            address_lines[3] = line4

            tag = data.get("tag", "Home")

            emirates = data.get("emirates", "")

            address_obj = Address.objects.get(uuid=uuid)
            prev_address_obj = deepcopy(address_obj)
            address_obj.first_name = first_name
            address_obj.last_name = last_name
            address_obj.address_lines = json.dumps(address_lines)
            address_obj.tag = tag
            address_obj.emirates = emirates
            address_obj.city = city
            address_obj.region = region
            address_obj.geo_coordinates = geo_coordinates
            if address_obj.location_group.name == "Geepas-Uganda":
                address_obj.region = emirates
                address_obj.city = line4

            address_obj.state = state
            address_obj.neighbourhood = neighbourhood
            address_obj.save()

            render_value = "Address updated offline for " + address_obj.user.username
            activitylog(request.user, Address, "updated", address_obj.uuid, prev_address_obj, address_obj, address_obj.location_group, render_value)
            response['status'] = 200

            try:
                dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
                calling_facebook_api(event_name="FindLocation",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("EditShippingAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("EditShippingAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))

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
            neighbourhood = data.get("neighbourhood", "")
            emirates = data.get("emirates", "")
            city = data.get("city","")
            region = data.get("region","")
            geo_coordinates = data.get("geoCoordinates","")
            if postcode==None:
                postcode = ""
            contact_number = dealshub_user_obj.contact_number
            tag = data.get("tag", "home")
            if tag==None:
                tag = "home"

            if dealshub_user_obj.first_name=="":
                dealshub_user_obj.first_name = first_name
                dealshub_user_obj.last_name = last_name
                dealshub_user_obj.save()

            address_obj = Address.objects.create(first_name=first_name, 
                                                last_name=last_name, 
                                                address_lines=address_lines, 
                                                state=state, postcode=postcode, 
                                                contact_number=contact_number, 
                                                user=dealshub_user_obj, 
                                                tag=tag, 
                                                location_group=location_group_obj, 
                                                neighbourhood=neighbourhood, 
                                                emirates=emirates,
                                                city=city,
                                                region=region,
                                                geo_coordinates=geo_coordinates,
                                                is_shipping=True)
            if address_obj.location_group.name == "Geepas-Uganda":
                address_obj.region = emirates
                address_obj.city = line4
                address_obj.save()
            response["uuid"] = address_obj.uuid
            response['status'] = 200

            try:
                calling_facebook_api(event_name="FindLocation",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("CreateShippingAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateShippingAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CreateBillingAddressAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("CreateBillingAddressAPI: %s", str(data))
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
            neighbourhood = data.get("neighbourhood", "")
            emirates = data.get("emirates", "")
            geo_coordinates = data.get("geoCoordinates", "")
            if postcode==None:
                postcode = ""
            contact_number = dealshub_user_obj.contact_number
            tag = data.get("tag", "home")
            if tag==None:
                tag = "home"

            if dealshub_user_obj.first_name=="":
                dealshub_user_obj.first_name = first_name
                dealshub_user_obj.last_name = last_name
                dealshub_user_obj.save()

            address_obj = Address.objects.create(first_name=first_name, 
                                                last_name=last_name, 
                                                address_lines=address_lines, 
                                                state=state, postcode=postcode, 
                                                contact_number=contact_number, 
                                                user=dealshub_user_obj, 
                                                tag=tag, 
                                                location_group=location_group_obj, 
                                                neighbourhood=neighbourhood, 
                                                emirates=emirates,
                                                geo_coordinates=geo_coordinates,
                                                is_billing=True)

            response["uuid"] = address_obj.uuid
            response['status'] = 200

            try:
                calling_facebook_api(event_name="FindLocation",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("CreateBillingAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateBillingAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

#API with active log
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
                if address_obj.location_group.name == "Geepas-Uganda":
                    address_obj.region = emirates
                    address_obj.city = line4
                    address_obj.save()
                response["uuid"] = address_obj.uuid

                render_value = "New Offline Shipping Address created for " + username
                activitylog(request.user, Address, "created", address_obj.uuid, None, address_obj, location_group_obj, render_value)
                response['status'] = 200
            else:
                response["status"] = 409

            try:
                calling_facebook_api(event_name="FindLocation",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("CreateOfflineShippingAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateOfflineShippingAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class CreateOfflineBillingAddressAPI(APIView):
    
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("CreateOfflineBillingAddressAPI: %s", str(data))
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

                billing_address_obj = Address.objects.create(user=dealshub_user_obj,
                                                    first_name=first_name,
                                                    last_name=last_name, 
                                                    address_lines=address_lines, 
                                                    state=state, 
                                                    postcode=postcode, 
                                                    contact_number=contact_number, 
                                                    tag=tag, 
                                                    location_group=location_group_obj, 
                                                    emirates=emirates, 
                                                    is_billing=True)

                response["uuid"] = billing_address_obj.uuid

                render_value = "New Offline Billing Address created for " + username
                activitylog(request.user, Address, "created", billing_address_obj.uuid, None, billing_address_obj, location_group_obj, render_value)
                response['status'] = 200
            else:
                response["status"] = 409
            
            try:
                calling_facebook_api(event_name="FindLocation",user=dealshub_user_obj,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("CreateOfflineBillingAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateOfflineBillingAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class DeleteShippingAddressAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteShippingAddressAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            uuid = data["uuid"]

            address_obj = Address.objects.get(uuid=uuid)
            dealshub_user_obj = address_obj.user
            cart_obj = Cart.objects.get(owner=dealshub_user_obj)

            if cart_obj.shipping_address != None and cart_obj.shipping_address.pk == address_obj.pk:
                cart_obj.shipping_address = None
                cart_obj.save()

            if cart_obj.billing_address != None and cart_obj.billing_address.pk == address_obj.pk:
                cart_obj.billing_address = None
                cart_obj.save()

            address_obj.is_deleted = True
            address_obj.save()

            response['status'] = 200

            try:
                calling_facebook_api(event_name="FindLocation",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("DeleteShippingAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))

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
                unit_cart_obj = UnitCart.objects.create(cart=cart_obj, product=dealshub_product_obj, quantity=quantity, offline_price=dealshub_product_obj.get_actual_price_for_customer(dealshub_user_obj))

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

            try:
                custom_data = []
                custom_data.append(CustomData(
                    content_type="product",
                    value=dealshub_product_obj.now_price,
                    currency=dealshub_product_obj.get_currency(),
                    content_name=dealshub_product_obj.get_name(),
                    content_category=dealshub_product_obj.get_category(),
                    contents=[Content(product_id=dealshub_product_obj.get_product_id(), quantity=dealshub_product_obj.stock, item_price=dealshub_product_obj.now_price)],
                ))
                calling_facebook_api(event_name="AddToCart",user=dealshub_user_obj,request=request,custom_data=custom_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("AddToCartAPI: %s at %s", e, str(exc_tb.tb_lineno))

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
            quantity = data.get("quantity", 1)

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

            try:
                custom_data = []
                custom_data.append(CustomData(
                    content_type="product",
                    value=dealshub_product_obj.now_price,
                    currency=dealshub_product_obj.get_currency(),
                    content_name=dealshub_product_obj.get_name(),
                    content_category=dealshub_product_obj.get_category(),
                    contents=[Content(product_id=dealshub_product_obj.get_product_id(), quantity=dealshub_product_obj.stock, item_price=dealshub_product_obj.now_price)],
                ))
                calling_facebook_api(event_name="AddToCart",user=dealshub_user_obj,request=request,custom_data=custom_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("AddToFastCartAPI: %s at %s", e, str(exc_tb.tb_lineno))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddToFastCartAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
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
            prev_cart_obj = deepcopy(cart_obj)
            unit_cart_obj = None
            if UnitCart.objects.filter(cart=cart_obj, product__uuid=product_uuid).exists()==True:
                unit_cart_obj = UnitCart.objects.get(cart=cart_obj, product__uuid=product_uuid)
                unit_cart_obj.quantity += quantity
                unit_cart_obj.save()
            else:
                unit_cart_obj = UnitCart.objects.create(cart=cart_obj, 
                                                        product=dealshub_product_obj, 
                                                        quantity=quantity,
                                                        offline_price=dealshub_product_obj.get_actual_price_for_customer(dealshub_user_obj))

            update_cart_bill(cart_obj,cod=True,offline=True)

            subtotal = cart_obj.get_subtotal(offline=True)
            delivery_fee = cart_obj.get_delivery_fee(offline=True)
            total_amount = cart_obj.get_total_amount(offline=True)
            vat = cart_obj.get_vat(offline=True)

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
                "codCharge": cart_obj.offline_cod_charge,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }

            response["unitCartUuid"] = unit_cart_obj.uuid
            render_value = "Product " + dealshub_product_obj.product_name + " added to offline cart for " + username
            activitylog(request.user, Cart, "updated", cart_obj.uuid, prev_cart_obj, cart_obj, location_group_obj, render_value)
            response["status"] = 200


            try:
                custom_data = []
                custom_data.append(CustomData(
                    content_type="product",
                    value=dealshub_product_obj.now_price,
                    currency=dealshub_product_obj.get_currency(),
                    content_name=dealshub_product_obj.get_name(),
                    content_category=dealshub_product_obj.get_category(),
                    contents=[Content(product_id=dealshub_product_obj.get_product_id(), quantity=dealshub_product_obj.stock, item_price=dealshub_product_obj.now_price)],
                ))
                calling_facebook_api(event_name="AddToCart",user=dealshub_user_obj,request=request,custom_data=custom_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("AddToOfflineCartAPI: %s at %s", e, str(exc_tb.tb_lineno))

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
            language_code = data.get("language","en")
            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
            unit_cart_objs = UnitCart.objects.filter(cart=cart_obj)
            unit_cart_list = []
            custom_data = []
            for unit_cart_obj in unit_cart_objs:
                try:
                    temp_dict = {}
                    temp_dict["uuid"] = unit_cart_obj.uuid
                    temp_dict["quantity"] = unit_cart_obj.quantity
                    temp_dict["price"] = unit_cart_obj.product.get_actual_price_for_customer(dealshub_user_obj)
                    temp_dict["showNote"] = unit_cart_obj.product.is_promo_restriction_note_required(dealshub_user_obj)
                    temp_dict["moq"] = unit_cart_obj.product.get_moq(dealshub_user_obj)
                    temp_dict["stock"] = unit_cart_obj.product.stock
                    temp_dict["super_category"] = unit_cart_obj.product.get_super_category()        
                    temp_dict["category"] = unit_cart_obj.product.get_category()
                    temp_dict["sub_category"] = unit_cart_obj.product.get_sub_category()
                    temp_dict["allowedQty"] = unit_cart_obj.product.get_allowed_qty()
                    temp_dict["currency"] = unit_cart_obj.product.get_currency()
                    temp_dict["dateCreated"] = unit_cart_obj.get_date_created()
                    temp_dict["productName"] = unit_cart_obj.product.get_name(language_code)
                    temp_dict["productImageUrl"] = unit_cart_obj.product.get_display_image_url()
                    temp_dict["productUuid"] = unit_cart_obj.product.uuid
                    temp_dict["link"] = unit_cart_obj.product.url
                    temp_dict["brand"] = unit_cart_obj.product.get_brand(language_code)
                    temp_dict["isStockAvailable"] = unit_cart_obj.product.stock > 0
                    unit_cart_list.append(temp_dict)
                    try:
                        custom_data.append(CustomData(
                            content_type="product",
                            value=unit_cart_obj.product.get_actual_price_for_customer(dealshub_user_obj),
                            currency=unit_cart_obj.product.get_currency(),
                            content_name=unit_cart_obj.product.get_name(),
                            content_category=unit_cart_obj.product.get_category(),
                            contents=[Content(product_id=unit_cart_obj.product.get_product_id(), quantity=unit_cart_obj.quantity, item_price=unit_cart_obj.product.get_actual_price_for_customer(dealshub_user_obj))],
                        ))
                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        logger.error("FetchCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

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

            response["additional_note"] = cart_obj.additional_note
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

            try:
                dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
                calling_facebook_api(event_name="ViewContent",user=dealshub_user_obj,request=request,custom_data=custom_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("FetchCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

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
            language_code = data.get("language","en")
            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            username = data["username"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            dealshub_user_obj = DealsHubUser.objects.get(username=username)
            cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
            unit_cart_objs = UnitCart.objects.filter(cart=cart_obj)
            unit_cart_list = []
            custom_data = []
            for unit_cart_obj in unit_cart_objs:
                temp_dict = {}
                temp_dict["uuid"] = unit_cart_obj.uuid
                temp_dict["quantity"] = unit_cart_obj.quantity
                temp_dict["price"] = unit_cart_obj.offline_price
                temp_dict["sellerSku"] = unit_cart_obj.product.get_seller_sku()
                temp_dict["showNote"] = unit_cart_obj.product.is_promo_restriction_note_required(dealshub_user_obj)
                temp_dict["currency"] = unit_cart_obj.product.get_currency()
                temp_dict["dateCreated"] = unit_cart_obj.get_date_created()
                temp_dict["productName"] = unit_cart_obj.product.get_name(language_code)
                temp_dict["productImageUrl"] = unit_cart_obj.product.get_display_image_url()
                temp_dict["productUuid"] = unit_cart_obj.product.uuid
                temp_dict["link"] = unit_cart_obj.product.url
                temp_dict["brand"] = unit_cart_obj.product.get_brand(language_code)
                temp_dict["isStockAvailable"] = unit_cart_obj.product.stock > 0
                unit_cart_list.append(temp_dict)
                try:
                    custom_data.append(CustomData(
                        content_type="product",
                        value=unit_cart_obj.product.now_price,
                        currency=unit_cart_obj.product.get_currency(),
                        content_name=unit_cart_obj.product.get_name(),
                        content_category=unit_cart_obj.product.get_category(),
                        contents=[Content(product_id=unit_cart_obj.product.get_product_id(), quantity=unit_cart_obj.quantity, item_price=unit_cart_obj.product.now_price)],
                    ))
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchOfflineCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

            update_cart_bill(cart_obj,cod=True,offline=True)

            subtotal = cart_obj.get_subtotal(offline=True)

            delivery_fee = cart_obj.get_delivery_fee(offline=True)
            total_amount = cart_obj.get_total_amount(offline=True)
            vat = cart_obj.get_vat(offline=True)

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
                    
            response["cartUuid"] = cart_obj.uuid
            response["additional_note"] = cart_obj.additional_note
            response["referenceMedium"] = cart_obj.reference_medium
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
                "codCharge": cart_obj.offline_cod_charge,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }

            response["unitCartList"] = unit_cart_list
            response["status"] = 200

            try:
                calling_facebook_api(event_name="ViewContent",user=cart_obj.owner,request=request,custom_data=custom_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("FetchOfflineCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

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
            if is_order_offline:
                offline_price = data["offline_price"]

            unit_cart_obj = UnitCart.objects.get(uuid=unit_cart_uuid)
            unit_cart_obj.quantity = quantity
            if is_order_offline:
                unit_cart_obj.offline_price = offline_price
            unit_cart_obj.save()
            custom_data = []
            try:
                custom_data.append(CustomData(
                    content_type="product",
                    value=unit_cart_obj.product.now_price,
                    currency=unit_cart_obj.product.get_currency(),
                    content_name=unit_cart_obj.product.get_name(),
                    content_category=unit_cart_obj.product.get_category(),
                    contents=[Content(product_id=unit_cart_obj.product.get_product_id(), quantity=unit_cart_obj.quantity, item_price=unit_cart_obj.product.now_price)],
                ))
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("UpdateCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
            cod=False
            if is_order_offline==True:
                cod=True

            update_cart_bill(unit_cart_obj.cart,cod=cod,offline=is_order_offline)

            cart_obj = unit_cart_obj.cart

            subtotal = cart_obj.get_subtotal(offline=is_order_offline)
            
            delivery_fee = cart_obj.get_delivery_fee(offline=is_order_offline)
            total_amount = cart_obj.get_total_amount(offline=is_order_offline)
            vat = cart_obj.get_vat(offline=is_order_offline)

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
                "codCharge": cart_obj.offline_cod_charge if is_order_offline==True else cart_obj.location_group.cod_charge,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }

            response["status"] = 200

            try:
                calling_facebook_api(event_name="AddToCart",user=cart_obj.owner,request=request,custom_data=custom_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("UpdateCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class UpdateOfflineCartDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):
    
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateOfflineCartDetailsAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            cart_uuid = data["cartUuid"]

            offline_cod_charge = data["offline_cod_charge"]
            offline_delivery_fee = data["offline_delivery_fee"]
            is_order_offline = True

            cart_obj = Cart.objects.get(uuid=cart_uuid)
            prev_cart_obj = deepcopy(cart_obj)

            cart_obj.offline_cod_charge = offline_cod_charge
            cart_obj.offline_delivery_fee = offline_delivery_fee
            cart_obj.save()

            update_cart_bill(cart_obj,cod=True,offline=is_order_offline, delivery_fee_calculate=False)

            subtotal = cart_obj.get_subtotal(offline=is_order_offline)
            
            delivery_fee = cart_obj.get_delivery_fee(offline=is_order_offline, calculate=False)
            total_amount = cart_obj.get_total_amount(offline=is_order_offline, delivery_fee_calculate=False)
            vat = cart_obj.get_vat(offline=is_order_offline, delivery_fee_calculate=False)

            delivery_fee_with_cod = cart_obj.get_delivery_fee(cod=True, offline=is_order_offline, calculate=False)
            total_amount_with_cod = cart_obj.get_total_amount(cod=True, offline=is_order_offline, delivery_fee_calculate=False)
            vat_with_cod = cart_obj.get_vat(cod=True, offline=is_order_offline, delivery_fee_calculate=False)

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
                "codCharge": cart_obj.get_cod_charge(offline=is_order_offline),
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }

            render_value = "Offline Cart updated for " + cart_obj.owner.username
            activitylog(request.user, Cart, "updated", cart_obj.uuid, prev_cart_obj, cart_obj, cart_obj.location_group, render_value)
            response["status"] = 200

            custom_data = []
            unit_cart_objs = UnitCart.objects.filter(cart=cart_obj)
            try:
                for unit_cart_obj in unit_cart_objs:
                    custom_data.append(CustomData(
                        content_type="product",
                        value=unit_cart_obj.product.now_price,
                        currency=unit_cart_obj.product.get_currency(),
                        content_name=unit_cart_obj.product.get_name(),
                        content_category=unit_cart_obj.product.get_category(),
                        contents=[Content(product_id=unit_cart_obj.product.get_product_id(), quantity=unit_cart_obj.quantity, item_price=unit_cart_obj.product.now_price)],
                    ))
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("UpdateOfflineCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
            try:
                calling_facebook_api(event_name="AddToCart",user=cart_obj.owner,request=request,custom_data=custom_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("UpdateOfflineCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
                
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateOfflineCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
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

            try:
                calling_facebook_api(event_name="CompleteRegistration",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("BulkUpdateCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
                
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

            try:
                custom_data = []
                custom_data.append(CustomData(
                    content_type="product",
                    value=fast_cart_obj.product.now_price,
                    currency=fast_cart_obj.product.get_currency(),
                    content_name=fast_cart_obj.product.get_name(),
                    content_category=fast_cart_obj.product.get_category(),
                    contents=[Content(product_id=fast_cart_obj.product.get_product_id(), quantity=fast_cart_obj.quantity, item_price=fast_cart_obj.product.now_price)],
                ))
                calling_facebook_api(event_name="AddToCart",user=fast_cart_obj.owner,request=request,custom_data=custom_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("UpdateFastCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
                
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
            is_order_offline = data.get("is_order_offline",False)

            unit_cart_obj = UnitCart.objects.get(uuid=unit_cart_uuid)
            cart_obj = unit_cart_obj.cart
            try:
                custom_data = []
                custom_data.append(CustomData(
                    content_type="product",
                    value=unit_cart_obj.product.now_price,
                    currency=unit_cart_obj.product.get_currency(),
                    content_name=unit_cart_obj.product.get_name(),
                    content_category=unit_cart_obj.product.get_category(),
                    contents=[Content(product_id=unit_cart_obj.product.get_product_id(), quantity=unit_cart_obj.quantity, item_price=unit_cart_obj.product.now_price)],
                ))
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("RemoveFromCartAPI: %s at %s", e, str(exc_tb.tb_lineno))
            unit_cart_obj.delete()

            cod = False
            if is_order_offline==True:
                cod = True

            update_cart_bill(cart_obj,cod=cod,offline=is_order_offline)

            subtotal = cart_obj.get_subtotal(offline=is_order_offline)
            
            delivery_fee = cart_obj.get_delivery_fee(offline=is_order_offline)
            total_amount = cart_obj.get_total_amount(offline=is_order_offline)
            vat = cart_obj.get_vat(offline=is_order_offline)

            delivery_fee_with_cod = cart_obj.get_delivery_fee(cod=True,offline=is_order_offline)
            total_amount_with_cod = cart_obj.get_total_amount(cod=True,offline=is_order_offline)
            vat_with_cod = cart_obj.get_vat(cod=True,offline=is_order_offline)

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
                "codCharge": cart_obj.offline_cod_charge if is_order_offline==True else cart_obj.location_group.cod_charge,
                "is_voucher_applied": is_voucher_applied,
                "voucher_discount": voucher_discount,
                "voucher_code": voucher_code
            }

            response["status"] = 200

            try:
                calling_facebook_api(event_name="AddToCart",user=cart_obj.owner,request=request,custom_data=custom_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("RemoveFromCartAPI: %s at %s", e, str(exc_tb.tb_lineno))
                
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

            try:
                dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
                calling_facebook_api(event_name="ViewContent",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SelectAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))
                            
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SelectAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class SelectBillingAddressAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SelectBillingAddressAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            billing_address_uuid = data["billingAddressUuid"]
            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            billing_address_obj = Address.objects.get(uuid=billing_address_uuid)

            if data.get("is_fast_cart", False)==True:
                fast_cart_obj = FastCart.objects.get(owner=dealshub_user_obj, location_group=billing_address_obj.location_group)
                fast_cart_obj.billing_address = billing_address_obj
                fast_cart_obj.save()
            else:
                cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=billing_address_obj.location_group)
                cart_obj.billing_address = billing_address_obj
                cart_obj.save()

            response["status"] = 200

            try:
                dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
                calling_facebook_api(event_name="ViewContent",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SelectBillingAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))
                            
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SelectBillingAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

#API with active log
class SelectOfflineAddressAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SelectOfflineAddressAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            is_b2b = data.get("is_b2b", False)
            shipping_address_uuid = data["shippingAddressUuid"]
            shipping_address_obj = Address.objects.get(uuid=shipping_address_uuid)
            shipping_address_obj.is_shipping = True
            shipping_address_obj.save()
            username = data["username"]
            dealshub_user_obj = DealsHubUser.objects.get(username=username)
            cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=shipping_address_obj.location_group)
            cart_obj.shipping_address = shipping_address_obj

            if is_b2b:
                billing_address_uuid = data["billingAddressUuid"]
                billing_address_obj = Address.objects.get(uuid=billing_address_uuid)
                billing_address_obj.is_billing = True
                billing_address_obj.save()
                cart_obj.billing_address = billing_address_obj
                dealshub_user_obj.prime_billing_address = billing_address_obj
                dealshub_user_obj.save()
            cart_obj.save()
            
            response["status"] = 200

            try:
                dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
                calling_facebook_api(event_name="ViewContent",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SelectOfflineAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
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

            unit_cart_objs = UnitCart.objects.filter(cart=cart_obj)

            try:
                custom_data = []
                for unit_cart_obj in unit_cart_objs:
                    custom_data.append(CustomData(
                        content_type="product",
                        value=unit_cart_obj.product.now_price,
                        currency=unit_cart_obj.product.get_currency(),
                        content_name=unit_cart_obj.product.get_name(),
                        content_category=unit_cart_obj.product.get_category(),
                        contents=[Content(product_id=unit_cart_obj.product.get_product_id(), quantity=unit_cart_obj.quantity, item_price=unit_cart_obj.product.now_price)],
                    ))
                calling_facebook_api(event_name="InitiateCheckout",user=dealshub_user_obj,request=request,custom_data=custom_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SelectPaymentModeAPI: %s at %s", e, str(exc_tb.tb_lineno))

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
            language_code = data.get("language","en")
            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)

            update_cart_bill(cart_obj)
            
            if cart_obj.shipping_address==None and Address.objects.filter(is_deleted=False, user=request.user, location_group=location_group_obj, is_shipping=True).count()>0:
                cart_obj.shipping_address = Address.objects.filter(is_deleted=False, user=request.user, location_group=location_group_obj, is_shipping=True)[0]
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
                temp_dict["productName"] = unit_cart_obj.product.get_name(language_code)
                temp_dict["productImageUrl"] = unit_cart_obj.product.get_display_image_url()
                temp_dict["productUuid"] = unit_cart_obj.product.uuid
                temp_dict["link"] = unit_cart_obj.product.url
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

            unit_cart_objs = UnitCart.objects.filter(cart=cart_obj)
            custom_data = []

            try:
                for unit_cart_obj in unit_cart_objs:
                    custom_data.append(CustomData(
                        content_type="product",
                        value=unit_cart_obj.product.now_price,
                        currency=unit_cart_obj.product.get_currency(),
                        content_name=unit_cart_obj.product.get_name(),
                        content_category=unit_cart_obj.product.get_category(),
                        contents=[Content(product_id=unit_cart_obj.product.get_product_id(), quantity=unit_cart_obj.quantity, item_price=unit_cart_obj.product.now_price)],
                    ))
                calling_facebook_api(event_name="InitiateCheckout",user=dealshub_user_obj,request=request,custom_data=custom_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("FetchActiveOrderDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
                
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchActiveOrderDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class PlaceOrderRequestAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("PlaceOrderRequestAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            payment_mode = data["paymentMode"]

            is_fast_cart = data.get("is_fast_cart", False)

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            order_request_obj = None
            if is_fast_cart==False:
                cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)

                try:
                    if cart_obj.shipping_address==None:
                        address_obj = Address.objects.filter(user=dealshub_user_obj, is_shipping=True)[0]
                        cart_obj.shipping_address = address_obj
                    if cart_obj.billing_address==None:
                        billing_address_obj = Address.objects.filter(user=dealshub_user_obj, is_billing=True)[0]
                        cart_obj.billing_address = billing_address_obj
                    cart_obj.save()
                except Exception as e:
                    pass

                if location_group_obj.is_voucher_allowed_on_cod==False:
                    cart_obj.voucher = None
                    cart_obj.save()

                update_cart_bill(cart_obj)

                unit_cart_objs = UnitCart.objects.filter(cart=cart_obj)
                
                if unit_cart_objs.count() == 0:
                    response["status"] = 500
                    response["message"] = "empty cart"
                    return Response(data=response)
                
                if payment_mode=="COD":
                    cart_obj.to_pay += cart_obj.location_group.cod_charge
                    cart_obj.save()
                cod_charge = cart_obj.location_group.cod_charge
                if payment_mode=="CHEQUE":
                    cod_charge = 0
                order_request_obj = OrderRequest.objects.create(owner=cart_obj.owner,
                                                 shipping_address=cart_obj.shipping_address,
                                                 billing_address=cart_obj.billing_address,
                                                 to_pay=cart_obj.to_pay,
                                                 real_to_pay=cart_obj.to_pay,
                                                 voucher=cart_obj.voucher,
                                                 location_group=cart_obj.location_group,
                                                 delivery_fee=cart_obj.get_delivery_fee(),
                                                 payment_mode = payment_mode,
                                                 cod_charge=cod_charge,
                                                 additional_note=cart_obj.additional_note)

                for unit_cart_obj in unit_cart_objs:
                    unit_order_request_obj = UnitOrderRequest.objects.create(order_request=order_request_obj,
                                                              product=unit_cart_obj.product,
                                                              initial_quantity=unit_cart_obj.quantity,
                                                              initial_price=unit_cart_obj.product.get_actual_price_for_customer(dealshub_user_obj))

                # Cart gets empty
                for unit_cart_obj in unit_cart_objs:
                    unit_cart_obj.delete()

                # cart_obj points to None
                cart_obj.billing_address = None
                cart_obj.shipping_address = None
                cart_obj.voucher = None
                cart_obj.to_pay = 0
                cart_obj.additional_note = ""
                cart_obj.merchant_reference = ""
                cart_obj.payment_info = "{}"
                cart_obj.save()
            else:
                fast_cart_obj = FastCart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
                
                if fast_cart_obj.product == None:
                    response["status"] = 500
                    response["message"] = "empty fast cart"
                    return Response(data=response)
                
                try:
                    if fast_cart_obj.shipping_address==None:
                        address_obj = Address.objects.filter(user=dealshub_user_obj, is_shipping=True)[0]
                        fast_cart_obj.shipping_address = address_obj
                    if fast_cart_obj.billing_address==None:
                        billing_address_obj = Address.objects.filter(user=dealshub_user_obj, is_billing=True)[0]
                        fast_cart_obj.billing_address = billing_address_obj
                    fast_cart_obj.save()
                except Exception as e:
                    pass

                if location_group_obj.is_voucher_allowed_on_cod==False:
                    fast_cart_obj.voucher = None
                    fast_cart_obj.save()

                update_fast_cart_bill(fast_cart_obj)

                fast_cart_obj.to_pay += fast_cart_obj.location_group.cod_charge
                fast_cart_obj.save()

                order_request_obj = OrderRequest.objects.create(owner=fast_cart_obj.owner,
                                                 shipping_address=fast_cart_obj.shipping_address,
                                                 billing_address=fast_cart_obj.billing_address,
                                                 to_pay=fast_cart_obj.to_pay,
                                                 real_to_pay=fast_cart_obj.to_pay,
                                                 voucher=fast_cart_obj.voucher,
                                                 location_group=fast_cart_obj.location_group,
                                                 delivery_fee=fast_cart_obj.get_delivery_fee(),
                                                 cod_charge=fast_cart_obj.location_group.cod_charge,
                                                 additional_note=fast_cart_obj.additional_note)

                unit_order_request_obj = UnitOrderRequest.objects.create(order_request=order_request_obj,
                                                          product=fast_cart_obj.product,
                                                          initial_quantity=fast_cart_obj.quantity,
                                                          initial_price=fast_cart_obj.product.get_actual_price_for_customer(dealshub_user_obj))

                # fast_cart_obj points to None
                fast_cart_obj.billing_address = None
                fast_cart_obj.shipping_address = None
                fast_cart_obj.voucher = None
                fast_cart_obj.to_pay = 0
                fast_cart_obj.additional_note = ""
                fast_cart_obj.merchant_reference = ""
                fast_cart_obj.payment_info = "{}"
                fast_cart_obj.product = None
                fast_cart_obj.save()


            # Trigger Email
            try:
                p1 = threading.Thread(target=send_order_request_placed_mail, args=(order_request_obj,))
                p1.start()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("PlaceOrderRequestAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["status"] = 200

            try:
                calling_facebook_api(event_name="CompleteRegistration",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("PlaceOrderRequestAPI: %s at %s", e, str(exc_tb.tb_lineno))
                
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PlaceOrderRequestAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class ProcessOrderRequestAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("ProcessOrderRequestAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            unit_order_requests = data["UnitOrderRequests"]
            request_status = data["requestStatus"]
            admin_note = data.get("adminNote","")

            order_request_obj = OrderRequest.objects.get(uuid = data["OrderRequestUuid"])

            unit_order_request_objs = UnitOrderRequest.objects.filter(order_request = order_request_obj)
            unit_order_request_objs.update(request_status="Rejected")

            for unit_order_request in unit_order_requests:
                unit_order_request_obj = UnitOrderRequest.objects.get(order_request=order_request_obj, uuid = unit_order_request["uuid"])
                unit_order_request_obj.final_quantity = int(unit_order_request["quantity"])
                unit_order_request_obj.final_price = float(unit_order_request["price"])
                unit_order_request_obj.request_status = unit_order_request["status"]
                unit_order_request_obj.save()

            order_request_obj.request_status = request_status
            order_request_obj.admin_note = admin_note
            order_request_obj.save()

            if request_status == "Rejected":
                response['message'] = "Order Request Rejected"
                response["status"] = 200
                return Response(data=response)
                                

            if order_request_obj.payment_mode == "COD" or order_request_obj.payment_mode == "CHEQUE":
                try:
                    if order_request_obj.shipping_address==None:
                        address_obj = Address.objects.filter(user=dealshub_user_obj)[0]
                        order_request_obj.shipping_address = address_obj
                        order_request_obj.save()
                except Exception as e:
                    pass

                if location_group_obj.is_voucher_allowed_on_cod==False:
                    order_request_obj.voucher = None
                    order_request_obj.save()

                update_order_request_bill(order_request_obj,cod=True if order_request_obj.payment_mode == "COD" else False)
                cod_charge = order_request_obj.location_group.cod_charge
                if order_request_obj.payment_mode == "CHEQUE":
                    cod_charge = 0

                order_obj = Order.objects.create(owner = order_request_obj.owner,
                                                 shipping_address=order_request_obj.shipping_address,
                                                 billing_address=order_request_obj.billing_address,
                                                 to_pay=order_request_obj.to_pay,
                                                 real_to_pay=order_request_obj.to_pay,
                                                 payment_mode = order_request_obj.payment_mode,
                                                 payment_status = "cod" if order_request_obj.payment_mode == "COD" else "paid",
                                                 order_placed_date=timezone.now(),
                                                 voucher=order_request_obj.voucher,
                                                 location_group=order_request_obj.location_group,
                                                 delivery_fee=order_request_obj.get_delivery_fee(),
                                                 cod_charge=cod_charge,
                                                 additional_note=order_request_obj.additional_note,
                                                 admin_note = order_request_obj.admin_note)

                for unit_order_request_obj in unit_order_request_objs:
                    unit_order_obj = UnitOrder.objects.create(order=order_obj,
                                                              product=unit_order_request_obj.product,
                                                              quantity=unit_order_request_obj.final_quantity,
                                                              price=unit_order_request_obj.final_price)
                    UnitOrderStatus.objects.create(unit_order=unit_order_obj)

                order_request_obj.is_placed = True
                order_request_obj.save()

                # Trigger Email
                try:
                    p1 = threading.Thread(target=send_order_confirmation_mail, args=(order_obj,))
                    p1.start()
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("ProcessOrderRequestAPI: %s at %s", e, str(exc_tb.tb_lineno))

                # Refresh Stock
                refresh_stock(order_obj)
                response['message'] = "Order Placed"

            else:
                update_order_request_bill(order_request_obj)

                # Trigger Email
                try:
                    p1 = threading.Thread(target=send_order_request_approval_mail, args=(order_request_obj,))
                    p1.start()
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("ProcessOrderRequestAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ProcessOrderRequestAPI: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)


class DeleteOrderRequestAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("DeleteOrderRequestAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)
            location_group_uuid = data["locationGroupUuid"]
            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            order_request_obj = OrderRequest.objects.get(location_group__uuid=location_group_uuid, uuid = data["OrderRequestUuid"])

            if order_request_obj.owner == dealshub_user_obj:
                order_request_obj_copy = deepcopy(order_request_obj)
                # Trigger Email
                try:
                    p1 = threading.Thread(target=send_order_request_deleted_mail, args=(order_request_obj_copy,))
                    p1.start()
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("DeleteOrderRequestAPI: %s at %s", e, str(exc_tb.tb_lineno))
                order_request_obj.delete()
            response["status"] = 200

            try:
                calling_facebook_api(event_name="CompleteRegistration",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("DeleteOrderRequestAPI: %s at %s", e, str(exc_tb.tb_lineno))
                
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteOrderRequestAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class PlaceInquiryAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("PlaceInquiryAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            message = data["message"]
            product_uuid = data["productUuid"]
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=product_uuid)

            if dealshub_product_obj.location_group!=location_group_obj:
                response["status"] = 403
                logger.error("PlaceInquiryAPI: Product does not exist in LocationGroup!")
                return Response(data=response)

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            to_email = location_group_obj.get_support_email_id()
            password = location_group_obj.get_support_email_password()

            try:
                p1 = threading.Thread(target=send_inquiry_now_mail, args=(message, to_email, password, dealshub_user_obj, dealshub_product_obj))
                p1.start()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("PlaceInquiryAPI: %s at %s", e, str(exc_tb.tb_lineno))
            response["status"] = 200

            try:
                custom_data = []
                custom_data.append(CustomData(
                    content_type="product",
                    value=dealshub_product_obj.now_price,
                    currency=dealshub_product_obj.get_currency(),
                    content_name=dealshub_product_obj.get_name(),
                    content_category=dealshub_product_obj.get_category(),
                    contents=[Content(product_id=dealshub_product_obj.get_product_id(), quantity=dealshub_product_obj.stock, item_price=dealshub_product_obj.now_price)],
                ))
                calling_facebook_api(event_name="Contact",user=dealshub_user_obj,request=request,custom_data=custom_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("PlaceInquiryAPI: %s at %s", e, str(exc_tb.tb_lineno))
                
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PlaceInquiryAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class PlaceB2BOnlineOrderAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("PlaceB2BOnlineOrderAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            merchant_reference = data["merchant_reference"]
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            b2b_user_obj = B2BUser.objects.get(username = request.user.username)

            order_request_obj = OrderRequest.objects.get(uuid = data["OrderRequestUuid"])

            if Order.objects.filter(merchant_reference=merchant_reference).exists():
                logger.warning("PlaceB2BOnlineOrderAPI: Credentials for older order!")
                return Response(data=response)

            if order_request_obj.request_status != "Approved":
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("PlaceB2BOnlineOrderAPI: Order Request Not Approved %s at %s", e, str(exc_tb.tb_lineno))
                response["message"] = "Order request not approved"
                return Response(data=response)

            online_payment_mode = data.get("online_payment_mode","card")

            if online_payment_mode.strip().lower()=="network_global_android":
                if check_order_status_from_network_global_android(merchant_reference, location_group_obj)==False:
                    logger.warning("PlaceB2BOnlineOrderAPI: NETWORK GLOBAL ANDROID STATUS MISMATCH!")
                    return Response(data=response)  
            else:
                if check_order_status_from_network_global(merchant_reference, location_group_obj)==False:
                    logger.warning("PlaceB2BOnlineOrderAPI: NETWORK GLOBAL STATUS MISMATCH!")
                    return Response(data=response)

            try:
                voucher_obj = order_request_obj.voucher
                if voucher_obj!=None:
                    if voucher_obj.is_expired()==False and is_voucher_limt_exceeded_for_customer(order_request_obj.owner, voucher_obj)==False:
                        voucher_obj.total_usage += 1
                        voucher_obj.save()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("PlaceB2BOnlineOrderAPI: voucher code not handled properly! %s at %s", e, str(exc_tb.tb_lineno))

            payment_info = "NA"
            payment_mode = "NA"
            try:
                payment_info = data["paymentMethod"]
                payment_mode = data["paymentMethod"]["name"]
            except Exception as e:
                pass

            order_obj = Order.objects.create(owner = order_request_obj.owner,
                                             shipping_address=order_request_obj.shipping_address,
                                             billing_address=order_request_obj.billing_address,
                                             to_pay=order_request_obj.to_pay,
                                             real_to_pay=order_request_obj.to_pay,
                                             order_placed_date=timezone.now(),
                                             voucher=order_request_obj.voucher,
                                             location_group=order_request_obj.location_group,
                                             delivery_fee=order_request_obj.get_delivery_fee(),
                                             payment_status="paid",
                                             payment_info=payment_info,
                                             payment_mode=payment_mode,
                                             merchant_reference=merchant_reference,
                                             bundleid=order_request_obj.merchant_reference,
                                             additional_note=order_request_obj.additional_note,
                                             admin_note = order_request_obj.admin_note,
                                             cod_charge=0)

            unit_order_request_objs = UnitOrderRequest.objects.filter(order_request=order_request_obj).exclude(request_status="Rejected")

            for unit_order_request_obj in unit_order_request_objs:
                unit_order_obj = UnitOrder.objects.create(order=order_obj,
                                                          product=unit_order_request_obj.product,
                                                          quantity=unit_order_request_obj.final_quantity,
                                                          price=unit_order_request_obj.final_price)
                UnitOrderStatus.objects.create(unit_order=unit_order_obj)

            order_request_obj.is_placed = True
            order_request_obj.save()

            # Trigger Email
            try:
                p1 = threading.Thread(target=send_order_confirmation_mail, args=(order_obj,))
                p1.start()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("PlaceB2BOnlineOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))

            # Refresh Stock
            refresh_stock(order_obj)

            response["purchase"] = calculate_gtm(order_obj)

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PlaceB2BOnlineOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))
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
                        address_obj = Address.objects.filter(user=dealshub_user_obj, is_shipping=True)[0]
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
                                                 billing_address=cart_obj.billing_address,
                                                 to_pay=cart_obj.to_pay,
                                                 real_to_pay=cart_obj.to_pay,
                                                 order_placed_date=timezone.now(),
                                                 voucher=cart_obj.voucher,
                                                 location_group=cart_obj.location_group,
                                                 delivery_fee=cart_obj.get_delivery_fee(),
                                                 cod_charge=cart_obj.location_group.cod_charge,
                                                 additional_note=cart_obj.additional_note)

                for unit_cart_obj in unit_cart_objs:
                    unit_order_obj = UnitOrder.objects.create(order=order_obj,
                                                              product=unit_cart_obj.product,
                                                              quantity=unit_cart_obj.quantity,
                                                              price=unit_cart_obj.product.get_actual_price_for_customer(dealshub_user_obj))
                    UnitOrderStatus.objects.create(unit_order=unit_order_obj)


                try:
                    unit_cart_objs = UnitCart.objects.filter(cart=cart_obj)
                    custom_data = []
                    for unit_cart_obj in unit_cart_objs:
                        custom_data.append(CustomData(
                            content_type="product",
                            value=unit_cart_obj.product.now_price,
                            currency=unit_cart_obj.product.get_currency(),
                            content_name=unit_cart_obj.product.get_name(),
                            content_category=unit_cart_obj.product.get_category(),
                            contents=[Content(product_id=unit_cart_obj.product.get_product_id(), quantity=unit_cart_obj.quantity, item_price=unit_cart_obj.product.now_price)],
                        ))
                    calling_facebook_api(event_name="Purchase",user=dealshub_user_obj,request=request,custom_data=custom_data)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("PlaceOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))

                # Cart gets empty
                for unit_cart_obj in unit_cart_objs:
                    unit_cart_obj.delete()

                # cart_obj points to None
                cart_obj.shipping_address = None
                cart_obj.voucher = None
                cart_obj.to_pay = 0
                cart_obj.additional_note = ""
                cart_obj.merchant_reference = ""
                cart_obj.payment_info = "{}"
                cart_obj.save()
            else:
                fast_cart_obj = FastCart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)

                try:
                    if fast_cart_obj.shipping_address==None:
                        address_obj = Address.objects.filter(user=dealshub_user_obj, is_shipping=True)[0]
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
                                                 billing_address=fast_cart_obj.billing_address,
                                                 to_pay=fast_cart_obj.to_pay,
                                                 real_to_pay=fast_cart_obj.to_pay,
                                                 order_placed_date=timezone.now(),
                                                 voucher=fast_cart_obj.voucher,
                                                 location_group=fast_cart_obj.location_group,
                                                 delivery_fee=fast_cart_obj.get_delivery_fee(),
                                                 cod_charge=fast_cart_obj.location_group.cod_charge,
                                                 additional_note=fast_cart_obj.additional_note)

                unit_order_obj = UnitOrder.objects.create(order=order_obj,
                                                          product=fast_cart_obj.product,
                                                          quantity=fast_cart_obj.quantity,
                                                          price=fast_cart_obj.product.get_actual_price_for_customer(dealshub_user_obj))
                UnitOrderStatus.objects.create(unit_order=unit_order_obj)

                try:
                    custom_data = []
                    custom_data.append(CustomData(
                        content_type="product",
                        value=fast_cart_obj.product.now_price,
                        currency=fast_cart_obj.product.get_currency(),
                        content_name=fast_cart_obj.product.get_name(),
                        content_category=fast_cart_obj.product.get_category(),
                        contents=[Content(product_id=fast_cart_obj.product.get_product_id(), quantity=fast_cart_obj.quantity, item_price=fast_cart_obj.product.now_price)],
                    ))
                    calling_facebook_api(event_name="Purchase",user=fast_cart_obj.owner,request=request,custom_data=custom_data)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("PlaceOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))
                    
                # cart_obj points to None
                fast_cart_obj.shipping_address = None
                fast_cart_obj.voucher = None
                fast_cart_obj.to_pay = 0
                fast_cart_obj.additional_note = ""
                fast_cart_obj.merchant_reference = ""
                fast_cart_obj.payment_info = "{}"
                fast_cart_obj.product = None
                fast_cart_obj.save()


            # Trigger Email
            try:
                p1 = threading.Thread(target=send_order_confirmation_mail, args=(order_obj,))
                p1.start()
                website_group = order_obj.location_group.website_group.name
                unit_order_obj = UnitOrder.objects.filter(order=order_obj)[0]
                customer_name = order_obj.owner.first_name
                order_uuid = order_obj.uuid
                link = order_obj.location_group.website_group.link
                if website_group=="parajohn":
                    message = "Dear "+customer_name +", Thank you for shopping with "+ link +". Your order "+ link + "/orders/" + order_uuid +" has been confirmed & will be shipped soon."
                    p2 = threading.Thread(target=send_parajohn_order_status_sms, args=(unit_order_obj,message,))
                    p2.start()
                elif website_group in ["shopnesto", "shopnestokuwait", "shopnestobahrain"]:
                    message = "Dear "+customer_name +", Thank you for shopping with "+ link +". Your order "+ link + "/orders/" + order_uuid +" has been confirmed & will be shipped soon."
                    p2 = threading.Thread(target=send_wigme_order_status_sms, args=(unit_order_obj,message,))
                    p2.start()
                elif website_group=="daycart":
                    message = "Dear "+customer_name +", Thank you for shopping with "+ link +". Your order "+ link + "/orders/" + order_uuid +" has been confirmed & will be shipped soon."
                    p2 = threading.Thread(target=send_daycart_order_status_sms, args=(unit_order_obj,message,))
                    p2.start()
                elif website_group=="geepasuganda":
                    message = "Dear "+customer_name +", Thank you for shopping with "+ link +". Your order "+ link + "/orders/" + order_uuid +" has been confirmed & will be shipped soon."
                    p2 = threading.Thread(target=send_geepas_order_status_sms, args=(unit_order_obj,message,))
                    p2.start()
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

            unit_cart_objs = UnitCart.objects.filter(cart=cart_obj)
            
            omnycomm_user_obj = OmnyCommUser.objects.get(username=request.user.username)
            order_obj = Order.objects.create(owner=cart_obj.owner,
                                             shipping_address=cart_obj.shipping_address,
                                             billing_address=cart_obj.billing_address,
                                             to_pay=cart_obj.to_pay,
                                             real_to_pay=cart_obj.to_pay,
                                             order_placed_date=timezone.now(),
                                             voucher=cart_obj.voucher,
                                             reference_medium= cart_obj.reference_medium,
                                             additional_note=cart_obj.additional_note,
                                             is_order_offline = True,
                                             location_group=cart_obj.location_group,
                                             delivery_fee=cart_obj.offline_delivery_fee,
                                             cod_charge=cart_obj.offline_cod_charge,
                                             offline_sales_person=omnycomm_user_obj)
            
            for unit_cart_obj in unit_cart_objs:
                unit_order_obj = UnitOrder.objects.create(order=order_obj,
                                                          product=unit_cart_obj.product,
                                                          quantity=unit_cart_obj.quantity,
                                                          price=unit_cart_obj.offline_price)
                UnitOrderStatus.objects.create(unit_order=unit_order_obj)

            try:
                unit_cart_objs = UnitCart.objects.filter(cart=cart_obj)
                custom_data = []
                for unit_cart_obj in unit_cart_objs:
                    custom_data.append(CustomData(
                        content_type="product",
                        value=unit_cart_obj.product.now_price,
                        currency=unit_cart_obj.product.get_currency(),
                        content_name=unit_cart_obj.product.get_name(),
                        content_category=unit_cart_obj.product.get_category(),
                        contents=[Content(product_id=unit_cart_obj.product.get_product_id(), quantity=unit_cart_obj.quantity, item_price=unit_cart_obj.product.now_price)],
                    ))
                calling_facebook_api(event_name="Purchase",user=dealshub_user_obj,request=request,custom_data=custom_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("PlaceOfflineOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))

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
            language_code = data.get("language","en")
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
                    
                    if order_obj.payment_mode == "CHEQUE":
                        image_objs = order_obj.cheque_images.all()
                        cheque_images_list = []
                        for image_obj in image_objs:
                            try:
                                if image_obj.mid_image!=None:
                                    temp_dict_cheque_image = {}
                                    temp_dict_cheque_image["url"] = image_obj.mid_image.url
                                    temp_dict_cheque_image["uuid"] = image_obj.pk
                                    cheque_images_list.append(temp_dict_cheque_image)
                            except Exception as e:
                                exc_type, exc_obj, exc_tb = sys.exc_info()
                                logger.warning("FetchOrderListAPI: %s at %s", e, str(exc_tb.tb_lineno))
                        temp_dict["cheque_images_list"] = cheque_images_list
                        temp_dict["cheque_approved"] =  order_obj.cheque_approved

                    temp_dict["paymentStatus"] = order_obj.payment_status
                    temp_dict["customerName"] = order_obj.owner.first_name
                    temp_dict["bundleId"] = order_obj.bundleid
                    temp_dict["uuid"] = order_obj.uuid
                    temp_dict["isVoucherApplied"] = is_voucher_applied
                    if is_voucher_applied:
                        temp_dict["voucherCode"] = voucher_obj.voucher_code
                    temp_dict["shippingAddress"] = order_obj.shipping_address.get_shipping_address()
                    temp_dict["billingAddress"] = ""
                    if order_obj.billing_address != None:
                        temp_dict["billingAddress"] = order_obj.billing_address.get_shipping_address()

                    unit_order_objs = UnitOrder.objects.filter(order=order_obj)
                    unit_order_list = []
                    custom_data = []
                    for unit_order_obj in unit_order_objs:
                        temp_dict2 = {}
                        temp_dict2["orderId"] = unit_order_obj.orderid
                        temp_dict2["uuid"] = unit_order_obj.uuid
                        temp_dict2["currentStatus"] = unit_order_obj.current_status
                        temp_dict2["quantity"] = unit_order_obj.quantity
                        temp_dict2["price"] = unit_order_obj.price
                        temp_dict2["currency"] = unit_order_obj.product.get_currency()
                        unit_order_status = unit_order_obj.current_status_admin
                        temp_dict2["can_user_cancel_unitorder"] = False
                        if unit_order_status=="pending" or unit_order_status=="approved" or unit_order_status=="picked":
                            temp_dict2["can_user_cancel_unitorder"] = True
                        temp_dict2["productName"] = unit_order_obj.product.get_name(language_code)
                        temp_dict2["productImageUrl"] = unit_order_obj.product.get_display_image_url()
                        unit_order_list.append(temp_dict2)
                        try:
                            custom_data.append(CustomData(
                                content_type="product",
                                value=unit_order_obj.product.now_price,
                                currency=unit_order_obj.product.get_currency(),
                                content_name=unit_order_obj.product.get_name(),
                                content_category=unit_order_obj.product.get_category(),
                                contents=[Content(product_id=unit_order_obj.product.get_product_id(), quantity=unit_order_obj.product.stock, item_price=unit_order_obj.product.now_price)],
                            ))
                        except Exception as e:
                            exc_type, exc_obj, exc_tb = sys.exc_info()
                            logger.error("FetchOrderListAPI: %s at %s", e, str(exc_tb.tb_lineno))   
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

            try:
                dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
                calling_facebook_api(event_name="ViewContent",user=dealshub_user_obj,request=request,custom_data=custom_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("FetchOrderListAPI: %s at %s", e, str(exc_tb.tb_lineno))
                
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOrderListAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchOrderRequestListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchOrderRequestListAPI: %s", str(data))
            language_code = data.get("language","en")
            if not isinstance(data, dict):
                data = json.loads(data)

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            order_request_list = []
            order_request_objs = OrderRequest.objects.filter(owner=dealshub_user_obj).filter(is_placed=False).order_by('-pk')
            for order_request_obj in order_request_objs:
                try:
                    voucher_obj = order_request_obj.voucher
                    is_voucher_applied = voucher_obj is not None
                    temp_dict = {}
                    temp_dict["dateCreated"] = order_request_obj.get_date_created()
                    temp_dict["paymentMode"] = order_request_obj.payment_mode
                    temp_dict["requestStatus"] = order_request_obj.request_status
                    temp_dict["customerName"] = order_request_obj.owner.first_name
                    temp_dict["bundleId"] = order_request_obj.bundleid
                    temp_dict["uuid"] = order_request_obj.uuid
                    temp_dict["isVoucherApplied"] = is_voucher_applied
                    temp_dict["additionalNote"] = order_request_obj.additional_note
                    if is_voucher_applied:
                        temp_dict["voucherCode"] = voucher_obj.voucher_code
                    address_obj = order_request_obj.shipping_address
                    temp_dict["shippingAddress"] = {
                        "tag": address_obj.tag,
                        "line1": json.loads(address_obj.address_lines)[0],
                        "line2": json.loads(address_obj.address_lines)[1],
                        "emirates": address_obj.emirates
                    }
                    temp_dict["billingAddress"] = {}
                    billing_address_obj = order_request_obj.billing_address
                    if billing_address_obj != None:
                        temp_dict["billingAddress"] = {
                            "tag": billing_address_obj.tag,
                            "line1": json.loads(billing_address_obj.address_lines)[0],
                            "line2": json.loads(billing_address_obj.address_lines)[1],
                            "emirates": billing_address_obj.emirates
                        }

                    unit_order_request_objs = UnitOrderRequest.objects.filter(order_request=order_request_obj)
                    if order_request_obj.request_status == "Approved" and unit_order_request_objs.exclude(request_status="Rejected").count() != unit_order_request_objs.count():
                        temp_dict["requestStatus"] = "Partially Approved"
                    unit_order_request_list = []
                    for unit_order_request_obj in unit_order_request_objs:
                        temp_dict2 = {}
                        temp_dict2["orderReqId"] = unit_order_request_obj.order_req_id
                        temp_dict2["uuid"] = unit_order_request_obj.uuid
                        temp_dict2["currentStatus"] = unit_order_request_obj.request_status
                        temp_dict2["initialQuantity"] = unit_order_request_obj.initial_quantity
                        temp_dict2["initialPrice"] = unit_order_request_obj.initial_price
                        temp_dict2["finalQuantity"] = unit_order_request_obj.final_quantity
                        temp_dict2["finalPrice"] = unit_order_request_obj.final_price
                        temp_dict2["currency"] = unit_order_request_obj.product.get_currency()
                        temp_dict2["productName"] = unit_order_request_obj.product.get_name(language_code)
                        temp_dict2["productImageUrl"] = unit_order_request_obj.product.get_display_image_url()
                        if unit_order_request_obj.request_status == "Approved" and temp_dict2["initialQuantity"] != temp_dict2["finalQuantity"]:
                            temp_dict["requestStatus"] = "Partially Approved"
                        unit_order_request_list.append(temp_dict2)
                    temp_dict["currency"] = order_request_obj.get_currency()
                    temp_dict["totalItems"] = unit_order_request_objs.exclude(request_status="Rejected").count()
                    temp_dict["totalQuantity"] = unit_order_request_objs.exclude(request_status="Rejected").aggregate(total_quantity=Sum('final_quantity'))["total_quantity"]
                    temp_dict["totalAmount"] =order_request_obj.get_subtotal()
                    temp_dict["unitOrderRequestList"] = unit_order_request_list
                    order_request_list.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchOrderRequestListAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["orderRequestList"] = order_request_list
            if len(order_request_list)==0:
                response["isOrderRequestListEmpty"] = True
            else:
                response["isOrderRequestListEmpty"] = False

            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOrderRequestListAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class UpdateUnitOrderRequestAdminAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateUnitOrderRequestAdminAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            order_request_obj = OrderRequest.objects.get(uuid=data["OrderRequestUuid"])
            unit_order_request_uuid = data.get("UnitOrderRequestUuid","")

            if unit_order_request_uuid != "":
                unit_order_request_obj = UnitOrderRequest.objects.get(order_request = order_request_obj,uuid = unit_order_request_uuid)
                prev_instance = deepcopy(unit_order_request_obj)
                unit_order_request_obj.final_quantity = data.get("finalQuantity",unit_order_request_obj.final_quantity)
                unit_order_request_obj.final_price = data.get("finalPrice",unit_order_request_obj.final_price)
                unit_order_request_obj.request_status = data.get("requestStatus",unit_order_request_obj.request_status)
                unit_order_request_obj.save()
                render_value = "unit order request {} of order request {} is updated.".format(unit_order_request_obj.order_req_id,order_request_obj.uuid)
                activitylog(user=request.user,table_name=UnitOrderRequest,action_type='updated',location_group_obj=unit_order_request_obj.order_request.location_group,prev_instance=prev_instance,current_instance=unit_order_request_obj,table_item_pk=unit_order_request_obj.uuid,render=render_value)

            update_order_request_bill(order_request_obj,cod=True)
            unit_order_request_objs = UnitOrderRequest.objects.filter(order_request=order_request_obj)   

            response["OrderRequestUuid"] = order_request_obj.uuid
            response["totalItems"] = unit_order_request_objs.exclude(request_status="Rejected").count()
            response["totalQuantity"] = unit_order_request_objs.exclude(request_status="Rejected").aggregate(total_quantity=Sum('final_quantity'))["total_quantity"]

            is_cod = True if order_request_obj.payment_mode=="COD" else False
            subtotal = order_request_obj.get_subtotal()
            delivery_fee = order_request_obj.get_delivery_fee(cod=is_cod)
            cod_fee = order_request_obj.get_cod_charge(cod=is_cod)
            to_pay = order_request_obj.get_total_amount(cod=is_cod)
            vat = order_request_obj.get_vat(cod=is_cod)

            response["subtotal"] = str(subtotal)
            response["deliveryFee"] = str(delivery_fee)
            response["codFee"] = str(cod_fee)
            response["vat"] = str(vat)
            response["toPay"] = str(to_pay)
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateUnitOrderRequestAdminAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class SetOrderChequeImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SetOrderChequeImageAPI: %s", str(data))
            
            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            order_uuid = data["uuid"]
            action = data.get("action","")
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            order_obj = Order.objects.get(uuid=order_uuid)
            image_count = int(data.get("cheque_image_count",0))
            current_image_count = order_obj.cheque_images.count()
            prev_instance = list(order_obj.cheque_images.all())

            if is_oc_user(request.user)==False:
                # if user is dealshub user and if cheque images already present then restricted access!!
                if current_image_count:
                    response['status'] = 403
                    logger.warning("SetOrderChequeImageAPI Restricted Access!")
                else:
                    cheque_images_list = []
                    for i in range(image_count):
                        try:
                            image_obj = Image.objects.create(image = data["cheque_image_" + str(i)])
                            order_obj.cheque_images.add(image_obj)
                            temp_dict_cheque_image = {}
                            temp_dict_cheque_image["url"] = image_obj.mid_image.url
                            temp_dict_cheque_image["uuid"] = image_obj.pk
                            cheque_images_list.append(temp_dict_cheque_image)
                        except Exception as e:
                            exc_type, exc_obj, exc_tb = sys.exc_info()
                            logger.warning("SetOrderChequeImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
                            
                    order_obj.save()
                    response['status'] = 200
                    response["cheque_images_list"] = cheque_images_list
                    response["cheque_approved"] =  order_obj.cheque_approved
                return Response(data=response)
            else:
                if order_obj.cheque_approved:
                    # once cheque approved OCuser will not able to update it
                    response['status'] = 200
                    return Response(data=response)

                if action == "approve":
                    order_obj.cheque_approved = True
                    order_obj.save()

                elif action == "disapprove":
                    send_order_cheque_disapproval_mail(order_obj)
                    order_obj.cheque_images.clear()
                    order_obj.save()
                
                elif action == "delete":
                    image_uuid = int(data["image_uuid"])
                    image_obj = Image.objects.get(pk=image_uuid)
                    order_obj.cheque_images.remove(image_obj)
                    order_obj.save()

                elif action == "update":
                    for i in range(image_count):
                        image_obj = Image.objects.create(image = data["cheque_image_" + str(i)])
                        order_obj.cheque_images.add(image_obj)
                    order_obj.save()  
                    
                image_objs = order_obj.cheque_images.all()
                cheque_images_list = []
                for image_obj in image_objs:
                    try:
                        temp_dict_cheque_image = {}
                        temp_dict_cheque_image["url"] = image_obj.mid_image.url
                        temp_dict_cheque_image["uuid"] = image_obj.pk
                        cheque_images_list.append(temp_dict_cheque_image)
                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        logger.warning("SetOrderChequeImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
                response["cheque_images_list"] = cheque_images_list
                response["cheque_approved"] =  order_obj.cheque_approved

                render_value = "Cheque images "+ action +" by username:- " + request.user.username
                current_instance = list(order_obj.cheque_images.all())
                activitylog(user=request.user,table_name=Order,action_type='updated',location_group_obj=location_group_obj,prev_instance=prev_instance,current_instance=current_instance,table_item_pk=order_obj.uuid,render=render_value)
                    
            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SetOrderChequeImageAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchOrderListAdminAPI Restricted Access!")
                return Response(data=response)

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
            language_code = data.get("language","en")
            if not isinstance(data, dict):
                data = json.loads(data)

            order_uuid = data["uuid"]
            is_b2b = data.get("is_b2b", False)
            order_obj = Order.objects.get(uuid=order_uuid)
            voucher_obj = order_obj.voucher
            is_voucher_applied = voucher_obj is not None

            unit_order_objs = UnitOrder.objects.filter(order=order_obj)
            try:
                if order_obj.owner != DealsHubUser.objects.get(username = request.user.username):
                    response["status"] = 403
                    return Response(data=response)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("FetchOrderDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

            enable_order_edit = False
            if order_obj.payment_status=="cod": # and unit_order_objs.filter(current_status_admin="pending").exists():
                enable_order_edit = True

            response["enableOrderEdit"] = enable_order_edit
            response["is_order_offline"] = order_obj.is_order_offline
            response["bundleId"] = order_obj.bundleid 
            response["dateCreated"] = order_obj.get_date_created()
            response["paymentMode"] = order_obj.payment_mode
            response["paymentStatus"] = order_obj.payment_status
            response["customerName"] = order_obj.owner.first_name
            response["additional_note"] = order_obj.additional_note
            response["isVoucherApplied"] = is_voucher_applied
            if is_voucher_applied:
                response["voucherCode"] = voucher_obj.voucher_code
                response["voucherDiscount"] = voucher_obj.get_voucher_discount(order_obj.get_subtotal())
            response["shippingMethod"] = unit_order_objs[0].shipping_method
            response["shippingAddress"] = get_address_dict(order_obj.shipping_address)
            if is_b2b:
                response["billingAddress"] = get_address_dict(order_obj.billing_address)
            unit_order_list = []
            custom_data = []
            for unit_order_obj in unit_order_objs:
                temp_dict = {}
                temp_dict["orderId"] = unit_order_obj.orderid
                temp_dict["uuid"] = unit_order_obj.uuid
                temp_dict["currentStatus"] = unit_order_obj.current_status
                temp_dict["quantity"] = unit_order_obj.quantity
                temp_dict["price"] = unit_order_obj.price
                temp_dict["currency"] = unit_order_obj.product.get_currency()
                temp_dict["productName"] = unit_order_obj.product.get_name(language_code)
                temp_dict["productNameAr"] = unit_order_obj.product.get_name("ar")
                temp_dict["productImageUrl"] = unit_order_obj.product.get_display_image_url()
                temp_dict["sellerSku"] = unit_order_obj.product.get_seller_sku()
                temp_dict["productId"] = unit_order_obj.product.get_product_id()
                temp_dict["productUuid"] = unit_order_obj.product.uuid
                temp_dict["link"] = unit_order_obj.product.url
                temp_dict["user_cancellation_status"] = unit_order_obj.user_cancellation_status

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
                try:
                    custom_data.append(CustomData(
                        content_type="product",
                        value=unit_order_obj.product.now_price,
                        currency=unit_order_obj.product.get_currency(),
                        content_name=unit_order_obj.product.get_name(),
                        content_category=unit_order_obj.product.get_category(),
                        contents=[Content(product_id=unit_order_obj.product.get_product_id(), quantity=unit_order_obj.product.stock, item_price=unit_order_obj.product.now_price)],
                    ))
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchOrderDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))  
            subtotal = order_obj.get_subtotal()
            delivery_fee = order_obj.get_delivery_fee()
            cod_fee = order_obj.get_cod_charge()
            to_pay = order_obj.to_pay
            real_to_pay = order_obj.real_to_pay
            vat = order_obj.get_vat()

            response["subtotal"] = str(subtotal)
            response["deliveryFee"] = str(delivery_fee)
            response["codFee"] = str(cod_fee)
            response["vat"] = str(vat)
            response["toPay"] = str(to_pay)
            response["realToPay"] = str(real_to_pay)

            response["unitOrderList"] = unit_order_list
            response["status"] = 200

            try:
                dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
                calling_facebook_api(event_name="ViewContent",user=dealshub_user_obj,request=request,custom_data=custom_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("FetchOrderDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
                
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOrderDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchOrderVersionDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchOrderVersionDetails: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchOrderVersionDetailsAPI Restricted Access!")
                return Response(data=response)

            order_uuid = data["uuid"]
            order_obj = Order.objects.get(uuid=order_uuid)
            version_order_list = []
            version_order_objs = VersionOrder.objects.filter(order=order_obj).order_by('-pk')
            for version_order_obj in version_order_objs:
                temp_dict = {}
                temp_dict["uuid"] = version_order_obj.uuid
                temp_dict["date"] = str(timezone.localtime(version_order_obj.timestamp).strftime("%d %b, %Y"))
                temp_dict["time"] = str(timezone.localtime(version_order_obj.timestamp).strftime("%I:%M %p"))
                if version_order_obj.user!=None:
                    temp_dict["user"] = version_order_obj.user.username
                temp_dict["change_info"] = json.loads(version_order_obj.change_information)
                version_order_list.append(temp_dict)
            response['status'] = 200
            response['version_order_list'] = version_order_list
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOrderVersionDetails: %s at %s", e, str(exc_tb.tb_lineno))
        return Response(data=response)
      

class CreateUnitOrderCancellationRequestAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data 
            logger.info("CreateUnitOrderCancellationRequestAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            unit_order_cancellation_list = data["unit_order_cancellation_list"]

            for unit_order_cancellation_item in unit_order_cancellation_list:
                unit_order_obj = UnitOrder.objects.get(uuid=unit_order_cancellation_item["unit_order_uuid"])
                unit_order_obj.cancelled_by_user = True
                unit_order_obj.user_cancellation_note = unit_order_cancellation_item["note"]
                unit_order_obj.user_cancellation_status = "pending"
                unit_order_obj.save()
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateUnitOrderCancellationRequestAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CreateOrderCancellationRequestAPI(APIView):
    
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data 
            logger.info("CreateOrderCancellationRequestAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            order_uuid = data["order_uuid"]
            cancellation_note = data.get("note","")
            
            unit_order_objs = UnitOrder.objects.filter(order__uuid=order_uuid)

            for unit_order_obj in unit_order_objs:
                unit_order_obj.cancelled_by_user = True
                unit_order_obj.user_cancellation_note = cancellation_note
                unit_order_obj.user_cancellation_status = "pending"
                unit_order_obj.save()
                
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateOrderCancellationRequestAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

#API with active log
class CreateOfflineCustomerAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("CreateOfflineCustomerAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("CreateOfflineCustomerAPI Restricted Access!")
                return Response(data=response)

            contact_number = data["contact_number"]
            location_group_uuid = data["locationGroupUuid"]
            first_name = data["first_name"]
            last_name = data.get("last_name", "")
            email = data["email"]

            digits = "0123456789"
            OTP = ""
            for i in range(6):
                OTP += digits[int(math.floor(random.random()*10))]

            if contact_number[0]=="0":
                contact_number = contact_number[1:]

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            website_group_obj = location_group_obj.website_group
            website_group_name = website_group_obj.name

            if DealsHubUser.objects.filter(username=contact_number+"-"+website_group_name).exists()==False:
                if location_group_obj.is_b2b == True:
                    b2b_user_obj = B2BUser.objects.create(username=contact_number+"-"+website_group_name, contact_number=contact_number, first_name=first_name, last_name=last_name, email=email, email_verified=True, website_group=website_group_obj)
                    dealshub_user_obj = DealsHubUser.objects.get(username=b2b_user_obj.username)
                    b2b_user_obj.set_password(OTP)
                    b2b_user_obj.verification_code = OTP
                    b2b_user_obj.is_signup_completed = True
                    b2b_user_obj.passport_copy_status = "Approved"
                    b2b_user_obj.vat_certificate_status = "Approved"
                    b2b_user_obj.trade_license_status = "Approved"
                    b2b_user_obj.save()
                else:
                    dealshub_user_obj = DealsHubUser.objects.create(username=contact_number+"-"+website_group_name, contact_number=contact_number, first_name=first_name, last_name=last_name, email=email, email_verified=True, website_group=website_group_obj)
                    dealshub_user_obj.set_password(OTP)
                    dealshub_user_obj.verification_code = OTP
                    dealshub_user_obj.save()

                for location_group_obj in LocationGroup.objects.filter(website_group=website_group_obj):
                    Cart.objects.create(owner=dealshub_user_obj, location_group=location_group_obj, offline_cod_charge=location_group_obj.cod_charge, offline_delivery_fee=location_group_obj.delivery_fee)
                    WishList.objects.create(owner=dealshub_user_obj, location_group=location_group_obj)
                    FastCart.objects.create(owner=dealshub_user_obj, location_group=location_group_obj)

                response["username"] = dealshub_user_obj.username

                render_value = "New User created offline with username " + dealshub_user_obj.username
                activitylog(request.user, DealsHubUser, "created", dealshub_user_obj.username, None, dealshub_user_obj, location_group_obj, render_value)
                response["status"] = 200
            else:
                response["status"] = 409

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateOfflineCustomerAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

#API with active log
class UpdateOfflineUserProfileAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateOfflineUserProfileAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UpdateOfflineUserProfileAPI Restricted Access!")
                return Response(data=response)

            username = data["username"]
            email_id = data["emailId"]
            first_name = data["firstName"]
            last_name = data.get("lastName", "")
            contact_number = data["contactNumber"]

            if contact_number[0]=="0":
                contact_number = contact_number[1:]

            if DealsHubUser.objects.filter(username=username).exists():
                dealshub_user_obj = DealsHubUser.objects.get(username=username)
                prev_dealshub_user_obj = deepcopy(dealshub_user_obj)
                dealshub_user_obj.email = email_id
                dealshub_user_obj.first_name = first_name
                dealshub_user_obj.last_name = last_name
                dealshub_user_obj.contact_number = contact_number
                dealshub_user_obj.save()
                
                render_value = "User profile updated for username " + dealshub_user_obj.username
                activitylog(request.user, DealsHubUser, "updated", dealshub_user_obj.username, prev_dealshub_user_obj, dealshub_user_obj, None, render_value)
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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("SearchCustomerAutocompleteAPI Restricted Access!")
                return Response(data=response)

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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchOfflineUserProfileAPI Restricted Access!")
                return Response(data=response)

            username = data["username"]
            location_group_uuid = data.get("locationGroupUuid", "")
            is_set_default_COD_charges = data.get("isSetDefaultCODCharges", False)
            is_b2b = data.get("is_b2b", False)
            dealshub_user_obj = DealsHubUser.objects.get(username=username)

            response["firstName"] = dealshub_user_obj.first_name
            response["lastName"] = dealshub_user_obj.last_name
            response["emailId"] = dealshub_user_obj.email
            response["contactNumber"] = dealshub_user_obj.contact_number
            response['shippingAddressList'] = get_address_list(dealshub_user_obj, type_addr="shipping")
            if is_b2b:
                response['billingAddressList'] = get_address_list(dealshub_user_obj, type_addr="billing")
                response['primeBillingAddress'] = get_address_dict(dealshub_user_obj.prime_billing_address)
            if is_set_default_COD_charges:
                location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
                cart_obj = Cart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
                cart_obj.offline_delivery_fee = cart_obj.location_group.delivery_fee
                cart_obj.offline_cod_charge = cart_obj.location_group.cod_charge
                cart_obj.save()            
            
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

            try:
                calling_facebook_api(event_name="ViewContent",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("FetchUserProfileAPI: %s at %s", e, str(exc_tb.tb_lineno))
                
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

            try:
                calling_facebook_api(event_name="ViewContent",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("UpdateUserProfileAPI: %s at %s", e, str(exc_tb.tb_lineno))
                
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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchCustomerListAPI Restricted Access!")
                return Response(data=response)

            search_list = data.get("search_list", [])

            location_group_uuid = data["locationGroupUuid"]

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group
            website_dealshub_user_objs = DealsHubUser.objects.filter(website_group=website_group_obj)

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

            if location_group_obj.name in ["WIGme - B2B"]:
                dealshub_user_objs = dealshub_user_objs.filter(b2buser__is_signup_completed=True)

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

            if "b2b-verified" in filter_parameters:
                if filter_parameters["b2b-verified"]==True:
                    b2b_user_objs = B2BUser.objects.filter(vat_certificate_status="Approved", trade_license_status="Approved", passport_copy_status="Approved")
                    dealshub_user_objs = dealshub_user_objs.filter(b2buser__in=b2b_user_objs)
                elif filter_parameters["b2b-verified"]==False:
                    b2b_user_objs = B2BUser.objects.exclude(vat_certificate_status="Approved", trade_license_status="Approved", passport_copy_status="Approved")
                    dealshub_user_objs = dealshub_user_objs.filter(b2buser__in=b2b_user_objs)

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
                    temp_dict["date_created"] = str(dealshub_user_obj.date_created.strftime("%d %b %Y"))
                    if location_group_obj.is_b2b:
                        b2b_user_obj = B2BUser.objects.get(username = dealshub_user_obj.username)
                        temp_dict["companyName"] = b2b_user_obj.company_name
                        total_qty = UnitOrder.objects.filter(order__owner=dealshub_user_obj).aggregate(Sum('quantity'))["quantity__sum"]
                        if total_qty==None:
                            total_qty = 0
                        temp_dict["total_qty"] = total_qty
                        temp_dict["total_items"] = len(UnitOrder.objects.filter(order__owner=dealshub_user_obj).values("product").distinct())
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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchCustomerDetailsAPI Restricted Access!")
                return Response(data=response)

            username = data["username"]

            is_b2b = False
            dealshub_user_obj = DealsHubUser.objects.get(username=username)
            location_group_uuid = data.get("locationGroupUuid","")
            if location_group_uuid != "":
                location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
                is_b2b = location_group_obj.is_b2b

            temp_dict = {}
            temp_dict["customerName"] = dealshub_user_obj.first_name
            temp_dict["emailId"] = dealshub_user_obj.email
            temp_dict["contactNumber"] = dealshub_user_obj.contact_number
            if is_b2b == True:
                b2b_user_obj = B2BUser.objects.get(username = dealshub_user_obj.username)
                temp_dict["cohort"] = b2b_user_obj.cohort
                temp_dict["companyName"] = b2b_user_obj.company_name

                temp_dict["vatCertificate"] = ""
                temp_dict["vatCertificateType"] = "EMPTY"
                if b2b_user_obj.vat_certificate!=None and b2b_user_obj.vat_certificate!="":
                    temp_dict["vatCertificateType"] = "PDF"
                    temp_dict["vatCertificate"] = b2b_user_obj.vat_certificate.url
                elif b2b_user_obj.vat_certificate_images.exists() > 0:
                    temp_dict["vatCertificateType"] = "IMG"
                    temp_dict2 = []
                    vat_certificate_image_objs = b2b_user_obj.vat_certificate_images.all()
                    for vat_certificate_image_obj in vat_certificate_image_objs:
                        temp_dict3 = {}
                        temp_dict3["image_url"] = vat_certificate_image_obj.image.url
                        temp_dict3["pk"] = vat_certificate_image_obj.pk
                        temp_dict2.append(temp_dict3)
                    temp_dict["vatCertificate"] = temp_dict2

                temp_dict["passportCopy"] = ""
                temp_dict["passportCopyType"] = "EMPTY"
                if b2b_user_obj.passport_copy!=None and b2b_user_obj.passport_copy!="":
                    temp_dict["passportCopyType"] = "PDF"
                    temp_dict["passportCopy"] = b2b_user_obj.passport_copy.url
                elif b2b_user_obj.passport_copy_images.exists() > 0:
                    temp_dict["passportCopyType"] = "IMG"
                    temp_dict2 = []
                    passport_copy_image_objs = b2b_user_obj.passport_copy_images.all()
                    for passport_copy_image_obj in passport_copy_image_objs:
                        temp_dict3 = {}
                        temp_dict3["image_url"] = passport_copy_image_obj.image.url
                        temp_dict3["pk"] = passport_copy_image_obj.pk
                        temp_dict2.append(temp_dict3)
                    temp_dict["passportCopy"] = temp_dict2

                temp_dict["tradeLicense"] = ""
                temp_dict["tradeLicenseType"] = "EMPTY"
                if b2b_user_obj.trade_license!=None and b2b_user_obj.trade_license!="":
                    temp_dict["tradeLicenseType"] = "PDF"
                    temp_dict["tradeLicense"] = b2b_user_obj.trade_license.url
                elif b2b_user_obj.trade_license_images.exists() > 0:
                    temp_dict["tradeLicenseType"] = "IMG"
                    temp_dict2 = []
                    trade_license_image_objs = b2b_user_obj.trade_license_images.all()
                    for trade_license_image_obj in trade_license_image_objs:
                        temp_dict3 = {}
                        temp_dict3["image_url"] = trade_license_image_obj.image.url
                        temp_dict3["pk"] = trade_license_image_obj.pk
                        temp_dict2.append(temp_dict3)
                    temp_dict["tradeLicense"] = temp_dict2

                temp_dict["vatCertificateStatus"] = b2b_user_obj.vat_certificate_status
                temp_dict["tradeLicenseStatus"] = b2b_user_obj.trade_license_status
                temp_dict["passportCopyStatus"] = b2b_user_obj.passport_copy_status
                temp_dict["vatCertificateId"] = b2b_user_obj.vat_certificate_id
                temp_dict["passportCopyId"] = b2b_user_obj.passport_copy_id
                temp_dict["tradeLicenseId"] = b2b_user_obj.trade_license_id
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

            review_objs = Review.objects.filter(dealshub_user=dealshub_user_obj).exclude(is_published=False)
            
            unit_cart_list = []
            for unit_cart_obj in UnitCart.objects.filter(cart__owner=dealshub_user_obj):
                temp_dict2 = {}
                temp_dict2["uuid"] = unit_cart_obj.uuid
                temp_dict2["sellerSku"] = unit_cart_obj.product.get_seller_sku()
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
                temp_dict2["sellerSku"] = unit_cart_obj.product.get_seller_sku()
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

#API with active log
class UpdateB2BCustomerStatusAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response["status"] = 500

        try:
            data = request.data
            logger.info("UpdateB2BCustomerStatusAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UpdateB2BCustomerStatusAPI Restricted Access!")
                return Response(data=response)

            username = data["username"]

            b2b_user_obj = B2BUser.objects.get(username = username)
            prev_b2b_user_obj = deepcopy(b2b_user_obj)

            company_name = data["companyName"]
            vat_certificate_status = data["vatCertificateStatus"]
            trade_license_status = data["tradeLicenseStatus"]
            passport_copy_status = data["passportCopyStatus"]
            customer_name = data["customerName"]
            email_id = data["emailId"]
            cohort = data["cohort"]
            vat_certificate_id = data["vatCertificateId"]
            trade_license_id = data["tradeLicenseId"]
            passport_copy_id = data["passportCopyId"]
            vat_certificate_type = data["vatCertificateType"]
            trade_license_type = data["tradeLicenseType"]
            passport_copy_type = data["passportCopyType"]

            is_notify = False
            if vat_certificate_status != b2b_user_obj.vat_certificate_status or trade_license_status != b2b_user_obj.trade_license_status or passport_copy_status != b2b_user_obj.passport_copy_status:
                is_notify = True

            if vat_certificate_type == "IMG":
                image_count = int(data.get("vatCertificateImageCount",0))
                for i in range(image_count):
                    image_obj = Image.objects.create(image = data["vat-certificate-image-" + str(i+1)])
                    b2b_user_obj.vat_certificate_images.add(image_obj)
                b2b_user_obj.vat_certificate = None
            elif vat_certificate_type == "PDF":
                if data["vat-certificate-document"] != "":
                    b2b_user_obj.vat_certificate = data["vat-certificate-document"]
                image_objs = b2b_user_obj.vat_certificate_images.all()
                for image_obj in image_objs:
                    image_obj.delete()

            if trade_license_type == "IMG":
                image_count = int(data.get("tradeLicenseImageCount",0))
                for i in range(image_count):
                    image_obj = Image.objects.create(image = data["trade-license-image-" + str(i+1)])
                    b2b_user_obj.trade_license_images.add(image_obj)
                b2b_user_obj.trade_license = None
            elif trade_license_type == "PDF":
                if data["trade-license-document"] != "":
                    b2b_user_obj.trade_license = data["trade-license-document"]
                image_objs = b2b_user_obj.trade_license_images.all()
                for image_obj in image_objs:
                    image_obj.delete()

            if passport_copy_type == "IMG":
                image_count = int(data.get("passportCopyImageCount",0))
                for i in range(image_count):
                    image_obj = Image.objects.create(image = data["passport-copy-image-" + str(i+1)])
                    b2b_user_obj.passport_copy_images.add(image_obj)
                b2b_user_obj.passport_copy = None
            elif passport_copy_type == "PDF":
                if data["passport-copy-document"] != "":
                    b2b_user_obj.passport_copy = data["passport-copy-document"]
                image_objs = b2b_user_obj.passport_copy_images.all()
                for image_obj in image_objs:
                    image_obj.delete()

            b2b_user_obj.company_name = company_name
            b2b_user_obj.first_name = customer_name
            b2b_user_obj.email = email_id
            b2b_user_obj.vat_certificate_status = vat_certificate_status
            b2b_user_obj.trade_license_status = trade_license_status
            b2b_user_obj.passport_copy_status = passport_copy_status
            b2b_user_obj.cohort = cohort
            b2b_user_obj.save()

            if (b2b_user_obj.vat_certificate_id != vat_certificate_id and B2BUser.objects.filter(vat_certificate_id=vat_certificate_id).count()) or (b2b_user_obj.trade_license_id != trade_license_id and B2BUser.objects.filter(trade_license_id=trade_license_id).count()):
                response["status"] = 403
                response["message"] = "Vat Certificate number or Trade License number already exists!"
                logger.error("UploadB2BDocumentAPI: Vat Certificate number or Trade License number already exists!")
                return Response(data=response)
                
            b2b_user_obj.vat_certificate_id = vat_certificate_id
            b2b_user_obj.trade_license_id = trade_license_id
            b2b_user_obj.passport_copy_id = passport_copy_id
            b2b_user_obj.save()

            if is_notify == True:
                #threading send a mail
                 p1 = threading.Thread(target = send_b2b_user_status_change_mail, args=(b2b_user_obj,))
                 p1.start()

            b2b_location_group_obj = None
            if LocationGroup.objects.filter(is_b2b=True).exists():
                b2b_location_group_obj = LocationGroup.objects.filter(is_b2b=True)[0]
            render_value = "B2B user status updated offline for " + username
            activitylog(request.user, B2BUser, "updated", b2b_user_obj.username, prev_b2b_user_obj, b2b_user_obj, b2b_location_group_obj, render_value)
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateB2BCustomerStatusAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

#API with active log
class DeleteB2BDocumentImageAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response["status"] = 500

        try:
            data = request.data
            logger.info("DeleteB2BDocumentImageAPI: %s", str(data))

            pk = data["pk"]
            image_obj = Image.objects.get(pk = pk)
            image_url = image_obj.image.url
            image_obj.delete()
            
            b2b_location_group_obj = None
            if LocationGroup.objects.filter(is_b2b=True).exists():
                b2b_location_group_obj = LocationGroup.objects.filter(is_b2b=True)[0]
            render_value = "B2B document image " + image_url + " deleted"
            activitylog(request.user, Image, "deleted", pk, image_obj, None, b2b_location_group_obj, render_value)
            response["status"] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteB2BDocumentImageAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

#API with active log
class DeleteB2BDocumentAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response["status"] = 500

        try:
            data = request.data
            logger.info("DeleteB2BDocumentAPI: %s", str(data))

            document_type = data["documentType"]
            contact_number = data.get("contactNumber","")
            is_dealshub = data.get("isDealshub",True)
            location_group_uuid = data.get("locationGroupUuid","")

            if is_dealshub == True:
                b2b_user_obj = B2BUser.objects.get(username = request.user.username)
            else:
                location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
                website_group_name = location_group_obj.website_group.name.lower()
                b2b_user_obj = B2BUser.objects.get(username = contact_number + "-" + website_group_name)
                prev_b2b_user_obj = deepcopy(b2b_user_obj)
            if document_type=="VAT":
                b2b_user_obj.vat_certificate = None
            elif document_type=="PASSPORT":
                b2b_user_obj.passport_copy = None
            elif document_type=="TRADE":
                b2b_user_obj.trade_license = None
            b2b_user_obj.save()

            if is_dealshub == False:
                render_value =  "B2B documents deleted for user" + b2b_user_obj.username
                activitylog(request.user, B2BUser, "updated", b2b_user_obj.username, prev_b2b_user_obj, b2b_user_obj, location_group_obj, render_value)
            response["status"] = 200


            try:
                calling_facebook_api(event_name="CompleteRegistration",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("DeleteB2BDocumentAPI: %s at %s", e, str(exc_tb.tb_lineno))
                
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteB2BDocumentAPI: %s at %s", e, str(exc_tb.tb_lineno))

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
            custom_data = []
            for order_obj in order_objs:
                total_billing = 0
                temp_dict = {}
                temp_dict["datePlaced"] = order_obj.get_date_created()
                temp_dict["timePlaced"] = order_obj.get_time_created()
                temp_dict["bundleId"] = str(order_obj.bundleid)
                temp_dict["paymentMode"] = order_obj.payment_mode
                temp_dict["uuid"] = order_obj.uuid
                temp_dict["shippingMethod"] = "pending" if UnitOrder.objects.filter(order=order_obj).first() == None else UnitOrder.objects.filter(order=order_obj).first().shipping_method
                temp_dict["call_status"] = order_obj.call_status
                temp_dict["sapStatus"] = order_obj.sap_status
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
                    temp_dict2["shippingMethod"] = unit_order_obj.shipping_method
                    temp_dict2["sapStatus"] = unit_order_obj.sap_status
                    unit_order_list.append(temp_dict2)
                    try:
                        custom_data.append(CustomData(
                            content_type="product",
                            value=unit_order_obj.product.now_price,
                            currency=unit_order_obj.product.get_currency(),
                            content_name=unit_order_obj.product.get_name(),
                            content_category=unit_order_obj.product.get_category(),
                            contents=[Content(product_id=unit_order_obj.product.get_product_id(), quantity=unit_order_obj.product.stock, item_price=unit_order_obj.product.now_price)],
                        ))
                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        logger.error("FetchCustomerOrdersAPI: %s at %s", e, str(exc_tb.tb_lineno))
                temp_dict["totalBilling"] = str(order_obj.to_pay) + " " + str(order_obj.location_group.location.currency)
                temp_dict["unitOrderList"] = unit_order_list
                order_list.append(temp_dict)

            is_available = True
            if int(paginator.num_pages) == int(page):
                is_available = False

            response["is_available"] = is_available
            response["total_orders"] = total_orders
            response["customerName"] = dealshub_user_obj.first_name

            response["orderList"] = order_list
            response['status'] = 200

            try:
                dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
                calling_facebook_api(event_name="ViewContent",user=dealshub_user_obj,request=request,custom_data=custom_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("FetchCustomerOrdersAPI: %s at %s", e, str(exc_tb.tb_lineno))
                
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCustomerOrdersAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchCustomerOrderRequestsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchCustomerOrderRequestsAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            username = data["username"]
            page = data.get("page", 1)

            dealshub_user_obj = DealsHubUser.objects.get(username=username)

            order_request_objs = OrderRequest.objects.filter(owner=dealshub_user_obj).order_by('-pk')
            
            total_order_request = order_request_objs.count()
            paginator = Paginator(order_request_objs, 10)
            order_request_objs = paginator.page(page)

            order_request_list = []
            for order_request_obj in order_request_objs:
                try:
                    temp_dict = {}
                    temp_dict["uuid"] = order_request_obj.uuid
                    temp_dict["datePlaced"] = order_request_obj.get_date_created()
                    temp_dict["timePlaced"] = order_request_obj.get_time_created()
                    temp_dict["bundleId"] = str(order_request_obj.bundleid)
                    temp_dict["paymentMode"] = order_request_obj.payment_mode
                    temp_dict["requestStatus"] = order_request_obj.request_status
                    temp_dict["merchantReference"] = order_request_obj.merchant_reference
                    temp_dict["isPlaced"] = order_request_obj.is_placed
                    temp_dict["toPay"] = order_request_obj.to_pay
                    temp_dict["totalQuantity"] = order_request_obj.get_total_quantity()
                    try:
                        b2b_user_obj = B2BUser.objects.get(username=order_request_obj.owner.username)
                        temp_dict["companyName"] = b2b_user_obj.company_name
                    except Exception as e:
                        temp_dict["companyName"] = "NA"

                    unit_order_request_list = []
                    for unit_order_request_obj in UnitOrderRequest.objects.filter(order_request=order_request_obj):
                        temp_dict2 = {}
                        temp_dict2["orderRequestId"] = unit_order_request_obj.order_req_id
                        temp_dict2["uuid"] = unit_order_request_obj.uuid
                        temp_dict2["initialQuantity"] = unit_order_request_obj.initial_quantity
                        temp_dict2["initialPrice"] = unit_order_request_obj.initial_price
                        temp_dict2["finalQuantity"] = unit_order_request_obj.final_quantity
                        temp_dict2["finalPrice"] = unit_order_request_obj.final_price
                        temp_dict2["currency"] = unit_order_request_obj.product.get_currency()
                        temp_dict2["productName"] = unit_order_request_obj.product.get_name()
                        temp_dict2["productImageUrl"] = unit_order_request_obj.product.get_main_image_url()
                        unit_order_request_list.append(temp_dict2)
                    temp_dict["totalBilling"] = str(order_request_obj.to_pay) + " " + str(order_request_obj.location_group.location.currency)
                    temp_dict["unitOrderRequestList"] = unit_order_request_list
                    order_request_list.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchCustomerOrderRequestsAPI: %s at %s", e, str(exc_tb.tb_lineno))
            
            is_available = True
            if int(paginator.num_pages) == int(page):
                is_available = False

            response["is_available"] = is_available
            response["totalOrderRequests"] = total_order_request
            response["customerName"] = dealshub_user_obj.first_name
            response["orderList"] = order_request_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCustomerOrderRequestsAPI: %s at %s", e, str(exc_tb.tb_lineno))

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

            if location_group_obj.is_b2b == True:
                order_request_obj = OrderRequest.objects.get(uuid=data.get("OrderRequestUuid",""))
                order_request_obj.merchant_reference = merchant_reference
                order_request_obj.save()
            else:
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

            r = requests.post(url="https://sbpaymentservices.payfort.com/FortAPI/paymentApi", json=request_data, timeout=10)
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
                            address_obj = Address.objects.filter(user=cart_obj.owner, is_shipping=True)[0]
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
                                                     billing_address=cart_obj.billing_address,
                                                     to_pay=cart_obj.to_pay,
                                                     real_to_pay=cart_obj.to_pay,
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

                    try:
                        unit_cart_objs = UnitCart.objects.filter(cart=cart_obj)
                        custom_data = []
                        for unit_cart_obj in unit_cart_objs:
                            custom_data.append(CustomData(
                                content_type="product",
                                value=unit_cart_obj.product.now_price,
                                currency=unit_cart_obj.product.get_currency(),
                                content_name=unit_cart_obj.product.get_name(),
                                content_category=unit_cart_obj.product.get_category(),
                                contents=[Content(product_id=unit_cart_obj.product.get_product_id(), quantity=unit_cart_obj.quantity, item_price=unit_cart_obj.product.now_price)],
                            ))
                        calling_facebook_api(event_name="Purchase",user=dealshub_user_obj,request=request,custom_data=custom_data)
                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        logger.error("PaymentTransactionAPI: %s at %s", e, str(exc_tb.tb_lineno))

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
                            address_obj = Address.objects.filter(user=fast_cart_obj.owner, is_shipping=True)[0]
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
                                                     billing_address=fast_cart_obj.billing_address,
                                                     to_pay=fast_cart_obj.to_pay,
                                                     real_to_pay=fast_cart_obj.to_pay,
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

                    try:
                        custom_data = []
                        custom_data.append(CustomData(
                            content_type="product",
                            value=fast_cart_obj.product.now_price,
                            currency=fast_cart_obj.product.get_currency(),
                            content_name=fast_cart_obj.product.get_name(),
                            content_category=fast_cart_obj.product.get_category(),
                            contents=[Content(product_id=fast_cart_obj.product.get_product_id(), quantity=fast_cart_obj.quantity, item_price=fast_cart_obj.product.now_price)],
                        ))
                        calling_facebook_api(event_name="Purchase",user=fast_cart_obj.owner,request=request,custom_data=custom_data)
                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        logger.error("PaymentTransactionAPI: %s at %s", e, str(exc_tb.tb_lineno))
         
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

            try:
                dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
                calling_facebook_api(event_name="Contact",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("ContactUsSendEmailAPI: %s at %s", e, str(exc_tb.tb_lineno))
                
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ContactUsSendEmailAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchAccountStatusB2BUserAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] =500

        try:
            data = request.data
            logger.info("FetchAccountStatusB2BUserAPI: %s", str(data))

            b2b_user_obj = None
            is_verified = False
            b2b_user_obj = B2BUser.objects.get(username = request.user.username)
            if check_account_status(b2b_user_obj) == True:
                is_verified = True

                conf = json.loads(b2b_user_obj.conf)
                is_verified_shown = conf["isVerifiedShown"]
                response["IsVerifiedShown"] = is_verified_shown

                if is_verified_shown == False:
                    conf["isVerifiedShown"] = True
                    b2b_user_obj.conf = json.dumps(conf)
                    b2b_user_obj.save()
                response["status"] = 200
            
            response["IsVerified"] = is_verified
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchAccountStatusB2BUserAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SendB2BOTPSMSLoginAPI(APIView):
    permission_classes = [AllowAny,]

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500

        try:
            data = request.data
            logger.info("SendB2BOTPSMSLoginAPI: %s", str(data))
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

            if contact_number in ["888888888","777777777","777777788","777777789","777777799", "940804016", "888888881", "702290032", "888888883", "888888884"]:
                OTP = "777777"

            otp_sent = False
            username = contact_number + "-" + website_group_name
            b2b_user_obj = None
            if B2BUser.objects.filter(username = username).exists() == True:
                b2b_user_obj = B2BUser.objects.get(username=username)

            if b2b_user_obj != None and b2b_user_obj.contact_verified == True and b2b_user_obj.is_signup_completed == True:
                b2b_user_obj = B2BUser.objects.get(username = contact_number + "-" + website_group_name)
                b2b_user_obj.set_password(OTP)
                b2b_user_obj.verification_code = OTP
                b2b_user_obj.save()

                #Trigger sms
                try:
                    prefix_code = sms_country_info["prefix_code"]
                    user = sms_country_info["user"]
                    pwd = sms_country_info["pwd"]
                    link = website_group_obj.link
                    message = "Dear Customer, "+ OTP +" is you???re "+ link +" Login OTP. OTP valid for 2 minutes. Do not share it with anyone."
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
                    r = requests.post(url=url, data=req_data, timeout=10)
                    otp_sent = True

                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("SendB2BOTPSMSLoginAPI: %s at %s", e, str(exc_tb.tb_lineno))  

            response["status"] = 200
            response["OTPSent"] = otp_sent

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SendB2BOTPSMSLoginAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SendB2BOTPSMSSignUpAPI(APIView):
    permission_classes = [AllowAny]

    def post(self,request,*args,**kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SendB2BOTPSMSSignUpAPI: %s",str(data))
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

            if contact_number in ["888888888","777777777","777777788","777777789","777777799", "940804016", "888888881", "702290032", "888888883", "888888884"]:
                OTP = "777777"

            is_new_user = False
            username = contact_number + "-" + website_group_name
            b2b_user_obj = None
            if B2BUser.objects.filter(username = username).exists() == True:
                b2b_user_obj = B2BUser.objects.get(username=username)

            if b2b_user_obj == None:
                b2b_user_obj = B2BUser.objects.create(
                    username = contact_number+"-"+website_group_name,
                    contact_number = contact_number,
                    website_group = website_group_obj,
                    verification_code = OTP
                )
                b2b_user_obj.set_password(OTP)
                b2b_user_obj.save()
                is_new_user =True
            elif b2b_user_obj.contact_verified == False or b2b_user_obj.is_signup_completed == False:
                b2b_user_obj = B2BUser.objects.get(username = contact_number+ "-"+ website_group_name)
                b2b_user_obj.verification_code = OTP
                b2b_user_obj.set_password(OTP)
                b2b_user_obj.save()
                is_new_user = True
            else:
                response['isNewUser'] = is_new_user
                response['status'] = 403
                return Response(data=response)

            #Trigger sms
            try:
                prefix_code = sms_country_info["prefix_code"]
                user = sms_country_info["user"]
                pwd = sms_country_info["pwd"]
                link = website_group_obj.link
                message = "Dear Customer, "+ OTP +" is you???re "+ link +" Login OTP. OTP valid for 2 minutes. Do not share it with anyone."
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
                r = requests.post(url=url, data=req_data, timeout=10)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SendB2BOTPSMSSignUpAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["isNewUser"] = is_new_user
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SendB2BOTPSMSSignUpAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SignUpCompletionAPI(APIView):

    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500

        try:
            data = request.data
            logger.info("SignUpCompletionAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            contact_number = data["contactNumber"]
            name = data["fullName"]
            company_name = data["companyName"]
            email = data["email"]
            otp = data["otp"]
            vat_certificate_id = data.get("vat-certificate-id","")
            passport_copy_id = data.get("passport-copy-id","")
            trade_license_id = data.get("trade-license-id","")
            vat_certificate_type = data.get("vatCertificateType", "")
            trade_license_type = data.get("tradeLicenseType", "")
            passport_copy_type = data.get("passportCopyType", "")

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group
            website_group_name = website_group_obj.name.lower()

            b2b_user_obj = B2BUser.objects.get(username = contact_number + "-" + website_group_name)

            if (b2b_user_obj.vat_certificate_id != vat_certificate_id and B2BUser.objects.filter(vat_certificate_id=vat_certificate_id).count()) or (b2b_user_obj.trade_license_id != trade_license_id and B2BUser.objects.filter(trade_license_id=trade_license_id).count()):
                response["status"] = 403
                response["message"] = "Vat Certificate number or Trade License number already exists!"
                logger.error("UploadB2BDocumentAPI: Vat Certificate number or Trade License number already exists!")
                return Response(data=response)
            try:
                dealshub_user_obj = DealsHubUser.objects.get(username=contact_number + "-" + website_group_name)
                if Cart.objects.filter(owner=dealshub_user_obj,location_group=location_group_obj).exists() == True:
                    response["message"] = "SignUp is already completed for this account"
                    return Response(data=response)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SignUpCompletionAPI: %s at %s", e, str(exc_tb.tb_lineno))

            if vat_certificate_type == "IMG":
                image_count = int(data.get("vatCertificateImageCount",0))
                for i in range(image_count):
                    image_obj = Image.objects.create(image = data["vat-certificate-image-" + str(i+1)])
                    b2b_user_obj.vat_certificate_images.add(image_obj)
            elif vat_certificate_type == "PDF":
                if data["vat-certificate-document"] != "":
                    b2b_user_obj.vat_certificate = data["vat-certificate-document"]

            if trade_license_type == "IMG":
                image_count = int(data.get("tradeLicenseImageCount",0))
                for i in range(image_count):
                    image_obj = Image.objects.create(image = data["trade-license-image-" + str(i+1)])
                    b2b_user_obj.trade_license_images.add(image_obj)
            elif trade_license_type == "PDF":
                if data["trade-license-document"] != "":
                    b2b_user_obj.trade_license = data["trade-license-document"]

            if passport_copy_type == "IMG":
                image_count = int(data.get("passportCopyImageCount",0))
                for i in range(image_count):
                    image_obj = Image.objects.create(image = data["passport-copy-image-" + str(i+1)])
                    b2b_user_obj.passport_copy_images.add(image_obj)
            elif passport_copy_type == "PDF":
                if data["passport-copy-document"] != "":
                    b2b_user_obj.passport_copy = data["passport-copy-document"]

            is_new_user_created =False
            if b2b_user_obj.verification_code==otp:  
                b2b_user_obj.contact_number = contact_number
                b2b_user_obj.first_name = name
                b2b_user_obj.email = email
                b2b_user_obj.email_verified = True
                b2b_user_obj.date_created = timezone.now()
                b2b_user_obj.company_name = company_name
                b2b_user_obj.vat_certificate_id = vat_certificate_id
                b2b_user_obj.trade_license_id = trade_license_id
                b2b_user_obj.passport_copy_id = passport_copy_id
                is_new_user_created = True

                dealshub_user_obj = DealsHubUser.objects.get(username = b2b_user_obj.username)
                for location_group_obj in LocationGroup.objects.filter(website_group=website_group_obj):
                    Cart.objects.create(owner=dealshub_user_obj, location_group=location_group_obj)
                    WishList.objects.create(owner=dealshub_user_obj, location_group=location_group_obj)
                    FastCart.objects.create(owner=dealshub_user_obj, location_group=location_group_obj)

                conf = json.loads(b2b_user_obj.conf)
                conf["isVerifiedShown"] =False
                b2b_user_obj.conf = json.dumps(conf)

                b2b_user_obj.is_signup_completed = True
                b2b_user_obj.save()

            credentials = {
                "username": contact_number+"-"+website_group_name,
                "password": otp
            }

            if is_new_user_created == True:            
                r = requests.post(url=SERVER_IP+"/token-auth/", data=credentials, verify=False, timeout=10)
                token = json.loads(r.content)["token"]
                response["token"] = token

            response["status"] = 200
            try:
                calling_facebook_api(event_name="CompleteRegistration",user=b2b_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SignUpCompletionAPI: %s at %s", e, str(exc_tb.tb_lineno))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SignUpCompletionAPI: %s at %s", e, str(exc_tb.tb_lineno))

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

            if contact_number in ["88888888", "888888888","777777777","777777788","777777789","777777799", "940804016", "888888881", "702290032"]:
                OTP = "777777"

            is_new_user = False
            if DealsHubUser.objects.filter(username=contact_number+"-"+website_group_name).exists()==False:
                dealshub_user_obj = DealsHubUser.objects.create(username=contact_number+"-"+website_group_name, contact_number=contact_number, website_group=website_group_obj)
                dealshub_user_obj.set_password(OTP)
                dealshub_user_obj.verification_code = OTP
                dealshub_user_obj.save()
                is_new_user = True

                for location_group_obj in LocationGroup.objects.filter(website_group=website_group_obj):
                    Cart.objects.create(owner=dealshub_user_obj, location_group=location_group_obj, offline_cod_charge=location_group_obj.cod_charge, offline_delivery_fee=location_group_obj.delivery_fee)
                    WishList.objects.create(owner=dealshub_user_obj, location_group=location_group_obj)
                    FastCart.objects.create(owner=dealshub_user_obj, location_group=location_group_obj)

            else:
                dealshub_user_obj = DealsHubUser.objects.get(username=contact_number+"-"+website_group_name)
                dealshub_user_obj.set_password(OTP)
                dealshub_user_obj.verification_code = OTP
                dealshub_user_obj.save()
            link = website_group_obj.link

            message = "Dear Customer, "+ OTP +" is you???re "+ link +" Login OTP. OTP valid for 2 minutes. Do not share it with anyone."

            # Trigger SMS
            try:
                if location_group_obj.website_group.name.lower() in ["shopnesto", "daycart", "shopnestokuwait"]:
                    prefix_code = sms_country_info["prefix_code"]
                    user = sms_country_info["user"]
                    pwd = sms_country_info["pwd"]
                    sender_id = sms_country_info["sender_id"]

                    contact_number = prefix_code+contact_number

                    url = "http://www.smscountry.com/smscwebservice_bulk.aspx"
                    req_data = {
                        "user" : user,
                        "passwd": pwd,
                        "message": message,
                        "mobilenumber": contact_number,
                        "mtype":"N",
                        "DR":"Y",
                        "sid": sender_id
                    }
                    r = requests.post(url=url, data=req_data, timeout=10)
                elif location_group_obj.website_group.name.lower()=="kryptonworld":
                    contact_number = "971"+contact_number
                    url ="https://api.antwerp.ae/Send?phonenumbers="+contact_number+"&sms.sender=Krypton&sms.text="+message+"&sms.typesms=sms&apiKey=RUVFRkZCNEUtRkI5MC00QkM5LUFBMEMtQzRBMUI1NDQxRkE5"
                    r = requests.get(url, timeout=10)

                elif location_group_obj.website_group.name.lower() == "geepasuganda":
                    africastalking.initialize(
                        username='geepasug',
                        api_key='e5d7fd9be205264e7dd649fa904dbe36952f8c64efa21bea53b7b537f23155b9'
                    )
                    sms = africastalking.SMS
                    sms_country_info = json.loads(location_group_obj.sms_country_info)
                    prefix_code = sms_country_info["prefix_code"]
                    sender = sms_country_info["sender_id"]
                    recipients = ["+" + prefix_code + contact_number]    #["+917043300725"]
                    try:
                        response = sms.send(message, recipients, sender)
                        print (response)
                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        logger.error("SendOTPSMSLoginAPI: %s at %s", e, str(exc_tb.tb_lineno))

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SendOTPSMSLoginAPI: %s at %s", e, str(exc_tb.tb_lineno))

            if website_group_name not in ["shopnesto"]:
                response["isNewUser"] = is_new_user
            response["status"] = 200
        
            try:
                calling_facebook_api(event_name="CompleteRegistration",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SendOTPSMSLoginAPI: %s at %s", e, str(exc_tb.tb_lineno))     

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
                    Cart.objects.create(owner=dealshub_user_obj, location_group=location_group_obj, offline_cod_charge=location_group_obj.cod_charge, offline_delivery_fee=location_group_obj.delivery_fee)
                    WishList.objects.create(owner=dealshub_user_obj, location_group=location_group_obj)
                    FastCart.objects.create(owner=dealshub_user_obj, location_group=location_group_obj)
            else:
                dealshub_user_obj = DealsHubUser.objects.get(username=contact_number+"-"+website_group_name)
            
            response["is_pin_set"] = dealshub_user_obj.is_pin_set
            response["is_new_user"] = is_new_user
            response["status"] = 200

            try:
                calling_facebook_api(event_name="CompleteRegistration",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("CheckUserPinSetAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
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
                    r = requests.post(url=SERVER_IP+"/token-auth/", data=credentials, verify=False, timeout=10)
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

            try:
                calling_facebook_api(event_name="CompleteRegistration",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SetLoginPinAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
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
                    r = requests.post(url=SERVER_IP+"/token-auth/", data=credentials, verify=False, timeout=10)
                    token = json.loads(r.content)["token"]
                    response["token"] = token
                    dealshub_user_obj.contact_verified = True
                    verified = True
                    dealshub_user_obj.save()

            response["verified"] = verified
            response["status"] = 200
            try:
                calling_facebook_api(event_name="CompleteRegistration",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SetLoginPinAPI: %s at %s", e, str(exc_tb.tb_lineno))
        

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
            link = website_group_obj.link
            message = "Dear Customer, "+pin+" is you???re "+ link +" Login PIN. Do not share it with anyone."

            dealshub_user_obj = DealsHubUser.objects.get(username=contact_number+"-"+website_group_name)
            dealshub_user_obj.set_password(pin)
            dealshub_user_obj.verification_code = pin
            dealshub_user_obj.save()

            # Trigger SMS
            if location_group_obj.website_group.name.lower() in ["shopnesto", "daycart", "shopnestokuwait"]:
                mshastra_info = json.loads(location_group_obj.mshastra_info)
                prefix_code = mshastra_info["prefix_code"]
                sender_id = mshastra_info["sender_id"]
                user = mshastra_info["user"]
                pwd = mshastra_info["pwd"]
                contact_number = prefix_code+contact_number
                url = "http://mshastra.com/sendurlcomma.aspx?user="+user+"&pwd="+pwd+"&senderid="+sender_id+"&mobileno="+contact_number+"&msgtext="+message+"&priority=High&CountryCode=ALL"
                r = requests.get(url, timeout=10)
            elif location_group_obj.website_group.name.lower()=="parajohn":
                contact_number = "971"+contact_number
                url = "https://retail.atech.alarislabs.com/rest/send_sms?from=PARA JOHN&to="+contact_number+"&message="+message+"&username=r8NyrDLI&password=GLeOC6HO"
                r = requests.get(url, timeout=10)
            elif location_group_obj.website_group.name.lower()=="kryptonworld":
                contact_number = "971"+contact_number
                url ="https://api.antwerp.ae/Send?phonenumbers="+contact_number+"&sms.sender=Krypton&sms.text="+message+"&sms.typesms=sms&apiKey=RUVFRkZCNEUtRkI5MC00QkM5LUFBMEMtQzRBMUI1NDQxRkE5"
                r = requests.get(url, timeout=10)

            response["status"] = 200
            try:
                calling_facebook_api(event_name="CompleteRegistration",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("ForgotLoginPinAPI: %s at %s", e, str(exc_tb.tb_lineno))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ForgotLoginPinAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class VerifyB2BOTPSMSAPI(APIView):

    permission_classes = [AllowAny]

    def post(self,request,*args,**kwargs):
        response = {}
        response['status'] = 500

        try:
            data = request.data
            logger.info("VerifyB2BOTPSMSAPI: %s",str(data))
            if not isinstance(data,dict):
                data = json.loads(data)

            contact_number = data['contactNumber']
            otp = data["otp"]
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group
            website_group_name = website_group_obj.name.lower()

            b2b_user_obj = B2BUser.objects.get(username = contact_number+"-"+website_group_name)

            credentials = {
                "username":contact_number+"-"+website_group_name,
                "password":otp
            }

            is_verified = False
            if b2b_user_obj.verification_code==otp:
                r = requests.post(url = SERVER_IP+"/token-auth/",data=credentials,verify=False, timeout=10)
                token = json.loads(r.content)["token"]
                if b2b_user_obj.contact_verified == True:
                    response["token"] = token
                else:
                    b2b_user_obj.contact_verified = True
                is_verified = True
                b2b_user_obj.save()

            response["verified"]=is_verified
            response["status"]=200
            try:
                calling_facebook_api(event_name="CompleteRegistration",user=b2b_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("VerifyB2BOTPSMSAPI: %s at %s", e, str(exc_tb.tb_lineno))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("VerifyB2BOTPSMSAPI: %s at %s", e, str(exc_tb.tb_lineno))

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

            sms_country_info = json.loads(location_group_obj.sms_country_info)

            dealshub_user_obj = DealsHubUser.objects.get(username=contact_number+"-"+website_group_name)
            
            credentials = {
                "username": contact_number+"-"+website_group_name,
                "password": otp
            }

            verified = False
            if dealshub_user_obj.verification_code==otp:
                r = requests.post(url=SERVER_IP+"/token-auth/", data=credentials, verify=False, timeout=10)
                token = json.loads(r.content)["token"]
                response["token"] = token
                response["message"] = "Login Successful!"
                verified = True
                dealshub_user_obj.contact_verified = True
                dealshub_user_obj.otp_attempts = 0
                dealshub_user_obj.save()
            else:
                otp_attempts = dealshub_user_obj.otp_attempts
                otp_attempts += 1
                response["message"] = "Invalid OTP!"
                if otp_attempts >= 5:
                    response["message"] = "Too many attempts! New OTP Sent"
                    otp_attempts = otp_attempts%5

                    digits = "0123456789"
                    OTP = ""
                    for i in range(6):
                        OTP += digits[int(math.floor(random.random()*10))]

                    if contact_number in ["88888888", "888888888","777777777","777777788","777777789","777777799","888888884", "940804016", "888888881", "702290032"]:
                        OTP = "777777"

                    dealshub_user_obj.set_password(OTP)
                    dealshub_user_obj.verification_code = OTP
                    dealshub_user_obj.save()
                    link = website_group_obj.link
                    message = "Welcome to "+ link +"! We are happy to serve you better. "+ OTP +" is your "+ link +" Login OTP. OTP valid for 2 minutes. Do not share it with anyone."

                    # Trigger SMS
                    try:
                        if location_group_obj.website_group.name.lower() in ["shopnesto", "daycart", "shopnestokuwait"]:
                            prefix_code = sms_country_info["prefix_code"]
                            user = sms_country_info["user"]
                            pwd = sms_country_info["pwd"]
                            sender_id = sms_country_info["sender_id"]

                            contact_number = prefix_code+contact_number

                            url = "http://www.smscountry.com/smscwebservice_bulk.aspx"
                            req_data = {
                                "user" : user,
                                "passwd": pwd,
                                "message": message,
                                "mobilenumber": contact_number,
                                "mtype":"N",
                                "DR":"Y",
                                "sid": sender_id
                            }
                            r = requests.post(url=url, data=req_data, timeout=10)
                        
                        elif location_group_obj.website_group.name.lower()=="kryptonworld":
                            contact_number = "971"+contact_number
                            url ="https://api.antwerp.ae/Send?phonenumbers="+contact_number+"&sms.sender=Krypton&sms.text="+message+"&sms.typesms=sms&apiKey=RUVFRkZCNEUtRkI5MC00QkM5LUFBMEMtQzRBMUI1NDQxRkE5"
                            r = requests.get(url, timeout=10)

                        elif location_group_obj.website_group.name.lower() == "geepasuganda":
                            africastalking.initialize(
                                username='geepasug',
                                api_key='e5d7fd9be205264e7dd649fa904dbe36952f8c64efa21bea53b7b537f23155b9'
                            )
                            sms = africastalking.SMS
                            sms_country_info = json.loads(location_group_obj.sms_country_info)
                            prefix_code = sms_country_info["prefix_code"]
                            sender = sms_country_info["sender_id"]
                            recipients = ["+" + prefix_code + contact_number]    #["+917043300725"]

                            try:
                                response = sms.send(message, recipients, sender)
                                print (response)
                            except Exception as e:
                                exc_type, exc_obj, exc_tb = sys.exc_info()
                                logger.error("VerifyOTPSMSLogin: %s at %s", e, str(exc_tb.tb_lineno))

                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        logger.error("VerifyOTPSMSLogin: %s at %s", e, str(exc_tb.tb_lineno))

                dealshub_user_obj.otp_attempts = otp_attempts
                dealshub_user_obj.save()

            response["verified"] = verified
            response["status"] = 200

            try:
                calling_facebook_api(event_name="CompleteRegistration",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("VerifyOTPSMSLoginAPI: %s at %s", e, str(exc_tb.tb_lineno))

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

            try:
                calling_facebook_api(event_name="CompleteRegistration",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("UpdateUserEmailAPI: %s at %s", e, str(exc_tb.tb_lineno))

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
            
            try:
                calling_facebook_api(event_name="ViewContent",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("AddReviewAPI: %s at %s", e, str(exc_tb.tb_lineno))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddReviewAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddFakeReviewAdminAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("AddFakeReviewAdminAPI: %s", str(data))
            
            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("AddFakeReviewAdminAPI Restricted Access!")
                return Response(data=response)

            product_code = str(data["product_code"])
            fake_customer_name = data["customerName"]
            rating = int(data["rating"])
            review_content = json.loads(data["review_content"])

            subject = str(review_content["subject"])
            content = str(review_content["content"])
            
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=product_code)

            review_content_obj = ReviewContent.objects.create(subject=subject, content=content)
            image_count = int(data.get("image_count", 0))
            for i in range(image_count):
                image_obj = Image.objects.create(image=data["image_"+str(i)])
                review_content_obj.images.add(image_obj)
            
            omnycomm_user_obj = OmnyCommUser.objects.get(username=request.user.username)

            review_obj = Review.objects.create(is_fake=True,
                                               product=dealshub_product_obj,
                                               rating=rating,
                                               content=review_content_obj,
                                               fake_customer_name=fake_customer_name,
                                               fake_oc_user=omnycomm_user_obj)
            
            response["uuid"] = review_obj.uuid
            response["review_content_uuid"] = review_content_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddFakeReviewAdminAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class BulkUploadFakeReviewAdminAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            
            data = request.data
            logger.info("BulkUploadFakeReviewAdminAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("BulkUploadFakeReviewAdminAPI Restricted Access!")
                return Response(data=response)

            location_group_uuid_list = data["locationGroupUuidList"]

            path = default_storage.save('tmp/bulk-upload-review.xlsx', data["import_file"])
            path = "http://cdn.omnycomm.com.s3.amazonaws.com/"+path

            if OCReport.objects.filter(is_processed=False).count()>6:
                response["approved"] = False
                response['status'] = 200
                return Response(data=response)

            report_type = "bulk upload product"
            report_title = "bulk upload fake review"
            filename = "files/reports/"+str(datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S_"))+report_type+".xlsx"
            oc_user_obj = OmnyCommUser.objects.get(username=request.user.username)
            note = "report for the bulk upload of the fake review" 
            custom_permission_obj = CustomPermission.objects.get(user=request.user)
            organization_obj = custom_permission_obj.organization


            for location_group_uuid in json.loads(location_group_uuid_list):
                try:
                    location_group_obj = LocationGroup.objects.filter(uuid=location_group_uuid).first()
                    oc_report_obj = OCReport.objects.create(name=report_type, report_title=report_title, created_by=oc_user_obj, note=note, filename=filename, location_group=location_group_obj, organization=organization_obj)
                    p1 =  threading.Thread(target=bulk_upload_fake_review , args=(oc_report_obj.uuid, path, filename, location_group_obj, oc_user_obj))
                    p1.start()
                    render_value = 'Bulk update fake reviews with report {} is created'.format(oc_report_obj.name)
                    activitylog(user=request.user,table_name=OCReport,action_type='created',location_group_obj=location_group_obj,prev_instance=None,current_instance=oc_report_obj,table_item_pk=oc_report_obj.uuid,render=render_value)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("BulkUploadFakeReviewAdminAPI: %s at %s", e, str(exc_tb.tb_lineno))
            
            response['status'] = 200
            response['approved'] = True
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("BulkUploadFakeReviewAdminAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


#API with active log
class UpdateReviewAdminAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:
            data = request.data
            logger.info("UpdateReviewAdminAPI: %s",str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UpdateReviewAdminAPI Restricted Access!")
                return Response(data=response)

            review_uuid = str(data["review_uuid"])
            fake_customer_name = data.get("customerName","")
            rating = int(data["rating"])
            review_content = json.loads(data["review_content"])
            created_date = str(data["created_at"])+"T00:00:00+04:00"
            modified_date = str(data["created_at"])+"T00:00:00+04:00"

            subject = str(review_content["subject"])
            content = str(review_content["content"])
            
            review_obj = Review.objects.get(uuid=review_uuid)
            prev_review_obj = deepcopy(review_obj)
            review_obj.rating = rating
            if review_obj.is_fake==True:
                review_obj.fake_customer_name = fake_customer_name
            
            review_content_obj = review_obj.content
            if review_content_obj is None:
                review_content_obj = ReviewContent.objects.create(subject=subject, content=content)
                prev_review_content_obj = None
            else:
                prev_review_content_obj = deepcopy(review_content_obj)
                review_content_obj.subject = subject
                review_content_obj.content = content
                review_content_obj.save()
            
            image_url_list = []
            image_count = int(data.get("image_count", 0))
            for i in range(image_count):
                image_obj = Image.objects.create(image=data["image_"+str(i)])
                review_content_obj.images.add(image_obj)
                temp_dict2 = {}
                temp_dict2["url"] = image_obj.image.url
                temp_dict2["uuid"] = image_obj.pk
                image_url_list.append(temp_dict2)
            review_content_obj.save()

            review_obj.content = review_content_obj
            review_obj.created_date = created_date
            review_obj.save()
            
            response['image_url_list'] = image_url_list
            response['review_uuid'] = review_obj.uuid
            response['review_content_uuid'] = review_content_obj.uuid

            render_value_1 = "Review of product " + review_obj.product.product_name + " updated"
            activitylog(request.user, Review, "updated", review_obj.uuid, prev_review_obj, review_obj, review_obj.product.location_group, render_value_1)
            render_value_2 = "Review Content of product " + review_obj.product.product_name + " updated"
            activitylog(request.user, ReviewContent, "updated", review_content_obj.uuid, prev_review_content_obj, review_content_obj, review_obj.product.location_group, render_value_2)

            response['status'] = 200
            
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateReviewAdminAPI: %s at %s", e, str(exc_tb.tb_lineno))

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

            try:
                calling_facebook_api(event_name="ViewContent",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("AddRatingAPI: %s at %s", e, str(exc_tb.tb_lineno))

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

            try:
                calling_facebook_api(event_name="ViewContent",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("UpdateRatingAPI: %s at %s", e, str(exc_tb.tb_lineno))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateRatingAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

#API with active log
class AddAdminCommentAPI(APIView):
    
    def post(self, request, *arg, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddAdminCommentAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("AddAdminCommentAPI Restricted Access!")
                return Response(data=response)

            uuid = str(data["uuid"])
            comment = str(data["comment"])

            review_obj = Review.objects.get(uuid=uuid)

            omnycomm_user_obj = OmnyCommUser.objects.get(username=request.user.username)

            if review_obj.content==None:
                response["status"] = 403
                return Response(data=response)

            if comment.strip()=="":
                review_content_obj = review_obj.content 
                prev_review_content_obj = deepcopy(review_content_obj)
                review_content_obj.admin_comment = None
                review_content_obj.save()
                render_value = "Admin comment for product " + review_obj.product.product_name +" deleted"
                activitylog(user=omnycomm_user_obj,table_name=ReviewContent,action_type='deleted',location_group_obj=review_obj.product.location_group, prev_instance=prev_review_content_obj,current_instance=review_content_obj,table_item_pk=review_content_obj.pk,render=render_value)
                response["status"] = 200
                return Response(data=response)
            
            admin_comment_obj = None
            if review_obj.content.admin_comment!=None:
                admin_comment_obj = review_obj.content.admin_comment
                prev_admin_comment_obj = deepcopy(admin_comment_obj)
                admin_comment_obj.comment = comment
                admin_comment_obj.user = omnycomm_user_obj
                admin_comment_obj.save()
                render_value = "Admin comment for product " + review_obj.product.product_name +" updated"
                activitylog(user=omnycomm_user_obj,table_name=AdminReviewComment,action_type='updated',location_group_obj=review_obj.product.location_group,prev_instance=prev_admin_comment_obj,current_instance=admin_comment_obj,table_item_pk=admin_comment_obj.pk,render=render_value)
            else:
                admin_comment_obj = AdminReviewComment.objects.create(user=omnycomm_user_obj, comment=comment)
                render_value = "Admin comment for product " + review_obj.product.product_name +" created"
                activitylog(user=omnycomm_user_obj,table_name=AdminReviewComment,action_type='created',location_group_obj=review_obj.product.location_group,prev_instance=None,current_instance=admin_comment_obj,table_item_pk=admin_comment_obj.pk,render=render_value)
                review_content_obj = review_obj.content
                review_content_obj.admin_comment = admin_comment_obj
                review_content_obj.save()    

            response["admin_comment_uuid"] = admin_comment_obj.uuid
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddAdminCommentAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

#API with active log
class UpdateAdminCommentAPI(APIView):
    
    def post(self, request, *arg, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateAdminCommentAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UpdateAdminCommentAPI Restricted Access!")
                return Response(data=response)

            uuid = str(data["admin_comment_uuid"])
            comment = str(data["comment"])

            admin_comment_obj = AdminReviewComment.objects.get(uuid=uuid)
            prev_admin_comment_obj = deepcopy(admin_comment_obj)
            admin_comment_obj.comment = comment
            admin_comment_obj.save()
            review_obj = Review.objects.get(content__admin_comment__uuid=uuid)
            render_value = "Admin review comment for product " + review_obj.product.product_name +" updated"
            activitylog(user=request.user,table_name=AdminReviewComment,action_type='updated',location_group_obj=review_obj.product.location_group,prev_instance=prev_admin_comment_obj,current_instance=admin_comment_obj,table_item_pk=admin_comment_obj.pk,render=render_value)
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

            try:
                calling_facebook_api(event_name="ViewContent",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("AddUpvoteAPI: %s at %s", e, str(exc_tb.tb_lineno))

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

            try:
                calling_facebook_api(event_name="ViewContent",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("DeleteUpvoteAPI: %s at %s", e, str(exc_tb.tb_lineno))

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
            response["username"] = str(review_obj.fake_customer_name if review_obj.is_fake==True else review_obj.dealshub_user.username)
            response["product_code"] = str(review_obj.product.uuid)
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

            response["is_published"] = review_obj.is_published
            response["review_content"] = review_content
            response["created_date"] = str(review_obj.created_date)
            response["modified_date"] = str(review_obj.modified_date)
            response["status"] = 200

            try:
                dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
                calling_facebook_api(event_name="ViewContent",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("FetchReviewAPI: %s at %s", e, str(exc_tb.tb_lineno))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchReviewAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchReviewsAdminAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchReviewsAdminAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchReviewsAdminAPI Restricted Access!")
                return Response(data=response)

            product_code = data.get("product_code","")
            from_date = data.get("from_date","")
            to_date = data.get("to_date","")
            category_uuid = data.get("category_uuid","")
            is_fake = data.get("is_fake", None)

            location_group_uuid = data["locationGroupUuid"]
            page = int(data.get("page",1))

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            review_objs = Review.objects.filter(product__location_group=location_group_obj).order_by('-modified_date')

            if product_code!="":
                dh_product_obj = DealsHubProduct.objects.get(uuid=product_code)
                review_objs = review_objs.filter(product=dh_product_obj)

            if from_date!="":
                from_date = from_date[:10]+"T00:00:00+04:00"
                review_objs = review_objs.filter(created_date__gte=from_date)

            if to_date!="":
                to_date = to_date[:10]+"T23:59:59+04:00"
                review_objs = review_objs.filter(created_date__lte=to_date)
            
            if category_uuid!="":
                category_obj = Category.objects.get(uuid=category_uuid)
                review_objs = review_objs.filter(product__category=category_obj)

            if is_fake!=None:
                review_objs = review_objs.filter(is_fake=is_fake)
            
            total_reviews = review_objs.count()

            paginator  = Paginator(review_objs,20)
            total_pages = int(paginator.num_pages)

            if page > total_pages:
                response['status'] = 404
                response['message'] = "Page number out of range"
                logger.warning("FetchReviewsAdminAPI : Page number out of range")
                return Response(data=response)

            review_objs = paginator.page(page)

            review_list = []
            for review_obj in review_objs:
                temp_dict= {}
                temp_dict["username"] = str(review_obj.fake_customer_name if review_obj.is_fake==True else review_obj.dealshub_user.username)
                temp_dict["display_name"] = str(review_obj.fake_customer_name if review_obj.is_fake==True else review_obj.dealshub_user.first_name)
                temp_dict["rating"] = str(review_obj.rating)
                temp_dict["is_fake"] = review_obj.is_fake
                temp_dict["is_published"] = review_obj.is_published
                if review_obj.is_fake and review_obj.fake_oc_user!=None:
                    temp_dict["fake_oc_user"] = review_obj.fake_oc_user.first_name

                review_content_obj = review_obj.content   

                admin_comment_obj = None
                if review_content_obj!=None:
                    admin_comment_obj = review_content_obj.admin_comment
                admin_comment = None
                if admin_comment_obj is not None:
                    admin_comment = {
                        "username" : str(admin_comment_obj.user.username),
                        "display_name" : str(admin_comment_obj.user.first_name+" "+admin_comment_obj.user.last_name),
                        "comment" : str(admin_comment_obj.comment),
                        "created_date" : str(timezone.localtime(admin_comment_obj.created_date).strftime("%d %b, %Y")),
                        "modified_date" : str(timezone.localtime(admin_comment_obj.modified_date).strftime("%d %b, %Y"))
                    }


                review_content = {
                    "subject" : "None",
                    "content" : "None",
                    "upvotes_count" : "0",
                    "admin_comment" : None,
                    "image_url_list": []
                }
                if review_content_obj is not None:
                    image_objs = review_content_obj.images.all()
                    image_url_list = []
                    for image_obj in image_objs:
                        try:
                            if image_obj.mid_image!=None:
                                temp_dict2 = {}
                                temp_dict2["url"] = image_obj.mid_image.url
                                temp_dict2["uuid"] = image_obj.pk
                                image_url_list.append(temp_dict2)
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
                product_details = {
                    "name" : review_obj.product.product_name,
                    "image_url" : review_obj.product.get_display_image_url(),
                    "seller_sku" : review_obj.product.get_seller_sku()
                }

                temp_dict["product_details"] =  product_details
                temp_dict["review_content"] = review_content
                temp_dict["created_date"] = str(timezone.localtime(review_obj.created_date).strftime("%d %b, %Y"))
                temp_dict["modified_date"] = str(timezone.localtime(review_obj.modified_date).strftime("%d %b, %Y"))
                temp_dict["review_uuid"] = str(review_obj.uuid)
                review_list.append(temp_dict)

            is_available = True
            if int(paginator.num_pages) == int(page):
                is_available = False

            response["is_available"] = is_available
            response["totalPages"] = paginator.num_pages
            response["total_reviews"] = total_reviews

            response["reviewList"] = review_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchReviewsAdminAPI: %s at %s", e, str(exc_tb.tb_lineno))

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
            review_objs = Review.objects.filter(product__uuid=product_code).exclude(is_published=False)
            total_reviews = review_objs.count()

            total_rating = 0
            for review_obj in review_objs:
                temp_dict = {}

                temp_dict["username"] = str(review_obj.fake_customer_name if review_obj.is_fake==True else review_obj.dealshub_user.username)
                temp_dict["display_name"] = str(review_obj.fake_customer_name if review_obj.is_fake==True else review_obj.dealshub_user.first_name)
                temp_dict["rating"] = str(review_obj.rating)
  
                total_rating += int(review_obj.rating)

                review_content_obj = review_obj.content

                admin_comment_obj = None
                if review_content_obj!=None:
                    admin_comment_obj = review_content_obj.admin_comment
                admin_comment = None
                if admin_comment_obj is not None:
                    admin_comment = {
                        "username" : str(admin_comment_obj.user.username),
                        "display_name" : str(admin_comment_obj.user.first_name+" "+admin_comment_obj.user.last_name),
                        "comment" : str(admin_comment_obj.comment),
                        "created_date" : str(timezone.localtime(admin_comment_obj.created_date).strftime("%d %b, %Y")),
                        "modified_date" : str(timezone.localtime(admin_comment_obj.modified_date).strftime("%d %b, %Y"))
                    }

                review_content = {
                    "subject" : "None",
                    "content" : "None",
                    "upvotes_count" : "0",
                    "admin_comment" : None,
                    "image_url_list": []
                }
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

                if Review.objects.filter(product__uuid=product_code, dealshub_user__username=request.user.username).exclude(is_published=False).exists():
                    is_user_reviewed = True
                    review_obj = Review.objects.get(product__uuid=product_code, dealshub_user__username=request.user.username)

                    review_content = {
                        "subject" : "None",
                        "content" : "None",
                        "upvotes_count" : "0",
                        "admin_comment" : None,
                        "image_url_list": []
                    }                    
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

            try:
                dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
                calling_facebook_api(event_name="ViewContent",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("FetchProductReviewsAPI: %s at %s", e, str(exc_tb.tb_lineno))

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

            try:
                dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
                calling_facebook_api(event_name="ViewContent",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("DeleteUserReviewImageAPI: %s at %s", e, str(exc_tb.tb_lineno))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteUserReviewImageAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

#API with active log
class DeleteAdminReviewImageAPI(APIView):

    def post(self, request, *arg, **kwargs):
        
        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DeleteAdminReviewImageAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("DeleteAdminReviewImageAPI Restricted Access!")
                return Response(data=response)
            
            image_uuid = int(data["image_uuid"])
            review_uuid = data["review_uuid"]

            review_obj = Review.objects.get(uuid=review_uuid)
            review_content_obj = review_obj.content
            prev_review_content_obj = deepcopy(review_content_obj)
            image_obj = Image.objects.get(pk=image_uuid)
            review_content_obj.images.remove(image_obj)
            review_content_obj.save()

            render_value = "Image "+ image_obj.image.url + "removed from review of product " + review_obj.product.product_name
            activitylog(user=request.user,table_name=ReviewContent,action_type='update',location_group_obj=review_obj.product.location_group,prev_instance=prev_review_content_obj,current_instance=review_content_obj,table_item_pk=review_content_obj.pk,render=render_value)
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteAdminReviewImageAPI: %s at %s", e, str(exc_tb.tb_lineno))

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
                review_obj.is_deleted = True
                review_obj.save()
                
            response["status"] = 200

            try:
                dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
                calling_facebook_api(event_name="ViewContent",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("DeleteUserReviewAPI: %s at %s", e, str(exc_tb.tb_lineno))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteUserReviewAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

#API with active log
class HideReviewAdminAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("HideReviewAdminAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("HideReviewAdminAPI Restricted Access!")
                return Response(data=response)

            review_uuid = data["review_uuid"]

            review_obj = Review.objects.get(uuid=review_uuid)
            prev_review_obj = deepcopy(review_obj)
            review_obj.is_deleted = True
            review_obj.save()

            render_value = "Review of product " + review_obj.product.product_name + "by user " + (review_obj.dealshub_user.username if review_obj.dealshub_user!=None else "") + " deleted"
            activitylog(user=request.user,table_name=Review,action_type='deleted',location_group_obj=review_obj.product.location_group,prev_instance=prev_review_obj,current_instance=review_obj,table_item_pk=review_obj.uuid,render=render_value)
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("HideReviewAdminAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

#API with active log
class UpdateReviewPublishStatusAPI(APIView):

    def post(self, request, *args, **kwargs):
    
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateReviewPublishStatusAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UpdateReviewPublishStatusAPI Restricted Access!")
                return Response(data=response)

            review_uuid = data["review_uuid"]
            is_published = data["is_published"]

            review_obj = Review.objects.get(uuid=review_uuid)
            prev_review_obj = deepcopy(review_obj)
            review_obj.is_published = is_published
            review_obj.save()
            render_value = "Review of product " + review_obj.product.product_name + "by user " + (review_obj.dealshub_user.username if review_obj.dealshub_user!=None else "") + " is " + ("published" if is_published==True else "unpublished")  
            activitylog(user=request.user,table_name=Review,action_type='update',location_group_obj=review_obj.product.location_group,prev_instance=prev_review_obj,current_instance=review_obj,table_item_pk=review_obj.uuid,render=render_value)
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateReviewPublishStatusAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchSalesExecutiveAnalysisAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchSalesExecutiveAnalysisAPI: %s", str(data))

            if not isinstance(data,dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchSalesExecutiveAnalysisAPI Restricted Access!")
                return Response(data=response)
            
            custom_permission_obj = CustomPermission.objects.get(user__username=request.user.username)
            misc = json.loads(custom_permission_obj.misc)
            if "analytics" not in misc:
                logger.warning("User does not have permission to view analytics!")
                response["status"] = 403
                return Response(data=response)

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            order_objs = Order.objects.filter(location_group=location_group_obj)
            
            from_date = data.get("fromDate", "")
            to_date = data.get("toDate", "")

            today = str(datetime.date.today())[:10] + "T00:00:00+04:00"
            yesterday = str(datetime.date.today() - datetime.timedelta(days=1))[:10] + "T00:00:00+04:00"
            month = str(datetime.datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0))[:10] + "T00:00:00+04:00"
            prev_month_value = datetime.datetime.now().month-1
            prev_year_value = datetime.datetime.now().year

            if prev_month_value==0:
                prev_month_value = 12
                prev_year_value -= 1
            
            prev_month = str(datetime.datetime.now().replace(year=prev_year_value, month=prev_month_value, day=1, hour=0, minute=0, second=0, microsecond=0))[:10] + "T00:00:00+04:00"
            sales_target_objs = SalesTarget.objects.filter(location_group=location_group_obj)

            sales_target_list = []
            for sales_target_obj in sales_target_objs:
                user_order_objs = Order.objects.none()
                if sales_target_obj.user!=None:
                    user_order_objs = order_objs.filter(is_order_offline=True, offline_sales_person=sales_target_obj.user)

                today_order_objs = user_order_objs.filter(date_created__gt = today)
                today_total_sales = today_order_objs.aggregate(total_sales=Sum('real_to_pay'))["total_sales"]
                today_total_sales = 0 if today_total_sales==None else round(today_total_sales,2)
                
                # all orders except fully cancelled
                today_order_list = list(today_order_objs)
                today_total_orders = UnitOrder.objects.filter(order__in=today_order_list).exclude(current_status_admin="cancelled").values_list('order__uuid').distinct().count()
                today_avg_order_value = 0 if today_total_orders==0 else round(float(today_total_sales/today_total_orders),2)
                
                status_list = ["delivered","pending","dispatched","returned","cancelled"]
                total_orders_status_count_list = []
                total_orders_status_amount_list = []
                for status in status_list:
                    today_status_objs = today_order_objs.filter(unitorder__current_status_admin = status).distinct()
                    total_orders_status_count_list.append(today_status_objs.count())
                    if today_status_objs.count() == 0:
                        total_orders_status_amount_list.append(0)
                        continue
                    total_amount = 0.0
                    for today_status_obj in today_status_objs:
                        total_amount+= today_status_obj.get_total_amount()
                    total_orders_status_amount_list.append(round(float(total_amount), 2))

                month_order_objs = user_order_objs.filter(date_created__gt = month)

                month_total_sales = month_order_objs.aggregate(total_sales=Sum('real_to_pay'))["total_sales"]
                month_total_sales = 0 if month_total_sales==None else round(month_total_sales,2)

                month_order_list = list(month_order_objs)
                month_total_orders = UnitOrder.objects.filter(order__in=month_order_list).exclude(current_status_admin="cancelled").values_list('order__uuid').distinct().count()

                month_avg_order_value = 0 if month_total_orders==0 else round(float(month_total_sales/month_total_orders),2)
                
                total_monthly_orders_status_count_list = []
                total_monthly_orders_status_amount_list = []
                for status in status_list:
                    month_status_objs = month_order_objs.filter(unitorder__current_status_admin = status).distinct()
                    total_monthly_orders_status_count_list.append(month_status_objs.count())
                    if month_status_objs.count() == 0:
                        total_monthly_orders_status_amount_list.append(0)
                        continue
                    total_amount = 0.0
                    for month_status_obj in month_status_objs:
                        total_amount+=month_status_obj.get_total_amount()
                    total_monthly_orders_status_amount_list.append(round(float(total_amount), 2))    
                
                days_in_month = float(datetime.datetime.now().day)

                custom_range_order_objs = user_order_objs
                if from_date!="":
                    from_date = from_date[:10]+"T00:00:00+04:00"
                    custom_range_order_objs = user_order_objs.filter(date_created__gte = from_date)

                if to_date!="":
                    to_date = to_date[:10]+"T23:59:59+04:00"
                    custom_range_order_objs = custom_range_order_objs.filter(date_created__lte = to_date)
  
                user_total_sales = custom_range_order_objs.aggregate(total_sales=Sum('real_to_pay'))["total_sales"]
                user_total_sales = 0 if user_total_sales==None else round(user_total_sales,2)

                user_order_list = list(custom_range_order_objs)
                user_total_orders = UnitOrder.objects.filter(order__in=user_order_list).exclude(current_status_admin="cancelled").values_list('order__uuid').distinct().count()

                user_avg_order_value = 0 if user_total_orders==0 else round(float(user_total_sales/user_total_orders),2)
                
                total_user_orders_status_count_list = []
                total_user_orders_status_amount_list = []
                for status in status_list:
                    user_status_objs = custom_range_order_objs.filter(unitorder__current_status_admin = status).distinct()
                    total_user_orders_status_count_list.append(user_status_objs.count())
                    if user_status_objs.count() == 0:
                        total_user_orders_status_amount_list.append(0)
                        continue
                    total_amount = 0.0
                    for user_status_obj in user_status_objs:
                        total_amount+=user_status_obj.get_total_amount()
                    total_user_orders_status_amount_list.append(round(float(total_amount), 2))    
                
                temp_dict = {}
                temp_dict["dateFilter"] = {
                    "sales" : user_total_sales,
                    "orders" : user_total_orders,
                    "avg_value" : user_avg_order_value,
                    "delivered": total_user_orders_status_count_list[0],
                    "user_done_delivery_amount" : total_user_orders_status_amount_list[0],
                    "pending" : total_user_orders_status_count_list[1],
                    "user_pending_amount" : total_user_orders_status_amount_list[1],
                    "dispatched": total_user_orders_status_count_list[2],
                    "user_dispatched_amount" : total_user_orders_status_amount_list[2],
                    "returned": total_user_orders_status_count_list[3],
                    "user_returned_amount" : total_user_orders_status_amount_list[3],
                    "cancelled": total_user_orders_status_count_list[4],
                    "user_cancelled_amount" : total_user_orders_status_amount_list[4],
                    "net_sales" : user_total_orders - total_user_orders_status_count_list[3],
                    "net_sales_amount" : round(float(user_total_sales - total_user_orders_status_amount_list[3]),2)
                }

                temp_dict["targets"] = {
                    "today_sales" : sales_target_obj.today_sales_target,
                    "today_orders" : sales_target_obj.today_orders_target,
                    "monthly_sales" : sales_target_obj.monthly_sales_target,
                    "monthly_orders" : sales_target_obj.monthly_orders_target
                }
                
                temp_dict["todays"] = {
                    "sales" : today_total_sales,
                    "orders" : today_total_orders,
                    "avg_value" : today_avg_order_value,
                    "delivered": total_orders_status_count_list[0],
                    "today_done_delivery_amount" : total_orders_status_amount_list[0],
                    "pending" : total_orders_status_count_list[1],
                    "today_pending_amount" : total_orders_status_amount_list[1],
                    "dispatched": total_orders_status_count_list[2],
                    "today_dispatched_amount" : total_orders_status_amount_list[2],
                    "returned": total_orders_status_count_list[3],
                    "today_returned_amount" : total_orders_status_amount_list[3],
                    "cancelled": total_orders_status_count_list[4],
                    "today_cancelled_amount" : total_orders_status_amount_list[4],
                    "net_sales" : today_total_orders - total_orders_status_count_list[3],
                    "net_sales_amount" : round(float(today_total_sales - total_orders_status_amount_list[3]),2)
                }

                temp_dict["monthly"] = {
                    "sales" : month_total_sales,
                    "orders" : month_total_orders,
                    "avg_value" : month_avg_order_value,
                    "delivered": total_monthly_orders_status_count_list[0],
                    "monthly_done_delivery_amount" : total_monthly_orders_status_amount_list[0],
                    "pending" : total_monthly_orders_status_count_list[1],
                    "monthly_pending_amount" : total_monthly_orders_status_amount_list[1],
                    "dispatched": total_monthly_orders_status_count_list[2],
                    "monthly_dispatched_amount" : total_monthly_orders_status_amount_list[2],
                    "returned": total_monthly_orders_status_count_list[3],
                    "monthly_returned_amount" : total_monthly_orders_status_amount_list[3],
                    "cancelled": total_monthly_orders_status_count_list[4],
                    "monthly_cancelled_amount" : total_monthly_orders_status_amount_list[4],
                    "net_sales" : month_total_orders - total_monthly_orders_status_count_list[3],
                    "net_sales_amount" : round(float(month_total_sales - total_monthly_orders_status_amount_list[3]),2)
                }

                temp_dict["currency"] = location_group_obj.location.currency
                temp_dict["username"] = sales_target_obj.user.username
                temp_dict["first_name"] = sales_target_obj.user.first_name
                sales_target_list.append(temp_dict)

                sales_target_list = sorted(sales_target_list, key = lambda i: i["todays"]["sales"], reverse=True)
                response["sales_target_list"] = sales_target_list
                response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSalesExecutiveAnalysisAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)

class FetchOrderSalesAnalyticsAPI(APIView):

    def post(self, request, *args, **kwargs):
    
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchOrderSalesAnalyticsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchOrderSalesAnalyticsAPI Restricted Access!")
                return Response(data=response)

            custom_permission_obj = CustomPermission.objects.get(user__username=request.user.username)
            misc = json.loads(custom_permission_obj.misc)
            if ("analytics" not in misc) and ("sales-analytics" not in misc):
                logger.warning("User does not have permission to view analytics!")
                response["status"] = 403
                return Response(data=response)

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            order_objs = Order.objects.filter(location_group=location_group_obj)

            if ("sales-analytics" in misc) and ("analytics" not in misc):
                oc_user_obj = OmnyCommUser.objects.get(username=request.user.username)
                order_objs = order_objs.filter(is_order_offline=True, offline_sales_person=oc_user_obj)

            # today's
            today = str(datetime.date.today())[:10] + "T00:00:00+04:00"
            yesterday = str(datetime.date.today() - datetime.timedelta(days=1))[:10] + "T00:00:00+04:00"

            today_order_objs = order_objs.filter(date_created__gt = today)
            
            today_total_sales = today_order_objs.aggregate(total_sales=Sum('real_to_pay'))["total_sales"]
            today_total_sales = 0 if today_total_sales==None else round(today_total_sales,2)
            
            # all orders except fully cancelled
            today_order_list = list(today_order_objs)
            today_total_orders = UnitOrder.objects.filter(order__in=today_order_list).exclude(current_status_admin="cancelled").values_list('order__uuid').distinct().count()

            today_avg_order_value = 0 if today_total_orders==0 else round(float(today_total_sales/today_total_orders),2)
            
            status_list = ["delivered","pending","dispatched","returned","cancelled"]
            total_orders_status_count_list = []
            total_orders_status_amount_list = []
            for status in status_list:
                today_status_objs = today_order_objs.filter(unitorder__current_status_admin = status).distinct()
                total_orders_status_count_list.append(today_status_objs.count())
                if today_status_objs.count() == 0:
                        total_orders_status_amount_list.append(0)
                        continue
                total_amount = 0.0
                for today_status_obj in today_status_objs:
                    total_amount+= today_status_obj.get_total_amount()
                total_orders_status_amount_list.append(round(float(total_amount), 2))
        
            # monthly
            month = str(datetime.datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0))[:10] + "T00:00:00+04:00"
            prev_month_value = datetime.datetime.now().month-1
            prev_year_value = datetime.datetime.now().year
            if prev_month_value==0:
                prev_month_value = 12
                prev_year_value -= 1
            prev_month = str(datetime.datetime.now().replace(year=prev_year_value, month=prev_month_value, day=1, hour=0, minute=0, second=0, microsecond=0))[:10] + "T00:00:00+04:00"

            month_order_objs = order_objs.filter(date_created__gt = month)
            prev_month_order_objs = order_objs.filter(date_created__gt = prev_month, date_created__lt = month)

            month_total_sales = month_order_objs.aggregate(total_sales=Sum('real_to_pay'))["total_sales"]
            month_total_sales = 0 if month_total_sales==None else round(month_total_sales,2)
            
            month_order_list = list(month_order_objs)
            month_total_orders = UnitOrder.objects.filter(order__in=month_order_list).exclude(current_status_admin="cancelled").values_list('order__uuid').distinct().count()
            
            month_avg_order_value = 0 if month_total_orders==0 else round(float(month_total_sales/month_total_orders),2)

            total_monthly_orders_status_count_list = []
            total_monthly_orders_status_amount_list = []
            for status in status_list:
                month_status_objs = month_order_objs.filter(unitorder__current_status_admin = status).distinct()
                total_monthly_orders_status_count_list.append(month_status_objs.count())
                if month_status_objs.count() == 0:
                        total_monthly_orders_status_amount_list.append(0)
                        continue
                total_amount = 0.0
                for month_status_obj in month_status_objs:
                    total_amount+=month_status_obj.get_total_amount()
                total_monthly_orders_status_amount_list.append(round(float(total_amount), 2))

            days_in_month = float(datetime.datetime.now().day)
            
            if ("sales-analytics" in misc) and ("analytics" not in misc):
                oc_user_obj = OmnyCommUser.objects.get(username=request.user.username)
                sales_target_objs = SalesTarget.objects.filter(user=oc_user_obj, location_group=location_group_obj)
                if sales_target_objs.exists():
                    response["targets"] = {
                        "today_sales" : sales_target_objs[0].today_sales_target,
                        "today_orders" : sales_target_objs[0].today_orders_target,
                        "monthly_sales" : sales_target_objs[0].monthly_sales_target,
                        "monthly_orders" : sales_target_objs[0].monthly_orders_target
                    }
                else:
                    response["targets"] = { "today_sales" : 0, "today_orders" : 0, "monthly_sales" : 0, "monthly_orders" : 0 }
            else:
                response["targets"] = {
                    "today_sales" : location_group_obj.today_sales_target,
                    "today_orders" : location_group_obj.today_orders_target,
                    "monthly_sales" : location_group_obj.monthly_sales_target,
                    "monthly_orders" : location_group_obj.monthly_orders_target
                }                                
            
            response["todays"] = {
                "sales" : today_total_sales,
                "orders" : today_total_orders,
                "avg_value" : today_avg_order_value,
                "delivered": total_orders_status_count_list[0],
                "today_done_delivery_amount" : total_orders_status_amount_list[0],
                "pending" : total_orders_status_count_list[1],
                "today_pending_amount" : total_orders_status_amount_list[1],
                "dispatched": total_orders_status_count_list[2],
                "today_dispatched_amount" : total_orders_status_amount_list[2],
                "returned": total_orders_status_count_list[3],
                "today_returned_amount" : total_orders_status_amount_list[3],
                "cancelled": total_orders_status_count_list[4],
                "today_cancelled_amount" : total_orders_status_amount_list[4],
                "net_sales" : today_total_orders - total_orders_status_count_list[3] - total_orders_status_count_list[4],
                "net_sales_amount" : round(float(today_total_sales - total_orders_status_amount_list[3] - total_orders_status_amount_list[4]),2)

            }
            response["monthly"] = {
                "sales" : month_total_sales,
                "orders" : month_total_orders,
                "avg_value" : month_avg_order_value,
                "delivered": total_monthly_orders_status_count_list[0],
                "monthly_done_delivery_amount" : total_monthly_orders_status_amount_list[0],
                "pending" : total_monthly_orders_status_count_list[1],
                "monthly_pending_amount" : total_monthly_orders_status_amount_list[1],
                "dispatched": total_monthly_orders_status_count_list[2],
                "monthly_dispatched_amount" : total_monthly_orders_status_amount_list[2],
                "returned": total_monthly_orders_status_count_list[3],
                "monthly_returned_amount" : total_monthly_orders_status_amount_list[3],
                "cancelled": total_monthly_orders_status_count_list[4],
                "monthly_cancelled_amount" : total_monthly_orders_status_amount_list[4],
                "net_sales" : month_total_orders - total_monthly_orders_status_count_list[3] - total_monthly_orders_status_count_list[4],
                "net_sales_amount" : round(float(month_total_sales - total_monthly_orders_status_amount_list[3] - total_monthly_orders_status_amount_list[4]),2)
 
            }
            response["currency"] = location_group_obj.location.currency
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOrderSalesAnalyticsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchFilteredOrderAnalyticsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchFilteredOrderAnalyticsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchFilteredOrderAnalyticsAPI Restricted Access!")
                return Response(data=response)

            from_date = data.get("fromDate", "")
            to_date = data.get("toDate", "")
            payment_type_list = data.get("paymentTypeList", [])
            min_qty = data.get("minQty", "")
            max_qty = data.get("maxQty", "")
            min_price = data.get("minPrice", "")
            max_price = data.get("maxPrice", "")
            cancellation_requested = data.get("cancellation_requested",False)
            sales_person = data.get("salesPerson","")
            currency_list = data.get("currencyList", [])
            shipping_method_list = data.get("shippingMethodList", [])
            tracking_status_list = data.get("trackingStatusList", [])
            is_order_offline = data.get("isOrderOffline", None)
            sap_status_list = data.get("sapStatusList", [])
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

            if len(sap_status_list)>0:
                unit_order_objs = unit_order_objs.filter(sap_status__in=sap_status_list)

            if is_order_offline!=None:
                unit_order_objs = unit_order_objs.filter(order__is_order_offline=is_order_offline)                

            if max_qty!="":
                unit_order_objs = unit_order_objs.filter(quantity__lte=int(max_qty))

            if min_qty!="":
                unit_order_objs = unit_order_objs.filter(quantity__gte=int(min_qty))

            if max_price!="":
                unit_order_objs = unit_order_objs.filter(price__lte=int(max_price))

            if min_price!="":
                unit_order_objs = unit_order_objs.filter(price__gte=int(min_price))
            
            if cancellation_requested:
                unit_order_objs = unit_order_objs.filter(cancelled_by_user=True)

            if sales_person!="":
                unit_order_objs = unit_order_objs.filter(order__offline_sales_person__username=sales_person)

            if len(search_list)>0:
                temp_unit_order_objs = UnitOrder.objects.none()
                for search_string in search_list:
                    search_string = search_string.strip()
                    temp_unit_order_objs |= unit_order_objs.filter(Q(product__product__base_product__seller_sku__icontains=search_string) | Q(order__bundleid__icontains=search_string) | Q(orderid__icontains=search_string) | Q(order__owner__first_name__icontains=search_string) | Q(order__shipping_address__contact_number__icontains=search_string) | Q(order__merchant_reference__icontains=search_string) | Q(order__sap_final_billing_info__icontains=search_string) | Q(sap_intercompany_info__icontains=search_string))
                unit_order_objs = temp_unit_order_objs.distinct()

            order_objs = Order.objects.filter(location_group__uuid=location_group_uuid, unitorder__in=unit_order_objs).distinct().order_by("-order_placed_date")    
            total_sales = order_objs.aggregate(Sum('real_to_pay'))["real_to_pay__sum"]
            total_sales = 0 if total_sales==None else round(total_sales, 2)
            order_list =  list(order_objs)
            # exclusive of cancelled orders
            real_total_orders = UnitOrder.objects.filter(order__in=order_list).exclude(current_status_admin="cancelled").values_list('order__uuid').distinct().count()
            avg_order_value = 0 if real_total_orders==0 else round(float(total_sales/real_total_orders),2)
            status_list = ["delivered","pending","dispatched","returned","cancelled"]

            total_filtered_orders_status_count_list = []
            total_filtered_orders_status_amount_list = []
            for status in status_list:
                filtered_status_objs = order_objs.filter(unitorder__current_status_admin = status).distinct()
                total_filtered_orders_status_count_list.append(filtered_status_objs.count())
                if filtered_status_objs.count() == 0:
                    total_filtered_orders_status_amount_list.append(0)
                    continue
                total_amount = 0.0
                for filtered_status_obj in filtered_status_objs:
                    total_amount+=filtered_status_obj.get_total_amount()
                total_filtered_orders_status_amount_list.append(round(float(total_amount), 2))

            response["order_analytics"] = {
                "sales" : total_sales,
                "orders" : real_total_orders,
                "avg_order_value" : avg_order_value,
                "delivered": total_filtered_orders_status_count_list[0],
                "filtered_done_delivery_amount" : total_filtered_orders_status_amount_list[0],
                "pending" : total_filtered_orders_status_count_list[1],
                "filtered_pending_amount" : total_filtered_orders_status_amount_list[1],
                "dispatched": total_filtered_orders_status_count_list[2],
                "filtered_dispatched_amount" : total_filtered_orders_status_amount_list[2],
                "returned": total_filtered_orders_status_count_list[3],
                "filtered_returned_amount" : total_filtered_orders_status_amount_list[3],
                "cancelled": total_filtered_orders_status_count_list[4],
                "filtered_cancelled_amount" : total_filtered_orders_status_amount_list[4],
                "net_sales" : real_total_orders - total_filtered_orders_status_count_list[3] - total_filtered_orders_status_count_list[4], 
                "net_sales_amount" : round(float(total_sales - total_filtered_orders_status_amount_list[3] - total_filtered_orders_status_amount_list[4]),2)
            }
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFilteredOrderAnalyticsAPI: %s at %s", e, str(exc_tb.tb_lineno))

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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchOrdersForWarehouseManagerAPI Restricted Access!")
                return Response(data=response)
 
            from_date = data.get("fromDate", "")
            to_date = data.get("toDate", "")
            payment_type_list = data.get("paymentTypeList", [])
            min_qty = data.get("minQty", "")
            max_qty = data.get("maxQty", "")
            min_price = data.get("minPrice", "")
            max_price = data.get("maxPrice", "")
            cancellation_requested = data.get("cancellation_requested",False)
            sales_person = data.get("salesPerson","")
            currency_list = data.get("currencyList", [])
            shipping_method_list = data.get("shippingMethodList", [])
            tracking_status_list = data.get("trackingStatusList", [])
            is_order_offline = data.get("isOrderOffline", None)
            sap_status_list = data.get("sapStatusList", [])
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

            if len(sap_status_list)>0:
                unit_order_objs = unit_order_objs.filter(sap_status__in=sap_status_list)

            if is_order_offline!=None:
                unit_order_objs = unit_order_objs.filter(order__is_order_offline=is_order_offline)                

            if max_qty!="":
                unit_order_objs = unit_order_objs.filter(quantity__lte=int(max_qty))

            if min_qty!="":
                unit_order_objs = unit_order_objs.filter(quantity__gte=int(min_qty))

            if max_price!="":
                unit_order_objs = unit_order_objs.filter(price__lte=int(max_price))

            if min_price!="":
                unit_order_objs = unit_order_objs.filter(price__gte=int(min_price))
            
            if cancellation_requested:
                unit_order_objs = unit_order_objs.filter(cancelled_by_user=True)

            if sales_person!="":
                unit_order_objs = unit_order_objs.filter(order__offline_sales_person__username=sales_person)

            if len(search_list)>0:
                temp_unit_order_objs = UnitOrder.objects.none()
                for search_string in search_list:
                    search_string = search_string.strip()
                    temp_unit_order_objs |= unit_order_objs.filter(Q(product__product__base_product__seller_sku__icontains=search_string) | Q(order__bundleid__icontains=search_string) | Q(orderid__icontains=search_string) | Q(order__owner__first_name__icontains=search_string) | Q(order__shipping_address__contact_number__icontains=search_string) | Q(order__shipping_address__first_name__icontains=search_string) | Q(order__shipping_address__last_name__icontains=search_string)|  Q(order__merchant_reference__icontains=search_string) | Q(order__sap_final_billing_info__icontains=search_string) | Q(sap_intercompany_info__icontains=search_string))
                unit_order_objs = temp_unit_order_objs.distinct()


            order_objs = Order.objects.filter(location_group__uuid=location_group_uuid, unitorder__in=unit_order_objs).distinct().order_by("-order_placed_date")
            
            omnycomm_user = OmnyCommUser.objects.get(username=request.user.username)         
            update_sendex_consignment_status(order_objs, omnycomm_user)
            total_revenue = order_objs.aggregate(Sum('real_to_pay'))["real_to_pay__sum"]
            if total_revenue==None:
                total_revenue = 0
            total_revenue = round(total_revenue, 2)
            
            currency = location_group_obj.location.currency

            paginator = Paginator(order_objs, 10)
            total_orders = order_objs.count()
            order_objs = paginator.page(page)

            shipping_charge = location_group_obj.delivery_fee
            free_delivery_threshold = location_group_obj.free_delivery_threshold
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
                    temp_dict["isSapManualUpdate"] = order_obj.sap_manual_update_status
                    temp_dict["dateCreated"] = order_obj.get_date_created()
                    temp_dict["time"] = order_obj.get_time_created()
                    temp_dict["paymentMode"] = order_obj.payment_mode
                    temp_dict["cheque_images_list"] = []
                    temp_dict["cheque_approved"] =  False
                    
                    if order_obj.payment_mode == "CHEQUE":
                        image_objs = order_obj.cheque_images.all()
                        cheque_images_list = []
                        for image_obj in image_objs:
                            try:
                                if image_obj.mid_image!=None:
                                    temp_dict_cheque_image = {}
                                    temp_dict_cheque_image["url"] = image_obj.mid_image.url
                                    temp_dict_cheque_image["uuid"] = image_obj.pk
                                    cheque_images_list.append(temp_dict_cheque_image)
                            except Exception as e:
                                exc_type, exc_obj, exc_tb = sys.exc_info()
                                logger.warning("FetchOrdersForWarehouseManagerAPI: %s at %s", e, str(exc_tb.tb_lineno))
                        temp_dict["cheque_images_list"] = cheque_images_list
                        temp_dict["cheque_approved"] =  order_obj.cheque_approved
                        
                    temp_dict["paymentStatus"] = order_obj.payment_status
                    temp_dict["merchant_reference"] = order_obj.merchant_reference
                    cancel_status = UnitOrder.objects.filter(order=order_obj, current_status_admin="cancelled").exists()
                    temp_dict["cancelStatus"] = cancel_status
                    temp_dict["cancelled_by_user"] = False
                    unit_order_count = UnitOrder.objects.filter(order=order_obj).count()
                    if UnitOrder.objects.filter(order=order_obj, cancelled_by_user=True).count() == unit_order_count:
                        temp_dict["cancelled_by_user"] = True
                    temp_dict["partially_cancelled_by_user"] = False
                    if temp_dict["cancelled_by_user"]==False and UnitOrder.objects.filter(order=order_obj, cancelled_by_user=True).exists():
                        temp_dict["partially_cancelled_by_user"] = True
                    cancelling_note = ""
                    if cancel_status==True and UnitOrder.objects.filter(order=order_obj, current_status_admin="cancelled").count() == unit_order_count:
                        cancelling_note = UnitOrder.objects.filter(order=order_obj, current_status_admin="cancelled")[0].cancelling_note
                    temp_dict["cancelling_note"] = cancelling_note
                    temp_dict["cancellation_request_action_taken"] = UnitOrder.objects.filter(order=order_obj, cancellation_request_action_taken=True).exists()
                    temp_dict["sap_final_billing_info"] = json.loads(order_obj.sap_final_billing_info)
                    temp_dict["isOrderOffline"] = order_obj.is_order_offline
                    temp_dict["referenceMedium"] = order_obj.reference_medium
                    temp_dict["call_status"] = order_obj.call_status
                    if order_obj.is_order_offline and order_obj.offline_sales_person!=None:
                        temp_dict["salesPerson"] = order_obj.offline_sales_person.username

                    address_obj = order_obj.shipping_address
                    
                    shipping_address = get_address_dict(address_obj)

                    customer_name = address_obj.first_name
                    if location_group_obj.is_b2b==True:
                        try:
                            b2b_user_obj = B2BUser.objects.get(username=order_obj.owner.username)
                            temp_dict["companyName"] = b2b_user_obj.company_name
                            shipping_address["vatCertificateId"] = b2b_user_obj.vat_certificate_id
                        except Exception as e:
                            temp_dict["companyName"] = "NA"
                            exc_type, exc_obj, exc_tb = sys.exc_info()
                            logger.error("b2b user company name: %s at %s", e, str(exc_tb.tb_lineno))

                    temp_dict["customerName"] = customer_name
                    temp_dict["emailId"] = order_obj.owner.email
                    temp_dict["contactNumer"] = order_obj.owner.contact_number
                    temp_dict["shippingAddress"] = shipping_address
                    temp_dict["billingAddress"] = get_address_dict(order_obj.billing_address)
                    temp_dict["adminNote"] = order_obj.admin_note
                    temp_dict["additionalNote"] = order_obj.additional_note

                    temp_dict["bundleId"] = order_obj.bundleid
                    temp_dict["uuid"] = order_obj.uuid
                    temp_dict["isVoucherApplied"] = is_voucher_applied
                    temp_dict["shippingMethod"] = UnitOrder.objects.filter(order=order_obj)[0].shipping_method
                    temp_dict["weight"] = order_obj.get_weight()

                    if temp_dict["partially_cancelled_by_user"]==True:
                        temp_dict["currentStatus"] = UnitOrder.objects.filter(order=order_obj).exclude(current_status_admin="cancelled")[0].current_status_admin
                    else:
                        temp_dict["currentStatus"] = UnitOrder.objects.filter(order=order_obj)[0].current_status_admin

                    if VersionOrder.objects.filter(user=request.user,order=order_obj).exists():
                        try:
                            version_order_obj = VersionOrder.objects.filter(user=request.user,order=order_obj).last()
                            change_information = json.loads(version_order_obj.change_information)
                            temp_dict["oldStatus"] = change_information["information"]['old_status']
                        except Exception as e:
                            exc_type, exc_obj, exc_tb = sys.exc_info()
                            logger.error("version order issue: %s at %s", e, str(exc_tb.tb_lineno))
                    
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
                    for unit_order_obj in UnitOrder.objects.filter(order=order_obj):
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
                        temp_dict2["productNameAr"] = unit_order_obj.product.get_seller_sku() + " - " + unit_order_obj.product.get_name("ar")
                        temp_dict2["productImageUrl"] = unit_order_obj.product.get_main_image_url()
                        temp_dict2["intercompany_order_id"] = unit_order_obj.get_sap_intercompany_order_id()
                        temp_dict2["cancelled_by_user"] = unit_order_obj.cancelled_by_user
                        temp_dict2["user_cancellation_note"] = unit_order_obj.user_cancellation_note
                        temp_dict2["user_cancellation_status"] = unit_order_obj.user_cancellation_status
                        intercompany_qty = unit_order_obj.get_sap_intercompany_order_qty()
                        final_qty = unit_order_obj.get_sap_final_order_qty()

                        if intercompany_qty != "" and final_qty != "":
                            if intercompany_qty != final_qty and order_obj.sap_status!="GRN Conflict":
                                order_obj.sap_status = "GRN Conflict"
                                unit_order_obj.sap_status = "GRN Conflict"
                                order_obj.save()
                                unit_order_obj.save()
                                try:
                                    p1 = threading.Thread(target=notify_grn_error, args=(order_obj,))
                                    p1.start()
                                except Exception as e:
                                    exc_type, exc_obj, exc_tb = sys.exc_info()
                                    logger.error("notify_grn_error: %s at %s", e, str(exc_tb.tb_lineno))

                        temp_dict2["intercompany_qty"] = intercompany_qty
                        temp_dict2["final_qty"] = final_qty
                        unit_order_list.append(temp_dict2)
                    temp_dict["approved"] = UnitOrder.objects.filter(order=order_obj, current_status_admin="approved").count()
                    temp_dict["picked"] = UnitOrder.objects.filter(order=order_obj, current_status_admin="picked").count()
                    temp_dict["dispatched"] = UnitOrder.objects.filter(order=order_obj, current_status_admin="dispatched").count()
                    temp_dict["delivered"] = UnitOrder.objects.filter(order=order_obj, current_status_admin="delivered").count()
                    temp_dict["deliveryFailed"] = UnitOrder.objects.filter(order=order_obj, current_status_admin="delivery failed").count()

                    temp_dict["sapStatus"] = order_obj.sap_status
                    sap_warning_list = ["GRN Conflict", "Failed"]
                    sap_warning = True if order_obj.sap_status=="Manual" or UnitOrder.objects.filter(order=order_obj, sap_status__in=sap_warning_list).exists() else False
                    temp_dict["showSapWarning"] = sap_warning

                    temp_dict["showResendSAPOrder"] = True if UnitOrder.objects.filter(order=order_obj, sap_status__in=sap_warning_list).exists() else False

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

                    temp_dict["shipping_charge"] = shipping_charge
                    temp_dict["free_delivery_threshold"] = free_delivery_threshold
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
            response["pendingOrderRequestCount"] = OrderRequest.objects.filter(location_group__uuid=location_group_uuid,request_status="Pending").distinct().count()
            response["isAvailable"] = is_available
            response["totalOrders"] = total_orders
            response["orderList"] = order_list
            response["totalRevenue"] = total_revenue
            response["currency"] = currency
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOrdersForWarehouseManagerAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchOrderRequestsForWarehouseManagerAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchOrderRequestsForWarehouseManagerAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchOrderRequestsForWarehouseManagerAPI Restricted Access!")
                return Response(data=response)

            location_group_uuid = data["locationGroupUuid"]
            request_status = data.get("requestStatus","")

            page = data.get("page", 1)

            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            order_request_objs = OrderRequest.objects.filter(location_group__uuid=location_group_uuid).distinct().order_by("-date_created")

            if request_status != "":
                order_request_objs = order_request_objs.filter(request_status=request_status)

            currency = location_group_obj.location.currency

            paginator = Paginator(order_request_objs, 20)
            total_orders = order_request_objs.count()
            order_request_objs = paginator.page(page)

            shipping_charge = location_group_obj.delivery_fee
            free_delivery_threshold = location_group_obj.free_delivery_threshold
            website_group_name = location_group_obj.website_group.name.lower()
            footer_text = json.loads(location_group_obj.website_group.conf).get("footer_text", "NA")

            order_request_list = []
            for order_request_obj in order_request_objs:
                try:
                    voucher_obj = order_request_obj.voucher
                    is_voucher_applied = voucher_obj is not None

                    temp_dict = {}
                    temp_dict["dateCreated"] = order_request_obj.get_date_created()
                    temp_dict["orderRequestStatus"] = order_request_obj.request_status
                    temp_dict["timeCreated"] = order_request_obj.get_time_created()
                    temp_dict["paymentMode"] = order_request_obj.payment_mode
                    unit_order_request_count = UnitOrderRequest.objects.filter(order_request=order_request_obj).count()
                    temp_dict["itemsCount"] = unit_order_request_count

                    address_obj = order_request_obj.shipping_address
                    shipping_address = {
                        "firstName": address_obj.first_name,
                        "lastName": address_obj.last_name,
                        "line1": json.loads(address_obj.address_lines)[0],
                        "line2": json.loads(address_obj.address_lines)[1],
                        "line3": json.loads(address_obj.address_lines)[2],
                        "line4": json.loads(address_obj.address_lines)[3],
                        "state": address_obj.state,
                        "emirates": address_obj.emirates,
                        "geoCoordinates": address_obj.geo_coordinates
                    }

                    customer_name = address_obj.first_name
                    if location_group_obj.is_b2b==True:
                        try:
                            b2b_user_obj = B2BUser.objects.get(username=order_request_obj.owner.username)
                            temp_dict["companyName"] = b2b_user_obj.company_name
                            shipping_address["vatCertificateId"] = b2b_user_obj.vat_certificate_id
                        except Exception as e:
                            temp_dict["companyName"] = "NA"
                            exc_type, exc_obj, exc_tb = sys.exc_info()
                            logger.error("b2b user company name: %s at %s", e, str(exc_tb.tb_lineno))

                    temp_dict["customerName"] = customer_name
                    temp_dict["emailId"] = order_request_obj.owner.email
                    temp_dict["contactNumber"] = order_request_obj.owner.contact_number
                    temp_dict["shippingAddress"] = shipping_address
                    temp_dict["additionalNote"] = order_request_obj.additional_note
                    temp_dict["adminNote"] = order_request_obj.admin_note

                    temp_dict["bundleId"] = order_request_obj.bundleid
                    temp_dict["uuid"] = order_request_obj.uuid
                    temp_dict["isVoucherApplied"] = is_voucher_applied

                    if is_voucher_applied:
                        temp_dict["voucherCode"] = voucher_obj.voucher_code
                        voucher_discount = voucher_obj.get_voucher_discount(order_request_obj.get_subtotal())
                        temp_dict["voucherDiscount"] = voucher_discount

                    unit_order_request_list = []
                    subtotal = 0
                    unit_order_request_objs = UnitOrderRequest.objects.filter(order_request=order_request_obj)
                    for unit_order_request_obj in unit_order_request_objs:
                        temp_dict2 = {}
                        temp_dict2["orderRequestId"] = unit_order_request_obj.order_req_id
                        temp_dict2["requestStatus"] = unit_order_request_obj.request_status
                        temp_dict2["uuid"] = unit_order_request_obj.uuid
                        temp_dict2["initialQuantity"] = unit_order_request_obj.initial_quantity
                        temp_dict2["initialPrice"] = unit_order_request_obj.initial_price
                        temp_dict2["finalQuantity"] = unit_order_request_obj.final_quantity
                        temp_dict2["finalPrice"] = unit_order_request_obj.final_price
                        temp_dict2["productName"] = unit_order_request_obj.product.get_seller_sku() + " - " + unit_order_request_obj.product.get_name()
                        temp_dict2["productImageUrl"] = unit_order_request_obj.product.get_main_image_url()

                        unit_order_request_list.append(temp_dict2)
                    
                    is_cod = True if order_request_obj.payment_mode=="COD" else False
                    subtotal = order_request_obj.get_subtotal()
                    delivery_fee = order_request_obj.get_delivery_fee(cod=is_cod)
                    cod_fee = order_request_obj.get_cod_charge(cod=is_cod)
                    vat = order_request_obj.get_vat(cod=is_cod)
                    to_pay = order_request_obj.get_total_amount(cod=is_cod)

                    temp_dict["subtotal"] = str(subtotal)
                    temp_dict["totalQuantity"] = unit_order_request_objs.exclude(request_status="Rejected").aggregate(total_quantity=Sum('final_quantity'))["total_quantity"]
                    temp_dict["deliveryFee"] = str(delivery_fee)
                    temp_dict["codFee"] = str(cod_fee)
                    temp_dict["toPay"] = str(to_pay)
                    temp_dict["currency"] = currency
                    temp_dict["vat"] = str(vat)

                    temp_dict["unitOrderRequestList"] = unit_order_request_list

                    temp_dict["shipping_charge"] = shipping_charge
                    temp_dict["free_delivery_threshold"] = free_delivery_threshold
                    temp_dict["website_group_name"] = website_group_name
                    temp_dict["footer_text"] = footer_text

                    order_request_list.append(temp_dict)

                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchOrderRequestsForWarehouseManagerAPI: %s at %s", e, str(exc_tb.tb_lineno))

            is_available = True
            if int(paginator.num_pages) == int(page):
                is_available = False

            response["isAvailable"] = is_available
            response["totalOrders"] = total_orders
            response["orderRequestList"] = order_request_list
            response["currency"] = currency
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOrderRequestsForWarehouseManagerAPI: %s at %s", e, str(exc_tb.tb_lineno))

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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchShippingMethodAPI Restricted Access!")
                return Response(data=response)
            
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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("SetShippingMethodAPI Restricted Access!")
                return Response(data=response)

            shipping_method = data["shippingMethod"]
            unit_order_uuid_list = data["unitOrderUuidList"]
            sap_manual_update_status = data["isSapManualUpdate"]
            order_obj = UnitOrder.objects.get(uuid=unit_order_uuid_list[0]).order
            order_shipping_method = UnitOrder.objects.filter(order=order_obj).exclude(current_status_admin="cancelled")[0].shipping_method
  
            # after checking for all the shipping methods possible
            sap_info_render = []

            if not(sap_manual_update_status) and order_obj.location_group.is_sap_enabled and order_shipping_method != shipping_method:
                user_input_requirement = {}
                
                for unit_order_obj in UnitOrder.objects.filter(order=order_obj).exclude(current_status_admin="cancelled"):
                    seller_sku = unit_order_obj.product.get_seller_sku()
                    brand_name = unit_order_obj.product.get_brand()
                    company_code_obj = CompanyCodeSAP.objects.get(location_group=order_obj.location_group, brand__name=brand_name)
                    stock_price_information = fetch_prices_and_stock(seller_sku, company_code_obj.code)

                    if stock_price_information["status"] == 500:
                        response["status"] = 403
                        response["message"] = stock_price_information["message"]
                        logger.error("SetShippingMethodAPI: fetch prices and stock gave 500!")
                        return Response(data=response)

                    user_input_requirement[seller_sku] = is_user_input_required_for_sap_punching(stock_price_information, unit_order_obj.quantity)

                user_input_sap = data.get("user_input_sap", None)
                
                if user_input_sap==None:
                    
                    modal_info_list = []
                    
                    for unit_order_obj in UnitOrder.objects.filter(order=order_obj).exclude(current_status_admin="cancelled"):
                        seller_sku = unit_order_obj.product.get_seller_sku()
                        brand_name = unit_order_obj.product.get_brand()
                        company_code_obj = CompanyCodeSAP.objects.get(location_group=order_obj.location_group, brand__name=brand_name)
                        
                        if user_input_requirement[seller_sku]==True:
                            result = fetch_prices_and_stock(seller_sku, company_code_obj.code)
                            result["uuid"] = unit_order_obj.uuid
                            result["seller_sku"] = seller_sku
                            result["disable_atp_holding"] = False
                            result["disable_atp"] = False
                            result["disable_holding"] = False
                            if result["total_holding"] < unit_order_obj.quantity and result["total_atp"] < unit_order_obj.quantity:
                                result["disable_atp_holding"] = True
                            elif result["total_atp"] <  unit_order_obj.quantity:
                                result["disable_atp"] = True
                            elif result["total_holding"] < unit_order_obj.quantity:
                                result["disable_holding"] = True

                            modal_info_list.append(result)
                    
                    if len(modal_info_list)>0:
                        response["modal_info_list"] = modal_info_list
                        response["status"] = 200
                        return Response(data=response)

                error_flag = 0
                sap_info_render = []

                # [ List pf Querysets of (UnitOrder Objects grouped by Brand) ]

                unit_order_objs = UnitOrder.objects.filter(order=order_obj).exclude(current_status_admin="cancelled")

                if unit_order_objs.filter(grn_filename="").exists():

                    grouped_unit_orders = {} 

                    for unit_order_obj in unit_order_objs:
                        
                        brand_name = unit_order_obj.product.get_brand()
                        
                        if brand_name not in grouped_unit_orders:
                            grouped_unit_orders[brand_name] = []
                        
                        grouped_unit_orders[brand_name].append(unit_order_obj)
                    
                    for brand_name in grouped_unit_orders: 
                        if grouped_unit_orders[brand_name][0].sap_status=="In GRN":
                            continue

                        order_information = {}
                        company_code_obj = CompanyCodeSAP.objects.get(location_group=order_obj.location_group, brand__name=brand_name)
                        order_information["order_id"] = order_obj.bundleid.replace("-","")
                        order_information["refrence_id"] = order_obj.bundleid.replace("-","&#45;")
                        is_b2b = order_obj.location_group.is_b2b
                        order_information["is_b2b"] = is_b2b
                        if is_b2b==True:
                            order_information["street"] = json.loads(order_obj.shipping_address.address_lines)[1]
                            order_information["region"] = order_obj.shipping_address.state
                            order_information["telephone"] = order_obj.shipping_address.contact_number
                            order_information["email"] = order_obj.owner.email
                            b2b_user_obj = B2BUser.objects.get(username=order_obj.owner.username) 
                            order_information["trn"] = b2b_user_obj.vat_certificate_id
                            if order_information["trn"] == "":
                                response["message"] = "TRN number is empty"
                                response["status"] = 406
                                return Response(data=response)
                        order_information["items"] = []
                        
                        seller_sku_list = []
                        for unit_order_obj in grouped_unit_orders[brand_name]:

                            seller_sku = unit_order_obj.product.get_seller_sku()
                            seller_sku_list.append(seller_sku)
                            x_value = ""
                            
                            if user_input_requirement[seller_sku]==True:
                                x_value = user_input_sap[seller_sku]
                            
                            item_list =  fetch_order_information_for_sap_punching(seller_sku, company_code_obj.code, x_value, unit_order_obj.quantity)
                            for item in item_list:
                                price = format(unit_order_obj.get_subtotal_without_vat_custom_qty(item["qty"]),'.2f')
                                item.update({"price": price})
                            order_information["items"] += item_list
                        logger.info("FINAL ORDER INFO: %s", str(order_information))

                        orig_result_pre = create_intercompany_sales_order(company_code_obj.code, order_information, seller_sku_list)

                        manual_intervention_required = is_manual_intervention_required(orig_result_pre)

                        if manual_intervention_required==True:
                            order_obj.sap_status = "Manual"
                            order_obj.save()

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
                                try:
                                    p1 = threading.Thread(target=notify_grn_error, args=(unit_order_obj.order,))
                                    p1.start()
                                except Exception as e:
                                    exc_type, exc_obj, exc_tb = sys.exc_info()
                                    logger.error("notify_grn_error: %s at %s", e, str(exc_tb.tb_lineno))

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
                
            for unit_order_obj in UnitOrder.objects.filter(order=order_obj).exclude(current_status_admin="cancelled"):
                set_shipping_method(unit_order_obj, shipping_method)

            omnycomm_user = OmnyCommUser.objects.get(username=request.user.username)         
            order_status_change_information = {
                "event": "order_status",
                "information": {
                    "old_status": "pending",
                    "new_status": "approved"
                }
            }

            VersionOrder.objects.create(order=order_obj,
                                        user= omnycomm_user,
                                        change_information=json.dumps(order_status_change_information))

            if "weight" in data and shipping_method.lower()=="sendex" and order_obj.location_group.website_group.name.lower() in ["daycart", "shopnesto"]:
                modified_weight = data["weight"]
                if sendex_add_consignment(order_obj, modified_weight) == "failure":
                    logger.warning("SetShippingMethodAPI: failed status from sendex api")
                else:
                    logger.info("SetShippingMethodAPI: Success in sendex api")

            if sap_manual_update_status:
                sap_manual_update(order_obj, omnycomm_user)
                logger.info("SetShippingMethodAPI: sap_manual_update_status: %s", str(sap_manual_update_status))

            response["sap_info_render"] = sap_info_render
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SetShippingMethodAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class ResendSAPOrderAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("ResendSAPOrderAPI: %s", str(data))

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("ResendSAPOrderAPI Restricted Access!")
                return Response(data=response)

            if not isinstance(data, dict):
                data = json.loads(data)

            order_uuid = data["orderUuid"]
            order_obj = Order.objects.get(uuid=order_uuid)

            sap_info_render = []
            if order_obj.location_group.is_sap_enabled:
                user_input_requirement = {}
                
                for unit_order_obj in UnitOrder.objects.filter(order=order_obj).exclude(current_status_admin="cancelled"):
                    seller_sku = unit_order_obj.product.get_seller_sku()
                    brand_name = unit_order_obj.product.get_brand()
                    company_code_obj = CompanyCodeSAP.objects.get(location_group=order_obj.location_group, brand__name=brand_name)
                    stock_price_information = fetch_prices_and_stock(seller_sku, company_code_obj.code)

                    if stock_price_information["status"] == 500:
                        response["status"] = 403
                        response["message"] = stock_price_information["message"]
                        return Response(data=response)

                    user_input_requirement[seller_sku] = is_user_input_required_for_sap_punching(stock_price_information, unit_order_obj.quantity)

                user_input_sap = data.get("user_input_sap", None)
                
                if user_input_sap==None:
                    
                    modal_info_list = []
                    
                    for unit_order_obj in UnitOrder.objects.filter(order=order_obj).exclude(current_status_admin="cancelled"):
                        seller_sku = unit_order_obj.product.get_seller_sku()
                        brand_name = unit_order_obj.product.get_brand()
                        company_code_obj = CompanyCodeSAP.objects.get(location_group=order_obj.location_group, brand__name=brand_name)
                        
                        if user_input_requirement[seller_sku]==True:
                            result = fetch_prices_and_stock(seller_sku, company_code_obj.code)
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

                unit_order_objs = UnitOrder.objects.filter(order=order_obj).exclude(current_status_admin="cancelled")

                if unit_order_objs.filter(grn_filename="").exists():

                    grouped_unit_orders = {} 

                    for unit_order_obj in unit_order_objs:
                        
                        brand_name = unit_order_obj.product.get_brand()
                        
                        if brand_name not in grouped_unit_orders:
                            grouped_unit_orders[brand_name] = []
                        
                        grouped_unit_orders[brand_name].append(unit_order_obj)
                    
                    for brand_name in grouped_unit_orders: 
                        if grouped_unit_orders[brand_name][0].sap_status=="In GRN":
                            continue

                        order_information = {}
                        company_code_obj = CompanyCodeSAP.objects.get(location_group=order_obj.location_group, brand__name=brand_name)
                        order_information["order_id"] = order_obj.bundleid.replace("-","")
                        order_information["refrence_id"] = order_obj.bundleid.replace("-","&#45;")
                        is_b2b = order_obj.location_group.is_b2b
                        order_information["is_b2b"] = is_b2b
                        if is_b2b==True:
                            order_information["street"] = json.loads(order_obj.shipping_address.address_lines)[1]
                            order_information["region"] = order_obj.shipping_address.state
                            order_information["telephone"] = order_obj.shipping_address.contact_number
                            order_information["email"] = order_obj.owner.email
                            b2b_user_obj = B2BUser.objects.get(username=order_obj.owner.username) 
                            order_information["trn"] = b2b_user_obj.vat_certificate_id
                        order_information["items"] = []
                        
                        seller_sku_list = []
                        for unit_order_obj in grouped_unit_orders[brand_name]:

                            seller_sku = unit_order_obj.product.get_seller_sku()
                            seller_sku_list.append(seller_sku)
                            x_value = ""
                            
                            if user_input_requirement[seller_sku]==True:
                                x_value = user_input_sap[seller_sku]
                            
                            item_list =  fetch_order_information_for_sap_punching(seller_sku, company_code_obj.code, x_value, unit_order_obj.quantity)
                            for item in item_list:
                                price = format(unit_order_obj.get_subtotal_without_vat_custom_qty(item["qty"]),'.2f')
                                item.update({"price": price})
                            order_information["items"] += item_list

                        orig_result_pre = create_intercompany_sales_order(company_code_obj.code, order_information, seller_sku_list)

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
                                try:
                                    p1 = threading.Thread(target=notify_grn_error, args=(unit_order_obj.order,))
                                    p1.start()
                                except Exception as e:
                                    exc_type, exc_obj, exc_tb = sys.exc_info()
                                    logger.error("notify_grn_error: %s at %s", e, str(exc_tb.tb_lineno))

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

            response["sap_info_render"] = sap_info_render
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ResendSAPOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

#API with active log
class UpdateManualOrderAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateManualOrderAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UpdateManualOrderAPI Restricted Access!")
                return Response(data=response)

            order_uuid = data["orderUuid"]

            order_obj = Order.objects.get(uuid=order_uuid)
            prev_order_instance = deepcopy(order_obj)
            order_obj.sap_status = "Success"
            order_obj.save()
            render_value = "Order " + order_obj.bundleid + "sap status updated"
            activitylog(user=request.user,table_name=Order,action_type='update',location_group_obj=order_obj.location_group,prev_instance=prev_order_instance,current_instance=order_obj,table_item_pk=order_obj.uuid,render=render_value)

            unit_order_objs = UnitOrder.objects.filter(order=order_obj).exclude(current_status_admin="cancelled")
            unit_order_objs.update(sap_status="GRN Done")
            
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateManualOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))

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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("SetOrdersStatusAPI Restricted Access!")
                return Response(data=response)

            order_status = data["orderStatus"]
            unit_order_uuid_list = data["unitOrderUuidList"]
            first_unit_order_obj  = UnitOrder.objects.get(uuid=unit_order_uuid_list[0])

            for unit_order_uuid in unit_order_uuid_list:
                unit_order_obj = UnitOrder.objects.get(uuid=unit_order_uuid)
                set_order_status(unit_order_obj, order_status)
               
            omnycomm_user = OmnyCommUser.objects.get(username=request.user.username)         
            order_status_change_information = {
                "event": "order_status",
                "information": {
                    "old_status": first_unit_order_obj.current_status_admin,
                    "new_status": order_status
                }
            }

            VersionOrder.objects.create(order=first_unit_order_obj.order,
                                        user= omnycomm_user,
                                        change_information=json.dumps(order_status_change_information))

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SetOrdersStatusAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SetOrdersStatusBulkAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SetOrdersStatusBulkAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("SetOrdersStatusBulkAPI Restricted Access!")
                return Response(data=response)

            order_status = data["orderStatus"]
            order_uuid_list = data["orderUuidList"]

            for order_uuid in order_uuid_list:
                try:
                    order_obj = Order.objects.get(uuid=order_uuid)
                    for unit_order_obj in UnitOrder.objects.filter(order=order_obj).exclude(current_status_admin="cancelled"):
                        set_order_status(unit_order_obj, order_status)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("SetOrdersStatusBulkAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SetOrdersStatusBulkAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UpdateOrderStatusAPI(APIView):
    
    authentication_classes = (CsrfExemptSessionAuthentication,) 
    permission_classes = [AllowAny]

    def post(self,request,*args,**kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UpdateOrderStatusAPI: %s", str(data))
            sap_invoice_id = data["sap_invoice_id"]
            incoming_order_status = data["incoming_order_status"]
            if sap_invoice_id.strip()=="":
                            return Response(data=response)
            order_obj = Order.objects.get(sap_final_billing_info__icontains=sap_invoice_id)
            doc_list = json.loads(order_obj.sap_final_billing_info)["doc_list"]
            flag = False
            for doc in doc_list:
                if doc["id"]==sap_invoice_id:
                    flag = True
                    break

            if flag==False:
                return Response(data = response)
            unit_order_objs = UnitOrder.objects.filter(order = order_obj)

            for unit_order_obj in unit_order_objs:
                if incoming_order_status == "dispatched" and unit_order_obj.current_status_admin == "picked":          
                    set_order_status_without_mail(unit_order_obj, "dispatched")
                elif incoming_order_status == "delivered" and unit_order_obj.current_status_admin == "dispatched":
                    set_order_status_without_mail(unit_order_obj, "delivered")
                else:
                    logger.warning("UpdateOrderStatusAPI: Bad transition request-400")
                    break
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateOrderStatusAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data = response)


class BulkUpdateOrderStatusAPI(APIView):
    
    authentication_classes = (CsrfExemptSessionAuthentication,) 
    permission_classes = [AllowAny]

    def post(self,request,*args,**kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("BulkUpdateOrderStatusAPI: %s", str(data))
            list_of_orders = json.loads(data["list_of_orders"])
            p1 =  threading.Thread(target=bulk_update_order_status , args=(list_of_orders))
            p1.start()
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("BulkUpdateOrderStatusAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

        return Response(data = response)

class SetCallStatusAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:
            data = request.data
            logger.info("SetCallStatusAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("SetCallStatusAPI Restricted Access!")
                return Response(data=response)

            updated_call_status = data["call_status"]
            order_uuid  = data["orderUuid"]

            order_obj = Order.objects.get(uuid=order_uuid)
            old_call_status = order_obj.call_status
            order_obj.call_status = updated_call_status
            order_obj.save()

            omnycomm_user = OmnyCommUser.objects.get(username=request.user.username)         
            call_status_change_information = {
                "event": "call_status",
                "information": {
                    "old_status": old_call_status,
                    "new_status": updated_call_status
                }
            }

            VersionOrder.objects.create(order=order_obj,
                                        user= omnycomm_user,
                                        change_information=json.dumps(call_status_change_information))

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SetCallStatusAPI: %s at %s",e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class FetchOCSalesPersonsAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchOCSalesPersonsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchOCSalesPersonsAPI Restricted Access!")
                return Response(data=response)

            location_group_uuid = data["locationGroupUuid"]
            is_sales_executive = data.get("is_sales_executive",False)
            
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            custom_permission_objs = location_group_obj.custompermission_set.all()
            
            if is_sales_executive==True:
                sales_custom_permission_objs = CustomPermission.objects.none()
                for custom_permission_obj in custom_permission_objs:
                    misc = json.loads(custom_permission_obj.misc)
                    if "sales-analytics" in misc:
                        sales_custom_permission_objs = sales_custom_permission_objs | CustomPermission.objects.filter(pk=custom_permission_obj.pk)
                custom_permission_objs = sales_custom_permission_objs

            sales_person_list=[]
            for custom_permission_obj in custom_permission_objs:
                temp_dict = {}
                temp_dict["username"] = custom_permission_obj.user.username
                temp_dict["firstName"] = custom_permission_obj.user.first_name
                temp_dict["lastName"] = custom_permission_obj.user.last_name
                sales_person_list.append(temp_dict)
        
            response["salesPersonList"] = sales_person_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOCSalesPersonsAPI: %s at %s", e, str(exc_tb.tb_lineno))

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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("CancelOrdersAPI Restricted Access!")
                return Response(data=response)

            unit_order_uuid_list = data["unitOrderUuidList"]
            cancelling_note = data["cancellingNote"]

            order_obj = None
            for unit_order_uuid in unit_order_uuid_list:
                unit_order_obj = UnitOrder.objects.get(uuid=unit_order_uuid)
                cancel_order_admin(unit_order_obj, cancelling_note)
                order_obj = unit_order_obj.order

            if order_obj!=None:

                omnycomm_user_obj = OmnyCommUser.objects.get(username=request.user.username)
                order_cancel_information = {
                    "event" : "order_cancel",
                    "information" : {}
                }
                VersionOrder.objects.create(order=order_obj,
                                            user= omnycomm_user_obj,
                                            change_information=json.dumps(order_cancel_information))
                order_obj.real_to_pay = order_obj.get_total_amount(is_real=True)
                order_obj.save()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CancelOrdersAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class ApproveCancellationRequestAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            
            data = request.data
            logger.info("ApproveCancellationRequestAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("ApproveCancellationRequestAPI Restricted Access!")
                return Response(data=response)

            unit_order_uuid_list = data["unit_order_uuid_list"]

            unit_order_objs = UnitOrder.objects.filter(uuid__in=unit_order_uuid_list)

            for unit_order_obj in unit_order_objs:
                if unit_order_obj.order.payment_mode=="COD":
                    unit_order_obj.user_cancellation_status="approved"
                    unit_order_obj.cancellation_request_action_taken=True
                    unit_order_obj.save()
                    notify_order_cancel_status_to_user(unit_order_obj,"approved")
                else:
                    unit_order_obj.user_cancellation_status="refund processed"
                    unit_order_obj.cancellation_request_action_taken=True
                    unit_order_obj.save()
                    notify_order_cancel_status_to_user(unit_order_obj,"refund processed")
                cancel_order_admin(unit_order_obj,unit_order_obj.user_cancellation_note)
                
            
            if unit_order_objs.exists():
                order_obj = unit_order_objs[0].order
                order_obj.real_to_pay = order_obj.get_total_amount(is_real=True)
                order_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ApproveCancellationRequestAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class RejectCancellationRequestAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            
            data = request.data
            logger.info("RejectCancellationRequestAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("RejectCancellationRequestAPI Restricted Access!")
                return Response(data=response)

            unit_order_uuid_list = data["unit_order_uuid_list"]
            for unit_order_uuid in unit_order_uuid_list:
                unit_order_obj = UnitOrder.objects.get(uuid=unit_order_uuid)
                unit_order_obj.user_cancellation_status = "rejected"
                unit_order_obj.cancellation_request_action_taken = True
                unit_order_obj.save()
                notify_order_cancel_status_to_user(unit_order_obj,"rejected")
                
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("RejectCancellationRequestAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class UpdateCancellationRequestRefundStatusAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            
            data = request.data
            logger.info("UpdateCancellationRequestRefundStatusAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UpdateCancellationRequestRefundStatusAPI Restricted Access!")
                return Response(data=response)

            unit_order_uuid = data["unit_order_uuid"]

            unit_order_obj = UnitOrder.objects.get(uuid=unit_order_uuid)
            prev_unit_order_instance = unit_order_obj
            unit_order_obj.user_cancellation_status = "refunded"
            unit_order_obj.save()

            notify_order_cancel_status_to_user(unit_order_obj,"refunded")
            activitylog(user=request.user,table_name=UnitOrder,action_type='update',location_group_obj=None,prev_instance=prev_unit_order_instance,current_instance=unit_order_obj,table_item_pk=unit_order_obj.pk,render='{} refunded'.format(unit_order_obj))
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateCancellationRequestRefundStatusAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("DownloadOrdersAPI Restricted Access!")
                return Response(data=response)

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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("UploadOrdersAPI Restricted Access!")
                return Response(data=response)
            
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
                if voucher_obj.is_super_category_eligible(cart_obj)==False:
                    response["error_message"] = "NOT APPLICABLE"
                    response["voucher_success"] = False
                    response["status"] = 200
                    return Response(data=response)
            else:
                if voucher_obj.is_super_category_eligible(fast_cart_obj)==False:
                    response["error_message"] = "NOT APPLICABLE"
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
                currency = cart_obj.get_currency()
                response["currency"] = currency
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

                currency = fast_cart_obj.get_currency()
                response["currency"] = currency
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

            try:
                custom_data = []
                custom_data.append(CustomData(
                    content_type="product",
                    value=total_amount,
                    currency=currency,
                ))
                calling_facebook_api(event_name="Purchase",user=owner,request=request,custom_data=custom_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("ApplyVoucherCodeAPI: %s at %s", e, str(exc_tb.tb_lineno))
            
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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("ApplyOfflineVoucherCodeAPI Restricted Access!")
                return Response(data=response)
            
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

            if voucher_obj.is_eligible(cart_obj.get_subtotal(offline=True))==False:
                response["error_message"] = "NOT APPLICABLE"
                response["voucher_success"] = False
                response["status"] = 200
                return Response(data=response)

            if voucher_obj.is_super_category_eligible(cart_obj)==False:
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

            update_cart_bill(cart_obj,cod=True,offline=True)

            subtotal = cart_obj.get_subtotal(offline=True)
            
            delivery_fee = cart_obj.get_delivery_fee(offline=True)
            total_amount = cart_obj.get_total_amount(offline=True)
            vat = cart_obj.get_vat(offline=True)

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
                "codCharge": cart_obj.offline_cod_charge,
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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("RemoveOfflineVoucherCodeAPI Restricted Access!")
                return Response(data=response)
            
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            username = data["username"]

            cart_obj = Cart.objects.get(location_group=location_group_obj, owner__username=username)
            cart_obj.voucher = None
            cart_obj.save()

            update_cart_bill(cart_obj,cod=True,offline=True)

            subtotal = cart_obj.get_subtotal(offline=True)
            
            delivery_fee = cart_obj.get_delivery_fee(offline=True)
            total_amount = cart_obj.get_total_amount(offline=True)
            vat = cart_obj.get_vat(offline=True)

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
                "codCharge": cart_obj.offline_cod_charge,
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

class AddOfflineReferenceMediumAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddOfflineReferenceMediumAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("AddOfflineReferenceMediumAPI Restricted Access!")
                return Response(data=response)
            
            location_group_uuid = data["locationGroupUuid"]
            username = data["username"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            reference_medium = data["reference_medium"]

            cart_obj = Cart.objects.get(location_group=location_group_obj, owner__username=username)
            cart_obj.reference_medium = reference_medium
            cart_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddOfflineReferenceMediumAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class AddOnlineAdditionalNoteAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddOnlineAdditionalNoteAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            additional_note = data["additional_note"]
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            is_fast_cart = data.get("is_fast_cart", False)

            if is_fast_cart==False:
                cart_obj = Cart.objects.get(location_group=location_group_obj, owner__username=request.user.username)
                cart_obj.additional_note = additional_note
                cart_obj.save()
                total_amount = cart_obj.get_total_amount()
                currency = cart_obj.get_currency()
            else:
                fast_cart_obj = FastCart.objects.get(location_group=location_group_obj, owner__username=request.user.username)
                fast_cart_obj.additional_note = additional_note
                fast_cart_obj.save()
                total_amount = fast_cart_obj.get_total_amount()
                currency = fast_cart_obj.get_currency()
            response['status'] = 200

            try:
                custom_data = []
                custom_data.append(CustomData(
                    content_type="product",
                    value=total_amount,
                    currency=currency,
                ))
                calling_facebook_api(event_name="Purchase",user=request.user,request=request,custom_data=custom_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("AddOnlineAdditionalNoteAPI: %s at %s", e, str(exc_tb.tb_lineno))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddOnlineAdditionalNoteAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddOfflineAdditionalNoteAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddOfflineAdditionalNoteAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("AddOfflineAdditionalNoteAPI Restricted Access!")
                return Response(data=response)
            
            location_group_uuid = data["locationGroupUuid"]
            username = data["username"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            additional_note = data["additional_note"]
            
            cart_obj = Cart.objects.get(location_group=location_group_obj, owner__username=username)
            cart_obj.additional_note = additional_note
            cart_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddOfflineAdditionalNoteAPI: %s at %s", e, str(exc_tb.tb_lineno))

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


class PlaceDaycartOnlineOrderAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("PlaceDaycartOnlineOrderAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            checkout_id = data["checkoutID"]
            payment_method = data["paymentMethod"]

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            is_fast_cart = data.get("is_fast_cart", False)

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            order_obj = None
            order_info = get_order_info_from_hyperpay(checkout_id, payment_method, location_group_obj)
            if order_info["result"]==False:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("PlaceDaycartOnlineOrderAPI: HYPERPAY STATUS MISMATCH!")
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
                    logger.warning("PlaceDaycartOnlineOrderAPI: voucher code not handled properly! %s at %s", e, str(exc_tb.tb_lineno))

                payment_info = "NA"
                payment_mode = "NA"
                try:
                    payment_info = order_info["payment_info"]
                    payment_mode = order_info["payment_info"]["paymentBrand"]
                except Exception as e:
                    pass

                order_obj = Order.objects.create(owner=cart_obj.owner,
                                                 shipping_address=cart_obj.shipping_address,
                                                 billing_address=cart_obj.billing_address,
                                                 to_pay=cart_obj.to_pay,
                                                 order_placed_date=timezone.now(),
                                                 voucher=cart_obj.voucher,
                                                 location_group=cart_obj.location_group,
                                                 payment_status="paid",
                                                 payment_info=payment_info,
                                                 payment_mode=payment_mode,
                                                 merchant_reference=checkout_id,
                                                 bundleid=cart_obj.merchant_reference,
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
                        address_obj = Address.objects.filter(user=dealshub_user_obj, is_shipping=True)[0]
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
                    logger.warning("PlaceDaycartOnlineOrderAPI: voucher code not handled properly! %s at %s", e, str(exc_tb.tb_lineno))

                payment_info = "NA"
                payment_mode = "NA"
                try:
                    payment_info = order_info["payment_info"]
                    payment_mode = order_info["payment_info"]["paymentBrand"]
                except Exception as e:
                    pass

                order_obj = Order.objects.create(owner=fast_cart_obj.owner,
                                                 shipping_address=fast_cart_obj.shipping_address,
                                                 billing_address=fast_cart_obj.billing_address,
                                                 to_pay=fast_cart_obj.to_pay,
                                                 order_placed_date=timezone.now(),
                                                 voucher=fast_cart_obj.voucher,
                                                 location_group=fast_cart_obj.location_group,
                                                 payment_status="paid",
                                                 payment_info=payment_info,
                                                 payment_mode=payment_mode,
                                                 merchant_reference=checkout_id,
                                                 bundleid=fast_cart_obj.merchant_reference,
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
                logger.error("PlaceDaycartOnlineOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))

            # Refresh Stock
            #refresh_stock(order_obj)

            #response["purchase"] = calculate_gtm(order_obj)

            response["status"] = 200

            try:
                calling_facebook_api(event_name="Purchase",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("PlaceDaycartOnlineOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("PlaceDaycartOnlineOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
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
            
            if is_fast_cart == "false":
                is_fast_cart = False
            elif is_fast_cart == "true":
                is_fast_cart = True

            online_payment_mode = data.get("online_payment_mode","card")
            
            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            order_obj = None

            if Order.objects.filter(merchant_reference=merchant_reference).exists():
                response["message"] = "Credentials for older order."
                logger.warning("PlaceOnlineOrderAPI: Credentials for older order!")
                return Response(data=response)
            
            if online_payment_mode.strip().lower()=="spotii":
                if on_approve_capture_order(merchant_reference)==False:
                    logger.warning("PlaceOnlineOrderAPI: SPOTII STATUS MISMATCH!")
                    return Response(data=response)
            elif online_payment_mode.strip().lower()=="tap":
                if get_charge_status(data["charge_id"])!="CAPTURED":
                    logger.warning("PlaceOnlineOrderAPI: TAP STATUS MISMATCH!")
                    return Response(data=response)
            elif online_payment_mode.strip().lower()=="network_global_android":
                if check_order_status_from_network_global_android(merchant_reference, location_group_obj)==False:
                    logger.warning("PlaceOnlineOrderAPI: NETWORK GLOBAL ANDROID STATUS MISMATCH!")
                    return Response(data=response)  
            elif online_payment_mode.strip().lower()=="credimax_gateway":
                if check_order_status_from_credimax_gateway(merchant_reference, location_group_obj)==False:
                    logger.warning("PlaceOnlineOrderAPI: CREDIMAX GATEWAY STATUS MISMATCH!")
                    response["message"]="Order is not placed."
                    return Response(data=response)  
            else:
                if check_order_status_from_network_global(merchant_reference, location_group_obj)==False:
                    logger.warning("PlaceOnlineOrderAPI: NETWORK GLOBAL STATUS MISMATCH!")
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
                                                 billing_address=cart_obj.billing_address,
                                                 to_pay=cart_obj.to_pay,
                                                 real_to_pay = cart_obj.to_pay,
                                                 order_placed_date=timezone.now(),
                                                 voucher=cart_obj.voucher,
                                                 location_group=cart_obj.location_group,
                                                 additional_note=cart_obj.additional_note,
                                                 payment_status="paid",
                                                 payment_info=payment_info,
                                                 payment_mode=payment_mode,
                                                 merchant_reference=merchant_reference,
                                                 bundleid=cart_obj.merchant_reference,
                                                 delivery_fee=cart_obj.get_delivery_fee(),
                                                 cod_charge=0)

                for unit_cart_obj in unit_cart_objs:
                    unit_order_obj = UnitOrder.objects.create(order=order_obj,
                                                              product=unit_cart_obj.product,
                                                              quantity=unit_cart_obj.quantity,
                                                              price=unit_cart_obj.product.get_actual_price_for_customer(dealshub_user_obj))
                    UnitOrderStatus.objects.create(unit_order=unit_order_obj)

                try:
                    unit_cart_objs = UnitCart.objects.filter(cart=cart_obj)
                    custom_data = []
                    for unit_cart_obj in unit_cart_objs:
                        custom_data.append(CustomData(
                            content_type="product",
                            value=unit_cart_obj.product.now_price,
                            currency=unit_cart_obj.product.get_currency(),
                            content_name=unit_cart_obj.product.get_name(),
                            content_category=unit_cart_obj.product.get_category(),
                            contents=[Content(product_id=unit_cart_obj.product.get_product_id(), quantity=unit_cart_obj.quantity, item_price=unit_cart_obj.product.now_price)],
                        ))
                    calling_facebook_api(event_name="Purchase",user=dealshub_user_obj,request=request,custom_data=custom_data)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("PlaceOnlineOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))

                # Cart gets empty
                for unit_cart_obj in unit_cart_objs:
                    unit_cart_obj.delete()

                # cart_obj points to None
                cart_obj.shipping_address = None
                cart_obj.voucher = None
                cart_obj.additional_note = ""
                cart_obj.to_pay = 0
                cart_obj.merchant_reference = ""
                cart_obj.payment_info = "{}"
                cart_obj.save()
            else:
                fast_cart_obj = FastCart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)

                try:
                    if fast_cart_obj.shipping_address==None:
                        address_obj = Address.objects.filter(user=dealshub_user_obj, is_shipping=True)[0]
                        fast_cart_obj.shipping_address = address_obj
                        fast_cart_obj.save()
                except Exception as e:
                    pass

                update_fast_cart_bill(fast_cart_obj)

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
                                                 billing_address=fast_cart_obj.billing_address,
                                                 to_pay=fast_cart_obj.to_pay,
                                                 real_to_pay=fast_cart_obj.to_pay,
                                                 order_placed_date=timezone.now(),
                                                 voucher=fast_cart_obj.voucher,
                                                 location_group=fast_cart_obj.location_group,
                                                 additional_note=fast_cart_obj.additional_note,
                                                 payment_status="paid",
                                                 payment_info=payment_info,
                                                 payment_mode=payment_mode,
                                                 merchant_reference=merchant_reference,
                                                 bundleid=fast_cart_obj.merchant_reference,
                                                 delivery_fee=fast_cart_obj.get_delivery_fee(),
                                                 cod_charge=0)

                unit_order_obj = UnitOrder.objects.create(order=order_obj,
                                                          product=fast_cart_obj.product,
                                                          quantity=fast_cart_obj.quantity,
                                                          price=fast_cart_obj.product.get_actual_price_for_customer(dealshub_user_obj))
                UnitOrderStatus.objects.create(unit_order=unit_order_obj)


                try:
                    custom_data = []
                    custom_data.append(CustomData(
                        content_type="product",
                        value=fast_cart_obj.product.now_price,
                        currency=fast_cart_obj.product.get_currency(),
                        content_name=fast_cart_obj.product.get_name(),
                        content_category=fast_cart_obj.product.get_category(),
                        contents=[Content(product_id=fast_cart_obj.product.get_product_id(), quantity=fast_cart_obj.quantity, item_price=fast_cart_obj.product.now_price)],
                    ))
                    calling_facebook_api(event_name="Purchase",user=fast_cart_obj.owner,request=request,custom_data=custom_data)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("PlaceOnlineOrderAPI: %s at %s", e, str(exc_tb.tb_lineno))
         
                # cart_obj points to None
                fast_cart_obj.shipping_address = None
                fast_cart_obj.voucher = None
                fast_cart_obj.additional_note = ""
                fast_cart_obj.to_pay = 0
                fast_cart_obj.merchant_reference = ""
                fast_cart_obj.payment_info = "{}"
                fast_cart_obj.product = None
                fast_cart_obj.save()

            # Trigger Email
            try:
                p1 = threading.Thread(target=send_order_confirmation_mail, args=(order_obj,))
                p1.start()
                website_group = order_obj.location_group.website_group.name
                unit_order_obj = UnitOrder.objects.filter(order=order_obj)[0]
                customer_name = order_obj.owner.first_name
                link = order_obj.location_group.website_group.link
                order_uuid = order_obj.uuid

                if website_group=="parajohn":
                    message = "Dear "+customer_name +", Thank you for shopping with "+ link +". Your order "+ link + "/orders/" + order_uuid +" has been confirmed & will be shipped soon."
                    p2 = threading.Thread(target=send_parajohn_order_status_sms, args=(unit_order_obj,message,))
                    p2.start()
                elif website_group in ["shopnesto", "shopnestokuwait", "shopnestobahrain"]:
                    message = "Dear "+customer_name +", Thank you for shopping with "+ link +". Your order "+ link + "/orders/" + order_uuid +" has been confirmed & will be shipped soon."
                    p2 = threading.Thread(target=send_wigme_order_status_sms, args=(unit_order_obj,message,))
                    p2.start()
                elif website_group=="daycart":
                    message = "Dear "+customer_name +", Thank you for shopping with "+ link +". Your order "+ link + "/orders/" + order_uuid +" has been confirmed & will be shipped soon."
                    p2 = threading.Thread(target=send_daycart_order_status_sms, args=(unit_order_obj,message,))
                    p2.start()
                elif website_group=="geepasuganda":
                    message = "Dear "+customer_name +", Thank you for shopping with "+ link +". Your order "+ link + "/orders/" + order_uuid +" has been confirmed & will be shipped soon."
                    p2 = threading.Thread(target=send_geepas_order_status_sms , args=(unit_order_obj,message,))
                    p2.start()
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

            if is_oc_user(request.user)==False:
                response['status'] = 403
                logger.warning("FetchPostaPlusTrackingAPI Restricted Access!")
                return Response(data=response)

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
            language_code = data.get("language","en")
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
            cart_details["moq"] = fast_cart_obj.product.moq
            cart_details["stock"] = fast_cart_obj.product.stock
            cart_details["allowedQty"] = fast_cart_obj.product.get_allowed_qty()
            cart_details["currency"] = fast_cart_obj.product.get_currency()
            cart_details["productName"] = fast_cart_obj.product.get_name(language_code)
            cart_details["productImageUrl"] = fast_cart_obj.product.get_display_image_url()
            cart_details["productUuid"] = fast_cart_obj.product.uuid
            cart_details["link"] = fast_cart_obj.product.url
            cart_details["brand"] = fast_cart_obj.product.get_brand(language_code)
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
            try:
                custom_data = []
                custom_data.append(CustomData(
                    content_type="product",
                    value=fast_cart_obj.product.now_price,
                    currency=fast_cart_obj.product.get_currency(),
                    content_name=fast_cart_obj.product.get_name(),
                    content_category=fast_cart_obj.product.get_category(),
                    contents=[Content(product_id=fast_cart_obj.product.get_product_id(), quantity=fast_cart_obj.quantity, item_price=fast_cart_obj.product.now_price)],
                ))
                calling_facebook_api(event_name="Purchase",user=fast_cart_obj.owner,request=request,custom_data=custom_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("FetchFastCartDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
         

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

                    GRN_information_dict = {} #GRN information grouped by seller sku

                    for product in GRN_products:
                        info = product.split(';')
                        temp_dict = {}
                        seller_sku = info[1]
                        temp_dict["seller_sku"] = seller_sku
                        temp_dict["location"] = info[2]
                        temp_dict["batch"] = info[3]
                        temp_dict["qty"] = info[4]
                        temp_dict["uom"] = info[5]
                        if seller_sku not in GRN_information_dict:
                            GRN_information_dict[seller_sku] = []
                        GRN_information_dict[seller_sku].append(temp_dict)

                    for unit_order_obj in unit_order_objs:
                        
                        unit_order_information = json.loads(unit_order_obj.order_information)
                        unit_order_information["final_billing_info"] = []

                        seller_sku = unit_order_obj.product.get_seller_sku()
                        grn_batch_wise_list = GRN_information_dict.get(seller_sku,None)

                        if grn_batch_wise_list == None:
                            temp_dict_default = {}
                            temp_dict_default["seller_sku"] = seller_sku
                            temp_dict_default["location"] = ""
                            temp_dict_default["batch"] = ""
                            temp_dict_default["qty"] = 0.0
                            temp_dict_default["uom"] = ""
                            temp_dict_default["from_holding"] = unit_order_information["intercompany_sales_info"]["from_holding"]
                            temp_dict_default["price"] = unit_order_information["intercompany_sales_info"]["price"]
                            unit_order_information["final_billing_info"].append(temp_dict_default)
                        
                        else:
                            for grn_info in grn_batch_wise_list:
                                grn_info["from_holding"] = unit_order_information["intercompany_sales_info"]["from_holding"]
                                grn_info["price"] = unit_order_information["intercompany_sales_info"]["price"]
                                unit_order_information["final_billing_info"].append(grn_info)
                        
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
                        order_information["refrence_id"] = order_obj.bundleid.replace("-","&#45;")
                        order_information["charges"] = get_all_the_charges(order_obj)
                        order_information["customer_id"] = order_obj.get_customer_id_for_final_sap_billing()
                        is_b2b = order_obj.location_group.is_b2b
                        order_information["is_b2b"] = is_b2b
                        if is_b2b==True:
                            order_information["street"] = json.loads(order_obj.shipping_address.address_lines)[1]
                            order_information["region"] = order_obj.shipping_address.state
                            order_information["telephone"] = order_obj.shipping_address.contact_number
                            order_information["email"] = order_obj.owner.email
                            b2b_user_obj = B2BUser.objects.get(username=order_obj.owner.username) 
                            order_information["trn"] = b2b_user_obj.vat_certificate_id

                        unit_order_information_list = []
                        seller_sku_list = []
                        for unit_order_obj in UnitOrder.objects.filter(order=order_obj):
                            seller_sku_list.append(unit_order_obj.product.get_seller_sku())
                            unit_order_final_billing_information = json.loads(unit_order_obj.order_information)["final_billing_info"]
                            
                            if unit_order_final_billing_information != []:
                                unit_order_information_list += unit_order_final_billing_information
                        
                        order_information["unit_order_information_list"] = unit_order_information_list

                        result = create_final_order(WIGME_COMPANY_CODE, order_information, seller_sku_list)
                        
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
                            for unit_order_obj in UnitOrder.objects.filter(order=order_obj):
                                set_order_status(unit_order_obj,"picked")
                        else:
                            order_obj.sap_status = "Failed"
                            try:
                                p1 = threading.Thread(target=notify_grn_error, args=(order_obj,))
                                p1.start()
                            except Exception as e:
                                exc_type, exc_obj, exc_tb = sys.exc_info()
                                logger.error("notify_grn_error: %s at %s", e, str(exc_tb.tb_lineno))

                        order_obj.sap_final_billing_info = json.dumps(result)
                        #order_obj.order_information = json.dumps(order_information)
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

            try:
                calling_facebook_api(event_name="CompleteRegistration",user=dealshub_user_obj,request=request,custom_data=None)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("UpdateUserNameAndEmailAPI: %s at %s", e, str(exc_tb.tb_lineno))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateUserNameAndEmailAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SendNewProductEmailNotificationAPI(APIView):

    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        response = {}
        response["status"] = 500

        try:
            data = request.data
            logger.info("SendNewProductEmailNotificationAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            dealshub_product_objs = DealsHubProduct.objects.filter(is_notified = False)
            location_group_pks = dealshub_product_objs.values_list("location_group",flat=True)
            location_group_objs = LocationGroup.objects.filter(pk__in = location_group_pks)
            
            for location_group_obj in location_group_objs:
                temp_dealshub_product_objs = dealshub_product_objs.filter(location_group=location_group_obj)
                location_group_name = location_group_obj.name
                #generate excel sheet
                product_list = []
                for temp_dealshub_product_obj in temp_dealshub_product_objs:
                    temp_dict = {
                        "Product Name": temp_dealshub_product_obj.product_name,
                        "Product ID": temp_dealshub_product_obj.get_product_id(),
                        "Brand": temp_dealshub_product_obj.get_brand(),
                        "Seller SKU": temp_dealshub_product_obj.get_seller_sku(),
                    }
                    product_list.append(temp_dict)
                    temp_dealshub_product_obj.is_notified = True
                    temp_dealshub_product_obj.save()

                filename = location_group_name + "-new-product.xlsx"
                filepath = os.path.join("files/csv/" + filename)
                sheet_name = "new-products-" + location_group_name
                df = pd.DataFrame(product_list)
                with pd.ExcelWriter('./'+filepath) as workbook:
                    df.to_excel(workbook, sheet_name=sheet_name,index=False)
                #trigger email
                try:
                    p1 = threading.Thread(target=notify_new_products_email, args =(filepath,location_group_obj))
                    p1.start()
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("SendNewProductEmailNotificationAPI: %s at %s", str(exc_tb.tb_lineno))

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SendNewProductEmailNotificationAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchB2BUserProfileAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response["status"] = 500

        try:
            data = request.data
            logger.info("FetchB2BUserProfileAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            b2b_user_obj = B2BUser.objects.get(username=request.user.username)

            response["fullName"] = b2b_user_obj.first_name
            response["contact_number"] = b2b_user_obj.contact_number
            response["emailId"] = b2b_user_obj.email
            response["companyName"] = b2b_user_obj.company_name
            response["vatCertificateId"] = b2b_user_obj.vat_certificate_id
            response["passportCopyId"] = b2b_user_obj.passport_copy_id
            response["tradeLicenseId"] = b2b_user_obj.trade_license_id

            response["vat_certificate"] = ""
            response["vat_certificate_type"] = "EMPTY"
            if b2b_user_obj.vat_certificate!=None and b2b_user_obj.vat_certificate!="":
                response["vat_certificate_type"] = "PDF"
                response["vat_certificate"] = b2b_user_obj.vat_certificate.url
            elif b2b_user_obj.vat_certificate_images.exists() > 0:
                response["vat_certificate_type"] = "IMG"
                temp_dict = []
                vat_certificate_image_objs = b2b_user_obj.vat_certificate_images.all()
                for vat_certificate_image_obj in vat_certificate_image_objs:
                    temp_dict2 = {}
                    temp_dict2["image_url"] = vat_certificate_image_obj.image.url
                    temp_dict2["pk"] = vat_certificate_image_obj.pk
                    temp_dict.append(temp_dict2)
                response["vat_certificate"] = temp_dict

            response["passport_copy"] = ""
            response["passport_copy_type"] = "EMPTY"
            if b2b_user_obj.passport_copy!=None and b2b_user_obj.passport_copy!="":
                response["passport_copy_type"] = "PDF"
                response["passport_copy"] = b2b_user_obj.passport_copy.url
            elif b2b_user_obj.passport_copy_images.exists() > 0 :
                response["passport_copy_type"] = "IMG"
                temp_dict = []
                passport_copy_image_objs = b2b_user_obj.passport_copy_images.all()
                for passport_copy_image_obj in passport_copy_image_objs:
                    temp_dict2 = {}
                    temp_dict2["image_url"] = passport_copy_image_obj.image.url
                    temp_dict2["pk"] = passport_copy_image_obj.pk
                    temp_dict.append(temp_dict2)
                response["passport_copy"] = temp_dict

            response["trade_license"] = ""
            response["trade_license_type"] = "EMPTY"
            if b2b_user_obj.trade_license!=None and b2b_user_obj.trade_license!="":
                response["trade_license_type"] = "PDF"
                response["trade_license"] = b2b_user_obj.trade_license.url
            elif b2b_user_obj.trade_license_images.exists() > 0:
                response["trade_license_type"] = "IMG"
                temp_dict = []
                trade_license_image_objs = b2b_user_obj.trade_license_images.all()
                for trade_license_image_obj in trade_license_image_objs:
                    temp_dict2 = {}
                    temp_dict2["image_url"] = trade_license_image_obj.image.url
                    temp_dict2["pk"] = trade_license_image_obj.pk
                    temp_dict.append(temp_dict2)
                response["trade_license"] = temp_dict

            response["vat_certificate_status"] = b2b_user_obj.vat_certificate_status
            response["passport_copy_status"] = b2b_user_obj.passport_copy_status
            response["trade_license_status"] = b2b_user_obj.trade_license_status
            response["vat_certificate_id"] = b2b_user_obj.vat_certificate_id

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchB2BUserProfileAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadB2BDocumentAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response["status"] = 500

        try:
            data = request.data
            logger.info("UploadB2BDocumentAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            vat_certificate_type = data["vat-certificate-type"]
            trade_license_type = data["trade-license-type"]
            passport_copy_type = data["passport-copy-type"]
            vat_certificate_id = data["vat-certificate-id"]
            trade_license_id = data["trade-license-id"]
            passport_copy_id = data["passport-copy-id"]
            b2b_user_obj = B2BUser.objects.get(username=request.user.username)

            if (b2b_user_obj.vat_certificate_id != vat_certificate_id and B2BUser.objects.filter(vat_certificate_id=vat_certificate_id).count()) or (b2b_user_obj.trade_license_id != trade_license_id and B2BUser.objects.filter(trade_license_id=trade_license_id).count()):
                response["status"] = 403
                response["message"] = "Vat Certificate number or Trade License number already exists!"
                logger.error("UploadB2BDocumentAPI: Vat Certificate number or Trade License number already exists!")
                return Response(data=response)

            if vat_certificate_type == "IMG":
                image_count = int(data.get("vat-certificate-image-count",0))
                for i in range(image_count):
                    image_obj = Image.objects.create(image = data["vat-certificate-image-" + str(i+1)])
                    b2b_user_obj.vat_certificate_images.add(image_obj)
                b2b_user_obj.vat_certificate = None
            elif vat_certificate_type == "PDF":
                if data["vat-certificate-document"] != "":
                    b2b_user_obj.vat_certificate = data["vat-certificate-document"]
                image_objs = b2b_user_obj.vat_certificate_images.all()
                for image_obj in image_objs:
                    image_obj.delete()

            if passport_copy_type == "IMG":
                image_count = int(data.get("passport-copy-image-count",0))
                for i in range(image_count):
                    image_obj = Image.objects.create(image = data["passport-copy-image-" + str(i+1)])
                    b2b_user_obj.passport_copy_images.add(image_obj)
                b2b_user_obj.passport_copy = None
            elif passport_copy_type == "PDF":
                if data["passport-copy-document"] != "":
                    b2b_user_obj.passport_copy = data["passport-copy-document"]
                image_objs = b2b_user_obj.passport_copy_images.all()
                for image_obj in image_objs:
                    image_obj.delete()

            if trade_license_type == "IMG":
                image_count = int(data.get("trade-license-image-count",0))
                for i in range(image_count):
                    image_obj = Image.objects.create(image = data["trade-license-image-" + str(i+1)])
                    b2b_user_obj.trade_license_images.add(image_obj)
                b2b_user_obj.trade_license = None
            elif trade_license_type == "PDF":
                if data["trade-license-document"] != "":
                    b2b_user_obj.trade_license = data["trade-license-document"]
                image_objs = b2b_user_obj.trade_license_images.all()
                for image_obj in image_objs:
                    image_obj.delete()

            b2b_user_obj.vat_certificate_id = vat_certificate_id
            b2b_user_obj.trade_license_id = trade_license_id
            b2b_user_obj.passport_copy_id = passport_copy_id
            b2b_user_obj.save()
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadB2BDocumentAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UpdateB2BCustomerDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response["status"] = 500

        try:
            data = request.data
            logger.info("UpdateB2BCustomerDetailsAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            full_name = data["fullName"]
            email = data["emailId"]
            company_name = data["companyName"]

            b2b_user_obj = B2BUser.objects.get(username=request.user.username)
            b2b_user_obj.first_name = full_name
            b2b_user_obj.email = email
            b2b_user_obj.company_name = company_name
            b2b_user_obj.save()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateB2BCustomerDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchSEODataAPI(APIView):

    authentication_classes = (CsrfExemptSessionAuthentication,) 
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchSEODataAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            response["seo_title"] = location_group_obj.seo_title
            response["seo_long_description"] = location_group_obj.seo_long_description
            response["seo_short_description"] = location_group_obj.seo_short_description
            response["seo_google_meta"] = location_group_obj.seo_google_meta
            response["seo_google_meta_title"] = location_group_obj.seo_google_meta_title
            response['status'] = 200    

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSEODataAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


FetchShippingAddressList = FetchShippingAddressListAPI.as_view()

FetchBillingAddressList = FetchBillingAddressListAPI.as_view()

EditShippingAddress = EditShippingAddressAPI.as_view()

CreateShippingAddress = CreateShippingAddressAPI.as_view()

CreateBillingAddress = CreateBillingAddressAPI.as_view()

CreateOfflineShippingAddress = CreateOfflineShippingAddressAPI.as_view()

CreateOfflineBillingAddress = CreateOfflineBillingAddressAPI.as_view()

DeleteShippingAddress = DeleteShippingAddressAPI.as_view()

AddToCart = AddToCartAPI.as_view()

AddToFastCart = AddToFastCartAPI.as_view()

AddToOfflineCart = AddToOfflineCartAPI.as_view()

FetchCartDetails = FetchCartDetailsAPI.as_view()

CreateUnitOrderCancellationRequest = CreateUnitOrderCancellationRequestAPI.as_view()

CreateOrderCancellationRequest = CreateOrderCancellationRequestAPI.as_view()

FetchOfflineCartDetails = FetchOfflineCartDetailsAPI.as_view()

UpdateCartDetails = UpdateCartDetailsAPI.as_view()

UpdateOfflineCartDetails = UpdateOfflineCartDetailsAPI.as_view()

RemoveFromCart = RemoveFromCartAPI.as_view()

SelectAddress = SelectAddressAPI.as_view()

SelectBillingAddress = SelectBillingAddressAPI.as_view()

SelectOfflineAddress = SelectOfflineAddressAPI.as_view()

SelectPaymentMode = SelectPaymentModeAPI.as_view()

FetchActiveOrderDetails = FetchActiveOrderDetailsAPI.as_view()

PlaceOrderRequest = PlaceOrderRequestAPI.as_view()

DeleteOrderRequest = DeleteOrderRequestAPI.as_view()

UpdateUnitOrderRequestAdmin = UpdateUnitOrderRequestAdminAPI.as_view()

SetOrderChequeImage = SetOrderChequeImageAPI.as_view()

PlaceInquiry = PlaceInquiryAPI.as_view()

PlaceB2BOnlineOrder = PlaceB2BOnlineOrderAPI.as_view()

ProcessOrderRequest = ProcessOrderRequestAPI.as_view()

PlaceOrder = PlaceOrderAPI.as_view()

PlaceOfflineOrder = PlaceOfflineOrderAPI.as_view()

CancelOrder = CancelOrderAPI.as_view()

FetchOrderRequestList = FetchOrderRequestListAPI.as_view()

FetchOrderList = FetchOrderListAPI.as_view()

FetchOrderListAdmin = FetchOrderListAdminAPI.as_view()

FetchOrderDetails = FetchOrderDetailsAPI.as_view()

FetchOrderVersionDetails = FetchOrderVersionDetailsAPI.as_view()

CreateOfflineCustomer = CreateOfflineCustomerAPI.as_view()

UpdateOfflineUserProfile = UpdateOfflineUserProfileAPI.as_view()

SearchCustomerAutocomplete = SearchCustomerAutocompleteAPI.as_view()

FetchOfflineUserProfile = FetchOfflineUserProfileAPI.as_view()

FetchUserProfile = FetchUserProfileAPI.as_view()

UpdateUserProfile = UpdateUserProfileAPI.as_view()

FetchCustomerList = FetchCustomerListAPI.as_view()

FetchCustomerDetails = FetchCustomerDetailsAPI.as_view()

UpdateB2BCustomerStatus = UpdateB2BCustomerStatusAPI.as_view()

DeleteB2BDocumentImage = DeleteB2BDocumentImageAPI.as_view()

DeleteB2BDocument = DeleteB2BDocumentAPI.as_view()

FetchCustomerOrders = FetchCustomerOrdersAPI.as_view()

FetchCustomerOrderRequests = FetchCustomerOrderRequestsAPI.as_view()

FetchTokenRequestParameters = FetchTokenRequestParametersAPI.as_view()

MakePurchaseRequest = MakePurchaseRequestAPI.as_view()

PaymentTransaction = PaymentTransactionAPI.as_view()

PaymentNotification = PaymentNotificationAPI.as_view()

# FetchInstallmentPlans = FetchInstallmentPlansAPI.as_view()

# MakePurchaseRequestInstallment = MakePurchaseRequestInstallmentAPI.as_view()

CalculateSignature = CalculateSignatureAPI.as_view()

ContactUsSendEmail = ContactUsSendEmailAPI.as_view()

FetchAccountStatusB2BUser = FetchAccountStatusB2BUserAPI.as_view()

SendB2BOTPSMSLogin = SendB2BOTPSMSLoginAPI.as_view()

SendB2BOTPSMSSignUp = SendB2BOTPSMSSignUpAPI.as_view()

SignUpCompletion = SignUpCompletionAPI.as_view()

SendOTPSMSLogin = SendOTPSMSLoginAPI.as_view()

VerifyB2BOTPSMS = VerifyB2BOTPSMSAPI.as_view()

VerifyOTPSMSLogin = VerifyOTPSMSLoginAPI.as_view()

CheckUserPinSet = CheckUserPinSetAPI.as_view()

SetLoginPin = SetLoginPinAPI.as_view()

VerifyLoginPin = VerifyLoginPinAPI.as_view()

ForgotLoginPin = ForgotLoginPinAPI.as_view()

UpdateUserEmail = UpdateUserEmailAPI.as_view()

AddReview = AddReviewAPI.as_view()

AddFakeReviewAdmin = AddFakeReviewAdminAPI.as_view()

UpdateReviewAdmin = UpdateReviewAdminAPI.as_view()

BulkUploadFakeReviewAdmin = BulkUploadFakeReviewAdminAPI.as_view()

AddRating = AddRatingAPI.as_view()

UpdateRating = UpdateRatingAPI.as_view()

AddAdminComment = AddAdminCommentAPI.as_view()

UpdateAdminComment = UpdateAdminCommentAPI.as_view()

AddUpvote = AddUpvoteAPI.as_view()

DeleteUpvote = DeleteUpvoteAPI.as_view()

FetchReview = FetchReviewAPI.as_view()

FetchReviewsAdmin = FetchReviewsAdminAPI.as_view()

FetchProductReviews = FetchProductReviewsAPI.as_view()

DeleteUserReviewImage = DeleteUserReviewImageAPI.as_view()

DeleteAdminReviewImage = DeleteAdminReviewImageAPI.as_view()

DeleteUserReview = DeleteUserReviewAPI.as_view()

HideReviewAdmin = HideReviewAdminAPI.as_view()

UpdateReviewPublishStatus = UpdateReviewPublishStatusAPI.as_view()

FetchSalesExecutiveAnalysis = FetchSalesExecutiveAnalysisAPI.as_view()

FetchOrderSalesAnalytics = FetchOrderSalesAnalyticsAPI.as_view()

FetchOrderRequestsForWarehouseManager = FetchOrderRequestsForWarehouseManagerAPI.as_view()

FetchFilteredOrderAnalytics = FetchFilteredOrderAnalyticsAPI.as_view()

FetchOrdersForWarehouseManager = FetchOrdersForWarehouseManagerAPI.as_view()

FetchShippingMethod = FetchShippingMethodAPI.as_view()

SetShippingMethod = SetShippingMethodAPI.as_view()

ResendSAPOrder = ResendSAPOrderAPI.as_view()

UpdateManualOrder = UpdateManualOrderAPI.as_view()

SetOrdersStatus = SetOrdersStatusAPI.as_view()

SetOrdersStatusBulk = SetOrdersStatusBulkAPI.as_view()

UpdateOrderStatus = UpdateOrderStatusAPI.as_view()

BulkUpdateOrderStatus = BulkUpdateOrderStatusAPI.as_view()

SetCallStatus = SetCallStatusAPI.as_view()

CancelOrders = CancelOrdersAPI.as_view()

ApproveCancellationRequest = ApproveCancellationRequestAPI.as_view()

RejectCancellationRequest = RejectCancellationRequestAPI.as_view()

UpdateCancellationRequestRefundStatus = UpdateCancellationRequestRefundStatusAPI.as_view()

FetchOCSalesPersons = FetchOCSalesPersonsAPI.as_view()

DownloadOrders = DownloadOrdersAPI.as_view()

UploadOrders = UploadOrdersAPI.as_view()

ApplyVoucherCode = ApplyVoucherCodeAPI.as_view()

RemoveVoucherCode = RemoveVoucherCodeAPI.as_view()

ApplyOfflineVoucherCode = ApplyOfflineVoucherCodeAPI.as_view()

RemoveOfflineVoucherCode = RemoveOfflineVoucherCodeAPI.as_view()

AddOfflineReferenceMedium = AddOfflineReferenceMediumAPI.as_view()

AddOnlineAdditionalNote = AddOnlineAdditionalNoteAPI.as_view()

AddOfflineAdditionalNote = AddOfflineAdditionalNoteAPI.as_view()

FetchOrderAnalyticsParams = FetchOrderAnalyticsParamsAPI.as_view()

PlaceDaycartOnlineOrder = PlaceDaycartOnlineOrderAPI.as_view()

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

SendNewProductEmailNotification = SendNewProductEmailNotificationAPI.as_view()

FetchB2BUserProfile = FetchB2BUserProfileAPI.as_view()

UploadB2BDocument = UploadB2BDocumentAPI.as_view()

UpdateB2BCustomerDetails = UpdateB2BCustomerDetailsAPI.as_view()

FetchSEOData = FetchSEODataAPI.as_view()
