from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

from WAMSApp.models import *
from WAMSApp.utils import *
from WAMSApp.utils_sourcing import *

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
from django.db.models import Q
from django.db.models import Count
from django.db.models import Sum
from django.conf import settings
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
import zipfile
import inflect
import boto3
import urllib.request, urllib.error, urllib.parse

from datetime import datetime
from django.utils import timezone
from django.core.files import File


logger = logging.getLogger(__name__)


class FetchFactoryListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchFactoryListAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            chip_data = data.get('tags', [])

            factory_objs = Factory.objects.all()
            
            if len(chip_data)>0:
                factory_objs = Factory.objects.none()
                for tag in chip_data:
                    factory_objs |= Factory.objects.filter(name__icontains=tag)
                factory_objs = factory_objs.distinct()

            page = int(data.get('page', 1))
            paginator = Paginator(factory_objs, 20)
            total_factories = factory_objs.count()
            factory_objs = paginator.page(page)

            factory_list = []
            
            for factory_obj in factory_objs:
                temp_dict = {}
                temp_dict["name"] = factory_obj.name
                temp_dict["address"] = factory_obj.address
                temp_dict["pk"] = factory_obj.pk
                temp_dict["phone_numbers"] = json.loads(factory_obj.phone_numbers)
                
                images_list = []
                try:
                    temp_dict["business_card"] = factory_obj.business_card.image.url
                except Exception as e:
                    temp_dict["business_card"] = Config.objects.all()[0].product_404_image.image.url
                
                temp_dict["operating_hours"] = json.loads(factory_obj.operating_hours)

                try:
                    temp_dict["logo"] = factory_obj.logo.image.url
                except Exception as e:
                    temp_dict["logo"] = Config.objects.all()[0].product_404_image.image.url
              
                temp_dict["total_products"] = Product.objects.filter(factory=factory_obj).count()
                temp_dict["average_delivery_days"] = factory_obj.average_delivery_days
                temp_dict["average_turn_around_time"] = factory_obj.average_turn_around_time


                factory_list.append(temp_dict)
 
            is_available = True
            
            if paginator.num_pages == page:
                is_available = False

            response["is_available"] = is_available

            response["factories"] = factory_list
            response["total_factories"] = total_factories
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFactoryListAPI: %s at %s", e, str(exc_tb.tb_lineno))

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

            pk = int(data['pk'])
            factory_obj = Factory.objects.get(pk=pk)

            temp_dict = {}
            temp_dict["name"] = factory_obj.name
            temp_dict["address"] = factory_obj.address
            temp_dict["email_id"] = factory_obj.factory_emailid

            temp_dict["loading_port"] = factory_obj.loading_port
            temp_dict["location"] = factory_obj.location

            temp_dict["notes"] = factory_obj.other_info
            temp_dict["contact_person_name"] = factory_obj.contact_person_name
            temp_dict["contact_person_mobile_number"] = factory_obj.contact_person_mobile_no
            temp_dict["contact_person_email_id"] = factory_obj.contact_person_emailid
            temp_dict["tag"] = factory_obj.social_media_tag
            temp_dict["tag_info"] = factory_obj.social_media_tag_information
            
            temp_dict["bank_name"] = factory_obj.bank_details.name
            temp_dict["bank_address"] = factory_obj.bank_details.address
            temp_dict["bank_account_number"] = factory_obj.bank_details.account_number
            temp_dict["bank_ifsc_code"] = factory_obj.bank_details.ifsc_code
            temp_dict["bank_swift_code"] = factory_obj.bank_details.swift_code
            temp_dict["bank_branch_code"] = factory_obj.bank_details.branch_code

            temp_dict["pk"] = factory_obj.pk
            temp_dict["phone_numbers"] = json.loads(factory_obj.phone_numbers)
            images_list = []
            if factory_obj.images.all().count() > 0:
                for image in factory_obj.images.all():
                    temp_dict2 = {}
                    temp_dict2["url"] = image.image.url
                    temp_dict2["pk"] = image.pk
                    images_list.append(temp_dict2)
            temp_dict["images_list"] = images_list

            temp_dict["operating_hours"] = json.loads(factory_obj.operating_hours)
            
            try:
                temp_dict["logo"] = factory_obj.logo.image.url
            except Exception as e:
                temp_dict["logo"] = Config.objects.all()[0].product_404_image.image.url
            
            temp_dict["total_products"] = Product.objects.filter(factory=factory_obj).count()

            response["factory"] = temp_dict
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFactoryDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchProductListingForPIAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:
            data = request.data
            logger.info("FetchProductListingForPIAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
                
            chip_data = data.get('tags', [])

            product_objs = Product.objects.exclude(factory=None)
            if "factory_pk" in data:
                factory_obj = Factory.objects.get(pk=data["factory_pk"])
                product_objs = Product.objects.filter(factory=factory_obj)

                
            if len(chip_data) != 0:
                temp_product_objs = Product.objects.none()
                for tag in chip_data:
                    temp_product_objs |= product_objs.filter(product_name__icontains=tag)
                product_objs = temp_product_objs.distinct()
               
            product_list = []

            for product_obj in product_objs:
                try:
                    sourcing_product = SourcingProduct.objects.get(product=product_obj)
                    temp_dict = {}

                    temp_dict["factory_pk"] = product_obj.factory.pk
                    temp_dict["factory_name"] =  product_obj.factory.name
                    temp_dict["factory_code"] =  product_obj.factory.factory_code
                    temp_dict["product_name"] = product_obj.product_name
                    temp_dict["seller_sku"] = product_obj.base_product.seller_sku
                    temp_dict["brand_name"] = str(product_obj.base_product.brand)
                    temp_dict["category"] = "" if product_obj.base_product.category==None else str(product_obj.base_product.category)
                    temp_dict["sub_category"] = "" if product_obj.base_product.sub_category==None else str(product_obj.base_product.sub_category)
                    temp_dict["price"] = sourcing_product.price
                    temp_dict["currency"] = sourcing_product.currency
                    temp_dict["minimum_order_qty"] = sourcing_product.minimum_order_qty
                    temp_dict["qty_metric"] = sourcing_product.qty_metric
                    temp_dict["order_qty"] = sourcing_product.order_qty
                    temp_dict["other_info"] = sourcing_product.other_info
                    temp_dict["delivery_days"] = sourcing_product.delivery_days
                    temp_dict["product_pk"] = product_obj.pk
                    temp_dict["product_uuid"] = product_obj.uuid
                    temp_dict["image_url"] = ""
                    try:
                        temp_dict["image_url"] = MainImages.objects.get(product=product_obj, is_sourced=True).main_images.all()[0].image.image.url
                    except Exception as e:
                        temp_dict["image_url"] = Config.objects.all()[0].product_404_image.image.url

                    product_list.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchProductListingForPIAPI: %s at %s",
                        e, str(exc_tb.tb_lineno))

            response["product_list"] = product_list
            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductListingForPIAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class SaveFactoryDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("class SaveFactoryDetailsAPI: % s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            factory_obj = Factory.objects.get(pk = int(data["pk"]))

            factory_obj.name = data["factory_name"]
            factory_obj.address = data["factory_address"]
            factory_obj.factory_emailid = data["factory_emailid"]
            factory_obj.loading_port = data["loading_port"]
            factory_obj.location = data["location"]
            factory_obj.notes = data["notes"]
            factory_obj.contact_person_name = data["contact_person_name"]
            factory_obj.contact_person_mobile_no = data["contact_person_mobile_number"]
            factory_obj.contact_person_emailid = data["contact_person_emailid"]
            factory_obj.social_media_tag = data["tag"]
            factory_obj.social_media_tag_information = data["tag_info"]
            factory_obj.other_info = data["notes"]
            factory_obj.phone_numbers = json.dumps(data["phone_numbers"])

            bank_obj = None
            if factory_obj.bank_details == None:
                bank_obj, created = Bank.objects.get_or_create(ifsc_code=data["bank_ifsc_code"])
                factory_obj.bank_details = bank_obj
                factory_obj.save()
            else:
                bank_obj = factory_obj.bank_details

            bank_obj.name = data["bank_name"]
            bank_obj.address= data["bank_address"]
            bank_obj.account_number=data["bank_account_number"]
            bank_obj.swift_code=data["bank_swift_code"]
            bank_obj.branch_code=data["bank_branch_code"] 
            bank_obj.save()
            
            factory.save()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveFactoryDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadFactoryImagesAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UploadFactoryImagesAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            factory_obj = Factory.objects.get(pk = int(data["factory_pk"]))
            images_count = int(data["images_count"])

            images_list = []
            for i in range(images_count):
                image_obj = Image.objects.create(image=data["image_"+str(i)])
                factory_obj.images.add(image_obj)

            factory_obj.save()

            response["status"] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadFactoryImagesAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DownloadBulkPIAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DownloadBulkPIAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            factory_list = data["factory_list"]

            proforma_invoice_bundle_obj = ProformaInvoiceBundle.objects.create()

            filepath_list = []
            for factory in factory_list:
                filepath = generate_pi(factory["factory_code"], factory["invoice_details"], factory["product_list"])
                filepath_list.append(filepath)
                invoice_details = factory["invoice_details"]
                factory_obj = Factory.objects.get(factory_code=factory["factory_code"])

                local_file = open(filepath, "rb")
                djangofile = File(local_file)

                proforma_invoice_obj = ProformaInvoice.objects.create(payment_terms=invoice_details["payment_terms"],
                                                                      advance=invoice_details["advance"],
                                                                      inco_terms=invoice_details["inco_terms"],
                                                                      ttl_cntrs=invoice_details["ttl_cntrs"],
                                                                      delivery_terms=invoice_details["delivery_terms"],
                                                                      factory=factory_obj,
                                                                      invoice_number=invoice_details["invoice_number"],
                                                                      proforma_invoice_bundle=proforma_invoice_bundle_obj)
                proforma_invoice_obj.proforma_pdf.save(filepath.split("/")[-1], djangofile, save=True)
                local_file.close()

                for product in factory["product_list"]:
                    product_obj = Product.objects.get(uuid=product["uuid"])
                    UnitProformaInvoice.objects.create(product=product_obj, quantity=int(product["quantity"]), proforma_invoice=proforma_invoice_obj)


            zip_path = "files/invoices/proforma_invoice.zip"
            zf = zipfile.ZipFile(zip_path, "w")
            for filepath in filepath_list:
                zf.write(filepath)
            zf.close()

            local_file = open(zip_path, "rb")
            djangofile = File(local_file)
            proforma_invoice_bundle_obj.proforma_zip.save(zip_path.split("/")[-1], djangofile, save=True)
            local_file.close()
                    
            response['filepath'] = proforma_invoice_bundle_obj.proforma_zip.url
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DownloadBulkPIAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchProformaBundleListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:

            data = request.data
            logger.info("FetchProformaBundleList: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            proforma_invoice_bundle_objs = ProformaInvoiceBundle.objects.all().order_by("-pk")

            page = int(data.get('page',1))
            paginator = Paginator(proforma_invoice_bundle_objs, 20)
            total_bundle_count = proforma_invoice_bundle_objs.count()
            proforma_invoice_bundle_objs = paginator.page(page)

            proforma_invoice_bundle_list = []
            for proforma_invoice_bundle_obj in proforma_invoice_bundle_objs:
                try:
                    temp_dict = {}
                    temp_dict["uuid"] = proforma_invoice_bundle_obj.uuid
                    proforma_invoice_objs = ProformaInvoice.objects.filter(proforma_invoice_bundle=proforma_invoice_bundle_obj)
                    factory_list = []
                    for proforma_invoice_obj in proforma_invoice_objs:
                        temp_dict2 = {}
                        temp_dict2["uuid"] = proforma_invoice_obj.uuid
                        temp_dict2["factory_code"] = proforma_invoice_obj.factory.factory_code
                        temp_dict2["factory_name"] = proforma_invoice_obj.factory.name
                        temp_dict2["filepath"] = proforma_invoice_obj.proforma_pdf.url
                        temp_dict2["product_count"] = UnitProformaInvoice.objects.filter(proforma_invoice=proforma_invoice_obj).count()
                        factory_list.append(temp_dict2)
                    temp_dict["factory_list"] = factory_list
                    temp_dict["created_date"] = proforma_invoice_bundle_obj.created_date.strftime("%d %b, %Y")
                    temp_dict["filepath"] = proforma_invoice_bundle_obj.proforma_zip.url
                    proforma_invoice_bundle_list.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchProformaBundleList: %s at %s", e, str(exc_tb.tb_lineno))

            is_available = True
            
            if paginator.num_pages == page:
                is_available = False

            response["is_available"] = is_available
            
            response["total_bundle_count"] = total_bundle_count
            response["proforma_invoice_bundle_list"] = proforma_invoice_bundle_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProformaBundleList: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchPIFactoryListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:

            data = request.data
            logger.info("FetchPIFactoryListAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            proforma_invoice_bundle_obj = ProformaInvoiceBundle.objects.get(uuid=data["uuid"])

            proforma_invoice_objs = ProformaInvoice.objects.filter(proforma_invoice_bundle=proforma_invoice_bundle_obj)

            pi_factory_list = []
            for proforma_invoice_obj in proforma_invoice_objs:
                try:
                    proforma_invoice_bundle_obj = proforma_invoice_obj.proforma_invoice_bundle
                    temp_dict = {}
                    temp_dict["uuid"] = proforma_invoice_obj.uuid
                    temp_dict["factory_code"] = proforma_invoice_obj.factory.factory_code
                    temp_dict["factory_name"] = proforma_invoice_obj.factory.name
                    if proforma_invoice_obj.proforma_pdf==None:
                        temp_dict["pdf_ready"] = False
                    else:
                        temp_dict["pdf_ready"] = True
                        temp_dict["filepath"] = proforma_invoice_obj.proforma_pdf.url
                    temp_dict["product_count"] = UnitProformaInvoice.objects.filter(proforma_invoice=proforma_invoice_obj).count()
                    temp_dict["product_qty_count"] = UnitProformaInvoice.objects.filter(proforma_invoice=proforma_invoice_obj).aggregate(Sum('quantity'))["quantity__sum"]

                    temp_dict["created_date"] = proforma_invoice_bundle_obj.created_date.strftime("%d %b, %Y")
                    pi_factory_list.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchProformaBundleList: %s at %s", e, str(exc_tb.tb_lineno))
            
            response["pi_factory_list"] = pi_factory_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchPIFactoryListAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadFactoryPIAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:

            data = request.data
            logger.info("UploadFactoryPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            proforma_invoice_obj = ProformaInvoice.objects.get(uuid=data["uuid"])
            decoded_file = decode_base64_file(data["proforma_pdf"])
            proforma_invoice_obj.proforma_pdf = decoded_file
            proforma_invoice_obj.save()
        
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadFactoryPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchPIFormAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:

            data = request.data
            logger.info("FetchPIFormAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            proforma_invoice_obj = ProformaInvoice.objects.get(uuid=data["uuid"])
            factory_obj = proforma_invoice_obj.factory
            bank_obj = factory_obj.bank_details

            response["factory_name"] = str(factory_obj.name)
            response["factory_address"] = str(factory_obj.address)
            try:
                response["factory_number"] = str(json.loads(factory_obj.phone_numbers)[0])
            except Exception as e:
                response["factory_number"] = ""

            response["contact_person_name"] = str(factory_obj.contact_person_name)
            response["contact_person_mobile_number"] = str(factory_obj.contact_person_mobile_no)
            response["loading_port"] = str(factory_obj.loading_port)
            response["discharge_port"] = str(proforma_invoice_obj.discharge_port)
            response["vessel_details"] = str(proforma_invoice_obj.vessel_details)
            response["vessel_final_destination"] = str(proforma_invoice_obj.vessel_final_destination)
            response["payment_terms"] = str(proforma_invoice_obj.payment_terms)
            response["inco_terms"] = str(proforma_invoice_obj.inco_terms)
            response["delivery_terms"] = str(proforma_invoice_obj.delivery_terms)
            response["shipment_lot_number"] = str(proforma_invoice_obj.ship_lot_number)
            response["invoice_number"] = str(proforma_invoice_obj.invoice_number)
            response["invoice_date"] = str(proforma_invoice_obj.invoice_date)
            response["bank_name"] = str(bank_obj.name)
            response["account_number"] = str(bank_obj.account_number)
            response["ifsc_code"] = str(bank_obj.ifsc_code)
            response["swift_code"] = str(bank_obj.swift_code)
            response["branch_code"] = str(bank_obj.branch_code)
            response["bank_address"] = str(bank_obj.address)
            response["important_notes"] = str(proforma_invoice_obj.important_notes)
            response["terms_and_condition"] = str(proforma_invoice_obj.terms_and_condition)
            
            unit_proforma_invoice_objs = UnitProformaInvoice.objects.filter(proforma_invoice=proforma_invoice_obj)
            unit_proforma_invoice_list = []
            total_amount = 0
            total_amount_in_words = ""
            for unit_proforma_invoice_obj in unit_proforma_invoice_objs:
                try:
                    product_obj = unit_proforma_invoice_obj.product
                    sourcing_product_obj = SourcingProduct.objects.get(product=product_obj)
                    temp_dict = {}
                    temp_dict["product_name"] = product_obj.product_name
                    temp_dict["seller_sku"] = product_obj.base_product.seller_sku
                    temp_dict["brand_name"] = str(product_obj.base_product.brand)
                    temp_dict["size"] = str(sourcing_product_obj.size)
                    temp_dict["weight"] = str(sourcing_product_obj.weight) + " " + str(sourcing_product_obj.weight_metric)
                    temp_dict["thickness"] = "NA"
                    temp_dict["design"] = str(sourcing_product_obj.design)
                    temp_dict["pkg_m_ctn"] = str(sourcing_product_obj.pkg_m_ctn)
                    temp_dict["p_ctn_cbm"] = str(sourcing_product_obj.p_ctn_cbm)
                    temp_dict["pkg_inner"] = str(sourcing_product_obj.pkg_inner)
                    temp_dict["ttl_ctn"] = str(sourcing_product_obj.ttl_ctn)
                    temp_dict["ttl_cbm"] = str(sourcing_product_obj.ttl_cbm)
                    temp_dict["quantity"] = str(unit_proforma_invoice_obj.quantity)
                    temp_dict["quantity_meteric"] = "Sets"
                    temp_dict["price"] = str(sourcing_product_obj.price)
                    temp_dict["amount"] = str(round(float(temp_dict["price"])*float(temp_dict["quantity"]), 2))
                    total_amount += float(temp_dict["price"])*float(temp_dict["quantity"])

                    try:
                        image_url = MainImages.objects.get(product=product_obj, is_sourced=True).main_images.all()[0].image.image.url

                        s3 = boto3.client('s3',
                                          aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                          aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

                        filename = urllib.parse.unquote(image_url)
                        filename = "/".join(filename.split("/")[3:])
                        local_link = "/files/images_s3/" + str(filename)
                        s3.download_file(settings.AWS_STORAGE_BUCKET_NAME, filename, "." + local_link)
                        temp_dict["image_url"] = local_link
                    except Exception as e:
                        temp_dict["image_url"] = ""

                    unit_proforma_invoice_list.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchPIFormAPI: %s at %s", e, str(exc_tb.tb_lineno))        
            
            total_quantity = unit_proforma_invoice_objs.aggregate(Sum('quantity'))["quantity__sum"]
            total_amount = round(total_amount, 2)
            p = inflect.engine()
            total_amount_in_words = p.number_to_words(total_amount)
            response["total_quantity"] = str(total_quantity)
            response["total_amount"] = str(total_amount)
            response["total_amount_in_words"] = str(total_amount_in_words)
            
            response["unit_proforma_invoice_list"] = unit_proforma_invoice_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchPIFormAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SavePIFormAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500

        try:

            data = request.data
            logger.info("SavePIFormAPI: %s", str(data))
            if not isinstance(data, dict):
                data = json.loads(data)

            proforma_invoice_obj = ProformaInvoice.objects.get(uuid=data["uuid"])
            factory_obj = proforma_invoice_obj.factory

            proforma_invoice_obj.discharge_port = data["discharge_port"]
            proforma_invoice_obj.vessel_details = data["vessel_details"]
            proforma_invoice_obj.vessel_final_destination = data["vessel_final_destination"]
            proforma_invoice_obj.payment_terms = data["payment_terms"]
            proforma_invoice_obj.inco_terms = data["inco_terms"]
            proforma_invoice_obj.delivery_terms = data["delivery_terms"]
            proforma_invoice_obj.ship_lot_number = data["shipment_lot_number"]
            proforma_invoice_obj.invoice_number = data["invoice_number"]
            #proforma_invoice_obj.invoice_date = data["invoice_date"]
            proforma_invoice_obj.important_notes = data["important_notes"]
            proforma_invoice_obj.terms_and_condition = data["terms_and_condition"]
            proforma_invoice_obj.save()
            
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SavePIFormAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


FetchFactoryList = FetchFactoryListAPI.as_view()

FetchFactoryDetails = FetchFactoryDetailsAPI.as_view() 

FetchProductListingForPI = FetchProductListingForPIAPI.as_view()

SaveFactoryDetails = SaveFactoryDetailsAPI.as_view()

UploadFactoryImages = UploadFactoryImagesAPI.as_view()

DownloadBulkPI = DownloadBulkPIAPI.as_view()

FetchProformaBundleList = FetchProformaBundleListAPI.as_view()

FetchPIFactoryList = FetchPIFactoryListAPI.as_view()

UploadFactoryPI = UploadFactoryPIAPI.as_view()

FetchPIForm = FetchPIFormAPI.as_view()

SavePIForm = SavePIFormAPI.as_view()