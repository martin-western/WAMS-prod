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
import pandas as pd


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
