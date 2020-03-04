from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

from WAMSApp.models import *
from WAMSApp.utils import *

from django.shortcuts import render, HttpResponse, get_object_or_404
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.core.mail import EmailMessage
from django.utils import timezone

import requests
import json
import os
import pytz
import csv
import uuid
import logging
import sys
import xlrd

from datetime import datetime
from django.utils import timezone

IP_ADDR = "http://13.235.116.162:8004"

logger = logging.getLogger(__name__)

class FetchFactoriesAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchFactoriesAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            factories = Factory.objects.all()
            factory_list = []
            for factory in factories:
                temp_dict = {}
                temp_dict["name"] = factory.name
                temp_dict["business-card"] = ""
                if factory.business_card != None and factory.business_card.image != "" and factory.business_card.image != "undefined":
                    temp_dict["business-card"] = factory.business_card.image.url
                else:
                    temp_dict["business-card"] = Config.objects.all()[0].DEFAULT_IMAGE.url
                temp_dict["address"] = factory.address
                temp_dict["pk"] = factory.pk
                temp_dict["contact-person-mobile-no"] = factory.contact_person_mobile_no
                temp_dict["contact-person-emailid"] = factory.contact_person_emailid
                temp_dict["contact-person-name"] = factory.contact_person_name
                temp_dict["loading-port"] = factory.loading_port
                temp_dict["location"] = factory.location
                temp_dict["social-media-tag"] = factory.social_media_tag
                temp_dict["social-media-tag-information"] = factory.social_media_tag_information
                phone_numbers = []
                for phone_number in factory.phone_numbers.all():
                    phone_numbers.append(phone_number.number)
                temp_dict["phone-numbers"] = phone_numbers
                temp_dict["total-products"] = sourcing_user_factory.products.all().count()
                factory_list.append(temp_dict)

            sourcing_user = SourcingUser.objects.get(
                username=request.user.username)
            if SourcingUserFactory.objects.filter(created_by=sourcing_user).count() == 0:
                response["tutorial_enable"] = True
            else:
                response["tutorial_enable"] = False

            response["factory_list"] = factory_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFactoriesAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddNewFactoryAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddNewFactoryAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            phone_numbers = json.loads(data["mobile-numbers"])

            sourcing_user = SourcingUser.objects.get(
                username=request.user.username)

            image_obj = None
            if data["business-card"] == "":
                image_obj = None
            else:
                image_obj = Image.objects.create(image=data["business-card"])

            factory = Factory.objects.create(business_card=image_obj,
                                             address=data["address"],
                                             factory_emailid=data["factory-emailid"],
                                             contact_person_name=data["contact-person"],
                                             contact_person_mobile_no=data["contact-person-mobile-no"],
                                             contact_person_emailid=data["contact-person-emailid"],
                                             loading_port=data["loading-port"],
                                             social_media_tag=data["tag"],
                                             social_media_tag_information=data["tag-info"],
                                             location=data["location"],
                                             created_date=timezone.now())

            sourcing_user_factory = SourcingUserFactory.objects.create(base_factory=factory,
                                                                       name=data["factory-name"],
                                                                       created_by=sourcing_user,
                                                                       other_info=data["other-info"])
            for phone_number in phone_numbers:
                p_obj = PhoneNumber.objects.create(number=str(phone_number))
                factory.phone_numbers.add(p_obj)
                factory.save()

            response["pk"] = factory.pk
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddNewFactoryAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchFactoryDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchFactoryDetailsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            factory = Factory.objects.get(pk=data["pk"])
            sourcing_user_factory = SourcingUserFactory.objects.get(
                base_factory=factory)
            response["factory-name"] = sourcing_user_factory.name
            if factory.business_card != None and factory.business_card.image != "" and factory.business_card.image != "undefined":
                response["business-card"] = factory.business_card.image.url
            else:
                response["business-card"] = Config.objects.all()[0].DEFAULT_IMAGE.url

            if factory.logo != "" and factory.logo != None:
                response["logo"] = factory.logo.image.url
            else:
                response["logo"] = Config.objects.all()[0].DEFAULT_IMAGE.url

            phone_numbers = factory.phone_numbers.all()
            phone_numbers_list = []
            for phone_number in phone_numbers:
                phone_numbers_list.append(phone_number.number)
            response["phone-numbers"] = phone_numbers_list

            response["address"] = factory.address

            operating_hours = factory.operating_hours.all()
            operating_hours_list = []
            for operating_hour in operating_hours:
                temp_dict = {}
                temp_dict["day"] = operating_hour.day
                temp_dict["from-time"] = operating_hour.from_time.strftime(
                    "%H:%M %p")
                temp_dict["to-time"] = operating_hour.to_time.strftime(
                    "%H:%M %p")
                operating_hours_list.append(temp_dict)

            response["factory-emailid"] = factory.factory_emailid
            response["operating-hours"] = operating_hours_list
            if factory.bank_details != None:
                response["bank-details"] = factory.bank_details.name
            else:
                response["bank-details"] = ""
            response["contact-person-mobile-no"] = factory.contact_person_mobile_no
            response["contact-person-emailid"] = factory.contact_person_emailid
            response["contact-person-name"] = factory.contact_person_name
            response["loading-port"] = factory.loading_port
            response["location"] = factory.location
            response["social-media-tag"] = factory.social_media_tag
            response["social-media-tag-information"] = factory.social_media_tag_information
            response["other-info"] = sourcing_user_factory.other_info

            images = sourcing_user_factory.images.all()

            images_list = []

            for image in images:
                temp_dict = {}
                temp_dict["url"] = image.image.url
                images_list.append(temp_dict)

            response["images"] = images_list
            response["pk"] = factory.pk

            products = sourcing_user_factory.products.all()
            products_list = []
            for product in products:
                sourcing_user_product = SourcingUserProduct.objects.get(
                    base_product=product)
                temp_dict = {}
                temp_dict["name"] = sourcing_user_product.name
                temp_dict["code"] = sourcing_user_product.code
                temp_dict["price"] = sourcing_user_product.price
                temp_dict["delivery-days"] = product.delivery_days
                temp_dict["category"] = getattr(product.category, 'name', None)
                temp_dict["country"] = getattr(product.country, 'name', None)
                temp_dict["moq"] = product.minimum_order_qty
                temp_dict["qty-metric"] = product.qty_metric
                temp_dict["order-qty"] = product.order_qty
                temp_dict["other-info"] = sourcing_user_product.other_info
                temp_dict["is_shared"] = sourcing_user_product.is_shared
                temp_dict["pk"] = product.pk
                images_list = []
                images = sourcing_user_product.images.all()

                if len(images) == 0:
                    temp_dict2 = {}
                    temp_dict2["url"] = Config.objects.all()[
                        0].DEFAULT_IMAGE.url
                    images_list.append(temp_dict2)

                for image in images:
                    temp_dict2 = {}
                    temp_dict2["url"] = image.image.url
                    images_list.append(temp_dict2)
                temp_dict["images"] = images_list
                products_list.append(temp_dict)

            sourcing_user = SourcingUser.objects.get(
                username=request.user.username)
            sourcing_user_factories = SourcingUserFactory.objects.filter(
                created_by=sourcing_user)
            tutorial_enable = True
            for sourcing_user_factory in sourcing_user_factories:
                if sourcing_user_factory.products.all().count() > 0:
                    tutorial_enable = False
                    break

            response["tutorial_enable"] = tutorial_enable
            response["products"] = products_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFactoryDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchConstantsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchConstantsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            category_list = []
            categories = Category.objects.all()
            for category in categories:
                temp_dict = {}
                temp_dict["name"] = category.name
                temp_dict["pk"] = category.pk
                category_list.append(temp_dict)

            country_list = []
            countries = Country.objects.all()
            for country in countries:
                temp_dict = {}
                temp_dict["name"] = country.name
                temp_dict["pk"] = country.pk
                country_list.append(temp_dict)

            material_specs_list = []
            material_specs = MaterialSpecs.objects.all()
            for material_spec in material_specs:
                temp_dict = {}
                temp_dict["name"] = material_spec.name
                temp_dict["pk"] = material_spec.pk
                material_specs_list.append(temp_dict)

            technical_specs_list = []
            technical_specs = TechnicalSpecs.objects.all()
            for technical_spec in technical_specs:
                temp_dict = {}
                temp_dict["name"] = technical_spec.name
                temp_dict["pk"] = technical_spec.pk
                technical_specs_list.append(temp_dict)

            response["category_list"] = category_list
            response["country_list"] = country_list
            response["material_specs_list"] = material_specs_list
            response["technical_specs_list"] = technical_specs_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchConstantsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


# UploadFactoriesProductsAPI

class UploadFactoriesProductsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UploadFactoriesProductsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            print(type(data["uploadedFile"]))

            wb = xlrd.open_workbook(file_contents=data["uploadedFile"].read())
            factory_sheet = wb.sheet_by_index(0)
            product_sheet = wb.sheet_by_index(1)

            sourcing_user = SourcingUser.objects.get(username=request.user.username)

            try:
                for row_number in range(1, factory_sheet.nrows):

                    factory_exists = SourcingUserFactory.objects.filter(
                        name=factory_sheet.cell_value(row_number, 0)).exists()
                    if factory_exists == False:
                        new_factory = Factory.objects.create(address=factory_sheet.cell_value(row_number, 1),
                                                             factory_emailid=factory_sheet.cell_value(
                                                                 row_number, 2),
                                                             contact_person_name=factory_sheet.cell_value(
                                                                 row_number, 7),
                                                             contact_person_mobile_no=str(
                                                                 factory_sheet.cell_value(row_number, 8)).split(".")[0],
                                                             contact_person_emailid=factory_sheet.cell_value(
                                                                 row_number, 9),
                                                             loading_port=factory_sheet.cell_value(
                                                                 row_number, 3),
                                                             social_media_tag=factory_sheet.cell_value(
                                                                 row_number, 10),
                                                             social_media_tag_information=factory_sheet.cell_value(
                                                                 row_number, 11),
                                                             location=factory_sheet.cell_value(
                                                                 row_number, 4),
                                                             created_date=timezone.now())

                        sourcing_user_factory = SourcingUserFactory.objects.create(base_factory=new_factory,
                                                                                   name=factory_sheet.cell_value(
                                                                                       row_number, 0),
                                                                                   created_by=sourcing_user,
                                                                                   other_info=factory_sheet.cell_value(row_number, 6))

                        phone_numbers = str(
                            factory_sheet.cell_value(1, 5)).split(",")

                        for phone_number in phone_numbers:
                            phone_number = str(phone_number).split(".")[
                                0].strip()

                            p_obj = PhoneNumber.objects.create(
                                number=str(phone_number))
                            new_factory.phone_numbers.add(p_obj)
                            new_factory.save()
            except Exception as e:
                print(e)

            products = []
            count = 0

            try:
                for row_number in range(1, product_sheet.nrows):

                    product_exists = SourcingUserProduct.objects.filter(
                        name=product_sheet.cell_value(row_number, 0)).exists()

                    if product_exists == False:
                        product = Product.objects.create(minimum_order_qty=int(product_sheet.cell_value(row_number, 4)),
                                                         order_qty=int(
                                                             product_sheet.cell_value(row_number, 6)),
                                                         qty_metric=product_sheet.cell_value(row_number, 5))

                        sourcing_user_product = SourcingUserProduct.objects.create(name=product_sheet.cell_value(row_number, 0),
                                                                                   code=product_sheet.cell_value(
                                                                                       row_number, 1),
                                                                                   price=float(
                                                                                       product_sheet.cell_value(row_number, 2)),
                                                                                   base_product=product,
                                                                                   other_info=product_sheet.cell_value(
                                                                                       row_number, 7),
                                                                                   created_by=sourcing_user,
                                                                                   currency=product_sheet.cell_value(row_number, 3))

                        count += 1
                        sourcing_user_factory = SourcingUserFactory.objects.get(
                            name=product_sheet.cell_value(row_number, 8))
                        sourcing_user_factory.products.add(product)
                        sourcing_user_factory.save()

                    print(count)
            except Exception as e:
                print(e)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadFactoriesProductsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


#########################


class UploadFactoriesProductsFromSourcingAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info(
                "UploadFactoriesProductsFromSourcingAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            wb = xlrd.open_workbook(file_contents=data["uploadedFile"].read())
            factory_sheet = wb.sheet_by_index(0)
            product_sheet = wb.sheet_by_index(1)

            sourcing_user = SourcingUser.objects.get(username=request.user.username)
            upload_format = data["upload_format"]
            try:
                for row_number in range(1, factory_sheet.nrows):

                    factory_exists = SourcingUserFactory.objects.filter(
                        name=factory_sheet.cell_value(row_number, 0)).exists()
                    if factory_exists == False:
                        new_factory = Factory.objects.create(address=factory_sheet.cell_value(row_number, 1),
                                                             factory_emailid=factory_sheet.cell_value(
                                                                 row_number, 2),
                                                             contact_person_name=factory_sheet.cell_value(
                                                                 row_number, 7),
                                                             contact_person_mobile_no=str(
                                                                 factory_sheet.cell_value(row_number, 8)).split(".")[0],
                                                             contact_person_emailid=factory_sheet.cell_value(
                                                                 row_number, 9),
                                                             loading_port=factory_sheet.cell_value(
                                                                 row_number, 3),
                                                             social_media_tag=factory_sheet.cell_value(
                                                                 row_number, 10),
                                                             social_media_tag_information=factory_sheet.cell_value(
                                                                 row_number, 11),
                                                             location=factory_sheet.cell_value(
                                                                 row_number, 4),
                                                             created_date=timezone.now())

                        sourcing_user_factory = SourcingUserFactory.objects.create(base_factory=new_factory,
                                                                                   name=factory_sheet.cell_value(
                                                                                       row_number, 0),
                                                                                   created_by=sourcing_user,
                                                                                   other_info=factory_sheet.cell_value(row_number, 6))

                        phone_numbers = str(
                            factory_sheet.cell_value(row_number, 5)).split(",")

                        for phone_number in phone_numbers:
                            phone_number = str(phone_number).split(".")[
                                0].strip()

                            p_obj = PhoneNumber.objects.create(
                                number=str(phone_number))
                            new_factory.phone_numbers.add(p_obj)
                            new_factory.save()

                        bank, bank_created = Bank.objects.get_or_create(
                            ifsc_code=factory_sheet.cell_value(row_number, 15))
                        if bank_created == False:
                            new_factory.bank_details = bank
                            new_factory.save()
                        else:
                            bank.name = factory_sheet.cell_value(row_number, 12)
                            bank.account_number = factory_sheet.cell_value(row_number, 14)
                            bank.address = factory_sheet.cell_value(row_number, 13)
                            bank.swift_code = factory_sheet.cell_value(row_number, 16)
                            bank.branch_code = factory_sheet.cell_value(
                                row_number, 17)
                            bank.save()
                            new_factory.bank_details = bank
                            new_factory.save()

                    else:
                        existing_sourcing_user_factory = SourcingUserFactory.objects.get(
                            name=factory_sheet.cell_value(row_number, 0))
                        existing_factory = existing_sourcing_user_factory.base_factory

                        existing_factory.address = get_format_value(
                            existing_factory.address, factory_sheet.cell_value(row_number, 1), upload_format)
                        existing_factory.factory_emailid = get_format_value(
                            existing_factory.factory_emailid, factory_sheet.cell_value(row_number, 2), upload_format)
                        existing_factory.contact_person_name = get_format_value(
                            existing_factory.contact_person_name, factory_sheet.cell_value(row_number, 7), upload_format)
                        existing_factory.contact_person_mobile_no = get_format_value(
                            existing_factory.contact_person_mobile_no, str(factory_sheet.cell_value(row_number, 8)), upload_format)
                        existing_factory.contact_person_emailid = get_format_value(
                            existing_factory.contact_person_emailid, factory_sheet.cell_value(row_number, 9), upload_format)
                        existing_factory.loading_port = get_format_value(
                            existing_factory.loading_port, factory_sheet.cell_value(row_number, 3), upload_format)
                        existing_factory.social_media_tag = get_format_value(
                            existing_factory.social_media_tag, factory_sheet.cell_value(row_number, 10), upload_format)
                        existing_factory.social_media_tag_information = get_format_value(
                            existing_factory.social_media_tag_information, factory_sheet.cell_value(row_number, 11), upload_format)
                        existing_factory.location = get_format_value(
                            existing_factory.location, factory_sheet.cell_value(row_number, 4), upload_format)

                        existing_factory.save()

                        existing_sourcing_user_factory.name = get_format_value(
                            existing_sourcing_user_factory.name, factory_sheet.cell_value(row_number, 0), upload_format)
                        existing_sourcing_user_factory.other_info = get_format_value(
                            existing_sourcing_user_factory.other_info, factory_sheet.cell_value(row_number, 6), upload_format)

                        existing_sourcing_user_factory.save()

                        if existing_sourcing_user_factory.base_factory.bank_details == None:
                            bank, bank_created = Bank.objects.get_or_create(
                                ifsc_code=factory_sheet.cell_value(row_number, 15))
                            bank.name = factory_sheet.cell_value(
                                    row_number, 12)
                            bank.account_number = factory_sheet.cell_value(
                                row_number, 14)
                            bank.address = factory_sheet.cell_value(
                                row_number, 13)
                            bank.swift_code = factory_sheet.cell_value(
                                row_number, 16)
                            bank.branch_code = factory_sheet.cell_value(
                                row_number, 17)
                            bank.save()
                            existing_factory.bank_details = bank
                            existing_factory.save()
                        else:
                            existing_factory.bank_details.name = get_format_value(
                                existing_factory.bank_details.name, factory_sheet.cell_value(row_number, 12), upload_format)
                            existing_factory.bank_details.address = get_format_value(
                                existing_factory.bank_details.address, factory_sheet.cell_value(row_number, 13), upload_format)
                            existing_factory.bank_details.account_number = get_format_value(
                                existing_factory.bank_details.account_number, factory_sheet.cell_value(row_number, 14), upload_format)
                            existing_factory.bank_details.ifsc_code = get_format_value(
                                existing_factory.bank_details.ifsc_code, factory_sheet.cell_value(row_number, 15), upload_format)
                            existing_factory.bank_details.swift_code = get_format_value(
                                existing_factory.bank_details.swift_code, factory_sheet.cell_value(row_number, 16), upload_format)
                            existing_factory.bank_details.branch_code = get_format_value(
                                existing_factory.bank_details.branch_code, factory_sheet.cell_value(row_number, 17), upload_format)

                            existing_factory.save()

                        try:

                            phone_numbers = str(
                                factory_sheet.cell_value(row_number, 5)).split(",")

                            new_phone_numbers = get_phone_numbers(
                                phone_numbers, existing_sourcing_user_factory.base_factory.phone_numbers.all(), upload_format)
                            if len(list(filter(lambda x: (len(x) > 0), new_phone_numbers))) == 0:

                                existing_sourcing_user_factory.base_factory.phone_numbers.clear()
                                existing_sourcing_user_factory.save()
                            else:
                                for phone_number in set(new_phone_numbers):
                                    phone_number = str(phone_number).split(".")[
                                        0].strip()

                                    p_obj, flag = PhoneNumber.objects.get_or_create(
                                        number=str(phone_number))
                                    existing_sourcing_user_factory.base_factory.phone_numbers.add(
                                        p_obj)
                                    existing_sourcing_user_factory.save()
                        except Exception as e:
                            exc_type, exc_obj, exc_tb = sys.exc_info()
                            logger.error("UploadFactoriesProductsFromSourcingAPI: %s at %s",
                             e, str(exc_tb.tb_lineno))


                        # existing_sourcing_user_factory.base_factory.phone_numbers.add(*new_phone_numbers)

                        existing_sourcing_user_factory.save()

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("UploadFactoriesProductsFromSourcingAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

            products = []
            count = 0

            try:
                for row_number in range(1, product_sheet.nrows):
                    product_exists = SourcingUserProduct.objects.filter(
                        name=product_sheet.cell_value(row_number, 0)).exists()

                    #order_qty=int( product_sheet.cell_value(row_number, 6)),

                    if product_exists == False:
                        product = Product.objects.create(minimum_order_qty=int(product_sheet.cell_value(row_number, 4)),

                                                         qty_metric=product_sheet.cell_value(
                                                             row_number, 5),
                                                         size=product_sheet.cell_value(row_number, 8),)
                        #weight_metric=product_sheet.cell_value(row_number, 11),
                        sourcing_user_product = SourcingUserProduct.objects.create(name=product_sheet.cell_value(row_number, 0),
                                                                                   code=product_sheet.cell_value(row_number, 1),
                                                                                    price=float(product_sheet.cell_value(row_number, 2)),
                                                                                    base_product=product,
                                                                                    other_info=product_sheet.cell_value(row_number, 6),
                                                                                    created_by=sourcing_user,
                                                                                    currency=product_sheet.cell_value(row_number, 3),
                                                                                    weight=product_sheet.cell_value(row_number, 10),

                                                                                    design=product_sheet.cell_value(row_number, 12),
                                                                                    pkg_inner=product_sheet.cell_value(row_number, 13),
                                                                                    pkg_m_ctn=product_sheet.cell_value(row_number, 14),
                                                                                    p_ctn_cbm=product_sheet.cell_value(row_number, 15),
                                                                                    ttl_ctn=product_sheet.cell_value(  row_number, 16),
                                                                                    ttl_cbm=product_sheet.cell_value(row_number, 17),
                                                                                    ship_lot_number=product_sheet.cell_value(row_number, 18))

                        count += 1
                        sourcing_user_factory = SourcingUserFactory.objects.get(
                            name=product_sheet.cell_value(row_number, 9))
                        sourcing_user_factory.products.add(product)
                        sourcing_user_factory.save()

                        colors = product_sheet.cell_value(
                            row_number, 7).split(", ")

                        for color in colors:

                            new_color, new_color_created = ColorGroup.objects.get_or_create(
                                name=color)
                            sourcing_user_product.base_product.color_group.add(new_color)
                            sourcing_user_product.save()

                    else:
                        existing_sourcing_user_product = SourcingUserProduct.objects.get(
                                name=product_sheet.cell_value(row_number, 0))
                        
                        try:
                            existing_product = existing_sourcing_user_product.base_product

                            existing_product.minimum_order_qty = get_format_value(
                                existing_product.minimum_order_qty, int(product_sheet.cell_value(row_number, 4)), upload_format)
                            # existing_product.order_qty = get_format_value(
                            #     existing_product.order_qty, product_sheet.cell_value(row_number, 5), upload_format)
                            existing_product.qty_metric = get_format_value(
                                existing_product.qty_metric, product_sheet.cell_value(row_number, 5), upload_format)
                            existing_product.size = get_format_value(
                                existing_product.size, product_sheet.cell_value(row_number, 8), upload_format)
                            existing_product.save()
                           
                        except Exception as e:
                            print(e)
                        existing_sourcing_user_product.name = get_format_value(
                            existing_sourcing_user_product.name, product_sheet.cell_value(row_number, 0), upload_format)
                        existing_sourcing_user_product.price = get_format_value(
                            existing_sourcing_user_product.price, float(product_sheet.cell_value(row_number, 2)), upload_format)
                        existing_sourcing_user_product.base_product = existing_product
                        existing_sourcing_user_product.other_info = get_format_value(
                            existing_sourcing_user_product.other_info, product_sheet.cell_value(row_number, 6), upload_format)
                        existing_sourcing_user_product.size = get_format_value(
                            existing_sourcing_user_product.base_product.size, product_sheet.cell_value(row_number, 8), upload_format)
                        existing_sourcing_user_product.created_by = sourcing_user
                        existing_sourcing_user_product.currency = get_format_value(
                            existing_sourcing_user_product.currency, product_sheet.cell_value(row_number, 3), upload_format)

                        existing_sourcing_user_product.weight = get_format_value(
                            existing_sourcing_user_product.weight, product_sheet.cell_value(row_number, 10), upload_format)

                        # existing_sourcing_user_product.weight_metric = get_format_value(
                        #     existing_sourcing_user_product.weight_metric, product_sheet.cell_value(row_number, 11), upload_format)

                        existing_sourcing_user_product.design = get_format_value(
                            existing_sourcing_user_product.design, product_sheet.cell_value(row_number, 12), upload_format)

                        existing_sourcing_user_product.pkg_inner = get_format_value(
                            existing_sourcing_user_product.pkg_inner, product_sheet.cell_value(row_number, 13), upload_format)

                        existing_sourcing_user_product.pkg_m_ctn = get_format_value(
                            existing_sourcing_user_product.pkg_m_ctn, product_sheet.cell_value(row_number, 14), upload_format)

                        existing_sourcing_user_product.p_ctn_cbm = get_format_value(
                            existing_sourcing_user_product.p_ctn_cbm, product_sheet.cell_value(row_number, 15), upload_format)

                        existing_sourcing_user_product.ttl_ctn = get_format_value(
                            existing_sourcing_user_product.ttl_ctn, product_sheet.cell_value(row_number, 16), upload_format)

                        existing_sourcing_user_product.ttl_cbm = get_format_value(
                            existing_sourcing_user_product.ttl_cbm, product_sheet.cell_value(row_number, 17), upload_format)

                        existing_sourcing_user_product.ship_lot_number = get_format_value(
                            existing_sourcing_user_product.ship_lot_number, product_sheet.cell_value(row_number, 18), upload_format)

                        colors = product_sheet.cell_value(
                            row_number, 7).split(", ")

                        

                        new_colors = get_colors(
                            colors, existing_sourcing_user_product.base_product.color_group.all(), upload_format)

                        if upload_format == 'partial_overwrite':
                            existing_sourcing_user_product.base_product.color_group.clear()
                            existing_sourcing_user_product.save()

                        temp_color_list = []
                        for color in new_colors:
                            temp_color, created = ColorGroup.objects.get_or_create(
                                name=color)
                            temp_color_list.append(temp_color)
                        existing_sourcing_user_product.base_product.color_group.add(
                            *temp_color_list)

                        existing_sourcing_user_product.save()
                        count += 1
                    print(count)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("UploadFactoriesProductsFromSourcingAPI: %s at %s",
                             e, str(exc_tb.tb_lineno))
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadFactoriesProductsFromSourcingAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


###########################


class AddNewProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddNewProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            if SourcingUserProduct.objects.filter(code=data["product-code"]).exists():
                response["message"] = "Duplicate product detected!"
                return Response(data=response)

            sourcing_user = SourcingUser.objects.get(
                username=request.user.username)

            product = Product.objects.create(minimum_order_qty=int(data["moq"]),
                                             order_qty=int(data["order-qty"]),
                                             qty_metric=data["qty-metric"])

            sourcing_user_product = SourcingUserProduct.objects.create(name=data["product-name"],
                                                                       code=data["product-code"],
                                                                       price=float(
                                                                           data["product-price"]),
                                                                       base_product=product,
                                                                       other_info=data["other-info"],
                                                                       created_by=sourcing_user,
                                                                       currency=data["currency"])

            factory = Factory.objects.get(pk=int(data["factory-pk"]))
            sourcing_user_factory = SourcingUserFactory.objects.get(
                base_factory=factory)
            sourcing_user_factory.products.add(product)
            sourcing_user_factory.save()

            for i in range(int(data["product-images-count"])):
                im_obj = Image.objects.create(
                    image=data["product-images-"+str(i)])
                sourcing_user_product.images.add(im_obj)
                sourcing_user_product.save()

            for i in range(int(data["attachments-count"])):
                at_obj = Attachment.objects.create(
                    attachment=data["attachment-"+str(i)])
                sourcing_user_product.attachments.add(at_obj)
                sourcing_user_product.save()

            response["pk"] = product.pk
            response["message"] = "Product added successfully!"
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddNewProductAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchProductDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchProductDetailsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product = Product.objects.get(pk=int(data["pk"]))
            sourcing_user_product = SourcingUserProduct.objects.get(
                base_product=product)

            try:
                factory_manager_product = FactoryManagerProduct.objects.get(
                    base_product=product)

                response["factory-manager-product-name"] = factory_manager_product.name
                response["factory-manager-product-code"] = factory_manager_product.code
                response["factory-manager-product-price"] = factory_manager_product.price
                response["factory-manager-product-price-currency"] = factory_manager_product.currency
            except Exception as e:
                response["factory-manager-product-name"] = ""
                response["factory-manager-product-code"] = ""
                response["factory-manager-product-price"] = ""
                response["factory-manager-product-price-currency"] = ""

            images_list = []
            images = sourcing_user_product.images.all()

            # print(len(images))

            if len(images) == 0:
                temp_dict = {}
                temp_dict["url"] = Config.objects.all()[0].DEFAULT_IMAGE.url
                images_list.append(temp_dict)

            for image in images:
                temp_dict = {}
                temp_dict["url"] = image.image.url
                temp_dict["pk"] = image.pk
                images_list.append(temp_dict)

            attachment_list = []
            attachments = sourcing_user_product.attachments.all()
            for attachment in attachments:
                temp_dict = {}
                temp_dict["url"] = attachment.attachment.name
                temp_dict["pk"] = attachment.pk
                temp_dict["name"] = os.path.basename(
                    attachment.attachment.file.name)
                attachment_list.append(temp_dict)

            response["factory-name"] = ""
            response["factory-pk"] = ""
            if product.sourcinguserfactory_set.all().count() > 0:
                temp_factory = product.sourcinguserfactory_set.all()[0]
                response["factory-name"] = temp_factory.name
                response["factory-pk"] = temp_factory.base_factory.pk

                try:
                    temp_factory = product.factorymanagerfactory_set.all()[0]
                    response["factory-manager-factory-name"] = temp_factory.name
                except Exception as e:
                    response["factory-manager-factory-name"] = ""

            response["product-name"] = sourcing_user_product.name
            response["product-code"] = sourcing_user_product.code
            response["product-price"] = sourcing_user_product.price

            response["is_pr_ready"] = product.is_pr_ready

            response["moq"] = product.minimum_order_qty
            response["order-qty"] = product.order_qty
            response["other-info"] = sourcing_user_product.other_info
            response["images"] = images_list
            response["attachments"] = attachment_list
            response["currency"] = sourcing_user_product.currency
            response["qty-metric"] = product.qty_metric
            response["pk"] = product.pk

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SavePhoneNumbersAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SavePhoneNumbersAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            phone_numbers_list = json.loads(data["phone_numbers"])

            factory = Factory.objects.get(pk=int(data["pk"]))
            sourcing_user_factory = SourcingUserFactory.objects.get(
                base_factory=factory)
            phone_number_objs = factory.phone_numbers.all()
            for phone_number_obj in phone_number_objs:
                phone_number_obj.delete()

            for phone_number in phone_numbers_list:
                p_obj = PhoneNumber.objects.create(number=str(phone_number))
                factory.phone_numbers.add(p_obj)
                factory.save()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SavePhoneNumbersAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveAddressAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SaveAddressAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            address = data["address"]

            factory = Factory.objects.get(pk=int(data["pk"]))
            factory.address = address
            factory.save()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveAddressAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveFactoryNameAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SaveFactoryNameAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            factory_name = data["factory_name"]

            factory = Factory.objects.get(pk=int(data["pk"]))
            sourcing_user_factory = SourcingUserFactory.objects.get(
                base_factory=factory)
            sourcing_user_factory.name = factory_name
            sourcing_user_factory.save()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveFactoryNameAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveProductDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SaveProductDetailsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_name = data["product_name"]
            product_price = data["product_price"]
            product_code = data["product_code"]
            moq = data["moq"]
            order_qty = data["order_qty"]
            other_info = data["other_info"]
            qty_metric = data["qty_metric"]
            currency = data["currency"]

            product = Product.objects.get(pk=int(data["pk"]))
            sourcing_user_product = SourcingUserProduct.objects.get(
                base_product=product)
            sourcing_user_product.name = product_name
            sourcing_user_product.price = float(product_price)
            sourcing_user_product.code = product_code
            product.minimum_order_qty = int(moq)
            product.order_qty = int(order_qty)
            sourcing_user_product.other_info = other_info
            sourcing_user_product.currency = currency
            product.qty_metric = qty_metric
            sourcing_user_product.save()
            product.save()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveProductDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveBusinessCardAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SaveBusinessCardAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            factory = Factory.objects.get(pk=int(data["pk"]))
            image_obj = Image.objects.create(image=data["business-card"])
            factory.business_card = image_obj
            factory.save()

            response["image-url"] = factory.business_card.image.url
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveBusinessCardAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadProductImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UploadProductImageAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product = Product.objects.get(pk=int(data["pk"]))
            sourcing_user_product = SourcingUserProduct.objects.get(
                base_product=product)
            im_obj = Image.objects.create(image=data["product-image"])
            sourcing_user_product.images.add(im_obj)
            sourcing_user_product.save()

            response["image-url"] = im_obj.image.url
            response["pk"] = im_obj.pk
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadProductImageAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DeleteImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("DeleteImageAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            Image.objects.get(pk=int(data["pk"])).delete()
            product = Product.objects.get(pk=int(data["product_pk"]))
            sourcing_user_product = SourcingUserProduct.objects.get(
                base_product=product)

            images_list = []
            images = sourcing_user_product.images.all()
            for image in images:
                temp_dict = {}
                temp_dict["url"] = image.image.url
                temp_dict["pk"] = image.pk
                images_list.append(temp_dict)

            response["images"] = images_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteImageAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadAttachmentAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UploadAttachmentAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product = Product.objects.get(pk=int(data["pk"]))
            sourcing_user_product = SourcingUserProduct.objects.get(
                base_product=product)
            attachment_obj = Attachment.objects.create(
                attachment=data["attachment"])
            sourcing_user_product.attachments.add(attachment_obj)
            sourcing_user_product.save()

            response["url"] = attachment_obj.attachment.name
            response["name"] = os.path.basename(
                attachment_obj.attachment.file.name)
            response["pk"] = attachment_obj.pk
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadAttachmentAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DeleteAttachmentAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("DeleteAttachmentAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            Attachment.objects.get(pk=int(data["pk"])).delete()
            product = Product.objects.get(pk=int(data["product_pk"]))
            sourcing_user_product = SourcingUserProduct.objects.get(
                base_product=product)
            attachment_list = []
            attachments = sourcing_user_product.attachments.all()
            for attachment in attachments:
                temp_dict = {}
                temp_dict["url"] = attachment.attachment.name
                temp_dict["pk"] = attachment.pk
                temp_dict["name"] = os.path.basename(
                    attachment.attachment.file.name)
                attachment_list.append(temp_dict)

            response["attachments"] = attachment_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteAttachmentAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchProductCardsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchProductCardsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            # sourcing_user = SourcingUser.objects.get(username=request.user.username)
            # sourcing_user_product_list = SourcingUserProduct.objects.filter(created_by=sourcing_user).order_by('-pk')
            sourcing_user_product_list = SourcingUserProduct.objects.all()
            paginator = Paginator(sourcing_user_product_list, 4)

            page = int(data["card_page"])
            print("Page number received: ", page)
            sourcing_user_products = paginator.page(page)
            products = []

            for sourcing_user_product in sourcing_user_products:
                temp_dict = {}
                product = sourcing_user_product.base_product
                temp_dict["name"] = sourcing_user_product.name
                temp_dict["code"] = sourcing_user_product.code
                temp_dict["price"] = sourcing_user_product.price
                temp_dict["moq"] = product.minimum_order_qty
                temp_dict["order-qty"] = product.order_qty
                temp_dict["other-info"] = sourcing_user_product.other_info
                temp_dict["currency"] = sourcing_user_product.currency
                temp_dict["qty-metric"] = product.qty_metric

                temp_dict["pk"] = product.pk
                temp_dict["image-url"] = ""

                if sourcing_user_product.images.all().count() > 0:
                    temp_dict["image-url"] = sourcing_user_product.images.all()[0].image.url
                else:
                    temp_dict["image-url"] = Config.objects.all()[0].DEFAULT_IMAGE.url

                temp_dict["factory-name"] = ""
                temp_dict["factory-pk"] = ""

                if product.sourcinguserfactory_set.all().count() > 0:
                    temp_factory = product.sourcinguserfactory_set.all()[0]
                    temp_dict["factory-name"] = temp_factory.name
                    temp_dict["factory-pk"] = temp_factory.pk

                products.append(temp_dict)

            is_available = True
            if paginator.num_pages == page:
                is_available = False

            response["total-products"] = SourcingUserProduct.objects.all().count()
            response["is_available"] = is_available
            response["products"] = products
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductCardsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveFactoryDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SaveFactoryDetailsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            factory = Factory.objects.get(pk=int(data["pk"]))
            sourcing_user_factory = SourcingUserFactory.objects.get(
                base_factory=factory)
            sourcing_user_factory.name = data["name"]
            factory.address = data["address"]
            factory.factory_emailid = data["factory_emailid"]
            factory.contact_person_name = data["contact_person_name"]
            factory.contact_person_mobile_no = data["contact_person_mobile_no"]
            factory.contact_person_emailid = data["contact_person_emailid"]
            factory.social_media_tag = data["social_media_tag"]
            factory.social_media_tag_information = data["social_media_tag_information"]
            factory.loading_port = data["loading_port"]
            factory.location = data["location"]
            factory.other_info = data["other_info"]
            factory.save()

            phone_numbers = json.loads(data["phone_numbers"])
            phone_numbers_old = factory.phone_numbers.all()
            for phone in phone_numbers_old:
                phone.delete()

            for phone_number in phone_numbers:
                phone_number_obj = PhoneNumber.objects.create(
                    str(number=phone_number))
                factory.phone_numbers.add(phone_number_obj)
                factory.save()

            response["name"] = sourcing_user_factory.name
            response["address"] = factory.address
            response["phone_numbers"] = phone_numbers
            response["factory_emailid"] = factory.factory_emailid
            response["contact_person_name"] = factory.contact_person_name
            response["contact_person_mobile_no"] = factory.contact_person_mobile_no
            response["contact_person_emailid"] = factory.contact_person_emailid
            response["social_media_tag"] = factory.social_media_tag
            response["social_media_tag_information"] = factory.social_media_tag_information
            response["loading_port"] = factory.loading_port
            response["location"] = factory.location
            response["other_info"] = factory.other_info

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveFactoryDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class ExportFactoriesAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("ExportFactoriesAPI: %s", str(data))

            email_id = data["email_id_list"]

            factories = Factory.objects.all()

            factory_file = open("./files/factories.csv", mode='w')
            writer = csv.writer(factory_file, delimiter=',',
                                quotechar='"', quoting=csv.QUOTE_MINIMAL)

            row = ["UID", "Name", "Main Image URL", "Creation date", "Count of products", "Created By",
                   "Factory Email Id", "Contact Person", "Contact Person Mobile Number",
                   "Contact Person Email ID", "Social Media", "Social Media Information",
                   "Loading Port", "Location"]
            writer.writerow(row)

            for factory in factories:
                sourcing_user_factory = SourcingUserFactory.objects.get(
                    base_factory=factory)
                products_count = sourcing_user_factory.products.all().count()
                img_url = ""

                if(factory.business_card != None and factory.business_card.image != "undefined" and factory.business_card.image != ""):
                    img_url = factory.business_card.image.url
                row = [str(factory.pk), str(factory.name), str(IP_ADDR + img_url),
                       str(factory.created_date.strftime("%d, %b %Y ")),
                       str(products_count), str(
                           factory.sourcing_manager.username),
                       str(factory.factory_emailid), str(
                           factory.contact_person_name),
                       str(factory.contact_person_mobile_no), str(
                           factory.contact_person_emailid),
                       str(factory.social_media_tag), str(
                           factory.social_media_tag_information),
                       str(factory.loading_port), str(factory.location)]

                print(row)
                writer.writerow(row)

            product_file = open("./files/products.csv", mode='w')
            product_writer = csv.writer(product_file, delimiter=',', quotechar='"',
                                        quoting=csv.QUOTE_MINIMAL)

            product_row = ["Product Id", "Product Name", "Factory UID", "Created Date",
                           "Created By", "Price", "Currency", "Minimum Order Quantity",
                           "Quantity Metric", "Image 1 url", "Image 2 url", "Image 3 url",
                           "Image 4 url", "Image 5 url"]
            product_writer.writerow(product_row)

            for factory in factories:
                sourcing_user_factory = SourcingUserFactory.objects.get(
                    base_factory=factory)
                products = sourcing_user_factory.products.all()
                for product in products:
                    img_url = ""
                    sourcing_user_product = SourcingUserProduct.objects.get(
                        base_product=product)
                    product_row = [str(product.pk), str(sourcing_user_product.name),
                                   str(factory.pk),
                                   str(factory.created_date.strftime(
                                       "%d, %b %Y ")),
                                   str(sourcing_user_product.created_by.username),
                                   str(sourcing_user_product.price), str(
                                       sourcing_user_product.currency),
                                   str(product.minimum_order_qty),
                                   str(product.qty_metric)]
                    if(sourcing_user_product.images.all().count() != 0):
                        images = product.images.all()
                        for img in images:
                            img_url = img.image.url
                            product_row.append(str(IP_ADDR + img_url))
                    print()
                    print(product_row)
                    print()
                    product_writer.writerow(product_row)

            factory_file.close()
            product_file.close()

            email = EmailMessage(
                str("Factory and Product Details"), str("PFA"), to=[email_id])
            email.attach_file("./files/factories.csv")
            email.attach_file("./files/products.csv")
            print()
            print(email.__dict__)
            print()
            email.send()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ExportFactoriesAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SendFactoryShareEmailAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SendFactoryShareEmailAPI: %s", str(data))

            email_id = data["email_id_list"]
            signup_url = data["signup_url"]

            email = EmailMessage(str("Factory shared with you"),
                                 str(signup_url), to=[email_id])
            print(email.__dict__)
            email.send()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SendFactoryShareEmailAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SearchFactoriesAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SearchFactoriesAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            query = data["query"]

            sourcing_user_factories = SourcingUserFactory.objects.filter(
                name__icontains=query)

            factory_list = []
            for sourcing_user_factory in sourcing_user_factories:
                factory = sourcing_user_factory.base_factory
                temp_dict = {}
                temp_dict["name"] = sourcing_user_factory.name
                if factory.business_card != None and factory.business_card.image != "" and factory.business_card.image != "undefined":

                    temp_dict["business-card"] = factory.business_card.image.url
                else:
                    temp_dict["business-card"] = Config.objects.all()[0].DEFAULT_IMAGE.url
                temp_dict["address"] = factory.address
                temp_dict["pk"] = factory.pk
                temp_dict["contact-person-mobile-no"] = factory.contact_person_mobile_no
                temp_dict["contact-person-name"] = factory.contact_person_name
                temp_dict["contact-person-emailid"] = factory.contact_person_emailid
                temp_dict["loading-port"] = factory.loading_port
                temp_dict["location"] = factory.location
                temp_dict["social-media-tag"] = factory.social_media_tag
                temp_dict["social-media-tag-information"] = factory.social_media_tag_information
                phone_numbers = []
                for phone_number in factory.phone_numbers.all():
                    phone_numbers.append(phone_number.number)
                temp_dict["phone-numbers"] = phone_numbers
                temp_dict["total-products"] = sourcing_user_factory.products.all().count()
                factory_list.append(temp_dict)

            sourcing_user = SourcingUser.objects.get(
                username=request.user.username)
            if SourcingUserFactory.objects.filter(created_by=sourcing_user).count() == 0:
                response["tutorial_enable"] = True
            else:
                response["tutorial_enable"] = False

            response["factory_list"] = factory_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchFactoriesAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SearchFactoriesByDateAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SearchFactoriesByDateAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            start_date = data["start_date"]
            end_date = data["end_date"]

            if y < x:
                response["error_msg"] = "The start date can not be more than end date"
            else:
                start_date = datetime.strptime(start_date, "%b %d, %Y")
                end_date = datetime.strptime(end_date, "%b %d, %Y")

                if start_date == end_date:
                    factories = Factory.objects.filter(
                        created_date__date=start_date)
                else:
                    factories = Factory.objects.filter(
                        created_date__date__range=[start_date, end_date])

                sourcing_user_factories = []
                for factory in factories:
                    sourcing_user_factory = SourcingUserFactory.objects.get(
                        base_factory=factory)
                    sourcing_user_factories.append(sourcing_user_factory)

                factory_list = []
                for sourcing_user_factory in sourcing_user_factories:
                    factory = sourcing_user_factory.base_factory
                    temp_dict = {}
                    temp_dict["name"] = sourcing_user_factory.name
                    if factory.business_card != None and factory.business_card.image != "" and factory.business_card.image != "undefined":
                        temp_dict["business-card"] = factory.business_card.image.url
                    else:
                        temp_dict["business-card"] = Config.objects.all()[0].DEFAULT_IMAGE.url
                    temp_dict["address"] = factory.address
                    temp_dict["pk"] = factory.pk
                    temp_dict["contact-person-mobile-no"] = factory.contact_person_mobile_no
                    temp_dict["contact-person-name"] = factory.contact_person_name
                    temp_dict["contact-person-emailid"] = factory.contact_person_emailid
                    temp_dict["loading-port"] = factory.loading_port
                    temp_dict["location"] = factory.location
                    temp_dict["social-media-tag"] = factory.social_media_tag
                    temp_dict["social-media-tag-information"] = factory.social_media_tag_information
                    phone_numbers = []
                    for phone_number in factory.phone_numbers.all():
                        phone_numbers.append(phone_number.number)
                    temp_dict["phone-numbers"] = phone_numbers
                    temp_dict["total-products"] = sourcing_user_factory.products.all().count()
                    factory_list.append(temp_dict)

                sourcing_user = SourcingUser.objects.get(
                    username=request.user.username)
                if SourcingUserFactory.objects.filter(created_by=sourcing_user).count() == 0:
                    response["tutorial_enable"] = True
                else:
                    response["tutorial_enable"] = False

                response["factory_list"] = factory_list
                response["status"] = 200
                response["error_msg"] = ""

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchFactoriesByDateAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SearchProductsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SearchProductsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            query = data["query"]

            sourcing_user_products = SourcingUserProduct.objects.filter(
                name__icontains=query).order_by('-pk')

            products = []
            for sourcing_user_product in sourcing_user_products:
                temp_dict = {}
                product = sourcing_user_product.base_product
                temp_dict["name"] = sourcing_user_product.name
                temp_dict["code"] = sourcing_user_product.code
                temp_dict["price"] = sourcing_user_product.price
                temp_dict["moq"] = product.minimum_order_qty
                temp_dict["order-qty"] = product.order_qty
                temp_dict["other-info"] = sourcing_user_product.other_info
                temp_dict["currency"] = sourcing_user_product.currency
                temp_dict["qty-metric"] = product.qty_metric

                temp_dict["pk"] = product.pk
                temp_dict["image-url"] = ""
                if sourcing_user_product.images.all().count() > 0:
                    temp_dict["image-url"] = sourcing_user_product.images.all()[0].image.url
                else:
                    temp_dict["image-url"] = Config.objects.all()[0].DEFAULT_IMAGE.url
                temp_dict["factory-name"] = ""
                temp_dict["factory-pk"] = ""
                if product.sourcinguserfactory_set.all().count() > 0:
                    temp_factory = product.sourcinguserfactory_set.all()[0]
                    temp_dict["factory-name"] = temp_factory.name
                    temp_dict["factory-pk"] = temp_factory.pk

                products.append(temp_dict)

            response["total-products"] = sourcing_user_products.count()
            response["products"] = products
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchProductsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class ShareFactoryAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("ShareFactoryAPI: %s", str(data))

            uuid_obj = ""
            if not isinstance(data, dict):
                data = json.loads(data)

            factory = Factory.objects.get(pk=int(data["pk"]))

            sourcing_user_factory = SourcingUserFactory.objects.get(
                base_factory=factory)

            factory_manager_factory, created = FactoryManagerFactory.objects.get_or_create(
                name=sourcing_user_factory.name, base_factory=factory)

            products = sourcing_user_factory.products.all()
            for product in products:
                sourcing_user_product = SourcingUserProduct.objects.get(
                    base_product=product)
                if sourcing_user_product.is_shared == True:
                    factory_manager_factory.products.add(product)

            factory_manager_factory.save()

            uuid_exists = LinkGenerator.objects.filter(
                factory=factory).exists()

            if uuid_exists:

                link_generator_obj = LinkGenerator.objects.get(factory=factory)
                uuid_obj = link_generator_obj.uuid
                response["uuid"] = str(uuid_obj)

            else:
                uuid_obj = uuid.uuid4()
                link_generator_obj = LinkGenerator.objects.create(
                    uuid=str(uuid_obj), factory=factory)
                response["uuid"] = str(uuid_obj)

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ShareFactoryAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class ShareProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("ShareProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product = Product.objects.get(pk=int(data["pk"]))
            sourcing_user_product = SourcingUserProduct.objects.get(
                base_product=product)
            sourcing_user_product.is_shared = True
            sourcing_user_product.save()

            sourcing_user_factory = SourcingUserFactory.objects.get(
                pk=data["factory_pk"])
            factory = sourcing_user_factory.base_factory

            if FactoryManagerFactory.objects.filter(base_factory=factory).exists():
                factory_manager_factory = FactoryManagerFactory.objects.get(
                    base_factory=factory)
            else:
                factory_manager_factory, created = FactoryManagerFactory.objects.get_or_create(
                    base_factory=factory, name=sourcing_user_factory.name)

            factory_manager_product = FactoryManagerProduct.objects.create(name=sourcing_user_product.name,
                                                                           code=sourcing_user_product.code,
                                                                           price=sourcing_user_product.price,
                                                                           currency=sourcing_user_product.currency,
                                                                           base_product=product)  # ,
            # images = sourcing_user_product.images.all(),
            # certifications = sourcing_user_product.certifications.all(),
            # attachments = sourcing_user_product.attachments.all())

            factory_manager_factory.products.add(product)
            factory_manager_factory.save()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ShareProductAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchFactoryNameFromUUIDAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchFactoryNameFromUUIDAPI: %s", str(data))

            uuid_obj = data['factory_uuid']

            link_generator_obj = LinkGenerator.objects.get(uuid=str(uuid_obj))

            factory = link_generator_obj.factory
            factory_manager_factory = FactoryManagerFactory.objects.get(base_factory=factory)

            response["factory-name"] = factory_manager_factory.name
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFactoryNameFromUUIDAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)   

class FetchFactoryForSourcingUserAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchFactoryForSourcingUserAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            pk = int(data['pk'])
            sourcing_user_factory = SourcingUserFactory.objects.get(pk=pk)

            temp_dict = {}
            temp_dict["name"] = sourcing_user_factory.name
            temp_dict["address"] = sourcing_user_factory.base_factory.address
            temp_dict["email_id"] = sourcing_user_factory.base_factory.factory_emailid

            temp_dict["loading_port"] = sourcing_user_factory.base_factory.loading_port
            temp_dict["location"] = sourcing_user_factory.base_factory.location

            temp_dict["notes"] = sourcing_user_factory.other_info
            temp_dict["contact_person_name"] = sourcing_user_factory.base_factory.contact_person_name
            temp_dict["contact_person_mobile_number"] = sourcing_user_factory.base_factory.contact_person_mobile_no
            temp_dict["contact_person_email_id"] = sourcing_user_factory.base_factory.contact_person_emailid
            temp_dict["tag"] = sourcing_user_factory.base_factory.social_media_tag
            temp_dict["tag_info"] = sourcing_user_factory.base_factory.social_media_tag_information
            
            if sourcing_user_factory.base_factory.bank_details:
                temp_dict["bank_name"] = sourcing_user_factory.base_factory.bank_details.name
                temp_dict["bank_address"] = sourcing_user_factory.base_factory.bank_details.address
                temp_dict["bank_account_number"] = sourcing_user_factory.base_factory.bank_details.account_number
                temp_dict["bank_ifsc_code"] = sourcing_user_factory.base_factory.bank_details.ifsc_code
                temp_dict["bank_swift_code"] = sourcing_user_factory.base_factory.bank_details.swift_code
                temp_dict["bank_branch_code"] = sourcing_user_factory.base_factory.bank_details.branch_code

            temp_dict["pk"] = sourcing_user_factory.pk
            phone_numbers = []
            for phone_number in sourcing_user_factory.base_factory.phone_numbers.all():
                phone_numbers.append(phone_number.number)
            temp_dict["phone-numbers"] = phone_numbers
            images_list = []
            if sourcing_user_factory.images.all().count() > 0:
                for image in sourcing_user_factory.images.all():
                    temp_dict2 = {}
                    temp_dict2["url"] = image.image.url
                    temp_dict2["pk"] = image.pk
                    images_list.append(temp_dict2)
            temp_dict["images_list"] = images_list
            print(temp_dict["images_list"])
            operating_hours = []
            for operating_hour in sourcing_user_factory.base_factory.operating_hours.all():
                operating_hour_dict = {}
                operating_hour_dict["day"] = operating_hour.day
                operating_hour_dict["from_time"] = str(operating_hour.from_time)
                operating_hour_dict["to_time"] = str(operating_hour.to_time)
                operating_hours.append(operating_hour_dict)
            temp_dict["operating-hours"] = operating_hours
            if(sourcing_user_factory.base_factory.logo != None and sourcing_user_factory.logo != ""):
                temp_dict["logo"] = sourcing_user_factory.base_factory.logo.image.url
            else:
                temp_dict["logo"] = Config.objects.all()[
                    0].DEFAULT_IMAGE.url
            # temp_dict["bank-details"] = sourcing_user_factory.base_factory.bank_details
            temp_dict["total-products"] = sourcing_user_factory.products.all().count()

 
            response["factory"] = temp_dict
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFactoryForSourcingUserAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchFactoriesForSourcingUserAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchFactoriesForSourcingUserAPI: %s", str(data))
            
            sourcing_user = SourcingUser.objects.get(username=request.user.username)
            
            chip_data = json.loads(data['tags'])

            factories = SourcingUserFactory.objects.filter(Q(created_by=sourcing_user) | 
                Q(created_by__reports_to=sourcing_user))
            if len(chip_data)>0:
                for tag in chip_data:
                    factories = factories.filter(name__icontains = tag)
            factory_list = []
            
            for factory in factories:
                temp_dict = {}
                temp_dict["name"] = factory.name
                temp_dict["address"] = factory.base_factory.address
                temp_dict["pk"] = factory.pk
                phone_numbers = []
                for phone_number in factory.base_factory.phone_numbers.all():
                    phone_numbers.append(phone_number.number)
                temp_dict["phone-numbers"] = phone_numbers
                images_list = []
                
                try:
                    temp_dict["business_card"] = factory.base_factory.business_card.image.url
                except Exception as e:
                    print(e, factory.base_factory.pk)
                    temp_dict["business_card"] = Config.objects.all()[
                        0].DEFAULT_IMAGE.url

                
                operating_hours = []
                for operating_hour in factory.base_factory.operating_hours.all():
                    operating_hour_dict = {}
                    operating_hour_dict["day"] = operating_hour.day
                    operating_hour_dict["from_time"] = str(operating_hour.from_time)
                    operating_hour_dict["to_time"] = str(operating_hour.to_time)
                    operating_hours.append(operating_hour_dict)
                temp_dict["operating-hours"] = operating_hours
                # print(factory.logo)
                if(factory.base_factory.logo != None and factory.base_factory.logo != ""):
                    temp_dict["logo"] = factory.base_factory.logo.image.url
                elif len(factory.images.all()) > 0:
                    temp_dict["logo"] = factory.images.all()[0].image.url
                else:
                    temp_dict["logo"] = Config.objects.all()[
                        0].DEFAULT_IMAGE.url
              
                temp_dict["total-products"] = factory.products.all().count()

                temp_dict["average_delivery_days"] = factory.base_factory.average_delivery_days
                temp_dict["average_turn_around_time"] = factory.base_factory.average_turn_around_time


                factory_list.append(temp_dict)
 
            response["factories"] = factory_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFactoriesForSourcingUserAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)



class FetchSourcingUserDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchSourcingUserDetailsAPI: %s", str(data))
            
            sourcing_user = SourcingUser.objects.get(username=request.user.username)
            temp_dict = {}

            temp_dict["name"] = sourcing_user.username
            temp_dict["pk"] = sourcing_user.pk
            factory = factory_manager.factory
            factory_manager_factory = FactoryManagerFactory.objects.get(base_factory=factory)

            temp_dict = {}
            temp_dict["name"] = factory_manager_factory.name
            temp_dict["address"] = factory.address
            temp_dict["pk"] = factory.pk
            phone_numbers = []
            for phone_number in factory.phone_numbers.all():
                phone_numbers.append(phone_number.number)
            temp_dict["phone-numbers"] = phone_numbers
            images_list = []

            for image in factory_manager_factory.images.all():
                temp_dict2 = {}
                temp_dict2["url"] = image.image.url
                temp_dict2["pk"] = image.pk
                images_list.append(temp_dict)
            temp_dict["images_list"] = images_list
            operating_hours = []
            for operating_hour in factory.operating_hours.all():
                operating_hour_dict = {}
                operating_hour_dict["day"] = operating_hour.day
                operating_hour_dict["from_time"] = str(operating_hour.from_time)
                operating_hour_dict["to_time"] = str(operating_hour.to_time)
                operating_hours.append(operating_hour_dict)
            temp_dict["operating-hours"] = operating_hours
            
            if(factory.logo != None and factory.logo != ""):
                temp_dict["logo"] = factory.logo.image.url
            else:
                temp_dict["logo"] = ""
            temp_dict["bank-details"] = factory.bank_details
            temp_dict["total-products"] = factory_manager_factory.products.all().count()

 
            response["factory"] = json.dumps(temp_dict)
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSourcingUserDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)



class FetchProductsFromFactoryAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        is_sourcing_user = False

        try:
            is_sourcing_user = SourcingUser.objects.filter(username=request.user.username).exists()
        except Exception as e:
            print("User is not sourcing user")

        
        try:
            data = request.data
            logger.info("FetchProductsFromFactoryAPI: %s", str(data))
            products = []
            chip_data = json.loads(data['tags'])
            if is_sourcing_user:
                logger.info("FetchProductsFromFactoryAPI: debugging %s", is_sourcing_user)
                sourcing_user = SourcingUser.objects.get(username=request.user.username)

                factories = SourcingUserFactory.objects.filter(Q(created_by=sourcing_user) | 
                Q(created_by__reports_to=sourcing_user))
                products_objs = SourcingUserProduct.objects.filter(Q(created_by=sourcing_user) |
                                                              Q(created_by__reports_to=sourcing_user))
                if len(chip_data) != 0:
                    for tag in chip_data:
                        search = factories.filter(name__icontains=tag)
                        factories = search
              
                if len(chip_data) != 0:
                    for tag in chip_data:
                        search = products_objs.filter(name__icontains=tag)
                        products_objs = search
                products_objs = set(products_objs)
               
                try:                    
                    for product_temp in products_objs:
                        sourcing_user_product = product_temp
                        temp_dict = {}

                        temp_dict["factory_pk"] = SourcingUserFactory.objects.get(products = product_temp.base_product).pk
                        temp_dict["factory_name"] =  SourcingUserFactory.objects.get(products = product_temp.base_product).name
                        temp_dict["name"] = sourcing_user_product.name
                        temp_dict["code"] = sourcing_user_product.code
                        temp_dict["price"] = sourcing_user_product.price
                        temp_dict["currency"] = sourcing_user_product.currency
                        temp_dict["moq"] = product_temp.base_product.minimum_order_qty
                        temp_dict["minimum-order-qty"] = product_temp.base_product.minimum_order_qty
                        temp_dict["qty-metric"] = product_temp.base_product.qty_metric
                        temp_dict["order-qty"] = product_temp.base_product.order_qty
                        temp_dict["other-info"] = sourcing_user_product.other_info
                        temp_dict["created-date"] = product_temp.base_product.created_date
                        temp_dict["go-live-status"] = product_temp.base_product.go_live
                        temp_dict["delivery_days"] = product_temp.base_product.delivery_days

                        temp_dict["pk"] = product_temp.base_product.pk
                        temp_dict["image-url"] = ""
                        if sourcing_user_product.images.all().count()>0:
                            temp_dict["image-url"] = sourcing_user_product.images.all()[
                                0].image.url
                        else :
                            temp_dict["image-url"] = Config.objects.all()[0].DEFAULT_IMAGE.url

                        products.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchProductsFromFactoryAPI: %s at %s",
                        e, str(exc_tb.tb_lineno))

            else:

                factory_manager = FactoryManager.objects.get(username=request.user.username)
                factory = factory_manager.factory
                factory_manager_factory = FactoryManagerFactory.objects.get(base_factory=factory)
                product_objs = factory_manager_factory.products.filter(is_pr_ready = True)
                
                for product in product_objs:

                    factory_manager_product = FactoryManagerProduct.objects.get(base_product=product)
                    print(factory_manager_product.name, product.is_pr_ready)
                    temp_dict = {}
                    temp_dict["name"] = factory_manager_product.name
                    temp_dict["code"] = factory_manager_product.code
                    temp_dict["price"] = factory_manager_product.price
                    temp_dict["currency"] = factory_manager_product.currency
                    temp_dict["moq"] = product.minimum_order_qty
                    temp_dict["minimum-order-qty"] = product.minimum_order_qty
                    temp_dict["qty-metric"] = product.qty_metric
                    temp_dict["order-qty"] = product.order_qty
                    temp_dict["other-info"] = factory_manager_product.other_info
                    temp_dict["created-date"] = product.created_date

                    temp_dict["pk"] = product.pk
                    temp_dict["image-url"] = ""
                    if factory_manager_product.images.all().count()>0:
                        temp_dict["image-url"] = factory_manager_product.images.all()[0].image.url
                    else :
                        temp_dict["image-url"] = Config.objects.all()[0].DEFAULT_IMAGE.url

                    products.append(temp_dict)
                

            response["products"] = products
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductsFromFactoryAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchSharedProductsForFactoryAPI(APIView):

    def post(self, request, *args, **kwargs):


        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchSharedProductsForFactoryAPI: %s", str(data))
            
            factory_manager = FactoryManager.objects.get(username=request.user.username)
            factory = factory_manager.factory
            factory_manager_factory = FactoryManagerFactory.objects.get(base_factory=factory)
            product_objs = factory_manager_factory.products.all()
            products = []
            for product in product_objs:
                sourcing_user_product = SourcingUserProduct.objects.get(base_product=product)
                factory_manager_product = FactoryManagerProduct.objects.get(base_product=product)
                temp_dict = {}
                temp_dict["name"] = sourcing_user_product.name
                temp_dict["code"] = sourcing_user_product.code
                temp_dict["price"] = sourcing_user_product.price
                temp_dict["currency"] = sourcing_user_product.currency
                temp_dict["minimum-order-qty"] = product.minimum_order_qty
                temp_dict["qty-metric"] = product.qty_metric
                temp_dict["order-qty"] = product.order_qty
                temp_dict["other-info"] = sourcing_user_product.other_info
                temp_dict["created-date"] = product.created_date
                temp_dict["export_carton_qty_l"] = product.export_carton_qty_l
                temp_dict["export_carton_qty_r"] = product.export_carton_qty_r
                temp_dict["export_carton_qty_h"] = product.export_carton_qty_h
                temp_dict["gift_box_l"] = product.gift_box_l
                temp_dict["gift_box_r"] = product.gift_box_r
                temp_dict["gift_box_h"] = product.gift_box_h
  
                #Fields important for calculating the progress bar
                try:
                    temp_dict["factory_manager_product_name"] = factory_manager_product.name
                    temp_dict["factory_manager_product_price"] = factory_manager_product.price
                    temp_dict["factory_manager_product_currency"] = factory_manager_product.currency
                except Exception as e:
                    print(e)

                temp_dict["spare_part_name"] = product.spare_part_name
                temp_dict["spare_part_qty"] = product.spare_part_qty

                temp_dict["pk"] = product.pk
                temp_dict["image-url"] = ""
                if sourcing_user_product.images.all().count()>0:
                    temp_dict["image-url"] = sourcing_user_product.images.all()[0].image.url
                else :
                    temp_dict["image-url"] = Config.objects.all()[0].DEFAULT_IMAGE.url

                products.append(temp_dict)

            response["products"] = set(products)
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSharedProductsForFactoryAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class SaveSourcingProductDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):
        print("SaveSourcingProductDetailsAPI")
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SaveSourcingProductDetailsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product = Product.objects.get(pk=int(data["pk"]))

            sourcing_user_product = SourcingUserProduct.objects.get(
                base_product=product)

            sourcing_user_product.name = data["product_name"]

            if data["product_price"] != "":
                sourcing_user_product.price = float(data["product_price"])

            sourcing_user_product.code = data["product_code"]

            if data["minimum_order_qty"] != "":
                product.minimum_order_qty = int(data["minimum_order_qty"])

            if data["order_qty"] != "":
                product.order_qty = int(data["order_qty"])
          
            product.qty_metric = data["qty_metric"]
            sourcing_user_product.currency = data["currency"]

            if data["inner_box_qty"] != "":
                product.inner_box_qty = int(data["inner_box_qty"])

            if data["country"] != "":
                country = Country.objects.get(pk=int(data["country"]))
                product.country = country

            if data["technical_specs"] != "":
                technical_specs = TechnicalSpecs.objects.get(
                    pk=int(data["technical_specs"]))
                product.technical_specs = technical_specs

            product.spare_part_name = data["spare_part_name"]

            if data["spare_part_qty"] != "":
                product.spare_part_qty = int(data["spare_part_qty"])

            if data["category"] != "":
                category = Category.objects.get(pk=int(data["category"]))
                product.category = category

            if data["delivery_days"] != "":
                product.delivery_days = int(data["delivery_days"])

            if data["material_specs"] != "":
                material_specs = MaterialSpecs.objects.get(
                    pk=int(data["material_specs"]))
                product.material_specs = material_specs

            if data["export_carton_qty_l"] != "":
                product.export_carton_qty_l = float(
                    data["export_carton_qty_l"])

            if data["export_carton_qty_r"] != "":
                product.export_carton_qty_r = float(
                    data["export_carton_qty_r"])

            if data["export_carton_qty_h"] != "":

                product.export_carton_qty_h = float(
                    data["export_carton_qty_h"])

            if data["export_carton_crm_l"] != "":
                product.export_carton_crm_l = float(
                    data["export_carton_crm_l"])

            if data["export_carton_crm_r"] != "":
                product.export_carton_crm_r = float(
                    data["export_carton_crm_r"])

            if data["export_carton_crm_h"] != "":
                product.export_carton_crm_h = float(
                    data["export_carton_crm_h"])

            if data["product_dimension_l"] != "":
                product.product_dimension_l = float(
                    data["product_dimension_l"])

            if data["product_dimension_r"] != "":
                product.product_dimension_r = float(
                    data["product_dimension_r"])

            if data["product_dimension_h"] != "":
                product.product_dimension_h = float(
                    data["product_dimension_h"])

            if data["giftbox_l"] != "":
                product.gift_box_l = float(data["giftbox_l"])

            if data["giftbox_r"] != "":
                product.gift_box_r = float(data["giftbox_r"])

            if data["giftbox_h"] != "":
                product.gift_box_h = float(data["giftbox_h"])

            product.size = data["size"]
            sourcing_user_product.weight = data["weight"]
            sourcing_user_product.design = data["design"]
            sourcing_user_product.pkg_inner = data["pkg_inner"]
            sourcing_user_product.pkg_m_ctn = data["pkg_m_ctn"]
            sourcing_user_product.p_ctn_cbm = data["p_ctn_cbm"]
            sourcing_user_product.ttl_ctn = data["ttl_ctn"]
            sourcing_user_product.ttl_cbm = data["ttl_cbm"]
            sourcing_user_product.ship_lot_number = data["ship_lot_number"]

            product.save()
            sourcing_user_product.save()

            if (product.minimum_order_qty != None and product.minimum_order_qty != '' and
                product.order_qty != None and product.order_qty != '' and
                product.spare_part_name != None and product.spare_part_name != '' and
                product.spare_part_qty != None and product.spare_part_qty != '' and
                product.export_carton_qty_l != None and product.export_carton_qty_l != '' and
                product.export_carton_qty_r != None and product.export_carton_qty_r != '' and
                product.export_carton_qty_h != None and product.export_carton_qty_h != '' and

                product.gift_box_l != None and product.gift_box_l != '' and
                product.gift_box_r != None and product.gift_box_r != '' and
                product.gift_box_h != None and product.gift_box_h != '' and


                sourcing_user_product.name != None and sourcing_user_product.name != '' and
                sourcing_user_product.price != None and sourcing_user_product.price != '' and
                sourcing_user_product.currency != None and sourcing_user_product.currency != ''):

                product.is_pr_ready = True
                print("The product is pr ready")

            else:
                product.is_pr_ready = False
                product.go_live = False
                print("pr ready is setting False")

            product.save()
            if product.is_pr_ready == False:
                product.go_live = False
                print("go libve is set flase")

            product.save()

            response["status"] = 200
            response["flag"] = product.is_pr_ready

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveFactoryProductDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        print("coming from here")
        return Response(data=response)


class SaveSourcingFactoryDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):
        print("SaveSourcingProductDetailsAPI")
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info(
                "class SaveSourcingFactoryDetailsAPI(APIView):: % s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            sourcing_user_factory = SourcingUserFactory.objects.get(pk = int(data["pk"]))
            factory = sourcing_user_factory.base_factory

            sourcing_user_factory.name = data["factory_name"]

            if data["factory_address"] != '':
                factory.address = data["factory_address"]
            
            if data["factory_emailid"] != '':
                factory.factory_emailid = data["factory_emailid"]

            if data["loading_port"] != '':
                factory.loading_port = data["loading_port"]

            if data["location"] != '':
                factory.location = data["location"]

            if data["notes"] != '':
                factory.notes = data["notes"]

            if data["contact_person_name"] != '':
                factory.contact_person_name = data["contact_person_name"]

            if data["contact_person_mobile_number"] != '':
                factory.contact_person_mobile_no = data["contact_person_mobile_number"]

            if data["contact_person_emailid"] != '':
                factory.contact_person_emailid = data["contact_person_emailid"]

            if data["tag"] != '':
                factory.social_media_tag = data["tag"]

            if data["tag_info"] != '':
                factory.social_media_tag_information = data["tag_info"]

            sourcing_user_factory.other_info = data["notes"]
            sourcing_user_factory.save()
           
            if factory.bank_details == None:

                temp_bank , created = Bank.objects.get_or_create(ifsc_code=data["bank_ifsc_code"])
                if created == False:
                    temp_bank.name = data["bank_name"]
                    temp_bank.address= data["bank_address"]
                    temp_bank.account_number=data["bank_account_number"]
                    temp_bank.swift_code=data["bank_swift_code"]
                    temp_bank.branch_code=data["bank_branch_code"] 
                    temp_bank.save()

                factory.bank_details = temp_bank
            else:
                temp_bank = factory.bank_details
                if data["bank_name"] != '':
                    temp_bank.name = data["bank_name"]


                if data["bank_address"] != '':
                    temp_bank.address = data["bank_address"]

                if data["bank_account_number"] != '':
                    temp_bank.account_number = data["bank_account_number"]

                if data["bank_ifsc_code"] != '':
                    temp_bank.ifsc_code = data["bank_ifsc_code"]

                if data["bank_swift_code"] != '':
                    temp_bank.swift_code = data["bank_swift_code"]

                if data["bank_branch_code"] != '':
                    temp_bank.branch_code = data["bank_branch_code"]
                temp_bank.save()
            phone_numbers = []
            if len(data["phone_numbers"]) > 0:
                phone_numbers = json.loads(data["phone_numbers"])
            phone_numbers_old = factory.phone_numbers.all()
            for phone in phone_numbers_old:
                phone.delete()

            for phone_number in str(phone_numbers).split(", "):
                phone_number_obj = PhoneNumber.objects.create(
                    number=phone_number)
                factory.phone_numbers.add(phone_number_obj)
                factory.save()

            factory.save()
            sourcing_user_factory.save()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveSourcingFactoryDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))
        print("coming from here")
        return Response(data=response)


class FetchSourcingProductDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):
        print("FetchSourcingProductDetailsAPI")
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchSourcingProductDetailsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product = Product.objects.get(pk=int(data["pk"]))
            sourcing_user_product = SourcingUserProduct.objects.get(
                base_product=product)

            response["product-name"] = sourcing_user_product.name
            response["price"] = sourcing_user_product.price
            response["product-code"] = sourcing_user_product.code
            response["minimum-order-qty"] = product.minimum_order_qty
            response["order-qty"] = product.order_qty
            response["other-info"] = sourcing_user_product.other_info
            response["qty-metric"] = product.qty_metric
            response["currency"] = sourcing_user_product.currency
            response["inner-box-qty"] = product.inner_box_qty
            if(product.country != None):
                response["country"] = product.country.pk
            else:
                response["country"] = ""
            if(product.category != None):
                response["category"] = product.category.pk
            else:
                response["category"] = ""
            if(product.technical_specs != None):
                response["technical-specs"] = product.technical_specs.pk
            else:
                response["technical-specs"] = ""
            if(product.material_specs != None):
                response["material-specs"] = product.material_specs.pk
            else:
                response["material-specs"] = ""
            response["spare-part-name"] = product.spare_part_name
            response["spare-part-qty"] = product.spare_part_qty
            response["delivery-days"] = product.delivery_days
            response["export-carton-qty-l"] = product.export_carton_qty_l
            response["export-carton-qty-r"] = product.export_carton_qty_r
            response["export-carton-qty-h"] = product.export_carton_qty_h
            response["export-carton-crm-l"] = product.export_carton_crm_l
            response["export-carton-crm-r"] = product.export_carton_crm_r
            response["export-carton-crm-h"] = product.export_carton_crm_h
            response["product-dimension-l"] = product.product_dimension_l
            response["product-dimension-r"] = product.product_dimension_r
            response["product-dimension-h"] = product.product_dimension_h
            response["giftbox-l"] = product.gift_box_l
            response["giftbox-r"] = product.gift_box_r
            response["giftbox-h"] = product.gift_box_h
            response["go-live-status"] = product.go_live
            
            response["size"] = product.size

            response["weight"] = sourcing_user_product.weight
            response["design"] = sourcing_user_product.design
            response["pkg-inner"] = sourcing_user_product.pkg_inner
            response["pkg-m-ctn"] = sourcing_user_product.pkg_m_ctn
            response["p-ctn-cbm"] = sourcing_user_product.p_ctn_cbm
            response["ttl-ctn"] = sourcing_user_product.ttl_ctn
            response["ttl-cbm"] = sourcing_user_product.ttl_cbm
            response["ship-lot-number"] = sourcing_user_product.ship_lot_number

            response["created-date"] = ""
            if product.created_date!=None:
                response["created-date"] = str(product.created_date.strftime("%Y-%m-%d"))

            images = sourcing_user_product.images.all()
            images_list = []

            if(len(images) == 0):
                temp_dict = {}
                temp_dict["url"] = Config.objects.all()[0].DEFAULT_IMAGE.url
                temp_dict["pk"] = None
                images_list.append(temp_dict)

            for image in images:
                temp_dict = {}
                temp_dict["url"] = image.image.url
                temp_dict["pk"] = image.pk
                images_list.append(temp_dict)

            response["images_list"] = images_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchSourcingProductDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveFactoryProductDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SaveFactoryProductDetailsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product = Product.objects.get(pk=int(data["pk"]))
            
            factory_manager_product = FactoryManagerProduct.objects.get(base_product=product)

            factory_manager_product.name = data["product_name"]
            
            if data["product_price"]!="":
                factory_manager_product.price = float(data["product_price"])
            
            factory_manager_product.code = data["product_code"]
            
            if data["minimum_order_qty"]!="":
                product.minimum_order_qty = int(data["minimum_order_qty"])
            
            if data["order_qty"]!="":
                product.order_qty = int(data["order_qty"])
            
            product.qty_metric = data["qty_metric"]
            factory_manager_product.currency = data["currency"]
            
            if data["inner_box_qty"]!="":
                product.inner_box_qty = int(data["inner_box_qty"])
            
            if data["country"]!="":
                country = Country.objects.get(pk=int(data["country"]))
                product.country = country
            
            if data["technical_specs"]!="":
                technical_specs = TechnicalSpecs.objects.get(pk=int(data["technical_specs"]))
                product.technical_specs = technical_specs

            product.spare_part_name = data["spare_part_name"]
            
            if data["spare_part_qty"]!="":
                product.spare_part_qty = int(data["spare_part_qty"])

            if data["category"]!="":
                category = Category.objects.get(pk=int(data["category"]))            
                product.category = category

            if data["delivery_days"]!="":
                product.delivery_days = int(data["delivery_days"])

            if data["material_specs"]!="":
                material_specs = MaterialSpecs.objects.get(pk=int(data["material_specs"]))
                product.material_specs = material_specs

            if data["export_carton_qty_l"]!="":
                product.export_carton_qty_l = float(data["export_carton_qty_l"])

            if data["export_carton_qty_r"]!="":
                product.export_carton_qty_r = float(data["export_carton_qty_r"])

            if data["export_carton_qty_h"]!="":

                product.export_carton_qty_h = float(data["export_carton_qty_h"])

            if data["export_carton_crm_l"]!="":
                product.export_carton_crm_l = float(data["export_carton_crm_l"])

            if data["export_carton_crm_r"]!="":
                product.export_carton_crm_r = float(data["export_carton_crm_r"])

            if data["export_carton_crm_h"]!="":
                product.export_carton_crm_h = float(data["export_carton_crm_h"])

            if data["product_dimension_l"]!="":
                product.product_dimension_l = float(data["product_dimension_l"])

            if data["product_dimension_r"]!="":
                product.product_dimension_r = float(data["product_dimension_r"])

            if data["product_dimension_h"]!="":
                product.product_dimension_h = float(data["product_dimension_h"])

            if data["giftbox_l"]!="":
                product.gift_box_l = float(data["giftbox_l"])

            if data["giftbox_r"]!="":
                product.gift_box_r = float(data["giftbox_r"])

            if data["giftbox_h"]!="":
                product.gift_box_h = float(data["giftbox_h"])

            product.save()
            factory_manager_product.save()

            if (product.minimum_order_qty != None and product.minimum_order_qty != '' and 
                product.order_qty != None and product.order_qty != '' and 
                product.spare_part_name != None and product.spare_part_name != '' and 
                product.spare_part_qty != None and product.spare_part_qty != '' and
                product.export_carton_qty_l != None and product.export_carton_qty_l != '' and
                product.export_carton_qty_r != None and product.export_carton_qty_r != '' and
                product.export_carton_qty_h != None and product.export_carton_qty_h != '' and

                product.gift_box_l != None and product.gift_box_l != '' and
                product.gift_box_r != None and product.gift_box_r != '' and
                product.gift_box_h != None and product.gift_box_h != '' and


                factory_manager_product.name != None and factory_manager_product.name != '' and 
                factory_manager_product.price != None and factory_manager_product.price != '' and
                factory_manager_product.currency != None and factory_manager_product.currency != ''):
                
                product.is_pr_ready = True

            else:
                product.is_pr_ready = False
                product.go_live = False
                print("pr ready is setting False")

            product.save()
            if product.is_pr_ready == False:
                product.go_live = False
            
            product.save()

            response["status"] = 200
            response["flag"] = product.is_pr_ready

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveFactoryProductDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))
    
        return Response(data=response)


class FetchFactoryProductDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchFactoryProductDetailsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product = Product.objects.get(pk=int(data["pk"]))
            factory_manager_product = FactoryManagerProduct.objects.get(base_product=product)

            response["product-name"] = factory_manager_product.name 
            response["price"] = factory_manager_product.price 
            response["product-code"] = factory_manager_product.code 
            response["minimum-order-qty"] = product.minimum_order_qty 
            response["order-qty"] = product.order_qty  
            response["other-info"] = factory_manager_product.other_info
            response["qty-metric"] = product.qty_metric 
            response["currency"] = factory_manager_product.currency 
            response["inner-box-qty"] = product.inner_box_qty 
            if(product.country != None):
                response["country"] = product.country.pk
            else:
                response["country"] = ""
            if(product.category != None):
                response["category"] = product.category.pk
            else:
                response["category"] = ""
            if(product.technical_specs != None):
                response["technical-specs"] = product.technical_specs.pk
            else:
                response["technical-specs"] = ""
            if(product.material_specs != None):
                response["material-specs"] = product.material_specs.pk
            else:
                response["material-specs"] = ""
            response["spare-part-name"] = product.spare_part_name 
            response["spare-part-qty"] = product.spare_part_qty
            response["delivery-days"] = product.delivery_days
            response["export-carton-qty-l"] = product.export_carton_qty_l 
            response["export-carton-qty-r"] = product.export_carton_qty_r               
            response["export-carton-qty-h"] = product.export_carton_qty_h 
            response["export-carton-crm-l"] = product.export_carton_crm_l 
            response["export-carton-crm-r"] = product.export_carton_crm_r
            response["export-carton-crm-h"] = product.export_carton_crm_h 
            response["product-dimension-l"] = product.product_dimension_l 
            response["product-dimension-r"] = product.product_dimension_r
            response["product-dimension-h"] = product.product_dimension_h
            response["giftbox-l"] = product.gift_box_l 
            response["giftbox-r"] = product.gift_box_r
            response["giftbox-h"] = product.gift_box_h
            response["go-live-status"] = product.go_live

            response["created-date"] = ''
            if product.created_date!=None:
                response["created-date"] = str(product.created_date.strftime("%Y-%m-%d"))


            images = factory_manager_product.images.all()
            images_list = []

            if(len(images)==0):
                temp_dict = {}
                temp_dict["url"] = Config.objects.all()[0].DEFAULT_IMAGE.url
                temp_dict["pk"] = None
                images_list.append(temp_dict)

            for image in images:
                temp_dict = {}
                temp_dict["url"] = image.image.url
                temp_dict["pk"] = image.pk
                images_list.append(temp_dict)

            response["images_list"] = images_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFactoryProductDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchFactorywiseProductListingAPI(APIView):

    def post(self, request, *args, **kwargs):

        print("Fetching factorywise products..")
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchFactorywiseProductListingAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            response_products = []
            sourcing_user_factory = SourcingUserFactory.objects.get(pk=int(data["pk"]))
            
            chip_data = json.loads(data['tags'])

            products_list = []
            products = sourcing_user_factory.products.all()
            for product in products:
                if len(chip_data)>0:
                    for tag in chip_data:
                        sourcing_user_products = SourcingUserProduct.objects.filter(
                    name__icontains=tag,base_product=product)
                        for sourcing_user_product in sourcing_user_products:
                            products_list.append(sourcing_user_product)
                else:
                    products_list.append(SourcingUserProduct.objects.get(base_product = product))
            print(products_list)
            products = products_list
            response["factory_name"] = sourcing_user_factory.name
            response["factory_address"] = sourcing_user_factory.base_factory.address
            response["factory_image"] = Config.objects.all()[
                0].DEFAULT_IMAGE.url
            response["factory_background_poster"] = Config.objects.all()[
                0].DEFAULT_IMAGE.url
            if sourcing_user_factory.images.all().count() > 0:
                response["factory_image"] = sourcing_user_factory.images.all()[
                    0].image.url
            if sourcing_user_factory.background_poster:
                response["factory_background_poster"] = sourcing_user_factory.background_poster.image.url
            try:
                for product in products:
                    sourcing_user_product = product
                    temp_dict = {}
                    temp_dict["pk"] = product.base_product.pk
                    temp_dict["name"] = sourcing_user_product.name
                    
                    temp_dict["moq"] = product.base_product.minimum_order_qty 
                    temp_dict["delivery_days"] = product.base_product.delivery_days
                    temp_dict["price"] = sourcing_user_product.price
                    temp_dict["go-live-status"] = product.base_product.go_live
                    temp_dict["factory_name"] = sourcing_user_factory.name


                    if sourcing_user_product.images.all().count()>0:
                        temp_dict["image-url"] = sourcing_user_product.images.all()[0].image.url
                    else :
                        temp_dict["image-url"] = Config.objects.all()[0].DEFAULT_IMAGE.url


                    response_products.append(temp_dict)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("FetchFactorywiseProductListingAPI: %s at %s", e, str(exc_tb.tb_lineno))
            print(response_products)
            response["products"] = response_products
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFactorywiseProductListingAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveFactoryManagerFactoryDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SaveFactoryManagerFactoryDetailsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            factory = Factory.objects.get(pk=int(data["pk"]))
            factory.name = data["name"]
            factory.address = data["address"]
            factory.factory_emailid = data["factory_emailid"]
            factory.contact_person_name = data["contact_person_name"]
            factory.contact_person_mobile_no = data["contact_person_mobile_no"]
            factory.contact_person_emailid = data["contact_person_emailid"]
            factory.social_media_tag = data["social_media_tag"]
            factory.social_media_tag_information = data["social_media_tag_information"]
            factory.loading_port = data["loading_port"]
            factory.location = data["location"]
            factory.other_info = data["other_info"]
            factory.save()
            
            phone_numbers = json.loads(data["phone_numbers"])
            phone_numbers_old = factory.phone_numbers.all()
            for phone in phone_numbers_old:
                phone.delete()

            for phone_number in phone_numbers:
                phone_number_obj = PhoneNumber.objects.create(number=phone_number)
                factory.phone_numbers.add(phone_number_obj)
                factory.save()

            response["name"] = sourcing_user_factory.name
            response["address"] = factory.address
            response["phone_numbers"] = phone_numbers
            response["factory_emailid"] = factory.factory_emailid
            response["contact_person_name"] = factory.contact_person_name 
            response["contact_person_mobile_no"] = factory.contact_person_mobile_no
            response["contact_person_emailid"] = factory.contact_person_emailid 
            response["social_media_tag"] = factory.social_media_tag
            response["social_media_tag_information"] = factory.social_media_tag_information
            response["loading_port"] = factory.loading_port 
            response["location"] = factory.location
            response["other_info"] = factory.other_info  

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveFactoryDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class UploadFactoryProductImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UploadFactoryProductImageAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product = Product.objects.get(pk=int(data["pk"]))
            factory_manager_product = FactoryManagerProduct.objects.get(base_product=product)

            images_count = int(data["images_count"])

            images_list = []
            for i in range(images_count):
                im_obj = Image.objects.create(image=data["product-image-"+str(i)])
                factory_manager_product.images.add(im_obj)

            factory_manager_product.save()

            images = factory_manager_product.images.all()
            
            images_list = []
            for image in images:
                temp_dict = {}
                temp_dict["url"] = image.image.url
                temp_dict["pk"] = image.pk
                images_list.append(temp_dict)

            response["images_list"] = images_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadFactoryProductImageAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadFactoryImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UploadFactoryImageAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            sourcing_user_factory = SourcingUserFactory.objects.get(pk = int(data["pk"]))
            images_count = int(data["images_count"])

            images_list = []
            for i in range(images_count):
                im_obj = Image.objects.create(
                    image=data["product-image-"+str(i)])
                sourcing_user_factory.images.add(im_obj)

            sourcing_user_factory.save()

            images = sourcing_user_factory.images.all()

            images_list = []
            for image in images:
                temp_dict = {}
                temp_dict["url"] = image.image.url
                temp_dict["pk"] = image.pk
                images_list.append(temp_dict)

            response["images_list"] = images_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadFactoryImageAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadSourcingProductProductImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UploadSourcingProductProductImageAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product = Product.objects.get(pk=int(data["pk"]))
            sourcing_user_product = SourcingUserProduct.objects.get(
                base_product=product)

            images_count = int(data["images_count"])

            images_list = []
            for i in range(images_count):
                im_obj = Image.objects.create(
                    image=data["product-image-"+str(i)])
                sourcing_user_product.images.add(im_obj)

            sourcing_user_product.save()

            images = sourcing_user_product.images.all()

            images_list = []
            for image in images:
                temp_dict = {}
                temp_dict["url"] = image.image.url
                temp_dict["pk"] = image.pk
                images_list.append(temp_dict)

            response["images_list"] = images_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadFactoryProductImageAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class ChangeGoLiveStatusAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        response['error_msg'] = ''
        try:
            data = request.data
            logger.info("ChangeGoLiveStatusAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product = Product.objects.get(pk=int(data["pk"]))
            temp = product.go_live
            if temp == False and product.is_pr_ready == True:
                product.go_live = True
            else:
                product.go_live = False
                response['error_msg'] = 'not_pr_ready'
            product.save()
            response["go-live-status"] = product.go_live
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ChangeGoLiveStatusAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DownloadPIAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        response['error_msg'] = 'Either no products are PR ready or the factory does not exist.'
        try:

            data = request.data
            logger.info("DownloadPIAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            pk = int(data['pk'])

            selected_products_dict = {}
            total_quantity = 0
            selected_products = data['selected_products']
            selected_products = json.loads(selected_products)
            for k in selected_products:
                selected_products_dict[k["pk"]] = k["quantity"]
                total_quantity += int(k["quantity"])

            temp_proforma_invoice=''
            
            type_of_payment = data.get("type_of_payment","")
            percentage_of_payment = data.get("percentage_of_payment","")
            delivery_days = data.get("delivery_days","")
            delivery_terms = data.get("delivery_terms", "")
            inco_terms= data.get("inco_terms", "")
            ttl_cntrs = data.get("ttl_cntrs", "")
            important_points = data.get("important_points", '')
            special_instructions = data.get("special_instructions",'')

            delivery_terms = str(delivery_days) +  " DAYS " + str(delivery_terms)
            selected_prod_obj = []
            
            for k in selected_products:
                temp_obj = SourcingUserProduct.objects.get(pk = int(k["pk"]))
                selected_prod_obj.append(temp_obj)
            
            if percentage_of_payment:
                pass
            else:
                percentage_of_payment = ''
            temp_proforma_invoice = ProformaInvoice.objects.create(
                payment_terms=type_of_payment, 
                advance=percentage_of_payment,
                inco_terms=inco_terms,
                ttl_cntrs=ttl_cntrs,
                delivery_terms=delivery_terms
            )

            temp_proforma_invoice.products.add(*selected_prod_obj)
            temp_proforma_invoice.save()

            try:
                sourcing_user_factory = SourcingUserFactory.objects.get(pk = pk)
                base_factory = sourcing_user_factory.base_factory
                temp_proforma_invoice.factory = sourcing_user_factory
                temp_proforma_invoice.save()
                
                if sourcing_user_factory.products > 0:

                    base_factory = sourcing_user_factory.base_factory

                    json_parameter = {}
                    json_parameter["factory_name"] = str(sourcing_user_factory.name)
                    json_parameter["factory_address"] = str(base_factory.address)
                    json_parameter["loading_port"] = str(base_factory.loading_port)
                    try:
                        json_parameter["bank_name"] = str(base_factory.bank_details.name)
                        json_parameter["bank_address"] = str(base_factory.bank_details.address)
                        json_parameter["bank_account_number"] = str(base_factory.bank_details.account_number)
                        json_parameter["bank_ifsc_code"] = str(base_factory.bank_details.ifsc_code)
                        json_parameter["bank_swift_code"] = str(base_factory.bank_details.swift_code)
                        json_parameter["bank_branch_code"] = str(base_factory.bank_details.branch_code)
                    except Exception as e:
                        json_parameter["bank_name"] = ""
                        json_parameter["bank_address"] = ""
                        json_parameter["bank_account_number"] = ""
                        json_parameter["bank_ifsc_code"] = ""
                        json_parameter["bank_swift_code"] = ""
                        json_parameter["bank_branch_code"] = ""
                            
                    json_parameter["payment_terms"] = str(temp_proforma_invoice.payment_terms) 
                    json_parameter["advance_payment"] = str(temp_proforma_invoice.advance)
                    json_parameter["inco_terms"] = str(temp_proforma_invoice.inco_terms)
                    json_parameter["delivery_terms"] = str(temp_proforma_invoice.delivery_terms)
                    json_parameter["special_instructions"] = str(special_instructions)
                    json_parameter["important_points"] = str(important_points)

                    selected_products_pk = []
                    for k in selected_products:
                        selected_products_pk.append(k["pk"])

                    sourcing_user_products = sourcing_user_factory.products.filter(pk__in=selected_products_pk)

                    product_info = []
                    logger.info("selected_products_dict %s", str(selected_products_dict))
                    for sourcing_user_product in sourcing_user_products:
                        
                        product = SourcingUserProduct.objects.get(base_product=sourcing_user_product)
                        base_product = sourcing_user_product

                        logger.info("product_pk %s", str(product.pk))
                        logger.info("base_product_pk %s", str(base_product.pk))

                        temp_dict = {} 
                        temp_dict["image_url"] = ""
                        if product.images.count()>0:
                            temp_dict["image_url"] = "file:///"+BASE_DIR + product.images.all()[0].image.url
                        temp_dict["code"] = str(product.code)
                        temp_dict["brand_category"] = str(base_product.brand_category)
                        temp_dict["other_info"] = str(product.other_info)
                        temp_dict["size"] = str(base_product.size)
                        temp_dict["weight"] = str(product.weight)
                        temp_dict["design"] = str(product.design)
                        temp_dict["colors"] = " ".join([i.name for i in base_product.color_group.all()])
                        temp_dict["pkg_inner"] = str(product.pkg_inner)
                        temp_dict["pkg_m_ctn"] = str(product.pkg_m_ctn)
                        temp_dict["p_ctn_cbm"] = str(product.p_ctn_cbm)
                        temp_dict["ttl_ctn"] = str(product.ttl_ctn)
                        temp_dict["ttl_cbm"] = str(product.ttl_cbm)
                        temp_dict["ship_lot_number"] = str(product.ship_lot_number)
                        temp_dict["order_quantity"] = selected_products_dict[str(product.pk)]
                        temp_dict["qty_metric"] = str(base_product.qty_metric)
                        temp_dict["price"] = str(product.price)
                        product_info.append(temp_dict)

                    json_parameter["product_info"] = product_info

                    filename = sourcing_user_factory.name.replace(" ", "-").replace(",", "").replace("&", "")+"_"+str(temp_proforma_invoice.pk)+".pdf"
                    filepath = generate_pi(json_parameter, filename)
                    logger.info("filepath returned %s", str(filepath))
                    temp_proforma_invoice.proforma_pdf = "pdf/"+filename
                    temp_proforma_invoice.save()

                    response['pdf_file'] = filepath
                    response['status'] = 200
                    response['error_msg'] = ''

            except Exception  as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("DownloadPIAPI: %s at %s", e, str(exc_tb.tb_lineno))
                response["error_msg"] = "Either no products are PR ready or the factory does not exist."
                print(e)
                print("error issss")

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DownloadPIAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DownloadPIBulkAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        response['error_msg'] = 'Either no products are PR ready or the factory does not exist.'
        try:

            data = request.data
            logger.info("DownloadPIAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            pk_draft_pi = int(data['pk_draft_pi'])

            selected_products = []
            selected_products_dict = {}
            total_quantity = 0
            selected_products = data['selected_products']
            selected_products = json.loads(selected_products)
            for k in selected_products:
                selected_products_dict[k["pk"]] = k["quantity"]
                total_quantity += int(k["quantity"])

            type_of_payment = data["type_of_payment"]
            percentage_of_payment = data["percentage_of_payment"]
            delivery_days = data["delivery_days"]
            delivery_terms = data["delivery_terms"]
            inco_terms= data["inco_terms"]
            ttl_cntrs = data["ttl_cntrs"]
            important_points = data.get("important_points", '')
            special_instructions = data.get("special_instructions",'')

            delivery_terms = str(delivery_days) +  " DAYS " + str(delivery_terms)
            selected_prod_obj = []

            draft_pi_object = DraftProformaInvoice.objects.get(pk = pk_draft_pi)

            temp_lines = str(draft_pi_object.lines)
            temp_lines = temp_lines.replace("L", "")

            draft_pi_lines = json.loads(str(temp_lines))
            
            draft_pi_lines_list = []
            for draft_pi_line in draft_pi_lines:
                draft_pi_line_obj = DraftProformaInvoiceLine.objects.get(pk = draft_pi_line)
                draft_pi_lines_list.append(draft_pi_line_obj)

            draft_pi_lines_dict = defaultdict(list)
            for draft_pi_line in draft_pi_lines_list:
                if draft_pi_line.sourcing_user_factory.pk in draft_pi_lines_dict.keys():
                    draft_pi_lines_dict[draft_pi_line.sourcing_user_factory.pk].append(draft_pi_line)
                else:
                    draft_pi_lines_dict[draft_pi_line.sourcing_user_factory.pk] = [draft_pi_line]

            
            if percentage_of_payment:
                pass
            else:
                percentage_of_payment = ''
            
            temp_proforma_invoice_ids = []
            for factory_pk in draft_pi_lines_dict:
                temp_proforma_invoice = ''
                temp_selected_products = []
                for x in draft_pi_lines_dict[factory_pk]:
                    temp_selected_products.append(x.sourcing_user_product.pk)
                for k in temp_selected_products:
                    temp_obj = SourcingUserProduct.objects.get(pk = int(k))
                    selected_prod_obj.append(temp_obj)
            
                temp_proforma_invoice = ProformaInvoice.objects.create(
                    payment_terms=type_of_payment, 
                    advance=percentage_of_payment,
                    inco_terms=inco_terms,
                    ttl_cntrs=ttl_cntrs,
                    delivery_terms=delivery_terms
                )
                temp_proforma_invoice.save()
                temp_proforma_invoice.products.add(*selected_prod_obj)
           

                try:
                    sourcing_user_factory = SourcingUserFactory.objects.get(pk=factory_pk)
                    base_factory = sourcing_user_factory.base_factory
                    temp_proforma_invoice.factory = sourcing_user_factory
                    temp_proforma_invoice.save()
                    
                    factory_manager_factory = None
                    
                    if sourcing_user_factory.products > 0:

                        base_factory = sourcing_user_factory.base_factory

                        json_parameter = {}
                        json_parameter["factory_name"] = str(sourcing_user_factory.name)
                        json_parameter["factory_address"] = str(base_factory.address)
                        json_parameter["loading_port"] = str(base_factory.loading_port)
                        try:
                            json_parameter["bank_name"] = str(base_factory.bank_details.name)
                            json_parameter["bank_address"] = str(base_factory.bank_details.address)
                            json_parameter["bank_account_number"] = str(base_factory.bank_details.account_number)
                            json_parameter["bank_ifsc_code"] = str(base_factory.bank_details.ifsc_code)
                            json_parameter["bank_swift_code"] = str(base_factory.bank_details.swift_code)
                            json_parameter["bank_branch_code"] = str(base_factory.bank_details.branch_code)
                        except Exception as e:
                            json_parameter["bank_name"] = ""
                            json_parameter["bank_address"] = ""
                            json_parameter["bank_account_number"] = ""
                            json_parameter["bank_ifsc_code"] = ""
                            json_parameter["bank_swift_code"] = ""
                            json_parameter["bank_branch_code"] = ""

                        json_parameter["payment_terms"] = str(temp_proforma_invoice.payment_terms) 
                        json_parameter["advance_payment"] = str(temp_proforma_invoice.advance)
                        json_parameter["inco_terms"] = str(temp_proforma_invoice.inco_terms)
                        json_parameter["delivery_terms"] = str(temp_proforma_invoice.delivery_terms)
                        json_parameter["special_instructions"] = str(special_instructions)
                        json_parameter["important_points"] = str(important_points)

                        selected_products_pk = []
                        for k in selected_products:
                            selected_products_pk.append(k["pk"])

                        sourcing_user_products = sourcing_user_factory.products.filter(pk__in=selected_products_pk)

                        product_info = []
                        for sourcing_user_product in sourcing_user_products:
                            
                            product = SourcingUserProduct.objects.get(base_product=sourcing_user_product)
                            base_product = sourcing_user_product
                            temp_dict = {} 
                            temp_dict["image_url"] = ""
                            if product.images.count()>0:
                                temp_dict["image_url"] = "file:///"+BASE_DIR + product.images.all()[0].image.url
                            temp_dict["code"] = str(product.code)
                            temp_dict["brand_category"] = str(base_product.brand_category)
                            temp_dict["other_info"] = str(product.other_info)
                            temp_dict["size"] = str(base_product.size)
                            temp_dict["weight"] = str(product.weight)
                            temp_dict["design"] = str(product.design)
                            temp_dict["colors"] = " ".join([i.name for i in base_product.color_group.all()])
                            temp_dict["pkg_inner"] = str(product.pkg_inner)
                            temp_dict["pkg_m_ctn"] = str(product.pkg_m_ctn)
                            temp_dict["p_ctn_cbm"] = str(product.p_ctn_cbm)
                            temp_dict["ttl_ctn"] = str(product.ttl_ctn)
                            temp_dict["ttl_cbm"] = str(product.ttl_cbm)
                            temp_dict["ship_lot_number"] = str(product.ship_lot_number)
                            temp_dict["order_quantity"] = str(selected_products_dict[str(product.pk)])
                            temp_dict["qty_metric"] = str(base_product.qty_metric)
                            temp_dict["price"] = str(product.price)
                            product_info.append(temp_dict)

                        json_parameter["product_info"] = product_info

                        filename = sourcing_user_factory.name.replace(" ", "-").replace(",", "").replace("&", "")+"_"+str(temp_proforma_invoice.pk)+".pdf"
                        filepath = generate_pi(json_parameter, filename)
                        logger.info("filepath returned %s", str(filepath))
                        temp_proforma_invoice.proforma_pdf = "pdf/"+filename
                        temp_proforma_invoice.save()
                        temp_proforma_invoice_ids.append(temp_proforma_invoice.pk)

                    zf = zipfile.ZipFile("files/proforma_invoice.zip", "w")
                    for x in temp_proforma_invoice_ids:
                        tpi = ProformaInvoice.objects.get(pk = x)
                        logger.info("proforma_pdf_url tpi %s", str(tpi.proforma_pdf.url[1:]))
                        zf.write(tpi.proforma_pdf.url[1:])
                    zf.close()
                    resp_filepath = '/'+zf.filename
                    logger.info("resp_filepath %s: ", str(resp_filepath))
                    response['pdf_file'] = resp_filepath
                    response['status'] = 200
                    response['error_msg'] = ''

                except Exception  as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("DownloadPIBulkAPI: %s at %s", e, str(exc_tb.tb_lineno))
                    response["error_msg"] = "Either no products are PR ready or the factory does not exist."

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DownloadPIBulkAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


#GeneratePIInBulkAPI
class GenerateDraftPILineAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        response['error_msg'] = 'There seems to be an error in the uploaded file.'
        # response['list_of_draft_lines'] = []
        list_of_draft_lines = []
        response["draft_pi"] = ''
        try:

            data = request.data
            logger.info("DownloadPIAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            wb = xlrd.open_workbook(file_contents=data["uploadedFile"].read())
            product_sheet = wb.sheet_by_index(0)
            temp_draft_pi_invoice = DraftProformaInvoice.objects.create(
                lines=list_of_draft_lines)
                
            for row_number in range(1,product_sheet.nrows):
                temp_sourcing_user_product = SourcingUserProduct.objects.get(
                    code=product_sheet.cell_value(row_number, 1))

                temp_sourcing_user_factory = SourcingUserFactory.objects.filter(products = temp_sourcing_user_product.base_product)[0]

                temp_draft_PI_line = DraftProformaInvoiceLine.objects.create(
                    sourcing_user_product = temp_sourcing_user_product,
                    sourcing_user_factory = temp_sourcing_user_factory,
                    quantity = product_sheet.cell_value(row_number, 2),
                    draft_proforma_invoice=temp_draft_pi_invoice)
                list_of_draft_lines.append(int(temp_draft_PI_line.pk))
            temp_draft_pi_invoice.lines = str(list_of_draft_lines)
            temp_draft_pi_invoice.save()
            response["draft_pi_pk"] = str(temp_draft_pi_invoice.pk)
            response['status'] = 200
            response["error_msg"] = ''
                  
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("GenerateDraftPILineAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)



class FetchDraftProformaInvoiceAPI(APIView):

    """
        The API returns the draft PI lines and pk's
    """


    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        response['error_msg'] = 'There seems to be an error in the draft proformas.'
        # response['list_of_draft_lines'] = []
        list_of_draft_lines = []
        data = request.data
        logger.info("DownloadPIAPI: %s", str(data))
        if not isinstance(data, dict):
            data = json.loads(data)

        pk = int(data['pk'])
        try:
            draft_lines = []
            data = request.data
            logger.info("DownloadPIAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            draft_pi = DraftProformaInvoice.objects.get(pk = pk)
            temp_lines = str(draft_pi.lines)
            temp_lines = temp_lines.replace("L", "")
            logger.info("draft_pi_line : %s" , str(draft_pi.lines))
            draft_lines_id_list = json.loads(str(temp_lines))
            
            temp_dict={}
            for line_id in draft_lines_id_list:
                temp_dict = {}
                draft_line = DraftProformaInvoiceLine.objects.get(pk = line_id)
                sourcing_user_product = draft_line.sourcing_user_product
                sourcing_user_factory = draft_line.sourcing_user_factory
                temp_dict["quantity"] = draft_line.quantity
                temp_dict["sourcing_user_factory_name"] = sourcing_user_factory.name
                temp_dict["sourcing_user_factory_pk"] = sourcing_user_factory.pk
                temp_dict["sourcing_user_product_name"] = sourcing_user_product.name
                temp_dict["sourcing_user_product_pk"] = sourcing_user_product.pk 
                temp_dict["sourcing_user_product_code"] = sourcing_user_product.code
                temp_dict["price"] = sourcing_user_product.price
                temp_dict["moq"] = str(sourcing_user_product.base_product.minimum_order_qty)
                temp_dict["draft_line_id"] = line_id
                temp_dict["draft_pi_id"] = draft_pi.pk
                if sourcing_user_product.images.all().count()>0:
                    temp_dict["image-url"] = sourcing_user_product.images.all()[0].image.url
                else :
                    temp_dict["image-url"] = Config.objects.all()[0].DEFAULT_IMAGE.url

                draft_lines.append(temp_dict)

            # response["draft_pi_pk"] = str(temp_draft_pi_invoice.pk)
            response['status'] = 200
            response['draft_lines'] = draft_lines
            response["error_msg"] = ''
                  
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("GenerateDraftPILineAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DeleteDraftLineAPI(APIView):

    """
        The API deletes the draft lines in a PI. It is invoked after clicking
        the "Remove" button from the factorywise product listing for PI generation
    """

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        response['error_msg'] = 'There seems to be an error in deleting.'
        # response['list_of_draft_lines'] = []
        data = request.data
        logger.info("DeleteDraftLineAPI: %s", str(data))
        if not isinstance(data, dict):
            data = json.loads(data)

        try:
            draft_PI = DraftProformaInvoice.objects.get(
                pk=int(data["draft_pi_id"]))
            
            temp_lines = str(draft_PI.lines)
            temp_lines = temp_lines.replace("L", "")
            temp_lines = json.loads(temp_lines)
           
            temp_lines.remove(int(data["draft_line_id"]))
            draft_PI.lines = str(temp_lines)
            draft_PI.save()
            draft_line = DraftProformaInvoiceLine.objects.get(pk = int(data["draft_line_id"]))
            draft_line.delete()
           

            response['status'] = 200
            response['error_msg'] = ''
                  
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteDraftLineAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CreateDraftPIFromProductSelectionAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        response['error_msg'] = 'There seems to be an error in deleting.'
        # response['list_of_draft_lines'] = []
        data = request.data
        logger.info("CreateDraftPIFromProductSelectionAPI: %s", str(data))
        if not isinstance(data, dict):
            data = json.loads(data)
        data = json.loads(data['selected_products'])
        try:

            factorywise_products = defaultdict(list)
            for x in data:

                if x["factory_pk"] in factorywise_products.keys():
                    factorywise_products[x["factory_pk"]].append(x)
                else:
                    factorywise_products[x["factory_pk"]] = [x]
            
            draft_pi_line_list = []
            draft_proforma_invoice = DraftProformaInvoice.objects.create()
            for factory_pk in factorywise_products:
                temp_products = factorywise_products[factory_pk]
                for temp_product in temp_products:
                    sourcing_user_product = SourcingUserProduct.objects.get(pk = temp_product["product_pk"])
                    sourcing_user_factory = SourcingUserFactory.objects.get(pk = temp_product["factory_pk"])

                    draft_pi_line = DraftProformaInvoiceLine.objects.create(sourcing_user_product = sourcing_user_product,sourcing_user_factory = sourcing_user_factory, quantity = temp_product["quantity"],
                    draft_proforma_invoice = draft_proforma_invoice)

                    draft_pi_line_list.append(draft_pi_line.pk)
                

            draft_proforma_invoice.lines = str(draft_pi_line_list)
            draft_proforma_invoice.save()
            response['draft_pi_pk'] = draft_proforma_invoice.pk
            response['status'] = 200
            response['error_msg'] = ''
                  
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateDraftPIFromProductSelectionAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchProformaInvoiceListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        response['error_msg'] = 'There seems to be an error in fetching invoices.'
        # response['list_of_draft_lines'] = []
        # data = request.data
        # logger.info("FetchProformaInvoiceListAPI: %s", str(data))
        # if not isinstance(data, dict):
        #     data = json.loads(data)
        # data = json.loads(data['selected_products'])
        try:
            

            proforma_invoices = ProformaInvoice.objects.all()

            invoices = []
            for pi in proforma_invoices:
                temp_dict = {}
                proforma_invoice_pdf = ''
                if pi.proforma_pdf == None or pi.proforma_pdf == '':
                    proforma_invoice_pdf = ''
                else:
                    proforma_invoice_pdf = '/'+ str(pi.proforma_pdf.url[1:])
                temp_dict["pk"] = pi.pk
                temp_dict["factory"] = str(pi.factory)
                temp_dict["created_date"] = pi.created_date.strftime("%d %b, %Y, %H:%M")
                temp_dict["proforma_invoice_pdf"] = proforma_invoice_pdf
                temp_dict["proforma_product_count"] = pi.products.count()
                invoices.append(temp_dict)

            response['proforma_invoices'] = invoices
            response['status'] = 200
            response['error_msg'] = ''
                  
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProformaInvoiceListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)



class FetchDraftProformaInvoicesCartAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        response['error_msg'] = 'There seems to be an error in fetching invoices.'
        # response['list_of_draft_lines'] = []
        # data = request.data
        # logger.info("FetchProformaInvoiceListAPI: %s", str(data))
        # if not isinstance(data, dict):
        #     data = json.loads(data)
        # data = json.loads(data['selected_products'])
        try:

            draft_proforma_invoices = DraftProformaInvoice.objects.all()

            draft_pis = []
            for dpi in draft_proforma_invoices:
                temp_dict = {}
                
                temp_dict["pk"] = dpi.pk
                temp_dict["created_date"] = dpi.created_date.strftime(
                    "%d %b, %Y, %H:%M")
                temp_list = str(dpi.lines)
                temp_list = temp_list.replace("L", "")
                temp_list = json.loads(temp_list)

                temp_dict["factory_count"] = len(temp_list)
                
                draft_pis.append(temp_dict)

            response['draft_pis'] = draft_pis
            response['status'] = 200
            response['error_msg'] = ''

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchDraftProformaInvoicesCartAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)



UploadFactoryImage = UploadFactoryImageAPI.as_view()

FetchFactoryNameFromUUID = FetchFactoryNameFromUUIDAPI.as_view()

FetchFactoryForSourcingUser = FetchFactoryForSourcingUserAPI.as_view()

FetchFactoriesForSourcingUser = FetchFactoriesForSourcingUserAPI.as_view()

FetchSourcingUserDetails = FetchSourcingUserDetailsAPI.as_view()

FetchProductsFromFactory = FetchProductsFromFactoryAPI.as_view()

FetchSharedProductsForFactory = FetchSharedProductsForFactoryAPI.as_view()

FetchFactorywiseProductListing = FetchFactorywiseProductListingAPI.as_view()

SaveFactoryProductDetails = SaveFactoryProductDetailsAPI.as_view()

FetchFactoryProductDetails = FetchFactoryProductDetailsAPI.as_view()

SaveFactoryManagerFactoryDetails = SaveFactoryManagerFactoryDetailsAPI.as_view()

UploadFactoryProductImage = UploadFactoryProductImageAPI.as_view()

ChangeGoLiveStatus = ChangeGoLiveStatusAPI.as_view()

DownloadPI = DownloadPIAPI.as_view()

GenerateDraftPILine = GenerateDraftPILineAPI.as_view()

SaveSourcingProductDetails = SaveSourcingProductDetailsAPI.as_view()

SaveSourcingFactoryDetails = SaveSourcingFactoryDetailsAPI.as_view()

FetchSourcingProductDetails = FetchSourcingProductDetailsAPI.as_view()

UploadSourcingProductProductImage = UploadSourcingProductProductImageAPI.as_view()

FetchDraftProformaInvoice = FetchDraftProformaInvoiceAPI.as_view()

DeleteDraftLine = DeleteDraftLineAPI.as_view()

DownloadPIBulk = DownloadPIBulkAPI.as_view()

CreateDraftPIFromProductSelection = CreateDraftPIFromProductSelectionAPI.as_view()

FetchProformaInvoiceList = FetchProformaInvoiceListAPI.as_view()

FetchDraftProformaInvoicesCart =  FetchDraftProformaInvoicesCartAPI.as_view()

FetchFactories = FetchFactoriesAPI.as_view()

AddNewFactory = AddNewFactoryAPI.as_view()

FetchFactoryDetails = FetchFactoryDetailsAPI.as_view()

FetchConstants = FetchConstantsAPI.as_view()

AddNewProduct = AddNewProductAPI.as_view()

FetchProductDetails = FetchProductDetailsAPI.as_view()

SavePhoneNumbers = SavePhoneNumbersAPI.as_view()

SaveAddress = SaveAddressAPI.as_view()

SaveFactoryName = SaveFactoryNameAPI.as_view()

SaveProductDetails = SaveProductDetailsAPI.as_view()

SaveBusinessCard = SaveBusinessCardAPI.as_view()

UploadProductImage = UploadProductImageAPI.as_view()

DeleteImage = DeleteImageAPI.as_view()

UploadAttachment = UploadAttachmentAPI.as_view()

DeleteAttachment = DeleteAttachmentAPI.as_view()

FetchProductCards = FetchProductCardsAPI.as_view()

SaveFactoryDetails = SaveFactoryDetailsAPI.as_view()

ExportFactories = ExportFactoriesAPI.as_view()

SearchFactories = SearchFactoriesAPI.as_view()

SearchFactoriesByDate = SearchFactoriesByDateAPI.as_view()

SearchProducts = SearchProductsAPI.as_view()

ShareFactory = ShareFactoryAPI.as_view()

SendFactoryShareEmail = SendFactoryShareEmailAPI.as_view()

ShareProduct = ShareProductAPI.as_view()

UploadFactoriesProducts = UploadFactoriesProductsAPI.as_view()

UploadFactoriesProductsFromSourcing = UploadFactoriesProductsFromSourcingAPI.as_view()
