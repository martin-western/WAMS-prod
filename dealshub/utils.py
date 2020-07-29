from WAMSApp.models import *
from dealshub.models import *
from dealshub.core_utils import *

import datetime
from django.utils import timezone

import hashlib
import random
import sys
import logging
import os
import json
import requests
from dealshub.constants import *
from django.core.mail import send_mail, get_connection
from django.core.mail import EmailMultiAlternatives
from django.template import loader
import threading
from WAMSApp.utils import fetch_refresh_stock

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
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("set_order_status: %s at %s", e, str(exc_tb.tb_lineno))
        elif order_status=="delivery failed":
            try:
                p1 = threading.Thread(target=send_order_delivery_failed_mail, args=(unit_order_obj,))
                p1.start()
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
                "product_name": productInfo[unit_order_obj.product_code]["productName"],
                "productImageUrl": productInfo[unit_order_obj.product_code]["productImageUrl"],
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


def refresh_stock(order_obj):

    try:
        unit_order_objs = UnitOrder.objects.filter(order=order_obj)
        uuid_list = []
        for unit_order_obj in unit_order_objs:
            dealshub_product_obj = unit_order_obj.product
            brand = dealshub_product_obj.get_brand().lower()
            seller_sku = dealshub_product_obj.get_seller_sku()
            stock = 0
            if "wigme" in seller_sku.lower():
                continue
            if brand=="geepas":
                stock1 = fetch_refresh_stock(seller_sku, "1070", "TG01")
                stock2 = fetch_refresh_stock(seller_sku, "1000", "AFS1")
                stock = max(stock1, stock2)
            elif brand=="baby plus":
                stock = fetch_refresh_stock(seller_sku, "5550", "TG01")
            elif brand=="royalford":
                stock = fetch_refresh_stock(seller_sku, "3000", "AFS1")
            elif brand=="krypton":
                stock = fetch_refresh_stock(seller_sku, "2100", "TG01")
            elif brand=="olsenmark":
                stock = fetch_refresh_stock(seller_sku, "1100", "AFS1")
            elif brand=="ken jardene":
                stock = fetch_refresh_stock(seller_sku, "5550", "AFS1") # 
            elif brand=="younglife":
                stock = fetch_refresh_stock(seller_sku, "5000", "AFS1")
            elif brand=="delcasa":
                stock = fetch_refresh_stock(seller_sku, "3000", "TG01")

            if stock > 10:
                dealshub_product_obj.stock = 5
            else:
                dealshub_product_obj.stock = 0

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
                "coupon": ""
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



def get_recommended_products(dealshub_product_objs):

    dealshub_product_objs = get_random_products(dealshub_product_objs)

    product_list = []
    for dealshub_product_obj in dealshub_product_objs:
        if dealshub_product_obj.get_actual_price()==0:
            continue
        temp_dict = {}
        temp_dict["name"] = dealshub_product_obj.get_name()
        temp_dict["brand"] = dealshub_product_obj.get_brand()
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
    return product_list