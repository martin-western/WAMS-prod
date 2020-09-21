from WAMSApp.models import *
from WAMSApp.xml_generators_SAP import *

import requests
import xmltodict
import json

logger = logging.getLogger(__name__)

test_price_stock_url = "http://94.56.89.116:8000/sap/bc/srt/rfc/sap/zser_stock_price/150/zser_stock_price/zbin_stock_price"
test_transfer_holding_url = "http://94.56.89.116:8000/sap/bc/srt/rfc/sap/zser_holding_so/150/zser_holding_so/zbin_holding_so"
test_online_order_url = "http://94.56.89.116:8000/sap/bc/srt/rfc/sap/zser_online_order/150/zser_online_order/zbin_online_order"  

test_customer_id = "40000195"

def fetch_prices_and_stock(seller_sku,company_code):
    
    try:

        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = ("MOBSERVICE", "~lDT8+QklV=(")
        
        body = xml_generator_for_price_and_stock_SAP(seller_sku,company_code,customer_id)
        
        response = requests.post(url=test_price_stock_url, auth=credentials, data=body, headers=headers)
        
        content = response.content
        xml_content = xmltodict.parse(content)
        response_dict = json.loads(json.dumps(xml_content))

        items = response_dict["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_STOCK_PRICEResponse"]["T_DATA"]["item"]
        
        total_atp = 0.0
        total_holding = 0.0
        result = {}
        stock_list = []

        if isinstance(items, dict):

            temp_dict={}
            temp_dict["batch"] = items["CHARG"]
            temp_dict["uom"] = items["MEINS"]    
            temp_dict["atp_qty"] = float(items["ATP_QTY"])
            total_atp = total_atp+float(items["ATP_QTY"])
            temp_dict["holding_qty"] = float(items["HQTY"])
            total_holding = total_holding + float(items["HQTY"])
            stock_list.append(temp_dict)

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
    
        else:
            for item in items:
                
                temp_dict={}
                temp_dict["batch"] = item["CHARG"]
                temp_dict["uom"] = item["MEINS"]    
                temp_dict["atp_qty"] = float(item["ATP_QTY"])
                total_atp = total_atp+float(item["ATP_QTY"])
                temp_dict["holding_qty"] = float(item["HQTY"])
                total_holding = total_holding + float(item["HQTY"])
                stock_list.append(temp_dict)

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

        prices = {}
        prices["EX_EA"] = str(EX_EA)
        prices["IC_EA"] = str(IC_EA)
        prices["OD_EA"] = str(OD_EA)
        prices["RET_EA"] = str(RET_EA)
        
        if isinstance(items,list):
            item = items[1]

        super_category = item["WWGHB1"]
        category = item["WWGHB2"]
        sub_category = item["WWGHB3"]

        sap_super_category , created = SapSuperCategory.objects.get_or_create(super_category=super_category)
        sap_category , created  = SapCategory.objects.get_or_create(category=category,super_category=sap_super_category)
        sap_sub_category , created  = SapSubCategory.objects.get_or_create(sub_category=sub_category,category=sap_category)

        category_mapping = CategoryMapping.objects.get_or_create(sap_sub_category=sap_sub_category)

        result["prices"] = prices
        result["stock_list"] = stock_list
        result["total_atp"] = total_atp
        result["total_holding"] = total_holding
        result["atp_threshold"] = category_mapping.atp_threshold
        result["holding_threshold"] = category_mapping.holding_threshold

        return result

    except Exception as e:
        
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("fetch_prices_and_stock: %s at %s", str(e), str(exc_tb.tb_lineno))
        return []

def transfer_from_atp_to_holding(seller_sku_list,company_code):
    
    try:

        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = ("MOBSERVICE", "~lDT8+QklV=(")
        
        for seller_sku in seller_sku_list :

            product_obj = Product.objects.filter(base_product__seller_sku=seller_sku)[0]
            is_sap_exception = product_obj.is_sap_exception

            result = fetch_prices_and_stock(seller_sku,company_code)
            
            if is_sap_exception == True:
                holding_threshold=product_obj.holding_threshold
                atp_threshold=product_obj.atp_threshold
            else:
                holding_threshold = result["holding_threshold"]
                atp_threshold = result["atp_threshold"]

            total_holding = result["total_holding"]
            total_atp = result["total_atp"]

            if total_holding < holding_threshold and total_atp > atp_threshold:

                total_holding_transfer = min(holding_threshold,total_holding+total_atp-atp_threshold)
                transfer_information = []

                while total_holding_transfer > 0:

                    for item in result["stock_list"]:

                        if item["atp_qty"] >= total_holding_transfer:

                            transfer_here = min(total_holding_transfer,item["atp_qty"])
                            
                            temp_dict = {}
                            temp_dict["seller_sku"] = seller_sku
                            temp_dict["qty"] = transfer_here
                            temp_dict["uom"] = item["uom"]
                            temp_dict["batch"] = item["batch"]
                            transfer_information.append(temp_dict)

                            total_holding_transfer = total_holding_transfer-transfer_here

                        if total_holding_transfer == 0:
                            break

        if len(transfer_information) > 0:

            body = xml_generator_for_holding_tansfer(company_code,customer_id,transfer_information)
            response = requests.post(url=test_transfer_holding_url, auth=credentials, data=body, headers=headers)
            content = response.content
            xml_content = xmltodict.parse(content)
            response_dict = json.loads(json.dumps(xml_content))

            return response_dict

        else :
            logger.info("transfer_from_atp_to_holding : Nothing to transfer to Holding in this call",seller_sku_list)
            return {}

    except Exception as e:
        
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("transfer_from_atp_to_holding: %s at %s", str(e), str(exc_tb.tb_lineno))
        return {}

def create_intercompany_sales_order(seller_sku,company_code,order_information):
    
    try:

        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = ("MOBSERVICE", "~lDT8+QklV=(")

        body = xml_generator_for_intercompany_tansfer(seller_sku,company_code,customer_id,order_information)
        
        response = requests.post(url=intercompany_order_url, auth=credentials, data=body, headers=headers)
        
        content = response.content
        xml_content = xmltodict.parse(content)
        response_dict = json.loads(json.dumps(xml_content))

        return response_dict

    except Exception as e:
        
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("test_online_order_url: %s at %s", str(e), str(exc_tb.tb_lineno))
        return []
