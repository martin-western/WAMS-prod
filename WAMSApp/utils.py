from WAMSApp.models import *
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
import requests
import xmltodict
import json
from django.utils import timezone
import sys
import xlsxwriter


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

def fetch_prices(product_id,company_code):
    try:

        # Check if Cached
        product_obj = Product.objects.filter(base_product__seller_sku=product_id)[0]
        # curr_time = timezone.now()
        # if (product_obj.sap_cache_time-curr_time).seconds<86400:
        #      warehouse_information = json.loads(product_obj.sap_cache)
        #      return warehouse_information

        url="http://94.56.89.114:8001/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"
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
            
        # warehouse_information.append(warehouse_dict)

        product_obj.sap_cache = json.dumps(warehouse_dict)
        product_obj.save()
        
        return warehouse_dict

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Fetch Prices: %s at %s", e, str(exc_tb.tb_lineno))
        return []




def fetch_prices_dealshub(uuid1, company_code):
    try:
        product_obj = Product.objects.get(uuid=uuid1)
        product_id = product_obj.base_product.seller_sku

        url="http://94.56.89.114:8001/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"
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



def generate_images_report(product_objs):
    try:
        os.system("rm ./files/csv/images-count-report.xlsx")
    except Exception as e:
        pass

    workbook = xlsxwriter.Workbook('./files/csv/images-count-report.xlsx')
    worksheet = workbook.add_worksheet()

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


def generate_mega_bulk_upload(product_objs):

    workbook = xlsxwriter.Workbook('./files/csv/mega-bulk-export.xlsx')
    worksheet = workbook.add_worksheet()

    #products = Product.objects.filter(base_product__brand__name="geepas")
    row = ["Sr. No.",
           "Product ID*",
           "Product Name*",
           "Brand*",
           "Category*",
           "Sub Category*",
           "Seller SKU*",
           "Manufacturer",
           "M. Part Number",
           "Product ID Type*",
           "Description",
           "Feature 1",
           "Feature 2",
           "Feature 3",
           "Feature 4",
           "Feature 5",
           "Color",
           "Color Map",
           "Material Type",
           "Standard Price",
           "MOQ",
           "Barcode",
           "Export Qty Length",
           "Export Qty Length Metric",
           "Export Qty Breadth",
           "Export Qty Breadth Metric",
           "Export Qty Height",
           "Export Qty Height Metric",
           "Export Carton CBM Length",
           "Export Carton CBM Length Metric",
           "Export Carton CBM Breadth",
           "Export Carton CBM Breadth Metric",
           "Export Carton CBM Height",
           "Export Carton CBM Height Metric",
           "Product Dimension Length",
           "Product Dimension Length Metric",
           "Product Dimension Breadth",
           "Product Dimension Breadth Metric",
           "Product Dimension Height",
           "Product Dimension Height Metric",
           "GiftBox Length",
           "GiftBox Length Metric",
           "GiftBox Breadth",
           "GiftBox Breadth Metric",
           "GiftBox Height",
           "GiftBox Height Metric",
           "Main Image",
           "Sub Image 1",
           "Sub Image 2",
           "Sub Image 3",
           "Sub Image 4",
           "Sub Image 5",
           "White Background Image 1",
           "White Background Image 2",
           "White Background Image 3",
           "White Background Image 4",
           "White Background Image 5",
           "PFL Image 1",
           "PFL Image 2",
           "PFL Image 3",
           "PFL Image 4",
           "PFL Image 5",
           "Lifestyle Image 1",
           "Lifestyle Image 2",
           "Lifestyle Image 3",
           "Lifestyle Image 4",
           "Lifestyle Image 5",
           "Certificate Image 1",
           "Certificate Image 2",
           "Certificate Image 3",
           "Certificate Image 4",
           "Certificate Image 5",
           "Giftbox Image 1",
           "Giftbox Image 2",
           "Giftbox Image 3",
           "Giftbox Image 4",
           "Giftbox Image 5",
           "Diecut Image 1",
           "Diecut Image 2",
           "Diecut Image 3",
           "Diecut Image 4",
           "Diecut Image 5",
           "A+ Content Image 1",
           "A+ Content Image 2",
           "A+ Content Image 3",
           "A+ Content Image 4",
           "A+ Content Image 5",
           "Ads Image 1",
           "Ads Image 2",
           "Ads Image 3",
           "Ads Image 4",
           "Ads Image 5",
           "Unedited Image 1",
           "Unedited Image 2",
           "Unedited Image 3",
           "Unedited Image 4",
           "Unedited Image 5",
           "Transparent Image 1",
           "Transparent Image 2",
           "Transparent Image 3",
           "Transparent Image 4",
           "Transparent Image 5",
           "Is Amazon UK Channel",
           "Product Name",
           "Amazon UK Product Description*",
           "Attribute 1",
           "Attribute 2",
           "Attribute 3",
           "Attribute 4",
           "Attribute 5",
           "Category*",
           "SubCategory",
           "Parentage",
           "Parent SKU",
           "Relationship Type",
           "Variation Theme",
           "Feed Product Type",
           "Update Delete",
           "Recommended Browse Nodes",
           "Search Terms",
           "Enclosure Material",
           "Cover Material Type",
           "Special Feature 1",
           "Special Feature 2",
           "Special Feature 3",
           "Special Feature 4",
           "Special Feature 5",
           "Sale Price",
           "Sale From",
           "Sale End",
           "Wattage",
           "Wattage Metric",
           "Item Count",
           "Item Count Metric",
           "Item Condition Note",
           "MOQ",
           "No. Of. Items",
           "Condition Type",
           "Package Length",
           "Package Length Metric",
           "Package Width",
           "Package Width Metric",
           "Package Height",
           "Package Height Metric",
           "Package Weight",
           "Package Weight Metric",
           "Package Quantity",
           "Shipping Weight",
           "Shipping Weight Metric",
           "Item Display Weight",
           "Item Display Weight Metric",
           "Item Display Volume",
           "Item Display Volume Metric",
           "Item Display Length",
           "Item Display Length Metric",
           "Item Display Width",
           "Item Display Width Metric",
           "Item Display Height",
           "Item Display Height Metric",
           "Item Weight",
           "Item Weight Metric",
           "Item Length",
           "Item Length Metric",
           "Item Width",
           "Item Width Metric",
           "Item Height",
           "Item Height Metric",
           "Is Amazon UK Verified",
           "Is Amazon UAE Channel",
           "Product Name",
           "Amazon UAE Product Description*",
           "Attribute 1",
           "Attribute 2",
           "Attribute 3",
           "Attribute 4",
           "Attribute 5",
           "Category*",
           "SubCategory",
           "Feed Product Type",
           "Recommended Browse Nodes",
           "Update Delete",
           "Is Amazon UAE Verified",
           "Is Ebay Product",
           "Product Name",
           "Ebay Product Description*",
           "Attribute 1",
           "Attribute 2",
           "Attribute 3",
           "Attribute 4",
           "Attribute 5",
           "Category*",
           "SubCategory",
           "Is Ebay Verified",
           "Is Noon Product",
           "Product Name",
           "Noon Product Description*",
           "Product Type",
           "Product SubType",
           "Parent SKU",
           "Category*",
           "SubCategory",
           "Model Number",
           "Model Name",
           "Attribute 1",
           "Attribute 2",
           "Attribute 3",
           "Attribute 4",
           "Attribute 5",
           "MSRP AE",
           "MSRP AE Unit",
           "Is Noon Verified"]

    cnt = 0
        
    colnum = 0
    for k in row:
        worksheet.write(cnt, colnum, k)
        colnum += 1
    
    for product in product_objs:
        try:
            common_row = ["" for i in range(210)]
            cnt += 1
            common_row[0] = str(cnt)
            common_row[1] = product.product_id
            common_row[2] = product.product_name
            common_row[3] = str(product.base_product.brand)
            common_row[4] = str(product.base_product.category)
            common_row[5] = str(product.base_product.sub_category)
            common_row[6] = str(product.base_product.seller_sku)
            common_row[7] = str(product.base_product.manufacturer)
            common_row[8] = str(product.base_product.manufacturer_part_number)
            common_row[9] = str(product.product_id_type)
            common_row[10] = str(product.product_description)
            product_features = json.loads(product.pfl_product_features)[:5]
            for i in range(len(product_features)):
                common_row[11+i] = product_features[i]
            common_row[16] = str(product.color)
            common_row[17] = str(product.color_map)
            common_row[18] = str(product.material_type)
            common_row[19] = "" if product.standard_price==None else str(product.standard_price)
            common_row[20] = "" if product.quantity==None else str(product.quantity)
            common_row[21] = str(product.barcode_string)
            dimensions = json.loads(product.base_product.dimensions)


            common_row[22] = str(dimensions["export_carton_quantity_l"])
            common_row[23] = str(dimensions["export_carton_quantity_l_metric"])
            common_row[24] = str(dimensions["export_carton_quantity_b"])
            common_row[25] = str(dimensions["export_carton_quantity_b_metric"])
            common_row[26] = str(dimensions["export_carton_quantity_h"])
            common_row[27] = str(dimensions["export_carton_quantity_h_metric"])
            common_row[28] = str(dimensions["export_carton_crm_l"])
            common_row[29] = str(dimensions["export_carton_crm_l_metric"])
            common_row[30] = str(dimensions["export_carton_crm_b"])
            common_row[31] = str(dimensions["export_carton_crm_b_metric"])
            common_row[32] = str(dimensions["export_carton_crm_h"])
            common_row[33] = str(dimensions["export_carton_crm_h_metric"])
            common_row[34] = str(dimensions["product_dimension_l"])
            common_row[35] = str(dimensions["product_dimension_l_metric"])
            common_row[36] = str(dimensions["product_dimension_b"])
            common_row[37] = str(dimensions["product_dimension_b_metric"])
            common_row[38] = str(dimensions["product_dimension_h"])
            common_row[39] = str(dimensions["product_dimension_h_metric"])
            common_row[40] = str(dimensions["giftbox_l"])
            common_row[41] = str(dimensions["giftbox_l_metric"])
            common_row[42] = str(dimensions["giftbox_b"])
            common_row[43] = str(dimensions["giftbox_b_metric"])
            common_row[44] = str(dimensions["giftbox_h"])
            common_row[45] = str(dimensions["giftbox_h_metric"])

            try:
                main_images = MainImages.objects.get(product=product, is_sourced=True)
                main_image = main_images.main_images.all()[0]
                common_row[46] = main_image.image.image.url
            except Exception as e:
                pass

            try:
                sub_images = SubImages.objects.get(product=product, is_sourced=True)
                sub_images = sub_images.sub_images.all()[:5]
                iterr = 0
                for sub_image in sub_images:
                    common_row[47+iterr] = sub_image.image.image.url
                    iterr += 1
            except Exception as e:
                pass

            try:
                iterr = 0
                for image in product.white_background_images.all()[:5]:
                    common_row[52+iterr] = image.image.url
                    iterr += 1
            except Exception as e:
                pass

            try:            
                iterr = 0
                for image in product.pfl_images.all()[:5]:
                    common_row[57+iterr] = image.image.url
                    iterr += 1
            except Exception as e:
                pass

            try:
                iterr = 0
                for image in product.lifestyle_images.all()[:5]:
                    common_row[62+iterr] = image.image.url
                    iterr += 1
            except Exception as e:
                pass

            try:
                iterr = 0
                for image in product.certificate_images.all()[:5]:
                    common_row[67+iterr] = image.image.url
                    iterr += 1
            except Exception as e:
                pass

            try:
                iterr = 0
                for image in product.giftbox_images.all()[:5]:
                    common_row[72+iterr] = image.image.url
                    iterr += 1
            except Exception as e:
                pass

            try:
                iterr = 0
                for image in product.diecut_images.all()[:5]:
                    common_row[77+iterr] = image.image.url
                    iterr += 1
            except Exception as e:
                pass

            try:
                iterr = 0
                for image in product.aplus_content_images.all()[:5]:
                    common_row[82+iterr] = image.image.url
                    iterr += 1
            except Exception as e:
                pass

            try:
                iterr = 0
                for image in product.ads_images.all()[:5]:
                    common_row[87+iterr] = image.image.url
                    iterr += 1
            except Exception as e:
                pass

            try:
                iterr = 0
                for image in product.base_product.unedited_images.all()[:5]:
                    common_row[92+iterr] = image.image.url
                    iterr += 1
            except Exception as e:
                pass

            try:
                iterr = 0
                for image in product.transparent_images.all()[:5]:
                    common_row[97+iterr] = image.image.url
                    iterr += 1
            except Exception as e:
                pass
            ############################################ Amazon UK
            amazon_uk_product_json = json.loads(product.channel_product.amazon_uk_product_json)
            common_row[102] = str(product.channel_product.is_amazon_uk_product_created)
            common_row[103] = str(amazon_uk_product_json["product_name"])
            common_row[104] = str(amazon_uk_product_json["product_description"])
            attributes = amazon_uk_product_json["product_attribute_list"][:5]
            for i in range(len(attributes)):
                common_row[105+i] = str(attributes[i])
            common_row[110] = str(amazon_uk_product_json["category"])
            common_row[111] = str(amazon_uk_product_json["sub_category"])
            common_row[112] = str(amazon_uk_product_json["parentage"])
            common_row[113] = str(amazon_uk_product_json["parent_sku"])
            common_row[114] = str(amazon_uk_product_json["relationship_type"])
            common_row[115] = str(amazon_uk_product_json["variation_theme"])
            common_row[116] = str(amazon_uk_product_json["feed_product_type"])
            common_row[117] = str(amazon_uk_product_json["update_delete"])
            common_row[118] = str(amazon_uk_product_json["recommended_browse_nodes"])
            common_row[119] = str(amazon_uk_product_json["search_terms"])
            common_row[120] = str(amazon_uk_product_json["enclosure_material"])
            common_row[121] = str(amazon_uk_product_json["cover_material_type"])
            special_features = amazon_uk_product_json["special_features"][:5]
            for i in range(len(special_features)):
                common_row[122+i] = str(special_features[i])        
            common_row[127] = str(amazon_uk_product_json["sale_price"])
            common_row[128] = str(amazon_uk_product_json["sale_from"])
            common_row[129] = str(amazon_uk_product_json["sale_end"])
            common_row[130] = str(amazon_uk_product_json["wattage"])
            common_row[131] = str(amazon_uk_product_json["wattage_metric"])
            common_row[132] = str(amazon_uk_product_json["item_count"])
            common_row[133] = str(amazon_uk_product_json["item_count_metric"])
            common_row[134] = str(amazon_uk_product_json["item_condition_note"])
            common_row[135] = str(amazon_uk_product_json["max_order_quantity"])
            common_row[136] = str(amazon_uk_product_json["number_of_items"])
            common_row[137] = str(amazon_uk_product_json["condition_type"])
            dimensions = amazon_uk_product_json["dimensions"]
            common_row[138] = dimensions["package_length"]
            common_row[139] = dimensions["package_length_metric"]
            common_row[140] = dimensions["package_width"]
            common_row[141] = dimensions["package_width_metric"]
            common_row[142] = dimensions["package_height"]
            common_row[143] = dimensions["package_height_metric"]
            common_row[144] = dimensions["package_weight"]
            common_row[145] = dimensions["package_weight_metric"]
            #common_row[146] = dimensions["package_quantity"]
            common_row[147] = dimensions["shipping_weight"]
            common_row[148] = dimensions["shipping_weight_metric"]
            common_row[149] = dimensions["item_display_weight"]
            common_row[150] = dimensions["item_display_weight_metric"]
            common_row[151] = dimensions["item_display_volume"]
            common_row[152] = dimensions["item_display_volume_metric"]
            common_row[153] = dimensions["item_display_length"]
            common_row[154] = dimensions["item_display_length_metric"]
            common_row[155] = dimensions["item_display_width"]
            common_row[156] = dimensions["item_display_width_metric"]
            common_row[157] = dimensions["item_display_height"]
            common_row[158] = dimensions["item_display_height_metric"]
            common_row[159] = dimensions["item_weight"]
            common_row[160] = dimensions["item_weight_metric"]
            common_row[161] = dimensions["item_length"]
            common_row[162] = dimensions["item_length_metric"]
            common_row[163] = dimensions["item_width"]
            common_row[164] = dimensions["item_width_metric"]
            common_row[165] = dimensions["item_height"]
            common_row[166] = dimensions["item_height_metric"]

            #common_row[167] = amazon_verified
            amazon_uae_product_json = json.loads(product.channel_product.amazon_uae_product_json)
            common_row[168] = str(product.channel_product.is_amazon_uae_product_created)
            common_row[169] = amazon_uae_product_json["product_name"]
            common_row[170] = amazon_uae_product_json["product_description"]
            attributes = amazon_uae_product_json["product_attribute_list"][:5]
            for i in range(len(attributes)):
                common_row[171+i] = attributes[i]
            common_row[176] = amazon_uae_product_json["category"]
            common_row[177] = amazon_uae_product_json["sub_category"]
            common_row[178] = amazon_uae_product_json["feed_product_type"]
            common_row[179] = amazon_uae_product_json["recommended_browse_nodes"]
            common_row[180] = amazon_uae_product_json["update_delete"]
            #common_row[181] = amazon_verified
            ebay_product_json = json.loads(product.channel_product.ebay_product_json)
            common_row[182] = str(product.channel_product.is_ebay_product_created)
            common_row[183] = ebay_product_json["product_name"]
            common_row[184] = ebay_product_json["product_description"]
            attributes = ebay_product_json["product_attribute_list"][:5]
            for i in range(len(attributes)):
                common_row[185+i] = attributes[i]
            common_row[190] = ebay_product_json["category"]
            common_row[191] = ebay_product_json["sub_category"]
            #common_row[192] = ebay_verified
            noon_product_json = json.loads(product.channel_product.noon_product_json)
            common_row[193] = str(product.channel_product.is_noon_product_created)
            common_row[194] = noon_product_json["product_name"]
            common_row[195] = noon_product_json["product_description"]
            common_row[196] = noon_product_json["product_type"]
            common_row[197] = noon_product_json["product_subtype"]
            common_row[198] = noon_product_json["parent_sku"]
            common_row[199] = noon_product_json["category"]
            #common_row[200] = noon_product_json["subtitle"]
            common_row[201] = noon_product_json["model_number"]
            common_row[202] = noon_product_json["model_name"]
            attributes = noon_product_json["product_attribute_list"][:5]
            for i in range(len(attributes)):
                common_row[203+i] = attributes[i]
            common_row[208] = noon_product_json["msrp_ae"]
            common_row[209] = noon_product_json["msrp_ae_unit"]
            #common_row[210] = noon_verified
            colnum = 0
            for k in common_row:
                worksheet.write(cnt, colnum, k)
                colnum += 1
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print("Error ", e, str(exc_tb.tb_lineno))

    workbook.close()