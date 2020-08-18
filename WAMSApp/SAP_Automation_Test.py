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

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Fetch Prices: ", e , " at ", str(exc_tb.tb_lineno))
        
        return []

fetch_prices(product_id,company_code,test_url,customer_id)

xml_string = """<n0:ZAPP_HOLDING_SO xmlns:n0="urn:sap-com:document:sap:rfc:functions">
                 <IM_AUART>Stri</IM_AUART>
                 <IM_DATE>2019-01-01</IM_DATE>
                 <IM_EXTRA>String 2</IM_EXTRA>
                 <IM_FLAG>S</IM_FLAG>
                 <IM_ID>String 4</IM_ID>
                 <IM_KUNNR>String 5</IM_KUNNR>
                 <IM_PERNR>6</IM_PERNR>
                 <IM_PO_NUMBER>String 7</IM_PO_NUMBER>
                 <IM_SPART>St</IM_SPART>
                 <IM_VKORG>Stri</IM_VKORG>
                 <IM_VTWEG>St</IM_VTWEG>
                 <T_ITEM>
                  <item>
                   <MATKL>String 11</MATKL>
                   <MATNR>""" + product_id + """</MATNR>
                   <ITEM>13</ITEM>
                   <MAKTX>String 14</MAKTX>
                   <QTY>15</QTY>
                   <UOM>Str</UOM>
                   <PRICE>17</PRICE>
                   <INDPRICE>18</INDPRICE>
                   <DISC>19</DISC>
                   <INDDISC>20</INDDISC>
                   <CHARG>String 21</CHARG>
                   <MO_PRICE>22</MO_PRICE>
                   <NO_STOCK_IND>S</NO_STOCK_IND>
                   <NO_STOCK_FOC>S</NO_STOCK_FOC>
                   <FOC_ITEM>String 25</FOC_ITEM>
                   <FOC_QTY>26</FOC_QTY>
                   <FOC_UOM>Str</FOC_UOM>
                   <FOC_CHARG>String 28</FOC_CHARG>
                   <PRC_DIFF_IND>S</PRC_DIFF_IND>
                   <PRC_DIFF_NEW>30</PRC_DIFF_NEW>
                   <SPCL_TEXT>String 31</SPCL_TEXT>
                   <FOC_STD>S</FOC_STD>
                   <FOC_ART>S</FOC_ART>
                   <FOC_MCL>S</FOC_MCL>
                   <INDICATOR1>S</INDICATOR1>
                   <INDICATOR2>S</INDICATOR2>
                   <TEXT1>String 37</TEXT1>
                   <TEXT2>String 38</TEXT2>
                   <CHARG_LIST>String 39</CHARG_LIST>
                   <PRICE_CHANGE>S</PRICE_CHANGE>
                   <FRM_ATP>S</FRM_ATP>
                  </item>
                 </T_ITEM>
                </n0:ZAPP_HOLDING_SO>"""