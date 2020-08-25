import pandas as pd
from WAMSApp.models import *
from dealshub.models import *
import urllib
from PIL import Image as IMAGE
import requests
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile

def check_string(temp_string):

    if(temp_string=="" or temp_string=="NaN" or temp_string=="nan" or temp_string=="none"):
        return False
    
    return True

filename = "scripts/SAP VS PARTNER SKU AS ON 12JUNE2020.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]

rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])
dfs = dfs.fillna("")

for i in range(rows):

    try:
        noon_sku = str(dfs.iloc[i,2])
        partner_sku = str(dfs.iloc[i,3])
        seller_sku = str(dfs.iloc[i,4])
        partner_barcode = str(dfs.iloc[i,8]).strip("'")
        psku_code = str(dfs.iloc[i,9])        

        sale_price = str(dfs.iloc[i,15])    
        sale_start_date = str(dfs.iloc[i,16])
        sale_end_date = str(dfs.iloc[i,17])
        is_active = str(dfs.iloc[i,18])

        stock = str(dfs.iloc[i,21])

        try:

            product = Product.objects.filter(base_product__seller_sku=seller_sku)[0]

            channel_product = product.channel_product

            noon_product_json = json.loads(channel_product.noon_product_json)

            if(check_string(partner_sku)):
                noon_product_json['partner_sku'] = partner_sku

            if(check_string(partner_barcode) and len(partner_barcode)==13):
                noon_product_json['partner_barcode'] = partner_barcode

            if(check_string(noon_sku)):
                noon_product_json['noon_sku'] = noon_sku

            if(check_string(psku_code)):
                noon_product_json['psku_code'] = psku_code                            

            try:
                noon_product_json['now_price'] = float(sale_price)
            except:
                pass

            try:
                noon_product_json['sale_price'] = float(sale_price)
            except:
                pass            

            if(check_string(sale_start_date)):
                noon_product_json['sale_start'] = sale_start_date

            if(check_string(sale_end_date)):
                noon_product_json['sale_end'] = sale_end_date

            try:
                if(int(float(is_active))==1):
                    noon_product_json['status'] = "Active"
                else:
                    noon_product_json['status'] = "Listed"
            except:
                noon_product_json['status'] = "Listed"

            try:
                noon_product_json['stock'] = int(float(stock))
            except:
                pass

            channel_product.noon_product_json = json.dumps(noon_product_json)

            channel_product.is_noon_product_created = True

            channel_product.save()

        except Exception as e:
            # print(str(e))
            pass
    except Exception as e:
            # print(str(e))
            pass
