from WAMSApp.models import *

import csv
import urllib
import os
import json
from django.utils import timezone
import sys
import xlsxwriter
import pandas as pd

company_code = "1000"
customer_id = "40000195"
product_id = "GAC9380"
qty = ""
uom = "EA"
charg = "BS"

test_url = "http://s4hdev.geepas.local:8000/sap/bc/srt/rfc/sap/zser_stock_price/150/zser_stock_price/zbin_stock_price"
production_url="http://wig.westernint.com:8000/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"

def fetch_prices(product_id,company_code,url,customer_id):
    
    try:

        # product_obj = Product.objects.filter(base_product__seller_sku=product_id)[0]

        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = ("MOBSERVICE", "~lDT8+QklV=(")
        
        warehouse_dict = {}
        body = """<soapenv:Envelope xmlns:urn="urn:sap-com:document:sap:rfc:functions" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
                    <soapenv:Header />
                    <soapenv:Body>
                    <urn:ZAPP_STOCK_PRICE>
                    <IM_KUNNR>"""+ customer_id +"""</IM_KUNNR>
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
                     <WERKS></WERKS>
                     <WWGHA1></WWGHA1>
                     <WWGHB1></WWGHB1>
                     <WWGHA2></WWGHA2>
                     <WWGHB2></WWGHB2>
                     <WWGHA3></WWGHA3>
                     <WWGHB3></WWGHB3>
                     <HQTY></HQTY>
                    </item>
                    </T_DATA>
                    </urn:ZAPP_STOCK_PRICE>
                    </soapenv:Body>
                    </soapenv:Envelope>"""

        import requests
        import xmltodict
        import json
        response2 = requests.post(url, auth=credentials, data=body, headers=headers)
        content = response2.content
        content = xmltodict.parse(content)
        content = json.loads(json.dumps(content))

        print(content)

        return content

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Fetch Prices: ", e , " at ", str(exc_tb.tb_lineno))
        
        return []

response = fetch_prices(product_id,company_code,production_url,customer_id)

"""
{ 
'soap-env:Envelope': {
    '@xmlns:soap-env': 'http://schemas.xmlsoap.org/soap/envelope/', 
    'soap-env:Header': None, 
    'soap-env:Body': {
        'n0:ZAPP_STOCK_PRICEResponse': {
            '@xmlns:n0': 'urn:sap-com:document:sap:rfc:functions', 
            'IM_MATNR': {
                'item': {
                    'MATNR': 'GAC9380'
                }
            }, 
            'IM_VKORG': {
                'item': {
                    'VKORG': '1000'
                }
            }, 'T_DATA': {
                'item': [{
                    'MATNR': None, 
                    'MAKTX': None, 
                    'LGORT': None, 
                    'CHARG': None, 
                    'SPART': None, 
                    'MEINS': None, 
                    'ATP_QTY': '0.0', 
                    'TOT_QTY': '0.0', 
                    'CURRENCY': None, 
                    'IC_EA': None, 
                    'OD_EA': None, 
                    'EX_EA': None, 
                    'RET_EA': None, 
                    'WERKS': None, 
                    'WWGHA1': None, 
                    'WWGHB1': None, 
                    'WWGHA2': None, 
                    'WWGHB2': None, 
                    'WWGHA3': None, 
                    'WWGHB3': None}, 
                    {
                    'MATNR': 'GAC9380', 
                    'MAKTX': '12" Air Cooler With Remote 5.5 L 1X1', 
                    'LGORT': 'AFS1', 
                    'CHARG': 'BS', 
                    'SPART': '01', 
                    'MEINS': 'EA', 
                    'ATP_QTY': '0.0', 
                    'TOT_QTY': '0.0', 
                    'CURRENCY': 'AED', 
                    'IC_EA': '272.00', 
                    'OD_EA': '335.00', 
                    'EX_EA': '280.00', 
                    'RET_EA': '335.00', 
                    'WERKS': '1000', 
                    'WWGHA1': 'G03000144', 
                    'WWGHB1': 'Mist Fan', 
                    'WWGHA2': 'G02000022', 
                    'WWGHB2': 'AIR COOLER', 
                    'WWGHA3': 'G01000002', 
                    'WWGHB3': 'HOME APPLIANCES'}, 
                    {
                    'MATNR': 'GAC9380', 
                    'MAKTX': '12" Air Cooler With Remote 5.5 L 1X1', 
                    'LGORT': 'AFS1', 
                    'CHARG': 'ESMA', 
                    'SPART': '01', 
                    'MEINS': 'EA', 
                    'ATP_QTY': '0.0', 
                    'TOT_QTY': '0.0', 
                    'CURRENCY': 'AED', 
                    'IC_EA': '272.00', 
                    'OD_EA': '335.00', 
                    'EX_EA': '280.00', 
                    'RET_EA': '335.00', 
                    'WERKS': '1000', 
                    'WWGHA1': 'G03000144', 
                    'WWGHB1': 'Mist Fan', 
                    'WWGHA2': 'G02000022', 
                    'WWGHB2': 'AIR COOLER', 
                    'WWGHA3': 'G01000002', 
                    'WWGHB3': 'HOME APPLIANCES'}
                    ]
                }
            }
        }
    }
}

"""
xml_string = """<n0:ZAPP_HOLDING_SO xmlns:n0="urn:sap-com:document:sap:rfc:functions">
                 <IM_AUART></IM_AUART>
                 <IM_DATE></IM_DATE>
                 <IM_EXTRA></IM_EXTRA>
                 <IM_FLAG></IM_FLAG>
                 <IM_ID></IM_ID>
                 <IM_KUNNR>"""+ customer_id + """</IM_KUNNR>
                 <IM_PERNR></IM_PERNR>
                 <IM_PO_NUMBER></IM_PO_NUMBER>
                 <IM_SPART></IM_SPART>
                 <IM_VKORG>""" + company_code +"""</IM_VKORG>
                 <IM_VTWEG></IM_VTWEG>
                 <T_ITEM>
                  <item>
                   <MATKL></MATKL>
                   <MATNR>"""+ product_id + """</MATNR>
                   <ITEM></ITEM>
                   <MAKTX></MAKTX>
                   <QTY>"""+ qty + """</QTY>
                   <UOM>"""+ uom + """</UOM>
                   <PRICE></PRICE>
                   <INDPRICE></INDPRICE>
                   <DISC></DISC>
                   <INDDISC></INDDISC>
                   <CHARG>""" + charg +"""</CHARG>
                   <MO_PRICE></MO_PRICE>
                   <NO_STOCK_IND></NO_STOCK_IND>
                   <NO_STOCK_FOC></NO_STOCK_FOC>
                   <FOC_ITEM></FOC_ITEM>
                   <FOC_QTY></FOC_QTY>
                   <FOC_UOM></FOC_UOM>
                   <FOC_CHARG></FOC_CHARG>
                   <PRC_DIFF_IND></PRC_DIFF_IND>
                   <PRC_DIFF_NEW></PRC_DIFF_NEW>
                   <SPCL_TEXT></SPCL_TEXT>
                   <FOC_STD></FOC_STD>
                   <FOC_ART></FOC_ART>
                   <FOC_MCL></FOC_MCL>
                   <INDICATOR1></INDICATOR1>
                   <INDICATOR2></INDICATOR2>
                   <TEXT1></TEXT1>
                   <TEXT2></TEXT2>
                   <CHARG_LIST></CHARG_LIST>
                   <PRICE_CHANGE></PRICE_CHANGE>
                   <FRM_ATP></FRM_ATP>
                  </item>
                 </T_ITEM>
                 <T_MESSAGE>
                  <item>
                   <VBELN></VBELN>
                   <TYPE></TYPE>
                   <ID></ID>
                   <NUMBER></NUMBER>
                   <MESSAGE></MESSAGE>
                   <LOG_NO></LOG_NO>
                   <LOG_MSG_NO></LOG_MSG_NO>
                   <MESSAGE_V1></MESSAGE_V1>
                   <MESSAGE_V2></MESSAGE_V2>
                   <MESSAGE_V3></MESSAGE_V3>
                   <MESSAGE_V4></MESSAGE_V4>
                   <PARAMETER></PARAMETER>
                   <ROW></ROW>
                   <FIELD></FIELD>
                   <SYSTEM></SYSTEM>
                  </item>
                 </T_MESSAGE>
                </n0:ZAPP_HOLDING_SO>"""