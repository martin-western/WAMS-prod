from WAMSApp.models import *
from WAMSApp.utils import *

from MWS import mws,APIs

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
from django.utils.timezone import utc

import requests
import json
import pytz
import csv
import logging
import sys
import xlrd
import time


from datetime import datetime, timedelta
from django.utils import timezone
from django.core.files import File

logger = logging.getLogger(__name__)

MWS_PARAMS = settings.MWS_PARAMS

MWS_ACCESS_KEY = MWS_PARAMS["MWS_ACCESS_KEY"] 
MWS_SECRET_KEY = MWS_PARAMS["MWS_SECRET_KEY"]
SELLER_ID = MWS_PARAMS["SELLER_ID"]

marketplace_id_uae = mws.Marketplaces["AE"].marketplace_id

amazon_order_ids = []

def convert_to_list(obj):

    if(type(obj)=="dict"):
        temp_list = []
        temp_list.append(obj)
        obj = temp_list

    return obj

class FetchOrdersPeriodicallyAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data=request.data
            logger.info("FetchOrdersPeriodicallyAPI: %s", str(data))

            regions = ["AE"]

            for region in regions:

                reports_api = APIs.Reports(MWS_ACCESS_KEY,MWS_SECRET_KEY,SELLER_ID, region=region)
                orders_api =  APIs.Orders(MWS_ACCESS_KEY,MWS_SECRET_KEY, SELLER_ID, region=region)

                flag = True

                next_token = ""
                current_time = datetime.now()
                from_date = (current_time-timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%S")
                to_date = current_time.strftime("%Y-%m-%dT%H:%M:%S")

                while(1):

                    report_request_list = ""

                    if(flag==True):
                        report_request_list = reports_api.get_report_request_list(from_date=from_date,to_date=to_date,report_types=["_GET_ORDERS_DATA_"])
                    else:
                        report_request_list = reports_api.get_report_request_list_by_next_token(token=next_token)

                    report_request_list = report_request_list.parsed

                    if("ReportRequestInfo" not in report_request_list):
                        break

                    report_request_list["ReportRequestInfo"] = convert_to_list(report_request_list["ReportRequestInfo"])

                    for report_request in report_request_list["ReportRequestInfo"]:

                        if(str(report_request["ReportProcessingStatus"]["value"]) != "_DONE_"):
                            continue
                        
                        report_id = str(report_request["GeneratedReportId"]["value"])
                        report = reports_api.get_report(report_id=report_id)
                        report = report.parsed

                        save_report_information(report,region)

                    if(report_request_list["HasNext"]["value"] == "true"):
                        next_token = report_request_list["NextToken"]["value"]
                        flag = False
                    else:
                        break

                getorder_information(orders_api)

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchOrdersPeriodicallyAPI: %s at %s",e, str(exc_tb.tb_lineno))

        return Response(data=response)

FetchOrdersPeriodically = FetchOrdersPeriodicallyAPI.as_view()

def save_report_information(report,region):

    report["Message"] = convert_to_list(report["Message"])

    global amazon_order_ids

    for message in report["Message"]:

        amazon_order_id = message["OrderReport"]["AmazonOrderID"]["value"]
        amazon_order_ids.append(amazon_order_id)
        amazon_order_date = message["OrderReport"]["OrderDate"]["value"]
        buyer_name = message["OrderReport"]["BillingData"]["BuyerName"]["value"]
        address_1 = message["OrderReport"]["FulfillmentData"]["Address"]["AddressFieldOne"]["value"]
        address_2 = message["OrderReport"]["FulfillmentData"]["Address"]["AddressFieldTwo"]["value"]                   
        city = message["OrderReport"]["FulfillmentData"]["Address"]["City"]["value"]
        country_code = message["OrderReport"]["FulfillmentData"]["Address"]["CountryCode"]["value"]

        channel_obj = ""

        if(region=="AE"):
            channel_obj = Channel.objects.get(name="Amazon UAE")
        elif(region=="UK"):
            channel_obj = Channel.objects.get(name="Amazon UK")

        amazon_order_obj = AmazonOrder.objects.create(

            amazon_order_id = amazon_order_id,
            order_date = amazon_order_date,
            buyer_name = buyer_name,
            address = str(address_1 + ", " + address_2),
            city = city,
            country_code = country_code,
            channel = channel_obj,
        )

        message["OrderReport"]["Item"] = convert_to_list(message["OrderReport"]["Item"])

        total_items = 0

        for item in message["OrderReport"]["Item"]:

            total_items += 1

            product_name = item["Title"]["value"]
            product_sku = item["SKU"]["value"]
            quantity = item["Quantity"]["value"]
            amazon_order_item_code = item["AmazonOrderItemCode"]["value"]

            amazon_item_obj = AmazonItem.objects.create(

                amazon_order = amazon_order_obj,
                amazon_order_item_code = amazon_order_item_code,
                sku = product_sku,
                name = product_name,
                quantity = quantity
            )

            item_price_json = json.loads(amazon_item_obj.item_price_json)
            item_amount = 0

            for components in item["ItemPrice"]["Component"]:

                component_value = components["Type"]["value"]
                component_amount = float(components["Amount"]["value"])

                item_price_json[component_value] = component_amount
                item_amount += component_amount

            amazon_item_obj.item_price_json = json.dumps(item_price_json)
            amazon_item_obj.amount = item_amount
            amazon_item_obj.save()

        amazon_order_obj.total_items = total_items
        amazon_order_obj.save()

def chunks(my_list, n):
    for i in range(0, len(my_list), n):
        yield my_list[i:i + n]

def getorder_information(orders_api):

    global amazon_order_ids

    for amazon_order_ids_chunk in chunks(amazon_order_ids,50):

        orders = orders_api.get_order(amazon_order_ids=amazon_order_ids_chunk)
        orders = orders.parsed

        orders["Orders"]["Order"] = convert_to_list(orders["Orders"]["Order"]) 

        for order in orders["Orders"]["Order"]:

            latest_ship_date = order["LatestShipDate"]["value"]
            number_of_items_shipped = order["NumberOfItemsShipped"]["value"]
            order_status = order["OrderStatus"]["value"]
            number_of_items_unshipped = order["NumberOfItemsUnshipped"]["value"]
            payment_method = order["PaymentMethodDetails"]["PaymentMethodDetail"]["value"]
            order_total = order["OrderTotal"]["Amount"]["value"]
            order_currency = order["OrderTotal"]["CurrencyCode"]["value"]
            shipment_service = order["ShipmentServiceLevelCategory"]["value"]
            earliest_ship_date = order["EarliestShipDate"]["value"]
            earliest_delivery_date = order["EarliestDeliveryDate"]["value"]


            amazon_order_obj = AmazonOrder.objects.get(amazon_order_id=str(order["AmazonOrderId"]["value"]))

            amazon_order_obj.latest_ship_date = latest_ship_date
            amazon_order_obj.earliest_ship_date = earliest_ship_date
            amazon_order_obj.earliest_delivery_date = earliest_delivery_date            

            amazon_order_obj.shipment_service = shipment_service

            amazon_order_obj.shipped_items = number_of_items_shipped 
            amazon_order_obj.unshipped_items = number_of_items_unshipped

            amazon_order_obj.order_status = order_status
            amazon_order_obj.payment_method = payment_method
            amazon_order_obj.amount = order_total
            amazon_order_obj.currency = order_currency

            amazon_order_obj.save()
