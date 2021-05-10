import sys
import logging

logger = logging.getLogger(__name__)

def xml_generator_for_price_and_stock_SAP(seller_sku,company_code,customer_id):

    try :

        xml_feed = """<soapenv:Envelope xmlns:urn="urn:sap-com:document:sap:rfc:functions" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
                    <soapenv:Header />
                    <soapenv:Body>
                    <urn:ZAPP_STOCK_PRICE>
                    <IM_KUNNR>"""+ str(customer_id) +"""</IM_KUNNR>
                    <IM_MATNR>
                    <item>
                     <MATNR>""" + str(seller_sku) + """</MATNR>
                    </item>
                    </IM_MATNR>
                    <IM_VKORG>
                    <item>
                     <VKORG>""" + str(company_code) + """</VKORG>
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

        return xml_feed

    except Exception as e:
        
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("xml_generator_for_price_and_stock_SAP: %s at %s", str(e), str(exc_tb.tb_lineno))
        return []

def xml_generator_for_holding_tansfer(company_code,customer_id,transfer_information):

    try :

        xml_feed = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:sap-com:document:sap:rfc:functions">
                        <soapenv:Header/>
                        <soapenv:Body>
                        <urn:ZAPP_HOLDING_SO>
                         <IM_AUART/>
                         <IM_DATE/>
                         <IM_EXTRA/>
                         <IM_FLAG/>
                         <IM_ID/>
                         <IM_KUNNR>"""+ str(customer_id) + """</IM_KUNNR>
                         <IM_PERNR/>
                         <IM_PO_NUMBER/>
                         <IM_SPART/>
                         <IM_VKORG>""" + str(company_code) +"""</IM_VKORG>
                         <IM_VTWEG/>
                         <T_ITEM>"""

        msg_feed="<T_MESSAGE>"
        for item in transfer_information:
            xml_feed+="""
                  <item>
                   <MATKL></MATKL>
                   <MATNR>"""+ str(item["seller_sku"]) + """</MATNR>
                   <ITEM></ITEM>
                   <MAKTX></MAKTX>
                   <QTY>"""+ str(item["qty"]) + """</QTY>
                   <UOM>EA</UOM>
                   <PRICE></PRICE>
                   <INDPRICE></INDPRICE>
                   <DISC></DISC>
                   <INDDISC></INDDISC>
                   <CHARG>"""+ str(item["batch"]) + """</CHARG>
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
                  </item>"""
            
            msg_feed+="""<item>
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
              </item>"""
              
        xml_feed+="</T_ITEM>"
        msg_feed+="</T_MESSAGE>"

        xml_feed+=msg_feed+"""</urn:ZAPP_HOLDING_SO>
                                </soapenv:Body>
                                </soapenv:Envelope>"""

        return xml_feed

    except Exception as e:
        
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("xml_generator_for_holding_tansfer: %s at %s", str(e), str(exc_tb.tb_lineno))
        return []

def xml_generator_for_intercompany_tansfer(company_code,customer_id,order_information):

    try :

        xml_feed = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:sap-com:document:sap:rfc:functions">
                         <soapenv:Header/>
                         <soapenv:Body>
                            <urn:ZAPP_ONLINE_ORDER>
                               <IM_AUART></IM_AUART>
                               <IM_DATE></IM_DATE>
                               <IM_EXTRA></IM_EXTRA>
                               <IM_FLAG>X</IM_FLAG>
                               <IM_ID>""" + str(order_information["order_id"]) + """</IM_ID>
                               <IM_KUNNR>""" + str(customer_id) + """</IM_KUNNR>
                               <IM_PERNR></IM_PERNR>
                               <IM_PO_NUMBER>"""+ str(order_information["refrence_id"]) +"""</IM_PO_NUMBER>
                               <IM_SPART></IM_SPART>
                               <IM_VKORG>""" + str(company_code) + """</IM_VKORG>
                               <IM_VTWEG></IM_VTWEG>"""
        if order_information["is_b2b"]==True:
           xml_feed +="""        <IM_STREET>""" + str(order_information["street"])+ """</IM_STREET>
                                 <IM_REGION>""" + str(order_information["region"])+ """</IM_REGION>
                                 <IM_TELEPHONE>""" + str(order_information["telephone"])+ """</IM_TELEPHONE>
                                 <IM_EMAIL>""" + str(order_information["email"])+ """</IM_EMAIL>
                                 <IM_STCEG>""" + str(order_information["trn"])+ """</IM_STCEG>"""
                             
        xml_feed +=         """<T_CONDITION>
                                  <item>
                                     <KPOSN></KPOSN>
                                     <KSCHL></KSCHL>
                                     <KWERT></KWERT>
                                  </item>
                               </T_CONDITION>
                               <T_DOCS>
                                  <item>
                                     <DOCTYP></DOCTYP>
                                     <VBELN></VBELN>
                                     <MSGTY></MSGTY>
                                     <MSGV1></MSGV1>
                                  </item>
                               </T_DOCS>
                                <T_ITEM>"""

        msg_feed = "<T_MESSAGE>"
        
        for item in order_information["items"]:
            
            xml_feed+="""<item>
                         <MATKL></MATKL>
                         <MATNR>"""+ str(item["seller_sku"]) + """</MATNR>
                         <ITEM></ITEM>
                         <MAKTX></MAKTX>
                         <QTY>"""+ str(item["qty"]) +"""</QTY>
                         <UOM>EA</UOM>
                         <PRICE></PRICE>
                         <INDPRICE></INDPRICE>
                         <DISC></DISC>
                         <INDDISC></INDDISC>
                         <CHARG>""" + str(item["batch"]) + """</CHARG>
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
                         <CONDITION1></CONDITION1>
                         <CONDITION2></CONDITION2>
                         <CONDITION3></CONDITION3>
                         <CONDITION4></CONDITION4>
                         <FRM_HOLDING>""" + str(item["from_holding"]) + """</FRM_HOLDING>
                      </item>"""
                
            msg_feed+="""<item>
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
                      </item>"""      
        
        xml_feed+="</T_ITEM>"
        msg_feed+="</T_MESSAGE>"

        xml_feed+=msg_feed+"""</urn:ZAPP_ONLINE_ORDER>
                                 </soapenv:Body>
                              </soapenv:Envelope>"""

        return xml_feed

    except Exception as e:
        
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("xml_generator_for_intercompany_tansfer: %s at %s", str(e), str(exc_tb.tb_lineno))
        return []

def xml_generator_for_final_billing(company_code,customer_id,order_information):

    try :

        condition_feed = ""

        for item in order_information["header_charges"]:
            condition_feed += """<item>
                                    <KPOSN></KPOSN>
                                    <KSCHL>"""+ str(item["name"]) + """</KSCHL>
                                    <KWERT>"""+ str(item["value"]) + """</KWERT>
                                </item>"""

        if condition_feed == "":
            condition_feed = """<item>
                                    <KPOSN></KPOSN>
                                    <KSCHL></KSCHL>
                                    <KWERT></KWERT>
                                </item>"""

        item_feed = ""

        for item in order_information["unit_order_information_list"]:

            item_feed += """<item>
                             <MATKL></MATKL>
                             <MATNR>"""+ str(item["seller_sku"]) + """</MATNR>
                             <ITEM></ITEM>
                             <MAKTX></MAKTX>
                             <QTY>"""+ str(item["qty"]) +"""</QTY>
                             <UOM>EA</UOM>
                             <PRICE></PRICE>
                             <INDPRICE></INDPRICE>
                             <DISC></DISC>
                             <INDDISC></INDDISC>
                             <CHARG>""" + str(item["batch"]) + """</CHARG>
                             <MO_PRICE>"""+ str(item["price"]) + """</MO_PRICE>
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
                             <CONDITION1>""" + str(order_information["promotional_charge"]) +"""</CONDITION1>
                             <CONDITION2></CONDITION2>
                             <CONDITION3></CONDITION3>
                             <CONDITION4></CONDITION4>
                             <FRM_HOLDING></FRM_HOLDING>
                          </item>"""

        xml_feed = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:sap-com:document:sap:rfc:functions">
                         <soapenv:Header/>
                         <soapenv:Body>
                            <urn:ZAPP_ONLINE_ORDER>
                               <IM_AUART>""" + str(order_information["order_type"]) + """</IM_AUART>
                               <IM_CITY>""" + str(order_information["city"]) + """</IM_CITY>
                               <IM_DATE></IM_DATE>
                               <IM_EXTRA></IM_EXTRA>
                               <IM_FLAG></IM_FLAG>
                               <IM_ID>""" + str(order_information["order_id"]) + """</IM_ID>
                               <IM_KUNNR>""" + str(customer_id) + """</IM_KUNNR>
                               <IM_PERNR></IM_PERNR>
                               <IM_PO_NUMBER>"""+ str(order_information["refrence_id"]) +"""</IM_PO_NUMBER>
                               <IM_SPART></IM_SPART>
                               <IM_NAME>""" + str(order_information["customer_first_name"]) + """</IM_NAME>
                               <IM_NAME2>""" + str(order_information["customer_middle_name"]) + """</IM_NAME2>
                               <IM_NAME3>""" + str(order_information["customer_last_name"]) + """</IM_NAME3>
                               <IM_VKORG>""" + str(company_code) + """</IM_VKORG>
                               <IM_VTWEG></IM_VTWEG>"""
        if order_information["is_b2b"]==True:
               xml_feed +="""        <IM_STREET>""" + str(order_information["street"])+ """</IM_STREET>
                                 <IM_REGION>""" + str(order_information["region"])+ """</IM_REGION>
                                 <IM_TELEPHONE>""" + str(order_information["telephone"])+ """</IM_TELEPHONE>
                                 <IM_EMAIL>""" + str(order_information["email"])+ """</IM_EMAIL>
                                 <IM_STCEG>""" + str(order_information["trn"])+ """</IM_STCEG>"""
        xml_feed +=         """<T_CONDITION>"""+ str(condition_feed) + """</T_CONDITION>
                               <T_DOCS>
                                  <item>
                                     <DOCTYP></DOCTYP>
                                     <VBELN></VBELN>
                                     <MSGTY></MSGTY>
                                     <MSGV1></MSGV1>
                                  </item>
                               </T_DOCS>
                               <T_ITEM>"""+ str(item_feed)+ """</T_ITEM>
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
                            </urn:ZAPP_ONLINE_ORDER>
                         </soapenv:Body>
                      </soapenv:Envelope>"""

        return xml_feed

    except Exception as e:
        
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("xml_generator_for_final_billing: %s at %s", str(e), str(exc_tb.tb_lineno))
        return []


def xml_generator_for_product_holding_details(company_code,seller_sku):
   try:
      xml_feed = """ <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:sap-com:document:sap:rfc:functions">
                        <soapenv:Header/>
                        <soapenv:Body>
                           <urn:ZAPP_ARTICLE_HOLDING_RPT>
                              <!--Optional:-->
                              <IM_MATNR>
                                 <!--Zero or more repetitions:-->
                                 <item>
                                    <MATNR>""" + str(seller_sku) + """</MATNR>
                                 </item>
                              </IM_MATNR>
                              <!--Optional:-->
                              <IM_VKORG>
                                 <!--Zero or more repetitions:-->
                                 <item>
                                    <VKORG>""" + str(company_code) + """</VKORG>
                                 </item>
                              </IM_VKORG>
                              <!--Optional:-->
                              <T_DATA>
                              <!--Zero or more repetitions:-->
                              <item>
                                 <VBELN></VBELN>
                                 <MATNR></MATNR>
                                 <MAKTX></MAKTX>
                                 <NAME1></NAME1>
                                 <OMENG></OMENG>
                                 <MEINS></MEINS>
                                 <CHARG></CHARG>
                                 <ERDAT></ERDAT>
                                 <VORNA></VORNA>
                                 <DOCTY></DOCTY>
                                 <BEZEI></BEZEI>
                              </item>
                           </T_DATA>
                           </urn:ZAPP_ARTICLE_HOLDING_RPT>
                        </soapenv:Body>
                     </soapenv:Envelope>"""
      return xml_feed

   except Exception as e:
        
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("xml_generator_for_product_holding_details: %s at %s", str(e), str(exc_tb.tb_lineno))
        return []