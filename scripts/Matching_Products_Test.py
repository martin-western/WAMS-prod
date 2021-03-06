from MWS import APIs
import time
import pandas as pd
from WAMSApp.models import *
from WAMSApp.utils import *
import xlsxwriter

access_key = 'AKIAI7PSOABCBAJGX36Q' #replace with your access key
seller_id = 'A3DNFJ8JVFH39T' #replace with your seller id
secret_key = '9un2k+5Q4eCFI4SRDjNyLhjTAHXrsFkZe0mWIRop' #replace with your secret key
marketplace_ae = 'A2VIGQ35RCS4UG'

product_list = [941,944,946,949,950]

xml = generate_xml_for_post_product_data_amazon_uk(product_list,seller_id)

# feeds_api = APIs.Feeds(access_key, secret_key, seller_id, region='AE')

# filename = "scripts/final-barcode.xlsx"

# dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]
# rows = len(dfs.iloc[:])
# columns = len(dfs.iloc[0][:])

# workbook = xlsxwriter.Workbook('scripts/report_matching_products.xlsx')
# worksheet = workbook.add_worksheet()
# rownum =0

# worksheet.write(rownum, 0,"Barcode Value")
# worksheet.write(rownum, 1,"Barcode Type")
# worksheet.write(rownum, 2,"Seller SKU")
# worksheet.write(rownum, 3,"Product Name")
# worksheet.write(rownum, 4,"Status")
# worksheet.write(rownum, 5,"Matched ASIN")
# rownum +=1

# temp = "ASIN"
# flag=0
# id_list = []
# cnt=0
# i=0

# while i < rows: #len(rows):
#     print(i)
#     try:

#         barcode_string = dfs.iloc[i][0]
#         barcode_type = dfs.iloc[i][1]
#         seller_sku = dfs.iloc[i][2]
#         product_title = dfs.iloc[i][3]
        
#         id_list.append(barcode_string)
        
#         if temp != barcode_type:
#             flag=1
#             i-=1
#             id_list.pop()

#         # print(seller_sku_main)
#         # print("Barcode Type : ",barcode_type , "  Barcode String : ", barcode_string)
#         if flag!=1:
#             worksheet.write(rownum, 0,barcode_string)
#             worksheet.write(rownum, 1,barcode_type)
#             worksheet.write(rownum, 2,seller_sku)
#             worksheet.write(rownum, 3,product_title)
#             rownum += 1
        
#         if flag != 1:
#             if i%5 == 4:
#                 flag=1

#         if i == rows - 1:
#             flag=1

#         if flag==1 and len(id_list) !=0:
            
#             print(id_list)


#             products = products_api.get_matching_product_for_id(marketplace_id=marketplace_ae, type_=temp, ids = id_list)
#             # print(products.parsed)
#             for j in range(len(products.parsed)):
#                 status = products.parsed[j]["status"]["value"]
#                 matched_ASIN = ""
#                 if status == "Success":
#                     parsed_products = products.parsed[j]["Products"]["Product"]
                    
#                     if isinstance(parsed_products,list):
                       
#                         matched_ASIN = []
#                         for k in range(len(parsed_products)):
#                             matched_ASIN.append(parsed_products[k]["Identifiers"]["MarketplaceASIN"]["ASIN"]["value"])
#                     else:
#                         matched_ASIN = products.parsed[j]["Products"]["Product"]["Identifiers"]["MarketplaceASIN"]["ASIN"]["value"]
#                 else :
#                     status = "Ivalid Barcode Value"
                
#                 worksheet.write(rownum -5 + j, 4,status)
#                 if isinstance(matched_ASIN,list):
#                     for k in range(len(matched_ASIN)):
#                         worksheet.write(rownum -5 + j, 5 + k,matched_ASIN[k])
#                 else:
#                     worksheet.write(rownum -5 + j, 5,matched_ASIN)

#             id_list = []
#             flag = 0

#             cnt+=1
#             print("Cnt: ",cnt)

#             if(cnt%2==0):
#                 time.sleep(1)

#         temp = barcode_type
#         i+=1

#         if len(id_list)==0:
#             flag=0

#     except Exception as e:

#         worksheet.write(rownum, 0,barcode_string)
#         worksheet.write(rownum, 1,barcode_type)
#         worksheet.write(rownum, 2,seller_sku)
#         worksheet.write(rownum, 3,product_title)
#         worksheet.write(rownum, 4,"Unknown Error")
#         rownum+=1

#         print(str(e))

#         pass

# # products = products_api.get_matching_product_for_id(marketplace_id=marketplace_ae, type_=barcode_type, ids = id_list)

# # for i in range(len(products.parsed)):
# #   status = products.parsed[i]["status"]["value"]
# #   matched_ASIN = ""
# #   if status == "Success":
# #       matched_ASIN = products.parsed[i]["Products"]["Product"]["Identifiers"]["MarketplaceASIN"]["ASIN"]["value"]
# #   else :
# #       status = "Ivalid Value"
# #   print(status,matched_ASIN)

# workbook.close()


"""
{'FeedSubmissionInfo': {'FeedSubmissionId': {'value': '50086018372'}, 'FeedType': {'value': '_POST_PRODUCT_DATA_'}, 'SubmittedDate': {'value': '2020-04-20T11:37:43+00:00'}, 'FeedProcessingStatus': {'value': '_SUBMITTED_'}}}

{'value': '\n\t\t', 'MessageID': {'value': '1'}, 'ProcessingReport': {'value': '\n\t\t\t', 'DocumentTransactionID': {'value': '50086018372'}, 'StatusCode': {'value': 'Complete'}, 'ProcessingSummary': {'value': '\n\t\t\t\t', 'MessagesProcessed': {'value': '5'}, 'MessagesSuccessful': {'value': '4'}, 'MessagesWithError': {'value': '1'}, 'MessagesWithWarning': {'value': '0'}}, 'Result': {'value': '\n\t\t\t\t', 'MessageID': {'value': '941'}, 'ResultCode': {'value': 'Error'}, 'ResultMessageCode': {'value': '6039'}, 'ResultDescription': {'value': 'Merchant is not authorized to sell products under this restricted product group.'}, 'AdditionalInfo': {'value': '\n\t\t\t\t\t', 'SKU': {'value': 'GA1960'}}}}}

{'value': '\n\t\t', 'MessageID': {'value': '1'}, 'ProcessingReport': {'value': '\n\t\t\t', 'DocumentTransactionID': {'value': '50061018367'}, 'StatusCode': {'value': 'Complete'}, 'ProcessingSummary': {'value': '\n\t\t\t\t', 'MessagesProcessed': {'value': '5'}, 'MessagesSuccessful': {'value': '0'}, 'MessagesWithError': {'value': '5'}, 'MessagesWithWarning': {'value': '0'}}, 'Result': [{'value': '\n\t\t\t\t', 'MessageID': {'value': '941'}, 'ResultCode': {'value': 'Error'}, 'ResultMessageCode': {'value': '5000'}, 'ResultDescription': {'value': "XML Parsing Error at Line 22, Column 48: cvc-complex-type.2.4.a: Invalid content was found starting with element 'Condition'. One of '{DiscoveryData, ProductData, ShippedByFreight, EnhancedImageURL, Amazon-Vendor-Only, Amazon-Only, RegisteredParameter, NationalStockNumber, UnspscCode, UVPListPrice}' is expected."}, 'AdditionalInfo': {'value': '\n\t\t\t\t\t', 'SKU': {'value': 'GA1960'}}}, {'value': '\n\t\t\t\t', 'MessageID': {'value': '944'}, 'ResultCode': {'value': 'Error'}, 'ResultMessageCode': {'value': '5000'}, 'ResultDescription': {'value': "XML Parsing Error at Line 39, Column 48: cvc-complex-type.2.4.a: Invalid content was found starting with element 'Condition'. One of '{DiscoveryData, ProductData, ShippedByFreight, EnhancedImageURL, Amazon-Vendor-Only, Amazon-Only, RegisteredParameter, NationalStockNumber, UnspscCode, UVPListPrice}' is expected."}, 'AdditionalInfo': {'value': '\n\t\t\t\t\t', 'SKU': {'value': 'GA58018'}}}, {'value': '\n\t\t\t\t', 'MessageID': {'value': '946'}, 'ResultCode': {'value': 'Error'}, 'ResultMessageCode': {'value': '5000'}, 'ResultDescription': {'value': "XML Parsing Error at Line 56, Column 48: cvc-complex-type.2.4.a: Invalid content was found starting with element 'Condition'. One of '{DiscoveryData, ProductData, ShippedByFreight, EnhancedImageURL, Amazon-Vendor-Only, Amazon-Only, RegisteredParameter, NationalStockNumber, UnspscCode, UVPListPrice}' is expected."}, 'AdditionalInfo': {'value': '\n\t\t\t\t\t', 'SKU': {'value': 'GA58021'}}}, {'value': '\n\t\t\t\t', 'MessageID': {'value': '949'}, 'ResultCode': {'value': 'Error'}, 'ResultMessageCode': {'value': '5000'}, 'ResultDescription': {'value': "XML Parsing Error at Line 73, Column 48: cvc-complex-type.2.4.a: Invalid content was found starting with element 'Condition'. One of '{DiscoveryData, ProductData, ShippedByFreight, EnhancedImageURL, Amazon-Vendor-Only, Amazon-Only, RegisteredParameter, NationalStockNumber, UnspscCode, UVPListPrice}' is expected."}, 'AdditionalInfo': {'value': '\n\t\t\t\t\t', 'SKU': {'value': 'GAC9433'}}}, {'value': '\n\t\t\t\t', 'MessageID': {'value': '950'}, 'ResultCode': {'value': 'Error'}, 'ResultMessageCode': {'value': '5000'}, 'ResultDescription': {'value': "XML Parsing Error at Line 90, Column 48: cvc-complex-type.2.4.a: Invalid content was found starting with element 'Condition'. One of '{DiscoveryData, ProductData, ShippedByFreight, EnhancedImageURL, Amazon-Vendor-Only, Amazon-Only, RegisteredParameter, NationalStockNumber, UnspscCode, UVPListPrice}' is expected."}, 'AdditionalInfo': {'value': '\n\t\t\t\t\t', 'SKU': {'value': 'GAC9486'}}}]}}

"""