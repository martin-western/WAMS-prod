import requests
import json
import sys
import xmltodict
import sys
import logging
from dealshub.models import *

logger = logging.getLogger(__name__)

def request_postaplus(order_obj):

    try:
        currency = order_obj.location_group.location.currency
        contact_number = order_obj.owner.contact_number
        customer_name = order_obj.get_customer_full_name()
        bundleid = order_obj.bundleid

        postaplus_info = json.loads(order_obj.location_group.postaplus_info)
        postaplus_codestation = postaplus_info["codestation"]
        postaplus_password = postaplus_info["password"]
        postaplus_shipper_account = postaplus_info["shipper_account"]
        postaplus_username = postaplus_info["postaplus_username"]

        consignee_company = postaplus_info["consignee_company"]
        consignee_from_address = postaplus_info["consignee_from_address"]
        consignee_from_area = postaplus_info["consignee_from_area"]
        consignee_from_city = postaplus_info["consignee_from_city"]
        consignee_from_country = postaplus_info["consignee_from_country"]
        consignee_from_mobile = postaplus_info["consignee_from_mobile"]
        consignee_from_province = postaplus_info["consignee_from_province"]
        consignee_to_address = order_obj.shipping_address.get_shipping_address()
        consignee_to_city = consignee_from_city
        consignee_to_country = consignee_from_country
        consignee_to_province = consignee_from_province

        total_pieces = 0
        connoteperminv = ""
        description = ""
        total_weight = 0
        for unit_order_obj in UnitOrder.objects.filter(order=order_obj):
            connoteperminv += """
                <pos:CONNOTEPERMINV>
                    <pos:CodeHS>8504.90.00</pos:CodeHS>
                    <pos:CodePackageType>PCKT1</pos:CodePackageType>
                    <pos:Description>"""+unit_order_obj.product.get_seller_sku()+"""</pos:Description>
                    <pos:OrginCountry>ARE</pos:OrginCountry>
                    <pos:Quantity>"""+str(unit_order_obj.quantity)+"""</pos:Quantity>
                    <pos:RateUnit>"""+str(unit_order_obj.price)+"""</pos:RateUnit>
                </pos:CONNOTEPERMINV>"""
            total_weight += unit_order_obj.product.get_weight() 
            description += unit_order_obj.product.get_seller_sku()+" ("+str(unit_order_obj.quantity)+"), "
            total_pieces += unit_order_obj.quantity

        total_weight = max(total_weight, 0.5)

        postaplus_request_body =  """
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/" xmlns:pos="http://schemas.datacontract.org/2004/07/PostaWebClient">
       <soapenv:Header/>
       <soapenv:Body>
          <tem:Shipment_Creation>
             <tem:SHIPINFO>
                <pos:ClientInfo>
                   <pos:CodeStation>"""+postaplus_codestation+"""</pos:CodeStation>
                   <pos:Password>"""+postaplus_password+"""</pos:Password>
                   <pos:ShipperAccount>"""+postaplus_shipper_account+"""</pos:ShipperAccount>
                   <pos:UserName>"""+postaplus_username+"""</pos:UserName>
                </pos:ClientInfo>
                <pos:CodeCurrency>"""+currency+"""</pos:CodeCurrency>
                <pos:CodeService>SRV6</pos:CodeService>
                <pos:CodeShippmentType>SHPT2</pos:CodeShippmentType>
                <pos:ConnoteContact>
                   <pos:Email1></pos:Email1>
                   <pos:Email2></pos:Email2>
                   <pos:TelHome></pos:TelHome>
                   <pos:TelMobile>"""+contact_number+"""</pos:TelMobile>
                </pos:ConnoteContact>
                <pos:ConnoteDescription>"""+description+"""</pos:ConnoteDescription>
                <pos:ConnotePerformaInvoice>
                    """+connoteperminv+"""
                </pos:ConnotePerformaInvoice>
                <pos:ConnotePieces>"""+str(total_pieces)+"""</pos:ConnotePieces>
                <pos:ConnoteProhibited>N</pos:ConnoteProhibited>
                <pos:ConnoteRef>
                    <pos:Reference1></pos:Reference1>
                    <pos:Reference2>"""+bundleid+"""</pos:Reference2>
                </pos:ConnoteRef>
                <pos:Consignee>
                   <pos:Company>"""+consignee_company+"""</pos:Company>
                   <pos:FromAddress>"""+consignee_from_address+"""</pos:FromAddress>
                   <pos:FromArea>"""+consignee_from_area+"""</pos:FromArea>
                   <pos:FromCity>"""+consignee_from_city+"""</pos:FromCity>
                   <pos:FromCodeCountry>"""+consignee_from_country+"""</pos:FromCodeCountry>
                   <pos:FromMobile>"""+consignee_from_mobile+"""</pos:FromMobile>
                   <pos:FromName>WESTERN INTERNATIONAL LLC - WIGME.COM</pos:FromName>
                   <pos:FromPinCode></pos:FromPinCode>
                   <pos:FromProvince>"""+consignee_from_province+"""</pos:FromProvince>
                   <pos:FromTelphone>"""+consignee_from_mobile+"""</pos:FromTelphone>
                   <pos:ToAddress>"""+consignee_to_address+"""</pos:ToAddress>
                   <pos:ToArea>NA</pos:ToArea>
                   <pos:ToCity>"""+consignee_to_city+"""</pos:ToCity>
                   <pos:ToCodeCountry>"""+consignee_to_country+"""</pos:ToCodeCountry>
                   <pos:ToCodeSector></pos:ToCodeSector>
                   <pos:ToMobile>"""+contact_number+"""</pos:ToMobile>
                   <pos:ToName>"""+customer_name+"""</pos:ToName>
                   <pos:ToProvince>"""+consignee_to_province+"""</pos:ToProvince>
                   <pos:ToTelPhone>"""+contact_number+"""</pos:ToTelPhone>
                </pos:Consignee>
                <pos:ItemDetails>
                    <pos:ITEMDETAILS>
                      <pos:ConnoteHeight>0</pos:ConnoteHeight>
                      <pos:ConnoteLength>0</pos:ConnoteLength>
                      <pos:ConnoteWeight>"""+str(total_weight)+"""</pos:ConnoteWeight>
                      <pos:ConnoteWidth>0</pos:ConnoteWidth>
                      <pos:ScaleWeight>"""+str(total_weight)+"""</pos:ScaleWeight>
                   </pos:ITEMDETAILS>
                </pos:ItemDetails>
             </tem:SHIPINFO>
          </tem:Shipment_Creation>
       </soapenv:Body>
    </soapenv:Envelope>"""

        logger.info("request body: %s", str(postaplus_request_body))

        response = requests.post(url="https://staging.postaplus.net/APIService/PostaWebClient.svc?wsdl",
                                 headers={
                                   "Content-Type": "text/xml",
                                   "SOAPAction":"http://tempuri.org/IPostaWebClient/Shipment_Creation"
                                 },
                                 data=postaplus_request_body, timeout=10)

        content = response.content
        content = xmltodict.parse(content)
        content = json.loads(json.dumps(content))

        logger.info("request content: %s", str(content))

        postaplus_info = {
            "awb_number": content["s:Envelope"]["s:Body"]["Shipment_CreationResponse"]["Shipment_CreationResult"]
        }

        order_obj.postaplus_info = json.dumps(postaplus_info)
        order_obj.is_postaplus = True
        order_obj.save()

        for unit_order_obj in UnitOrder.objects.filter(order=order_obj):
            unit_order_obj.shipping_method = "Postaplus"
            if unit_order_obj.current_status_admin=="pending":
                unit_order_obj.current_status_admin = "approved"
                UnitOrderStatus.objects.create(unit_order=unit_order_obj, status="ordered", status_admin="approved")
            unit_order_obj.save()

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("request_postaplus: %s at %s", e, str(exc_tb.tb_lineno))


def fetch_postaplus_tracking(awb_number):
    
    tracking_data = []
    try:
        postaplus_request_body = """
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
                <soapenv:Header/>
                <soapenv:Body>
                    <tem:Shipment_Tracking>
                        <tem:UserName>DXB51555</tem:UserName>
                        <tem:Password>12345</tem:Password>
                        <tem:ShipperAccount>DXB51555</tem:ShipperAccount>
                        <tem:AirwaybillNumber>"""+awb_number+"""</tem:AirwaybillNumber>
                        <tem:Reference1></tem:Reference1>
                        <tem:Reference2></tem:Reference2>
                    </tem:Shipment_Tracking>
                </soapenv:Body>
            </soapenv:Envelope>"""

        response = requests.post(url="https://staging.postaplus.net/APIService/PostaWebClient.svc?wsdl",
                                 headers={
                                   "Content-Type": "text/xml",
                                   "SOAPAction":"http://tempuri.org/IPostaWebClient/Shipment_Tracking"
                                 },
                                 data=postaplus_request_body, timeout=10)

        content = response.content
        content = xmltodict.parse(content)
        content = json.loads(json.dumps(content))
        track_data = content["s:Envelope"]["s:Body"]["Shipment_TrackingResponse"]["Shipment_TrackingResult"]["a:TRACKSHIPMENT"]

        if type(track_data)==list:
            for data in track_data:
                temp_data = {}
                temp_data["timestamp"] = data["a:DateTime"]
                temp_data["event"] = data["a:EventName"]
                tracking_data.append(temp_data)
        else:
            temp_data = {}
            temp_data["timestamp"] = track_data["a:DateTime"]
            temp_data["event"] = track_data["a:EventName"]
            tracking_data.append(temp_data)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("fetch_postaplus_tracking: %s at %s", e, str(exc_tb.tb_lineno))

    return tracking_data