from dealshub.models import *
from dealshub.core_utils import *
from WAMSApp.utils_SAP_Integration import *

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
from WAMSApp.utils_SAP_Integration import *

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
            if website_group=="parajohn":
                message = "Your order has been dispatched!"
                p2 = threading.Thread(target=send_parajohn_order_status_sms, args=(unit_order_obj,message,))
                p2.start()
            if website_group=="shopnesto":
                message = "Your order has been dispatched!"
                p2 = threading.Thread(target=send_wigme_order_status_sms, args=(unit_order_obj,message,))
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
                if website_group=="parajohn":
                    message = "Your order has been delivered!"
                    p2 = threading.Thread(target=send_parajohn_order_status_sms, args=(unit_order_obj,message,))
                    p2.start()
                if website_group=="shopnesto":
                    message = "Your order has been delivered!"
                    p2 = threading.Thread(target=send_wigme_order_status_sms , args=(unit_order_obj,message,))
                    p2.start()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("set_order_status: %s at %s", e, str(exc_tb.tb_lineno))
        
        elif order_status=="delivery failed":
            try:
                p1 = threading.Thread(target=send_order_delivery_failed_mail, args=(unit_order_obj,))
                p1.start()
                website_group = unit_order_obj.order.location_group.website_group.name
                if website_group=="parajohn":
                    message = "Sorry, we were unable to deliver your order!"
                    p2 = threading.Thread(target=send_parajohn_order_status_sms, args=(unit_order_obj,message,))
                    p2.start()
                if website_group=="shopnesto":
                    message = "Sorry, we were unable to deliver your order!"
                    p2 = threading.Thread(target=send_wigme_order_status_sms , args=(unit_order_obj,message,))
                    p2.start()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("set_order_status: %s at %s", e, str(exc_tb.tb_lineno))
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


def update_cart_bill(cart_obj):
    
    cart_obj.to_pay = cart_obj.get_total_amount()

    if cart_obj.voucher!=None:
        voucher_obj = cart_obj.voucher
        if voucher_obj.is_deleted==True or voucher_obj.is_published==False or voucher_obj.is_expired()==True or voucher_obj.is_eligible(cart_obj.get_subtotal())==False or is_voucher_limt_exceeded_for_customer(cart_obj.owner, voucher_obj):
            cart_obj.voucher = None
    cart_obj.save()


def update_fast_cart_bill(fast_cart_obj):
    
    fast_cart_obj.to_pay = fast_cart_obj.get_total_amount()

    if fast_cart_obj.voucher!=None:
        voucher_obj = fast_cart_obj.voucher
        if voucher_obj.is_deleted==True or voucher_obj.is_published==False or voucher_obj.is_expired()==True or voucher_obj.is_eligible(fast_cart_obj.get_subtotal())==False or is_voucher_limt_exceeded_for_customer(fast_cart_obj.owner, voucher_obj):
            fast_cart_obj.voucher = None
    fast_cart_obj.save()


def update_order_bill(order_obj):
    
    order_obj.to_pay = order_obj.get_total_amount()
    order_obj.save()


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
        r = requests.post(url=url, data=req_data)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("send_wigme_order_status_sms: %s at %s", e, str(exc_tb.tb_lineno))


def send_parajohn_order_status_sms(unit_order_obj,message):
    try:
        dealshub_user_obj = unit_order_obj.order.owner
        if dealshub_user_obj.contact_verified==False:
            return
        logger.info("send_parajohn_order_status_sms:", message)
        contact_number = dealshub_user_obj.contact_number
        url = "https://retail.antwerp.alarislabs.com/rest/send_sms?from=PARA JOHN&to=971"+contact_number+"&message="+message+"&username=r8NyrDLI&password=GLeOC6HO"
        requests.get(url)  
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("send_parajohn_order_status_sms: %s at %s", e, str(exc_tb.tb_lineno))


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
                "email_content": email_content
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
            logger.info("send_order_confirmation_mail")

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

        html_message = loader.render_to_string(
            os.getcwd()+'/dealshub/templates/order-dispatch.html',
            {
                "website_logo": website_logo,
                "customer_name": customer_name,
                "order_id": unit_order_obj.orderid,
                "product_name": unit_order_obj.product.get_name(),
                "productImageUrl": unit_order_obj.product.get_display_image_url(),
                "quantity": unit_order_obj.quantity,
                "order_dispatched_date": order_dispatched_date,
                "full_name": full_name,
                "address_lines": address_lines,
                "website_order_link": unit_order_obj.order.get_website_link()+"/orders/"+unit_order_obj.order.uuid
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

        html_message = loader.render_to_string(
            os.getcwd()+'/dealshub/templates/order-delivered.html',
            {
                "website_logo": website_logo,
                "customer_name": customer_name,
                "order_id": unit_order_obj.orderid,
                "product_name": unit_order_obj.product.get_name(),
                "productImageUrl": unit_order_obj.product.get_display_image_url(),
                "quantity": unit_order_obj.quantity,
                "order_delivered_date": order_delivered_date,
                "full_name": full_name,
                "address_lines": address_lines,
                "website_order_link": unit_order_obj.order.get_website_link()+"/orders/"+unit_order_obj.order.uuid
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

        html_message = loader.render_to_string(
            os.getcwd()+'/dealshub/templates/order-delivery-failed.html',
            {
                "website_logo": website_logo,
                "customer_name": customer_name,
                "order_id": unit_order_obj.orderid,
                "product_name": unit_order_obj.product.get_name(),
                "productImageUrl": unit_order_obj.product.get_display_image_url(),
                "quantity": unit_order_obj.quantity,
                "order_delivery_failed": order_delivery_failed,
                "full_name": full_name,
                "address_lines": address_lines,
                "website_order_link": unit_order_obj.order.get_website_link()+"/orders/"+unit_order_obj.order.uuid
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

        html_message = loader.render_to_string(
            os.getcwd()+'/dealshub/templates/order-cancelled.html',
            {
                "website_logo": website_logo,
                "customer_name": customer_name,
                "order_id": unit_order_obj.orderid,
                "product_name": unit_order_obj.product.get_name(),
                "productImageUrl": unit_order_obj.product.get_display_image_url(),
                "quantity": unit_order_obj.quantity,
                "order_cancelled_date": order_cancelled_date,
                "full_name": full_name,
                "address_lines": address_lines,
                "website_order_link": unit_order_obj.order.get_website_link()+"/orders/"+unit_order_obj.order.uuid
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
        custom_permission_objs = CustomPermission.objects.filter(location_groups__in=[dealshub_product_obj.location_group])
        for custom_permission_obj in custom_permission_objs:
            try:
                body = "This is to inform you that "+dealshub_product_obj.get_seller_sku()+" product is out of stock. Kindly check with SAP and take appropriate action."

                with get_connection(
                    host="smtp.gmail.com",
                    port=587, 
                    username="nisarg@omnycomm.com", 
                    password="verjtzgeqareribg",
                    use_tls=True) as connection:
                    email = EmailMessage(subject='Out of Stock: '+dealshub_product_obj.get_seller_sku(),
                                         body=body,
                                         from_email='nisarg@omnycomm.com',
                                         to=[custom_permission_obj.user.email],
                                         connection=connection)
                    email.send(fail_silently=True)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("notify_low_stock: %s at %s", e, str(exc_tb.tb_lineno))        
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("notify_low_stock: %s at %s", e, str(exc_tb.tb_lineno))


def notify_grn_error(order_obj):
    try:
        custom_permission_objs = CustomPermission.objects.filter(location_groups__in=[order_obj.location_group])
        email_list = []
        for custom_permission_obj in custom_permission_objs:
            if custom_permission_obj.user.email!="":
                email_list.append(custom_permission_obj.user.email)
        try:
            body = "This is to inform you that order number "+order_obj.bundleid+" has GRN error. Kindly check on Omnycomm and take appropriate action."
            with get_connection(
                host="smtp.gmail.com",
                port=587, 
                username="nisarg@omnycomm.com", 
                password="verjtzgeqareribg",
                use_tls=True) as connection:
                email = EmailMessage(subject='GRN Error: '+order_obj.bundleid,
                                     body=body,
                                     from_email='nisarg@omnycomm.com',
                                     to=email_list,
                                     connection=connection)
                email.send(fail_silently=True)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("notify_grn_error: %s at %s", e, str(exc_tb.tb_lineno))        
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("notify_grn_error: %s at %s", e, str(exc_tb.tb_lineno))        


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
                company_code = BRAND_COMPANY_DICT[brand_name]
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
            if dealshub_product_obj.location_group==wigme_location_group_obj:
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
                "coupon": "",
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
        if dealshub_product_obj.get_actual_price()==0:
            continue
        try:
            temp_dict = {}
            temp_dict["name"] = dealshub_product_obj.get_name(language_code)
            temp_dict["brand"] = dealshub_product_obj.get_brand(language_code)
            temp_dict["now_price"] = dealshub_product_obj.now_price
            temp_dict["was_price"] = dealshub_product_obj.was_price
            temp_dict["promotional_price"] = dealshub_product_obj.promotional_price
            temp_dict["stock"] = dealshub_product_obj.stock
            temp_dict["isStockAvailable"] = dealshub_product_obj.stock>0
            temp_dict["is_promotional"] = dealshub_product_obj.promotion!=None
            if dealshub_product_obj.promotion!=None:
                temp_dict["promotion_tag"] = dealshub_product_obj.promotion.promotion_tag
            else:
                temp_dict["promotion_tag"] = None
            temp_dict["currency"] = dealshub_product_obj.get_currency()
            temp_dict["uuid"] = dealshub_product_obj.uuid
            temp_dict["id"] = dealshub_product_obj.uuid
            temp_dict["heroImageUrl"] = dealshub_product_obj.get_display_image_url()
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


def fetch_order_information_for_sap_punching(seller_sku, company_code, x_value):

    try:

        result = fetch_prices_and_stock(seller_sku, company_code)

        stock_list = result["stock_list"]
        prices = result["prices"]
        total_atp = result["total_atp"]
        total_holding = result["total_holding"]
        atp_threshold = result["atp_threshold"]
        holding_threshold = result["holding_threshold"]

        order_information = {}
        
        if total_atp > atp_threshold:
            from_holding=""
            max_atp_qty = 0
            max_batch = ""
            max_uom = ""
            for item in stock_list:
                atp_qty = item["atp_qty"]
                batch = item["batch"]
                uom = item["uom"]
                if atp_qty>=max_atp_qty:
                    max_atp_qty = atp_qty
                    max_batch = batch
                    max_uom = uom
        else:
            from_holding = x_value
            max_holding_qty = 0
            max_batch = ""
            max_uom = ""
            if from_holding == "X":
                for item in stock_list:
                    holding_qty = item["holding_qty"]
                    batch = item["batch"]
                    uom = item["uom"]
                    if holding_qty>=max_holding_qty:
                        max_holding_qty = holding_qty
                        max_batch = batch
                        max_uom = uom
            else:
                for item in stock_list:
                    atp_qty = item["atp_qty"]
                    batch = item["batch"]
                    uom = item["uom"]
                    if atp_qty>=max_holding_qty:
                        max_holding_qty = atp_qty
                        max_batch = batch
                        max_uom = uom

        order_information["from_holding"] = from_holding
        order_information["uom"] = max_uom
        order_information["batch"] = max_batch

        return order_information
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("fetch_order_information_for_sap_punching: %s at %s", e, str(exc_tb.tb_lineno))
        return {}


def create_section_banner_product_report(dealshub_product_objs, filename):

    workbook = xlsxwriter.Workbook('./'+filename)
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