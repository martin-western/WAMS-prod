from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

from WIGApp.models import *
from WIGApp.utils import *

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


from WIGApp.views_factory_manager import *

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


class CsrfExemptSessionAuthentication(SessionAuthentication):

    def enforce_csrf(self, request):
        return


# def LoginSourcingUser(request):
#     return render(request, "WIGApp/login-sourcing-user.html")


def Login(request):
    return render(request, 'WIGApp/login.html')


@login_required(login_url='/login/')
def Logout(request):
    logout(request)
    return HttpResponseRedirect('/login/')


"""
    Put the conditional logins here. We need to create logins for sourcing manager and sourcing executive

"""
@login_required(login_url='/login/')
def Home(request):
    is_factory_manager = FactoryManager.objects.filter(
        username=request.user.username).exists()

    is_sourcing_user = SourcingUser.objects.filter(
        username=request.user.username).exists()

    if(is_factory_manager):
        return render(request, 'WIGApp/home-factory-manager.html')
        # return render(request, 'WIGApp/factory-page-bkp.html')
    elif is_sourcing_user:
        if SourcingUser.objects.get(username=request.user.username).is_scouting_user:
            return render(request, 'WIGApp/home.html')
        logger.info("From WIGApp/views: %s", str(is_sourcing_user))
        return render(request, 'WIGApp/sourcing-factory-listing.html')
    else:
        return render(request, 'WIGApp/home.html')


def RedirectHome(request):
    return HttpResponseRedirect('/home/')


@login_required(login_url='/login/')
def FactoryPage(request, pk):
    return render(request, 'WIGApp/factory-page.html')


@login_required(login_url='/login/')
def AddFactoryPage(request):
    return render(request, 'WIGApp/add-factory.html')


@login_required(login_url='/login/')
def NewProductPage(request, pk):
    return render(request, 'WIGApp/new-product.html')


@login_required(login_url='/login/')
def ProductPage(request, pk):
    return render(request, 'WIGApp/product-page.html')


@login_required(login_url='/login/')
def FactoryProducts(request):
    return render(request, 'WIGApp/factory-products.html')


@login_required(login_url='/login/')
def SourcingProducts(request):
    return render(request, 'WIGApp/sourcing-products.html')


class LoginSubmitAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("LoginSubmitAPI: %s", str(data))

            username = data['username']
            password = data['password']

            user = authenticate(username=username, password=password)

            login(request, user)

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("LoginSubmitAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchFactoriesAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchFactoriesAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            sourcing_user_factories = SourcingUserFactory.objects.all()
            factory_list = []
            for sourcing_user_factory in sourcing_user_factories:
                factory = sourcing_user_factory.base_factory
                temp_dict = {}
                temp_dict["name"] = sourcing_user_factory.name
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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

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


LoginSubmit = LoginSubmitAPI.as_view()

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
