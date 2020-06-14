import pandas as pd
from WAMSApp.models import *
from dealshub.models import *
import urllib
from PIL import Image as IMAGE
import requests
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile

filename = "scripts/Royalford_Data_Aswin.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet2"]
dfs.loc[:, 'Updated/Not Found'] = ""

rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])
dfs = dfs.fillna("")

cnt=0
brand_obj = Brand.objects.get(name="Royalford")

for i in range(rows):
    print(i)
    try:
        
        seller_sku = str(dfs.iloc[i,2])
        product_name = str(dfs.iloc[i,7])
        product_description = str(dfs.iloc[i,8])
        
        featurs_list = []

        for x in range(6):
            feature = str(dfs.iloc[i,9+x])
            if feature != "":
                featurs_list.append(feature)

        # print(featurs_list)
        # print(product_description)

        # if product_id != "":
        #     product_id = product_id.split(".")
        #     product_id = product_id[0] 
        #     product_id = str(int(product_id))
        
        # super_category = str(dfs.iloc[i,5])

        # if super_category == "Tools & Home Improvement":
        #     super_category= "Home Tools"

        # category = str(dfs.iloc[i,6])
        # sub_category = str(dfs.iloc[i,7])
        
        # pl = dfs.iloc[i,9]
        # if pl != "":
        #     pl = float(pl)

        # ph = dfs.iloc[i,10]
        # if ph != "":
        #     ph = float(ph)

        # pb = dfs.iloc[i,11]
        # if pb != "":
        #     pb = float(pb)

        # iw = dfs.iloc[i,12]
        # if iw != "":
        #     iw = float(iw)

        # gl = dfs.iloc[i,13]
        # if gl != "":
        #     gl = float(gl)

        # gh = dfs.iloc[i,14]
        # if gh != "":
        #     gh = float(gh)

        # gb = dfs.iloc[i,15]
        # if gb != "":
        #     gb = float(gb)

        # sw = dfs.iloc[i,16]
        # if sw != "":
        #     sw = float(sw)


        # featurs_list = featurs_list.split("•")[1:]
        # for f in range(len(featurs_list)):
        #     featurs_list[f] = featurs_list[f].replace("\n","").lstrip()
        
        # base_dimensions_json = {
        #     "export_carton_quantity_l": "",
        #     "export_carton_quantity_l_metric": "",
        #     "export_carton_quantity_b": "",
        #     "export_carton_quantity_b_metric": "",
        #     "export_carton_quantity_h": "",
        #     "export_carton_quantity_h_metric": "",
        #     "export_carton_crm_l": "",
        #     "export_carton_crm_l_metric": "",
        #     "export_carton_crm_b": "",
        #     "export_carton_crm_b_metric": "",
        #     "export_carton_crm_h": "",
        #     "export_carton_crm_h_metric": "",
        #     "product_dimension_l": pl,
        #     "product_dimension_l_metric": "cm",
        #     "product_dimension_b": pb,
        #     "product_dimension_b_metric": "cm",
        #     "product_dimension_h": ph,
        #     "product_dimension_h_metric": "cm",
        #     "giftbox_l": gl,
        #     "giftbox_l_metric": "cm",
        #     "giftbox_b": gb,
        #     "giftbox_b_metric": "cm",
        #     "giftbox_h": gh,
        #     "giftbox_h_metric": "cm"
        # }

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

        dfs.loc[i, 'Updated/Not Found'] = "Updated"
        cnt+=1
        print("Cnt : ",cnt)

    except Exception as e:
        print(str(e))
        dfs.loc[i, 'Updated/Not Found'] = "Not Found"
        pass

dfs.to_excel(filename,index=False)

# import pandas as pd
# from WAMSApp.models import *
# from dealshub.models import *
# import urllib
# from PIL import Image as IMAGE
# import requests
# from io import BytesIO
# from django.core.files.uploadedfile import InMemoryUploadedFile

# filename = "scripts/Krypton and Olsenmark.xlsx"
# filename1 = "scripts/mega-bulk-SANDEEP AND RAKESH 3 JUNE.xlsx"

# dfs_krypton = pd.read_excel(filename, sheet_name=None)["Krypton"]
# dfs_olsenmark = pd.read_excel(filename, sheet_name=None)["Olsenmark"]
# dfs_geepas = pd.read_excel(filename1, sheet_name=None)["Sheet1"]

# for sheet in range(3):

#     dfs = ""
#     brand_obj = ""

#     if(sheet == 0):
#         dfs = dfs_krypton
#         brand_obj = Brand.objects.get(name="Krypton")
#     elif(sheet == 1):
#         dfs = dfs_olsenmark
#         brand_obj = Brand.objects.get(name="Olsenmark")
#     else:
#         dfs = dfs_geepas
#         brand_obj = Brand.objects.get(name="Geepas")

#     rows = len(dfs.iloc[:])
#     columns = len(dfs.iloc[0][:])
#     dfs = dfs.fillna("")

#     for i in range(rows):

#         try:

#             seller_sku = str(dfs.iloc[i,5])
#             product_name = str(dfs.iloc[i,1])
#             product_description = str(dfs.iloc[i,9])

#             featurs_list = []

#             for x in range(5):
#                 feature = str(dfs.iloc[i,10+x])
#                 if feature != "":
#                     featurs_list.append(feature)

#             base_product , c = BaseProduct.objects.get_or_create(seller_sku=seller_sku)
#             base_product.brand=brand_obj
#             product , c = Product.objects.get_or_create(base_product=base_product)
#             channel_product  = product.channel_product
#             uk = json.loads(channel_product.amazon_uk_product_json)
#             uae = json.loads(channel_product.amazon_uae_product_json)
#             ebay = json.loads(channel_product.ebay_product_json)
#             noon = json.loads(channel_product.noon_product_json)
#             dh , c = DealsHubProduct.objects.get_or_create(product=product)

#             if product_name != "":
#                 base_product.base_product_name = product_name
#                 product.product_name = product_name
#                 uk["product_name"] = product_name
#                 uae["product_name"] = product_name
#                 ebay["product_name"] = product_name
#                 noon["product_name"] = product_name

#             if product_description != "":
#                 product.product_description = product_description
#                 channel_product.is_amazon_uk_product_created = True
#                 channel_product.is_amazon_uae_product_created = True
#                 channel_product.is_ebay_product_created = True
#                 channel_product.is_noon_product_created = True
#                 uk["product_description"] = product_description
#                 uae["product_description"] = product_description
#                 ebay["product_description"] = product_description
#                 noon["product_description"] = product_description

#             if len(featurs_list) != 0:
#                 uk["product_attribute_list"] = featurs_list
#                 uae["product_attribute_list"] = featurs_list
#                 ebay["product_attribute_list"] = featurs_list
#                 noon["product_attribute_list"] = featurs_list
#                 attribute_list = json.dumps(featurs_list)
#                 product.pfl_product_features = attribute_list


#             channel_product.amazon_uk_product_json = json.dumps(uk)
#             channel_product.amazon_uae_product_json = json.dumps(uae)
#             channel_product.ebay_product_json = json.dumps(ebay)
#             channel_product.noon_product_json = json.dumps(noon)
#             base_product.save()
#             product.save()
#             channel_product.save()

#         except Exception as e:
#             print(str(e))
#             pass