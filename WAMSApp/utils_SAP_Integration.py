from WAMSApp.models import *
from WAMSApp.xml_generator_SAP import *

import requests
import xmltodict
import json

logger = logging.getLogger(__name__)


def fetch_prices_and_stock(seller_sku,company_code,url,customer_id):
    
    try:

        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = ("MOBSERVICE", "~lDT8+QklV=(")
        
        body = xml_generator_for_price_and_stock_SAP(seller_sku,company_code,customer_id)
        
        response = requests.post(url=url, auth=credentials, data=body, headers=headers)
        
        content = response.content
        xml_content = xmltodict.parse(content)
        response_dict = json.loads(json.dumps(xml_content))

        return response_dict

    except Exception as e:
        
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("fetch_prices_and_stock: %s at %s", str(e), str(exc_tb.tb_lineno))
        return []

def transfer_from_atp_to_holding(seller_sku,company_code,url,customer_id,transfer_information):
    
    try:

        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = ("MOBSERVICE", "~lDT8+QklV=(")
        
        body = xml_generator_for_holding_tansfer(seller_sku,company_code,customer_id,transfer_information)
        
        response = requests.post(url=url, auth=credentials, data=body, headers=headers)
        
        content = response.content
        xml_content = xmltodict.parse(content)
        response_dict = json.loads(json.dumps(xml_content))

        return response_dict

    except Exception as e:
        
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("transfer_from_atp_to_holding: %s at %s", str(e), str(exc_tb.tb_lineno))
        return []

def fetch_prices_and_stock(seller_sku,company_code,url,customer_id):
    
    try:

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

