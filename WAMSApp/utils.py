from dealshub.models import *
import csv
import urllib
import os
from django.core.files import File
from WAMSApp.core_utils import *
from WAMSApp.amazon_uk import *
from WAMSApp.amazon_uae import *
from WAMSApp.ebay import *
from WAMSApp.noon import *
from WAMSApp.serializers import UserSerializer
from WAMSApp.models import *
from django.db.models import Q
from django.db.models import Count

import requests
import xmltodict
import json
from django.utils import timezone
import sys
import xlsxwriter
import pandas as pd
import string
import datetime
def my_jwt_response_handler(token, user=None, request=None):
    
    return {
        'token': token,
        'user': UserSerializer(user, context={'request': request}).data
    }

def compress(image_path):
    
    try:
        im = IMAGE.open(image_path)
        basewidth = 1024
        wpercent = (basewidth / float(im.size[0]))
        hsize = int((float(im.size[1]) * float(wpercent)))
        im = im.resize((basewidth, hsize), IMAGE.ANTIALIAS)
        im.save(image_path, optimize=True, quality=100)
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("compress image: %s at %s", e, str(exc_tb.tb_lineno))

def convert_to_ascii(s):
    
    s = s.replace(u'\u2013', "-").replace(u'\u2019', "'").replace(u'\u2018', "'").replace(u'\u201d','"').replace(u'\u201c','"')
    s = s.encode("ascii", "ignore")
    
    return s

def has_atleast_one_image(prod_obj):
    
    check = False
    images_count = 0

    main_images_objs = MainImages.objects.filter(product=prod_obj)
    for main_images_obj in main_images_objs:
        images_count += main_images_obj.main_images.count()

    sub_images_objs = SubImages.objects.filter(product=prod_obj)
    for sub_images_obj in sub_images_objs:
        images_count += sub_images_obj.sub_images.count()

    images_count += prod_obj.white_background_images.count()
    images_count += prod_obj.lifestyle_images.count()
    
    # return images_count
    if(images_count>0):
        check=True
    
    return check

def get_file_extension(file_name, decoded_file):

        extension = imghdr.what(file_name, decoded_file)
        extension = "jpg" if extension == "jpeg" else extension

        return extension

def decode_base64_file(data):

    if isinstance(data, six.string_types):
        if 'data:' in data and ';base64,' in data:
            header, data = data.split(';base64,')

        try:
            decoded_file = base64.b64decode(data)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error Invalid Image : %s at %s", e, str(exc_tb.tb_lineno))
                
        file_name = str(uuid.uuid4())[:12]
        file_extension = get_file_extension(file_name, decoded_file)

        complete_file_name = "%s.%s" % (file_name, file_extension, )

        return ContentFile(decoded_file, name=complete_file_name)


def decode_base64_pdf(data):

    if isinstance(data, six.string_types):
        if 'data:' in data and ';base64,' in data:
            header, data = data.split(';base64,')

        try:
            decoded_file = base64.b64decode(data)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error Invalid Image : %s at %s", e, str(exc_tb.tb_lineno))
                
        file_name = str(uuid.uuid4())[:12]
        file_extension = "pdf"

        complete_file_name = "%s.%s" % (file_name, file_extension, )

        return ContentFile(decoded_file, name=complete_file_name)


def fetch_prices(product_id,company_code):
    
    try:

        product_obj = Product.objects.filter(base_product__seller_sku=product_id)[0]

        url="http://wig.westernint.com:8000/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"
        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = ("MOBSERVICE", "~lDT8+QklV=(")
        
        warehouse_dict = {}
        body = """<soapenv:Envelope xmlns:urn="urn:sap-com:document:sap:rfc:functions" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
                  <soapenv:Header />
                  <soapenv:Body>
                  <urn:ZAPP_STOCK_PRICE>
                   <IM_MATNR>
                    <item>
                     <MATNR>""" + product_id + """</MATNR>
                    </item>
                   </IM_MATNR>
                   <IM_VKORG>
                    <item>
                     <VKORG>""" + company_code + """</VKORG>
                    </item>
                   </IM_VKORG>
                   <T_DATA>
                    <item>
                     <MATNR></MATNR>
                     <MAKTX></MAKTX>
                     <LGORT></LGORT>
                     <CHARG></CHARG>
                     <SPART></SPART>
                     <MEINS></MEINS>
                     <ATP_QTY></ATP_QTY>
                     <TOT_QTY></TOT_QTY>
                     <CURRENCY></CURRENCY>
                     <IC_EA></IC_EA>
                     <OD_EA></OD_EA>
                     <EX_EA></EX_EA>
                     <RET_EA></RET_EA>
                     <WERKS></WERKS>
                    </item>
                   </T_DATA>
                  </urn:ZAPP_STOCK_PRICE>
                  </soapenv:Body>
                  </soapenv:Envelope>"""

        response2 = requests.post(url, auth=credentials, data=body, headers=headers)
        content = response2.content
        content = xmltodict.parse(content)
        content = json.loads(json.dumps(content))
        
        items = content["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_STOCK_PRICEResponse"]["T_DATA"]["item"]
        
        EX_EA = 0.0
        IC_EA = 0.0
        OD_EA = 0.0
        RET_EA = 0.0
        qty=0.0
        
        warehouse_dict["company_code"] = company_code
        
        if isinstance(items, dict):
            temp_price = items["EX_EA"]
            if temp_price!=None:
                temp_price = float(temp_price)
                EX_EA = max(temp_price, EX_EA)
            temp_price = items["IC_EA"]
            if temp_price!=None:
                temp_price = float(temp_price)
                IC_EA = max(temp_price, IC_EA)
            temp_price = items["OD_EA"]
            if temp_price!=None:
                temp_price = float(temp_price)
                OD_EA = max(temp_price, OD_EA)
            temp_price = items["RET_EA"]
            if temp_price!=None:
                temp_price = float(temp_price)
                RET_EA = max(temp_price, RET_EA)
            temp_qty = items["TOT_QTY"]
            if temp_qty!=None:
                temp_qty = float(temp_qty)
                qty = max(temp_qty, qty)
        
        else:
            for item in items:
                temp_price = item["EX_EA"]
                if temp_price!=None:
                    temp_price = float(temp_price)
                    EX_EA = max(temp_price, EX_EA)
                temp_price = item["IC_EA"]
                if temp_price!=None:
                    temp_price = float(temp_price)
                    IC_EA = max(temp_price, IC_EA)
                temp_price = item["OD_EA"]
                if temp_price!=None:
                    temp_price = float(temp_price)
                    OD_EA = max(temp_price, OD_EA)
                temp_price = item["RET_EA"]
                if temp_price!=None:
                    temp_price = float(temp_price)
                    RET_EA = max(temp_price, RET_EA)
                temp_qty = item["TOT_QTY"]
                if temp_qty!=None:
                    temp_qty = float(temp_qty)
                    qty = max(temp_qty, qty)
        
        prices = {}
        prices["EX_EA"] = str(EX_EA)
        prices["IC_EA"] = str(IC_EA)
        prices["OD_EA"] = str(OD_EA)
        prices["RET_EA"] = str(RET_EA)
        
        warehouse_dict["prices"] = prices
        warehouse_dict["qty"] = qty

        #product_obj.save()
        
        return warehouse_dict

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Fetch Prices: %s at %s", e, str(exc_tb.tb_lineno))
        
        return []


def fetch_prices_dealshub(uuid1, company_code):
    
    try:
        
        product_obj = Product.objects.get(uuid=uuid1)
        product_id = product_obj.base_product.seller_sku

        url="http://wig.westernint.com:8000/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"
        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = ("MOBSERVICE", "~lDT8+QklV=(")
        
        warehouse_dict = {}
        body = """<soapenv:Envelope xmlns:urn="urn:sap-com:document:sap:rfc:functions" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
                    <soapenv:Header />
                    <soapenv:Body>
                    <urn:ZAPP_STOCK_PRICE>
                     <IM_MATNR>
                      <item>
                       <MATNR>""" + product_id + """</MATNR>
                      </item>
                     </IM_MATNR>
                     <IM_VKORG>
                      <item>
                       <VKORG>""" + company_code + """</VKORG>
                      </item>
                     </IM_VKORG>
                     <T_DATA>
                      <item>
                       <MATNR></MATNR>
                       <MAKTX></MAKTX>
                       <LGORT></LGORT>
                       <CHARG></CHARG>
                       <SPART></SPART>
                       <MEINS></MEINS>
                       <ATP_QTY></ATP_QTY>
                       <TOT_QTY></TOT_QTY>
                       <CURRENCY></CURRENCY>
                       <IC_EA></IC_EA>
                       <OD_EA></OD_EA>
                       <EX_EA></EX_EA>
                       <RET_EA></RET_EA>
                       <WERKS></WERKS>
                      </item>
                     </T_DATA>
                    </urn:ZAPP_STOCK_PRICE>
                    </soapenv:Body>
                    </soapenv:Envelope>"""

        response2 = requests.post(url, auth=credentials, data=body, headers=headers)
        content = response2.content
        content = xmltodict.parse(content)
        content = json.loads(json.dumps(content))
        
        items = content["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_STOCK_PRICEResponse"]["T_DATA"]["item"]
        EX_EA = 0.0
        
        if isinstance(items, dict):
            temp_price = items["EX_EA"]
            if temp_price!=None:
                temp_price = float(temp_price)
                EX_EA = max(temp_price, EX_EA)
        else:
            for item in items:
                temp_price = item["EX_EA"]
                if temp_price!=None:
                    temp_price = float(temp_price)
                    EX_EA = max(temp_price, EX_EA)
        
        return str(EX_EA)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("fetch_prices_dealshub: %s at %s", e, str(exc_tb.tb_lineno))
        
        return "0"


def generate_report(brand_name):
    
    try:
        os.system("rm ./files/csv/images-count-report.xlsx")
    except Exception as e:
        pass

    workbook = xlsxwriter.Workbook('./files/csv/images-count-report.xlsx')
    worksheet = workbook.add_worksheet()

    product_objs = Product.objects.filter(base_product__brand__name=brand_name)

    row = ["Sr. No.",
           "Product ID",
           "Seller SKU",
           "Product Name",
           "Main Images",
           "Sub Images",
           "PFL Images",
           "White Background Images",
           "Lifestyle Images",
           "Certificate Images",
           "Giftbox Images",
           "Diecut Images",
           "A+ Content Images",
           "Ads Images",
           "Unedited Images"]

    cnt = 0
        
    colnum = 0
    for k in row:
        worksheet.write(cnt, colnum, k)
        colnum += 1

    for product_obj in product_objs:
        try:
            cnt += 1
            common_row = ["" for i in range(15)]
            common_row[0] = str(cnt)
            common_row[1] = str(product_obj.product_id)
            common_row[2] = str(product_obj.base_product.seller_sku)
            common_row[3] = str(product_obj.product_name)
            try:
                common_row[4] = str(MainImages.objects.get(product=product_obj, is_sourced=True).main_images.count())
            except Exception as e:
                common_row[4] = "0"
            
            try:
                common_row[5] = str(SubImages.objects.get(product=product_obj, is_sourced=True).sub_images.count())
            except Exception as e:
                common_row[5] = "0"

            common_row[6] = str(product_obj.pfl_images.count())
            common_row[7] = str(product_obj.white_background_images.count())
            common_row[8] = str(product_obj.lifestyle_images.count())
            common_row[9] = str(product_obj.certificate_images.count())
            common_row[10] = str(product_obj.giftbox_images.count())
            common_row[11] = str(product_obj.diecut_images.count())
            common_row[12] = str(product_obj.aplus_content_images.count())
            common_row[13] = str(product_obj.ads_images.count())
            common_row[14] = str(product_obj.base_product.unedited_images.count())
            colnum = 0
            for k in common_row:
                worksheet.write(cnt, colnum, k)
                colnum += 1

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print("Error: %s at %s", e, str(exc_tb.tb_lineno), product_obj.product_id)

    workbook.close()


def is_part_of_list(data_point_input_variable,data_point_variable):
    try:

        data_point_variable_string = "".join(data_point_variable.split("_")[:-1])
        data_point_input_variable_string = "".join(data_point_input_variable.split("_")[:-1])

        data_point_variable_int = int(data_point_variable.split("_")[-1])
        data_point_input_variable_int = int(data_point_input_variable.split("_")[-1])

        if(data_point_variable_string == data_point_input_variable_string):
            return True
        return False
    except:
        return False


def get_attribute_number(data_point_variable):

    data_point_variable_int = int(data_point_variable.split("_")[-1])
    return data_point_variable_int


def save_data_value(product_obj, base_product_obj, channel_product_obj, data_point_variable, request_user, value):
    
    response = {}
    response["status"] = 500
    response["status_message"] = ""

    try:
        if data_point_variable=="product_name":
            product_obj.product_name = value
        if data_point_variable=="product_id":
            product_obj.product_id = value
        if data_point_variable=="product_id_type":
            product_obj.product_id_type = ProductIDType.objects.get(name=value)
        if data_point_variable=="product_description":
            product_obj.product_description = value

        if is_part_of_list(data_point_variable, "pfl_product_feature_1"):
            num = get_attribute_number(data_point_variable)
            num -= 1
            pfl_product_features = json.loads(product_obj.pfl_product_features)
            if len(pfl_product_features)==num:
                pfl_product_features.append(value)
                product_obj.pfl_product_features = json.dumps(pfl_product_features)
            elif len(pfl_product_features)>num:
                pfl_product_features[num] = value
                product_obj.pfl_product_features = json.dumps(pfl_product_features)
            else:
                response["status_message"] = "Index out of range pfl_product_feature"
                return response
       
        if data_point_variable=="color_map":
            product_obj.color_map = value
        if data_point_variable=="color":
            product_obj.color = value
        if data_point_variable=="material_type":
            material_type_obj, created = MaterialType.objects.get_or_create(name=value)
            product_obj.material_type = material_type_obj
        if data_point_variable=="standard_price":
            product_obj.standard_price = float(value)
        if data_point_variable=="currency":
            product_obj.currency = value
        if data_point_variable=="quantity":
            product_obj.quantity = int(float(value))
        if data_point_variable=="barcode_string":
            product_obj.barcode_string = value
        if data_point_variable=="factory_notes":
            product_obj.factory_notes = value 
        if data_point_variable=="min_price":
            product_obj.min_price = float(value)
        if data_point_variable=="max_price":
            product_obj.max_price = float(value)
        if data_point_variable=="product_warranty":
            product_obj.warranty = value
        # if data_point_variable=="seller_sku":
        #     base_product_obj.seller_sku = value
        if data_point_variable=="category":
            base_product_obj.category = Category.objects.filter(name=value)[0]
        if data_point_variable=="sub_category":
            base_product_obj.sub_category = SubCategory.objects.filter(name=value)[0]
        if data_point_variable=="brand":
            try:
                permissible_brands = custom_permission_filter_brands(request_user)
                base_product_obj.brand = permissible_brands.get(name=value)
            except:
                raise Exception("Brand Not in Permissible Brands")
        if data_point_variable=="manufacturer":
            base_product_obj.manufacturer = value
        if data_point_variable=="manufacturer_part_number":
            base_product_obj.manufacturer_part_number = value
        
        dimensions = json.loads(base_product_obj.dimensions)
        if data_point_variable in dimensions:
            dimensions[data_point_variable] = value
        
        base_product_obj.dimensions = json.dumps(dimensions)

        amazon_uk_product_json = json.loads(channel_product_obj.amazon_uk_product_json)

        if data_point_variable=="amazonuk_product_name":
            amazon_uk_product_json["product_name"] = value
        if data_point_variable=="amazonuk_product_description":
            amazon_uk_product_json["product_description"] = value

        if is_part_of_list(data_point_variable, "amazonuk_product_attribute_list_1"):
            num = get_attribute_number(data_point_variable)
            num -= 1
            if len(amazon_uk_product_json["product_attribute_list"])==num:
                amazon_uk_product_json["product_attribute_list"].append(value)
            elif len(amazon_uk_product_json["product_attribute_list"])>num:
                amazon_uk_product_json["product_attribute_list"][num] = value
            else:
                response["status_message"] = "Index out of range amazonuk_product_attribute_list"
                return response

        if data_point_variable=="amazonuk_category":
            amazon_uk_product_json["category"] = value
        if data_point_variable=="amazonuk_sub_category":
            amazon_uk_product_json["sub_category"] = value
        if data_point_variable=="amazonuk_parentage":
            amazon_uk_product_json["parentage"] = value
        if data_point_variable=="amazonuk_parent_sku":
            amazon_uk_product_json["parent_sku"] = value
        if data_point_variable=="amazonuk_relationship_type":
            amazon_uk_product_json["relationship_type"] = value
        if data_point_variable=="amazonuk_variation_theme":
            amazon_uk_product_json["variation_theme"] = value
        if data_point_variable=="amazonuk_feed_product_type":
            amazon_uk_product_json["feed_product_type"] = value
        if data_point_variable=="amazonuk_update_delete":
            amazon_uk_product_json["update_delete"] = value
        if data_point_variable=="amazonuk_recommended_browse_nodes":
            amazon_uk_product_json["recommended_browse_nodes"] = value
        if data_point_variable=="amazonuk_search_terms":
            amazon_uk_product_json["search_terms"] = value
        if data_point_variable=="amazonuk_enclosure_material":
            amazon_uk_product_json["enclosure_material"] = value
        if data_point_variable=="amazonuk_cover_material_type":
            amazon_uk_product_json["cover_material_type"] = value

        if is_part_of_list(data_point_variable, "amazonuk_special_feature_1"):
            num = get_attribute_number(data_point_variable)
            num -= 1
            if len(amazon_uk_product_json["special_features"])==num:
                amazon_uk_product_json["special_features"].append(value)
            elif len(amazon_uk_product_json["special_features"])>num:
                amazon_uk_product_json["special_features"][num] = value
            else:
                response["status_message"] = "Index out of range amazonuk_special_feature"
                return response

        if data_point_variable=="amazonuk_sale_price":
            amazon_uk_product_json["sale_price"] = float(value)
        if data_point_variable=="amazonuk_sale_from":
            amazon_uk_product_json["sale_from"] = value
        if data_point_variable=="amazonuk_sale_end":
            amazon_uk_product_json["sale_end"] = value
        if data_point_variable=="amazonuk_wattage":
            amazon_uk_product_json["wattage"] = value
        if data_point_variable=="amazonuk_wattage_metric":
            amazon_uk_product_json["wattage_metric"] = value
        if data_point_variable=="amazonuk_item_count":
            amazon_uk_product_json["item_count"] = value
        if data_point_variable=="amazonuk_item_count_metric":
            amazon_uk_product_json["item_count_metric"] = value
        if data_point_variable=="amazonuk_item_condition_note":
            amazon_uk_product_json["item_condition_note"] = value
        if data_point_variable=="amazonuk_max_order_quantity":
            amazon_uk_product_json["max_order_quantity"] = value
        if data_point_variable=="amazonuk_number_of_items":
            amazon_uk_product_json["number_of_items"] = value
        if data_point_variable=="amazonuk_condition_type":
            amazon_uk_product_json["condition_type"] = value
        if data_point_variable=="amazonuk_number_of_items":
            amazon_uk_product_json["number_of_items"] = value
        if data_point_variable=="amazonuk_package_length":
            amazon_uk_product_json["dimensions"]["package_length"] = value
        if data_point_variable=="amazonuk_package_length_metric":
            amazon_uk_product_json["dimensions"]["package_length_metric"] = value
        if data_point_variable=="amazonuk_package_width":
            amazon_uk_product_json["dimensions"]["package_width"] = value
        if data_point_variable=="amazonuk_package_width_metric":
            amazon_uk_product_json["dimensions"]["package_width_metric"] = value
        if data_point_variable=="amazonuk_package_height":
            amazon_uk_product_json["dimensions"]["package_height"] = value
        if data_point_variable=="amazonuk_package_height_metric":
            amazon_uk_product_json["dimensions"]["package_height_metric"] = value
        if data_point_variable=="amazonuk_package_weight":
            amazon_uk_product_json["dimensions"]["package_weight"] = value
        if data_point_variable=="amazonuk_package_weight_metric":
            amazon_uk_product_json["dimensions"]["package_weight_metric"] = value
        if data_point_variable=="amazonuk_package_quantity":
            amazon_uk_product_json["dimensions"]["package_quantity"] = value
        if data_point_variable=="amazonuk_shipping_weight":
            amazon_uk_product_json["dimensions"]["shipping_weight"] = value
        if data_point_variable=="amazonuk_shipping_weight_metric":
            amazon_uk_product_json["dimensions"]["shipping_weight_metric"] = value
        if data_point_variable=="amazonuk_item_display_weight":
            amazon_uk_product_json["dimensions"]["item_display_weight"] = value
        if data_point_variable=="amazonuk_item_display_weight_metric":
            amazon_uk_product_json["dimensions"]["item_display_weight_metric"] = value
        if data_point_variable=="amazonuk_item_display_volume":
            amazon_uk_product_json["dimensions"]["item_display_volume"] = value
        if data_point_variable=="amazonuk_item_display_volume_metric":
            amazon_uk_product_json["dimensions"]["item_display_volume_metric"] = value
        if data_point_variable=="amazonuk_item_display_length":
            amazon_uk_product_json["dimensions"]["item_display_length"] = value
        if data_point_variable=="amazonuk_item_display_length_metric":
            amazon_uk_product_json["dimensions"]["item_display_length_metric"] = value
        if data_point_variable=="amazonuk_item_weight":
            amazon_uk_product_json["dimensions"]["item_weight"] = value
        if data_point_variable=="amazonuk_item_weight_metric":
            amazon_uk_product_json["dimensions"]["item_weight_metric"] = value
        if data_point_variable=="amazonuk_item_length":
            amazon_uk_product_json["dimensions"]["item_length"] = value
        if data_point_variable=="amazonuk_item_length_metric":
            amazon_uk_product_json["dimensions"]["item_length_metric"] = value
        if data_point_variable=="amazonuk_item_width":
            amazon_uk_product_json["dimensions"]["item_width"] = value
        if data_point_variable=="amazonuk_item_width_metric":
            amazon_uk_product_json["dimensions"]["item_width_metric"] = value
        if data_point_variable=="amazonuk_item_height":
            amazon_uk_product_json["dimensions"]["item_height"] = value
        if data_point_variable=="amazonuk_item_height_metric":
            amazon_uk_product_json["dimensions"]["item_height_metric"] = value
        if data_point_variable=="amazonuk_item_display_width":
            amazon_uk_product_json["dimensions"]["item_display_width"] = value
        if data_point_variable=="amazonuk_item_display_width_metric":
            amazon_uk_product_json["dimensions"]["item_display_width_metric"] = value
        if data_point_variable=="amazonuk_item_display_height":
            amazon_uk_product_json["dimensions"]["item_display_height"] = value
        if data_point_variable=="amazonuk_item_display_height_metric":
            amazon_uk_product_json["dimensions"]["item_display_height_metric"] = value
        if data_point_variable=="amazonuk_http_link":
            amazon_uk_product_json["http_link"] = value
        if data_point_variable=="amazonuk_asin":
            amazon_uk_product_json["ASIN"] = value
        if data_point_variable=="amazonuk_status":
            amazon_uk_product_json["status"] = value
        if data_point_variable=="amazonuk_now_price":
            amazon_uk_product_json["now_price"] = float(value)
        if data_point_variable=="amazonuk_was_price":
            amazon_uk_product_json["was_price"] = float(value)
        if data_point_variable=="amazonuk_stock":
            amazon_uk_product_json["stock"] = int(float(value))

        
        amazon_uae_product_json = json.loads(channel_product_obj.amazon_uae_product_json)

        if data_point_variable=="amazonuae_product_name":
            amazon_uae_product_json["product_name"] = value
        if data_point_variable=="amazonuae_product_description":
            amazon_uae_product_json["product_description"] = value

        if is_part_of_list(data_point_variable, "amazonuae_product_attribute_list_1"):
            num = get_attribute_number(data_point_variable)
            num -= 1
            if len(amazon_uae_product_json["product_attribute_list"])==num:
                amazon_uae_product_json["product_attribute_list"].append(value)
            elif len(amazon_uae_product_json["product_attribute_list"])>num:
                amazon_uae_product_json["product_attribute_list"][num] = value
            else:
                response["status_message"] = "Index out of range amazonuae_product_attribute_list"
                return response

        if data_point_variable=="amazonuae_category":
            amazon_uae_product_json["category"] = value
        if data_point_variable=="amazonuae_sub_category":
            amazon_uae_product_json["sub_category"] = value
        if data_point_variable=="amazonuae_feed_product_type":
            amazon_uae_product_json["feed_product_type"] = value
        if data_point_variable=="amazonuae_recommended_browse_nodes":
            amazon_uae_product_json["recommended_browse_nodes"] = value
        if data_point_variable=="amazonuae_update_delete":
            amazon_uae_product_json["update_delete"] = value
        if data_point_variable=="amazonuae_http_link":
            amazon_uae_product_json["http_link"] = value
        if data_point_variable=="amazonuae_asin":
            amazon_uae_product_json["ASIN"] = value
        if data_point_variable=="amazonuae_status":
            amazon_uae_product_json["status"] = value
        if data_point_variable=="amazonuae_now_price":
            amazon_uae_product_json["now_price"] = float(value)
        if data_point_variable=="amazonuae_was_price":
            amazon_uae_product_json["was_price"] = float(value)
        if data_point_variable=="amazonuae_stock":
            amazon_uae_product_json["stock"] = int(float(value))

        ebay_product_json = json.loads(channel_product_obj.ebay_product_json)

        if data_point_variable=="ebay_category":
            ebay_product_json["category"] = value
        if data_point_variable=="ebay_sub_category":
            ebay_product_json["sub_category"] = value
        if data_point_variable=="ebay_product_name":
            ebay_product_json["product_name"] = value
        if data_point_variable=="ebay_product_description":
            ebay_product_json["product_description"] = value
        if data_point_variable=="ebay_status":
            ebay_product_json["status"] = value
        if data_point_variable=="ebay_now_price":
            ebay_product_json["now_price"] = float(value)
        if data_point_variable=="ebay_was_price":
            ebay_product_json["was_price"] = float(value)
        if data_point_variable=="ebay_stock":
            ebay_product_json["stock"] = int(float(value))

        if is_part_of_list(data_point_variable, "ebay_product_attribute_list_1"):
            num = get_attribute_number(data_point_variable)
            num -= 1
            if len(ebay_product_json["product_attribute_list"])==num:
                ebay_product_json["product_attribute_list"].append(value)
            elif len(ebay_product_json["product_attribute_list"])>num:
                ebay_product_json["product_attribute_list"][num] = value
            else:
                response["status_message"] = "Index out of range ebay_product_attribute_list"
                return response

        if data_point_variable=="ebay_http_link":
            ebay_product_json["http_link"] = value

        noon_product_json = json.loads(channel_product_obj.noon_product_json)

        if data_point_variable=="noon_product_name":
            noon_product_json["product_name"] = value
        if data_point_variable=="noon_product_type":
            noon_product_json["product_type"] = value
        if data_point_variable=="noon_product_subtype":
            noon_product_json["product_subtype"] = value
        if data_point_variable=="noon_category":
            noon_product_json["category"] = value
        if data_point_variable=="noon_subtitle":
            noon_product_json["subtitle"] = value
        if data_point_variable=="noon_sub_category":
            noon_product_json["sub_category"] = value
        if data_point_variable=="noon_model_number":
            noon_product_json["model_number"] = value
        if data_point_variable=="noon_model_name":
            noon_product_json["model_name"] = value
        if data_point_variable=="noon_msrp_ae":
            noon_product_json["msrp_ae"] = value
        if data_point_variable=="noon_msrp_ae_unit":
            noon_product_json["msrp_ae_unit"] = value
        if data_point_variable=="noon_product_description":
            noon_product_json["product_description"] = value
        if data_point_variable=="noon_now_price":
            noon_product_json["now_price"] = float(value)
        if data_point_variable=="noon_sale_price":
            noon_product_json["sale_price"] = float(value)
        if data_point_variable=="noon_sale_start":
            noon_product_json["sale_start"] = value
        if data_point_variable=="noon_sale_end":
            noon_product_json["sale_end"] = value
        if data_point_variable=="noon_stock":
            noon_product_json["stock"] = int(float(value))
        if data_point_variable=="noon_warranty":
            noon_product_json["warranty"] = value
        if data_point_variable=="noon_status":
            noon_product_json["status"] = value
        if data_point_variable=="noon_sku":
            noon_product_json["noon_sku"] = value
        if data_point_variable=="noon_partner_sku":
            noon_product_json["partner_sku"] = value
        if data_point_variable=="noon_partner_barcode":
            noon_product_json["partner_barcode"] = value
        if data_point_variable=="noon_psku_code":
            noon_product_json["psku_code"] = value


        if is_part_of_list(data_point_variable, "product_attribute_list_1"):
            num = get_attribute_number(data_point_variable)
            num -= 1
            if len(noon_product_json["product_attribute_list"])==num:
                noon_product_json["product_attribute_list"].append(value)
            elif len(noon_product_json["product_attribute_list"])>num:
                noon_product_json["product_attribute_list"][num] = value
            else:
                response["status_message"] = "Index out of range Noon Attribute List"
                return response
        
        if data_point_variable=="noon_http_link":
            noon_product_json["http_link"] = value

        channel_product_obj.noon_product_json = json.dumps(noon_product_json)
        channel_product_obj.amazon_uk_product_json = json.dumps(amazon_uk_product_json)
        channel_product_obj.amazon_uae_product_json = json.dumps(amazon_uae_product_json)
        channel_product_obj.ebay_product_json = json.dumps(ebay_product_json)

        response["product_obj"] = product_obj
        response["base_product_obj"] = base_product_obj
        response["channel_product_obj"] = channel_product_obj
        response["status"] = 200

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("save_data_value: %s at %s", e, str(exc_tb.tb_lineno))
        response["status_message"] = str(e)

    return response

def generate_dynamic_row(data_point_list,need_sr_no=True):

    if(need_sr_no == True):
        row = ["Sr. No."]
    else:
        row = []
    for data_point in data_point_list:
        data_point_obj = DataPoint.objects.get(variable=data_point)
        row.append(data_point_obj.name)

    return row


def get_data_value(product_obj, base_product_obj, channel_product_obj, data_point_variable):
    
    try:
        if data_point_variable=="product_name":
            return product_obj.product_name
        if data_point_variable=="product_id":
            return product_obj.product_id
        if data_point_variable=="product_id_type":
            return str(product_obj.product_id_type)
        if data_point_variable=="product_description":
            return product_obj.product_description
        if data_point_variable=="product_description_without_html":
            return product_obj.get_non_html_description()
        if is_part_of_list(data_point_variable, "pfl_product_feature_1"):
            num = get_attribute_number(data_point_variable)
            pfl_product_features = json.loads(product_obj.pfl_product_features)
            if len(pfl_product_features)>=num:
                return pfl_product_features[num-1]
            return ""

        if data_point_variable=="color_map":
            return product_obj.color_map
        if data_point_variable=="color":
            return product_obj.color
        if data_point_variable=="material_type":
            return str(product_obj.material_type)
        if data_point_variable=="standard_price":
            return "" if product_obj.standard_price==None else product_obj.standard_price
        if data_point_variable=="currency":
            return product_obj.currency
        if data_point_variable=="quantity":
            return "" if product_obj.quantity==None else product_obj.quantity
        if data_point_variable=="min_price":
            return product_obj.min_price
        if data_point_variable=="max_price":
            return product_obj.max_price
        if data_point_variable=="product_warranty":
            return product_obj.warranty

        if data_point_variable=="main_image":
            if MainImages.objects.get(product=product_obj, is_sourced=True).main_images.count()>0:
                return MainImages.objects.get(product=product_obj, is_sourced=True).main_images.all()[0].image.image.url
            return ""

        if is_part_of_list(data_point_variable, "sub_image_1"):
            num = get_attribute_number(data_point_variable)
            if SubImages.objects.get(product=product_obj, is_sourced=True).sub_images.count()>=num:
                return SubImages.objects.get(product=product_obj, is_sourced=True).sub_images.all()[num-1].image.image.url
            return ""

        if is_part_of_list(data_point_variable, "white_background_image_1"):
            num = get_attribute_number(data_point_variable)
            if product_obj.white_background_images.count()>=num:
                return product_obj.white_background_images.all()[num-1].image.url
            return ""

        if is_part_of_list(data_point_variable, "lifestyle_image_1"):
            num = get_attribute_number(data_point_variable)
            if product_obj.lifestyle_images.count()>=num:
                return product_obj.lifestyle_images.all()[num-1].image.url
            return ""

        if is_part_of_list(data_point_variable, "certificate_image_1"):
            num = get_attribute_number(data_point_variable)
            if product_obj.certificate_images.count()>=num:
                return product_obj.certificate_images.all()[num-1].image.url
            return ""

        if is_part_of_list(data_point_variable, "giftbox_image_1"):
            num = get_attribute_number(data_point_variable)
            if product_obj.giftbox_images.count()>=num:
                return product_obj.giftbox_images.all()[num-1].image.url
            return ""

        if is_part_of_list(data_point_variable, "diecut_image_1"):
            num = get_attribute_number(data_point_variable)
            if product_obj.diecut_images.count()>=num:
                return product_obj.diecut_images.all()[num-1].image.url
            return ""

        if is_part_of_list(data_point_variable, "aplus_content_image_1"):
            num = get_attribute_number(data_point_variable)
            if product_obj.aplus_content_images.count()>=num:
                return product_obj.aplus_content_images.all()[num-1].image.url
            return ""

        if is_part_of_list(data_point_variable, "ads_image_1"):
            num = get_attribute_number(data_point_variable)
            if product_obj.ads_images.count()>=num:
                return product_obj.ads_images.all()[num-1].image.url
            return ""

        if is_part_of_list(data_point_variable, "transparent_image_1"):
            num = get_attribute_number(data_point_variable)
            if product_obj.transparent_images.count()>=num:
                return product_obj.transparent_images.all()[num-1].image.url
            return ""

        if is_part_of_list(data_point_variable, "pfl_image_1"):
            num = get_attribute_number(data_point_variable)
            if product_obj.pfl_images.count()>=num:
                return product_obj.pfl_images.all()[num-1].image.url
            return ""

        if is_part_of_list(data_point_variable, "pfl_generated_image_1"):
            num = get_attribute_number(data_point_variable)
            if product_obj.pfl_images.count()>=num:
                return product_obj.pfl_generated_images.all()[num-1].image.url
            return ""

        if is_part_of_list(data_point_variable, "unedited_image_1"):
            num = get_attribute_number(data_point_variable)
            if base_product_obj.unedited_images.count()>=num:
                return base_product_obj.unedited_images.all()[num-1].image.url
            return ""            

        if data_point_variable=="barcode_string":
            return product_obj.barcode_string
        if data_point_variable=="factory_notes":
            return product_obj.factory_notes
        if data_point_variable=="seller_sku":
            return base_product_obj.seller_sku
        if data_point_variable=="category":
            return str(base_product_obj.category)
        if data_point_variable=="sub_category":
            return str(base_product_obj.sub_category)
        if data_point_variable=="brand":
            return str(base_product_obj.brand)
        if data_point_variable=="manufacturer":
            return base_product_obj.manufacturer
        if data_point_variable=="manufacturer_part_number":
            return base_product_obj.manufacturer_part_number
        
        dimensions = json.loads(base_product_obj.dimensions)
        if data_point_variable in dimensions:
            return dimensions[data_point_variable]
        
        amazon_uk_product_json = json.loads(channel_product_obj.amazon_uk_product_json)

        if data_point_variable=="amazonuk_product_name":
            return amazon_uk_product_json["product_name"]
        if data_point_variable=="amazonuk_product_description":
            return amazon_uk_product_json["product_description"]

        if is_part_of_list(data_point_variable, "amazonuk_product_attribute_list_1"):
            num = get_attribute_number(data_point_variable)
            if len(amazon_uk_product_json["product_attribute_list"])>=num:
                return amazon_uk_product_json["product_attribute_list"][num-1]
            else:
                return ""

        if data_point_variable=="amazonuk_category":
            return amazon_uk_product_json["category"]
        if data_point_variable=="amazonuk_sub_category":
            return amazon_uk_product_json["sub_category"]
        if data_point_variable=="amazonuk_parentage":
            return amazon_uk_product_json["parentage"]
        if data_point_variable=="amazonuk_parent_sku":
            return amazon_uk_product_json["parent_sku"]
        if data_point_variable=="amazonuk_relationship_type":
            return amazon_uk_product_json["relationship_type"]
        if data_point_variable=="amazonuk_variation_theme":
            return amazon_uk_product_json["variation_theme"]
        if data_point_variable=="amazonuk_feed_product_type":
            return amazon_uk_product_json["feed_product_type"]
        if data_point_variable=="amazonuk_update_delete":
            return amazon_uk_product_json["update_delete"]
        if data_point_variable=="amazonuk_recommended_browse_nodes":
            return amazon_uk_product_json["recommended_browse_nodes"]
        if data_point_variable=="amazonuk_search_terms":
            return amazon_uk_product_json["search_terms"]
        if data_point_variable=="amazonuk_enclosure_material":
            return amazon_uk_product_json["enclosure_material"]
        if data_point_variable=="amazonuk_cover_material_type":
            return amazon_uk_product_json["cover_material_type"]

        if is_part_of_list(data_point_variable, "amazonuk_special_feature_1"):
            num = get_attribute_number(data_point_variable)
            if len(amazon_uk_product_json["special_features"])>=num:
                return amazon_uk_product_json["special_features"][num-1]
            else:
                return ""

        if data_point_variable=="amazonuk_sale_price":
            return amazon_uk_product_json["sale_price"]
        if data_point_variable=="amazonuk_sale_from":
            return amazon_uk_product_json["sale_from"]
        if data_point_variable=="amazonuk_sale_end":
            return amazon_uk_product_json["sale_end"]
        if data_point_variable=="amazonuk_wattage":
            return amazon_uk_product_json["wattage"]
        if data_point_variable=="amazonuk_wattage_metric":
            return amazon_uk_product_json["wattage_metric"]
        if data_point_variable=="amazonuk_item_count":
            return amazon_uk_product_json["item_count"]
        if data_point_variable=="amazonuk_item_count_metric":
            return amazon_uk_product_json["item_count_metric"]
        if data_point_variable=="amazonuk_item_condition_note":
            return amazon_uk_product_json["item_condition_note"]
        if data_point_variable=="amazonuk_max_order_quantity":
            return amazon_uk_product_json["max_order_quantity"]
        if data_point_variable=="amazonuk_number_of_items":
            return amazon_uk_product_json["number_of_items"]
        if data_point_variable=="amazonuk_condition_type":
            return amazon_uk_product_json["condition_type"]
        if data_point_variable=="amazonuk_number_of_items":
            return amazon_uk_product_json["number_of_items"]
        if data_point_variable=="amazonuk_package_length":
            return amazon_uk_product_json["dimensions"]["package_length"]
        if data_point_variable=="amazonuk_package_length_metric":
            return amazon_uk_product_json["dimensions"]["package_length_metric"]
        if data_point_variable=="amazonuk_package_width":
            return amazon_uk_product_json["dimensions"]["package_width"]
        if data_point_variable=="amazonuk_package_width_metric":
            return amazon_uk_product_json["dimensions"]["package_width_metric"]
        if data_point_variable=="amazonuk_package_height":
            return amazon_uk_product_json["dimensions"]["package_height"]
        if data_point_variable=="amazonuk_package_height_metric":
            return amazon_uk_product_json["dimensions"]["package_height_metric"]
        if data_point_variable=="amazonuk_package_weight":
            return amazon_uk_product_json["dimensions"]["package_weight"]
        if data_point_variable=="amazonuk_package_weight_metric":
            return amazon_uk_product_json["dimensions"]["package_weight_metric"]
        if data_point_variable=="amazonuk_package_quantity":
            return amazon_uk_product_json["dimensions"]["package_quantity"]
        if data_point_variable=="amazonuk_shipping_weight":
            return amazon_uk_product_json["dimensions"]["shipping_weight"]
        if data_point_variable=="amazonuk_shipping_weight_metric":
            return amazon_uk_product_json["dimensions"]["shipping_weight_metric"]
        if data_point_variable=="amazonuk_item_display_weight":
            return amazon_uk_product_json["dimensions"]["item_display_weight"]
        if data_point_variable=="amazonuk_item_display_weight_metric":
            return amazon_uk_product_json["dimensions"]["item_display_weight_metric"]
        if data_point_variable=="amazonuk_item_display_volume":
            return amazon_uk_product_json["dimensions"]["item_display_volume"]
        if data_point_variable=="amazonuk_item_display_volume_metric":
            return amazon_uk_product_json["dimensions"]["item_display_volume_metric"]
        if data_point_variable=="amazonuk_item_display_length":
            return amazon_uk_product_json["dimensions"]["item_display_length"]
        if data_point_variable=="amazonuk_item_display_length_metric":
            return amazon_uk_product_json["dimensions"]["item_display_length_metric"]
        if data_point_variable=="amazonuk_item_weight":
            return amazon_uk_product_json["dimensions"]["item_weight"]
        if data_point_variable=="amazonuk_item_weight_metric":
            return amazon_uk_product_json["dimensions"]["item_weight_metric"]
        if data_point_variable=="amazonuk_item_length":
            return amazon_uk_product_json["dimensions"]["item_length"]
        if data_point_variable=="amazonuk_item_length_metric":
            return amazon_uk_product_json["dimensions"]["item_length_metric"]
        if data_point_variable=="amazonuk_item_width":
            return amazon_uk_product_json["dimensions"]["item_width"]
        if data_point_variable=="amazonuk_item_width_metric":
            return amazon_uk_product_json["dimensions"]["item_width_metric"]
        if data_point_variable=="amazonuk_item_height":
            return amazon_uk_product_json["dimensions"]["item_height"]
        if data_point_variable=="amazonuk_item_height_metric":
            return amazon_uk_product_json["dimensions"]["item_height_metric"]
        if data_point_variable=="amazonuk_item_display_width":
            return amazon_uk_product_json["dimensions"]["item_display_width"]
        if data_point_variable=="amazonuk_item_display_width_metric":
            return amazon_uk_product_json["dimensions"]["item_display_width_metric"]
        if data_point_variable=="amazonuk_item_display_height":
            return amazon_uk_product_json["dimensions"]["item_display_height"]
        if data_point_variable=="amazonuk_item_display_height_metric":
            return amazon_uk_product_json["dimensions"]["item_display_height_metric"]
        if data_point_variable=="amazonuk_http_link":
            return amazon_uk_product_json["http_link"]
        if data_point_variable=="amazonuk_asin":
            return amazon_uk_product_json["ASIN"]
        if data_point_variable=="amazonuk_status":
            return amazon_uk_product_json["status"]
        if data_point_variable=="amazonuk_now_price":
            return amazon_uk_product_json["now_price"]
        if data_point_variable=="amazonuk_was_price":
            return amazon_uk_product_json["was_price"]
        if data_point_variable=="amazonuk_stock":
            return amazon_uk_product_json["stock"]

        
        amazon_uae_product_json = json.loads(channel_product_obj.amazon_uae_product_json)

        if data_point_variable=="amazonuae_product_name":
            return amazon_uae_product_json["product_name"]
        if data_point_variable=="amazonuae_product_description":
            return amazon_uae_product_json["product_description"]

        if is_part_of_list(data_point_variable, "amazonuae_product_attribute_list_1"):
            num = get_attribute_number(data_point_variable)
            if len(amazon_uae_product_json["product_attribute_list"])>=num:
                return amazon_uae_product_json["product_attribute_list"][num-1]
            else:
                return ""

        if data_point_variable=="amazonuae_category":
            return amazon_uae_product_json["category"]
        if data_point_variable=="amazonuae_sub_category":
            return amazon_uae_product_json["sub_category"]
        if data_point_variable=="amazonuae_feed_product_type":
            return amazon_uae_product_json["feed_product_type"]
        if data_point_variable=="amazonuae_recommended_browse_nodes":
            return amazon_uae_product_json["recommended_browse_nodes"]
        if data_point_variable=="amazonuae_update_delete":
            return amazon_uae_product_json["update_delete"]
        if data_point_variable=="amazonuae_http_link":
            return amazon_uae_product_json["http_link"]
        if data_point_variable=="amazonuae_asin":
            return amazon_uae_product_json["ASIN"]
        if data_point_variable=="amazonuae_status":
            return amazon_uae_product_json["status"]
        if data_point_variable=="amazonuae_now_price":
            return amazon_uae_product_json["now_price"]
        if data_point_variable=="amazonuae_was_price":
            return amazon_uae_product_json["was_price"]
        if data_point_variable=="amazonuae_stock":
            return amazon_uae_product_json["stock"]

        ebay_product_json = json.loads(channel_product_obj.ebay_product_json)

        if data_point_variable=="ebay_category":
            return ebay_product_json["category"]
        if data_point_variable=="ebay_sub_category":
            return ebay_product_json["sub_category"]
        if data_point_variable=="ebay_product_name":
            return ebay_product_json["product_name"]
        if data_point_variable=="ebay_product_description":
            return ebay_product_json["product_description"]
        if data_point_variable=="ebay_status":
            return ebay_product_json["status"]
        if data_point_variable=="ebay_now_price":
            return ebay_product_json["now_price"]
        if data_point_variable=="ebay_was_price":
            return ebay_product_json["was_price"]
        if data_point_variable=="ebay_stock":
            return ebay_product_json["stock"]

        if is_part_of_list(data_point_variable, "ebay_product_attribute_list_1"):
            num = get_attribute_number(data_point_variable)
            if len(ebay_product_json["product_attribute_list"])>=num:
                return ebay_product_json["product_attribute_list"][num-1]
            else:
                return ""

        if data_point_variable=="ebay_http_link":
            return ebay_product_json["http_link"]

        noon_product_json = json.loads(channel_product_obj.noon_product_json)

        if data_point_variable=="noon_product_name":
            return noon_product_json["product_name"]
        if data_point_variable=="noon_product_type":
            return noon_product_json["product_type"]
        if data_point_variable=="noon_product_subtype":
            return noon_product_json["product_subtype"]
        if data_point_variable=="noon_parent_sku":
            return noon_product_json["parent_sku"]
        if data_point_variable=="noon_category":
            return noon_product_json["category"]
        if data_point_variable=="noon_subtitle":
            return noon_product_json["subtitle"]
        if data_point_variable=="noon_sub_category":
            return noon_product_json["sub_category"]
        if data_point_variable=="noon_model_number":
            return noon_product_json["model_number"]
        if data_point_variable=="noon_model_name":
            return noon_product_json["model_name"]
        if data_point_variable=="noon_msrp_ae":
            return noon_product_json["msrp_ae"]
        if data_point_variable=="noon_msrp_ae_unit":
            return noon_product_json["msrp_ae_unit"]
        if data_point_variable=="noon_product_description":
            return noon_product_json["product_description"]
        if data_point_variable=="noon_now_price":
            return noon_product_json["now_price"]
        if data_point_variable=="noon_sale_price":
            return noon_product_json["sale_price"]
        if data_point_variable=="noon_sale_start":
            return noon_product_json["sale_start"]
        if data_point_variable=="noon_sale_end":
            return noon_product_json["sale_end"]
        if data_point_variable=="noon_stock":
            return noon_product_json["stock"]
        if data_point_variable=="noon_warranty":
            return noon_product_json["warranty"]
        if data_point_variable=="noon_status":
            return noon_product_json["status"]
        if data_point_variable=="noon_sku":
            return noon_product_json["noon_sku"]
        if data_point_variable=="noon_partner_sku":
            return noon_product_json["partner_sku"]
        if data_point_variable=="noon_partner_barcode":
            return noon_product_json["partner_barcode"]
        if data_point_variable=="noon_psku_code":
            return noon_product_json["psku_code"]

        if is_part_of_list(data_point_variable, "product_attribute_list_1"):
            num = get_attribute_number(data_point_variable)
            if len(noon_product_json["product_attribute_list"])>=num:
                return noon_product_json["product_attribute_list"][num-1]
            else:
                return ""

        if data_point_variable=="noon_http_link":
            return noon_product_json["http_link"]
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("get_data_value: %s at %s", e, str(exc_tb.tb_lineno))
        return ""


def generate_dynamic_export(filename, product_uuid_list, data_point_list):

    # try:
    #     os.system("rm ./files/csv/dynamic_export.xlsx")
    # except Exception as e:
    #     pass

    workbook = xlsxwriter.Workbook('./files/csv/'+filename)
    worksheet = workbook.add_worksheet()

    row = generate_dynamic_row(data_point_list)
    cnt = 0        
    colnum = 0
    for k in row:
        worksheet.write(cnt, colnum, k)
        colnum += 1

    for product_uuid in product_uuid_list:
        try:
            cnt += 1
            product_obj = Product.objects.get(uuid=product_uuid)
            base_product_obj = product_obj.base_product
            channel_product_obj = ChannelProduct.objects.get(product=product_obj)

            common_row = ["" for i in range(len(data_point_list)+1)]
            common_row[0] = str(cnt)
            for i in range(len(data_point_list)):
                common_row[i+1] = get_data_value(product_obj, base_product_obj, channel_product_obj, data_point_list[i])

            colnum = 0
            for k in common_row:
                worksheet.write(cnt, colnum, k)
                colnum += 1
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print("Error ", e, str(exc_tb.tb_lineno))

    workbook.close()


def upload_dynamic_excel_for_product(path,operation,request_user):

    response = {}
    response["status_message"] = ""
    response["status"] = 500

    try:

        logger.info("upload_dynamic_excel_for_product [Path]: %s", path)

        dfs = pd.read_excel(path, sheet_name=None)

        dfs = dfs["Sheet1"]

        logger.info("upload_dynamic_excel_for_product [Excel]: %s ", dfs)

        data_point_list = []

        for x in dfs.columns:
            data_point_list.append(str(x).strip().lower())

        logger.info("upload_dynamic_excel_for_product [Data Point List]: %s", data_point_list)

        rows = len(dfs.iloc[:])

        result_list = []

        filename = "files/dynamic bulk upload excel/Dynamic Excel Upload Result.xlsx"

        workbook = xlsxwriter.Workbook(filename)

        worksheet = workbook.add_worksheet()

        organization_obj = CustomPermission.objects.get(user__username=request_user.username).organization

        for i in range(rows):

            errors = []

            warnings = []

            result = []

            base_product_exists = False

            product_obj = Product.objects.none()
            base_product_obj = BaseProduct.objects.none()
            channel_product_obj = ChannelProduct.objects.none()

            if(operation == "Update"):
                try:
                    product_id = None
                    error_flag = ["Product ID"]
                    for j in range(len(data_point_list)):
                        if(data_point_list[j] == ("Product ID").lower()):
                            error_flag[0] = ""
                            product_id = str(dfs.iloc[i][j]).strip()

                    for j in error_flag:
                        if(j!=""):
                            raise Exception("Required Column '" + j + "' does not exist")

                    result.append(str(product_id))

                    if(product_id=="" or product_id=="nan"):
                        raise Exception("Required Fields must not be empty!")

                    product_obj = Product.objects.get(product_id=product_id)
                    base_product_obj = product_obj.base_product
                    channel_product_obj = product_obj.channel_product
                except Exception as e:
                    errors.append(str(e))
                    result.append(warnings)
                    result.append(errors)
                    result.append("Rejected")
                    result_list.append(result)
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("upload_dynamic_excel_for_product: %s at %s", e, str(exc_tb.tb_lineno))
                    continue
            else:
                try:
                    seller_sku = None
                    product_id = None
                    category_name = None
                    sub_category_name = None
                    brand_name = None

                    product_name = ""
                    manufacturer = ""
                    manufacturer_part_number = ""

                    error_flag = ["Seller SKU","Product ID","Product Name","Brand","Manufacturer","Manufacturer Part Number","Category","SubCategory"]

                    for j in range(len(data_point_list)):
                        if(data_point_list[j] == ("Seller SKU").lower()):
                            error_flag[0] = ""
                            seller_sku = str(dfs.iloc[i][j]).strip()
                        if(data_point_list[j] == ("Product ID").lower()):
                            error_flag[1] = ""
                            product_id = str(dfs.iloc[i][j]).strip()
                        if(data_point_list[j] == ("Product Name").lower()):
                            error_flag[2] = ""
                            product_name = str(dfs.iloc[i][j]).strip()
                        if(data_point_list[j] == ("Brand").lower()):
                            error_flag[3] = ""
                            brand_name = str(dfs.iloc[i][j]).strip()
                        if(data_point_list[j] == ("Manufacturer").lower()):
                            error_flag[4] = ""
                            manufacturer = str(dfs.iloc[i][j]).strip()
                        if(data_point_list[j] == ("Manufacturer Part Number").lower()):
                            error_flag[5] = ""
                            manufacturer_part_number = str(dfs.iloc[i][j]).strip()
                        if(data_point_list[j] == ("Category").lower()):
                            error_flag[6] = ""
                            category_name = str(dfs.iloc[i][j]).strip()
                        if(data_point_list[j] == ("SubCategory").lower()):
                            error_flag[7] = ""
                            sub_category_name = str(dfs.iloc[i][j]).strip()
    
                    result.append(str(product_id))

                    for j in error_flag:
                        if(j!=""):
                            raise Exception("Required Column '" + j + "' does not exist")

                    if(product_name == "" or manufacturer == "" or manufacturer_part_number == "" or category_name == "" or sub_category_name == "" or product_id == "" or brand_name == "" or seller_sku == ""):
                        raise Exception("Required Fields must not be empty!")

                    if manufacturer == "nan":
                        manufacturer = ""

                    if manufacturer_part_number == "nan":
                        manufacturer_part_number = ""

                    if category_name == "nan":
                        category_name = "GENERAL"

                    if sub_category_name == "nan":
                        sub_category_name = "GENERAL"

                    if(product_name == "nan" or product_id == "nan" or brand_name == "nan" or seller_sku == "nan"):
                        logger.info("Product Name: %s", product_name)
                        logger.info("Manufacturer: %s", manufacturer)
                        logger.info("Manufacturer PN: %s", manufacturer_part_number)
                        logger.info("Category: %s", category_name)
                        logger.info("sub_category_name: %s", sub_category_name)
                        logger.info("Product ID: %s", product_id)
                        logger.info("Brand: %s", brand_name)
                        logger.info("Seller SKU: %s", seller_sku)
                        raise Exception("Required Fields must not be empty!")

                    if Category.objects.filter(name=category_name).exists()==False:
                        raise Exception("Category does not exist. Please make sure that the category is selected from sheet2 from the downloaded template.")

                    if SubCategory.objects.filter(name=sub_category_name).exists()==False:
                        raise Exception("SubCategory does not exist. Please make sure that the sub-category is selected from sheet2 from the downloaded template.")

                    category_obj = Category.objects.filter(name=category_name)[0]
                    sub_category_obj = SubCategory.objects.filter(name=sub_category_name)[0]
                    brand_obj = Brand.objects.none()
                    permissible_brands = custom_permission_filter_brands(request_user)
                    try:    
                        brand_obj = permissible_brands.get(name=brand_name)
                    except:
                        raise Exception("Brand not in Permissible Brands")

                    base_product_obj = BaseProduct.objects.none()

                    if(Product.objects.filter(product_id=product_id, base_product__brand__organization=organization_obj).exists()):
                        raise Exception("Product Already Exists on OmnyComm with same Product ID!")

                    base_product_exists = False
                    try:
                        base_product_obj = BaseProduct.objects.get(seller_sku=seller_sku, brand__organization=organization_obj)
                        base_product_exists = True
                    except:
                        base_product_obj = BaseProduct.objects.create(
                            base_product_name=product_name,
                            seller_sku=seller_sku,
                            brand=brand_obj,
                            category=category_obj,
                            sub_category=sub_category_obj,
                            manufacturer=manufacturer,
                            manufacturer_part_number=manufacturer_part_number,
                        )
                
                    product_obj = Product.objects.create(
                        product_name = product_name,
                        product_name_sap=product_name,
                        pfl_product_name=product_name,
                        base_product=base_product_obj,
                        product_id = product_id,
                    )

                    location_group_objs = LocationGroup.objects.filter(website_group__brands__in=[brand_obj])
                    for location_group_obj in location_group_objs:
                        DealsHubProduct.objects.create(product_name=product_obj.product_name, product=product_obj, location_group=location_group_obj, category=base_product_obj.category, sub_category=base_product_obj.sub_category)

                    channel_product_obj = product_obj.channel_product

                except Exception as e:
                    errors.append(str(e))
                    result.append(warnings)
                    result.append(errors)
                    result.append("Rejected")
                    result_list.append(result)
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("upload_dynamic_excel_for_product: %s at %s", e, str(exc_tb.tb_lineno))
                    continue

            for j in range(len(data_point_list)):

                value = str(dfs.iloc[i][j]).strip()

                data_point_variable = ""

                try:
                    flag = 0
                    for data_point_obj in DataPoint.objects.all():
                        if(str(data_point_obj.name).lower()==data_point_list[j]):
                            data_point_variable = data_point_obj.variable
                            flag = 1
                            break
                    if(flag == 0):
                        raise Exception("Did'nt Match")
                except:
                    errors.append("Column '" + data_point_list[j] + "' does not match")
                    continue

                if(value != "" and value !="nan"):
                    incoming_response = save_data_value(product_obj,base_product_obj,channel_product_obj,data_point_variable,request_user,value)
                else:
                    warnings.append(data_point_list[j] + " is empty")
                    continue

                if(incoming_response["status"]!=200):  
                    errors.append(str(incoming_response["status_message"]))
                else:
                    channel_product_obj = incoming_response["channel_product_obj"]
                    product_obj = incoming_response["product_obj"]
                    base_product_obj = incoming_response["base_product_obj"]
               
            result.append(warnings)
            result.append(errors)

            if(len(errors) == 0):
                result.append("Accepted")
                channel_product_obj.save()
                product_obj.save()
                base_product_obj.save()
            else:
                result.append("Rejected")
                if(operation == "Create"):
                    channel_product_obj.delete()
                    product_obj.delete()
                    if(base_product_exists == False):
                        base_product_obj.delete()

            result_list.append(result)

        worksheet.write(0, 0, "Product ID")
        worksheet.write(0, 1, "Warnings")
        worksheet.write(0, 2, "Errors")
        worksheet.write(0, 3, "Status")

        accepted_products = 0
        rejected_products = 0

        for i in range(len(result_list)):
            row = i+1       
            worksheet.write(row, 0, result_list[i][0])
            worksheet.write(row, 3, result_list[i][-1])
            if(result_list[i][-1]=="Accepted"):
                accepted_products += 1
            else:
                rejected_products += 1
            for k in range(1,3):
                excel_value = ""
                for j in range(0,len(result_list[i][k])):
                    delimiter = ""
                    if(j != len(result_list[i][k])-1):
                        delimiter = " | "
                    excel_value += result_list[i][k][j] + delimiter
                worksheet.write(row, k, excel_value)
    
        workbook.close()
        response["status"] = 200
        response["result_path"] = filename
        response["accepted_products"] = accepted_products
        response["rejected_products"] = rejected_products

    except Exception as e:
        response["status_message"] = str(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("upload_dynamic_excel_for_product: %s at %s", e, str(exc_tb.tb_lineno))

    return response


def fetch_sap_details_for_order_punching(dealshub_product_obj):
    sap_details = {
        "company_code": "NA",
        "sales_office": "NA",
        "vendor_code": "NA",
        "purchase_org": "NA"
    }
    try:
        if dealshub_product_obj.get_brand().lower()=="geepas":
            sap_details["company_code"] = "1100"
            sap_details["sales_office"] = "1005"
            sap_details["vendor_code"] = "V1001"
            sap_details["purchase_org"] = "1200"
        elif dealshub_product_obj.get_brand().lower()=="olsenmark":
            sap_details["company_code"] = "1100"
            sap_details["sales_office"] = "1105"
            sap_details["vendor_code"] = "V1100"
            sap_details["purchase_org"] = "1200"
        elif dealshub_product_obj.get_brand().lower()=="krypton":
            sap_details["company_code"] = "2100"
            sap_details["sales_office"] = "2105"
            sap_details["vendor_code"] = "V2100"
            sap_details["purchase_org"] = "1200"
        elif dealshub_product_obj.get_brand().lower()=="royalford":
            sap_details["company_code"] = "3000"
            sap_details["sales_office"] = "3005"
            sap_details["vendor_code"] = "V3001"
            sap_details["purchase_org"] = "1200"
        elif dealshub_product_obj.get_brand().lower()=="abraj":
            sap_details["company_code"] = "6000"
            sap_details["sales_office"] = "6008"
            sap_details["vendor_code"] = "V6000"
            sap_details["purchase_org"] = "1200"
        elif dealshub_product_obj.get_brand().lower()=="baby plus":
            sap_details["company_code"] = "5550"
            sap_details["sales_office"] = "5558"
            sap_details["vendor_code"] = "V5550"
            sap_details["purchase_org"] = "1200"
        
        return sap_details

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("fetch_sap_details_for_order_punching: %s at %s", e, str(exc_tb.tb_lineno))
        return "NA"


def get_company_code_from_brand_name(brand_name):
    brand_name = brand_name.lower()
    if brand_name=="geepas":
        return "1000"
    if brand_name=="abraj":
        return "6000"
    if brand_name=="baby plus":
        return "5550"
    if brand_name=="bag house":
        return "5600"
    if brand_name=="clarkford":
        return "7000"
    if brand_name=="crystal promo":
        return "5110"
    if brand_name=="crystal":
        return "5100"
    if brand_name=="delcasa":
        return "3050"
    if brand_name=="epsilon":
        return "2100"
    if brand_name=="leather plus":
        return "5700"
    if brand_name=="olsenmark":
        return "1100"
    if brand_name=="royalford":
        return "3000"
    if brand_name=="young life":
        return "5000"
    return ""


def get_sap_batch_and_uom(company_code, seller_sku):
    response = {
        "batch": "",
        "uom": ""
    }
    return response
    try:
        url="http://wig.westernint.com:8000/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"
        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = ("MOBSERVICE", "~lDT8+QklV=(")
        body = """<soapenv:Envelope xmlns:urn="urn:sap-com:document:sap:rfc:functions" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
        <soapenv:Header />
        <soapenv:Body>
        <urn:ZAPP_STOCK_PRICE>
         <IM_MATNR>
          <item>
           <MATNR>""" + seller_sku + """</MATNR>
          </item>
         </IM_MATNR>
         <IM_VKORG>
          <item>
           <VKORG>""" + company_code + """</VKORG>
          </item>
         </IM_VKORG>
         <T_DATA>
          <item>
           <MATNR></MATNR>
           <MAKTX></MAKTX>
           <LGORT></LGORT>
           <CHARG></CHARG>
           <SPART></SPART>
           <MEINS></MEINS>
           <ATP_QTY></ATP_QTY>
           <TOT_QTY></TOT_QTY>
           <CURRENCY></CURRENCY>
           <IC_EA></IC_EA>
           <OD_EA></OD_EA>
           <EX_EA></EX_EA>
           <RET_EA></RET_EA>
           <WERKS></WERKS>
          </item>
         </T_DATA>
        </urn:ZAPP_STOCK_PRICE>
        </soapenv:Body>
        </soapenv:Envelope>"""
        sap_response = requests.post(url, auth=credentials, data=body, headers=headers)
        content = sap_response.content
        content = xmltodict.parse(content)
        content = json.loads(json.dumps(content))
        items = content["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_STOCK_PRICEResponse"]["T_DATA"]["item"]
            
        if isinstance(items, dict):
            if items["MEINS"]!=None:
                response["uom"] = items["MEINS"]
            if items["CHARG"]!=None:
                response["batch"] = items["CHARG"]
        else:
            for item in items:
                if items["MEINS"]!=None and items["CHARG"]!=None:
                    response["uom"] = items["MEINS"]
                    response["batch"] = items["CHARG"]

        return response
    except Exception as e:
        return response


def generate_sap_order_format(unit_order_list):

    try:
        os.system("rm ./files/csv/sap-order-format.xlsx")
    except Exception as e:
        pass

    workbook = xlsxwriter.Workbook('./files/csv/sap-order-format.xlsx')

    # Step 1

    worksheet1 = workbook.add_worksheet()

    row = ["Company Code",
           "Distribution Channel",
           "Division",
           "Sales Office",
           "Order Type",
           "SAP Customer ID",
           "Order ID",
           "Article Code",
           "Qty",
           "UoM",
           "Batch"]

    cnt = 0
        
    colnum = 0
    for k in row:
        worksheet1.write(cnt, colnum, k)
        colnum += 1

    for unit_order in unit_order_list:
        try:
            cnt += 1

            dealshub_product_obj = DealsHubProduct.objects.get(uuid=unit_order["productUuid"])

            sap_details = fetch_sap_details_for_order_punching(dealshub_product_obj)

            common_row = ["" for i in range(11)]
            common_row[0] = sap_details["company_code"]
            common_row[1] = "01"
            common_row[2] = "00"
            common_row[3] = sap_details["sales_office"]
            common_row[4] = "ZWIC"
            common_row[5] = "40000637"
            common_row[6] = unit_order["orderId"]
            common_row[7] = dealshub_product_obj.get_seller_sku()
            common_row[8] = unit_order["quantity"]
            
            colnum = 0
            for k in common_row:
                worksheet1.write(cnt, colnum, k)
                colnum += 1

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("generate_sap_order_format: %s at %s", e, str(exc_tb.tb_lineno))


    # Step 2

    worksheet2 = workbook.add_worksheet()

    row = ["PO Order Type",
           "Company Code",
           "Purchase Org",
           "Site",
           "Storage Location",
           "Purchase Group",
           "Pricing Condition (Header) ZPA3",
           "Invoice Reference",
           "Vendor Code",
           "Item Code",
           "Order Unit",
           "Order Price UoM",
           "Purchase Order Qty",
           "Net Price",
           "Date"]

    cnt = 0
        
    colnum = 0
    for k in row:
        worksheet2.write(cnt, colnum, k)
        colnum += 1

    for unit_order in unit_order_list:
        try:
            cnt += 1

            dealshub_product_obj = DealsHubProduct.objects.get(uuid=unit_order["productUuid"])

            sap_details = fetch_sap_details_for_order_punching(dealshub_product_obj)

            common_row = ["" for i in range(15)]
            common_row[0] = "WIC"
            common_row[1] = "1200"
            common_row[2] = "1200"
            common_row[3] = "1202"
            common_row[4] = "TG01"
            common_row[5] = "GP2"

            common_row[7] = "Invoice Ref ID"
            common_row[8] = sap_details["vendor_code"]
            common_row[9] = dealshub_product_obj.get_seller_sku()
            common_row[10] = "EA"
            common_row[11] = "EA"
            common_row[12] = unit_order["quantity"]
            common_row[13] = unit_order["price"]
            common_row[14] = unit_order["orderPlacedDate"]

            colnum = 0
            for k in common_row:
                worksheet2.write(cnt, colnum, k)
                colnum += 1

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("generate_sap_order_format: %s at %s", e, str(exc_tb.tb_lineno))


    # Step 3

    worksheet3 = workbook.add_worksheet()

    row = ["Company Code",
           "Order Type",
           "SAP Customer ID",
           "End Customer Name",
           "Area",
           "Order ID",
           "Article Code",
           "Qty",
           "UoM",
           "Batch",
           "Total Amount",
           "Promotion Discount Line Item",
           "Voucher Discount Header",
           "Courier Charge Header",
           "COD Charge Header",
           "Other Charge-Header",
           "Other Charge-Line Item"]

    cnt = 0
        
    colnum = 0
    for k in row:
        worksheet3.write(cnt, colnum, k)
        colnum += 1

    for unit_order in unit_order_list:
        try:
            cnt += 1

            dealshub_product_obj = DealsHubProduct.objects.get(uuid=unit_order["productUuid"])

            order_type = "ZJCR"
            customer_code = ""
            if unit_order["shippingMethod"]=="WIG Fleet":
                customer_code = "50000629"
            elif unit_order["shippingMethod"]=="TFM":
                customer_code = "50000627"

            company_code = get_company_code_from_brand_name(dealshub_product_obj.get_brand())
            response = get_sap_batch_and_uom(company_code, dealshub_product_obj.get_seller_sku())
            batch = response["batch"]
            uom = response["uom"]

            common_row = ["" for i in range(17)]
            common_row[0] = "1200"
            common_row[1] = order_type
            common_row[2] = customer_code
            common_row[3] = unit_order["customerName"]
            common_row[4] = unit_order["area"]
            common_row[5] = unit_order["orderId"]
            common_row[6] = dealshub_product_obj.get_seller_sku()
            common_row[7] = unit_order["quantity"]
            common_row[8] = uom
            common_row[9] = batch
            common_row[10] = unit_order["total"]

            colnum = 0
            for k in common_row:
                worksheet3.write(cnt, colnum, k)
                colnum += 1

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("generate_sap_order_format: %s at %s", e, str(exc_tb.tb_lineno))

    workbook.close()


def generate_regular_order_format(unit_order_list):

    try:
        os.system("rm ./files/csv/regular-order-format.xlsx")
    except Exception as e:
        pass

    workbook = xlsxwriter.Workbook('./files/csv/regular-order-format.xlsx')

    worksheet = workbook.add_worksheet()


    row = ["Sr. No.",
           "Datetime",
           "Order ID",
           "Order Item ID",
           "Channel",
           "Product Name",
           "Product ID",
           "Seller SKU",
           "Currency",
           "Strike Price",
           "Selling Price",
           "Delivery (inc. VAT)",
           "Delivery VAT",
           "Delivery (excl. VAT)",
           "COD (inc. VAT)",
           "COD VAT",
           "COD (excl. VAT)",
           "Subtotal (inc. VAT)",
           "Subtotal VAT",
           "Subtotal (excl. VAT)", 
           "Quantity",
           "Customer Name",
           "Customer Email ID",
           "Customer Phone Number",
           "Billing Address",
           "Shipping Address",
           "Payment Status",
           "Shipping Method",
           "Order Tracking Status",
           "Order Tracking Status Time"]

    cnt = 0
        
    colnum = 0
    for k in row:
        worksheet.write(cnt, colnum, k)
        colnum += 1

    for unit_order in unit_order_list:
        try:
            cnt += 1

            dh_product_obj = DealsHubProduct.objects.get(uuid=unit_order["productUuid"])

            common_row = ["" for i in range(len(row))]
            common_row[0] = str(cnt)
            common_row[1] = unit_order["orderPlacedDate"]
            common_row[2] = unit_order["bundleId"]
            common_row[3] = unit_order["orderId"]
            common_row[4] = dh_product_obj.location_group.name
            common_row[5] = dh_product_obj.get_name()
            common_row[6] = dh_product_obj.get_product_id()
            common_row[7] = dh_product_obj.get_seller_sku()
            common_row[8] = dh_product_obj.get_currency()
            common_row[9] = str(dh_product_obj.was_price)
            common_row[10] = unit_order["price"]

            common_row[11] = unit_order["deliveryFeeWithVat"]
            common_row[12] = unit_order["deliveryFeeVat"]
            common_row[13] = unit_order["deliveryFeeWithoutVat"]
            common_row[14] = unit_order["codFeeWithVat"]
            common_row[15] = unit_order["codFeeVat"]
            common_row[16] = unit_order["codFeeWithoutVat"]
            common_row[17] = unit_order["subtotalWithVat"]
            common_row[18] = unit_order["subtotalVat"]
            common_row[19] = unit_order["subtotalWithoutVat"]

            common_row[20] = unit_order["quantity"]
            common_row[21] = unit_order["customerName"]
            common_row[22] = unit_order["customerEmail"]
            common_row[23] = unit_order["customerContactNumber"]
            common_row[24] = unit_order["shippingAddress"]
            common_row[25] = unit_order["shippingAddress"]
            common_row[26] = unit_order["paymentStatus"]
            common_row[27] = unit_order["shippingMethod"]
            common_row[28] = unit_order["trackingStatus"]
            common_row[29] = unit_order["trackingStatusTime"]
            
            colnum = 0
            for k in common_row:
                worksheet.write(cnt, colnum, k)
                colnum += 1

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("generate_regular_order_format: %s at %s", e, str(exc_tb.tb_lineno))

    workbook.close()



def fetch_refresh_stock(seller_sku, company_code, location_code):

    try:
        url="http://wig.westernint.com:8000/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"
        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = ("MOBSERVICE", "~lDT8+QklV=(")
        
        body = """<soapenv:Envelope xmlns:urn="urn:sap-com:document:sap:rfc:functions" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
                  <soapenv:Header />
                  <soapenv:Body>
                  <urn:ZAPP_STOCK_PRICE>
                   <IM_MATNR>
                    <item>
                     <MATNR>""" + seller_sku + """</MATNR>
                    </item>
                   </IM_MATNR>
                   <IM_VKORG>
                    <item>
                     <VKORG>""" + company_code + """</VKORG>
                    </item>
                   </IM_VKORG>
                   <T_DATA>
                    <item>
                     <MATNR></MATNR>
                     <MAKTX></MAKTX>
                     <LGORT></LGORT>
                     <CHARG></CHARG>
                     <SPART></SPART>
                     <MEINS></MEINS>
                     <ATP_QTY></ATP_QTY>
                     <TOT_QTY></TOT_QTY>
                     <CURRENCY></CURRENCY>
                     <IC_EA></IC_EA>
                     <OD_EA></OD_EA>
                     <EX_EA></EX_EA>
                     <RET_EA></RET_EA>
                     <WERKS></WERKS>
                    </item>
                   </T_DATA>
                  </urn:ZAPP_STOCK_PRICE>
                  </soapenv:Body>
                  </soapenv:Envelope>"""

        response2 = requests.post(url, auth=credentials, data=body, headers=headers)
        content = response2.content
        content = xmltodict.parse(content)
        content = json.loads(json.dumps(content))
        
        items = content["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_STOCK_PRICEResponse"]["T_DATA"]["item"]
        
        if isinstance(items, dict):
            if items["LGORT"]==location_code:
                return float(items["ATP_QTY"])
            return 0
        else:
            max_qty = 0
            for item in items:
                if item["LGORT"]==location_code:
                    max_qty = max(max_qty, float(item["ATP_QTY"]))
            return max_qty

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("fetch_tg01_stock %s at %s", e, str(exc_tb.tb_lineno))
        return 0

def add_imagebucket_to_channel_main_images(image_bucket_obj,product_obj):

    try:
        channel_obj = Channel.objects.get(name="Amazon UK")
        main_images_obj , created = MainImages.objects.get_or_create(product=product_obj,channel=channel_obj)
        main_images_obj.main_images.add(image_bucket_obj)
        main_images_obj.save()

        channel_obj = Channel.objects.get(name="Amazon UAE")
        main_images_obj , created = MainImages.objects.get_or_create(product=product_obj,channel=channel_obj)
        main_images_obj.main_images.add(image_bucket_obj)
        main_images_obj.save()

        channel_obj = Channel.objects.get(name="Ebay")
        main_images_obj , created = MainImages.objects.get_or_create(product=product_obj,channel=channel_obj)
        main_images_obj.main_images.add(image_bucket_obj)
        main_images_obj.save()

        channel_obj = Channel.objects.get(name="Noon")
        main_images_obj , created = MainImages.objects.get_or_create(product=product_obj,channel=channel_obj)
        main_images_obj.main_images.add(image_bucket_obj)
        main_images_obj.save()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("add_imagebucket_to_channel_main_images %s at %s", e, str(exc_tb.tb_lineno))

def get_channel_product_dict(channel_name,channel_product):

    channel_product_dict = {}

    try:
        if channel_name == "Amazon UAE":
            channel_product_dict = json.loads(channel_product.amazon_uae_product_json)
        if channel_name == "Amazon UK":
            channel_product_dict = json.loads(channel_product.amazon_uk_product_json)
        if channel_name == "Ebay":
            channel_product_dict = json.loads(channel_product.ebay_product_json)
        if channel_name == "Noon":
            channel_product_dict = json.loads(channel_product.noon_product_json)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("get_channel_product_dict %s at %s", e, str(exc_tb.tb_lineno))

    return channel_product_dict

def assign_channel_product_json(channel_name,channel_product,channel_product_dict):

    try:
        if channel_name == "Amazon UAE":
            channel_product.amazon_uae_product_json = json.dumps(channel_product_dict)
        if channel_name == "Amazon UK":
            channel_product.amazon_uk_product_json = json.dumps(channel_product_dict)
        if channel_name == "Ebay":
            channel_product.ebay_product_json = json.dumps(channel_product_dict)
        if channel_name == "Noon":
            channel_product.noon_product_json = json.dumps(channel_product_dict)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("get_channel_product_dict %s at %s", e, str(exc_tb.tb_lineno))

    return channel_product

def permission_channel_boolean_response(user,channel_obj):
    
    try:
        permissible_channels = custom_permission_filter_channels(user)
        
        if channel_obj not in permissible_channels:
            logger.warning("permission_channel_response Restricted Access of " + channel_name+" !")
            response['status'] = 403
            return False
        return True
    except Exception as e:
        logger.error("permission_channel_response Restricted Access of "+channel_name+" Channel!")
        return False

def get_custom_permission_page_list(user):

    try:
        page_list = CustomPermission.objects.get(user=user).page_list
    except:
        page_list = "[]"
        logger.info("get_custom_permission_page_list: CustomPermission Object does not exist")

    page_list = json.loads(page_list)

    return page_list


def individual_logs_from_dict(json1,json2,new_changes,location_str):

    if type(json1)!=dict and type(json2)!=dict :

        if json1!=json2 :
            new_changes[location_str] = [json1,json2]

        return new_changes

    for key in json1.keys():

        other_key_val = None

        try:
            other_key_val = json2[key]
        except:
            other_key_val = None 

        location_str_temp = location_str + " > " + key.replace("_", " ").title()

        new_changes = individual_logs_from_dict(json1[key],other_key_val,new_changes,location_str_temp)

    for key in json2.keys():

        other_key_val = None
        
        try:
            other_key_val = json1[key]
        except:
            other_key_val = None 

        location_str_temp = location_str + " > " + key.replace("_", " ").title()

        new_changes = individual_logs_from_dict(other_key_val,json2[key],new_changes,location_str_temp)

    return new_changes


def logentry_dict_to_attributes(changes):

    new_changes = {}

    for key in changes:

        changes[key][0] = str(changes[key][0]).replace("\\U2018", "").replace("\\U2019", "")
        changes[key][1] = str(changes[key][1]).replace("\\U2018", "").replace("\\U2019", "")

        json1 = changes[key][0]
        json2 = changes[key][1]

        try:    
            json1 = json.loads(changes[key][0])
            json1 = json.loads(json1)
        except Exception as e:
            pass
        try:
            json2 = json.loads(changes[key][1])
            json2 = json.loads(json2)
        except Exception as e:
            pass

        print(type(json1),type(json2))

        new_changes = individual_logs_from_dict(json1,json2,new_changes,key)

    return new_changes

def content_health_filtered_list(filter_parameters,search_list_product_objs):

    if filter_parameters.get("Product Description", None) == True:
        search_list_product_objs = search_list_product_objs.exclude(Q(product_description=None) | Q(product_description=""))
    elif filter_parameters.get("Product Description", None) == False:
        search_list_product_objs = search_list_product_objs.filter(Q(product_description=None) | Q(product_description=""))

    if filter_parameters.get("Product Name", None) == True:
        search_list_product_objs = search_list_product_objs.exclude(Q(product_name=None) | Q(product_name=""))
    elif filter_parameters.get("Product Name", None) == False:
        search_list_product_objs = search_list_product_objs.filter(Q(product_name=None) | Q(product_name=""))

    if filter_parameters.get("Product ID", None) == True:
        search_list_product_objs = search_list_product_objs.exclude(Q(product_id=None) | Q(product_id=""))
    elif filter_parameters.get("Product ID", None) == False:
        search_list_product_objs = search_list_product_objs.filter(Q(product_id=None) | Q(product_id=""))

    if filter_parameters.get("Product Verified", None) == True:
        search_list_product_objs = search_list_product_objs.filter(verified=True)
    elif filter_parameters.get("Product Verified", None) == False:
        search_list_product_objs = search_list_product_objs.filter(verified=False)

    if filter_parameters.get("Amazon UK Product", None) == True:
        search_list_product_objs = search_list_product_objs.filter(channel_product__is_amazon_uk_product_created=True)
    elif filter_parameters.get("Amazon UK Product", None) == False:
        search_list_product_objs = search_list_product_objs.filter(channel_product__is_amazon_uk_product_created=False)

    if filter_parameters.get("Amazon UAE Product", None) == True:
        search_list_product_objs = search_list_product_objs.filter(channel_product__is_amazon_uae_product_created=True)
    elif filter_parameters.get("Amazon UAE Product", None) == False:
        search_list_product_objs = search_list_product_objs.filter(channel_product__is_amazon_uae_product_created=False)

    if filter_parameters.get("Noon Product", None) == True:
        search_list_product_objs = search_list_product_objs.filter(channel_product__is_noon_product_created=True)
    elif filter_parameters.get("Noon Product", None) == False:
        search_list_product_objs = search_list_product_objs.filter(channel_product__is_noon_product_created=False)

    if filter_parameters.get("Ebay Product", None) == True:
        search_list_product_objs = search_list_product_objs.filter(channel_product__is_ebay_product_created=True)
    elif filter_parameters.get("Ebay Product", None) == False:
        search_list_product_objs = search_list_product_objs.filter(channel_product__is_ebay_product_created=False)

    if filter_parameters.get("Product Features", None) == True:
        search_list_product_objs = search_list_product_objs.exclude(Q(pfl_product_features="") | Q(pfl_product_features="[]"))
    elif filter_parameters.get("Product Features", None) == False:
        search_list_product_objs = search_list_product_objs.filter(Q(pfl_product_features="") | Q(pfl_product_features="[]"))

    if filter_parameters.get("White Background Images > 0", None) == True:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('white_background_images')).filter(c__gt=0)
    elif filter_parameters.get("White Background Images > 0", None) == False:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('white_background_images')).filter(c=0)

    if filter_parameters.get("White Background Images > 1", None) == True:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('white_background_images')).filter(c__gt=1)
    elif filter_parameters.get("White Background Images > 1", None) == False:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('white_background_images')).filter(c__lt=2)

    if filter_parameters.get("White Background Images > 2", None) == True:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('white_background_images')).filter(c__gt=2)
    elif filter_parameters.get("White Background Images > 2", None) == False:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('white_background_images')).filter(c__lt=3)

    if filter_parameters.get("Lifestyle Images > 0", None) == True:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('lifestyle_images')).filter(c__gt=0)
    elif filter_parameters.get("Lifestyle Images > 0", None) == False:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('lifestyle_images')).filter(c=0)

    if filter_parameters.get("Lifestyle Images > 1", None) == True:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('lifestyle_images')).filter(c__gt=1)
    elif filter_parameters.get("Lifestyle Images > 1", None) == False:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('lifestyle_images')).filter(c__lt=2)

    if filter_parameters.get("Lifestyle Images > 2", None) == True:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('lifestyle_images')).filter(c__gt=2)
    elif filter_parameters.get("Lifestyle Images > 2", None) == False:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('lifestyle_images')).filter(c__lt=3)

    if filter_parameters.get("Giftbox Images > 0", None) == True:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('giftbox_images')).filter(c__gt=0)
    elif filter_parameters.get("Giftbox Images > 0", None) == False:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('giftbox_images')).filter(c=0)

    if filter_parameters.get("Giftbox Images > 1", None) == True:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('giftbox_images')).filter(c__gt=1)
    elif filter_parameters.get("Giftbox Images > 1", None) == False:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('giftbox_images')).filter(c__lt=2)

    if filter_parameters.get("Giftbox Images > 2", None) == True:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('giftbox_images')).filter(c__gt=2)
    elif filter_parameters.get("Giftbox Images > 2", None) == False:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('giftbox_images')).filter(c__lt=3)

    if filter_parameters.get("Transparent Images > 0", None) == True:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('transparent_images')).filter(c__gt=0)
    elif filter_parameters.get("Transparent Images > 0", None) == False:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('transparent_images')).filter(c=0)

    if filter_parameters.get("Transparent Images > 1", None) == True:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('transparent_images')).filter(c__gt=1)
    elif filter_parameters.get("Transparent Images > 1", None) == False:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('transparent_images')).filter(c__lt=2)

    if filter_parameters.get("Transparent Images > 2", None) == True:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('transparent_images')).filter(c__gt=2)
    elif filter_parameters.get("Transparent Images > 2", None) == False:
        search_list_product_objs = search_list_product_objs.annotate(c=Count('transparent_images')).filter(c__lt=3)

    if filter_parameters.get("Main Images", None) == True:  
        search_list_product_objs = search_list_product_objs.filter(mainimages__in=MainImages.objects.annotate(num_main_images=Count('main_images')).filter(is_sourced=True,num_main_images__gt=0))
    elif filter_parameters.get("Main Images", None) == False:  
        search_list_product_objs = search_list_product_objs.exclude(mainimages__in=MainImages.objects.annotate(num_main_images=Count('main_images')).filter(is_sourced=True,num_main_images__gt=0))

    if filter_parameters.get("Sub Images > 0", None) == True:  
        search_list_product_objs = search_list_product_objs.filter(product__in=SubImages.objects.annotate(num_sub_images=Count('sub_images')).filter(is_sourced=True,num_sub_images__gt=0))
    elif filter_parameters.get("Sub Images > 0", None) == False:  
        search_list_product_objs = search_list_product_objs.exclude(product__in=SubImages.objects.annotate(num_sub_images=Count('sub_images')).filter(is_sourced=True,num_sub_images__gt=0))

    if filter_parameters.get("Sub Images > 1", None) == True:  
        search_list_product_objs = search_list_product_objs.filter(product__in=SubImages.objects.annotate(num_sub_images=Count('sub_images')).filter(is_sourced=True,num_sub_images__gt=1))
    elif filter_parameters.get("Sub Images > 1", None) == False:
        search_list_product_objs = search_list_product_objs.exclude(product__in=SubImages.objects.annotate(num_sub_images=Count('sub_images')).filter(is_sourced=True,num_sub_images__gt=1))

    if filter_parameters.get("Sub Images > 2", None) == True:  
        search_list_product_objs = search_list_product_objs.filter(product__in=SubImages.objects.annotate(num_sub_images=Count('sub_images')).filter(is_sourced=True,num_sub_images__gt=2))
    elif filter_parameters.get("Sub Images > 2", None) == False:  
        search_list_product_objs = search_list_product_objs.exclude(product__in=SubImages.objects.annotate(num_sub_images=Count('sub_images')).filter(is_sourced=True,num_sub_images__gt=2))

    return search_list_product_objs 

def get_recommended_browse_node(seller_sku,channel):

    try:

        url="http://wig.westernint.com:8000/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"
        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = ("MOBSERVICE", "~lDT8+QklV=(")
        company_code_dict ={
            "Geepas" : "1000",
            "Abraj": "6000",
            "BabyPlus": "5550",
            "Baby Plus": "5550",
            "Crystal": "5100",
            "Delcasa": "3050",
            "Olsenmark": "1100",
            "Royalford": "3000",
            "Younglife": "5000"
        }
        
        product_obj = Product.objects.filter(base_product__seller_sku=seller_sku)[0]
        company_code = company_code_dict[product_obj.base_product.brand.name]
        body = """<soapenv:Envelope xmlns:urn="urn:sap-com:document:sap:rfc:functions" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
                  <soapenv:Header />
                  <soapenv:Body>
                  <urn:ZAPP_STOCK_PRICE>
                   <IM_MATNR>
                    <item>
                     <MATNR>""" + seller_sku + """</MATNR>
                    </item>
                   </IM_MATNR>
                   <IM_VKORG>
                    <item>
                     <VKORG>""" + company_code + """</VKORG>
                    </item>
                   </IM_VKORG>
                   <T_DATA>
                    <item>
                     <MATNR></MATNR>
                     <MAKTX></MAKTX>
                     <LGORT></LGORT>
                     <CHARG></CHARG>
                     <SPART></SPART>
                     <MEINS></MEINS>
                     <ATP_QTY></ATP_QTY>
                     <TOT_QTY></TOT_QTY>
                     <CURRENCY></CURRENCY>
                     <IC_EA></IC_EA>
                     <OD_EA></OD_EA>
                     <EX_EA></EX_EA>
                     <RET_EA></RET_EA>
                     <WERKS></WERKS>
                    </item>
                   </T_DATA>
                  </urn:ZAPP_STOCK_PRICE>
                  </soapenv:Body>
                  </soapenv:Envelope>"""
        response2 = requests.post(url, auth=credentials, data=body, headers=headers)
        content = response2.content
        content = xmltodict.parse(content)
        content = json.loads(json.dumps(content))
        item = content["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_STOCK_PRICEResponse"]["T_DATA"]["item"]
        if isinstance(item,list):
            item = item[1]

        try:
            recommended_browse_node = CategoryMapping.objects.filter(channel__name=channel,sap_sub_category__sub_category=item["WWGHB1"])[0].recommended_browse_node
            return recommended_browse_node
        except:
            logger.error("get_recommended_browse_node: Mapping not found")
            return ""

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("get_recommended_browse_node: %s at %s", e, str(exc_tb.tb_lineno))
        return ""


def get_category_mapping(category_mapping_pk):

    category_mapping = CategoryMapping.objects.get(pk=category_mapping_pk)

    all_data_category_mapping = {}
    all_data_category_mapping['pk'] = category_mapping.pk
    all_data_category_mapping['atp_thresold'] = category_mapping.atp_thresold
    all_data_category_mapping['holding_thresold'] = category_mapping.holding_thresold
    all_data_category_mapping['recommended_browse_node'] = category_mapping.recommended_browse_node

    return all_data_category_mapping
    
def isNoneOrEmpty(variable):

    try :

        if variable == None or variable =="None" or variable == "":
            return True

        return False

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("isNoneOrEmpty: %s at %s", e, str(exc_tb.tb_lineno))
        return True

def generate_random_password(length):
    chars = string.ascii_uppercase + string.digits + string.ascii_lowercase
    password = ''
    for i in range(length):
        password += chars[ord(os.urandom(1)) % len(chars)]
    return password

def is_oc_user(user_obj):
    if OmnyCommUser.objects.filter(username=user_obj.username).exists():
        return True
    return False


def bulk_update_dealshub_product_price_or_stock_or_status(oc_uuid,path,filename, location_group_obj, update_type):
    try:
        
        dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
        dfs.fillna("")
        rows = len(dfs.iloc[:])

        workbook = xlsxwriter.Workbook('./'+filename)
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
            try:
                cnt += 1
                product_id = str(dfs.iloc[i][0]).strip()
                product_id = product_id.split(".")[0]

                common_row = ["" for i in range(len(row))]
                common_row[0] = str(cnt)
                common_row[1] = product_id

                if DealsHubProduct.objects.filter(location_group=location_group_obj, product__product_id=product_id).exists():
                    dh_product_obj = DealsHubProduct.objects.get(location_group=location_group_obj, product__product_id=product_id)
                    if update_type == "stock":
                        stock = float(dfs.iloc[i][1])
                        dh_product_obj.stock = stock
                        dh_product_obj.save()
                    elif update_type == "price":
                        now_price = float(dfs.iloc[i][1])
                        was_price = float(dfs.iloc[i][2])
                        dh_product_obj.now_price = now_price
                        dh_product_obj.was_price = was_price
                        dh_product_obj.save()
                    elif update_type == "status":
                        is_cod_allowed = str(dfs.iloc[i][1]).strip().lower()
                        is_promo_restricted = str(dfs.iloc[i][2]).strip().lower()
                        is_new_arrival = str(dfs.iloc[i][3]).strip().lower()
                        is_on_sale = str(dfs.iloc[i][4]).strip().lower()
                        is_promotional = str(dfs.iloc[i][5]).strip().lower()
                        if is_cod_allowed =='true':
                            is_cod_allowed = True
                        elif is_cod_allowed =='false':
                            is_cod_allowed=False
                        else:
                            common_row[2]='COD value is not proper.'
                            continue
                        if is_promo_restricted =='true':
                            is_promo_restricted = True
                        elif is_promo_restricted =='false':
                            is_promo_restricted=False
                        else:
                            common_row[2]='Promo restricted value is not proper.'
                            continue
                        if is_new_arrival =='true':
                            is_new_arrival = True
                        elif is_new_arrival =='false':
                            is_new_arrival=False
                        else:
                            common_row[2]='New arrival value is not proper.'
                            continue
                        if is_on_sale =='true':
                            is_on_sale = True
                        elif is_on_sale =='false':
                            is_on_sale=False
                        else:
                            common_row[2]='On sale value is not proper.'
                            continue
                        if is_promotional =='true':
                            is_promotional = True
                        elif is_promotional =='false':
                            is_promotional=False
                        else:
                            common_row[2]='Promotional value is not proper.'
                            continue
                        
                        logger.info("test after %s",str(dh_product_obj.__dict__))

                        dh_product_obj.is_cod_allowed = is_cod_allowed
                        dh_product_obj.is_promo_restricted = is_promo_restricted
                        dh_product_obj.is_new_arrival = is_new_arrival
                        dh_product_obj.is_on_sale = is_on_sale
                        
                        promotion_obj = dh_product_obj.promotion
                        if dh_product_obj.is_promotional == False and promotion_obj != None:
                                common_row[2] = "Already in Promotion"
                                continue
                        if is_promotional:
                            promotional_tag = str(dfs.iloc[i][6])
                            start_date = datetime.datetime.strptime(str(dfs.iloc[i][7]), "%Y-%m-%d %H:%M:%S")
                            end_date = datetime.datetime.strptime(str(dfs.iloc[i][8]), "%Y-%m-%d %H:%M:%S")
                            try :
                                promotional_price = float(str(dfs.iloc[i][9]))
                                if promotional_price <=0:
                                    common_row[2]='Promotional price cannot be 0.'
                                    continue
                            except :
                                common_row[2]='Promotional price is not proper.'
                                continue
                            if promotion_obj==None:
                                promotion_obj = Promotion.objects.create(promotion_tag=promotional_tag, start_time=start_date, end_time=end_date)
                            else:
                                promotion_obj.promotion_tag = promotional_tag
                                promotion_obj.start_time = start_date
                                promotion_obj.end_time = end_date
                                promotion_obj.save()
                            dh_product_obj.is_promotional = True
                            dh_product_obj.promotional_price = promotional_price
                        else:
                            if dh_product_obj.is_promotional==True:
                                promotion_obj = None
                                dh_product_obj.is_promotional = False
                        dh_product_obj.promotion = promotion_obj
                        dh_product_obj.save()
                        logger.info("test after %s",str(dh_product_obj.__dict__))
                    common_row[2] = "success"
                else:
                    common_row[2] = "Product {} not exists.".format(product_id)
                colnum = 0
                for k in common_row:
                    worksheet.write(cnt, colnum, k)
                    colnum += 1

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("bulk_update_dealshub_product_price_or_stock_or_status: %s at %s", e, str(exc_tb.tb_lineno))
            
        workbook.close()

        oc_report_obj = OCReport.objects.get(uuid=oc_uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("bulk_update_dealshub_product_price_or_stock_or_status: %s at %s", e, str(exc_tb.tb_lineno))


def bulk_update_b2b_dealshub_product_price(oc_uuid,path,filename, location_group_obj):
    try:
        dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
        dfs.fillna("")
        rows = len(dfs.iloc[:])

        workbook = xlsxwriter.Workbook('./'+filename)
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
            try:
                cnt += 1
                product_id = str(dfs.iloc[i][0]).strip()
                product_id = product_id.split(".")[0]

                common_row = ["" for i in range(len(row))]
                common_row[0] = str(cnt)
                common_row[1] = product_id

                if DealsHubProduct.objects.filter(location_group=location_group_obj, product__product_id=product_id).exists():
                    dealshub_product_obj = DealsHubProduct.objects.get(location_group=location_group_obj, product__product_id=product_id)
                    if str(dfs.iloc[i][1]) != "nan" and str(dfs.iloc[i][1]) != "":
                        now_price = float(dfs.iloc[i][1])
                        dealshub_product_obj.now_price = now_price

                    if str(dfs.iloc[i][2]) != "nan" and str(dfs.iloc[i][2]) != "":
                        now_price_cohort1 = float(dfs.iloc[i][2])
                        dealshub_product_obj.now_price_cohort1 = now_price_cohort1

                    if str(dfs.iloc[i][3]) != "nan" and str(dfs.iloc[i][3]) != "":
                        now_price_cohort2 = float(dfs.iloc[i][3])
                        dealshub_product_obj.now_price_cohort2 = now_price_cohort2

                    if str(dfs.iloc[i][4]) != "nan" and str(dfs.iloc[i][4]) != "":
                        now_price_cohort3 = float(dfs.iloc[i][4])
                        dealshub_product_obj.now_price_cohort3 = now_price_cohort3

                    if str(dfs.iloc[i][5]) != "nan" and str(dfs.iloc[i][5]) != "":
                        now_price_cohort4 = float(dfs.iloc[i][5])
                        dealshub_product_obj.now_price_cohort4 = now_price_cohort4

                    if str(dfs.iloc[i][6]) != "nan" and str(dfs.iloc[i][6]) != "":
                        now_price_cohort5 = float(dfs.iloc[i][6])
                        dealshub_product_obj.now_price_cohort5 = now_price_cohort5

                    if str(dfs.iloc[i][7]) != "nan" and str(dfs.iloc[i][7]) != "":
                        promotional_price = float(dfs.iloc[i][7])
                        dealshub_product_obj.promotional_price = promotional_price

                    if str(dfs.iloc[i][8]) != "nan" and str(dfs.iloc[i][8]) != "":
                        promotional_price_cohort1 = float(dfs.iloc[i][8])
                        dealshub_product_obj.promotional_price_cohort1 = promotional_price_cohort1

                    if str(dfs.iloc[i][9]) != "nan" and str(dfs.iloc[i][9]) != "":
                        promotional_price_cohort2 = float(dfs.iloc[i][9])
                        dealshub_product_obj.promotional_price_cohort2 = promotional_price_cohort2

                    if str(dfs.iloc[i][10]) != "nan" and str(dfs.iloc[i][10]) != "":
                        promotional_price_cohort3 = float(dfs.iloc[i][10])
                        dealshub_product_obj.promotional_price_cohort3 = promotional_price_cohort3

                    if str(dfs.iloc[i][11]) != "nan" and str(dfs.iloc[i][11]) != "":
                        promotional_price_cohort4 = float(dfs.iloc[i][11])
                        dealshub_product_obj.promotional_price_cohort4 = promotional_price_cohort4

                    if str(dfs.iloc[i][12]) != "nan" and str(dfs.iloc[i][12]) != "":
                        promotional_price_cohort5 = float(dfs.iloc[i][12])
                        dealshub_product_obj.promotional_price_cohort5 = promotional_price_cohort5

                    dealshub_product_obj.save()
                    common_row[2] = "success"
                else:
                    common_row[2] = "fail"

                colnum = 0
                for k in common_row:
                    worksheet.write(cnt, colnum, k)
                    colnum += 1

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("bulk_update_b2b_dealshub_product_price: %s at %s", e, str(exc_tb.tb_lineno))
        
        workbook.close()

        oc_report_obj = OCReport.objects.get(uuid=oc_uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("bulk_update_b2b_dealshub_product_price: %s at %s", e, str(exc_tb.tb_lineno))


def bulk_update_b2b_dealshub_product_moq(oc_uuid,path,filename, location_group_obj):
    try:
        dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
        dfs.fillna("")
        rows = len(dfs.iloc[:])

        workbook = xlsxwriter.Workbook('./'+filename)
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
            try:
                cnt += 1
                product_id = str(dfs.iloc[i][0]).strip()
                product_id = product_id.split(".")[0]

                common_row = ["" for i in range(len(row))]
                common_row[0] = str(cnt)
                common_row[1] = product_id

                if DealsHubProduct.objects.filter(location_group=location_group_obj, product__product_id=product_id).exists():
                    dealshub_product_obj = DealsHubProduct.objects.get(location_group=location_group_obj, product__product_id=product_id)
                    if str(dfs.iloc[i][1]) != "nan" and str(dfs.iloc[i][1]) != "":
                        moq = int(dfs.iloc[i][1])
                        dealshub_product_obj.moq = moq

                    if str(dfs.iloc[i][2]) != "nan" and str(dfs.iloc[i][2]) != "":
                        moq_cohort1 = int(dfs.iloc[i][2])
                        dealshub_product_obj.moq_cohort1 = moq_cohort1

                    if str(dfs.iloc[i][3]) != "nan" and str(dfs.iloc[i][3]) != "":
                        moq_cohort2 = int(dfs.iloc[i][3])
                        dealshub_product_obj.moq_cohort2 = moq_cohort2

                    if str(dfs.iloc[i][4]) != "nan" and str(dfs.iloc[i][4]) != "":
                        moq_cohort3 = int(dfs.iloc[i][4])
                        dealshub_product_obj.moq_cohort3 = moq_cohort3

                    if str(dfs.iloc[i][5]) != "nan" and str(dfs.iloc[i][5]) != "":
                        moq_cohort4 = int(dfs.iloc[i][5])
                        dealshub_product_obj.moq_cohort4 = moq_cohort4

                    if str(dfs.iloc[i][6]) != "nan" and str(dfs.iloc[i][6]) != "":
                        moq_cohort5 = int(dfs.iloc[i][6])
                        dealshub_product_obj.moq_cohort5 = moq_cohort5

                    dealshub_product_obj.save()
                    common_row[2] = "success"
                else:
                    common_row[2] = "fail"

                colnum = 0
                for k in common_row:
                    worksheet.write(cnt, colnum, k)
                    colnum += 1

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("bulk_update_b2b_dealshub_product_moq: %s at %s", e, str(exc_tb.tb_lineno))
        
        workbook.close()

        oc_report_obj = OCReport.objects.get(uuid=oc_uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("bulk_update_b2b_dealshub_product_moq: %s at %s", e, str(exc_tb.tb_lineno))


def activitylog(user,table_name,action_type,table_item_pk='',prev_instance=None,current_instance=None,location_group_obj=None,render=''):
    try:
        if render == "":
            render = "pk :- {} is {} in model {}".format(table_item_pk,action_type,table_name)
        
        if prev_instance!=None:
            prev_instance = convert_django_object_to_object(table_name,prev_instance)
        else:
            prev_instance = {}
        if current_instance!=None:
            current_instance = convert_django_object_to_object(table_name,current_instance)
        else:
            current_instance = {}
        
        ActivityLog.objects.create(
            user=user,
            location_group = location_group_obj,
            table_name = table_name._meta.object_name,
            table_item_pk = table_item_pk,
            action_type = action_type,
            prev_instance = json.dumps(prev_instance),
            current_instance = json.dumps(current_instance),
            render = render
            )
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("activitylog: %s at %s", e, str(exc_tb.tb_lineno))


def convert_django_object_to_object(model_name,django_object):
    result = {}
    for field in model_name._meta.get_fields():
        try:
            field_object = model_name._meta.get_field(field.name)
            field_value = str(field_object.value_from_object(django_object))
            result[field.name] = field_value
        except Exception as e:
            pass
    return result

