from WAMSApp.models import *
from dealshub.models import *
import datetime
from django.utils import timezone

def convert_to_datetime(date_str):
    date_str = date_str[:-1] + "+0400"
    return date_str
    #return datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

def check_valid_promotion(promotion_obj):
    return timezone.now() >= promotion_obj.start_time and timezone.now() <= promotion_obj.end_time

def get_promotional_price(product_obj):
    dealshub_product_obj = DealsHubProduct.objects.get(product=product_obj)
    return dealshub_product_obj.promotional_price

def get_actual_price(dealshub_product_obj):
    if dealshub_product_obj.promotion==None:
        return dealshub_product_obj.now_price
    if check_valid_promotion(dealshub_product_obj.promotion):
        return dealshub_product_obj.promotional_price
    return dealshub_product_obj.now_price

##################################################### 

# DealsHub project

#####################################################

from dealshub.serializers import UserSerializer
import hashlib
import sys
import logging
import os
import json
import requests
from dealshub.models import *
from dealshub.constants import *
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.template import loader
import threading
from WAMSApp.utils import fetch_refresh_stock
from WAMSApp.models import *

logger = logging.getLogger(__name__)

def my_jwt_response_handler(token, user=None, request=None):
    return {
        'token': token,
        'user': UserSerializer(user, context={'request': request}).data
    }


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
  
    unit_cart_objs = UnitCart.objects.filter(cart=cart_obj, cart_type="active")
    total_amount = 0
    for t_unit_cart_obj in unit_cart_objs:
        total_amount += float(t_unit_cart_obj.price)*float(t_unit_cart_obj.quantity)

    delivery_fee = 0
    if total_amount<100 and total_amount>0:
        delivery_fee = 15

    total_amount += delivery_fee
    total_amount = round(total_amount, 2)
    

    order_obj = cart_obj.order
    if order_obj == None:
        order_obj = Order.objects.create(owner=cart_obj.owner)
        cart_obj.order = order_obj
        cart_obj.save()
    order_obj.to_pay = total_amount
    order_obj.save()


def send_order_confirmation_mail(order_obj):
    try:
        logger.info("send_order_confirmation_mail started!")
        if order_obj.owner.email_verified==False:
            return

        unit_order_objs = UnitOrder.objects.filter(order=order_obj)
        uuid_list = []
        for unit_order_obj in unit_order_objs:
            uuid_list.append(unit_order_obj.product_code)
        productInfo = fetch_bulk_product_info(uuid_list)

        custom_unit_order_list = []
        subtotal = 0
        for unit_order_obj in unit_order_objs:
            temp_dict = {
                "order_id": unit_order_obj.orderid,
                "product_name": productInfo[unit_order_obj.product_code]["productName"],
                "productImageUrl": productInfo[unit_order_obj.product_code]["productImageUrl"],
                "quantity": unit_order_obj.quantity,
                "price": unit_order_obj.price,
                "currency": unit_order_obj.currency
            }
            subtotal += float(unit_order_obj.price)*float(unit_order_obj.quantity)
            custom_unit_order_list.append(temp_dict)

        delivery_fee = 0
        if subtotal<100:
            delivery_fee = 15
        cod_fee = 0
        if order_obj.payment_mode=="COD":
            cod_fee = 5

        subtotal = round(subtotal, 2)
        grand_total = round(subtotal + delivery_fee + cod_fee, 2)
        

        order_placed_date = str(timezone.localtime(order_obj.order_placed_date).strftime("%A, %B %d, %Y | %I:%M %p"))

        customer_name = str(order_obj.owner.first_name)

        address_lines = json.loads(order_obj.shipping_address.address_lines)
        full_name = order_obj.owner.first_name + " " + order_obj.owner.last_name

        html_message = loader.render_to_string(
            os.getcwd()+'/dealshub/templates/order-confirmation.html',
            {
                "customer_name": customer_name,
                "custom_unit_order_list":  custom_unit_order_list,
                "subtotal": str(subtotal) + " AED",
                "delivery_fee": str(delivery_fee) + " AED",
                "cod_fee": str(cod_fee) + " AED",
                "grand_total": str(grand_total) + " AED",
                "order_placed_date": order_placed_date,
                "full_name": full_name,
                "address_lines": address_lines,
                "website_order_link": WEBSITE_LINK+"/orders/"+order_obj.uuid
            }
        )

        # send_mail(
        #     'Order Confirmation',
        #     'Order Confirmation',
        #     'nisarg@omnycomm.com',
        #     [order_obj.owner.email],
        #     fail_silently=False,
        #     html_message=html_message
        # )

        email = EmailMultiAlternatives(
                    subject='Order Confirmation', 
                    body='Order Confirmation', 
                    from_email='orders@wigme.com',
                    to=[order_obj.owner.email],
                    cc=['orders@wigme.com'],
                    bcc=['hari.pk@westernint.com', 'siddhansh@omnycomm.com']
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

        uuid_list = [unit_order_obj.product_code]
        productInfo = fetch_bulk_product_info(uuid_list)


        order_dispatched_date = UnitOrderStatus.objects.filter(unit_order=unit_order_obj, status="shipped")[0].date_created

        order_dispatched_date = str(timezone.localtime(order_dispatched_date).strftime("%A, %B %d, %Y | %I:%M %p"))

        customer_name = str(unit_order_obj.order.owner.first_name)

        address_lines = json.loads(unit_order_obj.order.shipping_address.address_lines)
        full_name = unit_order_obj.order.owner.first_name + " " + unit_order_obj.order.owner.last_name

        html_message = loader.render_to_string(
            os.getcwd()+'/dealshub/templates/order-dispatch.html',
            {
                "customer_name": customer_name,
                "order_id": unit_order_obj.orderid,
                "product_name": productInfo[unit_order_obj.product_code]["productName"],
                "productImageUrl": productInfo[unit_order_obj.product_code]["productImageUrl"],
                "quantity": unit_order_obj.quantity,
                "price": unit_order_obj.price,
                "currency": unit_order_obj.currency,
                "order_dispatched_date": order_dispatched_date,
                "full_name": full_name,
                "address_lines": address_lines,
                "website_order_link": WEBSITE_LINK+"/orders/"+unit_order_obj.order.uuid
            }
        )

        # send_mail(
        #     'Order Dispatch',
        #     'Order Dispatch',
        #     'nisarg@omnycomm.com',
        #     [unit_order_obj.order.owner.email],
        #     fail_silently=False,
        #     html_message=html_message
        # )

        email = EmailMultiAlternatives(
                    subject='Order Dispatch', 
                    body='Order Dispatch', 
                    from_email='orders@wigme.com',
                    to=[unit_order_obj.order.owner.email],
                    cc=['orders@wigme.com'],
                    bcc=['hari.pk@westernint.com', 'siddhansh@omnycomm.com']
                )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("send_order_dispatch_mail: %s at %s", e, str(exc_tb.tb_lineno))


def send_order_delivered_mail(unit_order_obj):
    try:

        if unit_order_obj.order.owner.email_verified==False:
            return

        uuid_list = [unit_order_obj.product_code]
        productInfo = fetch_bulk_product_info(uuid_list)


        order_delivered_date = UnitOrderStatus.objects.filter(unit_order=unit_order_obj, status="delivered")[0].date_created

        order_delivered_date = str(timezone.localtime(order_delivered_date).strftime("%A, %B %d, %Y | %I:%M %p"))

        customer_name = str(unit_order_obj.order.owner.first_name)

        address_lines = json.loads(unit_order_obj.order.shipping_address.address_lines)
        full_name = unit_order_obj.order.owner.first_name + " " + unit_order_obj.order.owner.last_name

        html_message = loader.render_to_string(
            os.getcwd()+'/dealshub/templates/order-delivered.html',
            {
                "customer_name": customer_name,
                "order_id": unit_order_obj.orderid,
                "product_name": productInfo[unit_order_obj.product_code]["productName"],
                "productImageUrl": productInfo[unit_order_obj.product_code]["productImageUrl"],
                "quantity": unit_order_obj.quantity,
                "price": unit_order_obj.price,
                "currency": unit_order_obj.currency,
                "order_delivered_date": order_delivered_date,
                "full_name": full_name,
                "address_lines": address_lines,
                "website_order_link": WEBSITE_LINK+"/orders/"+unit_order_obj.order.uuid
            }
        )

        # send_mail(
        #     'Order Delivered',
        #     'Order Delivered',
        #     'nisarg@omnycomm.com',
        #     [unit_order_obj.order.owner.email],
        #     fail_silently=False,
        #     html_message=html_message
        # )

        email = EmailMultiAlternatives(
                    subject='Order Delivered', 
                    body='Order Delivered', 
                    from_email='orders@wigme.com',
                    to=[unit_order_obj.order.owner.email],
                    cc=['orders@wigme.com'],
                    bcc=['hari.pk@westernint.com', 'siddhansh@omnycomm.com']
                )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("send_order_delivered_mail: %s at %s", e, str(exc_tb.tb_lineno))



def send_order_delivery_failed_mail(unit_order_obj):
    try:

        if unit_order_obj.order.owner.email_verified==False:
            return

        uuid_list = [unit_order_obj.product_code]
        productInfo = fetch_bulk_product_info(uuid_list)


        order_delivery_failed = UnitOrderStatus.objects.filter(unit_order=unit_order_obj, status_admin="delivery failed")[0].date_created

        order_delivery_failed = str(timezone.localtime(order_delivery_failed).strftime("%A, %B %d, %Y | %I:%M %p"))

        customer_name = str(unit_order_obj.order.owner.first_name)

        address_lines = json.loads(unit_order_obj.order.shipping_address.address_lines)
        full_name = unit_order_obj.order.owner.first_name + " " + unit_order_obj.order.owner.last_name

        html_message = loader.render_to_string(
            os.getcwd()+'/dealshub/templates/order-delivery-failed.html',
            {
                "customer_name": customer_name,
                "order_id": unit_order_obj.orderid,
                "product_name": productInfo[unit_order_obj.product_code]["productName"],
                "productImageUrl": productInfo[unit_order_obj.product_code]["productImageUrl"],
                "quantity": unit_order_obj.quantity,
                "price": unit_order_obj.price,
                "currency": unit_order_obj.currency,
                "order_delivery_failed": order_delivery_failed,
                "full_name": full_name,
                "address_lines": address_lines,
                "website_order_link": WEBSITE_LINK+"/orders/"+unit_order_obj.order.uuid
            }
        )

        # send_mail(
        #     'Order Delivery Failed',
        #     'Order Delivered Failed',
        #     'nisarg@omnycomm.com',
        #     [unit_order_obj.order.owner.email],
        #     fail_silently=False,
        #     html_message=html_message
        # )

        email = EmailMultiAlternatives(
                    subject='Order Delivery Failed', 
                    body='Order Delivery Failed', 
                    from_email='orders@wigme.com',
                    to=[unit_order_obj.order.owner.email],
                    cc=['orders@wigme.com'],
                    bcc=['hari.pk@westernint.com', 'siddhansh@omnycomm.com']
                )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("send_order_delivery_failed_mail: %s at %s", e, str(exc_tb.tb_lineno))



def send_order_cancelled_mail(unit_order_obj):
    try:

        if unit_order_obj.order.owner.email_verified==False:
            return

        uuid_list = [unit_order_obj.product_code]
        productInfo = fetch_bulk_product_info(uuid_list)

        order_cancelled_date = UnitOrderStatus.objects.filter(unit_order=unit_order_obj, status="cancelled")[0].date_created

        order_cancelled_date = str(timezone.localtime(order_cancelled_date).strftime("%A, %B %d, %Y | %I:%M %p"))

        customer_name = str(unit_order_obj.order.owner.first_name)

        address_lines = json.loads(unit_order_obj.order.shipping_address.address_lines)
        full_name = unit_order_obj.order.owner.first_name + " " + unit_order_obj.order.owner.last_name

        html_message = loader.render_to_string(
            os.getcwd()+'/dealshub/templates/order-cancelled.html',
            {
                "customer_name": customer_name,
                "order_id": unit_order_obj.orderid,
                "product_name": productInfo[unit_order_obj.product_code]["productName"],
                "productImageUrl": productInfo[unit_order_obj.product_code]["productImageUrl"],
                "quantity": unit_order_obj.quantity,
                "price": unit_order_obj.price,
                "currency": unit_order_obj.currency,
                "order_cancelled_date": order_cancelled_date,
                "full_name": full_name,
                "address_lines": address_lines,
                "website_order_link": WEBSITE_LINK+"/orders/"+unit_order_obj.order.uuid
            }
        )

        # send_mail(
        #     'Order Cancelled',
        #     'Order Cancelled',
        #     'nisarg@omnycomm.com',
        #     [unit_order_obj.order.owner.email],
        #     fail_silently=False,
        #     html_message=html_message
        # )

        email = EmailMultiAlternatives(
                    subject='Order Cancelled', 
                    body='Order Cancelled', 
                    from_email='orders@wigme.com',
                    to=[unit_order_obj.order.owner.email],
                    cc=['orders@wigme.com'],
                    bcc=['hari.pk@westernint.com', 'siddhansh@omnycomm.com']
                )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("send_order_cancelled_mail: %s at %s", e, str(exc_tb.tb_lineno))



def contact_us_send_email(your_email, message):
    try:

        body = """
        Customer Email: """+your_email+"""
        Message: """+message+"""
        """
        send_mail(
            subject='Contact Enquiry',
            message=body,
            from_email='support@wigme.com',
            auth_user='support@wigme.com',
            auth_password='western@123',
            recipient_list=["support@wigme.com"],
            fail_silently=False
        )

        # email = EmailMultiAlternatives(
        #             auth_user='support@wigme.com',
        #             auth_password='western@123',
        #             subject='Contact Enquiry', 
        #             body=body, 
        #             from_email='support@wigme.com',
        #             to=['support@wigme.com']
        #         )
        # email.send(fail_silently=False)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("contact_us_send_email: %s at %s", e, str(exc_tb.tb_lineno))


def fetch_total_bill_from_cart(cart_obj, online_payment):
    
    unit_cart_objs = UnitCart.objects.filter(cart=cart_obj, cart_type="active")
    
    subtotal_amount = 0
    for unit_cart_obj in unit_cart_objs:
        subtotal_amount += float(unit_cart_obj.price)*float(unit_cart_obj.quantity)

    delivery_fee = 0
    if subtotal_amount<100 and subtotal_amount>0:
        delivery_fee = 15

    total_amount = 1.05*(subtotal_amount+delivery_fee)
    if online_payment==False and total_amount>0:
        total_amount += 1.05*5
    
    return round(total_amount, 2)


def fetch_total_bill_from_order(order_obj):
    
    unit_order_objs = UnitOrder.objects.filter(order=order_obj)
    
    subtotal_amount = 0
    for unit_order_obj in unit_order_objs:
        subtotal_amount += float(unit_order_obj.price)*float(unit_order_obj.quantity)

    delivery_fee = 0
    if subtotal_amount<100:
        delivery_fee = 15

    total_amount = 1.05*(subtotal_amount+delivery_fee)
    if order_obj.payment_mode=="COD":
        total_amount += 1.05*5
    
    return round(total_amount, 2)


def refresh_stock(order_obj):

    try:
        unit_order_objs = UnitOrder.objects.filter(order=order_obj)
        uuid_list = []
        for unit_order_obj in unit_order_objs:
            uuid_list.append(unit_order_obj.product_code)
 
        for uuid in uuid_list:
            dealshub_product_obj = DealsHubProduct.objects.get(product__uuid=uuid)
            brand = str(dealshub_product_obj.product.base_product.brand).lower()
            seller_sku = str(dealshub_product_obj.product.base_product.seller_sku)
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

        uuid_list = []
        for unit_order_obj in unit_order_objs:
            uuid_list.append(unit_order_obj.product_code)

        productInfo = fetch_bulk_product_info(uuid_list)

        total_amount = 0
        for unit_order_obj in unit_order_objs:
            temp_dict = {
                "name": productInfo[unit_order_obj.product_code]["productName"],
                "id": unit_order_obj.product_code,
                "price": str(unit_order_obj.price),
                "brand": productInfo[unit_order_obj.product_code]["brandName"],
                "category": productInfo[unit_order_obj.product_code]["category"],
                "variant": "",
                "quantity": unit_order_obj.quantity,
                "coupon": ""
            }
            product_list.append(temp_dict)
            total_amount += float(unit_order_obj.price)*float(unit_order_obj.quantity)

        total_amount = round(total_amount, 2)
        delivery_fee = 0
        if total_amount<100 and total_amount>0:
            delivery_fee = 15

        to_pay = order_obj.to_pay
        vat = round((to_pay - to_pay/1.05), 2)

        purchase_info = {
            "actionField": {
                "id": order_obj.bundleid,
                "affiliation": "Online Store",
                "revenue": str(to_pay),
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


#######################################################################

# APIs to Functions

#######################################################################

def fetch_bulk_product_info(uuidList):

    productInfo = {}
    for uuid in uuidList:
        product_obj = Product.objects.get(uuid=uuid)

        main_image_url = Config.objects.all()[0].product_404_image.image.url
        try:
            main_images_obj = MainImages.objects.get(product=product_obj, is_sourced=True)
            main_images_list = main_images_obj.main_images.all()
            main_image_url = main_images_list.all()[0].image.mid_image.url
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("fetch_bulk_product_info: %s at %s", e, str(exc_tb.tb_lineno))

        temp_dict = {
            "productName": product_obj.product_name,
            "productImageUrl": main_image_url,
            "sellerSku": product_obj.base_product.seller_sku,
            "productId": product_obj.product_id,
            "brandName": str(product_obj.base_product.brand),
            "category": str(product_obj.base_product.category),
        }

        productInfo[uuid] = temp_dict
    
    return productInfo

def fetch_company_credentials(website_group_name):

    website_group_obj = WebsiteGroup.objects.get(name=website_group_name)

    credentials = json.loads(website_group_obj.payment_credentials)

    return credentials