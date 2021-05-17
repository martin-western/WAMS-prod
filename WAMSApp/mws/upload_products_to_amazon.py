from WAMSApp.models import *
from WAMSApp.utils import *
from WAMSApp.mws.xml_generators_uae import *

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

import requests
import json
import pytz
import csv
import logging
import sys
import xlrd
import time
import re

from datetime import datetime
from django.utils import timezone
from django.core.files import File

logger = logging.getLogger(__name__)

MWS_PARAMS = settings.MWS_PARAMS

MWS_ACCESS_KEY = MWS_PARAMS["MWS_ACCESS_KEY"] 
MWS_SECRET_KEY = MWS_PARAMS["MWS_SECRET_KEY"]
SELLER_ID = MWS_PARAMS["SELLER_ID"]

marketplace_id = mws.Marketplaces["AE"].marketplace_id

filename = "scripts/Upload_List.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]
dfs = dfs.fillna("")
dfs.loc[:, 'Status'] = ""
rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])
cnt=0

# product_pk_list = []

# for i in range(rows):
#     try:
#         seller_sku = dfs.iloc[i][0]
#         product_obj = Product.objects.filter(base_product__seller_sku=seller_sku)[0]
#         product_pk = product_obj.pk
#         product_pk_list.append(product_pk)
#     except Exception as e:
#         pass


# def generate_xml_for_post_product_data_amazon_uae1(product_pk_list,seller_id):
#     try:
#          # Check if Cached
#         from WAMSApp.models import Product
#         import json
#         xml_string = """<?xml version="1.0"?>
#                         <AmazonEnvelope xsi:noNamespaceSchemaLocation="amzn-envelope.xsd"
#                             xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
#                             <Header>
#                                 <DocumentVersion>1.01</DocumentVersion>
#                                 <MerchantIdentifier>"""+seller_id+"""</MerchantIdentifier>
#                             </Header>
#                             <MessageType>Product</MessageType>
#                             <PurgeAndReplace>false</PurgeAndReplace>"""
#         for product_pk in product_pk_list:
#             product_obj = Product.objects.get(pk=int(product_pk))
#             message_id = str(product_pk)
#             product_name = product_obj.product_name
#             if product_name == "":
#                 product_name = product_obj.base_product.product_name
#             seller_sku = product_obj.base_product.seller_sku
#             description = product_obj.product_description
#             brand_name = ""
#             product_id_type = ""
#             product_id = ""
#             try:
#                 brand_name = product_obj.base_product.brand.name
#             except Exception as e:
#                 brand_name = ""
#             try:
#                 product_id_type = product_obj.product_id_type.name
#             except Exception as e:
#                 product_id_type = "EAN"
#             try:
#                 product_id = str(product_obj.product_id)
#             except Exception as e:
#                 product_id = ""
#             amazon_uae_product = json.loads(product_obj.channel_product.amazon_uae_product_json)
#             category = product_obj.base_product.category.name
#             category = category.replace(" ","")
#             category = category.replace(" ","")
#             super_category = "Home"
#             sub_category = amazon_uae_product["sub_category"]
#             if(amazon_uae_product["recommended_browse_nodes"] != ""):
#                 amazon_uae_product["recommended_browse_nodes"] = get_recommended_browse_node(seller_sku,"Amazon UAE")
#             product_obj.channel_product.amazon_uae_product_json = json.dumps(amazon_uae_product)
#             product_obj.channel_product.save()
#             xml_string += """<Message>
#                                 <MessageID>"""+ message_id +"""</MessageID>
#                                 <OperationType>Update</OperationType> 
#                                 <Product>
#                                     <SKU>"""+ seller_sku +"""</SKU>
#                                     <StandardProductID>
#                                         <Type>"""+product_id_type+"""</Type>
#                                         <Value>"""+product_id +"""</Value>
#                                     </StandardProductID>
#                                     <Condition>
#                                         <ConditionType>New</ConditionType>
#                                         <ConditionNote></ConditionNote>
#                                     </Condition>
#                                     <DescriptionData>
#                                         <Title>"""+ product_name + """</Title>
#                                         <Brand>""" + brand_name +"""</Brand>
#                                         <Manufacturer>""" + brand_name +"""</Manufacturer>"""
#             if(amazon_uae_product["recommended_browse_nodes"] != ""):
#                 xml_string += """<RecommendedBrowseNode>"""+amazon_uae_product["recommended_browse_nodes"]+"""</RecommendedBrowseNode>"""
#             xml_string += """</DescriptionData>"""
#             # if(super_category != "" and category != ""):
#             #     xml_string += """<ProductData>
#             #                 <""" +super_category+""">
#             #                     <ProductType>
#             #                         <"""+category+""">
#             #                         </"""+category+""">
#             #                     </ProductType>
#             #                 </""" +super_category+""">
#             #                 </ProductData>"""

#             xml_string += """</Product>
#                             </Message> """

#         xml_string += """</AmazonEnvelope>"""
#         xml_string = xml_string.replace("&","and")
        
#         xml_string = xml_string.encode('utf-8')
#         # print(xml_string)
#         return xml_string

#     except Exception as e:
#         print(str(e))
#         exc_type, exc_obj, exc_tb = sys.exc_info()
#         print("Generating XML for Post Product Data UAE: %s at %s", e, str(exc_tb.tb_lineno))
#         return ""

feed_submission_id = 63270018492

feeds_api = APIs.Feeds(MWS_ACCESS_KEY,MWS_SECRET_KEY,SELLER_ID, 
                            region='AE')

response_feed_submission_result = feeds_api.get_feed_submission_result(feed_submission_id)

feed_submission_result = response_feed_submission_result.parsed

result = feed_submission_result["ProcessingReport"]["Result"]

temp_dict = {}

for i in range(len(result)):
    pk = result[i]["MessageID"]["value"]
    temp_dict[pk] = "1"
    
print(temp_dict)
product_pk_list = []

for i in range(rows):
    try:
        seller_sku = dfs.iloc[i][0]
        product_obj = Product.objects.filter(base_product__seller_sku=seller_sku)[0]
        product_pk = product_obj.pk
        
        try :
            if temp_dict[str(product_pk)] == "1":
                dfs.iloc[i,1] = "Not Uploaded"
            else:
                dfs.iloc[i,1] = "Uploaded"
        except Exception as e:
            dfs.iloc[i,1] = "Uploaded"

    except Exception as e:
        print(e)
        dfs.iloc[i,1] = "Not Found"
        pass

dfs.to_excel(filename,index=False)

# xml_string = generate_xml_for_post_product_data_amazon_uae1(product_pk_list,SELLER_ID)

# xml = xml_string.decode('utf-8').replace("\n","")
# xml = xml.replace("  ","")
# xml = xml.replace("  ","")
# xml = xml.replace("  ","")
# print(xml)


# # response_submeet_feed = feeds_api.submit_feed(xml_string,"_POST_PRODUCT_DATA_",marketplaceids=marketplace_id)

# # feed_submission_id = response_submeet_feed.parsed["FeedSubmissionInfo"]["FeedSubmissionId"]["value"]

# # print(feed_submission_id)

# xml_string = generate_xml_for_product_image_amazon_uae(product_pk_list,SELLER_ID)

# response_submeet_feed = feeds_api.submit_feed(xml_string,"_POST_PRODUCT_IMAGE_DATA_",marketplaceids=marketplace_id)

# feed_submission_id = response_submeet_feed.parsed["FeedSubmissionInfo"]["FeedSubmissionId"]["value"]

# print(feed_submission_id)



# xml_string = """
# <Description></Description>
# <BulletPoint></BulletPoint>
# <BulletPoint></BulletPoint>
# <BulletPoint></BulletPoint>
# <BulletPoint></BulletPoint>
# <BulletPoint></BulletPoint>
# <ItemDimensions>
# <Weight unitOfMeasure="KG">0.27</Weight>
# </ItemDimensions>
# <PackageWeight unitOfMeasure="KG">0.27</PackageWeight>
# <ShippingWeight unitOfMeasure="KG">0.27</ShippingWeight>
# <Manufacturer>Geepas</Manufacturer>
# <MfrPartNumber></MfrPartNumber>
# <ItemType></ItemType>
# <RecommendedBrowseNode></RecommendedBrowseNode>
# <MerchantShippingGroupName/>
# <Battery>
# <AreBatteriesRequired>false</AreBatteriesRequired>
# </Battery>
# <SupplierDeclaredDGHZRegulation>not_applicable</SupplierDeclaredDGHZRegulation>
# </DescriptionData>
# """

