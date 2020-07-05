from dealshub.models import *
import json
import urllib.request, urllib.error, urllib.parse
import datetime
import os


f = open("scripts/qadealshub.json", "r")
all_data_json = json.loads(f.read())
f.close()
cnt = 0

dealshub_user_pk_mapping = {}
all_data = all_data_json["dealshubplayApp.dealshubuser"]
for data in all_data:
    try:
        cnt+=1
        auth_users = all_data_json["auth.user"]
        for auth_user in auth_users:
            if auth_user["fields"]["username"] == data["fields"]["contact_number"] + "-" + data["fields"]["website_group"]:
                usr = auth_user["fields"]

        dealshub_user_obj, created = DealsHubUser.objects.get_or_create(
                                            username = usr["username"],
                                            password = usr["password"],
                                            last_login = usr["last_login"],
                                            is_superuser = usr["is_superuser"],
                                            first_name = usr["first_name"],
                                            last_name = usr["last_name"],
                                            email = usr["email"],
                                            is_staff = usr["is_staff"],
                                            is_active = usr["is_active"],
                                            date_joined = usr["date_joined"],
                                            contact_number=data["fields"]["contact_number"],
                                            date_created=data["fields"]["date_created"],
                                            email_verified=data["fields"]["email_verified"],
                                            contact_verified=data["fields"]["contact_verified"],
                                            verification_code=data["fields"]["verification_code"],
                                            website_group=data["fields"]["website_group"],
                                            )
        dealshub_user_pk_mapping[data["pk"]] = dealshub_user_obj.pk

        print(("DealsHubUser Cnt:", cnt))

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error DealsHubUser %s at %s", str(e), str(exc_tb.tb_lineno)))




address_pk_mapping = {}
cnt=0
for data in all_data_json[ "dealshubplayApp.address"]:
    try:

        cnt+=1
        user_obj = DealsHubUser.objects.get(username=data["fields"]["user"][0])
        address_obj, created = Address.objects.get_or_create(
                                            title=data["fields"]["title"],
                                            first_name=data["fields"]["first_name"],
                                            last_name=data["fields"]["last_name"],
                                            address_lines=json.dumps(data["fields"]["address_lines"]),
                                            state=data["fields"]["state"],
                                            postcode=data["fields"]["postcode"],
                                            user=user_obj,
                                            contact_number=data["fields"]["contact_number"],
                                            date_created=data["fields"]["date_created"],
                                            is_shipping=data["fields"]["is_shipping"],
                                            is_billing=data["fields"]["is_billing"],
                                            is_deleted=data["fields"]["is_deleted"],
                                            tag=data["fields"]["tag"],
                                            )
        address_pk_mapping[data["pk"]] = address_obj.pk

        print(("Address Cnt:", cnt))

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error Address %s at %s", str(e), str(exc_tb.tb_lineno)))

order_pk_mapping = {}
cnt=0
for data in all_data_json["dealshubplayApp.order"]:
    try:

        user_obj = DealsHubUser.objects.filter(username=data["fields"]["owner"][0]).first()
        if user_obj is not None:
            cnt+=1
            address_obj = Address.objects.get(pk=data["fields"]["shipping_address"])
            order_obj, created = Order.objects.get_or_create(
                                                bundleid=data["fields"]["bundleid"],
                                                owner=user_obj,
                                                date_created=data["fields"]["date_created"],
                                                shipping_address=address_obj,
                                                payment_mode=data["fields"]["payment_mode"],
                                                to_pay=data["fields"]["to_pay"],
                                                order_placed_date=data["fields"]["order_placed_date"],
                                                payment_status=data["fields"]["payment_status"],
                                                payment_info=data["fields"]["payment_info"],
                                                merchant_reference=data["fields"]["merchant_reference"],
                                                order_type=data["fields"]["order_type"],
                                                )
            order_pk_mapping[data["pk"]] = order_obj.pk
            print(("Order Cnt:", cnt))

        else:
            print("NOT EXIST " + data["fields"]["owner"][0])


    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error order %s at %s", str(e), str(exc_tb.tb_lineno)))


cart_pk_mapping = {}
cnt=0
for data in all_data_json["dealshubplayApp.cart"]:
    try:

        user_obj = DealsHubUser.objects.filter(username=data["fields"]["owner"][0]).first()
        if user_obj is not None:
            cnt+=1
            order_obj = Order.objects.get(pk=data["fields"]["order"])
            cart_obj, created = Cart.objects.get_or_create(
                                                    owner=user_obj,
                                                    order=order_obj,
                                                )
            cart_pk_mapping[data["pk"]] = cart_obj.pk

            print(("Cart Cnt:", cnt))

        else:
            print("NOT EXIST " + data["fields"]["owner"][0])

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error Cart %s at %s", str(e), str(exc_tb.tb_lineno)))


unit_cart_pk_mapping = {}
cnt=0
for data in all_data_json["dealshubplayApp.address"]:
    try:

        cnt+=1
        product_obj = DealsHubProduct.objects.get(product__uuid=data["fields"]["product_code"])
        cart_obj = Cart.objects.get(pk=data["fields"]["cart"])
        unit_cart_obj, created = UnitCart.objects.get_or_create(
                                            cart=cart_obj,
                                            product=product_obj,
                                            quantity=data["fields"]["quantity"],
                                            price=data["fields"]["price"],
                                            currency=data["fields"]["currency"],
                                            date_created=data["fields"]["date_created"],
                                            cart_type=data["fields"]["cart_type"],
                                            )
        unit_cart_pk_mapping[data["pk"]] = unit_cart_obj.pk

        print(("Unit cart Cnt:", cnt))

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error unit cart %s at %s", str(e), str(exc_tb.tb_lineno)))


unit_order_pk_mapping = {}
cnt=0
for data in all_data_json["dealshubplayApp.unitorder"]:
    try:

        cnt+=1
        product_obj = DealsHubProduct.objects.get(product__uuid=data["fields"]["product_code"])
        order_obj = Order.objects.get(pk=data["fields"]["order"])
        unit_order_obj, created = UnitOrder.objects.get_or_create(
                                            orderid=data["fields"]["orderid"],
                                            current_status=data["fields"]["current_status"],
                                            current_status_admin=data["fields"]["current_status_admin"],
                                            cancelling_note=data["fields"]["cancelling_note"],
                                            shipping_method=data["fields"]["shipping_method"],
                                            order=order_obj,
                                            product=product_obj,
                                            quantity=data["fields"]["quantity"],
                                            price=data["fields"]["price"],
                                            currency=data["fields"]["currency"],
                                            )
        unit_order_pk_mapping[data["pk"]] = unit_order_obj.pk

        print(("UnitOrder Cnt:", cnt))

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error UnitOrder %s at %s", str(e), str(exc_tb.tb_lineno)))


unit_order_status_pk_mapping = {}
cnt=0
for data in all_data_json["dealshubplayApp.unitorderstatus"]:
    try:

        cnt+=1
        unit_order_obj = Order.objects.get(pk=data["fields"]["unit_order"])
        unit_order_status_obj, created = UnitOrderStatus.objects.get_or_create(
                                            unit_order=unit_cart_obj,
                                            status=data["fields"]["status"],
                                            status_admin=data["fields"]["status_admin"],
                                            date_created=data["fields"]["date_created"],
                                            )

        unit_order_status_pk_mapping[data["pk"]] = unit_order_status_obj.pk

        print(("UnitOrderStatus Cnt:", cnt))

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error UnitOrderStatus %s at %s", str(e), str(exc_tb.tb_lineno)))


admin_review_comment_pk_mapping = {}
cnt=0
for data in all_data_json["dealshubplayApp.adminreviewcomment"]:
    try:
        cnt+=1
        admin_review_comment_obj, created = AdminReviewComment.objects.get_or_create(
                                            username=data["fields"]["username"],
                                            display_name=data["fields"]["display_name"],
                                            last_name=data["fields"]["last_name"],
                                            created_date=data["fields"]["created_date"],
                                            modified_date=data["fields"]["modified_date"],
                                            )
        admin_review_comment_pk_mapping[data["pk"]] = admin_review_comment_obj.pk

        print(("AdminReviewComment Cnt:", cnt))

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error AdminReviewComment %s at %s", str(e), str(exc_tb.tb_lineno)))


review_content_pk_mapping = {}
cnt=0
for data in all_data_json["dealshubplayApp.reviewcontent"]:
    try:

        cnt+=1
        admin_review_comment_obj = AdminReviewComment.objects.get(pk=data["fields"]["admin_comment"])
        review_content_obj, created = ReviewContent.objects.get_or_create(
                                            subject=data["fields"]["subject"],
                                            content=data["fields"]["content"],
                                            upvoted_users=data["fields"]["upvoted_users"],
                                            admin_comment=admin_review_comment_obj,
                                            )
        review_content_pk_mapping[data["pk"]] = review_content_obj.pk

        print(("ReviewContent Cnt:", cnt))

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error ReviewContent %s at %s", str(e), str(exc_tb.tb_lineno)))


review_pk_mapping = {}
for data in all_data_json[ "dealshubplayApp.review"]:
    try:

        cnt+=1
        product_obj = DealsHubProduct.objects.get(product__uuid=data["fields"]["product_code"])
        user_obj = DealsHubUser.objects.get(pk=data["fields"]["dealshub_user"])
        review_content_obj = ReviewContent.objects.get(pk=data["fields"]["content"])

        review_obj, created = Review.objects.get_or_create(
                                            dealshub_user=user_obj,
                                            product=product_obj,
                                            rating=data["fields"]["rating"],
                                            content=review_content_obj,
                                            created_date=data["fields"]["created_date"],
                                            modified_date=data["fields"]["modified_date"],
                                            )
        review_pk_mapping[data["pk"]] = review_obj.pk

        print(("Review Cnt:", cnt))

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error Review %s at %s", str(e), str(exc_tb.tb_lineno)))
