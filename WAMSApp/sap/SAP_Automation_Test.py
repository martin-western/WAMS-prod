from WAMSApp.sap.SAP_constants import *

company_code = "1000"
customer_id = "40000195"
product_id = "GAC9380"

IP = "192.168.77.48"

test_url = "http://s4hdev:8000/sap/bc/srt/rfc/sap/zser_stock_price/150/zser_stock_price/zbin_stock_price"
production_url="http://wig.westernint.com:8000/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"

def fetch_prices(product_id,company_code,url,customer_id):
    
    try:

        # product_obj = Product.objects.filter(base_product__seller_sku=product_id)[0]

        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = (SAP_USERNAME, SAP_PASSWORD)
        
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

        return content

    except Exception as e:
        print("Fetch Prices: ", e)
        
        return []


response = fetch_prices(product_id,company_code,test_url,customer_id)
# print(response)

items = response["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_STOCK_PRICEResponse"]["T_DATA"]["item"]
uom = "EA"
charg = "BS"
total_atp = 0.0
total_holding = 0.0
prices_stock_list = []

if isinstance(items, dict):
    temp_dict={}
    temp_dict["charg"] = items["CHARG"]
    temp_dict["uom"] = items["MEINS"]    
    temp_dict["atp_qty"] = float(items["ATP_QTY"])
    total_atp = total_atp+float(items["ATP_QTY"])
    temp_dict["qty_holding"] = float(items["HQTY"])
    total_holding = total_holding + float(items["HQTY"])
    prices_stock_list.append(temp_dict)
else:
    for item in items:
        temp_dict={}
        temp_dict["charg"] = item["CHARG"]
        temp_dict["uom"] = item["MEINS"]    
        temp_dict["atp_qty"] = float(item["ATP_QTY"])
        total_atp = total_atp+float(item["ATP_QTY"])
        temp_dict["qty_holding"] = float(item["HQTY"])
        total_holding = total_holding + float(item["HQTY"])
        prices_stock_list.append(temp_dict)

print("Before : ")
print("Total ATP :  ",total_atp)
print("Total Holding :  ",total_holding)
print()
for item in prices_stock_list:
    print(item["charg"])
    print(item["uom"])
    print(item["atp_qty"])
    print(item["qty_holding"])
    print()

qty_holding = 15.0

headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
credentials = (SAP_USERNAME, SAP_PASSWORD)

body = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:sap-com:document:sap:rfc:functions">
            <soapenv:Header/>
            <soapenv:Body>
            <urn:ZAPP_HOLDING_SO>
             <IM_AUART/>
             <IM_DATE/>
             <IM_EXTRA/>
             <IM_FLAG/>
             <IM_ID/>
             <IM_KUNNR>"""+ customer_id + """</IM_KUNNR>
             <IM_PERNR/>
             <IM_PO_NUMBER/>
             <IM_SPART/>
             <IM_VKORG>""" + company_code +"""</IM_VKORG>
             <IM_VTWEG/>
             <T_ITEM>
              <item>
               <MATKL></MATKL>
               <MATNR>"""+ product_id + """</MATNR>
               <ITEM></ITEM>
               <MAKTX></MAKTX>
               <QTY>"""+ str(5.0) + """</QTY>
               <UOM>"""+ uom + """</UOM>
               <PRICE></PRICE>
               <INDPRICE></INDPRICE>
               <DISC></DISC>
               <INDDISC></INDDISC>
               <CHARG>ESMA</CHARG>
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
              <item>
               <MATKL></MATKL>
               <MATNR>"""+ product_id + """</MATNR>
               <ITEM></ITEM>
               <MAKTX></MAKTX>
               <QTY>"""+ str(5.0) + """</QTY>
               <UOM>"""+ uom + """</UOM>
               <PRICE></PRICE>
               <INDPRICE></INDPRICE>
               <DISC></DISC>
               <INDDISC></INDDISC>
               <CHARG>BS</CHARG>
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
            </urn:ZAPP_HOLDING_SO>
            </soapenv:Body>
            </soapenv:Envelope>"""

holding_url = "http://s4hdev:8000/sap/bc/srt/rfc/sap/zser_holding_so/150/zser_holding_so/zbin_holding_so"
credentials = (SAP_USERNAME, SAP_PASSWORD)

import requests
import xmltodict
import json

response_holding = requests.post(url=holding_url, auth=credentials, data=body, headers=headers)
content = response_holding.content
content = xmltodict.parse(content)
content = json.loads(json.dumps(content))

response = fetch_prices(product_id,company_code,test_url,customer_id)
        
items = response["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_STOCK_PRICEResponse"]["T_DATA"]["item"]
uom = "EA"
charg = "BS"
total_atp = 0.0
total_holding = 0.0
prices_stock_list = []

if isinstance(items, dict):
    temp_dict={}
    temp_dict["charg"] = items["CHARG"]
    temp_dict["uom"] = items["MEINS"]    
    temp_dict["atp_qty"] = float(items["ATP_QTY"])
    total_atp = total_atp+float(items["ATP_QTY"])
    temp_dict["qty_holding"] = float(items["HQTY"])
    total_holding = total_holding + float(items["HQTY"])
    prices_stock_list.append(temp_dict)
else:
    for item in items:
        temp_dict={}
        temp_dict["charg"] = item["CHARG"]
        temp_dict["uom"] = item["MEINS"]    
        temp_dict["atp_qty"] = float(item["ATP_QTY"])
        total_atp = total_atp+float(item["ATP_QTY"])
        temp_dict["qty_holding"] = float(item["HQTY"])
        total_holding = total_holding + float(item["HQTY"])
        prices_stock_list.append(temp_dict)

print("After : ")
print("Total ATP :  ",total_atp)
print("Total Holding :  ",total_holding)
print()
for item in prices_stock_list:
    print(item["charg"])
    print(item["uom"])
    print(item["atp_qty"])
    print(item["qty_holding"])
    print()