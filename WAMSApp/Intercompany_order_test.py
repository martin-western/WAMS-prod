import requests
import xmltodict
import json
import uuid

company_code = "1000"
customer_id = "40000195"
product_id = "GTR34"
IP = "94.56.89.116"

headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
credentials = ("MOBSERVICE", "~lDT8+QklV=(")

print(product_id)
print()

test_url = "http://94.56.89.116:8000/sap/bc/srt/rfc/sap/zser_stock_price/150/zser_stock_price/zbin_stock_price"
# production_url="http://wig.westernint.com:8000/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"

def fetch_prices(product_id,company_code,url,customer_id):
    
    try:

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

        return content

    except Exception as e:
        print("Fetch Prices: ", e)
        return []


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

print("Before : ")
print("Batch"+'\t'+"UOM"+'\t'+"ATP"+'\t'+"Holding")
for item in prices_stock_list:
    if item["charg"] != None:
        print(str(item["charg"])+'\t'+str(item["uom"])+'\t'+str(item["atp_qty"])+'\t'+str(item["qty_holding"]))
print("Total"+'\t'+'\t'+str(total_atp)+'\t'+str(total_holding))
print()

##################################

###### Transfer to Holding ######

##################################

# qty_holding = 5.0

# body = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:sap-com:document:sap:rfc:functions">
#             <soapenv:Header/>
#             <soapenv:Body>
#             <urn:ZAPP_HOLDING_SO>
#              <IM_AUART/>
#              <IM_DATE/>
#              <IM_EXTRA/>
#              <IM_FLAG/>
#              <IM_ID/>
#              <IM_KUNNR>"""+ customer_id + """</IM_KUNNR>
#              <IM_PERNR/>
#              <IM_PO_NUMBER/>
#              <IM_SPART/>
#              <IM_VKORG>""" + company_code +"""</IM_VKORG>
#              <IM_VTWEG/>
#              <T_ITEM>
#               <item>
#                <MATKL></MATKL>
#                <MATNR>"""+ product_id + """</MATNR>
#                <ITEM></ITEM>
#                <MAKTX></MAKTX>
#                <QTY>"""+ str(qty_holding) + """</QTY>
#                <UOM>"""+ uom + """</UOM>
#                <PRICE></PRICE>
#                <INDPRICE></INDPRICE>
#                <DISC></DISC>
#                <INDDISC></INDDISC>
#                <CHARG>ESMA</CHARG>
#                <MO_PRICE></MO_PRICE>
#                <NO_STOCK_IND></NO_STOCK_IND>
#                <NO_STOCK_FOC></NO_STOCK_FOC>
#                <FOC_ITEM></FOC_ITEM>
#                <FOC_QTY></FOC_QTY>
#                <FOC_UOM></FOC_UOM>
#                <FOC_CHARG></FOC_CHARG>
#                <PRC_DIFF_IND></PRC_DIFF_IND>
#                <PRC_DIFF_NEW></PRC_DIFF_NEW>
#                <SPCL_TEXT></SPCL_TEXT>
#                <FOC_STD></FOC_STD>
#                <FOC_ART></FOC_ART>
#                <FOC_MCL></FOC_MCL>
#                <INDICATOR1></INDICATOR1>
#                <INDICATOR2></INDICATOR2>
#                <TEXT1></TEXT1>
#                <TEXT2></TEXT2>
#                <CHARG_LIST></CHARG_LIST>
#                <PRICE_CHANGE></PRICE_CHANGE>
#                <FRM_ATP></FRM_ATP>
#               </item>
#               <item>
#                <MATKL></MATKL>
#                <MATNR>"""+ product_id + """</MATNR>
#                <ITEM></ITEM>
#                <MAKTX></MAKTX>
#                <QTY>"""+ str(qty_holding) + """</QTY>
#                <UOM>"""+ uom + """</UOM>
#                <PRICE></PRICE>
#                <INDPRICE></INDPRICE>
#                <DISC></DISC>
#                <INDDISC></INDDISC>
#                <CHARG>BS</CHARG>
#                <MO_PRICE></MO_PRICE>
#                <NO_STOCK_IND></NO_STOCK_IND>
#                <NO_STOCK_FOC></NO_STOCK_FOC>
#                <FOC_ITEM></FOC_ITEM>
#                <FOC_QTY></FOC_QTY>
#                <FOC_UOM></FOC_UOM>
#                <FOC_CHARG></FOC_CHARG>
#                <PRC_DIFF_IND></PRC_DIFF_IND>
#                <PRC_DIFF_NEW></PRC_DIFF_NEW>
#                <SPCL_TEXT></SPCL_TEXT>
#                <FOC_STD></FOC_STD>
#                <FOC_ART></FOC_ART>
#                <FOC_MCL></FOC_MCL>
#                <INDICATOR1></INDICATOR1>
#                <INDICATOR2></INDICATOR2>
#                <TEXT1></TEXT1>
#                <TEXT2></TEXT2>
#                <CHARG_LIST></CHARG_LIST>
#                <PRICE_CHANGE></PRICE_CHANGE>
#                <FRM_ATP></FRM_ATP>
#               </item>
#              </T_ITEM>
#              <T_MESSAGE>
#               <item>
#                <VBELN></VBELN>
#                <TYPE></TYPE>
#                <ID></ID>
#                <NUMBER></NUMBER>
#                <MESSAGE></MESSAGE>
#                <LOG_NO></LOG_NO>
#                <LOG_MSG_NO></LOG_MSG_NO>
#                <MESSAGE_V1></MESSAGE_V1>
#                <MESSAGE_V2></MESSAGE_V2>
#                <MESSAGE_V3></MESSAGE_V3>
#                <MESSAGE_V4></MESSAGE_V4>
#                <PARAMETER></PARAMETER>
#                <ROW></ROW>
#                <FIELD></FIELD>
#                <SYSTEM></SYSTEM>
#               </item>
#               <item>
#                <VBELN></VBELN>
#                <TYPE></TYPE>
#                <ID></ID>
#                <NUMBER></NUMBER>
#                <MESSAGE></MESSAGE>
#                <LOG_NO></LOG_NO>
#                <LOG_MSG_NO></LOG_MSG_NO>
#                <MESSAGE_V1></MESSAGE_V1>
#                <MESSAGE_V2></MESSAGE_V2>
#                <MESSAGE_V3></MESSAGE_V3>
#                <MESSAGE_V4></MESSAGE_V4>
#                <PARAMETER></PARAMETER>
#                <ROW></ROW>
#                <FIELD></FIELD>
#                <SYSTEM></SYSTEM>
#               </item>
#              </T_MESSAGE>
#             </urn:ZAPP_HOLDING_SO>
#             </soapenv:Body>
#             </soapenv:Envelope>"""

# holding_url = "http://94.56.89.116:8000/sap/bc/srt/rfc/sap/zser_holding_so/150/zser_holding_so/zbin_holding_so"

# response_holding = requests.post(url=holding_url, auth=credentials, data=body, headers=headers)
# content = response_holding.content
# content = xmltodict.parse(content)
# content = json.loads(json.dumps(content))

# # #################################

# # ###### After Holding ############

# # ################################

# response = fetch_prices(product_id,company_code,test_url,customer_id)
        
# items = response["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_STOCK_PRICEResponse"]["T_DATA"]["item"]
# uom = "EA"
# charg = "BS"
# total_atp = 0.0
# total_holding = 0.0
# prices_stock_list = []

# if isinstance(items, dict):
#     temp_dict={}
#     temp_dict["charg"] = items["CHARG"]
#     temp_dict["uom"] = items["MEINS"]    
#     temp_dict["atp_qty"] = float(items["ATP_QTY"])
#     total_atp = total_atp+float(items["ATP_QTY"])
#     temp_dict["qty_holding"] = float(items["HQTY"])
#     total_holding = total_holding + float(items["HQTY"])
#     prices_stock_list.append(temp_dict)
# else:
#     for item in items:
#         temp_dict={}
#         temp_dict["charg"] = item["CHARG"]
#         temp_dict["uom"] = item["MEINS"]    
#         temp_dict["atp_qty"] = float(item["ATP_QTY"])
#         total_atp = total_atp+float(item["ATP_QTY"])
#         temp_dict["qty_holding"] = float(item["HQTY"])
#         total_holding = total_holding + float(item["HQTY"])
#         prices_stock_list.append(temp_dict)

# print("After Holding : ")
# print("Batch"+'\t'+"UOM"+'\t'+"ATP"+'\t'+"Holding")
# for item in prices_stock_list:
#     if item["charg"] != None:
#         print(str(item["charg"])+'\t'+str(item["uom"])+'\t'+str(item["atp_qty"])+'\t'+str(item["qty_holding"]))
# print("Total"+'\t'+'\t'+str(total_atp)+'\t'+str(total_holding))
# print()


# ###################################

# ####### Intercompany Order ########

# ###################################


# holding_order_qty = 1.0
# atp_order_qty = 1.0
# uid = str(uuid.uuid4()).split("-")[0]
# print(uid)
# transfer_flag="X"
# holding_flag="X"
# order_type = "ZWIC"

# body = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:sap-com:document:sap:rfc:functions">
#              <soapenv:Header/>
#              <soapenv:Body>
#                 <urn:ZAPP_ONLINE_ORDER>
#                    <IM_AUART></IM_AUART>
#                    <IM_DATE></IM_DATE>
#                    <IM_EXTRA></IM_EXTRA>
#                    <IM_FLAG>"""+ transfer_flag + """</IM_FLAG>
#                    <IM_ID>""" + uid + """</IM_ID>
#                    <IM_KUNNR>""" + customer_id + """</IM_KUNNR>
#                    <IM_PERNR></IM_PERNR>
#                    <IM_PO_NUMBER></IM_PO_NUMBER>
#                    <IM_SPART></IM_SPART>
#                    <IM_VKORG>""" + company_code + """</IM_VKORG>
#                    <IM_VTWEG></IM_VTWEG>
#                    <T_CONDITION>
#                       <item>
#                          <KPOSN></KPOSN>
#                          <KSCHL></KSCHL>
#                          <KWERT></KWERT>
#                       </item>
#                    </T_CONDITION>
#                    <T_DOCS>
#                       <item>
#                          <DOCTYP></DOCTYP>
#                          <VBELN></VBELN>
#                          <MSGTY></MSGTY>
#                          <MSGV1></MSGV1>
#                       </item>
#                    </T_DOCS>
#                    <T_ITEM>
#                       <item>
#                          <MATKL></MATKL>
#                          <MATNR>"""+ product_id + """</MATNR>
#                          <ITEM></ITEM>
#                          <MAKTX></MAKTX>
#                          <QTY>"""+ str(holding_order_qty) +"""</QTY>
#                          <UOM>""" + uom + """</UOM>
#                          <PRICE></PRICE>
#                          <INDPRICE></INDPRICE>
#                          <DISC></DISC>
#                          <INDDISC></INDDISC>
#                          <CHARG>BS</CHARG>
#                          <MO_PRICE></MO_PRICE>
#                          <NO_STOCK_IND></NO_STOCK_IND>
#                          <NO_STOCK_FOC></NO_STOCK_FOC>
#                          <FOC_ITEM></FOC_ITEM>
#                          <FOC_QTY></FOC_QTY>
#                          <FOC_UOM></FOC_UOM>
#                          <FOC_CHARG></FOC_CHARG>
#                          <PRC_DIFF_IND></PRC_DIFF_IND>
#                          <PRC_DIFF_NEW></PRC_DIFF_NEW>
#                          <SPCL_TEXT></SPCL_TEXT>
#                          <FOC_STD></FOC_STD>
#                          <FOC_ART></FOC_ART>
#                          <FOC_MCL></FOC_MCL>
#                          <INDICATOR1></INDICATOR1>
#                          <INDICATOR2></INDICATOR2>
#                          <TEXT1></TEXT1>
#                          <TEXT2></TEXT2>
#                          <CHARG_LIST></CHARG_LIST>
#                          <PRICE_CHANGE></PRICE_CHANGE>
#                          <CONDITION1></CONDITION1>
#                          <CONDITION2></CONDITION2>
#                          <CONDITION3></CONDITION3>
#                          <CONDITION4></CONDITION4>
#                          <FRM_HOLDING>"""+ holding_flag + """</FRM_HOLDING>
#                       </item>
#                       <item>
#                          <MATKL></MATKL>
#                          <MATNR>"""+ product_id + """</MATNR>
#                          <ITEM></ITEM>
#                          <MAKTX></MAKTX>
#                          <QTY>"""+ str(atp_order_qty) +"""</QTY>
#                          <UOM>""" + uom + """</UOM>
#                          <PRICE></PRICE>
#                          <INDPRICE></INDPRICE>
#                          <DISC></DISC>
#                          <INDDISC></INDDISC>
#                          <CHARG>ESMA</CHARG>
#                          <MO_PRICE></MO_PRICE>
#                          <NO_STOCK_IND></NO_STOCK_IND>
#                          <NO_STOCK_FOC></NO_STOCK_FOC>
#                          <FOC_ITEM></FOC_ITEM>
#                          <FOC_QTY></FOC_QTY>
#                          <FOC_UOM></FOC_UOM>
#                          <FOC_CHARG></FOC_CHARG>
#                          <PRC_DIFF_IND></PRC_DIFF_IND>
#                          <PRC_DIFF_NEW></PRC_DIFF_NEW>
#                          <SPCL_TEXT></SPCL_TEXT>
#                          <FOC_STD></FOC_STD>
#                          <FOC_ART></FOC_ART>
#                          <FOC_MCL></FOC_MCL>
#                          <INDICATOR1></INDICATOR1>
#                          <INDICATOR2></INDICATOR2>
#                          <TEXT1></TEXT1>
#                          <TEXT2></TEXT2>
#                          <CHARG_LIST></CHARG_LIST>
#                          <PRICE_CHANGE></PRICE_CHANGE>
#                          <CONDITION1></CONDITION1>
#                          <CONDITION2></CONDITION2>
#                          <CONDITION3></CONDITION3>
#                          <CONDITION4></CONDITION4>
#                          <FRM_HOLDING></FRM_HOLDING>
#                       </item>
#                    </T_ITEM>
#                    <T_MESSAGE>
#                       <item>
#                          <VBELN></VBELN>
#                          <TYPE></TYPE>
#                          <ID></ID>
#                          <NUMBER></NUMBER>
#                          <MESSAGE></MESSAGE>
#                          <LOG_NO></LOG_NO>
#                          <LOG_MSG_NO></LOG_MSG_NO>
#                          <MESSAGE_V1></MESSAGE_V1>
#                          <MESSAGE_V2></MESSAGE_V2>
#                          <MESSAGE_V3></MESSAGE_V3>
#                          <MESSAGE_V4></MESSAGE_V4>
#                          <PARAMETER></PARAMETER>
#                          <ROW></ROW>
#                          <FIELD></FIELD>
#                          <SYSTEM></SYSTEM>
#                       </item>
#                       <item>
#                          <VBELN></VBELN>
#                          <TYPE></TYPE>
#                          <ID></ID>
#                          <NUMBER></NUMBER>
#                          <MESSAGE></MESSAGE>
#                          <LOG_NO></LOG_NO>
#                          <LOG_MSG_NO></LOG_MSG_NO>
#                          <MESSAGE_V1></MESSAGE_V1>
#                          <MESSAGE_V2></MESSAGE_V2>
#                          <MESSAGE_V3></MESSAGE_V3>
#                          <MESSAGE_V4></MESSAGE_V4>
#                          <PARAMETER></PARAMETER>
#                          <ROW></ROW>
#                          <FIELD></FIELD>
#                          <SYSTEM></SYSTEM>
#                       </item>
#                    </T_MESSAGE>
#                 </urn:ZAPP_ONLINE_ORDER>
#              </soapenv:Body>
#           </soapenv:Envelope>"""

# intercompany_order_url = "http://94.56.89.116:8000/sap/bc/srt/rfc/sap/zser_online_order/150/zser_online_order/zbin_online_order"

# response_intercompany_order = requests.post(url=intercompany_order_url, auth=credentials, data=body, headers=headers)
# content = response_intercompany_order.content
# content = xmltodict.parse(content)
# response_dict = json.loads(json.dumps(content))

# items = response_dict["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_ONLINE_ORDERResponse"]["T_DOCS"]["item"]

# doc_list = []

# if isinstance(items, dict):
#     temp_dict={}
#     temp_dict["type"] = items["DOCTYP"]
#     temp_dict["id"] = items["VBELN"]    
#     temp_dict["message_type"] = items["MSGTY"]    
#     temp_dict["message"] = items["MSGV1"]    
#     doc_list.append(temp_dict)
# else:
#     for item in items:
#         temp_dict={}
#         temp_dict["type"] = item["DOCTYP"]
#         temp_dict["id"] = item["VBELN"]    
#         temp_dict["message_type"] = item["MSGTY"]    
#         temp_dict["message"] = item["MSGV1"]    
#         doc_list.append(temp_dict)

# print("Order : ")
# print("Type"+'\t'+"ID"+'\t'+"Message Type"+'\t'+"Message")
# for item in doc_list:
#     if item["type"] != None:
#         print(str(item["type"])+'\t'+str(item["id"])+'\t'+str(item["message_type"])+'\t'+str(item["message"]))
# print()

# #################################

# ######## After Order ############

# #################################

# response = fetch_prices(product_id,company_code,test_url,customer_id)
        
# items = response["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_STOCK_PRICEResponse"]["T_DATA"]["item"]
# uom = "EA"
# charg = "BS"
# total_atp = 0.0
# total_holding = 0.0
# prices_stock_list = []

# if isinstance(items, dict):
#     temp_dict={}
#     temp_dict["charg"] = items["CHARG"]
#     temp_dict["uom"] = items["MEINS"]    
#     temp_dict["atp_qty"] = float(items["ATP_QTY"])
#     total_atp = total_atp+float(items["ATP_QTY"])
#     temp_dict["qty_holding"] = float(items["HQTY"])
#     total_holding = total_holding + float(items["HQTY"])
#     prices_stock_list.append(temp_dict)
# else:
#     for item in items:
#         temp_dict={}
#         temp_dict["charg"] = item["CHARG"]
#         temp_dict["uom"] = item["MEINS"]    
#         temp_dict["atp_qty"] = float(item["ATP_QTY"])
#         total_atp = total_atp+float(item["ATP_QTY"])
#         temp_dict["qty_holding"] = float(item["HQTY"])
#         total_holding = total_holding + float(item["HQTY"])
#         prices_stock_list.append(temp_dict)

# print("After Order : ")
# print("Batch"+'\t'+"UOM"+'\t'+"ATP"+'\t'+"Holding")
# for item in prices_stock_list:
#     if item["charg"] != None:
#         print(str(item["charg"])+'\t'+str(item["uom"])+'\t'+str(item["atp_qty"])+'\t'+str(item["qty_holding"]))
# print("Total"+'\t'+'\t'+str(total_atp)+'\t'+str(total_holding))
# print()

# ############################

# ###### Final Order #########

# ############################

# final_order_url = "http://94.56.89.116:8000/sap/bc/srt/rfc/sap/zser_online_order/150/zser_online_order/zbin_online_order"

# uid = str(uuid.uuid4()).split("-")[0]
# print(uid)
# print()
# city = "Dubai"
# customer_name = "Raj Shah"
# end_customer_price = 30.0

# body = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:sap-com:document:sap:rfc:functions">
#              <soapenv:Header/>
#              <soapenv:Body>
#                 <urn:ZAPP_ONLINE_ORDER>
#                    <IM_AUART>""" + str(order_type) + """</IM_AUART>
#                    <IM_CITY>""" + str(city) + """</IM_CITY>
#                    <IM_DATE></IM_DATE>
#                    <IM_EXTRA></IM_EXTRA>
#                    <IM_FLAG></IM_FLAG>
#                    <IM_ID>""" + uid + """</IM_ID>
#                    <IM_KUNNR>""" + customer_id + """</IM_KUNNR>
#                    <IM_PERNR></IM_PERNR>
#                    <IM_PO_NUMBER></IM_PO_NUMBER>
#                    <IM_SPART></IM_SPART>
#                    <IM_NAME>""" + str(customer_name) + """</IM_NAME>
#                    <IM_VKORG>""" + company_code + """</IM_VKORG>
#                    <IM_VTWEG></IM_VTWEG>
#                    <T_CONDITION>
#                       <item>
#                          <KPOSN></KPOSN>
#                          <KSCHL></KSCHL>
#                          <KWERT></KWERT>
#                       </item>
#                    </T_CONDITION>
#                    <T_DOCS>
#                       <item>
#                          <DOCTYP></DOCTYP>
#                          <VBELN></VBELN>
#                          <MSGTY></MSGTY>
#                          <MSGV1></MSGV1>
#                       </item>
#                    </T_DOCS>
#                    <T_ITEM>
#                       <item>
#                          <MATKL></MATKL>
#                          <MATNR>"""+ product_id + """</MATNR>
#                          <ITEM></ITEM>
#                          <MAKTX></MAKTX>
#                          <QTY>"""+ str(holding_order_qty) +"""</QTY>
#                          <UOM>""" + uom + """</UOM>
#                          <PRICE>"""+ str(end_customer_price) + """</PRICE>
#                          <INDPRICE></INDPRICE>
#                          <DISC></DISC>
#                          <INDDISC></INDDISC>
#                          <CHARG>BS</CHARG>
#                          <MO_PRICE></MO_PRICE>
#                          <NO_STOCK_IND></NO_STOCK_IND>
#                          <NO_STOCK_FOC></NO_STOCK_FOC>
#                          <FOC_ITEM></FOC_ITEM>
#                          <FOC_QTY></FOC_QTY>
#                          <FOC_UOM></FOC_UOM>
#                          <FOC_CHARG></FOC_CHARG>
#                          <PRC_DIFF_IND></PRC_DIFF_IND>
#                          <PRC_DIFF_NEW></PRC_DIFF_NEW>
#                          <SPCL_TEXT></SPCL_TEXT>
#                          <FOC_STD></FOC_STD>
#                          <FOC_ART></FOC_ART>
#                          <FOC_MCL></FOC_MCL>
#                          <INDICATOR1></INDICATOR1>
#                          <INDICATOR2></INDICATOR2>
#                          <TEXT1></TEXT1>
#                          <TEXT2></TEXT2>
#                          <CHARG_LIST></CHARG_LIST>
#                          <PRICE_CHANGE></PRICE_CHANGE>
#                          <CONDITION1></CONDITION1>
#                          <CONDITION2></CONDITION2>
#                          <CONDITION3></CONDITION3>
#                          <CONDITION4></CONDITION4>
#                          <FRM_HOLDING>"""+ holding_flag + """</FRM_HOLDING>
#                       </item>
#                       <item>
#                          <MATKL></MATKL>
#                          <MATNR>"""+ product_id + """</MATNR>
#                          <ITEM></ITEM>
#                          <MAKTX></MAKTX>
#                          <QTY>"""+ str(atp_order_qty) +"""</QTY>
#                          <UOM>""" + uom + """</UOM>
#                          <PRICE>"""+ str(end_customer_price) + """</PRICE>
#                          <INDPRICE></INDPRICE>
#                          <DISC></DISC>
#                          <INDDISC></INDDISC>
#                          <CHARG>ESMA</CHARG>
#                          <MO_PRICE></MO_PRICE>
#                          <NO_STOCK_IND></NO_STOCK_IND>
#                          <NO_STOCK_FOC></NO_STOCK_FOC>
#                          <FOC_ITEM></FOC_ITEM>
#                          <FOC_QTY></FOC_QTY>
#                          <FOC_UOM></FOC_UOM>
#                          <FOC_CHARG></FOC_CHARG>
#                          <PRC_DIFF_IND></PRC_DIFF_IND>
#                          <PRC_DIFF_NEW></PRC_DIFF_NEW>
#                          <SPCL_TEXT></SPCL_TEXT>
#                          <FOC_STD></FOC_STD>
#                          <FOC_ART></FOC_ART>
#                          <FOC_MCL></FOC_MCL>
#                          <INDICATOR1></INDICATOR1>
#                          <INDICATOR2></INDICATOR2>
#                          <TEXT1></TEXT1>
#                          <TEXT2></TEXT2>
#                          <CHARG_LIST></CHARG_LIST>
#                          <PRICE_CHANGE></PRICE_CHANGE>
#                          <CONDITION1></CONDITION1>
#                          <CONDITION2></CONDITION2>
#                          <CONDITION3></CONDITION3>
#                          <CONDITION4></CONDITION4>
#                          <FRM_HOLDING></FRM_HOLDING>
#                       </item>
#                    </T_ITEM>
#                    <T_MESSAGE>
#                       <item>
#                          <VBELN></VBELN>
#                          <TYPE></TYPE>
#                          <ID></ID>
#                          <NUMBER></NUMBER>
#                          <MESSAGE></MESSAGE>
#                          <LOG_NO></LOG_NO>
#                          <LOG_MSG_NO></LOG_MSG_NO>
#                          <MESSAGE_V1></MESSAGE_V1>
#                          <MESSAGE_V2></MESSAGE_V2>
#                          <MESSAGE_V3></MESSAGE_V3>
#                          <MESSAGE_V4></MESSAGE_V4>
#                          <PARAMETER></PARAMETER>
#                          <ROW></ROW>
#                          <FIELD></FIELD>
#                          <SYSTEM></SYSTEM>
#                       </item>
#                       <item>
#                          <VBELN></VBELN>
#                          <TYPE></TYPE>
#                          <ID></ID>
#                          <NUMBER></NUMBER>
#                          <MESSAGE></MESSAGE>
#                          <LOG_NO></LOG_NO>
#                          <LOG_MSG_NO></LOG_MSG_NO>
#                          <MESSAGE_V1></MESSAGE_V1>
#                          <MESSAGE_V2></MESSAGE_V2>
#                          <MESSAGE_V3></MESSAGE_V3>
#                          <MESSAGE_V4></MESSAGE_V4>
#                          <PARAMETER></PARAMETER>
#                          <ROW></ROW>
#                          <FIELD></FIELD>
#                          <SYSTEM></SYSTEM>
#                       </item>
#                    </T_MESSAGE>
#                 </urn:ZAPP_ONLINE_ORDER>
#              </soapenv:Body>
#           </soapenv:Envelope>"""

# response_final_order = requests.post(url=final_order_url, auth=credentials, data=body, headers=headers)
# content = response_final_order.content
# content = xmltodict.parse(content)
# response_dict = json.loads(json.dumps(content))

# print(response_dict)

# items = response_dict["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_ONLINE_ORDERResponse"]["T_DOCS"]["item"]

# doc_list = []

# if isinstance(items, dict):
#     temp_dict={}
#     temp_dict["type"] = items["DOCTYP"]
#     temp_dict["id"] = items["VBELN"]    
#     temp_dict["message_type"] = items["MSGTY"]    
#     temp_dict["message"] = items["MSGV1"]    
#     doc_list.append(temp_dict)
# else:
#     for item in items:
#         temp_dict={}
#         temp_dict["type"] = item["DOCTYP"]
#         temp_dict["id"] = item["VBELN"]    
#         temp_dict["message_type"] = item["MSGTY"]    
#         temp_dict["message"] = item["MSGV1"]    
#         doc_list.append(temp_dict)

# print("Order : ")
# print("Type"+'\t'+"ID"+'\t'+"Message Type"+'\t'+"Message")
# for item in doc_list:
#     if item["type"] != None:
#         print(str(item["type"])+'\t'+str(item["id"])+'\t'+str(item["message_type"])+'\t'+str(item["message"]))
# print()