from WAMSApp.utils import *
from WAMSApp.xml_generators_SAP import *
from WAMSApp.SAP_constants import *

import requests
import xmltodict
import json
import time
import xlsxwriter

logger = logging.getLogger(__name__)

def fetch_prices_and_stock(seller_sku,company_code):
    
    try:

        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = ("MOBSERVICE", "~lDT8+QklV=(")
        
        body = xml_generator_for_price_and_stock_SAP(seller_sku,company_code,CUSTOMER_ID)
        
        response = requests.post(url=PRICE_STOCK_URL, auth=credentials, data=body, headers=headers)
        
        content = response.content
        xml_content = xmltodict.parse(content)
        response_dict = json.loads(json.dumps(xml_content))

        items = response_dict["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_STOCK_PRICEResponse"]["T_DATA"]["item"]
        # logger.info(items)
        
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
        credentials = ("MOBSERVICE", "~lDT8+QklV=(")
        # credentials = ("WIABAP", "pradeepabap456")

        logger.info("In Utility Function : %s at company code %s",seller_sku,company_code)
        
        transfer_information = []

        product_obj = Product.objects.filter(base_product__seller_sku=seller_sku)[0]
        is_sap_exception = product_obj.is_sap_exception

        result ={
            "total_holding_before" : "",
            "total_atp_before" : "",
            "total_holding_after" : "",
            "total_atp_after" : "",
            "stock_status" : "",
            "SAP_message" : ""
        }

        prices_and_stock_information = fetch_prices_and_stock(seller_sku,company_code)
        
        if is_sap_exception == True:
            holding_threshold=product_obj.holding_threshold
            atp_threshold=product_obj.atp_threshold
        else:
            holding_threshold = float(prices_and_stock_information["holding_threshold"])
            atp_threshold = float(prices_and_stock_information["atp_threshold"])

        total_holding = float(prices_and_stock_information["total_holding"])
        total_atp = float(prices_and_stock_information["total_atp"])

        result["total_holding_before"] = total_holding
        result["total_atp_before"] = total_atp
        
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
            result["stock_status"] = "GOOD"

        logger.info(transfer_information)

        if len(transfer_information) > 0:

            body = xml_generator_for_holding_tansfer(company_code,CUSTOMER_ID,transfer_information)
            response = requests.post(url=TRANSFER_HOLDING_URL, auth=credentials, data=body, headers=headers)
            content = response.content
            xml_content = xmltodict.parse(content)
            response_dict = json.loads(json.dumps(xml_content))

            response_dict = response_dict["soap-env:Envelope"]["soap-env:Body"]["n0:ZAPP_HOLDING_SOResponse"]
            items = response_dict["T_MESSAGE"]["item"]

            if isinstance(items,list):
                for item in items:
                    if item["MESSAGE"] != None:
                        SAP_message = item["MESSAGE"]
                        result["SAP_message"] = SAP_message
            else:
                if items["MESSAGE"] != None:
                    SAP_message = items["MESSAGE"]
                    result["SAP_message"] = SAP_message

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
            else:
                result["stock_status"] = "CRITICAL STOCK"

            result["total_holding_after"] = total_holding
            result["total_atp_after"] = total_atp
            return result

        else :
            result["SAP_message"] = "NO HOLDING TRANSFER"
            logger.info("transfer_from_atp_to_holding : Nothing to transfer to Holding in this call",seller_sku)
            return result

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("transfer_from_atp_to_holding: %s at %s", str(e), str(exc_tb.tb_lineno))
        return result

def create_intercompany_sales_order(company_code,order_information):
    
    try:

        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = ("MOBSERVICE", "~lDT8+QklV=(")
        logger.info(order_information)

        body = xml_generator_for_intercompany_tansfer(company_code,CUSTOMER_ID,order_information)
        logger.info("XML Intercompany: %s",body)

        response = requests.post(url=ONLINE_ORDER_URL, auth=credentials, data=body, headers=headers)
        
        content = response.content
        xml_content = xmltodict.parse(content)
        response_dict = json.loads(json.dumps(xml_content))
        logger.info(response_dict)

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
        logger.error("create_intercompany_sales_order: %s at %s", str(e), str(exc_tb.tb_lineno))
        return []

def create_final_order(company_code,order_information):
    
    try:

        headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}
        credentials = ("MOBSERVICE", "~lDT8+QklV=(")

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

        body = xml_generator_for_final_billing(company_code,CUSTOMER_ID_FINAL_BILLING,order_information)
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


def create_holding_transfer_report(dealshub_product_objs):

    try:
        filename = "holding_transfer_report.xlsx"

        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        row = ["Seller SKU",
               "Brand Name",
               "Company Code",
               "Holding Before",
               "Holding After",
               "ATP Before",
               "ATP After",
               "Status",
               "SAP Message"]

        cnt = 0
            
        colnum = 0
        for k in row:
            worksheet.write(cnt, colnum, k)
            colnum += 1

        for dealshub_product_obj in dealshub_product_objs:

            cnt+=1
            common_row = ["" for i in range(9)]

            seller_sku = dealshub_product_obj.get_seller_sku()
            brand_name = dealshub_product_obj.get_brand()
            status = "FAILED"
            logger.info(seller_sku)
            
            try:
                company_code = BRAND_COMPANY_DICT[brand_name.lower()]
            except Exception as e:
                company_code = "BRAND NOT RECOGNIZED"

            common_row[0] = str(seller_sku)
            common_row[1] = str(brand_name)
            common_row[2] = str(company_code)

            if company_code != "BRAND NOT RECOGNIZED":
                try :
                    response_dict = transfer_from_atp_to_holding(seller_sku,company_code)
                   
                    common_row[3] = str(response_dict["total_holding_before"])
                    common_row[5] = str(response_dict["total_atp_before"])
                    common_row[4] = str(response_dict["total_holding_after"])
                    common_row[6] = str(response_dict["total_atp_after"])
                    common_row[7] = str(response_dict["stock_status"])
                    common_row[8] = str(response_dict["SAP_message"])

                except Exception as e:
                    logger.info(e)
                    common_row[7] = str("INTERNAL ERROR")
                    
            colnum = 0
            for k in common_row:
                worksheet.write(cnt, colnum, k)
                colnum += 1
        workbook.close()

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("create_holding_transfer_report: %s at %s", str(e), str(exc_tb.tb_lineno))