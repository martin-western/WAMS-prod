import pandas as pd
from WAMSApp.models import *
from dealshub.models import *
import urllib
from PIL import Image as IMAGE
import requests
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile

filename = "scripts/182 articles content missing list for vishal updated 14th june.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet3"]

rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])
dfs = dfs.fillna("")

brand_obj = Brand.objects.get(name="Royalford")

for i in range(rows):

    try:
        seller_sku = str(dfs.iloc[i,1])
        product_name = str(dfs.iloc[i,2])
        product_description = str(dfs.iloc[i,3])
        
        featurs_list = []

        for x in range(8):
            feature = str(dfs.iloc[i,4+x])
            if feature != "":
                featurs_list.append(feature)

        base_product , c = BaseProduct.objects.get_or_create(seller_sku=seller_sku)
        base_product.brand=brand_obj
        product , c = Product.objects.get_or_create(base_product=base_product)
        channel_product  = product.channel_product
        uk = json.loads(channel_product.amazon_uk_product_json)
        uae = json.loads(channel_product.amazon_uae_product_json)
        ebay = json.loads(channel_product.ebay_product_json)
        noon = json.loads(channel_product.noon_product_json)
        dh , c = DealsHubProduct.objects.get_or_create(product=product)

        print(product_name)
        if product_name != "":
            base_product.base_product_name = product_name
            product.product_name = product_name
            uk["product_name"] = product_name
            uae["product_name"] = product_name
            ebay["product_name"] = product_name
            noon["product_name"] = product_name
        
        if product_description != "":
            product.product_description = product_description
            channel_product.is_amazon_uk_product_created = True
            channel_product.is_amazon_uae_product_created = True
            channel_product.is_ebay_product_created = True
            channel_product.is_noon_product_created = True
            uk["product_description"] = product_description
            uae["product_description"] = product_description
            ebay["product_description"] = product_description
            noon["product_description"] = product_description
            
        if len(featurs_list) != 0:
            uk["product_attribute_list"] = featurs_list
            uae["product_attribute_list"] = featurs_list
            ebay["product_attribute_list"] = featurs_list
            noon["product_attribute_list"] = featurs_list
            attribute_list = json.dumps(featurs_list)
            product.pfl_product_features = attribute_list


        channel_product.amazon_uk_product_json = json.dumps(uk)
        channel_product.amazon_uae_product_json = json.dumps(uae)
        channel_product.ebay_product_json = json.dumps(ebay)
        channel_product.noon_product_json = json.dumps(noon)
        base_product.save()
        product.save()
        channel_product.save()

    except Exception as e:
        print(str(e))
        pass