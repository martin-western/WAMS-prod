from WAMSApp.models import *
from WAMSApp.utils import *

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Count
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

import requests
import json
import pytz
import csv
import logging
import sys
import xlrd
import time


from datetime import datetime
from django.utils import timezone
from django.core.files import File

logger = logging.getLogger(__name__)

session_id = "9df688a9-8079-4f0e-9a78-080417c7d2a8"
outlet_ref = "e209b88c-9fb6-4be8-ab4b-e4b977ad0e0d"

headers = {
            "Content-Type": "application/vnd.ni-identity.v1+json", 
            "Authorization": "Basic YWJjMjQyZDEtZWJlMC00NDc1LTlkMmItMWY3Y2ZmYWY0MGFkOjFmMmRlNWY2LTM1NTYtNDU3Yi05ZDVhLTExMGQ4MTU5M2ViNg==" #NDVlNzFjOTAtYjk1ZS00YmE4LWJlZGMtOWI2YjlhMTBhYmE1OmMwODc2OTBjLTM4ZmQtNGZlMS04YjFiLWUzOWQ1ODdiMDhjYg=="
        }

body = {
    "grant_type": "client_credentials"
}

response = requests.post("https://api-gateway.sandbox.ngenius-payments.com/identity/auth/access-token", 
                headers=headers)

print(response.content)

response_dict = json.loads(response.content)
access_token = response_dict["access_token"]

headers = {
            "Authorization": "Bearer " + access_token ,
            "Content-Type": "application/vnd.ni-payment.v2+json", 
            "Accept": "application/vnd.ni-payment.v2+json" 
        }

body = {
  "action": "SALE",
  "amount": { 
  	"currencyCode": "AED", 
  	"value":100 
  	}
}


API_URL = "https://api-gateway.sandbox.ngenius-payments.com/transactions/outlets/"+outlet_ref +"/payment/hosted-session/"+session_id

response2 = requests.post(API_URL, data=json.dumps(body),headers=headers)

print(response2.content)

API_URL = "https://staging.postaplus.net/APIService/PostaWebClient.svc?wsdl"

headers = {
	"Content-Type" : "text/xml"
}

xml_string = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:tem="http://tempuri.org/"
    xmlns:ship="http://schemas.datacontract.org/2004/07/ShippingClient">
    <soapenv:Header/>
    <soapenv:Body>
        <tem:Shipment_Creation>
            <tem:SHIPINFO>
                <!--Required-->
                <ship:ClientInfo>
                    <!--Required:-->
                    <ship:CodeStation>DXB</ship:CodeStation>
                    <!--Required:-->
                    <ship:Password>12345</ship:Password>
                    <!--Required:-->
                    <ship:ShipperAccount>DXB51555</ship:ShipperAccount>
                    <!--Required:-->
                    <ship:UserName>DXB51555</ship:UserName>
                </ship:ClientInfo>
                <!--Required:-->
                <ship:CodeCurrency>AED</ship:CodeCurrency>
                <!--Required:-->
                <ship:CodeService>SRV3</ship:CodeService>
                <!--Required:-->
                <ship:CodeShippmentType>SHPT2</ship:CodeShippmentType>
                <!--Required:-->
                <ship:ConnoteContact>
                    <!--Required:-->
                    <ship:TelMobile>9725705283</ship:TelMobile>
                </ship:ConnoteContact>
                <!--Required:-->
                <ship:ConnoteDescription>Test Description</ship:ConnoteDescription>
                <!--Conditional:-->
                <ship:ConnotePerformaInvoice>
                    <!--Zero or more repetitions:-->
                    <ship:CONNOTEPERMINV>
                        <!--Conditional/Required:-->
                        <ship:CodeHS>8504.90.00</ship:CodeHS>
                        <!--Conditional/Required:-->
                        <ship:CodePackageType>PCKT1</ship:CodePackageType>
                        <!--Conditional/Required:-->
                        <ship:Description>COMPUTER PART</ship:Description>
                        <!--Conditional/Required:-->
                        <ship:OrginCountry>ARE</ship:OrginCountry>
                        <!--Conditional/Required:-->
                        <ship:Quantity>1</ship:Quantity>
                        <!--Conditional/Required:-->
                        <ship:RateUnit>150</ship:RateUnit>
                    </ship:CONNOTEPERMINV>
                </ship:ConnotePerformaInvoice>
                <!--Required:-->
                <ship:ConnotePieces>2</ship:ConnotePieces>
                </ship:ConnoteRef>
                <!--Required:-->
                <ship:Consignee>
                    <!--Required:-->
                    <ship:Company>ABC TEST COMPANY</ship:Company>
                    <!--Required:-->
                    <ship:FromAddress>STREET 4</ship:FromAddress>
                    <!--Required:-->
                    <ship:FromArea>AREA</ship:FromArea>
                    <!--Required:-->
                    <ship:FromCity>CITY415670</ship:FromCity>
                    <!--Required:-->
                    <ship:FromCodeCountry>ARE</ship:FromCodeCountry>
                    <!--Required:-->
                    <ship:FromMobile>45887</ship:FromMobile>
                    <!--Required:-->
                    <ship:FromName>RAJ</ship:FromName>
                    <!--Required:-->
                    <ship:FromProvince>AJ</ship:FromProvince>
                    <!--Required:-->
                    <ship:ToAddress>NIL</ship:ToAddress>
                    <!--Required:-->
                    <ship:ToArea>AREA1004</ship:ToArea>
                    <!--Required:-->
                    <ship:ToCity>CITY415670</ship:ToCity>
                    <!--Required:-->
                    <ship:ToCodeCountry>ARE</ship:ToCodeCountry>
                    <!--Required:-->
                    <ship:ToMobile>971554845</ship:ToMobile>
                    <!--Required:-->
                    <ship:ToName>ABHINAV</ship:ToName>
                    <!--Required:-->
                    <ship:ToProvince>AJ</ship:ToProvince>
                    <!--Required:-->
                    <ship:ToTelPhone>1881881</ship:ToTelPhone>
                </ship:Consignee>
                <!--Optional:-->
                <ship:CostShipment>150</ship:CostShipment>
                <!--Optional:-->
                <ship:IsMPS></ship:IsMPS>
                <!--Required:-->
                <ship:ItemDetails>
                    <!--Zero or more repetitions:-->
                    <ship:ITEMDETAILS>
                        <!--Required:-->
                        <ship:ConnoteHeight>40</ship:ConnoteHeight>
                        <!--Required:-->
                        <ship:ConnoteLength>20</ship:ConnoteLength>
                        <!--Required:-->
                        <ship:ConnoteWeight>40</ship:ConnoteWeight>
                        <!--Required:-->
                        <ship:ConnoteWidth>40</ship:ConnoteWidth>
                        <!--Required:-->
                        <ship:ScaleWeight>10</ship:ScaleWeight>
                    </ship:ITEMDETAILS>
                </ship:ItemDetails>
                <!--Optional:-->
                <ship:NeedPickUp>N</ship:NeedPickUp>
                <!--Optional:-->
                <ship:NeedRoundTrip>N</ship:NeedRoundTrip>
                <!--Optional:-->
                <ship:ParentWayBill></ship:ParentWayBill>
                <!--Optional:-->
                <ship:PayMode></ship:PayMode>
                <!--Optional:-->
                <ship:WayBill></ship:WayBill>
            </tem:SHIPINFO>
        </tem:Shipment_Creation>
    </soapenv:Body>
</soapenv:Envelope>"""

xml_string = xml_string.encode('utf-8')

response = requests.post(API_URL, data=xml_string, headers=headers)