import pandas as pd
from WAMSApp.models import *
from dealshub.models import *

filename = "scripts/Geepas_Data_Aswin.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]
dfs.loc[:, 'Updated/Not Found'] = ""

rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])
dfs = dfs.fillna("")

cnt=0
brand_obj = Brand.objects.get(name="Geepas")

for i in range(rows):
    print(i)
    try:
        
        seller_sku = str(dfs.iloc[i,0])
        product_name = str(dfs.iloc[i,2])
        product_description = str(dfs.iloc[i,3])
        product_id = str(int(dfs.iloc[i,4]))
        barcode_string = str(dfs.iloc[i,4])
        super_category = str(dfs.iloc[i,5])
        category = str(dfs.iloc[i,6])
        sub_category = str(dfs.iloc[i,7])
        
        pl = dfs.iloc[i,9]
        if pl != "":
            pl = float(pl)

        ph = dfs.iloc[i,10]
        if ph != "":
            ph = float(ph)

        pb = dfs.iloc[i,11]
        if pb != "":
            pb = float(pb)

        iw = dfs.iloc[i,12]
        if iw != "":
            iw = float(iw)

        gl = dfs.iloc[i,13]
        if gl != "":
            gl = float(gl)

        gh = dfs.iloc[i,14]
        if gh != "":
            gh = float(gh)

        gb = dfs.iloc[i,15]
        if gb != "":
            gb = float(gb)

        sw = dfs.iloc[i,16]
        if sw != "":
            sw = float(sw)

        featurs_list = []

        for x in range(24):
            feature = str(dfs.iloc[i,17+x])
            if feature != "":
                featurs_list.append(feature)
        
        base_dimensions_json = {
            "export_carton_quantity_l": "",
            "export_carton_quantity_l_metric": "",
            "export_carton_quantity_b": "",
            "export_carton_quantity_b_metric": "",
            "export_carton_quantity_h": "",
            "export_carton_quantity_h_metric": "",
            "export_carton_crm_l": "",
            "export_carton_crm_l_metric": "",
            "export_carton_crm_b": "",
            "export_carton_crm_b_metric": "",
            "export_carton_crm_h": "",
            "export_carton_crm_h_metric": "",
            "product_dimension_l": pl,
            "product_dimension_l_metric": "cm",
            "product_dimension_b": pb,
            "product_dimension_b_metric": "cm",
            "product_dimension_h": ph,
            "product_dimension_h_metric": "cm",
            "giftbox_l": gl,
            "giftbox_l_metric": "cm",
            "giftbox_b": gb,
            "giftbox_b_metric": "cm",
            "giftbox_h": gh,
            "giftbox_h_metric": "cm"
        }

        base_product , c = BaseProduct.objects.get_or_create(seller_sku=seller_sku)
        product , c = Product.objects.get_or_create(base_product=base_product)
        channel_product  = product.channel_product
        uk = json.loads(channel_product.amazon_uk_product_json)
        uae = json.loads(channel_product.amazon_uae_product_json)
        ebay = json.loads(channel_product.ebay_product_json)
        noon = json.loads(channel_product.noon_product_json)
        dh , c = DealsHubProduct.objects.get_or_create(product=product)

        if super_category != "":
            super_category , c = SuperCategory.objects.get_or_create(name=super_category)
        else:
            super_category = None

        if category != "":
            category , c = Category.objects.get_or_create(name=category)
            category.super_category=super_category
            category.save()
        else:
            category = None
        
        if sub_category != "":
            sub_category , c = SubCategory.objects.get_or_create(name=sub_category)
            sub_category.category=category
            sub_category.save()
        else:
            sub_category = None

        if category != None:
            base_product.category=category
            uk["category"] = category.name
            uae["category"] = category.name
            ebay["category"] = category.name
            noon["category"] = category.name

        if sub_category != None:
            base_product.sub_category=sub_category
            uk["sub_category"] = sub_category.name
            uae["sub_category"] = sub_category.name
            ebay["sub_category"] = sub_category.name
            noon["sub_category"] = sub_category.name

        if product_name != "":
            base_product.base_product_name = product_name
            product.product_name = product_name
            uk["product_name"] = product_name
            uae["product_name"] = product_name
            ebay["product_name"] = product_name
            noon["product_name"] = product_name
        
        if product_description != "":
            product.product_description = product_description
            uk["product_description"] = product_description
            uae["product_description"] = product_description
            ebay["product_description"] = product_description
            noon["product_description"] = product_description

        if product_id != "":
            product.product_id = product_id
            product.barcode_string = product_id
            
        if len(featurs_list) != 0:
            uk["product_attribute_list"] = featurs_list
            uae["product_attribute_list"] = featurs_list
            ebay["product_attribute_list"] = featurs_list
            noon["product_attribute_list"] = featurs_list
            attribute_list = json.dumps(featurs_list)
            product.pfl_product_features = attribute_list

        base_product.dimensions = json.dumps(base_dimensions_json)

        channel_product.amazon_uk_product_json = json.dumps(uk)
        channel_product.amazon_uae_product_json = json.dumps(uae)
        channel_product.ebay_product_json = json.dumps(ebay)
        channel_product.noon_product_json = json.dumps(noon)
        base_product.save()
        product.save()
        channel_product.save()

        dfs.loc[i, 'Updated/Not Found'] = "Updated"
        cnt+=1
    
    except Exception as e:
        print(str(e))
        dfs.loc[i, 'Updated/Not Found'] = "Not Found"
        pass


print(filename, "Cnt : ",cnt)

# dfs.to_excel(filename,index=False)