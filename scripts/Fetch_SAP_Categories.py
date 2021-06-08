import pandas as pd
from WAMSApp.models import *
from dealshub.models import *

import requests
import xmltodict
import json
from django.utils import timezone
import sys
import xlsxwriter

filename = "scripts/Category_Mapping.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]

rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])
dfs.loc[:, 'SAP Category 1'] = ""
dfs.loc[:, 'SAP Category 2'] = ""
dfs.loc[:, 'SAP Category 3'] = ""
dfs.loc[:, 'SAP Category 1 ID'] = ""
dfs.loc[:, 'SAP Category 2 ID'] = ""
dfs.loc[:, 'SAP Category 3 ID'] = ""
dfs = dfs.fillna("")
cnt=0

url="http://wig.westernint.com:8000/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"
headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
credentials = (SAP_USERNAME, SAP_PASSWORD)

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

for i in range(rows):
    print(i)
    try:
        
        seller_sku = str(dfs.iloc[i,0])
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

        dfs.loc[i, 'SAP Category 1 ID'] = item["WWGHA1"]
        dfs.loc[i, 'SAP Category 1'] = item["WWGHB1"]
        dfs.loc[i, 'SAP Category 2 ID'] = item["WWGHA2"]
        dfs.loc[i, 'SAP Category 2'] = item["WWGHB2"]
        dfs.loc[i, 'SAP Category 3 ID'] = item["WWGHA3"]
        dfs.loc[i, 'SAP Category 3'] = item["WWGHB3"]

        print(item["WWGHA1"])

    except Exception as e:
        dfs.loc[i, 'SAP Category 1'] = "Not Found"
        dfs.loc[i, 'SAP Category 2'] = "Not Found"
        dfs.loc[i, 'SAP Category 3'] = "Not Found"
        dfs.loc[i, 'SAP Category 1 ID'] = "Not Found"
        dfs.loc[i, 'SAP Category 2 ID'] = "Not Found"
        dfs.loc[i, 'SAP Category 3 ID'] = "Not Found"
        pass

dfs.to_excel(filename,index=False)
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
            'MATNR': 'GT7661'
          }
        },
        'IM_VKORG': {
          'item': {
            'VKORG': '1000'
          }
        },
        'T_DATA': {
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
            'WWGHB3': None
          }, {
            'MATNR': 'GT7661',
            'MAKTX': '2Pc VoltageTester/3x140MM/3.5X190MM1X100',
            'LGORT': 'AFS1',
            'CHARG': 'OMAN',
            'SPART': '01',
            'MEINS': 'EA',
            'ATP_QTY': '0.0',
            'TOT_QTY': '0.0',
            'CURRENCY': 'AED',
            'IC_EA': '4.00',
            'OD_EA': '7.00',
            'EX_EA': '4.00',
            'RET_EA': '7.00',
            'WERKS': '1000',
            'WWGHA1': 'G03000311',
            'WWGHB1': 'Testing Equipment',
            'WWGHA2': 'G02000129',
            'WWGHB2': 'Hand Tools',
            'WWGHA3': 'G01000012',
            'WWGHB3': 'Tools'
          }, {
            'MATNR': 'GT7661',
            'MAKTX': '2Pc VoltageTester/3x140MM/3.5X190MM1X100',
            'LGORT': 'AFS1',
            'CHARG': 'BS',
            'SPART': '01',
            'MEINS': 'EA',
            'ATP_QTY': '1.0',
            'TOT_QTY': '1.0',
            'CURRENCY': 'AED',
            'IC_EA': '4.00',
            'OD_EA': '7.00',
            'EX_EA': '4.00',
            'RET_EA': '7.00',
            'WERKS': '1000',
            'WWGHA1': 'G03000311',
            'WWGHB1': 'Testing Equipment',
            'WWGHA2': 'G02000129',
            'WWGHB2': 'Hand Tools',
            'WWGHA3': 'G01000012',
            'WWGHB3': 'Tools'
          }, {
            'MATNR': 'GT7661',
            'MAKTX': '2Pc VoltageTester/3x140MM/3.5X190MM1X100',
            'LGORT': 'AFS1',
            'CHARG': 'UAE',
            'SPART': '01',
            'MEINS': 'EA',
            'ATP_QTY': '0.0',
            'TOT_QTY': '0.0',
            'CURRENCY': 'AED',
            'IC_EA': '4.00',
            'OD_EA': '7.00',
            'EX_EA': '4.00',
            'RET_EA': '7.00',
            'WERKS': '1000',
            'WWGHA1': 'G03000311',
            'WWGHB1': 'Testing Equipment',
            'WWGHA2': 'G02000129',
            'WWGHB2': 'Hand Tools',
            'WWGHA3': 'G01000012',
            'WWGHB3': 'Tools'
          }]
        }
      }
    }
  }
}
"""