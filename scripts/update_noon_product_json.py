import pandas as pd
from WAMSApp.models import *
from dealshub.models import *
import urllib
from PIL import Image as IMAGE
import requests
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import json
import math

def check_string(temp_string):

    if(temp_string=="" or temp_string=="NaN" or temp_string=="nan" or temp_string=="none"):
        return False

    return True


files = ["scripts/noon_json_upload_1.xlsx","scripts/noon_json_upload_2.xlsx"]

for filename in files:

    dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]

    rows = len(dfs.iloc[:])
    columns = len(dfs.iloc[0][:])
    dfs = dfs.fillna("")

    for i in range(rows):

        partner_sku = str(dfs.iloc[i,2])

        noon_sku = str(dfs.iloc[i,6])
        noon_reporting_category_1 = str(dfs.iloc[i,7])
        noon_reporting_category_2 = str(dfs.iloc[i,8])
        price = str(dfs.iloc[i,9])
        sale_price = str(dfs.iloc[i,10])
        sale_start_date = str(dfs.iloc[i,11])
        sale_end_date = str(dfs.iloc[i,12])
        warranty = str(dfs.iloc[i,14])
        stock_xdock_gross = str(dfs.iloc[i,16])
        noon_status = str(dfs.iloc[i,18])

        try:
            product = Product.objects.filter(base_product__seller_sku=partner_sku)

            if(product.count() !=1):
                continue

            product = product[0]

            channel_product = product.channel_product
            noon_product_json = json.loads(channel_product.noon_product_json)

            if(check_string(noon_sku)):
                noon_product_json["noon_sku"] = noon_sku

            if(check_string(noon_reporting_category_1)):
                noon_product_json["category"] = noon_reporting_category_1
            if(check_string(noon_reporting_category_2)):
                noon_product_json["sub_category"] = noon_reporting_category_2

            if(noon_status=="live"):
                noon_product_json["status"] = "Active"    
            else:
                 noon_product_json["status"] = "Listed"

            try:
                noon_product_json["now_price"] = float(sale_price)
            except Exception as e:
                pass

            try:
                noon_product_json["was_price"] = float(price)
            except Exception as e:
                print(price,str(e))
                pass

            try:
                noon_product_json["sale_price"] = float(sale_price)
            except Exception as e:
                print(sale_price,str(e))
                pass

            if(check_string(sale_start_date)):
                noon_product_json["sale_start"] = sale_start_date
            if(check_string(sale_end_date)):
                noon_product_json["sale_end"] = sale_end_date

            try:
                noon_product_json["stock"] = int(float(str(stock_xdock_gross)))
            except Exception as e:
                print(stock_xdock_gross,str(e))
                pass

            if(check_string(warranty)):
                noon_product_json["warranty"] = warranty

            channel_product.is_noon_product_created = True

            noon_product_json["product_name"] = product.product_name
            noon_product_json["product_description"] = product.product_description
            noon_product_json["product_attribute_list"] = json.loads(product.pfl_product_features)                   

            channel_product.noon_product_json = json.dumps(noon_product_json)
            channel_product.save()

        except Exception as e:
            print(e)
