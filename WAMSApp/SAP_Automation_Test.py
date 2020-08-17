from WAMSApp.models import *

import csv
import urllib
import os
import requests
import xmltodict
import json
from django.utils import timezone
import sys
import xlsxwriter
import pandas as pd

company_code = "1090"
customer_id = "40000195"
product_id = "GAC9380"

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
                   <MATNR>String 12</MATNR>
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
                  <item>
                   <MATKL>String 42</MATKL>
                   <MATNR>String 43</MATNR>
                   <ITEM>44</ITEM>
                   <MAKTX>String 45</MAKTX>
                   <QTY>46</QTY>
                   <UOM>Str</UOM>
                   <PRICE>48</PRICE>
                   <INDPRICE>49</INDPRICE>
                   <DISC>50</DISC>
                   <INDDISC>51</INDDISC>
                   <CHARG>String 52</CHARG>
                   <MO_PRICE>53</MO_PRICE>
                   <NO_STOCK_IND>S</NO_STOCK_IND>
                   <NO_STOCK_FOC>S</NO_STOCK_FOC>
                   <FOC_ITEM>String 56</FOC_ITEM>
                   <FOC_QTY>57</FOC_QTY>
                   <FOC_UOM>Str</FOC_UOM>
                   <FOC_CHARG>String 59</FOC_CHARG>
                   <PRC_DIFF_IND>S</PRC_DIFF_IND>
                   <PRC_DIFF_NEW>61</PRC_DIFF_NEW>
                   <SPCL_TEXT>String 62</SPCL_TEXT>
                   <FOC_STD>S</FOC_STD>
                   <FOC_ART>S</FOC_ART>
                   <FOC_MCL>S</FOC_MCL>
                   <INDICATOR1>S</INDICATOR1>
                   <INDICATOR2>S</INDICATOR2>
                   <TEXT1>String 68</TEXT1>
                   <TEXT2>String 69</TEXT2>
                   <CHARG_LIST>String 70</CHARG_LIST>
                   <PRICE_CHANGE>S</PRICE_CHANGE>
                   <FRM_ATP>S</FRM_ATP>
                  </item>
                 </T_ITEM>
                 <T_MESSAGE>
                  <item>
                   <VBELN>String 73</VBELN>
                   <TYPE>S</TYPE>
                   <ID>String 75</ID>
                   <NUMBER>76</NUMBER>
                   <MESSAGE>String 77</MESSAGE>
                   <LOG_NO>String 78</LOG_NO>
                   <LOG_MSG_NO>79</LOG_MSG_NO>
                   <MESSAGE_V1>String 80</MESSAGE_V1>
                   <MESSAGE_V2>String 81</MESSAGE_V2>
                   <MESSAGE_V3>String 82</MESSAGE_V3>
                   <MESSAGE_V4>String 83</MESSAGE_V4>
                   <PARAMETER>String 84</PARAMETER>
                   <ROW>85</ROW>
                   <FIELD>String 86</FIELD>
                   <SYSTEM>String 87</SYSTEM>
                  </item>
                  <item>
                   <VBELN>String 88</VBELN>
                   <TYPE>S</TYPE>
                   <ID>String 90</ID>
                   <NUMBER>91</NUMBER>
                   <MESSAGE>String 92</MESSAGE>
                   <LOG_NO>String 93</LOG_NO>
                   <LOG_MSG_NO>94</LOG_MSG_NO>
                   <MESSAGE_V1>String 95</MESSAGE_V1>
                   <MESSAGE_V2>String 96</MESSAGE_V2>
                   <MESSAGE_V3>String 97</MESSAGE_V3>
                   <MESSAGE_V4>String 98</MESSAGE_V4>
                   <PARAMETER>String 99</PARAMETER>
                   <ROW>100</ROW>
                   <FIELD>String 101</FIELD>
                   <SYSTEM>String 102</SYSTEM>
                  </item>
                 </T_MESSAGE>
                </n0:ZAPP_HOLDING_SO>"""