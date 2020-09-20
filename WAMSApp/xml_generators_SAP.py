import sys
import logging

logger = logging.getLogger(__name__)

def xml_generator_for_price_and_stock_SAP(seller_sku,company_code,customer_id):

    try :

        xml_feed = """<soapenv:Envelope xmlns:urn="urn:sap-com:document:sap:rfc:functions" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
                    <soapenv:Header />
                    <soapenv:Body>
                    <urn:ZAPP_STOCK_PRICE>
                    <IM_KUNNR>"""+ customer_id +"""</IM_KUNNR>
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
                         <IM_KUNNR>"""+ customer_id + """</IM_KUNNR>
                         <IM_PERNR/>
                         <IM_PO_NUMBER/>
                         <IM_SPART/>
                         <IM_VKORG>""" + company_code +"""</IM_VKORG>
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
                   <UOM>"""+ str(item["uom"]) + """</UOM>
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
              </item>
              <item>"""
              
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

def xml_generator_for_intercompany_tansfer(seller_sku,company_code,customer_id,order_information):

    try :

        xml_feed = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:sap-com:document:sap:rfc:functions">
                         <soapenv:Header/>
                         <soapenv:Body>
                            <urn:ZAPP_ONLINE_ORDER>
                               <IM_AUART></IM_AUART>
                               <IM_DATE></IM_DATE>
                               <IM_EXTRA></IM_EXTRA>
                               <IM_FLAG>X</IM_FLAG>
                               <IM_ID>""" + order_information["order_id"] + """</IM_ID>
                               <IM_KUNNR>""" + customer_id + """</IM_KUNNR>
                               <IM_PERNR></IM_PERNR>
                               <IM_PO_NUMBER></IM_PO_NUMBER>
                               <IM_SPART></IM_SPART>
                               <IM_VKORG>""" + company_code + """</IM_VKORG>
                               <IM_VTWEG></IM_VTWEG>
                               <T_CONDITION>
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

        items = order_information["items"]
        msg_feed = "<T_MESSAGE>"
        
        for item in items:
            xml_feed+="""<item>
                         <MATKL></MATKL>
                         <MATNR>"""+ str(item["seller_sku"]) + """</MATNR>
                         <ITEM></ITEM>
                         <MAKTX></MAKTX>
                         <QTY>"""+ str(item["qty"]) +"""</QTY>
                         <UOM>""" + str(item["uom"]) + """</UOM>
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