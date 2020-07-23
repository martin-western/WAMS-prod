from WAMSApp.models import *
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

from django.db.models import Q
from django.db.models import Count

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


def generate_dynamic_row(data_point_list):

    row = ["Sr. No."]
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
        if data_point_variable=="pfl_product_feature_1":
            pfl_product_features = json.loads(product_obj.pfl_product_features)
            if len(pfl_product_features)>=1:
                return pfl_product_features[0]
            return ""
        if data_point_variable=="pfl_product_feature_2":
            pfl_product_features = json.loads(product_obj.pfl_product_features)
            if len(pfl_product_features)>=2:
                return pfl_product_features[1]
            return ""
        if data_point_variable=="pfl_product_feature_3":
            pfl_product_features = json.loads(product_obj.pfl_product_features)
            if len(pfl_product_features)>=3:
                return pfl_product_features[2]
            return ""
        if data_point_variable=="pfl_product_feature_4":
            pfl_product_features = json.loads(product_obj.pfl_product_features)
            if len(pfl_product_features)>=4:
                return pfl_product_features[3]
            return ""
        if data_point_variable=="pfl_product_feature_5":
            pfl_product_features = json.loads(product_obj.pfl_product_features)
            if len(pfl_product_features)>=5:
                return pfl_product_features[4]
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

        if data_point_variable=="main_image":
            if MainImages.objects.get(product=product_obj, is_sourced=True).main_images.count()>0:
                return MainImages.objects.get(product=product_obj, is_sourced=True).main_images.all()[0].image.image.url
            return ""

        if data_point_variable=="sub_image_1":
            if SubImages.objects.get(product=product_obj, is_sourced=True).sub_images.count()>0:
                return SubImages.objects.get(product=product_obj, is_sourced=True).sub_images.all()[0].image.image.url
            return ""
        if data_point_variable=="sub_image_2":
            if SubImages.objects.get(product=product_obj, is_sourced=True).sub_images.count()>1:
                return SubImages.objects.get(product=product_obj, is_sourced=True).sub_images.all()[1].image.image.url
            return ""
        if data_point_variable=="sub_image_3":
            if SubImages.objects.get(product=product_obj, is_sourced=True).sub_images.count()>2:
                return SubImages.objects.get(product=product_obj, is_sourced=True).sub_images.all()[2].image.image.url
            return ""
        if data_point_variable=="sub_image_4":
            if SubImages.objects.get(product=product_obj, is_sourced=True).sub_images.count()>3:
                return SubImages.objects.get(product=product_obj, is_sourced=True).sub_images.all()[3].image.image.url
            return ""
        if data_point_variable=="sub_image_5":
            if SubImages.objects.get(product=product_obj, is_sourced=True).sub_images.count()>4:
                return SubImages.objects.get(product=product_obj, is_sourced=True).sub_images.all()[4].image.image.url
            return ""

        if data_point_variable=="white_background_image_1":
            if product_obj.white_background_images.count()>=1:
                return product_obj.white_background_images.all()[0].image.url
            return ""
        if data_point_variable=="white_background_image_2":
            if product_obj.white_background_images.count()>=2:
                return product_obj.white_background_images.all()[1].image.url
            return ""
        if data_point_variable=="white_background_image_3":
            if product_obj.white_background_images.count()>=3:
                return product_obj.white_background_images.all()[2].image.url
            return ""
        if data_point_variable=="white_background_image_4":
            if product_obj.white_background_images.count()>=4:
                return product_obj.white_background_images.all()[3].image.url
            return ""
        if data_point_variable=="white_background_image_5":
            if product_obj.white_background_images.count()>=5:
                return product_obj.white_background_images.all()[4].image.url
            return ""

        if data_point_variable=="lifestyle_image_1":
            if product_obj.lifestyle_images.count()>=1:
                return product_obj.lifestyle_images.all()[0].image.url
            return ""
        if data_point_variable=="lifestyle_image_2":
            if product_obj.lifestyle_images.count()>=2:
                return product_obj.lifestyle_images.all()[1].image.url
            return ""
        if data_point_variable=="lifestyle_image_3":
            if product_obj.lifestyle_images.count()>=3:
                return product_obj.lifestyle_images.all()[2].image.url
            return ""
        if data_point_variable=="lifestyle_image_4":
            if product_obj.lifestyle_images.count()>=4:
                return product_obj.lifestyle_images.all()[3].image.url
            return ""
        if data_point_variable=="lifestyle_image_5":
            if product_obj.lifestyle_images.count()>=5:
                return product_obj.lifestyle_images.all()[4].image.url
            return ""

        if data_point_variable=="certificate_image_1":
            if product_obj.certificate_images.count()>=1:
                return product_obj.certificate_images.all()[0].image.url
            return ""
        if data_point_variable=="certificate_image_2":
            if product_obj.certificate_images.count()>=2:
                return product_obj.certificate_images.all()[1].image.url
            return ""
        if data_point_variable=="certificate_image_3":
            if product_obj.certificate_images.count()>=3:
                return product_obj.certificate_images.all()[2].image.url
            return ""
        if data_point_variable=="certificate_image_4":
            if product_obj.certificate_images.count()>=4:
                return product_obj.certificate_images.all()[3].image.url
            return ""
        if data_point_variable=="certificate_image_5":
            if product_obj.certificate_images.count()>=5:
                return product_obj.certificate_images.all()[4].image.url
            return ""

        if data_point_variable=="giftbox_image_1":
            if product_obj.giftbox_images.count()>=1:
                return product_obj.giftbox_images.all()[0].image.url
            return ""
        if data_point_variable=="giftbox_image_2":
            if product_obj.giftbox_images.count()>=2:
                return product_obj.giftbox_images.all()[1].image.url
            return ""
        if data_point_variable=="giftbox_image_3":
            if product_obj.giftbox_images.count()>=3:
                return product_obj.giftbox_images.all()[2].image.url
            return ""
        if data_point_variable=="giftbox_image_4":
            if product_obj.giftbox_images.count()>=4:
                return product_obj.giftbox_images.all()[3].image.url
            return ""
        if data_point_variable=="giftbox_image_5":
            if product_obj.giftbox_images.count()>=5:
                return product_obj.giftbox_images.all()[4].image.url
            return ""

        if data_point_variable=="diecut_image_1":
            if product_obj.diecut_images.count()>=1:
                return product_obj.diecut_images.all()[0].image.url
            return ""
        if data_point_variable=="diecut_image_2":
            if product_obj.diecut_images.count()>=2:
                return product_obj.diecut_images.all()[1].image.url
            return ""
        if data_point_variable=="diecut_image_3":
            if product_obj.diecut_images.count()>=3:
                return product_obj.diecut_images.all()[2].image.url
            return ""
        if data_point_variable=="diecut_image_4":
            if product_obj.diecut_images.count()>=4:
                return product_obj.diecut_images.all()[3].image.url
            return ""
        if data_point_variable=="diecut_image_5":
            if product_obj.diecut_images.count()>=5:
                return product_obj.diecut_images.all()[4].image.url
            return ""

        if data_point_variable=="aplus_content_image_1":
            if product_obj.aplus_content_images.count()>=1:
                return product_obj.aplus_content_images.all()[0].image.url
            return ""
        if data_point_variable=="aplus_content_image_2":
            if product_obj.aplus_content_images.count()>=2:
                return product_obj.aplus_content_images.all()[1].image.url
            return ""
        if data_point_variable=="aplus_content_image_3":
            if product_obj.aplus_content_images.count()>=3:
                return product_obj.aplus_content_images.all()[2].image.url
            return ""
        if data_point_variable=="aplus_content_image_4":
            if product_obj.aplus_content_images.count()>=4:
                return product_obj.aplus_content_images.all()[3].image.url
            return ""
        if data_point_variable=="aplus_content_image_5":
            if product_obj.aplus_content_images.count()>=5:
                return product_obj.aplus_content_images.all()[4].image.url
            return ""

        if data_point_variable=="ads_image_1":
            if product_obj.ads_images.count()>=1:
                return product_obj.ads_images.all()[0].image.url
            return ""
        if data_point_variable=="ads_image_2":
            if product_obj.ads_images.count()>=2:
                return product_obj.ads_images.all()[1].image.url
            return ""
        if data_point_variable=="ads_image_3":
            if product_obj.ads_images.count()>=3:
                return product_obj.ads_images.all()[2].image.url
            return ""
        if data_point_variable=="ads_image_4":
            if product_obj.ads_images.count()>=4:
                return product_obj.ads_images.all()[3].image.url
            return ""
        if data_point_variable=="ads_image_5":
            if product_obj.ads_images.count()>=5:
                return product_obj.ads_images.all()[4].image.url
            return ""

        if data_point_variable=="transparent_image_1":
            if product_obj.transparent_images.count()>=1:
                return product_obj.transparent_images.all()[0].image.url
            return ""
        if data_point_variable=="transparent_image_2":
            if product_obj.transparent_images.count()>=2:
                return product_obj.transparent_images.all()[1].image.url
            return ""
        if data_point_variable=="transparent_image_3":
            if product_obj.transparent_images.count()>=3:
                return product_obj.transparent_images.all()[2].image.url
            return ""
        if data_point_variable=="transparent_image_4":
            if product_obj.transparent_images.count()>=4:
                return product_obj.transparent_images.all()[3].image.url
            return ""
        if data_point_variable=="transparent_image_5":
            if product_obj.transparent_images.count()>=5:
                return product_obj.transparent_images.all()[4].image.url
            return ""


        if data_point_variable=="pfl_image_1":
            if product_obj.pfl_images.count()>=1:
                return product_obj.pfl_images.all()[0].image.url
            return ""
        if data_point_variable=="pfl_image_2":
            if product_obj.pfl_images.count()>=2:
                return product_obj.pfl_images.all()[1].image.url
            return ""
        if data_point_variable=="pfl_image_3":
            if product_obj.pfl_images.count()>=3:
                return product_obj.pfl_images.all()[2].image.url
            return ""
        if data_point_variable=="pfl_image_4":
            if product_obj.pfl_images.count()>=4:
                return product_obj.pfl_images.all()[3].image.url
            return ""
        if data_point_variable=="pfl_image_5":
            if product_obj.pfl_images.count()>=5:
                return product_obj.pfl_images.all()[4].image.url
            return ""


        if data_point_variable=="pfl_generated_image_1":
            if product_obj.pfl_images.count()>=1:
                return product_obj.pfl_generated_images.all()[0].image.url
            return ""
        if data_point_variable=="pfl_generated_image_2":
            if product_obj.pfl_images.count()>=2:
                return product_obj.pfl_generated_images.all()[1].image.url
            return ""
        if data_point_variable=="pfl_generated_image_3":
            if product_obj.pfl_images.count()>=3:
                return product_obj.pfl_generated_images.all()[2].image.url
            return ""
        if data_point_variable=="pfl_generated_image_4":
            if product_obj.pfl_images.count()>=4:
                return product_obj.pfl_generated_images.all()[3].image.url
            return ""
        if data_point_variable=="pfl_generated_image_5":
            if product_obj.pfl_images.count()>=5:
                return product_obj.pfl_generated_images.all()[4].image.url
            return ""


        if data_point_variable=="unedited_image_1":
            if base_product_obj.unedited_images.count()>=1:
                return base_product_obj.unedited_images.all()[0].image.url
            return ""
        if data_point_variable=="unedited_image_2":
            if base_product_obj.unedited_images.count()>=2:
                return base_product_obj.unedited_images.all()[1].image.url
            return ""
        if data_point_variable=="unedited_image_3":
            if base_product_obj.unedited_images.count()>=3:
                return base_product_obj.unedited_images.all()[2].image.url
            return ""
        if data_point_variable=="unedited_image_4":
            if base_product_obj.unedited_images.count()>=4:
                return base_product_obj.unedited_images.all()[3].image.url
            return ""
        if data_point_variable=="unedited_image_5":
            if base_product_obj.unedited_images.count()>=5:
                return base_product_obj.unedited_images.all()[4].image.url
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
        
        dimensions = json.loads(base_product.dimensions)
        if data_point_variable in dimensions:
            return dimensions[data_point_variable]
        
        amazon_uk_product_json = json.loads(channel_product_obj.amazon_uk_product_json)

        if data_point_variable=="amazonuk_product_name":
            return amazon_uk_product_json["product_name"]
        if data_point_variable=="amazonuk_product_description":
            return amazon_uk_product_json["product_description"]

        if data_point_variable=="amazonuk_product_attribute_list_1":
            if len(amazon_uk_product_json["product_attribute_list"])>0:
                return amazon_uk_product_json["product_attribute_list"][0]
            else:
                return ""
        if data_point_variable=="amazonuk_product_attribute_list_2":
            if len(amazon_uk_product_json["product_attribute_list"])>1:
                return amazon_uk_product_json["product_attribute_list"][1]
            else:
                return ""
        if data_point_variable=="amazonuk_product_attribute_list_3":
            if len(amazon_uk_product_json["product_attribute_list"])>2:
                return amazon_uk_product_json["product_attribute_list"][2]
            else:
                return ""
        if data_point_variable=="amazonuk_product_attribute_list_4":
            if len(amazon_uk_product_json["product_attribute_list"])>3:
                return amazon_uk_product_json["product_attribute_list"][3]
            else:
                return ""
        if data_point_variable=="amazonuk_product_attribute_list_5":
            if len(amazon_uk_product_json["product_attribute_list"])>4:
                return amazon_uk_product_json["product_attribute_list"][4]
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
        if data_point_variable=="amazonuk_special_feature_1":
            if len(amazon_uk_product_json["special_features"])>0:
                return amazon_uk_product_json["special_features"][0]
            else:
                return ""
        if data_point_variable=="amazonuk_special_feature_2":
            if len(amazon_uk_product_json["special_features"])>1:
                return amazon_uk_product_json["special_features"][1]
            else:
                return ""
        if data_point_variable=="amazonuk_special_feature_3":
            if len(amazon_uk_product_json["special_features"])>2:
                return amazon_uk_product_json["special_features"][2]
            else:
                return ""
        if data_point_variable=="amazonuk_special_feature_4":
            if len(amazon_uk_product_json["special_features"])>3:
                return amazon_uk_product_json["special_features"][3]
            else:
                return ""
        if data_point_variable=="amazonuk_special_feature_5":
            if len(amazon_uk_product_json["special_features"])>4:
                return amazon_uk_product_json["special_features"][4]
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
            return amazon_uk_product_json["dimensions"]["item_weight_metric"]
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
        if data_point_variable=="amazonuk_item_heigth_metric":
            return amazon_uk_product_json["dimensions"]["item_heigth_metric"]
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

        
        amazon_uae_product_json = json.loads(channel_product_obj.amazon_uae_product_json)

        if data_point_variable=="amazonuae_product_name":
            return amazon_uae_product_json["product_name"]
        if data_point_variable=="amazonuae_product_description":
            return amazon_uae_product_json["product_description"]

        if data_point_variable=="amazonuae_product_attribute_list_1":
            if len(amazon_uae_product_json["product_attribute_list"])>0:
                return amazon_uae_product_json["product_attribute_list"][0]
            else:
                return ""
        if data_point_variable=="amazonuae_product_attribute_list_2":
            if len(amazon_uae_product_json["product_attribute_list"])>1:
                return amazon_uae_product_json["product_attribute_list"][1]
            else:
                return ""
        if data_point_variable=="amazonuae_product_attribute_list_3":
            if len(amazon_uae_product_json["product_attribute_list"])>2:
                return amazon_uae_product_json["product_attribute_list"][2]
            else:
                return ""
        if data_point_variable=="amazonuae_product_attribute_list_4":
            if len(amazon_uae_product_json["product_attribute_list"])>3:
                return amazon_uae_product_json["product_attribute_list"][3]
            else:
                return ""
        if data_point_variable=="amazonuae_product_attribute_list_5":
            if len(amazon_uae_product_json["product_attribute_list"])>4:
                return amazon_uae_product_json["product_attribute_list"][4]
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

        ebay_product_json = json.loads(channel_product_obj.ebay_product_json)

        if data_point_variable=="ebay_category":
            return ebay_product_json["category"]
        if data_point_variable=="ebay_sub_category":
            return ebay_product_json["sub_category"]
        if data_point_variable=="ebay_product_name":
            return ebay_product_json["product_name"]
        if data_point_variable=="ebay_product_description":
            return ebay_product_json["product_description"]
        if data_point_variable=="ebay_product_attribute_list_1":
            if len(ebay_product_json["product_attribute_list"])>0:
                return ebay_product_json["product_attribute_list"][0]
            else:
                return ""
        if data_point_variable=="ebay_product_attribute_list_2":
            if len(ebay_product_json["product_attribute_list"])>1:
                return ebay_product_json["product_attribute_list"][1]
            else:
                return ""
        if data_point_variable=="ebay_product_attribute_list_3":
            if len(ebay_product_json["product_attribute_list"])>2:
                return ebay_product_json["product_attribute_list"][2]
            else:
                return ""
        if data_point_variable=="ebay_product_attribute_list_4":
            if len(ebay_product_json["product_attribute_list"])>3:
                return ebay_product_json["product_attribute_list"][3]
            else:
                return ""
        if data_point_variable=="ebay_product_attribute_list_5":
            if len(ebay_product_json["product_attribute_list"])>4:
                return ebay_product_json["product_attribute_list"][4]
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
        if data_point_variable=="product_attribute_list_1":
            if len(noon_product_json["product_attribute_list"])>0:
                return noon_product_json["product_attribute_list"][0]
            else:
                return ""
        if data_point_variable=="product_attribute_list_2":
            if len(noon_product_json["product_attribute_list"])>1:
                return noon_product_json["product_attribute_list"][1]
            else:
                return ""
        if data_point_variable=="product_attribute_list_3":
            if len(noon_product_json["product_attribute_list"])>2:
                return noon_product_json["product_attribute_list"][2]
            else:
                return ""
        if data_point_variable=="product_attribute_list_4":
            if len(noon_product_json["product_attribute_list"])>3:
                return noon_product_json["product_attribute_list"][3]
            else:
                return ""
        if data_point_variable=="product_attribute_list_5":
            if len(noon_product_json["product_attribute_list"])>4:
                return noon_product_json["product_attribute_list"][4]
            else:
                return ""
        if data_point_variable=="noon_http_link":
            return noon_product_json["http_link"]
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("get_data_value: %s at %s", e, str(exc_tb.tb_lineno))
        return ""


def generate_dynamic_export(product_uuid_list, data_point_list):

    try:
        os.system("rm ./files/csv/dynamic_export.xlsx")
    except Exception as e:
        pass

    workbook = xlsxwriter.Workbook('./files/csv/dynamic_export.xlsx')
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
           "Selling Price",
           "Delivery Fee",
           "Strike Price",
           "Quantity",
           "Customer Name",
           "Customer Email ID",
           "Customer Phone Number",
           "Billing Address",
           "Shipping Address",
           "Payment Status",
           "Shipping Method",
           "Order Tracking Status"]

    cnt = 0
        
    colnum = 0
    for k in row:
        worksheet.write(cnt, colnum, k)
        colnum += 1

    for unit_order in unit_order_list:
        try:
            cnt += 1

            product_obj = Product.objects.get(uuid=unit_order["productUuid"])
            dh_product_obj = DealsHubProduct.objects.get(product=product_obj)

            common_row = ["" for i in range(21)]
            common_row[0] = str(cnt)
            common_row[1] = unit_order["orderPlacedDate"]
            common_row[2] = unit_order["bundleId"]
            common_row[3] = unit_order["orderId"]
            common_row[4] = "WIGme"
            common_row[5] = product_obj.product_name
            common_row[6] = product_obj.product_id
            common_row[7] = product_obj.base_product.seller_sku
            common_row[8] = "AED"
            common_row[9] = unit_order["price"]
            common_row[10] = unit_order["deliveryFee"]
            common_row[11] = str(dh_product_obj.was_price)
            common_row[12] = unit_order["quantity"]
            common_row[13] = unit_order["customerName"]
            common_row[14] = unit_order["customerEmail"]
            common_row[15] = unit_order["customerContactNumber"]
            common_row[16] = unit_order["shippingAddress"]
            common_row[17] = unit_order["shippingAddress"]
            common_row[18] = unit_order["paymentStatus"]
            common_row[19] = unit_order["shippingMethod"]
            common_row[20] = unit_order["trackingStatus"]
            
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