from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
import sys

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
from django.db.models import Q
from django.db.models import Count
from django.conf import settings

from PIL import Image as IMage
import StringIO
from django.core.files.uploadedfile import InMemoryUploadedFile

import barcode
from barcode.writer import ImageWriter

import requests
import json
import os
import xlrd
import csv
import datetime
import boto3
import urllib2
import logging

from WAMSApp.models import Product

logger = logging.getLogger(__name__)


class CsrfExemptSessionAuthentication(SessionAuthentication):

    def enforce_csrf(self, request):
        return


def Login(request):
    return render(request, 'WAMSApp/login.html')


@login_required(login_url='/login/')
def Logout(request):
    logout(request)
    return HttpResponseRedirect('/login/')


@login_required(login_url='/login/')
def EditProductPage(request, pk):
    return render(request, 'WAMSApp/edit-product-page.html')


@login_required(login_url='/login/')
def Products(request):
    return render(request, 'WAMSApp/products.html')


@login_required(login_url='/login/')
def ExportListPage(request):
    return render(request, 'WAMSApp/export-list.html')


def RedirectHome(request):
    return HttpResponseRedirect('/products/')


@login_required(login_url='/login/')
def PFLPage(request, pk):
    return render(request, 'WAMSApp/pfl.html')


@login_required(login_url='/login/')
def PFLDashboardPage(request):
    return render(request, 'WAMSApp/pfl-dashboard.html')


@login_required(login_url='/login/')
def FlyerPage(request, pk):
    return render(request, 'WAMSApp/flyer.html')


@login_required(login_url='/login/')
def FlyerDashboardPage(request):
    return render(request, 'WAMSApp/flyer-dashboard.html')


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


class FetchConstantValuesAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchConstantValuesAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            category_list = []
            category_objs = Category.objects.all()
            for category_obj in category_objs:
                temp_dict = {}
                temp_dict["name"] = category_obj.name
                temp_dict["pk"] = category_obj.pk
                category_list.append(temp_dict)

            material_list = []
            material_objs = MaterialType.objects.all()
            for material_obj in material_objs:
                temp_dict = {}
                temp_dict["name"] = material_obj.name
                temp_dict["pk"] = material_obj.pk
                material_list.append(temp_dict)

            brand_list = []
            brand_objs = Brand.objects.all()
            for brand_obj in brand_objs:
                temp_dict = {}
                temp_dict["name"] = brand_obj.name
                temp_dict["pk"] = brand_obj.pk
                brand_list.append(temp_dict)

            product_id_type_list = []
            product_id_type_objs = ProductIDType.objects.all()
            for product_id_type_obj in product_id_type_objs:
                temp_dict = {}
                temp_dict["name"] = product_id_type_obj.name
                temp_dict["pk"] = product_id_type_obj.pk
                product_id_type_list.append(temp_dict)

            response["category_list"] = category_list
            response["material_list"] = material_list
            response["brand_list"] = brand_list
            response["product_id_type_list"] = product_id_type_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchConstantValuesAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CreateNewProductAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if request.user.has_perm('WAMSApp.add_product') == False:
                logger.warning("CreateNewProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("CreateNewProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_name = convert_to_ascii(data["product_name"])
            seller_sku = convert_to_ascii(data["seller_sku"])

            if Product.objects.filter(seller_sku=seller_sku).exists():
                # Duplicate product detected!
                response["status"] = 409 
                return Response(data=response)

            prod_obj = Product.objects.create(product_name_amazon_uk=product_name,
                                              product_name_sap=product_name,
                                              product_name_amazon_uae=product_name,
                                              product_name_ebay=product_name,
                                              pfl_product_name=product_name,
                                              product_id=seller_sku,
                                              seller_sku=seller_sku)


            response["product_pk"] = prod_obj.pk
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateNewProductAPI: %s at %s",
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

            prod_obj = Product.objects.get(pk=data["pk"])

            brand_obj = prod_obj.brand

            response["pfl_product_name"] = prod_obj.pfl_product_name
            try:
                response["pfl_product_features"] = json.loads(
                    prod_obj.pfl_product_features)
            except Exception as e:
                response["pfl_product_features"] = []
            
            try:
                response["brand_logo"] = brand_obj.logo.image.url
            except Exception as e:
                response["brand_logo"] = ''
            
            try:
                response["barcode_string"] = prod_obj.barcode_string
            except Exception as e:
                response["barcode_string"] = ''
            
            response["product_name_amazon_uk"] = prod_obj.product_name_amazon_uk
            response["product_name_amazon_uae"] = prod_obj.product_name_amazon_uae
            response["product_name_ebay"] = prod_obj.product_name_ebay
            response["product_name_sap"] = prod_obj.product_name_sap
            response["category"] = prod_obj.category
            response["subtitle"] = prod_obj.subtitle

            if prod_obj.brand == None:
                response["brand"] = ""
            else:
                response["brand"] = prod_obj.brand.name

            response["manufacturer"] = prod_obj.manufacturer
            response["product_id"] = prod_obj.product_id
            response["product_id_type"] = prod_obj.product_id_type
            response["seller_sku"] = prod_obj.seller_sku
            response["manufacturer_part_number"] = prod_obj.manufacturer_part_number
            response["condition_type"] = prod_obj.condition_type
            response["feed_product_type"] = prod_obj.feed_product_type
            response["update_delete"] = prod_obj.update_delete
            response["recommended_browse_nodes"] = prod_obj.recommended_browse_nodes
            response["product_description_amazon_uk"] = prod_obj.product_description_amazon_uk
            response["product_description_amazon_uae"] = prod_obj.product_description_amazon_uae
            response["product_description_ebay"] = prod_obj.product_description_ebay
            response["product_attribute_list_amazon_uk"] = json.loads(
                prod_obj.product_attribute_list_amazon_uk)
            response["product_attribute_list_amazon_uae"] = json.loads(
                prod_obj.product_attribute_list_amazon_uae)
            response["product_attribute_list_ebay"] = json.loads(
                prod_obj.product_attribute_list_ebay)
            response["search_terms"] = prod_obj.search_terms
            response["color_map"] = prod_obj.color_map
            response["color"] = prod_obj.color
            response["enclosure_material"] = prod_obj.enclosure_material
            response["cover_material_type"] = prod_obj.cover_material_type
            response["special_features"] = json.loads(
                prod_obj.special_features)
            
            response["package_length"] = "" if prod_obj.package_length==None else prod_obj.package_length
            response["package_length_metric"] = prod_obj.package_length_metric
            response["package_width"] = "" if prod_obj.package_width==None else prod_obj.package_width
            response["package_width_metric"] = prod_obj.package_width_metric
            response["package_height"] = "" if prod_obj.package_height==None else prod_obj.package_height
            response["package_height_metric"] = prod_obj.package_height_metric
            response["package_weight"] = "" if prod_obj.package_weight==None else prod_obj.package_weight
            response["package_weight_metric"] = prod_obj.package_weight_metric
            response["shipping_weight"] = "" if prod_obj.shipping_weight==None else prod_obj.shipping_weight
            response["shipping_weight_metric"] = prod_obj.shipping_weight_metric
            response["item_display_weight"] = "" if prod_obj.item_display_weight==None else prod_obj.item_display_weight
            response[
                "item_display_weight_metric"] = prod_obj.item_display_weight_metric
            response["item_display_volume"] = "" if prod_obj.item_display_volume==None else prod_obj.item_display_volume
            response[
                "item_display_volume_metric"] = prod_obj.item_display_volume_metric
            response["item_display_length"] = "" if prod_obj.item_display_length==None else prod_obj.item_display_length
            response[
                "item_display_length_metric"] = prod_obj.item_display_length_metric
            response["item_weight"] = "" if prod_obj.item_weight==None else prod_obj.item_weight
            response["item_weight_metric"] = prod_obj.item_weight_metric
            response["item_length"] = "" if prod_obj.item_length==None else prod_obj.item_length
            response["item_length_metric"] = prod_obj.item_length_metric
            response["item_width"] = "" if prod_obj.item_width==None else prod_obj.item_width
            response["item_width_metric"] = prod_obj.item_width_metric
            response["item_height"] = "" if prod_obj.item_height==None else prod_obj.item_height
            response["item_height_metric"] = prod_obj.item_height_metric
            response["item_display_width"] = "" if prod_obj.item_display_width==None else prod_obj.item_display_width
            response[
                "item_display_width_metric"] = prod_obj.item_display_width_metric
            response["item_display_height"] = "" if prod_obj.item_display_height==None else prod_obj.item_display_height
            response[
                "item_display_height_metric"] = prod_obj.item_display_height_metric
            
            response["item_condition_note"] = prod_obj.item_condition_note
            response["max_order_quantity"] = "" if prod_obj.max_order_quantity==None else prod_obj.max_order_quantity
            response["number_of_items"] = "" if prod_obj.number_of_items==None else prod_obj.number_of_items
            response["wattage"] = "" if prod_obj.wattage==None else prod_obj.wattage
            response["wattage_metric"] = prod_obj.wattage_metric
            response["material_type"] = prod_obj.material_type
            response["parentage"] = prod_obj.parentage
            response["parent_sku"] = prod_obj.parent_sku
            response["relationship_type"] = prod_obj.relationship_type
            response["variation_theme"] = prod_obj.variation_theme
            response["standard_price"] = "" if prod_obj.standard_price==None else prod_obj.standard_price
            response["quantity"] = "" if prod_obj.quantity==None else prod_obj.quantity
            response["sale_price"] = "" if prod_obj.sale_price==None else prod_obj.sale_price
            response["sale_from"] = "" if prod_obj.sale_from==None else prod_obj.sale_from
            response["sale_end"] = "" if prod_obj.sale_end==None else prod_obj.sale_end

            response["verified"] = prod_obj.verified

            images = {}

            images["main_images"] = create_response_images_main(
                prod_obj.main_images.all())
            images["sub_images"] = create_response_images_sub(
                prod_obj.sub_images.all())
            images["pfl_images"] = create_response_images(
                prod_obj.pfl_images.all())
            images["pfl_generated_images"] = create_response_images(
                prod_obj.pfl_generated_images.all())
            images["white_background_images"] = create_response_images(
                prod_obj.white_background_images.all())
            images["lifestyle_images"] = create_response_images(
                prod_obj.lifestyle_images.all())
            images["certificate_images"] = create_response_images(
                prod_obj.certificate_images.all())
            images["giftbox_images"] = create_response_images(
                prod_obj.giftbox_images.all())
            images["diecut_images"] = create_response_images(
                prod_obj.diecut_images.all())
            images["aplus_content_images"] = create_response_images(
                prod_obj.aplus_content_images.all())
            images["ads_images"] = create_response_images(
                prod_obj.ads_images.all())
            images["unedited_images"] = create_response_images(
                prod_obj.unedited_images.all())

            repr_image_url = Config.objects.all()[0].product_404_image.image.url
            repr_high_def_url = repr_image_url
            if prod_obj.main_images.filter(is_main_image=True).count()>0:
                repr_image_url = prod_obj.main_images.filter(is_main_image=True)[0].image.mid_image.url
                repr_high_def_url = prod_obj.main_images.filter(is_main_image=True)[0].image.image.url

            response["repr_image_url"] = repr_image_url
            response["repr_high_def_url"] = repr_high_def_url

            pfl_pk = None
            if PFL.objects.filter(product=prod_obj).exists() == False:
                pfl_obj = PFL.objects.create(product=prod_obj)
                pfl_pk = pfl_obj.pk
            else:
                pfl_obj = PFL.objects.filter(product=prod_obj)[0]
                pfl_pk = pfl_obj.pk

            response["pfl_pk"] = pfl_pk

            response["images"] = images
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


def decode_base64_file(data):

    def get_file_extension(file_name, decoded_file):
        import imghdr

        extension = imghdr.what(file_name, decoded_file)
        extension = "jpg" if extension == "jpeg" else extension

        return extension

    from django.core.files.base import ContentFile
    import base64
    import six
    import uuid

    # Check if this is a base64 string
    if isinstance(data, six.string_types):
        # Check if the base64 string is in the "data:" format
        if 'data:' in data and ';base64,' in data:
            # Break out the header from the base64 content
            header, data = data.split(';base64,')

        # Try to decode the file. Return validation error if it fails.
        try:
            decoded_file = base64.b64decode(data)
        except TypeError:
            TypeError('invalid_image')

        # Generate file name:
        # 12 characters are more than enough.
        file_name = str(uuid.uuid4())[:12]
        # Get the file name extension:
        file_extension = get_file_extension(file_name, decoded_file)

        complete_file_name = "%s.%s" % (file_name, file_extension, )

        return ContentFile(decoded_file, name=complete_file_name)


class SaveProductAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            if request.user.has_perm('WAMSApp.change_product') == False:
                logger.warning("SaveProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("SaveProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            # Check for duplicate
            product_id = data["product_id"]
            seller_sku = data["seller_sku"]
            prod_obj = Product.objects.get(pk=int(data["product_pk"]))
            if Product.objects.filter(product_id=product_id).exclude(pk=data["product_pk"]).count()==1 or Product.objects.filter(seller_sku=seller_sku).exclude(pk=data["product_pk"]).count()==1:
                logger.warning("Duplicate product detected!")
                response['status'] = 409
                return Response(data=response)


            product_name_amazon_uk = convert_to_ascii(data["product_name_amazon_uk"])
            product_name_amazon_uae = convert_to_ascii(data["product_name_amazon_uae"])
            product_name_ebay = convert_to_ascii(data["product_name_ebay"])
            product_name_sap = convert_to_ascii(data["product_name_sap"])
            category = data["category"]
            subtitle = convert_to_ascii(data["subtitle"])
            brand = data["brand"]
            manufacturer = data["manufacturer"]
            product_id_type = data["product_id_type"]
            manufacturer_part_number = data["manufacturer_part_number"]
            barcode_string = data["barcode_string"]
            condition_type = data["condition_type"]
            feed_product_type = data["feed_product_type"]
            update_delete = data["update_delete"]
            recommended_browse_nodes = data["recommended_browse_nodes"]
            product_description_amazon_uk = convert_to_ascii(data["product_description_amazon_uk"])
            if product_description_amazon_uk=="<p>&nbsp;</p>":
                product_description_amazon_uk = ""

            product_description_amazon_uae = convert_to_ascii(data["product_description_amazon_uae"])
            if product_description_amazon_uae=="<p>&nbsp;</p>":
                product_description_amazon_uae = ""

            product_description_ebay = convert_to_ascii(data["product_description_ebay"])
            if product_description_ebay=="<p>&nbsp;</p>":
                product_description_ebay = ""

            product_attribute_list_amazon_uk = convert_to_ascii(data[
                "product_attribute_list_amazon_uk"])
            product_attribute_list_amazon_uae = convert_to_ascii(data[
                "product_attribute_list_amazon_uae"])
            product_attribute_list_ebay = convert_to_ascii(data["product_attribute_list_ebay"])
            search_terms = data["search_terms"]
            color_map = data["color_map"]
            color = data["color"]
            enclosure_material = data["enclosure_material"]
            cover_material_type = data["cover_material_type"]
            special_features = convert_to_ascii(data["special_features"])
            package_length = None if data[
                "package_length"] == "" else float(data["package_length"])
            package_length_metric = data["package_length_metric"]
            package_width = None if data[
                "package_width"] == "" else float(data["package_width"])
            package_width_metric = data["package_width_metric"]
            package_height = None if data[
                "package_height"] == "" else float(data["package_height"])
            package_height_metric = data["package_height_metric"]
            package_weight = None if data[
                "package_weight"] == "" else float(data["package_weight"])
            package_weight_metric = data["package_weight_metric"]
            shipping_weight = None if data[
                "shipping_weight"] == "" else float(data["shipping_weight"])
            shipping_weight_metric = data["shipping_weight_metric"]
            item_display_weight = None if data[
                "item_display_weight"] == "" else float(data["item_display_weight"])
            item_display_weight_metric = data["item_display_weight_metric"]
            item_display_volume = None if data[
                "item_display_volume"] == "" else float(data["item_display_volume"])
            item_display_volume_metric = data["item_display_volume_metric"]
            item_display_length = None if data[
                "item_display_length"] == "" else float(data["item_display_length"])
            item_display_length_metric = data["item_display_length_metric"]
            item_weight = None if data[
                "item_weight"] == "" else float(data["item_weight"])
            item_weight_metric = data["item_weight_metric"]
            item_length = None if data[
                "item_length"] == "" else float(data["item_length"])
            item_length_metric = data["item_length_metric"]
            item_width = None if data[
                "item_width"] == "" else float(data["item_width"])
            item_width_metric = data["item_width_metric"]
            item_height = None if data[
                "item_height"] == "" else float(data["item_height"])
            item_height_metric = data["item_height_metric"]
            item_display_width = None if data[
                "item_display_width"] == "" else float(data["item_display_width"])
            item_display_width_metric = data["item_display_width_metric"]
            item_display_height = None if data[
                "item_display_height"] == "" else float(data["item_display_height"])
            item_display_height_metric = data["item_display_height_metric"]
            item_condition_note = convert_to_ascii(data["item_condition_note"])
            max_order_quantity = None if data[
                "max_order_quantity"] == "" else int(data["max_order_quantity"])
            number_of_items = None if data[
                "number_of_items"] == "" else int(data["number_of_items"])
            wattage = None if data["wattage"] == "" else float(data["wattage"])
            wattage_metric = data["wattage_metric"]
            material_type = data["material_type"]
            parentage = data["parentage"]
            parent_sku = data["parent_sku"]
            relationship_type = data["relationship_type"]
            variation_theme = data["variation_theme"]
            standard_price = None if data[
                "standard_price"] == "" else float(data["standard_price"])
            quantity = None if data["quantity"] == "" else int(data["quantity"])
            sale_price = None if data[
                "sale_price"] == "" else float(data["sale_price"])
            sale_from = None if data["sale_from"] == "" else data["sale_from"]
            sale_end = None if data["sale_end"] == "" else data["sale_end"]

            pfl_product_name = convert_to_ascii(data["pfl_product_name"])
            pfl_product_features = convert_to_ascii(data["pfl_product_features"])


            brand_obj = None
            if brand != "":
                brand_obj, created = Brand.objects.get_or_create(name=brand)

            prod_obj.product_id = product_id

            try:
                if prod_obj.barcode_string != barcode_string and barcode_string!="":
                    EAN = barcode.ean.EuropeanArticleNumber13(
                        str(barcode_string), writer=ImageWriter())
                    thumb = EAN.save('temp_image')

                    thumb = IMage.open(open(thumb, "rb"))

                    thumb_io = StringIO.StringIO()
                    thumb.save(thumb_io, format='PNG')

                    thumb_file = InMemoryUploadedFile(
                        thumb_io, None, 'barcode_' + prod_obj.product_id + '.png', 'image/PNG', thumb_io.len, None)

                    barcode_image = Image.objects.create(image=thumb_file)
                    prod_obj.barcode = barcode_image
                    prod_obj.barcode_string = barcode_string

                    try:
                        import os
                        os.remove("temp_image.png")
                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        logger.warning("SaveProductAPI: %s at %s",
                                       e, str(exc_tb.tb_lineno))

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SaveProductAPI: %s at %s", e, str(exc_tb.tb_lineno))

            # try:
            #     image_decoded = decode_base64_file(data["image_data"])
            #     image_obj = Image.objects.create(image=image_decoded)
            #     prod_obj.pfl_generated_images.clear()
            #     prod_obj.pfl_generated_images.add(image_obj)
            # except Exception as e:
            #     exc_type, exc_obj, exc_tb = sys.exc_info()
            #     logger.error("SaveProductAPI: %s at %s", e, str(exc_tb.tb_lineno))

            prod_obj.product_name_amazon_uk = product_name_amazon_uk
            prod_obj.product_name_amazon_uae = product_name_amazon_uae
            prod_obj.product_name_ebay = product_name_ebay
            prod_obj.product_name_sap = product_name_sap

            prod_obj.category = category
            prod_obj.subtitle = subtitle
            prod_obj.brand = brand_obj
            prod_obj.manufacturer = manufacturer
            prod_obj.product_id_type = product_id_type
            prod_obj.seller_sku = seller_sku
            prod_obj.manufacturer_part_number = manufacturer_part_number
            prod_obj.condition_type = condition_type
            prod_obj.feed_product_type = feed_product_type
            prod_obj.update_delete = update_delete
            prod_obj.recommended_browse_nodes = recommended_browse_nodes
            prod_obj.product_description_amazon_uk = product_description_amazon_uk
            prod_obj.product_description_amazon_uae = product_description_amazon_uae
            prod_obj.product_description_ebay = product_description_ebay
            prod_obj.product_attribute_list_amazon_uk = product_attribute_list_amazon_uk
            prod_obj.product_attribute_list_amazon_uae = product_attribute_list_amazon_uae
            prod_obj.product_attribute_list_ebay = product_attribute_list_ebay
            prod_obj.search_terms = search_terms
            prod_obj.color_map = color_map
            prod_obj.color = color
            prod_obj.enclosure_material = enclosure_material
            prod_obj.cover_material_type = cover_material_type
            prod_obj.special_features = special_features
            prod_obj.package_length = package_length
            prod_obj.package_length_metric = package_length_metric
            prod_obj.package_width = package_width
            prod_obj.package_width_metric = package_width_metric
            prod_obj.package_height = package_height
            prod_obj.package_height_metric = package_height_metric
            prod_obj.package_weight = package_weight
            prod_obj.package_weight_metric = package_weight_metric
            prod_obj.shipping_weight = shipping_weight
            prod_obj.shipping_weight_metric = shipping_weight_metric
            prod_obj.item_display_weight = item_display_weight
            prod_obj.item_display_weight_metric = item_display_weight_metric
            prod_obj.item_display_volume = item_display_volume
            prod_obj.item_display_volume_metric = item_display_volume_metric
            prod_obj.item_display_length = item_display_length
            prod_obj.item_display_length_metric = item_display_length_metric
            prod_obj.item_weight = item_weight
            prod_obj.item_weight_metric = item_weight_metric
            prod_obj.item_length = item_length
            prod_obj.item_length_metric = item_length_metric
            prod_obj.item_width = item_width
            prod_obj.item_width_metric = item_width_metric
            prod_obj.item_height = item_height
            prod_obj.item_height_metric = item_height_metric
            prod_obj.item_display_width = item_display_width
            prod_obj.item_display_width_metric = item_display_width_metric
            prod_obj.item_display_height = item_display_height
            prod_obj.item_display_height_metric = item_display_height_metric
            prod_obj.item_condition_note = item_condition_note
            prod_obj.max_order_quantity = max_order_quantity
            prod_obj.number_of_items = number_of_items
            prod_obj.wattage = wattage
            prod_obj.wattage_metric = wattage_metric
            prod_obj.material_type = material_type
            prod_obj.parentage = parentage
            prod_obj.parent_sku = parent_sku
            prod_obj.relationship_type = relationship_type
            prod_obj.variation_theme = variation_theme
            prod_obj.standard_price = standard_price
            prod_obj.quantity = quantity
            prod_obj.sale_price = sale_price
            prod_obj.sale_from = sale_from
            prod_obj.sale_end = sale_end

            prod_obj.pfl_product_name = pfl_product_name
            prod_obj.pfl_product_features = pfl_product_features

            prod_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveProductAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchProductListAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchProductListAPI: %s", str(data))

            filter_parameters = json.loads(data['filter_parameters'])
            chip_data = json.loads(data['tags'])

            page = int(data['page'])
            search_list_objs = []
            product_objs_list = []
            if filter_parameters['verified']:
                product_objs_list = Product.objects.filter(
                    verified=filter_parameters['verified']).order_by('-pk')
            else:
                product_objs_list = Product.objects.all().order_by('-pk')

            if filter_parameters["start_date"] != "" and filter_parameters["end_date"] != "":
                start_date = datetime.datetime.strptime(
                    filter_parameters["start_date"], "%b %d, %Y")
                end_date = datetime.datetime.strptime(
                    filter_parameters["end_date"], "%b %d, %Y")
                product_objs_list = product_objs_list.filter(
                    created_date__gte=start_date).filter(created_date__lte=end_date)

            if filter_parameters["brand_pk"] != "":
                brand_obj = Brand.objects.get(pk=filter_parameters["brand_pk"])
                product_objs_list = product_objs_list.filter(brand=brand_obj)

            if filter_parameters["min_price"] != "":
                product_objs_list = product_objs_list.filter(
                    standard_price__gte=int(filter_parameters["min_price"]))

            if filter_parameters["max_price"] != "":
                product_objs_list = product_objs_list.filter(
                    standard_price__lte=int(filter_parameters["max_price"]))

            if filter_parameters["has_image"] == "1":
                product_objs_list = product_objs_list.annotate(
                    num_main_images=Count('main_images'),
                    num_pfl_images=Count('pfl_images'),
                    num_sub_images=Count('sub_images'),
                    num_white_background_images=Count(
                        'white_background_images'),
                    num_lifestyle_images=Count('lifestyle_images'),
                    num_certificate_images=Count('certificate_images'),
                    num_giftbox_images=Count('giftbox_images'),
                    num_diecut_images=Count('diecut_images'),
                    num_aplus_content_images=Count('aplus_content_images'),
                    num_ads_images=Count('ads_images'),
                    num_unedited_images=Count('unedited_images'),
                    num_pfl_generated_images=Count('pfl_generated_images')).exclude(num_main_images=0,
                                                                                    num_pfl_images=0,
                                                                                    num_sub_images=0,
                                                                                    num_white_background_images=0,
                                                                                    num_lifestyle_images=0,
                                                                                    num_certificate_images=0,
                                                                                    num_giftbox_images=0,
                                                                                    num_diecut_images=0,
                                                                                    num_aplus_content_images=0,
                                                                                    num_ads_images=0,
                                                                                    num_unedited_images=0,
                                                                                    num_pfl_generated_images=0)
            if filter_parameters["has_image"] == "2":
                product_objs_list = product_objs_list.annotate(
                    num_main_images=Count('main_images'),
                    num_pfl_images=Count('pfl_images'),
                    num_sub_images=Count('sub_images'),
                    num_white_background_images=Count(
                        'white_background_images'),
                    num_lifestyle_images=Count('lifestyle_images'),
                    num_certificate_images=Count('certificate_images'),
                    num_giftbox_images=Count('giftbox_images'),
                    num_diecut_images=Count('diecut_images'),
                    num_aplus_content_images=Count('aplus_content_images'),
                    num_ads_images=Count('ads_images'),
                    num_unedited_images=Count('unedited_images'),
                    num_pfl_generated_images=Count('pfl_generated_images')).exclude(num_main_images__gt=0).exclude(num_pfl_images__gt=0).exclude(num_sub_images__gt=0).exclude(num_white_background_images__gt=0).exclude(num_lifestyle_images__gt=0).exclude(num_certificate_images__gt=0).exclude(num_giftbox_images__gt=0).exclude(num_diecut_images__gt=0).exclude(num_aplus_content_images__gt=0).exclude(num_ads_images__gt=0).exclude(num_unedited_images__gt=0).exclude(num_pfl_generated_images__gt=0)

            if len(chip_data) == 0:
                search_list_objs = product_objs_list
            else:
                for tag in chip_data:
                    search = product_objs_list.filter(
                        Q(product_name_sap__icontains=tag) |
                        Q(product_name_amazon_uk__icontains=tag) |
                        Q(product_name_amazon_uae__icontains=tag) |
                        Q(product_name_ebay__icontains=tag) |
                        Q(product_id__icontains=tag) |
                        Q(seller_sku__icontains=tag)
                    )
                    for prod in search:
                        search_list_objs.append(prod)

            paginator = Paginator(search_list_objs, 20)
            product_objs = paginator.page(page)

            products = []
            for product_obj in product_objs:
                temp_dict = {}
                temp_dict["product_name_amazon_uk"] = product_obj.product_name_amazon_uk
                temp_dict["product_id"] = product_obj.product_id
                temp_dict["seller_sku"] = product_obj.seller_sku
                temp_dict["created_date"] = str(product_obj.created_date.strftime("%d %b, %Y"))
                temp_dict["status"] = product_obj.status
                temp_dict["product_pk"] = product_obj.pk
                
                if product_obj.main_images.filter(is_main_image=True).count() > 0:
                    try:
                        temp_dict["main_image"] = product_obj.main_images.filter(is_main_image=True)[0].image.thumbnail.url
                    except Exception as e:
                        temp_dict["main_image"] = Config.objects.all()[0].product_404_image.image.url
                else:
                    temp_dict["main_image"] = Config.objects.all()[0].product_404_image.image.url

                if product_obj.brand != None:
                    temp_dict["brand"] = product_obj.brand.name
                else:
                    temp_dict["brand"] = "-"

                products.append(temp_dict)
            is_available = True
            if paginator.num_pages == page:
                is_available = False

            response["is_available"] = is_available
            response["total_products"] = len(search_list_objs)
            response["products"] = products
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchExportListAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchExportListAPI: %s", str(data))

            chip_data = json.loads(data.get('tags', '[]'))

            search_list_objs = []
            export_list_objs = []

            if data.get("start_date", "") != "" and data.get("end_date", "") != "":
                start_date = datetime.datetime.strptime(
                    data["start_date"], "%b %d, %Y")
                end_date = datetime.datetime.strptime(
                    data["end_date"], "%b %d, %Y")
                export_list_objs = ExportList.objects.filter(
                    created_date__gte=start_date).filter(created_date__lte=end_date).filter(user=request.user)
            else:
                export_list_objs = ExportList.objects.all().filter(user=request.user)

            if len(chip_data) == 0:
                search_list_objs = export_list_objs
            else:
                for export_list in export_list_objs:
                    for product in export_list.products.all():
                        flag = 0
                        for chip in chip_data:
                            if chip.lower() in export_list.title.lower():
                                search_list_objs.append(export_list)
                                flag = 1
                                break
                            if (chip.lower() in product.product_name_sap.lower() or
                                    chip.lower() in product.product_name_amazon_uk.lower() or
                                    chip.lower() in product.product_name_amazon_uae.lower() or
                                    chip.lower() in product.product_name_ebay.lower() or
                                    chip.lower() in product.product_id.lower() or
                                    chip.lower() in product.seller_sku.lower()):
                                search_list_objs.append(export_list)
                                flag = 1
                                break
                        if flag == 1:
                            break

            export_list = []
            for export_list_obj in search_list_objs:
                temp_dict = {}
                temp_dict["title"] = export_list_obj.title
                temp_dict["created_date"] = str(
                    export_list_obj.created_date.strftime("%d %b, %Y"))
                temp_dict["pk"] = export_list_obj.pk
                temp_dict[
                    "product_count"] = export_list_obj.products.all().count()
                export_list.append(temp_dict)

            response["export_list"] = export_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchExportListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddToExportAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            if request.user.has_perm('WAMSApp.change_exportlist') == False:
                logger.warning("AddToExportAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("AddToExportAPI: %s", str(data))

            export_option = data["export_option"]
            export_title_pk = data["export_title_pk"]
            export_title = convert_to_ascii(data["export_title"])
            products = json.loads(data["products"])

            export_obj = None
            if export_option == "New":
                export_obj = ExportList.objects.create(title=export_title, user=request.user)
            else:
                export_obj = ExportList.objects.get(pk=int(export_title_pk))

            for product_pk in products:
                product = Product.objects.get(pk=int(product_pk))
                export_obj.products.add(product)
                export_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddToExportAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchExportProductListAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchExportProductListAPI: %s", str(data))

            export_obj = ExportList.objects.get(pk=int(data["export_pk"]))
            products = export_obj.products.all()

            product_list = []
            for product in products:
                temp_dict = {}
                temp_dict["product_name_sap"] = product.product_name_sap
                temp_dict["product_id"] = product.product_id
                temp_dict["product_pk"] = product.pk
                if product.main_images.filter(is_main_image=True).count() > 0:
                    temp_dict['product_image_url'] = product.main_images.filter(is_main_image=True)[
                        0].image.mid_image.url
                else:
                    temp_dict['product_image_url'] = Config.objects.all()[
                        0].product_404_image.image.url

                product_list.append(temp_dict)

            response["product_list"] = product_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchExportProductListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DownloadExportListAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DownloadExportListAPI: %s", str(data))

            export_format = data["export_format"]

            export_obj = ExportList.objects.get(pk=int(data["export_pk"]))
            products = export_obj.products.all()

            if export_format == "Amazon UK":
                export_amazon_uk(products)
                response["file_path"] = "/files/csv/export-list-amazon-uk.xlsx"
            elif export_format == "Amazon UAE":
                export_amazon_uae(products)
                response["file_path"] = "/files/csv/export-list-amazon-uae.csv"

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DownloadExportListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class ImportProductsAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if request.user.has_perm('WAMSApp.change_product') == False:
                logger.warning("ImportProductsAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("ImportProductsAPI: %s", str(data))

            import_format = data["import_format"]
            import_rule = data["import_rule"]
            import_file = data["import_file"]

            if import_format == "Amazon UK":
                import_amazon_uk(import_rule, import_file)
            elif import_format == "Amazon UAE":
                import_amazon_uae(import_rule, import_file)

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ImportProductsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadProductImageAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if request.user.has_perm("WAMSApp.add_image") == False:
                logger.warning("UploadProductImageAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            #logger.info("UploadProductImageAPI: %s", str(data))

            prod_obj = Product.objects.get(pk=int(data["product_pk"]))

            image_objs = []

            image_count = int(data["image_count"])
            for i in range(image_count):
                image_obj = Image.objects.create(image=data["image_"+str(i)])
                image_objs.append(image_obj)

            if data["image_category"] == "main_images":

                for image_obj in image_objs:
                    image_bucket_obj = ImageBucket.objects.create(image=image_obj)
                    prod_obj.main_images.add(image_bucket_obj)

                if prod_obj.main_images.all().count()==image_count:
                    image_bucket_obj = prod_obj.main_images.all()[0]
                    image_bucket_obj.is_main_image = True
                    image_bucket_obj.save()
                    try:
                        pfl_obj = PFL.objects.filter(product=prod_obj)[0]
                        if pfl_obj.product_image==None:
                            pfl_obj.product_image = image_objs[0]
                            pfl_obj.save()
                    except Exception as e:
                        pass
                
            elif data["image_category"] == "sub_images":
                for image_obj in image_objs:
                    image_bucket_obj = ImageBucket.objects.create(image=image_obj)
                    prod_obj.sub_images.add(image_bucket_obj)
            elif data["image_category"] == "pfl_images":
                for image_obj in image_objs:
                    prod_obj.pfl_images.add(image_obj)
            elif data["image_category"] == "white_background_images":
                for image_obj in image_objs:
                    prod_obj.white_background_images.add(image_obj)
            elif data["image_category"] == "lifestyle_images":
                for image_obj in image_objs:
                    prod_obj.lifestyle_images.add(image_obj)
            elif data["image_category"] == "certificate_images":
                for image_obj in image_objs:
                    prod_obj.certificate_images.add(image_obj)
            elif data["image_category"] == "giftbox_images":
                for image_obj in image_objs:
                    prod_obj.giftbox_images.add(image_obj)
            elif data["image_category"] == "diecut_images":
                for image_obj in image_objs:
                    prod_obj.diecut_images.add(image_obj)
            elif data["image_category"] == "aplus_content_images":
                for image_obj in image_objs:
                    prod_obj.aplus_content_images.add(image_obj)
            elif data["image_category"] == "ads_images":
                for image_obj in image_objs:
                    prod_obj.ads_images.add(image_obj)
            elif data["image_category"] == "unedited_images":
                for image_obj in image_objs:
                    prod_obj.unedited_images.add(image_obj)

            prod_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadProductImageAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)

class UpdateMainImageAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if request.user.has_perm('WAMSApp.change_image') == False:
                logger.warning("UpdateMainImageAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("UpdateMainImageAPI: %s", str(data))

            product_obj = Product.objects.get(pk=int(data["product_pk"]))
            reset_main_images(product_obj)

            image_bucket_obj = ImageBucket.objects.get(
                pk=int(data["checked_pk"]))
            image_bucket_obj.is_main_image = True
            image_bucket_obj.save()

            try:
                pfl_obj = PFL.objects.filter(product=product_obj)[0]
                if pfl_obj.product_image==None:
                    pfl_obj.product_image = image_bucket_obj.image
                    pfl_obj.save()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("UpdateMainImageAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateMainImageAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UpdateSubImagesAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if request.user.has_perm('WAMSApp.change_image') == False:
                logger.warning("UpdateSubImagesAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)
            
            data = request.data
            logger.info("UpdateSubImagesAPI: %s", str(data))

            product_obj = Product.objects.get(pk=int(data["product_pk"]))
            reset_sub_images(product_obj)

            sub_images = json.loads(data["sub_images"])
            for sub_image in sub_images:
                sub_image_obj = ImageBucket.objects.get(
                    pk=int(sub_image["pk"]))
                if sub_image["sub_image_index"] != "" and sub_image["sub_image_index"] != "0":
                    sub_image_obj.sub_image_index = int(
                        sub_image["sub_image_index"])
                    sub_image_obj.is_sub_image = True
                else:
                    sub_image_obj.sub_image_index = 0
                    sub_image_obj.is_sub_image = False
                sub_image_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateSubImagesAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


#################################### FLyer Section #######################


class CreateFlyerAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if request.user.has_perm('WAMSApp.add_flyer') == False:
                logger.warning("CreateFlyerAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("CreateFlyerAPI: %s", str(data))

            row = int(data["row"])
            column = int(data["column"])
            brand_obj = Brand.objects.get(pk=int(data["brand_pk"]))

            empty_grid = []
            for k in range(row):
                temp_list = [{"image_url": None, "image_pk": None,
                              "product_title": None, "price": None} for l in range(column)]
                empty_grid.append(temp_list)

            template_data = {"row": row, "column": column, "data": empty_grid}

            flyer_obj = Flyer.objects.create(name=convert_to_ascii(data["name"]),
                                             template_data=json.dumps(
                                                 template_data),
                                             brand=brand_obj)

            # Read excel file and populate flyer
            if data["import_file"] != "undefined" and data["import_file"] != None and data["import_file"] != "":
                path = default_storage.save(
                    'tmp/temp-flyer.csv', data["import_file"])
                cnt = 1
                with open('./files/' + path, 'rt') as fr:
                    data = csv.reader(fr)
                    for rowd in data:
                        if cnt > 1:
                            product_obj = Product.objects.get(
                                product_id=rowd[0])
                            flyer_obj.product_bucket.add(product_obj)
                            main_image_obj = product_obj.main_images.filter(is_main_image=True)[
                                0]
                            product_title = rowd[1]
                            if product_title == "":
                                product_title = product_obj.product_name_amazon_uk

                            product_price = rowd[2]
                            if product_price == "":
                                product_price = product_obj.outdoor_price

                            i = (cnt - 2) / column
                            j = (cnt - 2) % column

                            template_data["data"][i][j] = {
                                "image_url": main_image_obj.image.image.url,
                                "image_pk": main_image_obj.image.pk,
                                "product_title": product_title,
                                "price": product_price
                            }
                        cnt += 1
                flyer_obj.template_data = json.dumps(template_data)
                flyer_obj.save()

            response["flyer_pk"] = flyer_obj.pk

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateFlyerAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchFlyerDetailsAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchFlyerDetailsAPI: %s", str(data))

            flyer_obj = Flyer.objects.get(pk=int(data["pk"]))

            name = flyer_obj.name
            product_bucket_objs = flyer_obj.product_bucket.all()
            product_bucket_list = []
            images_dict = {}
            for product_bucket_obj in product_bucket_objs:
                temp_dict = {}
                temp_dict[
                    "product_bucket_name"] = product_bucket_obj.product_name_sap
                temp_dict["product_bucket_pk"] = product_bucket_obj.pk
                temp_dict["seller_sku"] = product_bucket_obj.seller_sku
                main_image_url = None
                if product_bucket_obj.main_images.filter(is_main_image=True).count() > 0:
                    main_image_url = product_bucket_obj.main_images.filter(is_main_image=True)[
                        0].image.image.url
                else:
                    main_image_url = Config.objects.all()[0].product_404_image.image.url
                temp_dict["product_bucket_image_url"] = main_image_url

                images = {}

                images["main_images"] = create_response_images_flyer_pfl_main_sub(
                    product_bucket_obj.main_images.all())
                images["sub_images"] = create_response_images_flyer_pfl_main_sub(
                    product_bucket_obj.sub_images.all())
                images["pfl_images"] = create_response_images_flyer_pfl(
                    product_bucket_obj.pfl_images.all())
                images["white_background_images"] = create_response_images_flyer_pfl(
                    product_bucket_obj.white_background_images.all())
                images["lifestyle_images"] = create_response_images_flyer_pfl(
                    product_bucket_obj.lifestyle_images.all())
                images["certificate_images"] = create_response_images_flyer_pfl(
                    product_bucket_obj.certificate_images.all())
                images["giftbox_images"] = create_response_images_flyer_pfl(
                    product_bucket_obj.giftbox_images.all())
                images["diecut_images"] = create_response_images_flyer_pfl(
                    product_bucket_obj.diecut_images.all())
                images["aplus_content_images"] = create_response_images_flyer_pfl(
                    product_bucket_obj.aplus_content_images.all())
                images["ads_images"] = create_response_images_flyer_pfl(
                    product_bucket_obj.ads_images.all())
                images["unedited_images"] = create_response_images_flyer_pfl(
                    product_bucket_obj.unedited_images.all())

                images["all_images"] = images["main_images"]+images["sub_images"]+images["pfl_images"]+images["white_background_images"]+images["lifestyle_images"]+images["certificate_images"]+images["giftbox_images"]+images["diecut_images"]+images["aplus_content_images"]+images["ads_images"]+images["unedited_images"]

                images_dict[product_bucket_obj.pk] = images

                product_bucket_list.append(temp_dict)

            template_data = json.loads(flyer_obj.template_data)

            background_images_bucket = create_response_images_flyer_pfl(
                flyer_obj.background_images_bucket.all())

            external_images_bucket_list = []
            external_images_bucket_objs = flyer_obj.external_images_bucket.all()
            for external_images_bucket_obj in external_images_bucket_objs:
                temp_dict = {}
                temp_dict["image_url"] = external_images_bucket_obj.image.url
                temp_dict["image_pk"] = external_images_bucket_obj.pk
                external_images_bucket_list.append(temp_dict)

            brand_image_url = None
            try:
                brand_image_url = flyer_obj.brand.logo.image.url
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("FetchFlyerDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["flyer_name"] = name
            response["product_bucket_list"] = product_bucket_list
            response["template_data"] = template_data
            response["images"] = images_dict
            #response["external_images_bucket_list"] = external_images_bucket_list
            response["background_images_bucket"] = background_images_bucket
            response["brand_image_url"] = brand_image_url

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFlyerDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CreatePFLAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if request.user.has_perm('WAMSApp.add_pfl') == False:
                logger.warning("CreatePFLAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("CreatePFLAPI: %s", str(data))

            pfl_obj = PFL.objects.create(name=convert_to_ascii(data["name"]))

            response["pfl_pk"] = pfl_obj.pk
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreatePFLAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchPFLDetailsAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchPFLDetailsAPI: %s", str(data))

            pfl_obj = PFL.objects.get(pk=int(data["pk"]))

            pfl_name = pfl_obj.name
            product_image = {"image_url": None, "image_pk": None}
            try:
                product_image["image_url"] = pfl_obj.product_image.image.url
                product_image["image_pk"] = pfl_obj.product_image.pk
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning("FetchPFLDetailsAPI: %s at %s",
                               e, str(exc_tb.tb_lineno))

            pfl_product_features = []
            pfl_product_name = ""
            seller_sku = ""
            if pfl_obj.product != None:
                try:
                    pfl_product_features = json.loads(
                        pfl_obj.product.pfl_product_features)
                except Exception as e:
                    pfl_product_features = []

                pfl_product_name = pfl_obj.product.pfl_product_name
                seller_sku = pfl_obj.product.seller_sku

            external_images_bucket_list = []
            external_images_bucket_objs = pfl_obj.external_images_bucket.all()
            for external_images_bucket_obj in external_images_bucket_objs:
                temp_dict = {}
                temp_dict["image_url"] = external_images_bucket_obj.image.url
                temp_dict["image_pk"] = external_images_bucket_obj.pk
                external_images_bucket_list.append(temp_dict)

            logo_image_url = None
            barcode_image_url = None
            brand_name = None
            product_id = ""
            product_pk = None
            product_main_image_url = None
            product_name_sap = ""
            seller_sku = ""
            if pfl_obj.product != None:
                try:
                    brand_obj = pfl_obj.product.brand
                    brand_name = brand_obj.name
                    logo_image_url = brand_obj.logo.image.url
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.warning("FetchPFLDetailsAPI: %s at %s",
                                   e, str(exc_tb.tb_lineno))

                try:
                    barcode_image_url = pfl_obj.product.barcode.image.url
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.warning("FetchPFLDetailsAPI: %s at %s",
                                   e, str(exc_tb.tb_lineno))

                product_id = pfl_obj.product.product_id
                product_pk = pfl_obj.product.pk

                if pfl_obj.product.main_images.filter(is_main_image=True).count() > 0:
                    product_main_image_url = pfl_obj.product.main_images.filter(is_main_image=True)[
                        0].image.image.url
                else:
                    product_main_image_url = Config.objects.all()[0].product_404_image.image.url

                product_name_sap = pfl_obj.product.product_name_sap
                seller_sku = pfl_obj.product.seller_sku

            response["pfl_name"] = pfl_name
            response["product_name"] = pfl_product_name
            response["product_name_sap"] = product_name_sap
            response["product_image"] = product_image
            response["pfl_product_features"] = pfl_product_features
            response["external_images_bucket_list"] = external_images_bucket_list
            response["logo_image_url"] = logo_image_url
            response["brand_name"] = brand_name
            response["barcode_image_url"] = barcode_image_url
            response["product_id"] = product_id
            response["product_pk"] = product_pk
            response["product_main_image_url"] = product_main_image_url
            response["seller_sku"] = seller_sku

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchPFLDetailsAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchProductListFlyerPFLAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchProductListFlyerPFLAPI: %s", str(data))

            product_objs = Product.objects.all()

            try:
                if "flyer_pk" in data:
                    brand_obj = Flyer.objects.get(pk=int(data["flyer_pk"])).brand
                    product_objs = product_objs.filter(brand=brand_obj)
            except Exception as e:
                logger.warning("Issue with filtering brands %s", str(e))


            product_list = []
            cnt = 1
            for product_obj in product_objs:
                try:
                    temp_dict = {}
                    temp_dict["product_pk"] = product_obj.pk
                    temp_dict["product_name"] = product_obj.product_name_sap

                    temp_dict["product_name_autocomplete"] = str(
                        product_obj.product_name_sap) + " | " + str(product_obj.product_id)
                    main_image_url = None
                    if product_obj.main_images.filter(is_main_image=True).count() > 0:
                        try:
                            main_image_url = product_obj.main_images.filter(is_main_image=True)[
                                0].image.thumbnail.url
                        except Exception as e:
                            main_image_url = Config.objects.all()[0].product_404_image.image.url
                    else:
                        main_image_url = Config.objects.all()[0].product_404_image.image.url

                    temp_dict["main_image_url"] = main_image_url
                    product_list.append(temp_dict)
                except Exception as e:
                    cnt += 1
                    pass

            response["product_list"] = product_list

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductListFlyerPFLAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddProductFlyerBucketAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if request.user.has_perm('WAMSApp.change_flyer') == False:
                logger.warning("AddProductFlyerBucketAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("AddProductFlyerBucketAPI: %s", str(data))

            flyer_obj = Flyer.objects.get(pk=int(data["flyer_pk"]))

            product_id = data["product_name"].split("|")[-1].strip()
            product_obj = Product.objects.get(product_id=product_id)

            flyer_obj.product_bucket.add(product_obj)
            flyer_obj.save()

            image_url = Config.objects.all()[0].product_404_image.image.url
            if product_obj.main_images.filter(is_main_image=True).exists():
                image_url = product_obj.main_images.filter(
                    is_main_image=True)[0].image.image.url

            images = {}

            images["main_images"] = create_response_images_flyer_pfl_main_sub(
                product_obj.main_images.all())
            images["sub_images"] = create_response_images_flyer_pfl_main_sub(
                product_obj.sub_images.all())
            images["pfl_images"] = create_response_images_flyer_pfl(
                product_obj.pfl_images.all())
            images["white_background_images"] = create_response_images_flyer_pfl(
                product_obj.white_background_images.all())
            images["lifestyle_images"] = create_response_images_flyer_pfl(
                product_obj.lifestyle_images.all())
            images["certificate_images"] = create_response_images_flyer_pfl(
                product_obj.certificate_images.all())
            images["giftbox_images"] = create_response_images_flyer_pfl(
                product_obj.giftbox_images.all())
            images["diecut_images"] = create_response_images_flyer_pfl(
                product_obj.diecut_images.all())
            images["aplus_content_images"] = create_response_images_flyer_pfl(
                product_obj.aplus_content_images.all())
            images["ads_images"] = create_response_images_flyer_pfl(
                product_obj.ads_images.all())
            images["unedited_images"] = create_response_images_flyer_pfl(
                product_obj.unedited_images.all())

            images["all_images"] = images["main_images"]+images["sub_images"]+images["pfl_images"]+images["white_background_images"]+images["lifestyle_images"]+images["certificate_images"]+images["giftbox_images"]+images["diecut_images"]+images["aplus_content_images"]+images["ads_images"]+images["unedited_images"]

            response["images"] = images
            response["product_pk"] = product_obj.pk
            response["product_name"] = product_obj.product_name_sap
            response["product_image_url"] = image_url
            response["seller_sku"] = product_obj.seller_sku

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddProductFlyerBucketAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddProductPFLBucketAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if request.user.has_perm('WAMSApp.change_pfl') == False:
                logger.warning("AddProductPFLBucketAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("AddProductPFLBucketAPI: %s", str(data))

            pfl_obj = PFL.objects.get(pk=int(data["pfl_pk"]))
            
            product_id = data["product_name"].split("|")[1].strip()
            product_obj = Product.objects.get(product_id=product_id)

            pfl_obj.product = product_obj
            pfl_obj.save()

            seller_sku = product_obj.seller_sku
            image_url = None
            if product_obj.main_images.filter(is_main_image=True).count() > 0:
                image_url = product_obj.main_images.filter(
                    is_main_image=True)[0].image.image.url

            response["product_name"] = product_obj.product_name_sap
            response["product_pk"] = product_obj.pk
            response["image_url"] = image_url
            response["seller_sku"] = seller_sku

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddProductPFLBucketAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchProductDetailsFlyerPFLAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchProductDetailsFlyerPFLAPI: %s", str(data))

            pfl_obj = PFL.objects.get(pk=int(data["pfl_pk"]))
            product_obj = Product.objects.get(pk=int(data["product_pk"]))
            product_name = product_obj.product_name_sap
            product_price = product_obj.outdoor_price
            product_id = product_obj.product_id

            images = {}

            images["main_images"] = create_response_images_flyer_pfl_main_sub(
                product_obj.main_images.all())
            images["sub_images"] = create_response_images_flyer_pfl_main_sub(
                product_obj.sub_images.all())
            images["pfl_images"] = create_response_images_flyer_pfl(
                product_obj.pfl_images.all())
            images["white_background_images"] = create_response_images_flyer_pfl(
                product_obj.white_background_images.all())
            images["lifestyle_images"] = create_response_images_flyer_pfl(
                product_obj.lifestyle_images.all())
            images["certificate_images"] = create_response_images_flyer_pfl(
                product_obj.certificate_images.all())
            images["giftbox_images"] = create_response_images_flyer_pfl(
                product_obj.giftbox_images.all())
            images["diecut_images"] = create_response_images_flyer_pfl(
                product_obj.diecut_images.all())
            images["aplus_content_images"] = create_response_images_flyer_pfl(
                product_obj.aplus_content_images.all())
            images["ads_images"] = create_response_images_flyer_pfl(
                product_obj.ads_images.all())
            images["unedited_images"] = create_response_images_flyer_pfl(
                product_obj.unedited_images.all())
            images["pfl_generated_images"] = create_response_images_flyer_pfl(
                product_obj.pfl_generated_images.all())
            images["external_images"] = create_response_images_flyer_pfl(
                pfl_obj.external_images_bucket.all())

            barcode_image_url = None
            if product_obj.barcode != None:
                barcode_image_url = product_obj.barcode.image.url

            brand_obj = product_obj.brand
            brand_name = "" if brand_obj==None else brand_obj.name
            logo_image_url = ''
            logo_image_url = None

            try:
                logo_image_url = brand_obj.logo.image.url
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(
                    "FetchProductDetailsFlyerPFLAPI: %s at %s", e, str(exc_tb.tb_lineno))

            response["product_name"] = product_name
            response["product_id"] = product_id
            response["product_price"] = product_price
            response["images"] = images
            response["barcode_image_url"] = barcode_image_url
            response["brand_name"] = brand_name
            response["logo_image_url"] = logo_image_url
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchProductDetailsFlyerPFLAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveFlyerTemplateAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if request.user.has_perm('WAMSApp.change_flyer') == False:
                logger.warning("SaveFlyerTemplateAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("SaveFlyerTemplateAPI: %s", str(data))

            flyer_obj = Flyer.objects.get(pk=int(data["flyer_pk"]))
            flyer_obj.template_data = data["template_data"]
            flyer_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveFlyerTemplateAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SavePFLTemplateAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if request.user.has_perm('WAMSApp.change_pfl') == False:
                logger.warning("SavePFLTemplateAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("SavePFLTemplateAPI: %s", str(data))

            pfl_obj = PFL.objects.get(pk=int(data["pfl_pk"]))

            if data["image_pk"] != None and data["image_pk"] != "":
                image_obj = Image.objects.get(pk=data["image_pk"])
                pfl_obj.product_image = image_obj

            product_name = convert_to_ascii(data["product_name"])
            product_features = convert_to_ascii(data["product_features"])

            pfl_obj.product.pfl_product_name = product_name
            pfl_obj.product.pfl_product_features = product_features
            pfl_obj.product.save()
            pfl_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SavePFLTemplateAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadImageExternalBucketFlyerAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UploadImageExternalBucketFlyerAPI: %s", str(data))

            flyer_obj = Flyer.objects.get(pk=int(data["flyer_pk"]))
            image_obj = Image.objects.create(image=data["image"])
            flyer_obj.external_images_bucket.add(image_obj)
            flyer_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadImageExternalBucketFlyerAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadImageExternalBucketPFLAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("UploadImageExternalBucketPFLAPI: %s", str(data))

            pfl_obj = PFL.objects.get(pk=int(data["pfl_pk"]))
            image_obj = Image.objects.create(image=data["image"])
            pfl_obj.external_images_bucket.add(image_obj)
            pfl_obj.product_image = image_obj
            pfl_obj.save()

            response["image_url"] = image_obj.image.url
            response["image_pk"] = image_obj.pk
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadImageExternalBucketPFLAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchPFLListAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchPFLListAPI: %s", str(data))

            pfl_objs = PFL.objects.all()
            pfl_list = []
            for pfl_obj in pfl_objs:
                temp_dict = {}
                temp_dict["pfl_name"] = pfl_obj.name
                temp_dict["pfl_pk"] = pfl_obj.pk
                temp_dict["product_name"] = ""
                temp_dict["product_id"] = ""
                if pfl_obj.product is not None:
                    temp_dict["product_name"] = pfl_obj.product.product_name_sap
                    temp_dict["product_id"] = pfl_obj.product.product_id

                # Update this later
                if pfl_obj.product is not None:
                    if pfl_obj.product.pfl_generated_images.all().count()>0:
                        temp_dict["product_image_url"] = pfl_obj.product.pfl_generated_images.all()[0].image.url
                    else:
                        temp_dict["product_image_url"] = Config.objects.all()[0].product_404_image.image.url
                else:
                    temp_dict["product_image_url"] = Config.objects.all()[
                        0].product_404_image.image.url

                pfl_list.append(temp_dict)

            response["pfl_list"] = pfl_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchPFLListAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchPFLSearchListAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchPFLSearchListAPI: %s", str(data))

            chip_data = json.loads(data["tags"])

            search_list_objs = []
            for chip in chip_data:
                search = PFL.objects.filter(
                    Q(product__product_name_sap__icontains=chip) |
                    Q(name__icontains=chip) |
                    Q(product__product_name_amazon_uk__icontains=chip) |
                    Q(product__product_name_amazon_uae__icontains=chip) |
                    Q(product__product_name_ebay__icontains=chip) |
                    Q(product__product_id__icontains=chip) |
                    Q(product__seller_sku__icontains=chip)
                )
                for prod in search:
                    search_list_objs.append(prod)

            pfl_objs = search_list_objs

            pfl_list = []
            for pfl_obj in pfl_objs:
                temp_dict = {}
                temp_dict["pfl_name"] = pfl_obj.name
                temp_dict["pfl_pk"] = pfl_obj.pk
                temp_dict["product_name"] = ""
                temp_dict["product_id"] = ""
                if pfl_obj.product is not None:
                    temp_dict["product_name"] = pfl_obj.product.product_name_sap
                    temp_dict["product_id"] = pfl_obj.product.product_id

                # Update this later
                if pfl_obj.product is not None:
                    if pfl_obj.product.pfl_generated_images.all().count()>0:
                        temp_dict["product_image_url"] = pfl_obj.product.pfl_generated_images.all()[0].image.url
                    else:
                        temp_dict["product_image_url"] = Config.objects.all()[0].product_404_image.image.url
                else:
                    temp_dict["product_image_url"] = Config.objects.all()[
                        0].product_404_image.image.url

                pfl_list.append(temp_dict)

            response["pfl_list"] = pfl_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchPFLSearchListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchFlyerListAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchFlyerListAPI: %s", str(data))

            flyer_objs = Flyer.objects.all()
            flyer_list = []
            for flyer_obj in flyer_objs:
                temp_dict = {}
                temp_dict["flyer_name"] = flyer_obj.name
                temp_dict["flyer_pk"] = flyer_obj.pk
                # Update this later
                if flyer_obj.flyer_image!=None:
                    temp_dict["flyer_image"] = flyer_obj.flyer_image.image.url
                else:    
                    temp_dict["flyer_image"] = Config.objects.all()[0].product_404_image.image.url
                flyer_list.append(temp_dict)

            response["flyer_list"] = flyer_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFlyerListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchFlyerSearchListAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchFlyerSearchListAPI: %s", str(data))

            chip_data = json.loads(data["tags"])

            flyer_objects = Flyer.objects.all()
            search_list_objs = []

            for flyer_object in flyer_objects:
                for product in flyer_object.product_bucket.all():
                    for chip in chip_data:
                        if chip in flyer_object.name.lower():
                            search_list_objs.append(flyer_object)
                            break
                        if (chip.lower() in product.product_name_sap.lower() or
                                chip.lower() in product.product_name_amazon_uk.lower() or
                                chip.lower() in product.product_name_amazon_uae.lower() or
                                chip.lower() in product.product_name_ebay.lower() or
                                chip.lower() in product.product_id.lower() or
                                chip.lower() in product.seller_sku.lower()):
                            search_list_objs.append(flyer_object)
                            break
            flyer_objs = search_list_objs
            flyer_list = []
            for flyer_obj in set(flyer_objs):
                temp_dict = {}
                temp_dict["flyer_name"] = flyer_obj.name
                temp_dict["flyer_pk"] = flyer_obj.pk
                flyer_list.append(temp_dict)

            response["flyer_list"] = flyer_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchFlyerSearchListAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadNewFlyerBGImageAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            if request.user.has_perm('WAMSApp.change_flyer') == False:
                logger.warning("UploadNewFlyerBGImageAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("UploadNewFlyerBGImageAPI: %s", str(data))

            flyer_obj = Flyer.objects.get(pk=int(data["flyer_pk"]))
            image_obj = Image.objects.create(image=data["bg_image"])
            flyer_obj.background_images_bucket.add(image_obj)
            flyer_obj.save()

            response["bg_image_url"] = image_obj.image.url
            response["bg_image_pk"] = image_obj.pk
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadNewFlyerBGImageAPI: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DownloadImagesS3API(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("DownloadImagesS3API: %s", str(data))

            links = json.loads(data['links'])

            # [{"key": "grind-1", "url": "aws/im1.png"}, {}]

            s3 = boto3.client('s3',
                              aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                              aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

            local_links = []
            for link in links:
                filename = urllib2.unquote(link["url"]).split("/")[-1]
                temp_dict = {}
                temp_dict["key"] = link["key"]
                temp_dict["url"] = "/files/images_s3/" + str(filename)
                local_links.append(temp_dict)
                s3.download_file(settings.AWS_STORAGE_BUCKET_NAME,
                                 filename, "." + temp_dict["url"])

            response['local_links'] = local_links
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DownloadImagesS3API: %s at %s",
                         e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchBrandsAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("FetchBrandsAPI: %s", str(data))

            brand_objs = Brand.objects.all()
            brand_list = []
            for brand_obj in brand_objs:
                temp_dict = {}
                temp_dict["name"] = brand_obj.name
                temp_dict["pk"] = brand_obj.pk
                brand_list.append(temp_dict)

            response["brand_list"] = brand_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchBrandsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SavePFLInBucketAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            #logger.info("SavePFLInBucketAPI: %s", str(data))

            image_obj = None

            if "product_pk" in data:
                prod_obj = Product.objects.get(pk=int(data["product_pk"]))

                image_decoded = decode_base64_file(data["image_data"])
                image_obj = Image.objects.create(image=image_decoded)
                prod_obj.pfl_generated_images.clear()
                prod_obj.pfl_generated_images.add(image_obj)
                prod_obj.save()
            elif "pfl_pk" in data:
                image_decoded = decode_base64_file(data["image_data"])
                image_obj = Image.objects.create(image=image_decoded)
                pfl_obj = PFL.objects.get(pk=int(data["pfl_pk"]))
                prod_obj = pfl_obj.product
                prod_obj.pfl_generated_images.clear()
                prod_obj.pfl_generated_images.add(image_obj)
                prod_obj.save()

            response["main-url"] = image_obj.image.url
            response["midimage-url"] = image_obj.mid_image.url
            response["thumbnail-url"] = image_obj.thumbnail.url

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SavePFLInBucketAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveFlyerInBucketAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            #logger.info("SavePFLInBucketAPI: %s", str(data))

            flyer_obj = Flyer.objects.get(pk=int(data["flyer_pk"]))

            image_decoded = decode_base64_file(data["image_data"])
            image_obj = Image.objects.create(image=image_decoded)
            flyer_obj.flyer_image = image_obj
            flyer_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveFlyerInBucketAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class VerifyProductAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            data = request.data
            logger.info("VerifyProductAPI: %s", str(data))

            if request.user.username not in ["priyanka", "naveed", "ramees"]:
                logger.warning("VerifyProductAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            product_obj = Product.objects.get(pk=int(data["product_pk"]))
            verify = int(data["verify"])
            if verify==1:
                product_obj.verified = True
                product_obj.status = "Verified"
            elif verify==0:
                product_obj.verified = False
                product_obj.status = "Pending"

            product_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("VerifyProductAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class DeleteImageAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            
            if request.user.has_perm('WAMSApp.delete_image') == False:
                logger.warning("DeleteImageAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("DeleteImageAPI: %s", str(data))

            image_type = data["image_type"]
            image_pk = int(data["image_pk"])
            if image_type=="other":
                Image.objects.get(pk=int(image_pk)).delete()
            elif image_type=="main_sub":
                ImageBucket.objects.get(pk=int(image_pk)).delete()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("DeleteImageAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class RemoveProductFromExportListAPI(APIView):

    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:

            if request.user.has_perm('WAMSApp.delete_exportlist') == False:
                logger.warning("RemoveProductFromExportListAPI Restricted Access!")
                response['status'] = 403
                return Response(data=response)

            data = request.data
            logger.info("RemoveProductFromExportListAPI: %s", str(data))

            product_pk = int(data["product_pk"])
            export_pk = int(data["export_pk"])
            
            export_obj = ExportList.objects.get(pk=export_pk)
            product_obj = Product.objects.get(pk=product_pk)

            export_obj.products.remove(product_obj)
            export_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("RemoveProductFromExportListAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)

LoginSubmit = LoginSubmitAPI.as_view()

FetchConstantValues = FetchConstantValuesAPI.as_view()

CreateNewProduct = CreateNewProductAPI.as_view()

FetchProductDetails = FetchProductDetailsAPI.as_view()

SaveProduct = SaveProductAPI.as_view()

FetchProductList = FetchProductListAPI.as_view()

FetchExportList = FetchExportListAPI.as_view()

AddToExport = AddToExportAPI.as_view()

FetchExportProductList = FetchExportProductListAPI.as_view()

DownloadExportList = DownloadExportListAPI.as_view()

ImportProducts = ImportProductsAPI.as_view()

UploadProductImage = UploadProductImageAPI.as_view()

UpdateMainImage = UpdateMainImageAPI.as_view()

UpdateSubImages = UpdateSubImagesAPI.as_view()

CreateFlyer = CreateFlyerAPI.as_view()

CreatePFL = CreatePFLAPI.as_view()

FetchFlyerDetails = FetchFlyerDetailsAPI.as_view()

FetchPFLDetails = FetchPFLDetailsAPI.as_view()

FetchProductListFlyerPFL = FetchProductListFlyerPFLAPI.as_view()

AddProductFlyerBucket = AddProductFlyerBucketAPI.as_view()

AddProductPFLBucket = AddProductPFLBucketAPI.as_view()

FetchProductDetailsFlyerPFL = FetchProductDetailsFlyerPFLAPI.as_view()

SaveFlyerTemplate = SaveFlyerTemplateAPI.as_view()

SavePFLTemplate = SavePFLTemplateAPI.as_view()

UploadImageExternalBucketFlyer = UploadImageExternalBucketFlyerAPI.as_view()

UploadImageExternalBucketPFL = UploadImageExternalBucketPFLAPI.as_view()

FetchPFLList = FetchPFLListAPI.as_view()

FetchPFLSearchList = FetchPFLSearchListAPI.as_view()

FetchFlyerList = FetchFlyerListAPI.as_view()

FetchFlyerSearchList = FetchFlyerSearchListAPI.as_view()

UploadNewFlyerBGImage = UploadNewFlyerBGImageAPI.as_view()

DownloadImagesS3 = DownloadImagesS3API.as_view()

FetchBrands = FetchBrandsAPI.as_view()

SavePFLInBucket = SavePFLInBucketAPI.as_view()

SaveFlyerInBucket = SaveFlyerInBucketAPI.as_view()

VerifyProduct = VerifyProductAPI.as_view()

DeleteImage = DeleteImageAPI.as_view()

RemoveProductFromExportList = RemoveProductFromExportListAPI.as_view()
