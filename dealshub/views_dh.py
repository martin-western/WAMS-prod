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
from dealshub.serializers import UserSerializer, UserSerializerWithToken
from dealshub.views_oc import * 

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


class FetchCustomerListAPI(APIView):

    permission_classes = [AllowAny]

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
            response["total_customers"] = dealshub_user_objs.count()
            paginator = Paginator(dealshub_user_objs, 20)
            dealshub_user_objs = paginator.page(page)

            customer_list = []
            for dealshub_user_obj in dealshub_user_objs:
                try:
                    temp_dict = {}
                    if dealshub_user_obj.first_name=="":
                        temp_dict["name"] = dealshub_user_obj.contact_number
                    else:
                        temp_dict["name"] = dealshub_user_obj.first_name + " " + dealshub_user_obj.last_name
                    temp_dict["dateCreated"] = str(timezone.localtime(dealshub_user_obj.date_created).strftime("%d %b, %Y"))
                    temp_dict["emailId"] = dealshub_user_obj.email
                    temp_dict["contactNumber"] = dealshub_user_obj.contact_number
                    temp_dict["username"] = dealshub_user_obj.username
                    temp_dict["is_cart_empty"] = not UnitCart.objects.filter(cart__owner=dealshub_user_obj).exists()
                    temp_dict["is_feedback_available"] = Review.objects.filter(dealshub_user=dealshub_user_obj).exists()
                    customer_list.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchCustomerListAPI: %s at %s", e, str(exc_tb.tb_lineno))

            is_available = True
            
            if int(paginator.num_pages) == int(page):
                is_available = False

            response["is_available"] = is_available

            response["customerList"] = customer_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchCustomerListAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchCustomerDetailsAPI(APIView):

    permission_classes = [AllowAny]

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

            
            uuid_list = []
            for unit_cart_obj in UnitCart.objects.filter(cart__owner=dealshub_user_obj):
                uuid_list.append(unit_cart_obj.product.product.uuid)

            review_objs = Review.objects.filter(dealshub_user=dealshub_user_obj)
            for review_obj in review_objs:
                uuid_list.append(review_obj.product.product.uuid)          

            productInfo = fetch_bulk_product_info(uuid_list)

            unit_cart_list = []
            for unit_cart_obj in UnitCart.objects.filter(cart__owner=dealshub_user_obj):
                temp_dict2 = {}
                temp_dict2["uuid"] = unit_cart_obj.uuid
                temp_dict2["quantity"] = unit_cart_obj.quantity
                temp_dict2["price"] = unit_cart_obj.price
                temp_dict2["currency"] = unit_cart_obj.currency        
                temp_dict2["productName"] = productInfo[unit_cart_obj.product.product.uuid]["productName"]
                temp_dict2["productImageUrl"] = productInfo[unit_cart_obj.product.product.uuid]["productImageUrl"]
                unit_cart_list.append(temp_dict2)

            review_list = []
            for review_obj in review_objs:
                try:
                    temp_dict2 = {}
                    temp_dict2["uuid"] = review_obj.uuid
                    temp_dict2["sellerSku"] = productInfo[review_obj.product.product.uuid]["sellerSku"]
                    temp_dict2["productImageUrl"] = productInfo[review_obj.product.product.uuid]["productImageUrl"]
                    temp_dict2["rating"] = review_obj.rating
                    temp_dict2["isReview"] = False
                    if review_obj.content!=None:
                        temp_dict2["isReview"] = True
                        temp_dict2["subject"] = review_obj.content.subject
                        temp_dict2["content"] = review_obj.content.content
                        temp_dict2["isReply"] = False
                        if review_obj.content.admin_comment!=None:
                            temp_dict2["isReply"] = True
                            temp_dict2["username"] = review_obj.content.admin_comment.username
                            temp_dict2["displayName"] = review_obj.content.admin_comment.display_name
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

    permission_classes = [AllowAny]

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

            order_objs = Order.objects.filter(owner=dealshub_user_obj, order_type="placedorder").order_by('-pk')
            
            total_orders = order_objs.count()
            paginator = Paginator(order_objs, 10)
            order_objs = paginator.page(page)

            uuid_list = []
            for order_obj in order_objs:
                for unit_order_obj in UnitOrder.objects.filter(order=order_obj):
                    uuid_list.append(unit_order_obj.product.product.uuid)

            productInfo = fetch_bulk_product_info(uuid_list)

            order_list = []
            for order_obj in order_objs:
                total_billing = 0
                temp_dict = {}
                temp_dict["datePlaced"] = str(timezone.localtime(order_obj.order_placed_date).strftime("%d %b, %Y"))
                temp_dict["timePlaced"] = str(timezone.localtime(order_obj.order_placed_date).strftime("%I:%M %p"))
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
                    temp_dict2["currency"] = unit_order_obj.currency
                    temp_dict2["productName"] = productInfo[unit_order_obj.product.product.uuid]["productName"]
                    temp_dict2["productImageUrl"] = productInfo[unit_order_obj.product.product.uuid]["productImageUrl"]
                    unit_order_list.append(temp_dict2)
                    total_billing += float(unit_order_obj.quantity)*unit_order_obj.price
                temp_dict["totalBilling"] = str(total_billing) + " AED"
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

            website_group_name = data["websiteGroupName"]
            return_url = data["returnUrl"]
            order_uuid = data["orderUuid"]

            payment_credentials = fetch_company_credentials(website_group_name)

            service_command = "TOKENIZATION"
            access_code = payment_credentials["access_code"]
            merchant_identifier = payment_credentials["merchant_identifier"]
            merchant_reference = str(uuid.uuid4())
            language = "en"
            PASS = payment_credentials["PASS"]

            order_obj = Order.objects.get(uuid=order_uuid)
            order_obj.merchant_reference = merchant_reference
            order_obj.save()

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

            website_group_name = data["websiteGroupName"]
            return_url = data["returnUrl"]
            merchant_reference = data["merchant_reference"]
            token_name = data["token_name"]
            #amount = data["amount"]
            #currency = data["currency"]
            currency = "AED"

            customer_ip = ""
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                customer_ip = x_forwarded_for.split(',')[0]
            else:
                customer_ip = request.META.get('REMOTE_ADDR')

            payment_credentials = fetch_company_credentials(website_group_name)

            access_code = payment_credentials["access_code"]
            merchant_identifier = payment_credentials["merchant_identifier"]
            language = "en"
            PASS = payment_credentials["PASS"]

            command = "PURCHASE"

            order_obj = Order.objects.get(merchant_reference=merchant_reference)

            amount = order_obj.to_pay
            
            dealshub_user_obj = order_obj.owner

            customer_email = dealshub_user_obj.email

            amount = str(int(float(amount)*100))

            #amount = "100"

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

            order_obj.payment_info = json.dumps(payment_response)
            order_obj.save()


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
            #PASS = "$2y$10$tGrWU3XZ0"
            # try:
            #     api_access = "5a72db78-b0f2-41ff-b09e-6af02c5b4c77"
            #     organization_name = data["organizationName"]
            #     r = requests.post(url=OMNYCOMM_IP+"/fetch-organization-credentials/", data={"organization_name":organization_name, "api_access":api_access}, verify=False)
            #     payment_credentials = json.loads(r.content)["credentials"]
            #     PASS = payment_credentials["PASS"]
            # except Exception as e:
            #     exc_type, exc_obj, exc_tb = sys.exc_info()
            #     logger.error("PaymentTransactionAPI: %s at %s", e, str(exc_tb.tb_lineno))


            calc_signature = calc_response_signature(PASS, data)
            if calc_signature!=data["signature"]:
                logger.error("PaymentTransactionAPI: SIGNATURE DOES NOT MATCH!")
                return Response(data=response)

            order_obj = Order.objects.get(merchant_reference=merchant_reference)

            if status=="14":
                order_obj.payment_status = "paid"
                order_obj.payment_info = json.dumps(data)
                order_obj.payment_mode = data.get("payment_option", "NA")
                order_obj.order_placed_date = timezone.now()
                order_obj.save()

                # Place Order

                dealshub_user = order_obj.owner
                cart_obj = Cart.objects.get(owner=dealshub_user)

                # Unit Cart gets converted to Unit Order
                unit_cart_objs = UnitCart.objects.filter(cart_type="active", cart__owner=dealshub_user)
                for unit_cart_obj in unit_cart_objs:
                    unit_order_obj = UnitOrder.objects.create(order=order_obj, 
                                                              product=unit_cart_obj.product, 
                                                              quantity=unit_cart_obj.quantity, 
                                                              price=unit_cart_obj.price, 
                                                              currency=unit_cart_obj.currency)
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
                cart_obj.order = None
                cart_obj.save()
                order_obj.order_type = "placedorder"
                order_obj.save()

                # Refresh Stock
                refresh_stock(order_obj)
            else:
                order_obj.payment_status = "failed"
                order_obj.payment_info = json.dumps(data)
                order_obj.save()
            
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


class FetchInstallmentPlansAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data

            logger.info("FetchInstallmentPlansAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            website_group_name = data["websiteGroupName"]
            currency = "AED"

            payment_credentials = fetch_company_credentials(website_group_name)

            access_code = payment_credentials["access_code"]
            merchant_identifier = payment_credentials["merchant_identifier"]
            language = "en"
            PASS = payment_credentials["PASS"]

            query_command = "GET_INSTALLMENTS_PLANS"

            order_obj = Cart.objects.get(owner__username=request.user.username).order

            amount = order_obj.to_pay
            
            amount = str(int(float(amount)*100))

            request_data = {
                "query_command":query_command,
                "access_code":access_code,
                "merchant_identifier":merchant_identifier,
                "amount":amount,
                "currency":currency,
                "language":language
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
            installment_plans = json.loads(r.content)

            response["installmentPlans"] = installment_plans
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchInstallmentPlansAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class MakePurchaseRequestInstallmentAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data

            logger.info("MakePurchaseRequestInstallmentAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            website_group_name = data["websiteGroupName"]
            return_url = data["returnUrl"]
            merchant_reference = data["merchant_reference"]
            token_name = data["token_name"]
            issuer_code = data["issuer_code"]
            plan_code = data["plan_code"]
            #amount = data["amount"]
            #currency = data["currency"]
            currency = "AED"
            installments = "HOSTED"

            customer_ip = ""
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                customer_ip = x_forwarded_for.split(',')[0]
            else:
                customer_ip = request.META.get('REMOTE_ADDR')

            payment_credentials = fetch_company_credentials(website_group_name)

            access_code = payment_credentials["access_code"]
            merchant_identifier = payment_credentials["merchant_identifier"]
            language = "en"
            PASS = payment_credentials["PASS"]

            command = "PURCHASE"

            order_obj = Order.objects.get(merchant_reference=merchant_reference)

            amount = order_obj.to_pay
            
            dealshub_user_obj = order_obj.owner

            customer_email = dealshub_user_obj.email

            amount = str(int(float(amount)*100))

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
                "issuer_code":issuer_code,
                "plan_code":plan_code,
                "installments":installments,
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

            order_obj.payment_info = json.dumps(payment_response)
            order_obj.save()


            response["paymentResponse"] = payment_response
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("MakePurchaseRequestInstallmentAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


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

            # Trigger Email
            try:
                p1 = threading.Thread(target=contact_us_send_email, args=(your_email,message,))
                p1.start()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("ContactUsSendEmail: %s at %s", e, str(exc_tb.tb_lineno))

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ContactUsSendEmailAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SendOTPSMSAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("SendOTPSMSAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)
            
            contact_number = data["contactNumber"]

            digits = "0123456789"
            OTP = "" 
            for i in range(6) : 
                OTP += digits[int(math.floor(random.random()*10))]

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            dealshub_user_obj.verification_code = OTP

            if dealshub_user_obj.contact_number!=contact_number:
                dealshub_user_obj.contact_number = contact_number
                dealshub_user_obj.contact_verified = False

            dealshub_user_obj.save()

            message = "OTP is " + OTP

            # Trigger SMS
            url = "http://mshastra.com/sendurlcomma.aspx?user=20087732&pwd=Western@13468&senderid=WIGME&mobileno="+contact_number+"&msgtext="+message+"&priority=High&CountryCode=ALL"
            #url = "http://mshastra.com/sendurlcomma.aspx?user=20076835&pwd=nesto@online&senderid=NESTO&mobileno="+contact_number+"&msgtext="+message+"&priority=High&CountryCode=ALL"
            r = requests.get(url)

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SendOTPSMSAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class VerifyOTPSMSAPI(APIView):

    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("VerifyOTPSMSAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)
            
            otp = data["otp"]

            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)
            verified = False
            if dealshub_user_obj.verification_code==otp:
                verified = True
                dealshub_user_obj.contact_verified = True
                dealshub_user_obj.save()

            response["verified"] = verified
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("VerifyOTPSMSAPI: %s at %s", e, str(exc_tb.tb_lineno))

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
            website_group_name = data["websiteGroupName"].lower()

            digits = "0123456789"
            OTP = "" 
            for i in range(6) : 
                OTP += digits[int(math.floor(random.random()*10))]

            if DealsHubUser.objects.filter(username=contact_number+"-"+website_group_name).exists()==False:
                dealshub_user_obj = DealsHubUser.objects.create(username=contact_number+"-"+website_group_name, contact_number=contact_number, website_group=website_group_name)
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
            contact_number = "971"+contact_number
            url = "http://mshastra.com/sendurlcomma.aspx?user=20087732&pwd=Western@13468&senderid=WIGME&mobileno="+contact_number+"&msgtext="+message+"&priority=High&CountryCode=ALL"
            #url = "http://mshastra.com/sendurlcomma.aspx?user=20076835&pwd=nesto@online&senderid=NESTO&mobileno="+contact_number+"&msgtext="+message+"&priority=High&CountryCode=ALL"
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
            website_group_name = data["websiteGroupName"].lower()

            dealshub_user_obj = DealsHubUser.objects.get(username=contact_number+"-"+website_group_name)
            
            credentials = {
                "username": contact_number+"-"+website_group_name,
                "password": otp
            }

            verified = False
            if dealshub_user_obj.verification_code==otp:
                r = requests.post(url=OMNYCOMM_IP+"/token-auth/", data=credentials, verify=False)
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

            if UnitOrder.objects.filter(product__product__uuid=product_code,order__owner=dealshub_user_obj).exists():
                review_obj, created = Review.objects.get_or_create(dealshub_user = dealshub_user_obj, product__product__uuid = product_code)
                review_obj.rating = rating
                review_content_obj = review_obj.content
                if review_content_obj is None:
                    review_content_obj = ReviewContent.objects.create(subject= subject, content = content)
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

            if UnitOrder.objects.filter(product__product__uuid=product_code,order__owner=dealshub_user_obj).exists():
                review_obj = Review.objects.create(dealshub_user = dealshub_user_obj, product__product__uuid = product_code, rating = rating)
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
            new_rating = int(data["rating"])

            review_obj = Review.objects.get(uuid=uuid)
            dealshub_user_obj = DealsHubUser.objects.get(username=request.user.username)

            if review_obj.dealshub_user == dealshub_user_obj:
                review_obj.rating = new_rating
                review_obj.save()
                response["status"] = 200
            else:
                response["status"] = 403

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateRatingAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddAdminCommentAPI(APIView):
    permission_classes = [AllowAny]
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

            if review_obj.content==None:
                response["status"] = 403
                return Response(data=response)

            admin_comment_obj = None
            if review_obj.content.admin_comment!=None:
                admin_comment_obj = review_obj.content.admin_comment
                admin_comment_obj.comment = comment
                admin_comment_obj.save()
            else:
                admin_comment_obj = AdminReviewComment.objects.create(username = username,display_name = display_name,comment = comment)
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
    permission_classes = [AllowAny]
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
                "display_name" : str(admin_comment_obj.display_name),
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
            review_objs = Review.objects.filter(product__product__uuid=product_code)
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
                        "display_name" : str(admin_comment_obj.display_name),
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

                if UnitOrder.objects.filter(product__product__uuid=product_code, order__owner__username=request.user.username).exists():
                    is_product_purchased = True

                if Review.objects.filter(product__product__uuid=product_code, dealshub_user__username=request.user.username).exists():
                    is_user_reviewed = True
                    review_obj = Review.objects.get(product__product__uuid=product_code, dealshub_user__username=request.user.username)
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
