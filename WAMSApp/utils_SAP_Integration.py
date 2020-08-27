from WAMSApp.models import *
import requests
import xmltodict
import json

logger = logging.getLogger(__name__)

def xml_generator_for_price_and_stock_SAP(seller_sku,company_code,customer_id)

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

def xml_generator_for_price_and_stock_SAP(seller_sku,company_code,customer_id)

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

def fetch_prices_and_stock(seller_sku,company_code,url,customer_id):
    
    try:

        # product_obj = Product.objects.filter(base_product__seller_sku=product_id)[0]

        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = ("MOBSERVICE", "~lDT8+QklV=(")
        
        body = xml_generator_for_price_and_stock_SAP(seller_sku,company_code,customer_id)
        
        response = requests.post(url, auth=credentials, data=body, headers=headers)
        
        content = response.content
        xml_content = xmltodict.parse(content)
        response_dict = json.loads(json.dumps(xml_content))

        return response_dict

    except Exception as e:
        
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("fetch_prices_and_stock: %s at %s", str(e), str(exc_tb.tb_lineno))
        return []

