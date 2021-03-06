from dealshub.models import *
from dealshub.core_utils import *
from WAMSApp.sap.utils_SAP_Integration import *
import datetime
from django.utils import timezone

import hashlib
import random
import sys
import logging
import os
import json
import requests
import xlsxwriter
from dealshub.constants import *
from django.core.mail import send_mail, get_connection
from django.core.mail import EmailMultiAlternatives
from django.core.mail import EmailMessage
from django.template import loader
import threading
from WAMSApp.utils import fetch_refresh_stock
from WAMSApp.sap.utils_SAP_Integration import *

import time
from facebook_business.adobjects.serverside.action_source import ActionSource
from facebook_business.adobjects.serverside.content import Content
from facebook_business.adobjects.serverside.custom_data import CustomData
from facebook_business.adobjects.serverside.delivery_category import DeliveryCategory
from facebook_business.adobjects.serverside.event import Event
from facebook_business.adobjects.serverside.event_request import EventRequest
from facebook_business.adobjects.serverside.gender import Gender
from facebook_business.adobjects.serverside.user_data import UserData
from facebook_business.api import FacebookAdsApi
import africastalking

logger = logging.getLogger(__name__)


def convert_to_datetime(date_str):
    date_str = date_str[:-1] + "+0400"
    return date_str
    #return datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

def get_promotional_price(product_obj):
    dealshub_product_obj = DealsHubProduct.objects.get(product=product_obj)
    return dealshub_product_obj.promotional_price

def get_actual_price(dealshub_product_obj):
    if dealshub_product_obj.promotion==None:
        return dealshub_product_obj.now_price
    if check_valid_promotion(dealshub_product_obj.promotion):
        return dealshub_product_obj.promotional_price
    return dealshub_product_obj.now_price

def get_product_promotion_details(dealshub_product_obj):
    data = {}
    if dealshub_product_obj.promotion!=None and check_valid_promotion(dealshub_product_obj.promotion):
        data["start_time"] = str(dealshub_product_obj.promotion.start_time)[:19]
        data["end_time"] = str(dealshub_product_obj.promotion.end_time)[:19]
        now_time = datetime.datetime.now()
        total_seconds = (timezone.localtime(dealshub_product_obj.promotion.end_time).replace(tzinfo=None) - now_time).total_seconds()
        data["remaining_time"] = {
            "days": int(total_seconds/(3600*24)),
            "hours": int(total_seconds/3600)%24,
            "minutes": int(total_seconds/60)%60,
            "seconds": int(total_seconds)%60
        }
        data["promotion_tag"] = str(dealshub_product_obj.promotion.promotion_tag)
    else:
        if dealshub_product_obj.promotion != None or dealshub_product_obj.is_promotional == True:    
            dealshub_product_obj.promotion = None
            dealshub_product_obj.is_promotional = False
            dealshub_product_obj.save()
        data["remaining_time"] = {}
        data["start_time"] = None
        data["end_time"] = None
        data["promotion_tag"] = None
    data["is_promotional"] = dealshub_product_obj.promotion!=None
    data["product_is_promotional"] = dealshub_product_obj.is_promotional
    return data

def calc_response_signature(PASS, data):
    try:
        keys = list(data.keys())
        keys.sort()
        signature_string = [PASS]
        for key in keys:
            if key not in ["signature"]:
                signature_string.append(key+"="+data[key])
        signature_string.append(PASS)

        signature_string = "".join(signature_string)
        signature = hashlib.sha256(signature_string.encode('utf-8')).hexdigest()
        return signature
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("calc_response_signature: %s at %s", e, str(exc_tb.tb_lineno))
        return ""


def set_shipping_method(unit_order_obj, shipping_method):

    if unit_order_obj.current_status_admin in ["pending", "approved"]:
        if unit_order_obj.shipping_method != shipping_method:
            unit_order_obj.shipping_method = shipping_method
        if unit_order_obj.current_status_admin=="pending":
            unit_order_obj.current_status_admin = "approved"
            UnitOrderStatus.objects.create(unit_order=unit_order_obj, status="ordered", status_admin="approved")
        unit_order_obj.save()

def set_order_status(unit_order_obj, order_status):
    if unit_order_obj.current_status_admin=="approved" and order_status in ["picked"]:
        unit_order_obj.current_status = "shipped"
        unit_order_obj.current_status_admin = order_status
        unit_order_obj.save()
        UnitOrderStatus.objects.create(unit_order=unit_order_obj, status="ordered", status_admin=order_status)
        return
    
    if unit_order_obj.current_status_admin=="picked" and order_status in ["dispatched"]:
        unit_order_obj.current_status = "intransit"
        unit_order_obj.current_status_admin = order_status
        unit_order_obj.save()
        UnitOrderStatus.objects.create(unit_order=unit_order_obj, status="shipped", status_admin=order_status)
        # Trigger Email
        try:
            p1 = threading.Thread(target=send_order_dispatch_mail, args=(unit_order_obj,))
            p1.start()
            website_group = unit_order_obj.order.location_group.website_group.name
            order_uuid = unit_order_obj.order.uuid
            link = order_obj.location_group.website_group.link

            if website_group=="parajohn":
                message = "Your Order "+ link + "/orders/" + order_uuid +" has been dispatched. Expected delivery within 2 days."
                p2 = threading.Thread(target=send_parajohn_order_status_sms, args=(unit_order_obj,message,))
                p2.start()
            elif website_group=="shopnesto":
                message = "Your Order "+ link + "/orders/" + order_uuid +" has been dispatched. Expected delivery within 2 days."
                p2 = threading.Thread(target=send_wigme_order_status_sms, args=(unit_order_obj,message,))
                p2.start()
            elif website_group=="geepasuganda":
                message = "Your Order "+ link + "/orders/" + order_uuid +" has been dispatched. Expected delivery within 2 days."
                p2 = threading.Thread(target=send_geepas_order_status_sms , args=(unit_order_obj,message,))
                p2.start()
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("set_order_status: %s at %s", e, str(exc_tb.tb_lineno))
        return

    if unit_order_obj.current_status_admin=="dispatched" and order_status in ["delivered", "delivery failed"]:
        unit_order_obj.current_status_admin = order_status
        status = ""
        if order_status=="delivered":
            unit_order_obj.current_status = "delivered"
            status = "delivered"
        elif order_status=="delivery failed":
            status = "intransit"
        unit_order_obj.save()
        UnitOrderStatus.objects.create(unit_order=unit_order_obj, status=status, status_admin=order_status)

        # Trigger Email
        if order_status=="delivered":
            try:
                p1 = threading.Thread(target=send_order_delivered_mail, args=(unit_order_obj,))
                p1.start()
                website_group = unit_order_obj.order.location_group.website_group.name
                link = unit_order_obj.order.location_group.website_group.link
                order_uuid = unit_order_obj.order.uuid
                
                if website_group=="parajohn":
                    message = "Your Order "+ link + "/orders/" + order_uuid +" has been delivered. We???d love to hear about your shopping experience. Let us know at "+ link
                    p2 = threading.Thread(target=send_parajohn_order_status_sms, args=(unit_order_obj,message,))
                    p2.start()
                elif website_group=="shopnesto":
                    message = "Your Order "+ link + "/orders/" + order_uuid +" has been delivered. We???d love to hear about your shopping experience. Let us know at "+ link
                    p2 = threading.Thread(target=send_wigme_order_status_sms , args=(unit_order_obj,message,))
                    p2.start()
                elif website_group=="geepasuganda":
                    message = "Your Order "+ link + "/orders/" + order_uuid +" has been delivered. We???d love to hear about your shopping experience. Let us know at "+ link
                    p2 = threading.Thread(target=send_geepas_order_status_sms , args=(unit_order_obj,message,))
                    p2.start()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("set_order_status: %s at %s", e, str(exc_tb.tb_lineno))
        
        elif order_status=="delivery failed":
            try:
                p1 = threading.Thread(target=send_order_delivery_failed_mail, args=(unit_order_obj,))
                p1.start()
                website_group = unit_order_obj.order.location_group.website_group.name
                order_uuid = unit_order_obj.order.uuid
                link = unit_order_obj.order.location_group.website_group.link
                
                if website_group=="parajohn":
                    message = "Your Order "+ link + "/orders/" + order_uuid +"we are not able to deliver the product. For reordering kindly please contact our dedicated customer care at 048129701."
                    p2 = threading.Thread(target=send_parajohn_order_status_sms, args=(unit_order_obj,message,))
                    p2.start()
                elif website_group=="shopnesto":
                    message = "Your Order "+ link + "/orders/" + order_uuid +"we are not able to deliver the product. For reordering kindly please contact our dedicated customer care at 048129701."
                    p2 = threading.Thread(target=send_wigme_order_status_sms , args=(unit_order_obj,message,))
                    p2.start()
                elif website_group=="geepasuganda":
                    message = "Your Order "+ link + "/orders/" + order_uuid +"we are not able to deliver the product. For reordering kindly please contact our dedicated customer care at 048129701."
                    p2 = threading.Thread(target=send_geepas_order_status_sms , args=(unit_order_obj,message,))
                    p2.start()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("set_order_status: %s at %s", e, str(exc_tb.tb_lineno))
        return

    if unit_order_obj.current_status_admin=="delivered" and order_status in ["returned"]:
        unit_order_obj.current_status_admin = order_status
        unit_order_obj.current_status = "returned"
        unit_order_obj.save()
        UnitOrderStatus.objects.create(unit_order=unit_order_obj, status="returned", status_admin=order_status)
        return

    if unit_order_obj.current_status_admin=="delivery failed" and order_status in ["returned"]:
        unit_order_obj.current_status_admin = order_status
        unit_order_obj.current_status = "returned"
        unit_order_obj.save()
        UnitOrderStatus.objects.create(unit_order=unit_order_obj, status="returned", status_admin=order_status)
        return

def set_order_status_without_mail(unit_order_obj, order_status):
    if unit_order_obj.current_status_admin=="approved" and order_status in ["picked"]:
        unit_order_obj.current_status = "shipped"
        unit_order_obj.current_status_admin = order_status
        unit_order_obj.save()
        UnitOrderStatus.objects.create(unit_order=unit_order_obj, status="ordered", status_admin=order_status)
        return
    
    if unit_order_obj.current_status_admin=="picked" and order_status in ["dispatched"]:
        unit_order_obj.current_status = "intransit"
        unit_order_obj.current_status_admin = order_status
        unit_order_obj.save()
        UnitOrderStatus.objects.create(unit_order=unit_order_obj, status="shipped", status_admin=order_status)
        try:
            UnitOrderMailRequest.objects.create(unit_order=unit_order_obj, status="dispatched") # save order dispatched mail details
            website_group = unit_order_obj.order.location_group.website_group.name
            order_uuid = unit_order_obj.order.uuid
            link = unit_order_obj.order.location_group.website_group.link

            if website_group=="parajohn":
                message = "Your Order "+ link + "/orders/" + order_uuid +" has been dispatched. Expected delivery within 2 days."
                send_parajohn_order_status_sms(unit_order_obj, message)
            elif website_group=="shopnesto":
                message = "Your Order "+ link + "/orders/" + order_uuid +" has been dispatched. Expected delivery within 2 days."
                send_wigme_order_status_sms(unit_order_obj,message)
            elif website_group=="geepasuganda":
                message = "Your Order "+ link + "/orders/" + order_uuid +" has been dispatched. Expected delivery within 2 days."
                send_geepas_order_status_sms(unit_order_obj,message)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("set_order_status: %s at %s", e, str(exc_tb.tb_lineno))
        return

    if unit_order_obj.current_status_admin=="dispatched" and order_status in ["delivered", "delivery failed"]:
        unit_order_obj.current_status_admin = order_status
        status = ""
        if order_status=="delivered":
            unit_order_obj.current_status = "delivered"
            status = "delivered"
        elif order_status=="delivery failed":
            status = "intransit"
        unit_order_obj.save()
        UnitOrderStatus.objects.create(unit_order=unit_order_obj, status=status, status_admin=order_status)

        if order_status=="delivered":
            try:
                UnitOrderMailRequest.objects.create(unit_order=unit_order_obj, status="delivered") # save order delivered mail details
                website_group = unit_order_obj.order.location_group.website_group.name
                link = unit_order_obj.order.location_group.website_group.link
                order_uuid = unit_order_obj.order.uuid

                if website_group=="parajohn":
                    message = "Your Order "+ link + "/orders/" + order_uuid +" has been delivered. We???d love to hear about your shopping experience. Let us know at "+ link
                    send_parajohn_order_status_sms(unit_order_obj,message)
                elif website_group=="shopnesto":
                    message = "Your Order "+ link + "/orders/" + order_uuid +" has been delivered. We???d love to hear about your shopping experience. Let us know at "+ link
                    send_wigme_order_status_sms(unit_order_obj,message)
                elif website_group=="geepasuganda":
                    message = "Your Order "+ link + "/orders/" + order_uuid +" has been delivered. We???d love to hear about your shopping experience. Let us know at "+ link
                    send_geepas_order_status_sms(unit_order_obj,message)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("set_order_status: %s at %s", e, str(exc_tb.tb_lineno))
        
        elif order_status=="delivery failed":
            try:
                website_group = unit_order_obj.order.location_group.website_group.name
                order_uuid = unit_order_obj.order.uuid
                link = unit_order_obj.order.location_group.website_group.link
                if website_group=="parajohn":
                    message = "Your Order "+ link + "/orders/" + order_uuid +"we are not able to deliver the product. For reordering kindly please contact our dedicated customer care at 048129701."
                    send_parajohn_order_status_sms(unit_order_obj,message)
                elif website_group=="shopnesto":
                    message = "Your Order "+ link + "/orders/" + order_uuid +"we are not able to deliver the product. For reordering kindly please contact our dedicated customer care at 048129701."
                    send_wigme_order_status_sms(unit_order_obj,message)
                elif website_group=="geepasuganda":
                    message = "Your Order "+ link + "/orders/" + order_uuid +"we are not able to deliver the product. For reordering kindly please contact our dedicated customer care at 048129701."
                    send_geepas_order_status_sms(unit_order_obj,message)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("set_order_status: %s at %s", e, str(exc_tb.tb_lineno))
        return

    if unit_order_obj.current_status_admin=="delivered" and order_status in ["returned"]:
        unit_order_obj.current_status_admin = order_status
        unit_order_obj.current_status = "returned"
        unit_order_obj.save()
        UnitOrderStatus.objects.create(unit_order=unit_order_obj, status="returned", status_admin=order_status)
        return

    if unit_order_obj.current_status_admin=="delivery failed" and order_status in ["returned"]:
        unit_order_obj.current_status_admin = order_status
        unit_order_obj.current_status = "returned"
        unit_order_obj.save()
        UnitOrderStatus.objects.create(unit_order=unit_order_obj, status="returned", status_admin=order_status)
        return


def cancel_order_admin(unit_order_obj, cancelling_note):

    if unit_order_obj.current_status_admin in ["pending", "approved", "delivery failed"]:
        unit_order_obj.current_status_admin = "cancelled"
        unit_order_obj.current_status = "cancelled"
        unit_order_obj.cancelling_note = cancelling_note
        unit_order_obj.save()
        UnitOrderStatus.objects.create(unit_order=unit_order_obj, status="cancelled", status_admin="cancelled")
        try:
            p1 = threading.Thread(target=send_order_cancelled_mail, args=(unit_order_obj,))
            p1.start()
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("cancel_order_admin: %s at %s", e, str(exc_tb.tb_lineno))
        return


def update_cart_bill(cart_obj,cod=False,offline=False, delivery_fee_calculate=True):
    
    cart_obj.to_pay = cart_obj.get_total_amount(cod=cod,offline=offline, delivery_fee_calculate=delivery_fee_calculate)
    cart_obj.offline_delivery_fee = cart_obj.get_delivery_fee(cod=cod,offline=offline, calculate=delivery_fee_calculate)

    if cart_obj.voucher!=None:
        voucher_obj = cart_obj.voucher
        if  voucher_obj.is_deleted==True or voucher_obj.is_published==False or voucher_obj.is_expired()==True or voucher_obj.is_eligible(cart_obj.get_subtotal(offline=offline))==False or is_voucher_limt_exceeded_for_customer(cart_obj.owner, voucher_obj) or voucher_obj.is_super_category_eligible(cart_obj)==False:
            cart_obj.voucher = None
    cart_obj.save()


def update_fast_cart_bill(fast_cart_obj):
    
    fast_cart_obj.to_pay = fast_cart_obj.get_total_amount()

    if fast_cart_obj.voucher!=None:
        voucher_obj = fast_cart_obj.voucher
        if voucher_obj.is_deleted==True or voucher_obj.is_published==False or voucher_obj.is_expired()==True or voucher_obj.is_eligible(fast_cart_obj.get_subtotal())==False or is_voucher_limt_exceeded_for_customer(fast_cart_obj.owner, voucher_obj)or voucher_obj.is_super_category_eligible(fast_cart_obj)==False:
            fast_cart_obj.voucher = None
    fast_cart_obj.save()


def update_order_bill(order_obj):
    
    order_obj.delivery_fee = order_obj.get_delivery_fee_update()
    order_obj.to_pay = order_obj.get_total_amount()
    order_obj.real_to_pay = order_obj.get_total_amount(is_real=True)
    order_obj.save()


def update_order_request_bill(order_request_obj,cod=False):

    order_request_obj.to_pay = order_request_obj.get_total_amount(cod=cod)
    order_request_obj.offline_delivery_fee = order_request_obj.get_delivery_fee(cod=cod)

    if order_request_obj.voucher!=None:
        voucher_obj = order_request_obj.voucher
        if voucher_obj.is_deleted==True or voucher_obj.is_published==False or voucher_obj.is_expired()==True or voucher_obj.is_eligible(order_request_obj.get_subtotal())==False or is_voucher_limt_exceeded_for_customer(order_request_obj.owner, voucher_obj):
            order_request_obj.voucher = None

    order_request_obj.to_pay = order_request_obj.get_total_amount(cod=cod)
    order_request_obj.offline_delivery_fee = order_request_obj.get_delivery_fee(cod=cod)
    order_request_obj.save()


def send_wigme_order_status_sms(unit_order_obj,message):
    try:
        dealshub_user_obj = unit_order_obj.order.owner
        if dealshub_user_obj.contact_verified==False:
            return
        
        logger.info("send_wigme_order_status_sms:", message)
        location_group_obj = unit_order_obj.order.location_group
        sms_country_info = json.loads(location_group_obj.sms_country_info)
        prefix_code = sms_country_info["prefix_code"]
        user = sms_country_info["user"]
        pwd = sms_country_info["pwd"]
        contact_number = prefix_code+dealshub_user_obj.contact_number

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
        logger.error("send_wigme_order_status_sms: %s at %s", e, str(exc_tb.tb_lineno))

def send_geepas_order_status_sms(unit_order_obj,message):
    try:
        dealshub_user_obj = unit_order_obj.order.owner
        if dealshub_user_obj.contact_verified==False:
            return
        
        logger.info("send_geepas_order_status_sms:", message)
        location_group_obj = unit_order_obj.order.location_group
        sms_country_info = json.loads(location_group_obj.sms_country_info)
        prefix_code = sms_country_info["prefix_code"]
        sender = sms_country_info["sender_id"]
        contact_number = "+" + prefix_code + dealshub_user_obj.contact_number

        africastalking.initialize(
            username='geepasug',
            api_key='e5d7fd9be205264e7dd649fa904dbe36952f8c64efa21bea53b7b537f23155b9'
        )
        sms = africastalking.SMS
        recipients = [contact_number]    #["+917043300725"]
        try:
            response = sms.send(message, recipients, sender)
            print (response)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("VerifyOTPSMSLogin: %s at %s", e, str(exc_tb.tb_lineno))

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("send_geepas_order_status_sms: %s at %s", e, str(exc_tb.tb_lineno))


def send_daycart_order_status_sms(unit_order_obj,message):
    try:
        dealshub_user_obj = unit_order_obj.order.owner
        if dealshub_user_obj.contact_verified==False:
            return
        
        logger.info("send_daycart_order_status_sms:", message)
        location_group_obj = unit_order_obj.order.location_group
        sms_country_info = json.loads(location_group_obj.sms_country_info)
        prefix_code = sms_country_info["prefix_code"]
        user = sms_country_info["user"]
        pwd = sms_country_info["pwd"]
        contact_number = prefix_code+dealshub_user_obj.contact_number

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
        logger.error("send_daycart_order_status_sms: %s at %s", e, str(exc_tb.tb_lineno))


def send_parajohn_order_status_sms(unit_order_obj,message):
    try:
        dealshub_user_obj = unit_order_obj.order.owner
        if dealshub_user_obj.contact_verified==False:
            return
        logger.info("send_parajohn_order_status_sms:", message)
        contact_number = dealshub_user_obj.contact_number
        url = "https://retail.atech.alarislabs.com/rest/send_sms?from=PARA JOHN&to=971"+contact_number+"&message="+message+"&username=r8NyrDLI&password=GLeOC6HO"
        requests.get(url, timeout=10)  
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("send_parajohn_order_status_sms: %s at %s", e, str(exc_tb.tb_lineno))


def send_inquiry_now_mail(message, to_email, password, dealshub_user_obj, dealshub_product_obj):
    try:
        body = """
        Customer Name:- """+dealshub_user_obj.first_name+"""
        Customer Email: """+dealshub_user_obj.email+"""
        Customer Number:- """+dealshub_user_obj.contact_number+"""

        Message: """+message+"""
        
        Product ID: """+dealshub_product_obj.get_product_id()+"""
        Product Name: """+dealshub_product_obj.product_name+"""
        Product Description: """+dealshub_product_obj.product_description+"""
        """

        send_mail(
            subject="Product Enquiry of " + str(dealshub_product_obj.product_name),
            message=body,
            from_email=to_email,
            auth_user=to_email,
            auth_password=password,
            recipient_list=[to_email],
            fail_silently=False,
        )

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("send_inquiry_now_mail: %s at %s", e, str(exc_tb.tb_lineno))


def send_order_request_placed_mail(order_request_obj):
    try:
        logger.info("send_order_request_placed_mail started!")
        if order_request_obj.owner.email_verified==False:
            return

        unit_order_request_objs = UnitOrderRequest.objects.filter(order_request=order_request_obj)

        website_group_obj = order_request_obj.location_group.website_group
        support_email = website_group_obj.email_info
        support_contact_number = json.loads(website_group_obj.conf).get("support_contact_number","")

        custom_unit_order_list = []
        for unit_order_request_obj in unit_order_request_objs:
            temp_dict = {
                "order_id": unit_order_request_obj.order_req_id,
                "product_name": unit_order_request_obj.product.get_name(),
                "productImageUrl": unit_order_request_obj.product.get_display_image_url(),
                "quantity": unit_order_request_obj.initial_quantity,
                "price": unit_order_request_obj.initial_price,
                "currency": unit_order_request_obj.product.get_currency()
            }
            custom_unit_order_list.append(temp_dict)

        order_placed_date = order_request_obj.get_date_created()
        customer_name = order_request_obj.get_customer_first_name()
        full_name = order_request_obj.get_customer_full_name()
        website_logo = order_request_obj.get_email_website_logo()
        email_content = order_request_obj.location_group.get_email_content()
        address_lines = json.loads(order_request_obj.shipping_address.address_lines)
        html_message = loader.render_to_string(
            os.getcwd()+'/dealshub/templates/order-confirmation.html',
            {
                "website_logo": website_logo,
                "customer_name": customer_name,
                "custom_unit_order_list":  custom_unit_order_list,
                "order_placed_date": order_placed_date,
                "full_name": full_name,
                "address_lines": address_lines,
                "website_order_link": order_request_obj.get_website_link()+"/orders/"+order_request_obj.uuid,
                "email_content": email_content,
                "support_email":support_email,
                "support_contact_number":support_contact_number
            }
        )

        location_group_obj = order_request_obj.location_group

        with get_connection(
            host=location_group_obj.get_email_host(),
            port=location_group_obj.get_email_port(),
            username=location_group_obj.get_order_from_email_id(),
            password=location_group_obj.get_order_from_email_password(),
            use_tls=True) as connection:

            email = EmailMultiAlternatives(
                        subject='Order Request Placed',
                        body='Order Request Placed',
                        from_email=location_group_obj.get_order_from_email_id(),
                        to=[order_request_obj.owner.email],
                        cc=location_group_obj.get_order_cc_email_list(),
                        bcc=location_group_obj.get_order_bcc_email_list(),
                        connection=connection
                    )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            logger.info("send_order_request_placed_mail")

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("send_order_request_placed_mail: %s at %s", e, str(exc_tb.tb_lineno))


def send_order_request_approval_mail(order_request_obj):
    try:
        logger.info("send_order_request_approval_mail started!")
        if order_request_obj.owner.email_verified==False:
            return

        location_group_obj = order_request_obj.location_group

        subject = 'Your Order Request dated ' + order_request_obj.get_date_created() + ' has been approved.'
        body = 'Dear ' + order_request_obj.get_customer_full_name() + '\n' + 'Your Order has been approved.'

        with get_connection(
            host=location_group_obj.get_email_host(),
            port=location_group_obj.get_email_port(),
            username=location_group_obj.get_order_from_email_id(),
            password=location_group_obj.get_order_from_email_password(),
            use_tls=True) as connection:

            email = EmailMultiAlternatives(
                        subject=subject,
                        body=body,
                        from_email=location_group_obj.get_order_from_email_id(),
                        to=[order_request_obj.owner.email],
                        cc=location_group_obj.get_order_cc_email_list(),
                        bcc=location_group_obj.get_order_bcc_email_list(),
                        connection=connection
                    )
            email.send(fail_silently=False)
            logger.info("send_order_request_approval_mail")

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("send_order_request_approval_mail: %s at %s", e, str(exc_tb.tb_lineno))


def send_order_request_deleted_mail(order_request_obj):
    try:
        logger.info("send_order_request_deleted_mail started!")
        if order_request_obj.owner.email_verified==False:
            return
        location_group_obj = order_request_obj.location_group
        subject = 'Your Order Request dated ' + order_request_obj.get_date_created() + ' has been cancelled.'
        body = 'Dear ' + order_request_obj.get_customer_full_name() + '\n' + 'Your Order Request has been cancelled.'

        with get_connection(
            host=location_group_obj.get_email_host(),
            port=location_group_obj.get_email_port(),
            username=location_group_obj.get_order_from_email_id(),
            password=location_group_obj.get_order_from_email_password(),
            use_tls=True) as connection:

            email = EmailMultiAlternatives(
                        subject=subject,
                        body=body,
                        from_email=location_group_obj.get_order_from_email_id(),
                        to=[order_request_obj.owner.email],
                        cc=location_group_obj.get_order_cc_email_list(),
                        bcc=location_group_obj.get_order_bcc_email_list(),
                        connection=connection
                    )
            email.send(fail_silently=False)
            logger.info("send_order_request_deleted_mail")

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("send_order_request_deleted_mail: %s at %s", e, str(exc_tb.tb_lineno))


def send_order_cheque_disapproval_mail(order_obj):
    try:
        logger.info("send_order_cheque_disapproval_mail started!")
        if order_obj.owner.email_verified==False:
            return

        location_group_obj = order_obj.location_group

        with get_connection(
            host=location_group_obj.get_email_host(),
            port=location_group_obj.get_email_port(),
            username=location_group_obj.get_order_from_email_id(),
            password=location_group_obj.get_order_from_email_password(),
            use_tls=True) as connection:

            email = EmailMultiAlternatives(
                        subject='Your cheque has been Disapproved', 
                        body='Dear ' + order_obj.get_customer_full_name() + '\n' + 'Your cheque has been disapproved for your order request dated ' + order_obj.get_date_created() + ".",
                        from_email=location_group_obj.get_order_from_email_id(),
                        to=[order_obj.owner.email],
                        cc=location_group_obj.get_order_cc_email_list(),
                        bcc=location_group_obj.get_order_bcc_email_list(),
                        connection=connection
                    )
            email.send(fail_silently=False)
            logger.info("send_order_cheque_disapproval_mail")

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("send_order_cheque_disapproval_mail: %s at %s", e, str(exc_tb.tb_lineno))


def send_order_confirmation_mail(order_obj):
    try:
        logger.info("send_order_confirmation_mail started!")
        if order_obj.owner.email_verified==False:
            return

        unit_order_objs = UnitOrder.objects.filter(order=order_obj)

        custom_unit_order_list = []
        for unit_order_obj in unit_order_objs:
            temp_dict = {
                "order_id": unit_order_obj.orderid,
                "product_name": unit_order_obj.product.get_name(),
                "productImageUrl": unit_order_obj.product.get_display_image_url(),
                "quantity": unit_order_obj.quantity,
                "price": unit_order_obj.price,
                "currency": unit_order_obj.product.get_currency()
            }
            custom_unit_order_list.append(temp_dict)

        order_placed_date = order_obj.get_date_created()
        customer_name = order_obj.get_customer_first_name()
        address_lines = json.loads(order_obj.shipping_address.address_lines)
        full_name = order_obj.get_customer_full_name()
        website_logo = order_obj.get_email_website_logo()
        email_content = order_obj.location_group.get_email_content()

        website_group_obj = order_obj.location_group.website_group
        support_email = website_group_obj.email_info
        support_contact_number = json.loads(website_group_obj.conf).get("support_contact_number","")

        html_message = loader.render_to_string(
            os.getcwd()+'/dealshub/templates/order-confirmation.html',
            {
                "website_logo": website_logo,
                "customer_name": customer_name,
                "custom_unit_order_list":  custom_unit_order_list,
                "order_placed_date": order_placed_date,
                "full_name": full_name,
                "address_lines": address_lines,
                "website_order_link": order_obj.get_website_link()+"/orders/"+order_obj.uuid,
                "email_content": email_content,
                "support_email":support_email,
                "support_contact_number":support_contact_number
            }
        )
        location_group_obj = order_obj.location_group

        with get_connection(
            host=location_group_obj.get_email_host(),
            port=location_group_obj.get_email_port(), 
            username=location_group_obj.get_order_from_email_id(), 
            password=location_group_obj.get_order_from_email_password(),
            use_tls=True) as connection:

            email = EmailMultiAlternatives(
                        subject='Order Confirmation', 
                        body='Order Confirmation', 
                        from_email=location_group_obj.get_order_from_email_id(),
                        to=[order_obj.owner.email],
                        cc=location_group_obj.get_order_cc_email_list(),
                        bcc=location_group_obj.get_order_bcc_email_list(),
                        connection=connection
                    )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            logger.info("send_order_confirmation_mail ended")

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("send_order_confirmation_mail: %s at %s", e, str(exc_tb.tb_lineno))


def send_order_dispatch_mail(unit_order_obj):
    try:
        if unit_order_obj.order.owner.email_verified==False:
            return

        order_dispatched_date = UnitOrderStatus.objects.filter(unit_order=unit_order_obj, status="shipped")[0].date_created
        order_dispatched_date = str(timezone.localtime(order_dispatched_date).strftime("%A, %B %d, %Y | %I:%M %p"))

        customer_name = unit_order_obj.order.get_customer_first_name()
        address_lines = json.loads(unit_order_obj.order.shipping_address.address_lines)
        full_name = unit_order_obj.order.get_customer_full_name()
        website_logo = unit_order_obj.order.get_email_website_logo()

        website_group_obj = unit_order_obj.order.location_group.website_group
        support_email = website_group_obj.email_info
        support_contact_number = json.loads(website_group_obj.conf).get("support_contact_number","")
        email_content = unit_order_obj.order.location_group.get_email_content()
        custom_unit_order_list = []
        temp_dict = {
            "order_id": unit_order_obj.orderid,
            "product_name": unit_order_obj.product.get_name(),
            "productImageUrl": unit_order_obj.product.get_display_image_url(),
            "quantity": unit_order_obj.quantity,
            "price": unit_order_obj.price,
            "currency": unit_order_obj.product.get_currency()
        }
        custom_unit_order_list.append(temp_dict)
        order_placed_date = unit_order_obj.order.get_date_created()
        html_message = loader.render_to_string(
            os.getcwd()+'/dealshub/templates/order-dispatch.html',
            {
                "website_logo": website_logo,
                "customer_name": customer_name,
                "custom_unit_order_list":  custom_unit_order_list,
                "order_placed_date": order_placed_date,
                "full_name": full_name,
                "address_lines": address_lines,
                "website_order_link": unit_order_obj.order.get_website_link()+"/orders/"+unit_order_obj.order.uuid,
                "email_content": email_content,
                "support_email":support_email,
                "support_contact_number":support_contact_number
            }
        )

        location_group_obj = unit_order_obj.order.location_group

        with get_connection(
            host=location_group_obj.get_email_host(),
            port=location_group_obj.get_email_port(), 
            username=location_group_obj.get_order_from_email_id(), 
            password=location_group_obj.get_order_from_email_password(),
            use_tls=True) as connection:

            email = EmailMultiAlternatives(
                        subject='Order Dispatch',
                        body='Order Dispatch',
                        from_email=location_group_obj.get_order_from_email_id(),
                        to=[unit_order_obj.order.owner.email],
                        cc=location_group_obj.get_order_cc_email_list(),
                        bcc=location_group_obj.get_order_bcc_email_list(),
                        connection=connection
                    )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            logger.info("send_order_dispatch_mail")

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("send_order_dispatch_mail: %s at %s", e, str(exc_tb.tb_lineno))


def send_order_delivered_mail(unit_order_obj):
    try:

        if unit_order_obj.order.owner.email_verified==False:
            return

        order_delivered_date = UnitOrderStatus.objects.filter(unit_order=unit_order_obj, status="delivered")[0].date_created
        order_delivered_date = str(timezone.localtime(order_delivered_date).strftime("%A, %B %d, %Y | %I:%M %p"))
        customer_name = unit_order_obj.order.get_customer_first_name()

        address_lines = json.loads(unit_order_obj.order.shipping_address.address_lines)
        full_name = unit_order_obj.order.get_customer_full_name()
        website_logo = unit_order_obj.order.get_email_website_logo()

        website_group_obj = unit_order_obj.order.location_group.website_group
        support_email = website_group_obj.email_info
        support_contact_number = json.loads(website_group_obj.conf).get("support_contact_number","")
        email_content = unit_order_obj.order.location_group.get_email_content()
        custom_unit_order_list = []
        temp_dict = {
            "order_id": unit_order_obj.orderid,
            "product_name": unit_order_obj.product.get_name(),
            "productImageUrl": unit_order_obj.product.get_display_image_url(),
            "quantity": unit_order_obj.quantity,
            "price": unit_order_obj.price,
            "currency": unit_order_obj.product.get_currency()
        }
        custom_unit_order_list.append(temp_dict)
        order_placed_date = unit_order_obj.order.get_date_created()
        html_message = loader.render_to_string(
            os.getcwd()+'/dealshub/templates/order-delivered.html',
            {
                "website_logo": website_logo,
                "customer_name": customer_name,
                "custom_unit_order_list":  custom_unit_order_list,
                "order_placed_date": order_placed_date,
                "full_name": full_name,
                "address_lines": address_lines,
                "website_order_link": unit_order_obj.order.get_website_link()+"/orders/"+unit_order_obj.order.uuid,
                "email_content": email_content,
                "support_email":support_email,
                "support_contact_number":support_contact_number
            }
        )

        location_group_obj = unit_order_obj.order.location_group

        with get_connection(
            host=location_group_obj.get_email_host(),
            port=location_group_obj.get_email_port(), 
            username=location_group_obj.get_order_from_email_id(), 
            password=location_group_obj.get_order_from_email_password(),
            use_tls=True) as connection:

            email = EmailMultiAlternatives(
                        subject='Order Delivered', 
                        body='Order Delivered', 
                        from_email=location_group_obj.get_order_from_email_id(),
                        to=[unit_order_obj.order.owner.email],
                        cc=location_group_obj.get_order_cc_email_list(),
                        bcc=location_group_obj.get_order_bcc_email_list(),
                        connection=connection
                    )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            logger.info("send_order_delivered_mail")

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("send_order_delivered_mail: %s at %s", e, str(exc_tb.tb_lineno))


def send_order_delivery_failed_mail(unit_order_obj):
    try:
        if unit_order_obj.order.owner.email_verified==False:
            return

        order_delivery_failed = UnitOrderStatus.objects.filter(unit_order=unit_order_obj, status_admin="delivery failed")[0].date_created
        order_delivery_failed = str(timezone.localtime(order_delivery_failed).strftime("%A, %B %d, %Y | %I:%M %p"))
        customer_name = unit_order_obj.order.get_customer_first_name()

        address_lines = json.loads(unit_order_obj.order.shipping_address.address_lines)
        full_name = unit_order_obj.order.get_customer_full_name()
        website_logo = unit_order_obj.order.get_email_website_logo()

        website_group_obj = unit_order_obj.order.location_group.website_group
        support_email = website_group_obj.email_info
        support_contact_number = json.loads(website_group_obj.conf).get("support_contact_number","")
        email_content = unit_order_obj.order.location_group.get_email_content()
        custom_unit_order_list = []
        temp_dict = {
            "order_id": unit_order_obj.orderid,
            "product_name": unit_order_obj.product.get_name(),
            "productImageUrl": unit_order_obj.product.get_display_image_url(),
            "quantity": unit_order_obj.quantity,
            "price": unit_order_obj.price,
            "currency": unit_order_obj.product.get_currency()
        }
        custom_unit_order_list.append(temp_dict)
        order_placed_date = unit_order_obj.order.get_date_created()
        html_message = loader.render_to_string(
            os.getcwd()+'/dealshub/templates/order-delivery-failed.html',
            {
                "website_logo": website_logo,
                "customer_name": customer_name,
                "custom_unit_order_list":  custom_unit_order_list,
                "order_placed_date": order_placed_date,
                "full_name": full_name,
                "address_lines": address_lines,
                "website_order_link": unit_order_obj.order.get_website_link()+"/orders/"+unit_order_obj.order.uuid,
                "email_content": email_content,
                "support_email":support_email,
                "support_contact_number":support_contact_number
            }
        )

        location_group_obj = unit_order_obj.order.location_group

        with get_connection(
            host=location_group_obj.get_email_host(),
            port=location_group_obj.get_email_port(), 
            username=location_group_obj.get_order_from_email_id(), 
            password=location_group_obj.get_order_from_email_password(),
            use_tls=True) as connection:

            email = EmailMultiAlternatives(
                        subject='Order Delivery Failed', 
                        body='Order Delivery Failed', 
                        from_email=location_group_obj.get_order_from_email_id(),
                        to=[unit_order_obj.order.owner.email],
                        cc=location_group_obj.get_order_cc_email_list(),
                        bcc=location_group_obj.get_order_bcc_email_list(),
                        connection=connection
                    )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            logger.info("send_order_delivery_failed_mail")

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("send_order_delivery_failed_mail: %s at %s", e, str(exc_tb.tb_lineno))


def send_order_cancelled_mail(unit_order_obj):
    try:
        if unit_order_obj.order.owner.email_verified==False:
            return

        order_cancelled_date = UnitOrderStatus.objects.filter(unit_order=unit_order_obj, status="cancelled")[0].date_created
        order_cancelled_date = str(timezone.localtime(order_cancelled_date).strftime("%A, %B %d, %Y | %I:%M %p"))
        customer_name = unit_order_obj.order.get_customer_first_name()

        address_lines = json.loads(unit_order_obj.order.shipping_address.address_lines)
        full_name = unit_order_obj.order.get_customer_full_name()
        website_logo = unit_order_obj.order.get_email_website_logo()

        website_group_obj = unit_order_obj.order.location_group.website_group
        support_email = website_group_obj.email_info
        support_contact_number = json.loads(website_group_obj.conf).get("support_contact_number","")
        email_content = unit_order_obj.order.location_group.get_email_content()
        custom_unit_order_list = []
        temp_dict = {
            "order_id": unit_order_obj.orderid,
            "product_name": unit_order_obj.product.get_name(),
            "productImageUrl": unit_order_obj.product.get_display_image_url(),
            "quantity": unit_order_obj.quantity,
            "price": unit_order_obj.price,
            "currency": unit_order_obj.product.get_currency()
        }
        custom_unit_order_list.append(temp_dict)
        order_placed_date = unit_order_obj.order.get_date_created()
        html_message = loader.render_to_string(
            os.getcwd()+'/dealshub/templates/order-cancelled.html',
            {
                "website_logo": website_logo,
                "customer_name": customer_name,
                "custom_unit_order_list":  custom_unit_order_list,
                "order_placed_date": order_placed_date,
                "full_name": full_name,
                "address_lines": address_lines,
                "website_order_link": unit_order_obj.order.get_website_link()+"/orders/"+unit_order_obj.order.uuid,
                "email_content": email_content,
                "support_email":support_email,
                "support_contact_number":support_contact_number
            }
        )

        location_group_obj = unit_order_obj.order.location_group

        with get_connection(
            host=location_group_obj.get_email_host(),
            port=location_group_obj.get_email_port(), 
            username=location_group_obj.get_order_from_email_id(), 
            password=location_group_obj.get_order_from_email_password(),
            use_tls=True) as connection:

            email = EmailMultiAlternatives(
                        subject='Order Cancelled', 
                        body='Order Cancelled',
                        from_email=location_group_obj.get_order_from_email_id(),
                        to=[unit_order_obj.order.owner.email],
                        cc=location_group_obj.get_order_cc_email_list(),
                        bcc=location_group_obj.get_order_bcc_email_list(),
                        connection=connection
                    )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            logger.info("send_order_cancelled_mail")

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("send_order_cancelled_mail: %s at %s", e, str(exc_tb.tb_lineno))


def notify_order_cancel_status_to_user(unit_order_obj, status):
    try:
        if unit_order_obj.order.owner.email_verified==False:
            return
        
        customer_name = unit_order_obj.order.get_customer_first_name()

        address_lines = json.loads(unit_order_obj.order.shipping_address.address_lines)
        full_name = unit_order_obj.order.get_customer_full_name()
        website_logo = unit_order_obj.order.get_email_website_logo()

        website_group_obj = unit_order_obj.order.location_group.website_group
        support_email = website_group_obj.email_info
        support_contact_number = json.loads(website_group_obj.conf).get("support_contact_number","")

        html_message = loader.render_to_string(
            os.getcwd()+'/dealshub/templates/order-cancel-status.html',
            {
                "website_logo": website_logo,
                "customer_name": customer_name,
                "custom_unit_order_list":  custom_unit_order_list,
                "order_placed_date": order_placed_date,
                "full_name": full_name,
                "address_lines": address_lines,
                "website_order_link": unit_order_obj.order.get_website_link()+"/orders/"+unit_order_obj.order.uuid,
                "email_content": email_content,
                "support_email":support_email,
                "support_contact_number":support_contact_number
            }
        )

        location_group_obj = unit_order_obj.order.location_group

        with get_connection(
            host=location_group_obj.get_email_host(),
            port=location_group_obj.get_email_port(), 
            username=location_group_obj.get_order_from_email_id(), 
            password=location_group_obj.get_order_from_email_password(),
            use_tls=True) as connection:

            email = EmailMultiAlternatives(
                        subject='Order Cancel Status', 
                        body='Order Cancel Status',
                        from_email=location_group_obj.get_order_from_email_id(),
                        to=[unit_order_obj.order.owner.email],
                        cc=location_group_obj.get_order_cc_email_list(),
                        bcc=location_group_obj.get_order_bcc_email_list(),
                        connection=connection
                    )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            logger.info("notify_order_cancel_status_to_user")

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("notify_order_cancel_status_to_user: %s at %s", e, str(exc_tb.tb_lineno))

def send_order_review_mail(order_obj, unit_order_objs, user_token):
    try:
        if order_obj.owner.email_verified == False:
            return
        
        customer_name = order_obj.get_customer_first_name()

        address_lines = json.loads(order_obj.shipping_address.address_lines)
        full_name = order_obj.get_customer_full_name()
        website_logo = order_obj.get_email_website_logo()

        website_group_obj = order_obj.location_group.website_group
        support_email = website_group_obj.email_info
        support_contact_number = json.loads(website_group_obj.conf).get("support_contact_number","")

        product_list = []
        for unit_order_obj in unit_order_objs:
            temp_dict = {}
            temp_dict["name"] = unit_order_obj.product.get_name()
            temp_dict["quantity"] = unit_order_obj.quantity
            temp_dict["image"] = unit_order_obj.product.get_display_image_url()
            product_list.append(temp_dict)

        if not product_list:
            return

        html_message = loader.render_to_string(
            os.getcwd()+'/dealshub/templates/order-review.html',
            {
                "website_logo": website_logo,
                "customer_name": customer_name,
                "order_id": order_obj.bundleid,
                "product_list": product_list,
                "review_url" : WIGME_IP + "/?" + order_obj.uuid + "&" + user_token,
                "website_order_link": order_obj.get_website_link()+"/orders/"+order_obj.uuid,
                "support_email": support_email,
                "support_contact_number": support_contact_number
            }
        )

        location_group_obj = order_obj.location_group

        with get_connection(
            host=location_group_obj.get_email_host(),
            port=location_group_obj.get_email_port(), 
            username=location_group_obj.get_order_from_email_id(), 
            password=location_group_obj.get_order_from_email_password(),
            use_tls=True) as connection:

            email = EmailMultiAlternatives(
                        subject='Hi ' + customer_name + '! We would really appreciate your feedback', 
                        body='Order Feedback',
                        from_email=location_group_obj.get_order_from_email_id(),
                        to=[order_obj.owner.email],
                        cc=location_group_obj.get_order_cc_email_list(),
                        bcc=location_group_obj.get_order_bcc_email_list(),
                        connection=connection
                    )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            logger.info("send_order_review_mail")

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("send_order_review_mail: %s at %s", e, str(exc_tb.tb_lineno))
    

def send_notification_for_blog_publish(blog_post_obj):
    
    try:
        website_link = blog_post_obj.location_group.website_group.link
        if website_link[-1] != "/":
            website_link = str(website_link)+'/'

        blog_link = str(website_link)+"/blogs/description/"+str(blog_post_obj.uuid)
        body = """

            Hey,

            Our new BLOG is finally here!!
            Title:- """+ str(blog_post_obj.title) +""".

            What makes our blogs different are, it gives an introduction to our products and why people want to buy it. 
            You can order directly from our website.
            
            Link to view: """+ str(blog_link) +""".
        """

        with get_connection(
            host="smtp.office365.com",
            port=587, 
            username="info@wigme.com", 
            password="western@#143",
            use_tls=True) as connection:
            email = EmailMessage(subject=str(blog_post_obj.title),
                                    body=body,
                                    from_email='info@wigme.com',
                                    to=json.loads(blog_post_obj.location_group.blog_emails),
                                    connection=connection)
            email.send(fail_silently=True)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error send_notification_for_blog_publish %s %s", e, str(exc_tb.tb_lineno))


def contact_us_send_email(your_email, message, to_email, password):
    try:
        body = """
        Customer Email: """+your_email+"""
        Message: """+message+"""
        """
        send_mail(
            subject='Contact Enquiry',
            message=body,
            from_email=to_email,
            auth_user=to_email,
            auth_password=password,
            recipient_list=[to_email],
            fail_silently=False
        )

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("contact_us_send_email: %s at %s", e, str(exc_tb.tb_lineno))


def notify_low_stock(dealshub_product_obj):
    try:   
        body = "This is to inform you that "+dealshub_product_obj.get_seller_sku()+" product is out of stock. Kindly check with SAP and take appropriate action."
        with get_connection(
            host="smtp.gmail.com",
            port=587, 
            username=EMAIL_USERNAME, 
            password=EMAIL_PASSWORD,
            use_tls=True) as connection:
            email = EmailMessage(subject='Out of Stock: '+dealshub_product_obj.get_seller_sku(),
                                    body=body,
                                    from_email=EMAIL_USERNAME,
                                    to=["hari.pk@westernint.com","faris.p@westernint.com","wigme.dm@westernint.com"],
                                    connection=connection)
            email.send(fail_silently=True)
         
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("notify_low_stock: %s at %s", e, str(exc_tb.tb_lineno))


def notify_grn_error(order_obj):
    try:
        custom_permission_objs = CustomPermission.objects.filter(location_groups__in=[order_obj.location_group])
        email_list = []
        email_record_names = ["hari.pk@westernint.com","rikas.k@westernint.com","wigme@westernint.com"]
        for custom_permission_obj in custom_permission_objs:
            if custom_permission_obj.user.email in email_record_names:
                email_list.append(custom_permission_obj.user.email)
        try:
            body = "This is to inform you that order number "+order_obj.bundleid+" has GRN error. Kindly check on Omnycomm and take appropriate action."
            with get_connection(
                host="smtp.gmail.com",
                port=587, 
                username=EMAIL_USERNAME, 
                password=EMAIL_PASSWORD,
                use_tls=True) as connection:
                email = EmailMessage(subject='GRN Error: '+order_obj.bundleid,
                                     body=body,
                                     from_email=EMAIL_USERNAME,
                                     to=email_list,
                                     connection=connection)
                email.send(fail_silently=True)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("notify_grn_error: %s at %s", e, str(exc_tb.tb_lineno))        
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("notify_grn_error: %s at %s", e, str(exc_tb.tb_lineno))        


def notify_new_products_email(filepath, location_group_obj):
    try:
        location_group_name = location_group_obj.name
        user_objs = CustomPermission.objects.filter(location_groups__pk = location_group_obj.pk)
        email_list = []
        email_record_names = ["hari.pk@westernint.com","faris.p@westernint.com","wigme.dm@westernint.com","rashid.c@westernint.com","support@westernint.com","marheamwk@gmail.com"]
        for user_obj in user_objs:
            if user_obj.user.email in email_record_names:
                email_list.append(user_obj.user.email)
        try:
            body = "Please find the attached sheet for new products published on " + location_group_name + "."
            subject = "Notification for new products created on " + location_group_name
            with get_connection(
                host = "smtp.gmail.com",
                port = 587,
                username=EMAIL_USERNAME,
                password=EMAIL_PASSWORD,
                use_tls=True) as connection:
                email = EmailMessage(subject=subject,
                                     body=body,
                                     from_email=EMAIL_USERNAME,
                                     to=email_list,
                                     connection=connection)
                email.attach_file(filepath)
                email.send(fail_silently=False)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("notify_new_products_email:- Email Failure %s at %s", e, str(exc_tb.tb_lineno))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("notify_new_products_email: %s at %s", e, str(exc_tb.tb_lineno))        


def refresh_stock(order_obj):

    try:
        unit_order_objs = UnitOrder.objects.filter(order=order_obj)
        uuid_list = []
        for unit_order_obj in unit_order_objs:
            dealshub_product_obj = unit_order_obj.product
            brand_name = dealshub_product_obj.get_brand().lower()
            seller_sku = dealshub_product_obj.get_seller_sku()
            stock = 0
            company_code = ""
            total_holding = 0.0

            try :
                company_code_obj = CompanyCodeSAP.objects.get(location_group=order_obj.location_group, brand__name=brand_name)
                company_code = company_code_obj.code
            except Exception as e:
                continue

            if "wigme" in seller_sku.lower():
                continue
            
            prices_stock_information = fetch_prices_and_stock(seller_sku, company_code)
            total_holding = prices_stock_information["total_holding"]
            holding_threshold = prices_stock_information["holding_threshold"]

            # if brand=="geepas":
            #     stock2 = fetch_prices_and_stock(seller_sku, "1000")
            #     stock = max(stock1, stock2)
            # elif brand=="baby plus":
            #     stock = fetch_refresh_stock(seller_sku, "5550", "TG01")
            # elif brand=="royalford":
            #     stock = fetch_refresh_stock(seller_sku, "3000", "AFS1")
            # elif brand=="krypton":
            #     stock = fetch_refresh_stock(seller_sku, "2100", "TG01")
            # elif brand=="olsenmark":
            #     stock = fetch_refresh_stock(seller_sku, "1100", "AFS1")
            # elif brand=="ken jardene":
            #     stock = fetch_refresh_stock(seller_sku, "5550", "AFS1") # 
            # elif brand=="younglife":
            #     stock = fetch_refresh_stock(seller_sku, "5000", "AFS1")
            # elif brand=="delcasa":
            #     stock = fetch_refresh_stock(seller_sku, "3000", "TG01")

            wigme_location_group_obj = LocationGroup.objects.get(name="WIGMe - UAE")
            if dealshub_product_obj.location_group==wigme_location_group_obj and dealshub_product_obj.product.base_product.brand.name.lower() != "ecka":
                dealshub_product_obj.stock = int(total_holding)
            
            if holding_threshold > total_holding:
                try:
                    p2 = threading.Thread(target=notify_low_stock, args=(dealshub_product_obj,))
                    p2.start()
                    #dealshub_product_obj.stock = 0
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("refresh_stock: %s at %s", e, str(exc_tb.tb_lineno))

            dealshub_product_obj.save()

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("refresh_stock: %s at %s", e, str(exc_tb.tb_lineno))


def calculate_gtm(order_obj):
    purchase_info = {}
    try:
        product_list = []
        unit_order_objs = UnitOrder.objects.filter(order=order_obj)

        total_amount = 0
        for unit_order_obj in unit_order_objs:
            temp_dict = {
                "name": unit_order_obj.product.get_name(),
                "id": unit_order_obj.product.uuid,
                "price": str(unit_order_obj.price),
                "brand": unit_order_obj.product.get_brand(),
                "category": unit_order_obj.product.get_category(),
                "variant": "",
                "quantity": unit_order_obj.quantity,
                "coupon": ""
            }
            product_list.append(temp_dict)

        total_amount = order_obj.get_total_amount()
        delivery_fee = order_obj.get_delivery_fee()
        vat = order_obj.get_vat()

        purchase_info = {
            "actionField": {
                "id": order_obj.bundleid,
                "affiliation": "Online Store",
                "revenue": str(total_amount),
                "tax": str(vat),
                "shipping": str(delivery_fee),
                "coupon": "" if order_obj.voucher==None else str(order_obj.voucher.voucher_code) ,
                "currency": str(order_obj.get_currency())
            },
            "products": product_list
        }
        return purchase_info
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("GTM Calculation: %s at %s", e, str(exc_tb.tb_lineno))
    return purchase_info


def get_random_products(dealshub_product_objs):
    
    try:
        if dealshub_product_objs.count()<=5:
            return dealshub_product_objs
        
        random_set = random.sample(range(0, dealshub_product_objs.count()), 5)
        selected_dealshub_product_objs = DealsHubProduct.objects.none()
        for i in random_set:
            selected_dealshub_product_objs |= DealsHubProduct.objects.filter(pk=dealshub_product_objs[i].pk)

        return selected_dealshub_product_objs
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("get_random_products: %s at %s", e, str(exc_tb.tb_lineno))
    return dealshub_product_objs[:5]



def get_recommended_products(dealshub_product_objs,language_code):

    dealshub_product_objs = get_random_products(dealshub_product_objs)

    product_list = []
    for dealshub_product_obj in dealshub_product_objs:
        if dealshub_product_obj.now_price==0:
            continue
        try:
            temp_dict = {}
            temp_dict["name"] = dealshub_product_obj.get_name(language_code)
            temp_dict["brand"] = dealshub_product_obj.get_brand(language_code)
            temp_dict["seller_sku"] = dealshub_product_obj.get_seller_sku()
            temp_dict["link"] = dealshub_product_obj.url
            temp_dict["now_price"] = dealshub_product_obj.now_price
            temp_dict["was_price"] = dealshub_product_obj.was_price
            temp_dict["promotional_price"] = dealshub_product_obj.promotional_price
            temp_dict["stock"] = dealshub_product_obj.stock
            temp_dict["isStockAvailable"] = dealshub_product_obj.stock>0
            product_promotion_details = get_product_promotion_details(dealshub_product_obj)
            for key in product_promotion_details.keys():
                temp_dict[key]=product_promotion_details[key]
            temp_dict["currency"] = dealshub_product_obj.get_currency()
            temp_dict["uuid"] = dealshub_product_obj.uuid
            temp_dict["id"] = dealshub_product_obj.uuid
            temp_dict["heroImageUrl"] = dealshub_product_obj.get_display_image_url()
            temp_dict["is_new_arrival"] = dealshub_product_obj.is_new_arrival
            temp_dict["is_on_sale"] = dealshub_product_obj.is_on_sale
            product_list.append(temp_dict)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("get_recommended_products: %s at %s", e, str(exc_tb.tb_lineno))
    return product_list


def is_user_input_required_for_sap_punching(stock_price_information, order_qty):
    
    try:
        
        total_atp = stock_price_information["total_atp"]
        atp_threshold = stock_price_information["atp_threshold"]
        holding_threshold = stock_price_information["holding_threshold"]
        
        if total_atp > atp_threshold and total_atp >= order_qty:
            return False
        
        return True
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("is_user_input_required_for_sap_punching: %s at %s", e, str(exc_tb.tb_lineno)) 
        return True


def fetch_order_information_for_sap_punching(seller_sku, company_code, x_value, order_qty):

    try:

        result = fetch_prices_and_stock(seller_sku, company_code)

        stock_list = result["stock_list"]
        prices = result["prices"]
        total_atp = result["total_atp"]
        total_holding = result["total_holding"]
        atp_threshold = result["atp_threshold"]
        holding_threshold = result["holding_threshold"]
        
        total_stock_info = []

        if total_atp > atp_threshold and total_atp>=order_qty:
            from_holding=""
            for item in stock_list:
                atp_qty = item["atp_qty"]
                batch = item["batch"]
                uom = item["uom"]
                if atp_qty>0:
                    temp_dict = {
                        "atp_qty": atp_qty,
                        "batch": batch,
                        "uom": uom
                    }
                    total_stock_info.append(temp_dict)
        else:
            from_holding = x_value
            if from_holding == "X":
                for item in stock_list:
                    holding_qty = item["holding_qty"]
                    batch = item["batch"]
                    uom = item["uom"]
                    if holding_qty>0:
                        temp_dict = {
                            "atp_qty": holding_qty,
                            "batch": batch,
                            "uom": uom
                        }
                        total_stock_info.append(temp_dict)
            else:
                for item in stock_list:
                    atp_qty = item["atp_qty"]
                    batch = item["batch"]
                    uom = item["uom"]
                    if atp_qty>0:
                        temp_dict = {
                            "atp_qty": atp_qty,
                            "batch": batch,
                            "uom": uom
                        }
                        total_stock_info.append(temp_dict)

        total_stock_info = sorted(total_stock_info, key=lambda k: k["atp_qty"], reverse=True) 
        order_information_list = []
        remaining_qty = order_qty
        for stock_info in total_stock_info:
            if remaining_qty==0:
                break
            if stock_info["atp_qty"]>=remaining_qty:
                temp_dict = {
                    "qty": format(remaining_qty,'.2f'),
                    "batch": stock_info["batch"],
                    "uom": stock_info["uom"],
                    "from_holding": from_holding,
                    "seller_sku": seller_sku
                }
                remaining_qty = 0
            else:
                temp_dict = {
                    "qty": format(stock_info["atp_qty"],'.2f'),
                    "batch": stock_info["batch"],
                    "uom": stock_info["uom"],
                    "from_holding": from_holding,
                    "seller_sku": seller_sku
                }
                remaining_qty -= stock_info["atp_qty"]
            order_information_list.append(temp_dict)

        logger.info("fetch_order_information_for_sap_punching: %s", str(order_information_list))
        return order_information_list
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("fetch_order_information_for_sap_punching: %s at %s", e, str(exc_tb.tb_lineno))
        return []


def create_section_banner_product_report(dealshub_product_objs, filename):

    workbook = xlsxwriter.Workbook('./'+filename,{'strings_to_urls': False})
    worksheet = workbook.add_worksheet()

    row = ["Product ID",
           "Product Name",
           "Brand",
           "Seller SKU",
           "Promotional Price",
           "Now Price"]

    cnt = 0
        
    colnum = 0
    for k in row:
        worksheet.write(cnt, colnum, k)
        colnum += 1

    for dealshub_product_obj in dealshub_product_objs:
        try:
            cnt += 1
            common_row = ["" for i in range(6)]
            common_row[0] = str(dealshub_product_obj.get_product_id())
            common_row[1] = str(dealshub_product_obj.get_name())
            common_row[2] = str(dealshub_product_obj.get_brand())
            common_row[3] = str(dealshub_product_obj.get_seller_sku())
            common_row[4] = str(dealshub_product_obj.promotional_price)
            common_row[5] = str(dealshub_product_obj.now_price)

            colnum = 0
            for k in common_row:
                worksheet.write(cnt, colnum, k)
                colnum += 1

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error create_section_banner_product_report %s %s", e, str(exc_tb.tb_lineno))

    workbook.close()

def get_all_the_charges(order_obj):

    charges = {
        "courier_charge" : "",
        "cod_charge" : "",
        "voucher_charge" : "",
        "other_charge" : "",
        "promotional_charge" : ""
    }
    
    try :

        cod_charge = order_obj.get_cod_charge_without_vat()
        # cod_charge = format(float(cod_charge),'.2f')
        courier_charge = order_obj.get_delivery_fee_without_vat()
        # courier_charge = format(float(courier_charge),'.2f')

        voucher_obj = order_obj.voucher
        is_voucher_applied = voucher_obj is not None

        voucher_charge = ""
        if is_voucher_applied:
            voucher_discount = voucher_obj.get_voucher_discount(order_obj.get_subtotal())
            voucher_charge = voucher_obj.get_voucher_discount_without_vat(voucher_discount)
            # voucher_charge = format(float(voucher_charge),'.2f')

        charges["cod_charge"] = cod_charge
        charges["courier_charge"] = courier_charge
        charges["voucher_charge"] = voucher_charge

        return charges

    except Exception as e:

        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("get_all_the_charges: %s at %s", e, str(exc_tb.tb_lineno))
        return charges

def remove_stopwords(string):
    words = string.strip().split(" ")
    stopwords = ["i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"]
    cleaned_words = []
    for word in words:
        if word not in stopwords:
            cleaned_words.append(word)
    cleaned_string = " ".join(cleaned_words)
    return cleaned_string

def dealshub_product_detail_in_dict(location_group_obj,dealshub_product_obj):
    temp_dict = {}
    try:
        temp_dict["thumbnailImageUrl"] = dealshub_product_obj.get_display_image_url()
        temp_dict["optimizedThumbnailImageUrl"] = dealshub_product_obj.get_optimized_display_image_url()
        temp_dict["name"] = dealshub_product_obj.get_name()
        temp_dict["sellerSku"] = dealshub_product_obj.get_seller_sku()
        temp_dict["brand"] = dealshub_product_obj.get_brand()
        temp_dict["displayId"] = dealshub_product_obj.get_product_id()
        temp_dict["uuid"] = dealshub_product_obj.uuid
        temp_dict["link"] = dealshub_product_obj.url
        dealshub_product_obj_base_product = dealshub_product_obj.product.base_product
        dealshub_same_baseproduct_objs = DealsHubProduct.objects.filter(location_group=location_group_obj,product__base_product = dealshub_product_obj_base_product,is_published=True).exclude(now_price=0).exclude(stock=0)
        temp_dict["color_list"] = []
        if dealshub_same_baseproduct_objs.count()>1:
            for dealshubproduct_obj in dealshub_same_baseproduct_objs:
                dealshubproduct_color = dealshubproduct_obj.product.color
                temp_dict["color_list"].append({"color":str(dealshubproduct_color),"uuid":str(dealshubproduct_obj.uuid)})
        
        temp_dict["category"] = dealshub_product_obj.get_category()
        temp_dict["currency"] = dealshub_product_obj.get_currency()
        
        temp_dict["promotional_price"] = dealshub_product_obj.promotional_price
        temp_dict["now_price"] = dealshub_product_obj.now_price
        temp_dict["was_price"] = dealshub_product_obj.was_price
        temp_dict["stock"] = dealshub_product_obj.stock
        temp_dict["is_new_arrival"] = dealshub_product_obj.is_new_arrival
        temp_dict["is_on_sale"] = dealshub_product_obj.is_on_sale
        product_promotion_details = get_product_promotion_details(dealshub_product_obj)
        for key in product_promotion_details.keys():
            temp_dict[key]=product_promotion_details[key]
        temp_dict["allowedQty"] = dealshub_product_obj.get_allowed_qty()
        if dealshub_product_obj.stock>0:
            temp_dict["isStockAvailable"] = True
        else:
            temp_dict["isStockAvailable"] = False

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("dealshub_product_detail_in_dict: %s at %s", e, str(exc_tb.tb_lineno))
    return temp_dict

def get_dealshub_product_details(dealshub_product_objs,dealshub_user_obj):
    products = []

    for dealshub_product_obj in dealshub_product_objs:
        try:
            if dealshub_product_obj.now_price==0:
                continue
            temp_dict = {}
            temp_dict["name"] = dealshub_product_obj.get_name()
            temp_dict["brand"] = dealshub_product_obj.get_brand()
            temp_dict["seller_sku"] = dealshub_product_obj.get_seller_sku()
            temp_dict["now_price"] = dealshub_product_obj.get_now_price(dealshub_user_obj)
            temp_dict["was_price"] = dealshub_product_obj.get_was_price(dealshub_user_obj)
            temp_dict["promotional_price"] = dealshub_product_obj.get_promotional_price(dealshub_user_obj)
            temp_dict["moq"] = dealshub_product_obj.get_moq(dealshub_user_obj)
            temp_dict["stock"] = dealshub_product_obj.stock
            temp_dict["is_new_arrival"] = dealshub_product_obj.is_new_arrival
            temp_dict["is_on_sale"] = dealshub_product_obj.is_on_sale
            temp_dict["allowedQty"] = dealshub_product_obj.get_allowed_qty()
            temp_dict["isStockAvailable"] = dealshub_product_obj.stock>0
            product_promotion_details = get_product_promotion_details(dealshub_product_obj)
            for key in product_promotion_details.keys():
                temp_dict[key]=product_promotion_details[key]
            temp_dict["currency"] = dealshub_product_obj.get_currency()
            temp_dict["uuid"] = dealshub_product_obj.uuid
            temp_dict["link"] = dealshub_product_obj.url
            temp_dict["id"] = dealshub_product_obj.uuid
            temp_dict["heroImageUrl"] = dealshub_product_obj.display_image_url
            products.append(temp_dict)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("get_dealshub_product_details: %s at %s", e, str(exc_tb.tb_lineno))
    return products

def bulk_upload_fake_review(oc_uuid, path,filename, location_group_obj, oc_user_obj):
    try:
        dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
        dfs.fillna("")
        rows = len(dfs.iloc[:])

        workbook = xlsxwriter.Workbook('./'+filename,{'strings_to_urls': False})
        worksheet = workbook.add_worksheet()
        row = ["No.","Product ID", "Status"]
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1})
        
        cnt=0
        colomn = 0
        for k in row:
            worksheet.write(cnt,colomn,k,header_format)
            colomn += 1
        
        for i in range(rows):
            cnt += 1
            product_id = str(dfs.iloc[i][0]).strip()
            product_id = product_id.split(".")[0]

            common_row = ["" for i in range(len(row))]
            common_row[0] = str(cnt)
            common_row[1] = product_id
            common_row[2] = ""

            try:
                product_id = str(dfs.iloc[i][0]).strip()
                product_id = product_id.split(".")[0]
                any_error = False

                if DealsHubProduct.objects.filter(location_group=location_group_obj, product__product_id=product_id).exists():
                    dealshub_product_obj = DealsHubProduct.objects.get(location_group=location_group_obj, product__product_id=product_id)
                    fake_customer_name = str(dfs.iloc[i][1]).strip()
                    subject = str(dfs.iloc[i][2]).strip()
                    content = str(dfs.iloc[i][3]).strip()
                    rating = int(dfs.iloc[i][4])
                    is_published = str(dfs.iloc[i][5]).strip().lower()
                    created_date = datetime.datetime.strptime(str(dfs.iloc[i][6]), "%Y-%m-%d %H:%M:%S")
                    if is_published =='yes':
                        is_published = True
                    elif is_published =='no':
                        is_published=False
                    else:
                        common_row[2]+='Published value is not proper.'
                        any_error = True
                    if not any_error:
                        review_content_obj = ReviewContent.objects.create(subject=subject, content=content)
                        review_obj = Review.objects.create(is_fake=True,
                                                        product=dealshub_product_obj,
                                                        rating=rating,
                                                        content=review_content_obj,
                                                        fake_customer_name=fake_customer_name,
                                                        fake_oc_user=oc_user_obj,
                                                        is_published = is_published,
                                                        created_date=created_date)
                        common_row[2] = "Success"

                else:
                    common_row[2] = "Product {} not exists.".format(product_id)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                common_row[2] = "Enter proper values."
                logger.error("bulk_upload_fake_review: %s at %s", e, str(exc_tb.tb_lineno))
            
            colnum = 0
            for k in common_row:
                worksheet.write(cnt, colnum, k)
                colnum += 1
                
        workbook.close()

        oc_report_obj = OCReport.objects.get(uuid=oc_uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("bulk_upload_fake_review: %s at %s", e, str(exc_tb.tb_lineno))

def send_b2b_user_status_change_mail(b2b_user_obj):
    try:
        logger.info("send_b2b_user_status_change_mail started!")

        website_group_obj = b2b_user_obj.website_group
        location_group_obj = LocationGroup.objects.get(website_group=website_group_obj)

        subject = b2b_user_obj.company_name + " - Change in Account Status! "
        body = 'Hi ' + b2b_user_obj.first_name + ',\n\n' + 'Your Account Status has been changed. \n\nHappy Shopping! \nTeam WIGMe'


        with get_connection(
            host=location_group_obj.get_email_host(),
            port=location_group_obj.get_email_port(),
            username=location_group_obj.get_order_from_email_id(),
            password=location_group_obj.get_order_from_email_password(),
            use_tls=True) as connection:

            email = EmailMultiAlternatives(
                        subject=subject,
                        body=body,
                        from_email=location_group_obj.get_order_from_email_id(),
                        to=[b2b_user_obj.email],
                        connection=connection
                    )
            email.send(fail_silently=False)
            logger.info("send_b2b_user_status_change_mail")

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("send_b2b_user_status_change_mail: %s at %s", e, str(exc_tb.tb_lineno))

def get_section_product_listing_details(is_dealshub, language_code,section_objs):
    dealshub_admin_sections = []
    for section_obj in section_objs:
        custom_product_section_objs = CustomProductSection.objects.filter(section=section_obj)
        if is_dealshub==True and custom_product_section_objs.exclude(product__now_price=0).exclude(product__stock=0).exists()==False:
            continue
        temp_dict = {}
        temp_dict["orderIndex"] = int(section_obj.order_index)
        temp_dict["name"] = str(section_obj.get_name(language_code))
        temp_dict["isPublished"] = section_obj.is_published
        temp_dict["type"] = "ProductListing"
        temp_dict["uuid"] = str(section_obj.uuid)
        dealshub_admin_sections.append(temp_dict)
    return dealshub_admin_sections 


def get_banner_type(banner_objs):
    dealshub_admin_sections = []
    for banner_obj in banner_objs:
        temp_dict = {}
        temp_dict["uuid"] = banner_obj.uuid
        temp_dict["name"] = banner_obj.name
        temp_dict["orderIndex"] = int(banner_obj.order_index)
        temp_dict["type"] = "Banner"
        temp_dict["isPublished"] = banner_obj.is_published
        temp_dict["bannerType"] = banner_obj.banner_type.name
        dealshub_admin_sections.append(temp_dict)
    return dealshub_admin_sections 

# utility method for FetchDealshubAdminSectionsAPI
def get_section_products(location_group_obj, is_dealshub, language_code, resolution, limit, section_objs):
    try:
        dealshub_admin_sections = []
        for section_obj in section_objs:
            custom_product_section_objs = CustomProductSection.objects.filter(section=section_obj)
            if is_dealshub==True and custom_product_section_objs.exclude(product__now_price=0).exclude(product__stock=0).exists()==False:
                continue
            temp_dict = {}
            temp_dict["orderIndex"] = int(section_obj.order_index)
            temp_dict["type"] = "ProductListing"
            temp_dict["uuid"] = str(section_obj.uuid)
            temp_dict["name"] = str(section_obj.get_name(language_code))
            temp_dict["listingType"] = str(section_obj.listing_type)
            temp_dict["createdOn"] = str(datetime.datetime.strftime(section_obj.created_date, "%d %b, %Y"))
            temp_dict["modifiedOn"] = str(datetime.datetime.strftime(section_obj.modified_date, "%d %b, %Y"))
            temp_dict["createdBy"] = str(section_obj.created_by)
            temp_dict["modifiedBy"] = str(section_obj.modified_by)
            temp_dict["isPublished"] = section_obj.is_published

            promotion_obj = section_obj.promotion
            if promotion_obj is None:
                temp_dict["is_promotional"] = False
                temp_dict["start_time"] = None
                temp_dict["end_time"] = None
                temp_dict["promotion_tag"] = None
                temp_dict["remaining_time"] = None
            else:
                temp_dict["is_promotional"] = True
                temp_dict["start_time"] = str(timezone.localtime(promotion_obj.start_time))[:19]
                temp_dict["end_time"] = str(timezone.localtime(promotion_obj.end_time))[:19]
                now_time = datetime.datetime.now()
                total_seconds = (timezone.localtime(promotion_obj.end_time).replace(tzinfo=None) - now_time).total_seconds()
                temp_dict["remaining_time"] = {
                    "days": int(total_seconds/(3600*24)),
                    "hours": int(total_seconds/3600)%24,
                    "minutes": int(total_seconds/60)%60,
                    "seconds": int(total_seconds)%60
                }
                temp_dict["promotion_tag"] = str(promotion_obj.promotion_tag)

            hovering_banner_img = section_obj.hovering_banner_image
            if hovering_banner_img is not None:
                temp_dict["hoveringBannerUuid"] = section_obj.hovering_banner_image.pk
                if resolution=="low":
                    temp_dict["hoveringBannerUrl"] = section_obj.hovering_banner_image.mid_image.url
                else:
                    temp_dict["hoveringBannerUrl"] = section_obj.hovering_banner_image.image.url
            else:
                temp_dict["hoveringBannerUrl"] = ""
                temp_dict["hoveringBannerUuid"] = ""

            temp_products = []

            custom_product_section_objs = CustomProductSection.objects.filter(section=section_obj)
            if is_dealshub==True:
                custom_product_section_objs = custom_product_section_objs.exclude(product__now_price=0).exclude(product__stock=0)

            dealshub_product_uuid_list = list(custom_product_section_objs.order_by('order_index').values_list("product__uuid", flat=True).distinct())
            
            section_products = DealsHubProduct.objects.filter(uuid__in=dealshub_product_uuid_list,is_published=True).exclude(stock=0,now_price=0)
            
            section_products = list(section_products)
            section_products.sort(key=lambda t: dealshub_product_uuid_list.index(t.uuid))
            
            section_products = section_products[:40]
            if limit==True:
                if section_obj.listing_type=="Carousel":
                    section_products = section_products[:14]
                elif section_obj.listing_type=="Grid Stack":
                    section_products = section_products[:14]

            for dealshub_product_obj in section_products:
                if dealshub_product_obj.now_price==0:
                    continue
                temp_dict2 = {}

                temp_dict2["thumbnailImageUrl"] = dealshub_product_obj.get_display_image_url()
                temp_dict2["optimizedThumbnailImageUrl"] = dealshub_product_obj.get_optimized_display_image_url()
                temp_dict2["name"] = dealshub_product_obj.get_name(language_code)
                temp_dict2["sellerSku"] = dealshub_product_obj.get_seller_sku()
                temp_dict2["brand"] = dealshub_product_obj.get_brand(language_code)
                temp_dict2["displayId"] = dealshub_product_obj.get_product_id()
                temp_dict2["uuid"] = dealshub_product_obj.uuid
                temp_dict2["link"] = dealshub_product_obj.url
                dealshub_product_obj_base_product = dealshub_product_obj.product.base_product
                dealshub_same_baseproduct_objs = DealsHubProduct.objects.filter(location_group=location_group_obj,product__base_product = dealshub_product_obj_base_product,is_published=True).exclude(now_price=0).exclude(stock=0)
                temp_dict2["color_list"] = []
                if dealshub_same_baseproduct_objs.count()>1:
                    for dealshubproduct_obj in dealshub_same_baseproduct_objs:
                        dealshubproduct_color = dealshubproduct_obj.product.color
                        temp_dict2["color_list"].append({"color":str(dealshubproduct_color),"uuid":str(dealshubproduct_obj.uuid)})
                
                if is_dealshub==True:
                    temp_dict2["category"] = dealshub_product_obj.get_category(language_code)
                    temp_dict2["currency"] = dealshub_product_obj.get_currency()
                
                temp_dict2["promotional_price"] = dealshub_product_obj.promotional_price
                temp_dict2["now_price"] = dealshub_product_obj.now_price
                temp_dict2["was_price"] = dealshub_product_obj.was_price
                temp_dict2["stock"] = dealshub_product_obj.stock
                temp_dict2["is_new_arrival"] = dealshub_product_obj.is_new_arrival
                temp_dict2["is_on_sale"] = dealshub_product_obj.is_on_sale
                if promotion_obj==None:
                    product_promotion_details = get_product_promotion_details(dealshub_product_obj)
                    for key in product_promotion_details.keys():
                        temp_dict2[key]=product_promotion_details[key]
                temp_dict2["allowedQty"] = dealshub_product_obj.get_allowed_qty()
                if dealshub_product_obj.stock>0:
                    temp_dict2["isStockAvailable"] = True
                else:
                    temp_dict2["isStockAvailable"] = False

                temp_products.append(temp_dict2)
            temp_dict["products"] = temp_products

            dealshub_admin_sections.append(temp_dict)
        return dealshub_admin_sections
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("FetchDealshubAdminSectionsAPI get_section_products: %s at %s", e, str(exc_tb.tb_lineno))

def get_section_product_b2b(location_group_obj, is_dealshub, language_code, resolution, limit, section_objs,dealshub_user_obj=None):
    try:
        dealshub_admin_sections = []
        for section_obj in section_objs:
            custom_product_section_objs = CustomProductSection.objects.filter(section=section_obj)
            if is_dealshub==True and custom_product_section_objs.exclude(product__now_price=0).exclude(product__stock=0).exists()==False:
                continue
            temp_dict = {}
            temp_dict["orderIndex"] = section_obj.order_index
            temp_dict["type"] = "ProductListing"
            temp_dict["uuid"] = str(section_obj.uuid)
            temp_dict["name"] = str(section_obj.name)
            temp_dict["listingType"] = str(section_obj.listing_type)
            temp_dict["createdOn"] = str(datetime.datetime.strftime(section_obj.created_date, "%d %b, %Y"))
            temp_dict["modifiedOn"] = str(datetime.datetime.strftime(section_obj.modified_date, "%d %b, %Y"))
            temp_dict["createdBy"] = str(section_obj.created_by)
            temp_dict["modifiedBy"] = str(section_obj.modified_by)
            temp_dict["isPublished"] = section_obj.is_published

            promotion_obj = section_obj.promotion
            if promotion_obj is None:
                temp_dict["is_promotional"] = False
                temp_dict["start_time"] = None
                temp_dict["end_time"] = None
                temp_dict["promotion_tag"] = None
                temp_dict["remaining_time"] = None
            else:
                temp_dict["is_promotional"] = True
                temp_dict["start_time"] = str(timezone.localtime(promotion_obj.start_time))[:19]
                temp_dict["end_time"] = str(timezone.localtime(promotion_obj.end_time))[:19]
                now_time = datetime.datetime.now()
                total_seconds = (timezone.localtime(promotion_obj.end_time).replace(tzinfo=None) - now_time).total_seconds()
                temp_dict["remaining_time"] = {
                    "days": int(total_seconds/(3600*24)),
                    "hours": int(total_seconds/3600)%24,
                    "minutes": int(total_seconds/60)%60,
                    "seconds": int(total_seconds)%60
                }
                temp_dict["promotion_tag"] = str(promotion_obj.promotion_tag)

            hovering_banner_img = section_obj.hovering_banner_image
            if hovering_banner_img is not None:
                temp_dict["hoveringBannerUuid"] = section_obj.hovering_banner_image.pk
                if resolution=="low":
                    temp_dict["hoveringBannerUrl"] = section_obj.hovering_banner_image.mid_image.url
                else:
                    temp_dict["hoveringBannerUrl"] = section_obj.hovering_banner_image.image.url
            else:
                temp_dict["hoveringBannerUrl"] = ""
                temp_dict["hoveringBannerUuid"] = ""

            temp_products = []

            custom_product_section_objs = CustomProductSection.objects.filter(section=section_obj)
            if is_dealshub==True:
                custom_product_section_objs = custom_product_section_objs.exclude(product__now_price=0).exclude(product__stock=0)

            dealshub_product_uuid_list = list(custom_product_section_objs.order_by('order_index').values_list("product__uuid", flat=True).distinct())
            
            section_products = DealsHubProduct.objects.filter(uuid__in=dealshub_product_uuid_list)
            
            section_products = list(section_products)
            section_products.sort(key=lambda t: dealshub_product_uuid_list.index(t.uuid))
            
            section_products = section_products[:40]
            if limit==True:
                if section_obj.listing_type=="Carousel":
                    section_products = section_products[:14]
                elif section_obj.listing_type=="Grid Stack":
                    section_products = section_products[:14]

            for dealshub_product_obj in section_products:
                if dealshub_product_obj.now_price==0:
                    continue
                temp_dict2 = {}

                temp_dict2["thumbnailImageUrl"] = dealshub_product_obj.get_display_image_url()
                temp_dict2["optimizedThumbnailImageUrl"] = dealshub_product_obj.get_optimized_display_image_url()
                temp_dict2["name"] = dealshub_product_obj.get_name(language_code)
                temp_dict2["sellerSku"] = dealshub_product_obj.get_seller_sku()
                temp_dict2["brand"] = dealshub_product_obj.get_brand(language_code)
                temp_dict2["displayId"] = dealshub_product_obj.get_product_id()
                temp_dict2["uuid"] = dealshub_product_obj.uuid
                temp_dict2["link"] = dealshub_product_obj.url

                if is_dealshub==True:
                    temp_dict2["category"] = dealshub_product_obj.get_category(language_code)
                    temp_dict2["currency"] = dealshub_product_obj.get_currency()
                    temp_dict2["promotional_price"] = dealshub_product_obj.get_promotional_price(dealshub_user_obj)
                    temp_dict2["now_price"] = dealshub_product_obj.get_now_price(dealshub_user_obj)
                else:
                    temp_dict2["now_price"] = dealshub_product_obj.now_price
                    temp_dict2["now_price_cohort1"] = dealshub_product_obj.now_price_cohort1
                    temp_dict2["now_price_cohort2"] = dealshub_product_obj.now_price_cohort2
                    temp_dict2["now_price_cohort3"] = dealshub_product_obj.now_price_cohort3
                    temp_dict2["now_price_cohort4"] = dealshub_product_obj.now_price_cohort4
                    temp_dict2["now_price_cohort5"] = dealshub_product_obj.now_price_cohort5

                    temp_dict2["promotional_price"] = dealshub_product_obj.promotional_price
                    temp_dict2["promotional_price_cohort1"] = dealshub_product_obj.promotional_price_cohort1
                    temp_dict2["promotional_price_cohort2"] = dealshub_product_obj.promotional_price_cohort2
                    temp_dict2["promotional_price_cohort3"] = dealshub_product_obj.promotional_price_cohort3
                    temp_dict2["promotional_price_cohort4"] = dealshub_product_obj.promotional_price_cohort4
                    temp_dict2["promotional_price_cohort5"] = dealshub_product_obj.promotional_price_cohort5

                temp_dict2["was_price"] = dealshub_product_obj.get_was_price(dealshub_user_obj)
                temp_dict2["moq"] = dealshub_product_obj.get_moq(dealshub_user_obj)
                temp_dict2["stock"] = dealshub_product_obj.stock
                temp_dict2["is_new_arrival"] = dealshub_product_obj.is_new_arrival
                temp_dict2["is_on_sale"] = dealshub_product_obj.is_on_sale
                if promotion_obj==None:
                    product_promotion_details = get_product_promotion_details(dealshub_product_obj)
                    for key in product_promotion_details.keys():
                        temp_dict2[key]=product_promotion_details[key]
                temp_dict2["allowedQty"] = dealshub_product_obj.get_allowed_qty()
                if dealshub_product_obj.stock>0:
                    temp_dict2["isStockAvailable"] = True
                else:
                    temp_dict2["isStockAvailable"] = False

                temp_products.append(temp_dict2)
            temp_dict["products"] = temp_products
            dealshub_admin_sections.append(temp_dict)

        return dealshub_admin_sections
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("FetchB2BDealshubAdminSectionsAPI get_section_products: %s at %s", e, str(exc_tb.tb_lineno))        

def get_banner_image_objects_b2b(is_dealshub, language_code, resolution, banner_objs):
    try:
        dealshub_admin_sections = []
        for banner_obj in banner_objs:
            unit_banner_image_objs = UnitBannerImage.objects.filter(banner=banner_obj)

            if is_dealshub:
                valid_unit_banner_image_objs = UnitBannerImage.objects.none()
                for unit_banner_image_obj in unit_banner_image_objs:
                    promotion_obj = unit_banner_image_obj.promotion
                    if promotion_obj is not None:
                        if check_valid_promotion(promotion_obj):
                            valid_unit_banner_image_objs |= UnitBannerImage.objects.filter(pk=unit_banner_image_obj.pk)
                    else:
                        valid_unit_banner_image_objs |= UnitBannerImage.objects.filter(pk=unit_banner_image_obj.pk)
                unit_banner_image_objs = valid_unit_banner_image_objs

            banner_images = []
            temp_dict = {}
            temp_dict["orderIndex"] = banner_obj.order_index
            temp_dict["type"] = "Banner"
            temp_dict["uuid"] = banner_obj.uuid
            temp_dict["name"] = banner_obj.name
            temp_dict["bannerType"] = banner_obj.banner_type.name
            temp_dict["limit"] = banner_obj.banner_type.limit
            for unit_banner_image_obj in unit_banner_image_objs:
                temp_dict2 = {}
                temp_dict2["uid"] = unit_banner_image_obj.uuid
                temp_dict2["httpLink"] = unit_banner_image_obj.http_link
                temp_dict2["url"] = ""
                temp_dict2["url-ar"] = ""

                try:
                    if unit_banner_image_obj.image!=None:
                        if resolution=="low":
                            temp_dict2["url"] = unit_banner_image_obj.image.mid_image.url
                            if unit_banner_image_obj.image_ar!=None:
                                temp_dict2["url-ar"] = unit_banner_image_obj.image_ar.mid_image.url
                            else:
                                temp_dict2["url-ar"] = unit_banner_image_obj.image.mid_image.url
                        else:
                            temp_dict2["url-jpg"] = unit_banner_image_obj.image.image.url
                            temp_dict2["url"] = unit_banner_image_obj.image.image.url
                            temp_dict2["urlWebp"] = unit_banner_image_obj.image.webp_image.url
                            if unit_banner_image_obj.image_ar!=None:
                                temp_dict2["url-jpg-ar"] = unit_banner_image_obj.image_ar.image.url
                                temp_dict2["url-ar"] = unit_banner_image_obj.image_ar.image.url
                                temp_dict2["urlWebp-ar"] = unit_banner_image_obj.image_ar.webp_image.url
                            else:
                                temp_dict2["url-jpg-ar"] = unit_banner_image_obj.image.image.url
                                temp_dict2["url-ar"] = unit_banner_image_obj.image.image.url
                                temp_dict2["urlWebp-ar"] = unit_banner_image_obj.image.webp_image.url
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchB2BDealshubAdminSectionsAPI: %s at %s with image %s", e, str(exc_tb.tb_lineno),  str(unit_banner_image_obj.uuid))

                temp_dict2["mobileUrl"] = ""
                temp_dict2["mobileUrl-ar"] = ""
                if unit_banner_image_obj.mobile_image!=None:
                    if resolution=="low":
                        temp_dict2["mobileUrl"] = unit_banner_image_obj.mobile_image.mid_image.url
                        if unit_banner_image_obj.mobile_image_ar!=None:
                            temp_dict2["mobileUrl-ar"] = unit_banner_image_obj.mobile_image_ar.mid_image.url
                        else:
                            temp_dict2["mobileUrl-ar"] = unit_banner_image_obj.mobile_image.mid_image.url
                    else:
                        temp_dict2["mobileUrl-jpg"] = unit_banner_image_obj.mobile_image.image.url
                        temp_dict2["mobileUrl"] = unit_banner_image_obj.mobile_image.image.url
                        temp_dict2["mobileUrlWebp"] = unit_banner_image_obj.mobile_image.webp_image.url
                        if unit_banner_image_obj.mobile_image_ar!=None:
                            temp_dict2["mobileUrl-jpg-ar"] = unit_banner_image_obj.mobile_image_ar.image.url
                            temp_dict2["mobileUrl-ar"] = unit_banner_image_obj.mobile_image_ar.image.url
                            temp_dict2["mobileUrlWebp-ar"] = unit_banner_image_obj.mobile_image_ar.webp_image.url
                        else:
                            temp_dict2["mobileUrl-jpg-ar"] = unit_banner_image_obj.mobile_image.image.url
                            temp_dict2["mobileUrl-ar"] = unit_banner_image_obj.mobile_image.image.url
                            temp_dict2["mobileUrlWebp-ar"] = unit_banner_image_obj.mobile_image.webp_image.url

                hovering_banner_img = unit_banner_image_obj.hovering_banner_image
                if hovering_banner_img is not None:
                    temp_dict2["hoveringBannerUuid"] = unit_banner_image_obj.hovering_banner_image.pk
                    if resolution=="low":
                        temp_dict2["hoveringBannerUrl"] = unit_banner_image_obj.hovering_banner_image.mid_image.url
                    else:
                        temp_dict2["hoveringBannerUrl"] = unit_banner_image_obj.hovering_banner_image.image.url
                else:
                    temp_dict2["hoveringBannerUrl"] = ""
                    temp_dict2["hoveringBannerUuid"] = ""

                promotion_obj = unit_banner_image_obj.promotion
                if promotion_obj is None:
                    temp_dict2["is_promotional"] = False
                    temp_dict2["start_time"] = None
                    temp_dict2["end_time"] = None
                    temp_dict2["promotion_tag"] = None
                else:
                    temp_dict2["is_promotional"] = True
                    temp_dict2["start_time"] = str(timezone.localtime(promotion_obj.start_time))[:19]
                    temp_dict2["end_time"] = str(timezone.localtime(promotion_obj.end_time))[:19]
                    temp_dict2["promotion_tag"] = str(promotion_obj.promotion_tag)


                custom_product_unit_banner_objs = CustomProductUnitBanner.objects.filter(unit_banner=unit_banner_image_obj)
                if is_dealshub==True:
                    custom_product_unit_banner_objs = custom_product_unit_banner_objs.exclude(product__now_price=0).exclude(product__stock=0)

                dealshub_product_uuid_list = list(custom_product_unit_banner_objs.order_by('order_index').values_list("product__uuid", flat=True).distinct())
                unit_banner_products = DealsHubProduct.objects.filter(uuid__in=dealshub_product_uuid_list)

                unit_banner_products = list(unit_banner_products)
                unit_banner_products.sort(key=lambda t: dealshub_product_uuid_list.index(t.uuid))

                if is_dealshub==False :
                    temp_products = []
                    for dealshub_product_obj in unit_banner_products[:40]:
                        if dealshub_product_obj.now_price==0:
                            continue
                        temp_dict3 = {}

                        temp_dict3["thumbnailImageUrl"] = dealshub_product_obj.get_display_image_url()
                        temp_dict3["optimizedThumbnailImageUrl"] = dealshub_product_obj.get_optimized_display_image_url()
                        temp_dict3["name"] = dealshub_product_obj.get_name(language_code)
                        temp_dict3["displayId"] = dealshub_product_obj.get_product_id()
                        temp_dict3["sellerSku"] = dealshub_product_obj.get_seller_sku()
                        temp_dict3["brand"] = dealshub_product_obj.get_brand(language_code)
                        temp_dict3["uuid"] = dealshub_product_obj.uuid
                        temp_dict3["link"] = dealshub_product_obj.url

                        promotion_obj = dealshub_product_obj.promotion

                        temp_dict3["promotional_price"] = dealshub_product_obj.promotional_price
                        temp_dict3["now_price"] = dealshub_product_obj.now_price
                        temp_dict3["was_price"] = dealshub_product_obj.was_price
                        temp_dict3["stock"] = dealshub_product_obj.stock
                        temp_dict3["allowedQty"] = dealshub_product_obj.get_allowed_qty()
                        if dealshub_product_obj.stock>0:
                            temp_dict3["isStockAvailable"] = True
                        else:
                            temp_dict3["isStockAvailable"] = False

                        temp_products.append(temp_dict3)    # No need to Send all
                    temp_dict2["products"] = temp_products
                
                temp_dict2["has_products"] = len(unit_banner_products)>0
                banner_images.append(temp_dict2)

            temp_dict["bannerImages"] = banner_images
            temp_dict["isPublished"] = banner_obj.is_published

            dealshub_admin_sections.append(temp_dict)
        return dealshub_admin_sections
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("FetchB2BDealshubAdminSectionsAPI get_banner_image_objects: %s at %s", e, str(exc_tb.tb_lineno))
# utility method for FetchDealshubAdminSectionsAPI
def get_banner_image_objects(is_dealshub, language_code, resolution, banner_objs):
    try:
        dealshub_admin_sections = []
        for banner_obj in banner_objs:
            unit_banner_image_objs = UnitBannerImage.objects.filter(banner=banner_obj)

            if is_dealshub:
                valid_unit_banner_image_objs = UnitBannerImage.objects.none()
                for unit_banner_image_obj in unit_banner_image_objs:
                    promotion_obj = unit_banner_image_obj.promotion
                    if promotion_obj is not None:
                        if check_valid_promotion(promotion_obj):
                            valid_unit_banner_image_objs |= UnitBannerImage.objects.filter(pk=unit_banner_image_obj.pk)
                    else:
                        valid_unit_banner_image_objs |= UnitBannerImage.objects.filter(pk=unit_banner_image_obj.pk)
                unit_banner_image_objs = valid_unit_banner_image_objs

            banner_images = []
            temp_dict = {}
            temp_dict["orderIndex"] = int(banner_obj.order_index)
            temp_dict["type"] = "Banner"
            temp_dict["uuid"] = banner_obj.uuid
            temp_dict["name"] = banner_obj.name
            temp_dict["bannerType"] = banner_obj.banner_type.name
            temp_dict["limit"] = banner_obj.banner_type.limit
            temp_dict["is_nested"] = banner_obj.is_nested
            for unit_banner_image_obj in unit_banner_image_objs:
                temp_dict2 = {}
                temp_dict2["uid"] = unit_banner_image_obj.uuid
                temp_dict2["httpLink"] = unit_banner_image_obj.http_link
                temp_dict2["url"] = ""
                temp_dict2["url-ar"] = ""
                try:
                    if unit_banner_image_obj.image!=None:
                        if resolution=="low":
                            temp_dict2["url"] = unit_banner_image_obj.image.mid_image.url
                            if unit_banner_image_obj.image_ar!=None:
                                temp_dict2["url-ar"] = unit_banner_image_obj.image_ar.mid_image.url
                            else:
                                temp_dict2["url-ar"] = ""
                        else:
                            if unit_banner_image_obj.image.optimal_image!=None:
                                temp_dict2["url-jpg"] = unit_banner_image_obj.image.optimal_image.url
                                temp_dict2["url"] = unit_banner_image_obj.image.optimal_image.url
                            else:
                                temp_dict2["url-jpg"] = unit_banner_image_obj.image.image.url
                                temp_dict2["url"] = unit_banner_image_obj.image.image.url
                            temp_dict2["urlWebp"] = unit_banner_image_obj.image.webp_image.url
                            if unit_banner_image_obj.image_ar!=None:
                                if unit_banner_image_obj.image.optimal_image!=None:
                                    temp_dict2["url-jpg-ar"] = unit_banner_image_obj.image_ar.optimal_image.url
                                    temp_dict2["url-ar"] = unit_banner_image_obj.image_ar.optimal_image.url
                                else:
                                    temp_dict2["url-jpg-ar"] = unit_banner_image_obj.image_ar.image.url
                                    temp_dict2["url-ar"] = unit_banner_image_obj.image_ar.image.url
                                temp_dict2["urlWebp-ar"] = unit_banner_image_obj.image_ar.webp_image.url
                            else:
                                if unit_banner_image_obj.image.optimal_image!=None:
                                    temp_dict2["url-jpg"] = unit_banner_image_obj.image.optimal_image.url
                                    temp_dict2["url"] = unit_banner_image_obj.image.optimal_image.url
                                else:
                                    temp_dict2["url-jpg"] = unit_banner_image_obj.image.image.url
                                    temp_dict2["url"] = unit_banner_image_obj.image.image.url
                                temp_dict2["urlWebp-ar"] = unit_banner_image_obj.image.webp_image.url
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchDealshubAdminSectionsAPI get_banner_image_objects: %s at %s with image %s", e, str(exc_tb.tb_lineno), str(unit_banner_image_obj.uuid))

                temp_dict2["mobileUrl"] = ""
                temp_dict2["mobileUrl-ar"] = ""
                try:
                    if unit_banner_image_obj.mobile_image!=None:
                        if resolution=="low":
                            temp_dict2["mobileUrl"] = unit_banner_image_obj.mobile_image.mid_image.url
                            if unit_banner_image_obj.mobile_image_ar!=None:
                                temp_dict2["mobileUrl-ar"] = unit_banner_image_obj.mobile_image_ar.mid_image.url
                            else:
                                temp_dict2["mobileUrl-ar"] = ""
                        else:
                            if unit_banner_image_obj.mobile_image.optimal_image!=None:
                                temp_dict2["mobileUrl-jpg"] = unit_banner_image_obj.mobile_image.optimal_image.url
                                temp_dict2["mobileUrl"] = unit_banner_image_obj.mobile_image.optimal_image.url
                            else:
                                temp_dict2["mobileUrl-jpg"] = unit_banner_image_obj.mobile_image.image.url
                                temp_dict2["mobileUrl"] = unit_banner_image_obj.mobile_image.image.url
                            temp_dict2["mobileUrlWebp"] = unit_banner_image_obj.mobile_image.webp_image.url
                            if unit_banner_image_obj.mobile_image_ar!=None:
                                if unit_banner_image_obj.mobile_image_ar.optimal_image!=None:   
                                    temp_dict2["mobileUrl-jpg-ar"] = unit_banner_image_obj.mobile_image_ar.optimal_image.url
                                    temp_dict2["mobileUrl-ar"] = unit_banner_image_obj.mobile_image_ar.optimal_image.url
                                else:
                                    temp_dict2["mobileUrl-jpg-ar"] = unit_banner_image_obj.mobile_image_ar.image.url
                                    temp_dict2["mobileUrl-ar"] = unit_banner_image_obj.mobile_image_ar.image.url
                                temp_dict2["mobileUrlWebp-ar"] = unit_banner_image_obj.mobile_image_ar.webp_image.url
                            else:
                                if unit_banner_image_obj.mobile_image.optimal_image!=None:
                                    temp_dict2["mobileUrl-jpg-ar"] = unit_banner_image_obj.mobile_image.optimal_image.url
                                    temp_dict2["mobileUrl-ar"] = unit_banner_image_obj.mobile_image.optimal_image.url
                                else:
                                    temp_dict2["mobileUrl-jpg-ar"] = unit_banner_image_obj.mobile_image.image.url
                                    temp_dict2["mobileUrl-ar"] = unit_banner_image_obj.mobile_image.image.url
                                temp_dict2["mobileUrlWebp-ar"] = unit_banner_image_obj.mobile_image.webp_image.url
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchDealshubAdminSectionsAPI get_banner_image_objects: %s at %s with image %s", e, str(exc_tb.tb_lineno), str(unit_banner_image_obj.uuid))

                hovering_banner_img = unit_banner_image_obj.hovering_banner_image
                if hovering_banner_img is not None:
                    temp_dict2["hoveringBannerUuid"] = unit_banner_image_obj.hovering_banner_image.pk
                    if resolution=="low":
                        temp_dict2["hoveringBannerUrl"] = unit_banner_image_obj.hovering_banner_image.mid_image.url
                    else:
                        if unit_banner_image_obj.hovering_banner_image.optimal_image!=None:  
                            temp_dict2["hoveringBannerUrl"] = unit_banner_image_obj.hovering_banner_image.optimal_image.url
                        else:
                            temp_dict2["hoveringBannerUrl"] = unit_banner_image_obj.hovering_banner_image.image.url
                else:
                    temp_dict2["hoveringBannerUrl"] = ""
                    temp_dict2["hoveringBannerUuid"] = ""

                promotion_obj = unit_banner_image_obj.promotion
                if promotion_obj is None:
                    temp_dict2["is_promotional"] = False
                    temp_dict2["start_time"] = None
                    temp_dict2["end_time"] = None
                    temp_dict2["promotion_tag"] = None
                else:
                    temp_dict2["is_promotional"] = True
                    temp_dict2["start_time"] = str(timezone.localtime(promotion_obj.start_time))[:19]
                    temp_dict2["end_time"] = str(timezone.localtime(promotion_obj.end_time))[:19]
                    temp_dict2["promotion_tag"] = str(promotion_obj.promotion_tag)


                custom_product_unit_banner_objs = CustomProductUnitBanner.objects.filter(unit_banner=unit_banner_image_obj)
                if is_dealshub==True:
                    custom_product_unit_banner_objs = custom_product_unit_banner_objs.exclude(product__now_price=0).exclude(product__stock=0)

                dealshub_product_uuid_list = list(custom_product_unit_banner_objs.order_by('order_index').values_list("product__uuid", flat=True).distinct())
                unit_banner_products = DealsHubProduct.objects.filter(uuid__in=dealshub_product_uuid_list)

                unit_banner_products = list(unit_banner_products)
                unit_banner_products.sort(key=lambda t: dealshub_product_uuid_list.index(t.uuid))

                if is_dealshub==False :
                    temp_products = []
                    for dealshub_product_obj in unit_banner_products[:40]:
                        if dealshub_product_obj.now_price==0:
                            continue
                        temp_dict3 = {}

                        temp_dict3["thumbnailImageUrl"] = dealshub_product_obj.get_display_image_url()
                        temp_dict3["optimizedThumbnailImageUrl"] = dealshub_product_obj.get_optimized_display_image_url()
                        temp_dict3["name"] = dealshub_product_obj.get_name(language_code)
                        temp_dict3["displayId"] = dealshub_product_obj.get_product_id()
                        temp_dict3["sellerSku"] = dealshub_product_obj.get_seller_sku()
                        temp_dict3["brand"] = dealshub_product_obj.get_brand(language_code)
                        temp_dict3["uuid"] = dealshub_product_obj.uuid
                        temp_dict3["link"] = dealshub_product_obj.url

                        promotion_obj = dealshub_product_obj.promotion

                        temp_dict3["promotional_price"] = dealshub_product_obj.promotional_price
                        temp_dict3["now_price"] = dealshub_product_obj.now_price
                        temp_dict3["was_price"] = dealshub_product_obj.was_price
                        temp_dict3["stock"] = dealshub_product_obj.stock
                        temp_dict3["allowedQty"] = dealshub_product_obj.get_allowed_qty()
                        if dealshub_product_obj.stock>0:
                            temp_dict3["isStockAvailable"] = True
                        else:
                            temp_dict3["isStockAvailable"] = False

                        temp_products.append(temp_dict3)    # No need to Send all
                    temp_dict2["products"] = temp_products
                
                temp_dict2["has_products"] = len(unit_banner_products)>0
                banner_images.append(temp_dict2)

            temp_dict["bannerImages"] = banner_images
            temp_dict["isPublished"] = banner_obj.is_published

            dealshub_admin_sections.append(temp_dict)
        return dealshub_admin_sections
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("FetchDealshubAdminSectionsAPI get_banner_image_objects: %s at %s", e, str(exc_tb.tb_lineno))

def sendex_add_consignment(order_obj, modified_weight):
    api_response = "failure"
    try:
        sendex_dict = {}
        address = order_obj.shipping_address
        sendex_dict["ToCompany"] = order_obj.get_customer_full_name()
        sendex_dict["ToAddress"] = address.get_address()
        sendex_dict["ToLocation"] = address.emirates
        sendex_dict["ToCountry"] = address.get_country()
        sendex_dict["ToCPerson"] = order_obj.get_customer_full_name()
        sendex_dict["ToContactno"] = address.contact_number
        sendex_dict["ToMobileno"] = ""
        sendex_dict["ReferenceNumber"] = str(order_obj.bundleid)
        sendex_dict["CompanyCode"] = ""
        sendex_dict["Weight"] = str(float(modified_weight))
        sendex_dict["Pieces"] = str(order_obj.get_total_quantity())
        sendex_dict["PackageType"] = "Parcel"
        sendex_dict["CurrencyCode"] = order_obj.get_currency()
        sendex_dict["NcndAmount"] = str(float(order_obj.get_sendex_ncnd_amount()))
        sendex_dict["ItemDescription"] = get_sellersku_and_quantity(order_obj)
        sendex_dict["SpecialInstruction"] = order_obj.additional_note
        sendex_dict["BranchName"] = "Dubai"
        response = get_sendex_api_response(sendex_dict, SENDEX_ADD_CONSIGNMENT_URL)
        order_obj.sendex_request_json = json.dumps(sendex_dict)
        order_obj.sendex_response_json = json.dumps(response)
        order_obj.save()
        logger.info("sendex_add_consignment: req:%s response:%s", str(sendex_dict), str(response))
        if response["success"] == 1:
            order_obj.sendex_awb = response["AwbNumber"]
            order_obj.sendex_awb_pdf = response["AwbPdf"]
            order_obj.save()
            api_response = "success"

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("SetShippingMethodAPI's utility - sendex add consignment: %s at %s", e, str(exc_tb.tb_lineno))

    return api_response

def get_sendex_api_response(sendex_dict, request_url):
    http_header = {
        "Content-Type" : "application/json",
        "API-KEY" : SENDEX_API_KEY
    }
    response = requests.post(url=request_url, headers=http_header, data=json.dumps(sendex_dict), timeout=10)
    response_dict = json.loads(response.content)
    return response_dict

# [SENDEX] updates the shipping status of all the orders which were registered as a consignment.
def update_sendex_consignment_status(order_objs, oc_user):
    try:
        order_objs = order_objs.exclude(sendex_awb="")
        sendex_dict = {
            "AwbNumber": list(order_objs.values_list('sendex_awb', flat=True).distinct())
        }
        if len(sendex_dict["AwbNumber"]) <= 0:
            return
        response = get_sendex_api_response(sendex_dict, SENDEX_TRACK_CONSIGNMENT_STATUS_URL)
        i = 0
        logger.info("update_sendex_consignment_status: request: %s, response: %s", str(sendex_dict), str(response))
        for order_obj in order_objs:
            try:
                if (i < len(response["TrackResponse"])) and order_obj.sendex_awb == response["TrackResponse"][i]["Shipment"]["awb_number"]:
                    sendex_status = response["TrackResponse"][i]["Shipment"]["current_status"]
                    status_admin = get_mapped_admin_status(sendex_status)
                    update_shipping_status_in_unit_orders(order_obj, status_admin, oc_user)
                    order_obj.sendex_tracking_reference = json.dumps(response["TrackResponse"][i]["Shipment"])
                    order_obj.save()
                    i += 1

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("update_sendex_consignment_status: %s at %s", e, str(exc_tb.tb_lineno))

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("update_sendex_consignment_status: %s at %s", e, str(exc_tb.tb_lineno))

def update_shipping_status_in_unit_orders(order_obj, order_status, oc_user):
    unit_order_objs = UnitOrder.objects.filter(order=order_obj).exclude(current_status_admin="cancelled")

    if order_status == unit_order_objs[0].current_status_admin:
        return

    old_order_status = unit_order_objs[0].current_status_admin
    for unit_order_obj in unit_order_objs:
        set_order_status(unit_order_obj, order_status)
        
    order_status_change_information = {
        "event": "order_status",
        "information": {
            "old_status": old_order_status,
            "new_status": order_status
        }
    }
    VersionOrder.objects.create(order=order_obj,
                                user= oc_user,
                                change_information=json.dumps(order_status_change_information))

    
# maps the status present in sendex response to locally maintained statuses 
def get_mapped_admin_status(sendex_status):
    if sendex_status.lower() in SENDEX_PHRASE_TO_STATUS:
        return SENDEX_PHRASE_TO_STATUS[sendex_status.lower()]
    elif sendex_status in SENDEX_CODE_TO_STATUS:
        return SENDEX_CODE_TO_STATUS[sendex_status]
    else:
        raise ValueError("update_sendex_consignment_status: Sendex API returned an unknown status code: %s", str(sendex_status))


def bulk_update_order_status(list_of_orders):
    try:
        for order in list_of_orders:
            try:
                sap_invoice_id = order["sap_invoice_id"]
                incoming_order_status = order["incoming_order_status"]

                order_obj = Order.objects.get(sap_final_billing_info__icontains=sap_invoice_id)
                doc_list = json.loads(order_obj.sap_final_billing_info)["doc_list"]
                flag = False
                for doc in doc_list:
                    if doc["id"]==sap_invoice_id:
                        flag = True
                        break

                if flag==False:
                    break

                unit_order_objs = UnitOrder.objects.filter(order = order_obj)

                for unit_order_obj in unit_order_objs:
                    if incoming_order_status == "dispatched" and unit_order_obj.current_status_admin == "picked":          
                        set_order_status(unit_order_obj, "dispatched")
                    elif incoming_order_status == "delivered" and unit_order_obj.current_status_admin == "dispatched":
                        set_order_status(unit_order_obj, "delivered")
                    else:
                        logger.warning("UpdateOrderStatusAPI: Bad transition request-400")
                        break
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("UpdateOrderStatusAPI: %s at %s", str(e), str(exc_tb.tb_lineno))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("UpdateOrderStatusAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

def sap_manual_update(order_obj, oc_user): 
    for unit_order_obj in UnitOrder.objects.filter(order=order_obj).exclude(current_status_admin="cancelled"):
        set_order_status(unit_order_obj,"picked")
    order_obj.sap_status = "Success"
    order_obj.sap_manual_update_status = True
    order_obj.save()
    order_status_change_information = {
        "event": "order_status",
        "information": {
            "old_status": "approved",
            "new_status": "picked"
        }
    }
    VersionOrder.objects.create(order=order_obj,
                                user=oc_user,
                                change_information=json.dumps(order_status_change_information)
                                )


def sha256_encode(string):
    result = hashlib.sha256(string.encode())
    return result.hexdigest()


def calling_facebook_api(event_name,user,request,custom_data=None):
    try:
        email = sha256_encode(str(user.email))
        first_name = sha256_encode(str(user.first_name))
        last_name = sha256_encode(str(user.last_name))
        address_obj = Address.objects.filter(user=user).first()
        contact_number = sha256_encode(str(address_obj.contact_number))
        state = sha256_encode(str(address_obj.state))
        country = sha256_encode(str(address_obj.get_country()))
        postcode = sha256_encode(str(address_obj.postcode))

        access_token = "EAAFwjqw5ZBQoBAEPNNkat7AkfrDZCqDs9MIYf6jKHDdHTiqwrqwTZCHNBK4xHJqVZBoIvF1PBdl5dezVOZBE2NSzoXuwjM5Vq1ca5LvZC4D2UaJiZAZBXZAyWsWT7Y0sY7QKpSUsMppY3l91HuxLBHYFOorYcyZCDoJIi87mMtO6P9wmC9IzldfGTG"
        pixel_id = '501666847923989'
        event_source_url = "https://b2b.wigme.com"

        now_time = int(time.time())
        # logger.info("in calling_facebook_api:- ")
        # x_forwarded_for = request.META["HTTP_X_FORWARDED_FOR"]
        # logger.info(request.META)

        FacebookAdsApi.init(access_token=access_token)

        user_data = UserData(
            emails=[email],
            first_names=[first_name],
            last_names=[last_name],
            phones=[contact_number],
            cities=[],
            states=[state],
            zip_codes=[postcode],
            country_codes=[country],
            client_ip_address=request.META["HTTP_X_FORWARDED_FOR"],
            client_user_agent=request.META["HTTP_USER_AGENT"],
            fbp= "fb.1.1627378308009.637490042",
        )

        events = []
        if custom_data == None:
            event = Event(
                event_name=event_name,
                event_time=now_time,
                user_data=user_data,
                event_source_url= event_source_url,
                action_source=ActionSource.WEBSITE,
            )
            events = [event]

        else:
            for custom_data_item in custom_data:
                event = Event(
                    event_name=event_name,
                    event_time=now_time,
                    user_data=user_data,
                    event_source_url= event_source_url, 
                    action_source=ActionSource.WEBSITE,
                    custom_data=custom_data_item,
                )
                events.append(event)
    
        event_request = EventRequest(
            events=events,
            pixel_id=pixel_id,
        )
        event_response = event_request.execute()
        # logger.info(event_response)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        # logger.error("calling_facebook_api: %s at %s", str(e), str(exc_tb.tb_lineno))


def get_address_list(dealshub_user_obj, type_addr=""):
    '''
    Returns the shipping/billing address list based upon `type_addr` in ["shipping", "billing"]
    '''
    address_list = []
    address_objs = None

    if type_addr not in ["shipping", "billing"]:
        return address_list
    
    if type_addr == "shipping":
        address_objs = Address.objects.filter(user=dealshub_user_obj, is_shipping=True)
    else:
        address_objs = Address.objects.filter(user=dealshub_user_obj, is_billing=True)
    if address_objs.exists():
        for address_obj in address_objs:
            address_list.append(get_address_dict(address_obj))
    return address_list

def get_address_dict(address_obj):
    '''
    Returns the address information in a dict format
    '''

    if address_obj == None:
        return {}
    else:
        if address_obj.location_group.name == "Geepas-Uganda":
            return {
            "firstName": address_obj.first_name,
            "lastName": address_obj.last_name,
            "line1": json.loads(address_obj.address_lines)[0],
            "line2": json.loads(address_obj.address_lines)[1],
            "line3": json.loads(address_obj.address_lines)[2],
            "line4": address_obj.city,
            "city": address_obj.city,
            "region":address_obj.region,
            "geoCoordinates":address_obj.geo_coordinates, 
            "emirates": address_obj.region,
            "state": address_obj.state,
            "country": address_obj.get_country(),
            "postcode": address_obj.postcode,
            "contactNumber": str(address_obj.contact_number),
            "tag": str(address_obj.tag),
            "uuid": str(address_obj.uuid),
            "neighbourhood": str(address_obj.neighbourhood)
            }

        return {
            "firstName": address_obj.first_name,
            "lastName": address_obj.last_name,
            "line1": json.loads(address_obj.address_lines)[0],
            "line2": json.loads(address_obj.address_lines)[1],
            "line3": json.loads(address_obj.address_lines)[2],
            "line4": json.loads(address_obj.address_lines)[3],
            "city": address_obj.city,
            "region":address_obj.region,
            "geoCoordinates":address_obj.geo_coordinates, 
            "emirates": address_obj.emirates,
            "state": address_obj.state,
            "country": address_obj.get_country(),
            "postcode": address_obj.postcode,
            "contactNumber": str(address_obj.contact_number),
            "tag": str(address_obj.tag),
            "uuid": str(address_obj.uuid),
            "neighbourhood": str(address_obj.neighbourhood)
        }