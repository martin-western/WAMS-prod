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
        images_count += main_images_obj.main_images.all().count()

    sub_images_objs = SubImages.objects.filter(product=prod_obj)
    for sub_images_obj in sub_images_objs:
        images_count += sub_images_obj.sub_images.all().count()

    images_count += prod_obj.white_background_images.all().count()
    images_count += prod_obj.lifestyle_images.all().count()
    
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

def fetch_prices(product_id):
    try:
        url="http://94.56.89.114:8001/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"
        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = ("MOBSERVICE", "~lDT8+QklV=(")
        company_codes = ["1070","1000","6000","5550","5600","7000","5110","5100","3050","2100","5700","1100","3000","5000"] 
        
        warehouse_information = []

        for company_code in company_codes:
            
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
                temp_qty += item["TOT_QTY"]
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

            warehouse_information.append(warehouse_dict)

        return warehouse_information

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Fetch Prices: %s at %s", e, str(exc_tb.tb_lineno))
        return 0