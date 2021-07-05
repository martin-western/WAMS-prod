from WAMSApp.models import *
from dealshub.models import *
from WAMSApp.sap.SAP_constants import *
import json
import requests
import xmltodict

def fetch_refresh_stock(seller_sku, company_code, location_code):
    try:
        url="http://94.56.89.114:8001/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"
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
        response2 = requests.post(url, auth=credentials, data=body, headers=headers, timeout=10)
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
        print("fetch_tg01_stock %s at %s", e, str(exc_tb.tb_lineno))
        return 0

dealshub_product_objs = DealsHubProduct.objects.filter(stock=0, is_published=True)
i=0
for dealshub_product_obj in dealshub_product_objs:
    i+=1
    brand = str(dealshub_product_obj.product.base_product.brand).lower()
    seller_sku = str(dealshub_product_obj.product.base_product.seller_sku)
    stock = 0
    if "wigme" in seller_sku.lower():
        continue
    if brand=="geepas":
        stock1 = fetch_refresh_stock(seller_sku, "1070", "TG01")
        stock2 = fetch_refresh_stock(seller_sku, "1000", "AFS1")
        stock = max(stock1, stock2)
    elif brand=="baby plus":
        stock = fetch_refresh_stock(seller_sku, "5550", "AFS1")
    elif brand=="royalford":
        stock = fetch_refresh_stock(seller_sku, "3000", "AFS1")
    elif brand=="krypton":
        stock = fetch_refresh_stock(seller_sku, "2100", "TG01")
    elif brand=="olsenmark":
        stock = fetch_refresh_stock(seller_sku, "1100", "AFS1")
    elif brand=="ken jardene":
        stock = fetch_refresh_stock(seller_sku, "5550", "AFS1") # 
    elif brand=="younglife":
        stock = fetch_refresh_stock(seller_sku, "5000", "AFS1")
    if stock > 10:
        dealshub_product_obj.stock = 5
    else:
        dealshub_product_obj.stock = 0
    print(i,"SKU : ",seller_sku,"Stock : " ,stock,"Updated Stock : " ,dealshub_product_obj.stock)
    dealshub_product_obj.save()