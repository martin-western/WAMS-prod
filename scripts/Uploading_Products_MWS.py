from MWS import APIs
import time
import pandas as pd
from WAMSApp.models import *
import xlsxwriter

access_key = 'AKIAI7PSOABCBAJGX36Q' #replace with your access key
seller_id = 'A3DNFJ8JVFH39T' #replace with your seller id
secret_key = '9un2k+5Q4eCFI4SRDjNyLhjTAHXrsFkZe0mWIRop' #replace with your secret key
marketplace_ae = 'A2VIGQ35RCS4UG'

# products_api = APIs.Products(access_key, secret_key, seller_id, region='AE')

feeds_api = APIs.Feeds(access_key,secret_key,seller_id,region="AE")

feeds_response = feeds_api.get_matching_product_for_id(marketplace_id=marketplace_ae, type_=barcode_type, ids = id_list)

# for i in range(len(products.parsed)):
#   status = products.parsed[i]["status"]["value"]
#   matched_ASIN = ""
#   if status == "Success":
#       matched_ASIN = products.parsed[i]["Products"]["Product"]["Identifiers"]["MarketplaceASIN"]["ASIN"]["value"]
#   else :
#       status = "Ivalid Value"
#   print(status,matched_ASIN)

workbook.close()


