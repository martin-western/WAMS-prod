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

logger = logging.getLogger(__name__)

class FetchFactoryDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchFactoryDetailsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            pk = int(data['pk'])
            factory = Factory.objects.get(pk=pk)

            temp_dict = {}
            temp_dict["name"] = factory.name
            temp_dict["address"] = factory.address
            temp_dict["email_id"] = factory.factory_emailid

            temp_dict["loading_port"] = factory.loading_port
            temp_dict["location"] = factory.location

            temp_dict["notes"] = factory.other_info
            temp_dict["contact_person_name"] = factory.contact_person_name
            temp_dict["contact_person_mobile_number"] = factory.contact_person_mobile_no
            temp_dict["contact_person_email_id"] = factory.contact_person_emailid
            temp_dict["tag"] = factory.social_media_tag
            temp_dict["tag_info"] = factory.social_media_tag_information
            
            if factory.bank_details:
                temp_dict["bank_name"] = factory.bank_details.name
                temp_dict["bank_address"] = factory.bank_details.address
                temp_dict["bank_account_number"] = factory.bank_details.account_number
                temp_dict["bank_ifsc_code"] = factory.bank_details.ifsc_code
                temp_dict["bank_swift_code"] = factory.bank_details.swift_code
                temp_dict["bank_branch_code"] = factory.bank_details.branch_code

            temp_dict["pk"] = factory.pk
            phone_numbers = []
            for phone_number in factory.phone_numbers.all():
                phone_numbers.append(phone_number.number)
            temp_dict["phone_numbers"] = phone_numbers
            images_list = []
            if factory.images.all().count() > 0:
                for image in factory.images.all():
                    temp_dict2 = {}
                    temp_dict2["url"] = image.image.url
                    temp_dict2["pk"] = image.pk
                    images_list.append(temp_dict2)
            temp_dict["images_list"] = images_list

            operating_hours = []
            for operating_hour in factory.operating_hours.all():
                operating_hour_dict = {}
                operating_hour_dict["day"] = operating_hour.day
                operating_hour_dict["from_time"] = str(operating_hour.from_time)
                operating_hour_dict["to_time"] = str(operating_hour.to_time)
                operating_hours.append(operating_hour_dict)
            temp_dict["operating_hours"] = operating_hours
            
            if(factory.logo != None and factory.logo != ""):
                temp_dict["logo"] = factory.logo.image.url
            else:
                temp_dict["logo"] = Config.objects.all()[
                    0].product_404_image.image.url
            # temp_dict["bank_details"] = factory.bank_details
            temp_dict["total_products"] = factory.products.all().count()

            response["factory"] = temp_dict
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFactoryDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchFactoriesListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchFactoriesListAPI: %s", str(data))
            
            user = OmnyCommUser.objects.get(username=request.user.username)
            
            chip_data = json.loads(data['tags'])

            factories = Factory.objects.filter(Q(created_by=user) | Q(created_by__reports_to=user))
            
            if len(chip_data)>0:
                for tag in chip_data:
                    factories = factories.filter(name__icontains = tag)
            factory_list = []
            
            for factory in factories:
                temp_dict = {}
                temp_dict["name"] = factory.name
                temp_dict["address"] = factory.address
                temp_dict["pk"] = factory.pk
                phone_numbers = []
                for phone_number in factory.phone_numbers.all():
                    phone_numbers.append(phone_number.number)
                temp_dict["phone_numbers"] = phone_numbers
                images_list = []
                
                try:
                    temp_dict["business_card"] = factory.business_card.image.url
                except Exception as e:
                    temp_dict["business_card"] = Config.objects.all()[
                        0].product_404_image.image.url

                
                operating_hours = []
                for operating_hour in factory.operating_hours.all():
                    operating_hour_dict = {}
                    operating_hour_dict["day"] = operating_hour.day
                    operating_hour_dict["from_time"] = str(operating_hour.from_time)
                    operating_hour_dict["to_time"] = str(operating_hour.to_time)
                    operating_hours.append(operating_hour_dict)
                temp_dict["operating_hours"] = operating_hours

                if(factory.logo != None and factory.logo != ""):
                    temp_dict["logo"] = factory.logo.image.url
                elif len(factory.images.all()) > 0:
                    temp_dict["logo"] = factory.images.all()[0].image.url
                else:
                    temp_dict["logo"] = Config.objects.all()[
                        0].product_404_image.image.url
              
                temp_dict["total_products"] = factory.products.all().count()

                temp_dict["average_delivery_days"] = factory.average_delivery_days
                temp_dict["average_turn_around_time"] = factory.average_turn_around_time


                factory_list.append(temp_dict)
 
            response["factories"] = factory_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFactoriesListAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchProductsFromFactoryAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        is_user = False

        try:
            is_user = OmnyCommUser.objects.filter(username=request.user.username).exists()

            try:
                data = request.data
                logger.info("FetchProductsFromFactoryAPI: %s", str(data))
                products = []
                chip_data = json.loads(data['tags'])

                    
                logger.info("FetchProductsFromFactoryAPI: debugging %s", is_user)
                
                user = OmnyCommUser.objects.get(username=request.user.username)

                factories = Factory.objects.filter(Q(created_by=user) | Q(created_by__reports_to=user))
                
                products_objs |= Product.objects.filter(factory__in=factories)
                
                if len(chip_data) != 0:
                    for tag in chip_data:
                        search = products_objs.filter(product_name__icontains=tag)
                        products_objs = search
                
                products_objs = set(products_objs)
               
                try:                    
                    for product in products_objs:
                        
                        sourcing_product = SourcingProduct.objects.get(product=product)
                        temp_dict = {}

                        temp_dict["factory_pk"] = product.factory.pk
                        temp_dict["factory_name"] =  product.factory.name
                        temp_dict["name"] = product.product_name
                        temp_dict["code"] = sourcing_product.code
                        temp_dict["price"] = sourcing_product.standard_price
                        temp_dict["currency"] = sourcing_product.currency
                        temp_dict["minimum_order_qty"] = sourcing_product.minimum_order_qty
                        temp_dict["qty_metric"] = sourcing_product.qty_metric
                        temp_dict["order_qty"] = sourcing_product.order_qty
                        temp_dict["other_info"] = sourcing_product.other_info
                        temp_dict["created_date"] = sourcing_product.created_date
                        temp_dict["go_live_status"] = sourcing_product.go_live
                        temp_dict["delivery_days"] = sourcing_product.delivery_days

                        temp_dict["pk"] = product.pk
                        temp_dict["image_url"] = ""
                        if product.images.all().count()>0:
                            temp_dict["image_url"] = product.images.all()[
                                0].image.url
                        else :
                            temp_dict["image_url"] = Config.objects.all()[0].product_404_image.image.url

                        products.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchProductsFromFactoryAPI: %s at %s",
                        e, str(exc_tb.tb_lineno))

                response["products"] = products
                
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("FetchProductsFromFactoryAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["status"] = 200

        except Exception as e:
            logger.info("User is not sourcing user")
        
        return Response(data=response)

class SaveFactoryDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info(
                "class SaveFactoryDetailsAPI: % s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            factory = Factory.objects.get(pk = int(data["pk"]))

            factory.name = data["factory_name"]

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

            factory.other_info = data["notes"]
            factory.save()
           
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

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveFactoryDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class FetchFactorywiseProductListingAPI(APIView):

    def post(self, request, *args, **kwargs):


        response = {}
        response['status'] = 500
        try:
            data = request.data
            
            logger.info("FetchFactorywiseProductListingAPI: %s", str(data))
            
            if not isinstance(data, dict):
                data = json.loads(data)

            response_products = []
            factory = Factory.objects.get(pk=int(data["factory_pk"]))
            
            chip_data = json.loads(data['tags'])

            products = Product.objects.none()
            
            if len(chip_data)>0:
                for tag in chip_data:
                    products |= Product.objects.filter(product_name__icontains=tag,factory=factory)

            products = products.distinct()

            response["factory_name"] = factory.name
            response["factory_address"] = factory.address
            response["factory_image"] = Config.objects.all()[0].product_404_image.image.url
            response["factory_background_poster"] = Config.objects.all()[0].product_404_image.image.url
            
            if factory.images.all().count() > 0:
                response["factory_image"] = factory.images.all()[0].image.url
            if factory.background_poster:
                response["factory_background_poster"] = factory.background_poster.image.url
            try:
                for product in products:
                    product = product
                    temp_dict = {}
                    temp_dict["pk"] = product.product.pk
                    temp_dict["name"] = product.name
                    
                    temp_dict["moq"] = product.product.minimum_order_qty 
                    temp_dict["delivery_days"] = product.product.delivery_days
                    temp_dict["price"] = product.price
                    temp_dict["go_live_status"] = product.product.go_live
                    temp_dict["factory_name"] = factory.name


                    if product.images.all().count()>0:
                        temp_dict["image_url"] = product.images.all()[0].image.url
                    else :
                        temp_dict["image_url"] = Config.objects.all()[0].product_404_image.image.url


                    response_products.append(temp_dict)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("FetchFactorywiseProductListingAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["products"] = response_products
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFactorywiseProductListingAPI: %s at %s", e, str(exc_tb.tb_lineno))

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

            factory = Factory.objects.get(pk = int(data["pk"]))
            images_count = int(data["images_count"])

            images_list = []
            for i in range(images_count):
                im_obj = Image.objects.create(
                    image=data["product_image_"+str(i)])
                factory.images.add(im_obj)

            factory.save()

            images = factory.images.all()

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
            sourcing_product = SourcingProduct.objects.get(product=product)

            temp = product.go_live

            if temp == False and sourcing_product.is_pr_ready == True:
                sourcing_product.go_live = True
            else:
                sourcing_product.go_live = False
                response['error_msg'] = 'not_pr_ready'

            sourcing_product.save()
            response["go_live_status"] = sourcing_product.go_live
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
                temp_obj = BaseProduct.objects.get(pk = int(k["pk"]))
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
                factory = Factory.objects.get(pk = pk)
                temp_proforma_invoice.factory = factory
                temp_proforma_invoice.save()
                
                if factory.products > 0:

                    json_parameter = {}
                    json_parameter["factory_name"] = str(factory.name)
                    json_parameter["factory_address"] = str(factory.address)
                    json_parameter["loading_port"] = str(factory.loading_port)
                    try:
                        json_parameter["bank_name"] = str(factory.bank_details.name)
                        json_parameter["bank_address"] = str(factory.bank_details.address)
                        json_parameter["bank_account_number"] = str(factory.bank_details.account_number)
                        json_parameter["bank_ifsc_code"] = str(factory.bank_details.ifsc_code)
                        json_parameter["bank_swift_code"] = str(factory.bank_details.swift_code)
                        json_parameter["bank_branch_code"] = str(factory.bank_details.branch_code)
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

                    products = factory.products.filter(pk__in=selected_products_pk)

                    product_info = []
                    logger.info("selected_products_dict %s", str(selected_products_dict))
                    for product in products:
                        
                        sourcing_product = SourcingProduct.objects.get(product=product)

                        temp_dict = {} 
                        temp_dict["image_url"] = ""
                        if product.images.count()>0:
                            temp_dict["image_url"] = "file:///"+BASE_DIR + product.images.all()[0].image.url
                        temp_dict["code"] = str(sourcing_product.code)
                        temp_dict["brand_category"] = str(product.brand.name)
                        temp_dict["other_info"] = str(sourcing_product.other_info)
                        temp_dict["size"] = str(sourcing_product.size)
                        temp_dict["weight"] = str(sourcing_product.weight)
                        temp_dict["design"] = str(sourcing_product.design)
                        temp_dict["colors"] = str(product.color)
                        temp_dict["pkg_inner"] = str(sourcing_product.pkg_inner)
                        temp_dict["pkg_m_ctn"] = str(sourcing_product.pkg_m_ctn)
                        temp_dict["p_ctn_cbm"] = str(sourcing_product.p_ctn_cbm)
                        temp_dict["ttl_ctn"] = str(sourcing_product.ttl_ctn)
                        temp_dict["ttl_cbm"] = str(sourcing_product.ttl_cbm)
                        temp_dict["ship_lot_number"] = str(sourcing_product.ship_lot_number)
                        temp_dict["order_quantity"] = selected_products_dict[str(product.pk)]
                        temp_dict["qty_metric"] = str(sourcing_product.qty_metric)
                        temp_dict["price"] = str(sourcing_product.price)
                        product_info.append(temp_dict)

                    json_parameter["product_info"] = product_info

                    filename = factory.name.replace(" ", "_").replace(",", "").replace("&", "")+"_"+str(temp_proforma_invoice.pk)+".pdf"
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
                if draft_pi_line.factory.pk in draft_pi_lines_dict.keys():
                    draft_pi_lines_dict[draft_pi_line.factory.pk].append(draft_pi_line)
                else:
                    draft_pi_lines_dict[draft_pi_line.factory.pk] = [draft_pi_line]

            
            if percentage_of_payment:
                pass
            else:
                percentage_of_payment = ''
            
            temp_proforma_invoice_ids = []
            for factory_pk in draft_pi_lines_dict:
                temp_proforma_invoice = ''
                temp_selected_products = []
                for x in draft_pi_lines_dict[factory_pk]:
                    temp_selected_products.append(x.product.pk)
                for k in temp_selected_products:
                    temp_obj = BaseProduct.objects.get(pk = int(k))
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
                    factory = Factory.objects.get(pk=factory_pk)
                    temp_proforma_invoice.factory = factory
                    temp_proforma_invoice.save()
                    
                    factory_manager_factory = None
                    
                    if factory.products > 0:

                        factory = factory

                        json_parameter = {}
                        json_parameter["factory_name"] = str(factory.name)
                        json_parameter["factory_address"] = str(factory.address)
                        json_parameter["loading_port"] = str(factory.loading_port)
                        try:
                            json_parameter["bank_name"] = str(factory.bank_details.name)
                            json_parameter["bank_address"] = str(factory.bank_details.address)
                            json_parameter["bank_account_number"] = str(factory.bank_details.account_number)
                            json_parameter["bank_ifsc_code"] = str(factory.bank_details.ifsc_code)
                            json_parameter["bank_swift_code"] = str(factory.bank_details.swift_code)
                            json_parameter["bank_branch_code"] = str(factory.bank_details.branch_code)
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

                        products = factory.products.filter(pk__in=selected_products_pk)

                        product_info = []
                        for product in products:
                            
                            sourcing_product = SourcingProduct.objects.get(product=product)
                            
                            temp_dict = {} 
                            temp_dict["code"] = str(sourcing_product.code)
                            temp_dict["brand_category"] = str(sourcing_product.brand.name)
                            temp_dict["other_info"] = str(sourcing_product.other_info)
                            temp_dict["size"] = str(sourcing_product.size)
                            temp_dict["weight"] = str(sourcing_product.weight)
                            temp_dict["design"] = str(sourcing_product.design)
                            temp_dict["colors"] = str(product.color)
                            temp_dict["pkg_inner"] = str(sourcing_product.pkg_inner)
                            temp_dict["pkg_m_ctn"] = str(sourcing_product.pkg_m_ctn)
                            temp_dict["p_ctn_cbm"] = str(sourcing_product.p_ctn_cbm)
                            temp_dict["ttl_ctn"] = str(sourcing_product.ttl_ctn)
                            temp_dict["ttl_cbm"] = str(sourcing_product.ttl_cbm)
                            temp_dict["ship_lot_number"] = str(sourcing_product.ship_lot_number)
                            temp_dict["order_quantity"] = str(selected_products_dict[str(product.pk)])
                            temp_dict["qty_metric"] = str(sourcing_product.qty_metric)
                            temp_dict["price"] = str(sourcing_product.price)
                            product_info.append(temp_dict)

                        json_parameter["product_info"] = product_info

                        filename = factory.name.replace(" ", "_").replace(",", "").replace("&", "")+"_"+str(temp_proforma_invoice.pk)+".pdf"
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
                sourcing_product = SourcingProduct.objects.get(
                    code=product_sheet.cell_value(row_number, 1))


                factory = Factory.objects.filter(products = sourcing_product.product)[0]

                temp_draft_PI_line = DraftProformaInvoiceLine.objects.create(
                    product = sourcing_product.product,
                    factory = factory,
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
                product = draft_line.product
                factory = draft_line.factory
                temp_dict["quantity"] = draft_line.quantity
                temp_dict["factory_name"] = factory.name
                temp_dict["factory_pk"] = factory.pk
                temp_dict["product_name"] = product.name
                temp_dict["product_pk"] = product.pk 
                temp_dict["product_code"] = product.code
                temp_dict["price"] = product.price
                temp_dict["moq"] = str(product.product.minimum_order_qty)
                temp_dict["draft_line_id"] = line_id
                temp_dict["draft_pi_id"] = draft_pi.pk
                
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
                    product = BaseProduct.objects.get(pk = temp_product["product_pk"])
                    factory = Factory.objects.get(pk = temp_product["factory_pk"])

                    draft_pi_line = DraftProformaInvoiceLine.objects.create(product = product,factory = factory, quantity = temp_product["quantity"],
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

FetchFactoryForOmnyCommUser = FetchFactoryForOmnyCommUserAPI.as_view()

FetchFactoriesForOmnyCommUser = FetchFactoriesForOmnyCommUserAPI.as_view()

FetchOmnyCommUserDetails = FetchOmnyCommUserDetailsAPI.as_view()

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
