from WAMSApp.models import *
from WAMSApp.xml_generator_SAP import *

import requests
import xmltodict
import json

logger = logging.getLogger(__name__)

price_stock_url = ""
transfer_holding_url = ""
intercompany_order_url = ""

def get_stock_thresholds(seller_sku,company_code,customer_id):

    try:

        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = ("MOBSERVICE", "~lDT8+QklV=(")
        
        body = xml_generator_for_price_and_stock_SAP(seller_sku,company_code,customer_id)
        
        response = requests.post(url=price_stock_url, auth=credentials, data=body, headers=headers)
        
        content = response.content
        xml_content = xmltodict.parse(content)
        response_dict = json.loads(json.dumps(xml_content))

        items = response_dict["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_STOCK_PRICEResponse"]["T_DATA"]["item"]
        
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

        prices_stock_list["total_atp"] = total_atp
        prices_stock_list["total_holding"] = total_holding

        return prices_stock_list

    except Exception as e:
        
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("get_stock_thresholds: %s at %s", str(e), str(exc_tb.tb_lineno))
        return []    

def fetch_prices_and_stock(seller_sku,company_code,customer_id):
    
    try:

        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = ("MOBSERVICE", "~lDT8+QklV=(")
        
        body = xml_generator_for_price_and_stock_SAP(seller_sku,company_code,customer_id)
        
        response = requests.post(url=price_stock_url, auth=credentials, data=body, headers=headers)
        
        content = response.content
        xml_content = xmltodict.parse(content)
        response_dict = json.loads(json.dumps(xml_content))

        items = response_dict["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_STOCK_PRICEResponse"]["T_DATA"]["item"]
        
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

        prices_stock_list["total_atp"] = total_atp
        prices_stock_list["total_holding"] = total_holding

        return prices_stock_list

    except Exception as e:
        
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("fetch_prices_and_stock: %s at %s", str(e), str(exc_tb.tb_lineno))
        return []

def transfer_from_atp_to_holding(seller_sku,company_code,customer_id,transfer_information):
    
    try:

        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = ("MOBSERVICE", "~lDT8+QklV=(")
        
        body = xml_generator_for_holding_tansfer(seller_sku,company_code,customer_id,transfer_information)
        
        response = requests.post(url=transfer_holding_url, auth=credentials, data=body, headers=headers)
        
        content = response.content
        xml_content = xmltodict.parse(content)
        response_dict = json.loads(json.dumps(xml_content))

        return response_dict

    except Exception as e:
        
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("transfer_from_atp_to_holding: %s at %s", str(e), str(exc_tb.tb_lineno))
        return []

def create_intercompany_sales_order(seller_sku,company_code,customer_id,order_information):
    
    try:

        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = ("MOBSERVICE", "~lDT8+QklV=(")

        prices_stock_list = fetch_prices_and_stock(seller_sku,company_code,customer_id)

        total_atp = prices_stock_list["total_atp"]
        total_holding = prices_stock_list["total_holding"]

        if total_atp > atp_threshold:
            from_holding=""



        order_information["from_holding"] = ""
        order_information["uom"] = ""
        order_information["batch"] = ""
        
        body = xml_generator_for_intercompany_tansfer(seller_sku,company_code,customer_id,order_information)
        
        response = requests.post(url=intercompany_order_url, auth=credentials, data=body, headers=headers)
        
        content = response.content
        xml_content = xmltodict.parse(content)
        response_dict = json.loads(json.dumps(xml_content))

        return response_dict

    except Exception as e:
        
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("create_intercompany_sales_order: %s at %s", str(e), str(exc_tb.tb_lineno))
        return []
