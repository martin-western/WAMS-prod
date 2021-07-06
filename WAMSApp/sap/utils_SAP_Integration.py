from WAMSApp.utils import *
from WAMSApp.sap.xml_generators_SAP import *
from WAMSApp.sap.SAP_constants import *

from django.core.mail import send_mail, get_connection
from django.core.mail import EmailMultiAlternatives
from django.core.mail import EmailMessage

import requests
import xmltodict
import json
import time
import xlsxwriter

import time

logger = logging.getLogger(__name__)

def fetch_prices_and_stock(seller_sku,company_code):
    
    try:

        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = (SAP_USERNAME, SAP_PASSWORD)
        
        body = xml_generator_for_price_and_stock_SAP(seller_sku,company_code,CUSTOMER_ID)
        logger.info("price and stock req body :%s", str(body))
        response = requests.post(url=PRICE_STOCK_URL, auth=credentials, data=body, headers=headers)
        
        content = response.content
        xml_content = xmltodict.parse(content)
        response_dict = json.loads(json.dumps(xml_content))

        items = response_dict["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_STOCK_PRICEResponse"]["T_DATA"]["item"]
        logger.info(items)
        
        total_atp = 0.0
        total_holding = 0.0
        atp_threshold = 0.0
        holding_threshold = 0.0

        EX_EA = 0.0
        IC_EA = 0.0
        OD_EA = 0.0
        RET_EA = 0.0

        result = {}
        stock_list = []

        if isinstance(items, dict):

            temp_dict={}
            
            if items["CHARG"] != None :
                temp_dict["batch"] = items["CHARG"]
            else:
                temp_dict["batch"] = ""

            if items["MEINS"] != None :
                temp_dict["uom"] = items["MEINS"]
            else:
                temp_dict["uom"] = ""

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

                if item["CHARG"] != None :
                    temp_dict["batch"] = item["CHARG"]
                else:
                    temp_dict["batch"] = ""

                if item["MEINS"] != None :
                    temp_dict["uom"] = item["MEINS"]
                else:
                    temp_dict["uom"] = "" 

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
        
        result["prices"] = prices
        result["stock_list"] = stock_list
        result["total_atp"] = total_atp
        result["total_holding"] = total_holding

        if isinstance(items,list):
            items = items[1]

        super_category = items["WWGHB1"]
        category = items["WWGHB2"]
        sub_category = items["WWGHB3"]

        result["atp_threshold"] = 0.0
        result["holding_threshold"] = 0.0

        if isNoneOrEmpty(super_category):
            result["status"] = 500
            result["message"] = "SAP Super Category Not Found for :" + seller_sku
            return result

        if isNoneOrEmpty(category):
            result["status"] = 500
            result["message"] = "SAP Category Not Found :" + seller_sku
            return result

        if isNoneOrEmpty(sub_category):
            result["status"] = 500
            result["message"] = "SAP SubCategory Not Found :" + seller_sku
            return result

        sap_super_category , created = SapSuperCategory.objects.get_or_create(super_category=super_category)
        sap_category , created  = SapCategory.objects.get_or_create(category=category,super_category=sap_super_category)
        sap_sub_category , created  = SapSubCategory.objects.get_or_create(sub_category=sub_category,category=sap_category)

        category_mapping , created = CategoryMapping.objects.get_or_create(sap_sub_category=sap_sub_category)

        atp_threshold = category_mapping.atp_threshold
        holding_threshold = category_mapping.holding_threshold

        result["atp_threshold"] = atp_threshold
        result["holding_threshold"] = holding_threshold
        logger.info("price and stock result : %s",str(json.dumps(result)))
        
        result["status"] = 200
        result["message"] = "Success"

        return result

    except Exception as e:
        
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("fetch_prices_and_stock: %s at %s", str(e), str(exc_tb.tb_lineno))
        return []

def transfer_from_atp_to_holding(seller_sku,company_code):
    
    try:

        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = (SAP_USERNAME, SAP_PASSWORD)
        # credentials = ("WIABAP", "pradeepabap456")

        transfer_information = []

        product_obj = Product.objects.filter(base_product__seller_sku=seller_sku)[0]
        is_sap_exception = product_obj.is_sap_exception

        result ={
            "atp_threshold" : "",
            "holding_threshold" : "",
            "total_holding_before" : "",
            "total_atp_before" : "",
            "total_holding_after" : "",
            "total_atp_after" : "",
            "stock_status" : "",
            "SAP_message" : ""
        }

        prices_and_stock_information = fetch_prices_and_stock(seller_sku,company_code)

        total_holding = float(prices_and_stock_information["total_holding"])
        total_atp = float(prices_and_stock_information["total_atp"])

        result["total_holding_before"] = total_holding
        result["total_atp_before"] = total_atp

        if prices_and_stock_information["message"] !="Success":
            result["SAP_message"] = prices_and_stock_information["message"]
            return result
        
        if is_sap_exception == True:
            holding_threshold=product_obj.holding_threshold
            atp_threshold=product_obj.atp_threshold
        else:
            holding_threshold = float(prices_and_stock_information["holding_threshold"])
            atp_threshold = float(prices_and_stock_information["atp_threshold"])

        result["holding_threshold"] = holding_threshold
        result["atp_threshold"] = atp_threshold

        if total_holding < holding_threshold and total_atp > atp_threshold:

            total_holding_transfer = min(holding_threshold,total_holding+total_atp-atp_threshold)

            while total_holding_transfer > 0:

                for item in prices_and_stock_information["stock_list"]:

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
        else :
            if total_holding == holding_threshold and total_atp >= atp_threshold:
                result["stock_status"] = "GOOD"
            elif total_holding < holding_threshold and total_atp >= atp_threshold:
                result["stock_status"] = "CRITICAL HOLDING"
            elif total_holding == holding_threshold and total_atp < atp_threshold:
                result["stock_status"] = "CRITICAL ATP"
            elif total_holding > holding_threshold:
                result["stock_status"] = "MORE HOLDING"
            else:
                result["stock_status"] = "CRITICAL STOCK"

        if len(transfer_information) > 0:
            logger.info("tansfer info : %s", str(json.dumps(transfer_information)))
            body = xml_generator_for_holding_tansfer(company_code,CUSTOMER_ID,transfer_information)
            response = requests.post(url=TRANSFER_HOLDING_URL, auth=credentials, data=body, headers=headers)
            content = response.content
            xml_content = xmltodict.parse(content)
            response_dict = json.loads(json.dumps(xml_content))

            response_dict = response_dict["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_HOLDING_SOResponse"]
            items = response_dict["T_ITEM"]["item"]

            try :
                if isinstance(items,list):
                    for item in items:
                        if item["INDICATOR1"] != None:
                            indicator = item["INDICATOR1"]
                            if indicator == "X":
                                result["SAP_message"] = "PRICES NOT MAINTAINED"
                else:
                    if items["MESSAGE"] != None:
                        indicator = items["INDICATOR1"]
                        if indicator == "X":
                            result["SAP_message"] = "PRICES NOT MAINTAINED"
            except Exception as e:
                pass

            items = response_dict["T_MESSAGE"]["item"]

            try :
                if isinstance(items,list):
                    for item in items:
                        if item["MESSAGE"] != None:
                            SAP_message = item["MESSAGE"]
                            result["SAP_message"] = SAP_message
                else:
                    if items["MESSAGE"] != None:
                        SAP_message = items["MESSAGE"]
                        result["SAP_message"] = SAP_message
            except Exception as e:
                pass

            time.sleep(2)
            prices_and_stock_information = fetch_prices_and_stock(seller_sku,company_code)
            
            if is_sap_exception == True:
                holding_threshold=product_obj.holding_threshold
                atp_threshold=product_obj.atp_threshold
            else:
                holding_threshold = float(prices_and_stock_information["holding_threshold"])
                atp_threshold = float(prices_and_stock_information["atp_threshold"])

            total_holding = float(prices_and_stock_information["total_holding"])
            total_atp = float(prices_and_stock_information["total_atp"])

            if total_holding == holding_threshold and total_atp >=atp_threshold:
                result["stock_status"] = "GOOD"
            elif total_holding < holding_threshold and total_atp >=atp_threshold:
                result["stock_status"] = "CRITICAL HOLDING"
            elif total_holding == holding_threshold and total_atp < atp_threshold:
                result["stock_status"] = "CRITICAL ATP"
            elif total_holding > holding_threshold:
                result["stock_status"] = "MORE HOLDING"
            else:
                result["stock_status"] = "CRITICAL STOCK"
            logger.info("afer holding transfer result : %s",str(json.dumps(result)))
            result["total_holding_after"] = total_holding
            result["total_atp_after"] = total_atp
            return result

        else :
            result["SAP_message"] = "NO HOLDING TRANSFER"
            result["total_holding_after"] = result["total_holding_before"]
            logger.info("transfer_from_atp_to_holding : Nothing to transfer to Holding in this call",seller_sku)
            return result

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("transfer_from_atp_to_holding: %s at %s", str(e), str(exc_tb.tb_lineno))
        return result

def holding_atp_transfer(seller_sku,company_code,final_holding):
    try:
        logger.info("holind_atp_transfer start: %s", str(final_holding))
        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = (SAP_USERNAME, SAP_PASSWORD)
        # credentials = ("WIABAP", "pradeepabap456")

        transfer_information = []

        result ={
            "total_holding_before" : "",
            "total_atp_before" : "",
            "total_holding_after" : "",
            "total_atp_after" : "",
            "SAP_message" : ""
        }

        prices_and_stock_information = fetch_prices_and_stock(seller_sku,company_code)
        logger.info("holind_atp_transfer price&stock info : %s", str(prices_and_stock_information))

        total_holding = float(prices_and_stock_information["total_holding"])
        total_atp = float(prices_and_stock_information["total_atp"])

        result["total_holding_before"] = total_holding
        result["total_atp_before"] = total_atp

        if prices_and_stock_information["message"] !="Success":
            result["SAP_message"] = prices_and_stock_information["message"]
            return result
        
        if final_holding < total_holding: # if dec.the holding

            change_in_holding = total_holding - final_holding # amount of change
            if change_in_holding > 0:

                for item in prices_and_stock_information["stock_list"]:
                    transfer_here = min(change_in_holding,item["holding_qty"]) # to not take more then available
                    temp_dict = {}
                    temp_dict["seller_sku"] = seller_sku
                    temp_dict["qty"] = item["holding_qty"] - transfer_here # final value of holding for this batch.
                    temp_dict["uom"] = item["uom"]
                    temp_dict["batch"] = item["batch"]
                    if temp_dict["qty"] > 0:
                        transfer_information.append(temp_dict)

                    change_in_holding = change_in_holding - transfer_here

                    if change_in_holding == 0:
                        break 
        else:  # if inc the holding
            total_holding_transfer = final_holding - total_holding
            if total_holding_transfer <= total_atp:
                if total_holding_transfer > 0:

                    for item in prices_and_stock_information["stock_list"]:

                        transfer_here = min(total_holding_transfer,item["atp_qty"])
                        
                        temp_dict = {}
                        temp_dict["seller_sku"] = seller_sku
                        temp_dict["qty"] = item["holding_qty"] + transfer_here
                        temp_dict["uom"] = item["uom"]
                        temp_dict["batch"] = item["batch"]
                        if temp_dict["qty"] > 0:
                            transfer_information.append(temp_dict)

                        total_holding_transfer = total_holding_transfer-transfer_here

                        if total_holding_transfer == 0:
                            break
                else:
                    logger.info("asking for more than available ATP to transfer to holding")

        if len(transfer_information) > 0:
            body = xml_generator_for_holding_tansfer(company_code,CUSTOMER_ID,transfer_information)
            logger.info("holind_atp_transfer BODY FOR API: %s",str(body))
            response = requests.post(url=TRANSFER_HOLDING_URL, auth=credentials, data=body, headers=headers)
            content = response.content
            xml_content = xmltodict.parse(content)
            response_dict = json.loads(json.dumps(xml_content))

            response_dict = response_dict["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_HOLDING_SOResponse"]
            items = response_dict["T_ITEM"]["item"]

            logger.info("holind_atp_transfer GOT SAP RESPONSE : %s", str(response_dict))

            try :
                if isinstance(items,list):
                    for item in items:
                        if item["INDICATOR1"] != None:
                            indicator = item["INDICATOR1"]
                            if indicator == "X":
                                result["SAP_message"] = "PRICES NOT MAINTAINED"
                else:
                    if items["MESSAGE"] != None:
                        indicator = items["INDICATOR1"]
                        if indicator == "X":
                            result["SAP_message"] = "PRICES NOT MAINTAINED"
            except Exception as e:
                pass

            items = response_dict["T_MESSAGE"]["item"]
            try :
                if isinstance(items,list):
                    for item in items:
                        if item["MESSAGE"] != None:
                            SAP_message = item["MESSAGE"]
                            result["SAP_message"] = SAP_message
                else:
                    if items["MESSAGE"] != None:
                        SAP_message = items["MESSAGE"]
                        result["SAP_message"] = SAP_message
            except Exception as e:
                pass

            time.sleep(2)
            prices_and_stock_information = fetch_prices_and_stock(seller_sku,company_code)
            total_holding = float(prices_and_stock_information["total_holding"])
            total_atp = float(prices_and_stock_information["total_atp"])

            result["total_holding_after"] = total_holding
            result["total_atp_after"] = total_atp
            return result

        else :
            result["SAP_message"] = "NO HOLDING TRANSFER"
            result["total_holding_after"] = result["total_holding_before"]
            logger.info("holding_atp_transfer : Nothing to transfer to Holding in this call",seller_sku)
            return result

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("holding_atp_transfer: %s at %s", str(e), str(exc_tb.tb_lineno))
        return result

def create_intercompany_sales_order(company_code,order_information):
    
    try:

        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = (SAP_USERNAME, SAP_PASSWORD)
        logger.info(order_information)

        body = xml_generator_for_intercompany_tansfer(company_code,CUSTOMER_ID,order_information)
        logger.info("XML Intercompany: %s",body)

        response = requests.post(url=ONLINE_ORDER_URL, auth=credentials, data=body, headers=headers)
        
        content = response.content
        xml_content = xmltodict.parse(content)
        response_dict = json.loads(json.dumps(xml_content))
        logger.info(response_dict)

        result = {}
        doc_list = []
        msg_list = []

        response_dict = response_dict["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_ONLINE_ORDERResponse"]
        
        items = response_dict["T_ITEM"]["item"]

        try :
            
            if isinstance(items,list):
                for item in items:
                    if item["INDICATOR1"] != None:
                        seller_sku = item["MATNR"]
                        indicator = item["INDICATOR1"]
                        if indicator == "X":
                            temp_dict = {}
                            temp_dict["message"] = "PRICES NOT MAINTAINED FOR " + seller_sku
                            msg_list.append(temp_dict)
            else:
                seller_sku = items["MATNR"]
                indicator = items["INDICATOR1"]
                if indicator == "X":
                    temp_dict = {}
                    temp_dict["message"] = "PRICES NOT MAINTAINED FOR " + seller_sku
                    msg_list.append(temp_dict)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.warning("create_intercompany_sales_order: %s at %s", str(e), str(exc_tb.tb_lineno))

        items = response_dict["T_DOCS"]["item"]


        if isinstance(items, dict):
            temp_dict={}
            temp_dict["type"] = items["DOCTYP"]
            temp_dict["id"] = items["VBELN"]    
            temp_dict["message_type"] = items["MSGTY"]    
            temp_dict["message"] = items["MSGV1"]    
            doc_list.append(temp_dict)
        else:
            for item in items:
                temp_dict={}
                temp_dict["type"] = item["DOCTYP"]
                temp_dict["id"] = item["VBELN"]    
                temp_dict["message_type"] = item["MSGTY"]    
                temp_dict["message"] = item["MSGV1"]    
                doc_list.append(temp_dict)

        items = response_dict["T_MESSAGE"]["item"]

        if isinstance(items, dict):
            temp_dict={}
            temp_dict["document_number"] = items["VBELN"]
            temp_dict["type"] = items["TYPE"]
            temp_dict["id"] = items["ID"]    
            temp_dict["number"] = items["NUMBER"]    
            temp_dict["message"] = items["MESSAGE"]    
            temp_dict["message_v1"] = items["MESSAGE_V1"]    
            temp_dict["message_v2"] = items["MESSAGE_V2"]    
            temp_dict["message_v3"] = items["MESSAGE_V3"]    
            temp_dict["message_v4"] = items["MESSAGE_V4"]    
            temp_dict["parameter"] = items["PARAMETER"]    
            msg_list.append(temp_dict)
        else:
            for item in items:
                temp_dict={}
                temp_dict["document_number"] = item["VBELN"]
                temp_dict["type"] = item["TYPE"]
                temp_dict["id"] = item["ID"]    
                temp_dict["number"] = item["NUMBER"]    
                temp_dict["message"] = item["MESSAGE"]    
                temp_dict["message_v1"] = item["MESSAGE_V1"]    
                temp_dict["message_v2"] = item["MESSAGE_V2"]    
                temp_dict["message_v3"] = item["MESSAGE_V3"]    
                temp_dict["message_v4"] = item["MESSAGE_V4"]    
                temp_dict["parameter"] = item["PARAMETER"]  
                msg_list.append(temp_dict)

        result["doc_list"] = doc_list
        result["msg_list"] = msg_list

        return result

    except Exception as e:
        
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("create_intercompany_sales_order: %s at %s", str(e), str(exc_tb.tb_lineno))
        return []


def is_manual_intervention_required(result):

    try:
        logger.info("is_manual_intervention_required: %s", str(result))
        msg_list = result["msg_list"]
        for item in msg_list:
            if item["message"]!=None:
                if "PRICES NOT MAINTAINED FOR" in item["message"] or "Price is not maintained for" in item["message"]:
                    return True
        return False
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("is_manual_intervention_required: %s at %s", str(e), str(exc_tb.tb_lineno))
        return True


def create_final_order(company_code,order_information):
    
    try:

        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = (SAP_USERNAME, SAP_PASSWORD)

        charges = order_information["charges"]
        header_charges = []

        if charges["courier_charge"] != "":
            temp_dict = {}
            temp_dict["name"] = "ZWJC"
            temp_dict["value"] = charges["courier_charge"]
            header_charges.append(temp_dict)

        if charges["cod_charge"] != "":
            temp_dict = {}
            temp_dict["name"] = "ZCOD"
            temp_dict["value"] = charges["cod_charge"]
            header_charges.append(temp_dict)

        if charges["voucher_charge"] != "":
            temp_dict = {}
            temp_dict["name"] = "ZWJS"
            temp_dict["value"] = charges["voucher_charge"]
            header_charges.append(temp_dict)

        if charges["other_charge"] != "":
            temp_dict = {}
            temp_dict["name"] = "ZWJA"
            temp_dict["value"] = charges["other_charge"]
            header_charges.append(temp_dict)

        order_information["promotional_charge"] = charges["promotional_charge"]
        order_information["header_charges"] = header_charges

        customer_id = order_information["customer_id"]

        customer_name = order_information["customer_name"].replace("'","&apos;").replace("&","&amp;")
        customer_name = customer_name[:89]

        words_list = customer_name.split(" ")
        names_list = ["","",""]
        ind = 0

        for word in words_list:
            if len(names_list[ind]) +len(word) < 30:
                names_list[ind] = names_list[ind] + word + " "
            else:
                ind+=1
                names_list[ind] = names_list[ind] + word + " "

        order_information["customer_first_name"] = names_list[0]
        order_information["customer_middle_name"] = names_list[1]
        order_information["customer_last_name"] = names_list[2]

        body = xml_generator_for_final_billing(company_code,customer_id,order_information)
        logger.info("XML Final: %s",body)

        response = requests.post(url=ONLINE_ORDER_URL, auth=credentials, data=body, headers=headers)
        
        content = response.content
        xml_content = xmltodict.parse(content)
        response_dict = json.loads(json.dumps(xml_content))
        logger.info("Response : %s",response_dict)

        items = response_dict["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_ONLINE_ORDERResponse"]["T_DOCS"]["item"]

        result = {}
        doc_list = []
        msg_list = []

        if isinstance(items, dict):
            temp_dict={}
            temp_dict["type"] = items["DOCTYP"]
            temp_dict["id"] = items["VBELN"]    
            temp_dict["message_type"] = items["MSGTY"]    
            temp_dict["message"] = items["MSGV1"]    
            doc_list.append(temp_dict)
        else:
            for item in items:
                temp_dict={}
                temp_dict["type"] = item["DOCTYP"]
                temp_dict["id"] = item["VBELN"]    
                temp_dict["message_type"] = item["MSGTY"]    
                temp_dict["message"] = item["MSGV1"]    
                doc_list.append(temp_dict)

        items = response_dict["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_ONLINE_ORDERResponse"]["T_MESSAGE"]["item"]

        if isinstance(items, dict):
            temp_dict={}
            temp_dict["document_number"] = items["VBELN"]
            temp_dict["type"] = items["TYPE"]
            temp_dict["id"] = items["ID"]    
            temp_dict["number"] = items["NUMBER"]    
            temp_dict["message"] = items["MESSAGE"]    
            temp_dict["message_v1"] = items["MESSAGE_V1"]    
            temp_dict["message_v2"] = items["MESSAGE_V2"]    
            temp_dict["message_v3"] = items["MESSAGE_V3"]    
            temp_dict["message_v4"] = items["MESSAGE_V4"]    
            temp_dict["parameter"] = items["PARAMETER"]    
            msg_list.append(temp_dict)
        else:
            for item in items:
                temp_dict={}
                temp_dict["document_number"] = item["VBELN"]
                temp_dict["type"] = item["TYPE"]
                temp_dict["id"] = item["ID"]    
                temp_dict["number"] = item["NUMBER"]    
                temp_dict["message"] = item["MESSAGE"]    
                temp_dict["message_v1"] = item["MESSAGE_V1"]    
                temp_dict["message_v2"] = item["MESSAGE_V2"]    
                temp_dict["message_v3"] = item["MESSAGE_V3"]    
                temp_dict["message_v4"] = item["MESSAGE_V4"]    
                temp_dict["parameter"] = item["PARAMETER"]  
                msg_list.append(temp_dict)

        result["doc_list"] = doc_list
        result["msg_list"] = msg_list

        return result

    except Exception as e:
        
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("create_final_order: %s at %s", str(e), str(exc_tb.tb_lineno))
        return []

def notify_account_manager(filename):

    try:
        with get_connection(
            host="smtp.gmail.com",
            port=587, 
            username="nisarg@omnycomm.com", 
            password="verjtzgeqareribg",
            use_tls=True) as connection:
            email = EmailMessage(subject='Omnycomm Stock Report Generated', 
                                 body='This is to inform you that Stock Report has been generated by Omnycomm and attached below',
                                 from_email='nisarg@omnycomm.com',
                                 to=['hari.pk@westernint.com',
                                     'rayees.hm@westernint.com',
                                     'nawas@westernint.com',
                                     'fathimasamah@westernint.com',
                                     'shahanas@westernint.com'],
                                 connection=connection)
            email.attach_file(filename)
            email.send(fail_silently=True)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error notify_account_manager %s %s", e, str(exc_tb.tb_lineno))


def create_holding_transfer_report(dealshub_product_objs):

    try:
        filename = "holding_transfer_report.xlsx"

        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        row = ["Seller SKU",
               "Brand Name",
               "Company Code",
               "ATP Threshold",
               "ATP Before",
               "ATP After",
               "Holding Threshold",
               "Holding Before",
               "Holding After",
               "Status",
               "SAP Message"]

        cnt = 0
            
        colnum = 0
        for k in row:
            worksheet.write(cnt, colnum, k)
            colnum += 1

        for dealshub_product_obj in dealshub_product_objs:

            cnt+=1
            common_row = ["" for i in range(11)]

            seller_sku = dealshub_product_obj.get_seller_sku()
            brand_name = ""
            status = "FAILED"
            
            try:
                brand_obj = dealshub_product_obj.product.base_product.brand
                company_code = brand_obj.get_company_code(dealshub_product_obj.location_group)
                brand_name = brand_obj.name
            except Exception as e:
                company_code = "BRAND NOT RECOGNIZED"

            common_row[0] = str(seller_sku)
            common_row[1] = str(brand_name)
            common_row[2] = str(company_code)

            if company_code != "BRAND NOT RECOGNIZED":
                try :
                    response_dict = transfer_from_atp_to_holding(seller_sku,company_code)
                   
                    common_row[3] = str(response_dict["atp_threshold"])
                    common_row[4] = str(response_dict["total_atp_before"])
                    common_row[5] = str(response_dict["total_atp_after"])
                    common_row[6] = str(response_dict["holding_threshold"])
                    common_row[7] = str(response_dict["total_holding_before"])
                    common_row[8] = str(response_dict["total_holding_after"])
                    common_row[9] = str(response_dict["stock_status"])
                    common_row[10] = str(response_dict["SAP_message"])

                    if isNoneOrEmpty(response_dict["total_holding_after"]) != True:
                        dealshub_product_obj.stock = int(response_dict["total_holding_after"])
                        dealshub_product_obj.save()

                except Exception as e:
                    logger.info(e)
                    common_row[9] = str("INTERNAL ERROR")
                    
            colnum = 0
            for k in common_row:
                worksheet.write(cnt, colnum, k)
                colnum += 1
        workbook.close()

        notify_account_manager('./'+filename)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("create_holding_transfer_report: %s at %s", str(e), str(exc_tb.tb_lineno))


def fetch_product_holding_details(dealshub_product_obj):

    try:
        seller_sku = dealshub_product_obj.get_seller_sku()
        status = "FAILED"
        
        try:
            brand_obj = dealshub_product_obj.product.base_product.brand
            company_code = brand_obj.get_company_code(dealshub_product_obj.location_group)
        except Exception as e:
            company_code = "BRAND NOT RECOGNIZED"
        
        product_holding_details = {}

        if company_code != "BRAND NOT RECOGNIZED":
            headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
            credentials = (SAP_USERNAME, SAP_PASSWORD)
            
            body = xml_generator_for_product_holding_details(company_code,seller_sku)

            response = requests.post(url=PRODUCT_HOLDING_URL, auth=credentials, data=body, headers=headers)

            content = response.content
            xml_content = xmltodict.parse(content)
            response_dict = json.loads(json.dumps(xml_content))
            
            logger.info("fetch_product_holding_details: Request: %s\nResponse: %s", str(body), str(response_dict))
            items = response_dict["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_ARTICLE_HOLDING_RPTResponse"]["T_DATA"]["item"]

            temp_list = []
            for item in items:
                flag = 0
                for temp_item in temp_list:
                    if temp_item["channel"] == item["VORNA"]:
                        temp_item["qty"] += float(item["OMENG"])
                        flag=1
                        break
                if flag==0:
                    temp_dict = {}
                    temp_dict["channel"] = item["VORNA"]
                    temp_dict["qty"] = float(item["OMENG"])
                    temp_list.append(temp_dict)
            
            prices_and_stock_information = fetch_prices_and_stock(seller_sku,company_code)

            total_holding = float(prices_and_stock_information["total_holding"])
            total_atp = float(prices_and_stock_information["total_atp"])

            product_holding_details["channel_holding_qty_list"] = temp_list
            product_holding_details["ATP"] = total_atp
            product_holding_details["holding"] = total_holding
           
        return product_holding_details
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("fetch_product_holding_details: %s at %s", str(e), str(exc_tb.tb_lineno))


def fetch_prices(product_id,company_code):
    
    try:

        product_obj = Product.objects.filter(base_product__seller_sku=product_id)[0]

        url="http://wig.westernint.com:8000/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"
        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = (SAP_USERNAME, SAP_PASSWORD)
        
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

        #product_obj.save()
        
        return warehouse_dict

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Fetch Prices: %s at %s", e, str(exc_tb.tb_lineno))
        
        return []


def fetch_prices_dealshub(uuid1, company_code):
    
    try:
        
        product_obj = Product.objects.get(uuid=uuid1)
        product_id = product_obj.base_product.seller_sku

        url="http://wig.westernint.com:8000/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"
        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = (SAP_USERNAME, SAP_PASSWORD)
        
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
        
        if isinstance(items, dict):
            temp_price = items["EX_EA"]
            if temp_price!=None:
                temp_price = float(temp_price)
                EX_EA = max(temp_price, EX_EA)
        else:
            for item in items:
                temp_price = item["EX_EA"]
                if temp_price!=None:
                    temp_price = float(temp_price)
                    EX_EA = max(temp_price, EX_EA)
        
        return str(EX_EA)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("fetch_prices_dealshub: %s at %s", e, str(exc_tb.tb_lineno))
        
        return "0"


def get_sap_batch_and_uom(company_code, seller_sku):
    response = {
        "batch": "",
        "uom": ""
    }
    return response
    try:
        url="http://wig.westernint.com:8000/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"
        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = (SAP_USERNAME, SAP_PASSWORD)
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
        sap_response = requests.post(url, auth=credentials, data=body, headers=headers)
        content = sap_response.content
        content = xmltodict.parse(content)
        content = json.loads(json.dumps(content))
        items = content["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_STOCK_PRICEResponse"]["T_DATA"]["item"]
            
        if isinstance(items, dict):
            if items["MEINS"]!=None:
                response["uom"] = items["MEINS"]
            if items["CHARG"]!=None:
                response["batch"] = items["CHARG"]
        else:
            for item in items:
                if items["MEINS"]!=None and items["CHARG"]!=None:
                    response["uom"] = items["MEINS"]
                    response["batch"] = items["CHARG"]

        return response
    except Exception as e:
        return response


def fetch_refresh_stock(seller_sku, company_code, location_code):

    try:
        url="http://wig.westernint.com:8000/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"
        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = (SAP_USERNAME, SAP_PASSWORD)
        
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
        
        items = content["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_STOCK_PRICEResponse"]["T_DATA"]["item"]
        
        if isinstance(items, dict):
            if items["LGORT"]==location_code:
                return float(items["ATP_QTY"])
            return 0
        else:
            max_qty = 0
            for item in items:
                if item["LGORT"]==location_code:
                    max_qty = max(max_qty, float(item["ATP_QTY"]))
            return max_qty

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("fetch_tg01_stock %s at %s", e, str(exc_tb.tb_lineno))
        return 0


def get_recommended_browse_node(seller_sku,channel):

    try:

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

        try:
            recommended_browse_node = CategoryMapping.objects.filter(channel__name=channel,sap_sub_category__sub_category=item["WWGHB1"])[0].recommended_browse_node
            return recommended_browse_node
        except:
            logger.error("get_recommended_browse_node: Mapping not found")
            return ""

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("get_recommended_browse_node: %s at %s", e, str(exc_tb.tb_lineno))
        return ""


def fetch_sap_details_for_order_punching(dealshub_product_obj):
    sap_details = {
        "company_code": "NA",
        "sales_office": "NA",
        "vendor_code": "NA",
        "purchase_org": "NA"
    }
    try:
        if dealshub_product_obj.get_brand().lower()=="geepas":
            sap_details["company_code"] = "1100"
            sap_details["sales_office"] = "1005"
            sap_details["vendor_code"] = "V1001"
            sap_details["purchase_org"] = "1200"
        elif dealshub_product_obj.get_brand().lower()=="olsenmark":
            sap_details["company_code"] = "1100"
            sap_details["sales_office"] = "1105"
            sap_details["vendor_code"] = "V1100"
            sap_details["purchase_org"] = "1200"
        elif dealshub_product_obj.get_brand().lower()=="krypton":
            sap_details["company_code"] = "2100"
            sap_details["sales_office"] = "2105"
            sap_details["vendor_code"] = "V2100"
            sap_details["purchase_org"] = "1200"
        elif dealshub_product_obj.get_brand().lower()=="royalford":
            sap_details["company_code"] = "3000"
            sap_details["sales_office"] = "3005"
            sap_details["vendor_code"] = "V3001"
            sap_details["purchase_org"] = "1200"
        elif dealshub_product_obj.get_brand().lower()=="abraj":
            sap_details["company_code"] = "6000"
            sap_details["sales_office"] = "6008"
            sap_details["vendor_code"] = "V6000"
            sap_details["purchase_org"] = "1200"
        elif dealshub_product_obj.get_brand().lower()=="baby plus":
            sap_details["company_code"] = "5550"
            sap_details["sales_office"] = "5558"
            sap_details["vendor_code"] = "V5550"
            sap_details["purchase_org"] = "1200"
        
        return sap_details

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("fetch_sap_details_for_order_punching: %s at %s", e, str(exc_tb.tb_lineno))
        return "NA"


def refresh_stock(order_obj):

    try:
        unit_order_objs = UnitOrder.objects.filter(order=order_obj)
        uuid_list = []
        for unit_order_obj in unit_order_objs:
            dealshub_product_obj = unit_order_obj.product
            brand_name = dealshub_product_obj.get_brand().lower()
            seller_sku = dealshub_product_obj.get_seller_sku()
            stock = 0
            company_code = ""
            total_holding = 0.0

            try :
                company_code_obj = CompanyCodeSAP.objects.get(location_group=order_obj.location_group, brand__name=brand_name)
                company_code = company_code_obj.code
            except Exception as e:
                continue

            if "wigme" in seller_sku.lower():
                continue
            
            prices_stock_information = fetch_prices_and_stock(seller_sku, company_code)
            total_holding = prices_stock_information["total_holding"]
            holding_threshold = prices_stock_information["holding_threshold"]

            # if brand=="geepas":
            #     stock2 = fetch_prices_and_stock(seller_sku, "1000")
            #     stock = max(stock1, stock2)
            # elif brand=="baby plus":
            #     stock = fetch_refresh_stock(seller_sku, "5550", "TG01")
            # elif brand=="royalford":
            #     stock = fetch_refresh_stock(seller_sku, "3000", "AFS1")
            # elif brand=="krypton":
            #     stock = fetch_refresh_stock(seller_sku, "2100", "TG01")
            # elif brand=="olsenmark":
            #     stock = fetch_refresh_stock(seller_sku, "1100", "AFS1")
            # elif brand=="ken jardene":
            #     stock = fetch_refresh_stock(seller_sku, "5550", "AFS1") # 
            # elif brand=="younglife":
            #     stock = fetch_refresh_stock(seller_sku, "5000", "AFS1")
            # elif brand=="delcasa":
            #     stock = fetch_refresh_stock(seller_sku, "3000", "TG01")

            wigme_location_group_obj = LocationGroup.objects.get(name="WIGMe - UAE")
            if dealshub_product_obj.location_group==wigme_location_group_obj:
                dealshub_product_obj.stock = int(total_holding)
            
            if holding_threshold > total_holding:
                try:
                    p2 = threading.Thread(target=notify_low_stock, args=(dealshub_product_obj,))
                    p2.start()
                    #dealshub_product_obj.stock = 0
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("refresh_stock: %s at %s", e, str(exc_tb.tb_lineno))

            dealshub_product_obj.save()

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("refresh_stock: %s at %s", e, str(exc_tb.tb_lineno))


def is_user_input_required_for_sap_punching(stock_price_information, order_qty):
    
    try:
        
        total_atp = stock_price_information["total_atp"]
        atp_threshold = stock_price_information["atp_threshold"]
        holding_threshold = stock_price_information["holding_threshold"]
        
        if total_atp > atp_threshold and total_atp >= order_qty:
            return False
        
        return True
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("is_user_input_required_for_sap_punching: %s at %s", e, str(exc_tb.tb_lineno)) 
        return True

def fetch_order_information_for_sap_punching(seller_sku, company_code, x_value, order_qty):

    try:

        result = fetch_prices_and_stock(seller_sku, company_code)

        stock_list = result["stock_list"]
        prices = result["prices"]
        total_atp = result["total_atp"]
        total_holding = result["total_holding"]
        atp_threshold = result["atp_threshold"]
        holding_threshold = result["holding_threshold"]
        
        total_stock_info = []

        if total_atp > atp_threshold and total_atp>=order_qty:
            from_holding=""
            for item in stock_list:
                atp_qty = item["atp_qty"]
                batch = item["batch"]
                uom = item["uom"]
                if atp_qty>0:
                    temp_dict = {
                        "atp_qty": atp_qty,
                        "batch": batch,
                        "uom": uom
                    }
                    total_stock_info.append(temp_dict)
        else:
            from_holding = x_value
            if from_holding == "X":
                for item in stock_list:
                    holding_qty = item["holding_qty"]
                    batch = item["batch"]
                    uom = item["uom"]
                    if holding_qty>0:
                        temp_dict = {
                            "atp_qty": holding_qty,
                            "batch": batch,
                            "uom": uom
                        }
                        total_stock_info.append(temp_dict)
            else:
                for item in stock_list:
                    atp_qty = item["atp_qty"]
                    batch = item["batch"]
                    uom = item["uom"]
                    if atp_qty>0:
                        temp_dict = {
                            "atp_qty": atp_qty,
                            "batch": batch,
                            "uom": uom
                        }
                        total_stock_info.append(temp_dict)

        total_stock_info = sorted(total_stock_info, key=lambda k: k["atp_qty"], reverse=True) 
        order_information_list = []
        remaining_qty = order_qty
        for stock_info in total_stock_info:
            if remaining_qty==0:
                break
            if stock_info["atp_qty"]>=remaining_qty:
                temp_dict = {
                    "qty": format(remaining_qty,'.2f'),
                    "batch": stock_info["batch"],
                    "uom": stock_info["uom"],
                    "from_holding": from_holding,
                    "seller_sku": seller_sku
                }
                remaining_qty = 0
            else:
                temp_dict = {
                    "qty": format(stock_info["atp_qty"],'.2f'),
                    "batch": stock_info["batch"],
                    "uom": stock_info["uom"],
                    "from_holding": from_holding,
                    "seller_sku": seller_sku
                }
                remaining_qty -= stock_info["atp_qty"]
            order_information_list.append(temp_dict)

        logger.info("fetch_order_information_for_sap_punching: %s", str(order_information_list))
        return order_information_list
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("fetch_order_information_for_sap_punching: %s at %s", e, str(exc_tb.tb_lineno))
        return []


def generate_sap_order_format(unit_order_list):

    try:
        os.system("rm ./files/csv/sap-order-format.xlsx")
    except Exception as e:
        pass

    workbook = xlsxwriter.Workbook('./files/csv/sap-order-format.xlsx')

    # Step 1

    worksheet1 = workbook.add_worksheet()

    row = ["Company Code",
           "Distribution Channel",
           "Division",
           "Sales Office",
           "Order Type",
           "SAP Customer ID",
           "Order ID",
           "Article Code",
           "Qty",
           "UoM",
           "Batch"]

    cnt = 0
        
    colnum = 0
    for k in row:
        worksheet1.write(cnt, colnum, k)
        colnum += 1

    for unit_order in unit_order_list:
        try:
            cnt += 1

            dealshub_product_obj = DealsHubProduct.objects.get(uuid=unit_order["productUuid"])

            sap_details = fetch_sap_details_for_order_punching(dealshub_product_obj)

            common_row = ["" for i in range(11)]
            common_row[0] = sap_details["company_code"]
            common_row[1] = "01"
            common_row[2] = "00"
            common_row[3] = sap_details["sales_office"]
            common_row[4] = "ZWIC"
            common_row[5] = "40000637"
            common_row[6] = unit_order["orderId"]
            common_row[7] = dealshub_product_obj.get_seller_sku()
            common_row[8] = unit_order["quantity"]
            
            colnum = 0
            for k in common_row:
                worksheet1.write(cnt, colnum, k)
                colnum += 1

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("generate_sap_order_format: %s at %s", e, str(exc_tb.tb_lineno))


    # Step 2

    worksheet2 = workbook.add_worksheet()

    row = ["PO Order Type",
           "Company Code",
           "Purchase Org",
           "Site",
           "Storage Location",
           "Purchase Group",
           "Pricing Condition (Header) ZPA3",
           "Invoice Reference",
           "Vendor Code",
           "Item Code",
           "Order Unit",
           "Order Price UoM",
           "Purchase Order Qty",
           "Net Price",
           "Date"]

    cnt = 0
        
    colnum = 0
    for k in row:
        worksheet2.write(cnt, colnum, k)
        colnum += 1

    for unit_order in unit_order_list:
        try:
            cnt += 1

            dealshub_product_obj = DealsHubProduct.objects.get(uuid=unit_order["productUuid"])

            sap_details = fetch_sap_details_for_order_punching(dealshub_product_obj)

            common_row = ["" for i in range(15)]
            common_row[0] = "WIC"
            common_row[1] = "1200"
            common_row[2] = "1200"
            common_row[3] = "1202"
            common_row[4] = "TG01"
            common_row[5] = "GP2"

            common_row[7] = "Invoice Ref ID"
            common_row[8] = sap_details["vendor_code"]
            common_row[9] = dealshub_product_obj.get_seller_sku()
            common_row[10] = "EA"
            common_row[11] = "EA"
            common_row[12] = unit_order["quantity"]
            common_row[13] = unit_order["price"]
            common_row[14] = unit_order["orderPlacedDate"]

            colnum = 0
            for k in common_row:
                worksheet2.write(cnt, colnum, k)
                colnum += 1

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("generate_sap_order_format: %s at %s", e, str(exc_tb.tb_lineno))


    # Step 3

    worksheet3 = workbook.add_worksheet()

    row = ["Company Code",
           "Order Type",
           "SAP Customer ID",
           "End Customer Name",
           "Area",
           "Order ID",
           "Article Code",
           "Qty",
           "UoM",
           "Batch",
           "Total Amount",
           "Promotion Discount Line Item",
           "Voucher Discount Header",
           "Courier Charge Header",
           "COD Charge Header",
           "Other Charge-Header",
           "Other Charge-Line Item"]

    cnt = 0
        
    colnum = 0
    for k in row:
        worksheet3.write(cnt, colnum, k)
        colnum += 1

    for unit_order in unit_order_list:
        try:
            cnt += 1

            dealshub_product_obj = DealsHubProduct.objects.get(uuid=unit_order["productUuid"])

            order_type = "ZJCR"
            customer_code = ""
            if unit_order["shippingMethod"]=="WIG Fleet":
                customer_code = "50000629"
            elif unit_order["shippingMethod"]=="TFM":
                customer_code = "50000627"

            company_code = get_company_code_from_brand_name(dealshub_product_obj.get_brand())
            response = get_sap_batch_and_uom(company_code, dealshub_product_obj.get_seller_sku())
            batch = response["batch"]
            uom = response["uom"]

            common_row = ["" for i in range(17)]
            common_row[0] = "1200"
            common_row[1] = order_type
            common_row[2] = customer_code
            common_row[3] = unit_order["customerName"]
            common_row[4] = unit_order["area"]
            common_row[5] = unit_order["orderId"]
            common_row[6] = dealshub_product_obj.get_seller_sku()
            common_row[7] = unit_order["quantity"]
            common_row[8] = uom
            common_row[9] = batch
            common_row[10] = unit_order["total"]

            colnum = 0
            for k in common_row:
                worksheet3.write(cnt, colnum, k)
                colnum += 1

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("generate_sap_order_format: %s at %s", e, str(exc_tb.tb_lineno))

    workbook.close()

def handle_SAP_processing(order_obj, data, response):
    user_input_requirement, is_final_response = get_user_input_requirement(order_obj, response)
    if is_final_response:
        return is_final_response
    is_final_response = True
    user_input_sap = data.get("user_input_sap", None)

    if user_input_sap == None:
        modal_info_list = get_modal_info_list(order_obj, user_input_requirement)
        if len(modal_info_list) > 0:
            response["modal_info_list"] = modal_info_list
            response["status"] = 200
            return is_final_response

    sap_info_render = []

    unit_order_objs = UnitOrder.objects.filter(order=order_obj).exclude(current_status_admin="cancelled")

    if unit_order_objs.filter(grn_filename="").exists():
        grouped_unit_orders = get_unit_orders_grouped_by_brand(unit_order_objs)
        for brand_name in grouped_unit_orders: 
            if grouped_unit_orders[brand_name][0].sap_status=="In GRN":
                continue

            order_information = {}
            company_code_obj = CompanyCodeSAP.objects.get(location_group=order_obj.location_group, brand__name=brand_name)
            order_information["order_id"] = order_obj.bundleid.replace("-","")
            order_information["refrence_id"] = order_obj.bundleid.replace("-","&#45;")
            is_b2b = order_obj.location_group.is_b2b
            order_information["is_b2b"] = is_b2b
            if is_b2b==True:
                order_information["street"] = json.loads(order_obj.shipping_address.address_lines)[1]
                order_information["region"] = order_obj.shipping_address.state
                order_information["telephone"] = order_obj.shipping_address.contact_number
                order_information["email"] = order_obj.owner.email
                b2b_user_obj = B2BUser.objects.get(username=order_obj.owner.username) 
                order_information["trn"] = b2b_user_obj.vat_certificate_id
                if order_information["trn"] == "":
                    response["message"] = "TRN number is empty"
                    response["status"] = 406
                    return is_final_response
            order_information["items"] = []
            
            for unit_order_obj in grouped_unit_orders[brand_name]:

                seller_sku = unit_order_obj.product.get_seller_sku()
                x_value = ""
                
                if user_input_requirement[seller_sku]==True:
                    x_value = user_input_sap[seller_sku]
                
                item_list =  fetch_order_information_for_sap_punching(seller_sku, company_code_obj.code, x_value, unit_order_obj.quantity)
                for item in item_list:
                    price = format(unit_order_obj.get_subtotal_without_vat_custom_qty(item["qty"]),'.2f')
                    item.update({"price": price})
                order_information["items"] += item_list
            logger.info("FINAL ORDER INFO: %s", str(order_information))

            orig_result_pre = create_intercompany_sales_order(company_code_obj.code, order_information)

            manual_intervention_required = is_manual_intervention_required(orig_result_pre)

            if manual_intervention_required==True:
                order_obj.sap_status = "Manual"
                order_obj.save()

            for item in order_information["items"]:
                
                temp_dict2 = {}
                temp_dict2["seller_sku"] = item["seller_sku"]
                temp_dict2["intercompany_sales_info"] = orig_result_pre
                
                sap_info_render.append(temp_dict2)
                
                unit_order_obj = UnitOrder.objects.get(product__product__base_product__seller_sku=item["seller_sku"],order=order_obj)
                
                result_pre = orig_result_pre["doc_list"]
                do_exists = 0
                so_exists = 0
                do_id = ""
                so_id = ""
                
                for k in result_pre:
                    if k["type"]=="DO":
                        do_exists = 1
                        do_id = k["id"]
                    elif k["type"]=="SO":
                        so_exists = 1
                        so_id = k["id"]
                
                if so_exists==0 or do_exists==0:
                    error_flag = 1
                    unit_order_obj.sap_status = "Failed"
                    unit_order_obj.sap_intercompany_info = json.dumps(orig_result_pre)
                    unit_order_obj.save()
                    try:
                        p1 = threading.Thread(target=notify_grn_error, args=(unit_order_obj.order,))
                        p1.start()
                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        logger.error("notify_grn_error: %s at %s", e, str(exc_tb.tb_lineno))

                    continue
                
                unit_order_information = {}
                unit_order_information["intercompany_sales_info"] = {}
                item["order_id"] = str(order_information["order_id"])
                unit_order_information["intercompany_sales_info"] = item
                unit_order_obj.order_information = json.dumps(unit_order_information)
                
                unit_order_obj.grn_filename = str(do_id)
                unit_order_obj.sap_intercompany_info = json.dumps(orig_result_pre)
                unit_order_obj.sap_status = "In GRN"
                unit_order_obj.save()
    return not(is_final_response)


def get_user_input_requirement(order_obj, response):
    '''
    Returns seller_sku wise user_input_requirement (bool value) information
    '''
    is_final_response = True
    user_input_requirement = {}            
    for unit_order_obj in UnitOrder.objects.filter(order=order_obj).exclude(current_status_admin="cancelled"):
        seller_sku = unit_order_obj.product.get_seller_sku()
        brand_name = unit_order_obj.product.get_brand()
        company_code_obj = CompanyCodeSAP.objects.get(location_group=order_obj.location_group, brand__name=brand_name)
        stock_price_information = fetch_prices_and_stock(seller_sku, company_code_obj.code)

        if stock_price_information["status"] == 500:
            response["status"] = 403
            response["message"] = stock_price_information["message"]
            logger.error("handle_SAP_processing: fetch prices and stock gave 500!")
            return user_input_requirement, is_final_response

        user_input_requirement[seller_sku] = is_user_input_required_for_sap_punching(stock_price_information, unit_order_obj.quantity)
    return user_input_requirement, not(is_final_response)


def get_modal_info_list(order_obj, user_input_requirement):
    modal_info_list = []
    for unit_order_obj in UnitOrder.objects.filter(order=order_obj).exclude(current_status_admin="cancelled"):
        seller_sku = unit_order_obj.product.get_seller_sku()
        brand_name = unit_order_obj.product.get_brand()
        company_code_obj = CompanyCodeSAP.objects.get(location_group=order_obj.location_group, brand__name=brand_name)
        
        if user_input_requirement[seller_sku]==True:
            result = fetch_prices_and_stock(seller_sku, company_code_obj.code)
            result["uuid"] = unit_order_obj.uuid
            result["seller_sku"] = seller_sku
            result["disable_atp_holding"] = False
            result["disable_atp"] = False
            result["disable_holding"] = False
            if result["total_holding"] < unit_order_obj.quantity and result["total_atp"] < unit_order_obj.quantity:
                result["disable_atp_holding"] = True
            elif result["total_atp"] <  unit_order_obj.quantity:
                result["disable_atp"] = True
            elif result["total_holding"] < unit_order_obj.quantity:
                result["disable_holding"] = True
            modal_info_list.append(result)
    return modal_info_list


def get_unit_orders_grouped_by_brand(unit_order_objs):
    '''
    unit_order_objs are grouped by their brands and the dictionary[brand : unit_order_objs] is returned
    '''
    grouped_unit_orders = {} 
    for unit_order_obj in unit_order_objs:
        brand_name = unit_order_obj.product.get_brand()
        if brand_name not in grouped_unit_orders:
            grouped_unit_orders[brand_name] = []
        grouped_unit_orders[brand_name].append(unit_order_obj)
    
    return grouped_unit_orders

    