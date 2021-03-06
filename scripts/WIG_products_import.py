import pandas as pd
from WAMSApp.models import *

filename = "scripts/wig-products.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet2"]
rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

cnt=0

for i in range(rows):
    try:
        category = dfs.iloc[i][0]
        sub_category = dfs.iloc[i][1]
        seller_sku = dfs.iloc[i][2]
        product_title = dfs.iloc[i][3]
        factory_code = dfs.iloc[i][3]
        product_length = dfs.iloc[i][5]
        product_width = dfs.iloc[i][6]
        product_height = dfs.iloc[i][7]
        product_dimension = dfs.iloc[i][8]
        giftbox_length = dfs.iloc[i][9]
        giftbox_width = dfs.iloc[i][10]
        giftbox_height = dfs.iloc[i][11]
        giftbox_dimension = dfs.iloc[i][12]
        carton_length = dfs.iloc[i][13]
        carton_width = dfs.iloc[i][14]
        carton_height = dfs.iloc[i][15]
        carton_dimension = dfs.iloc[i][16]
        carton_qty = dfs.iloc[i][17]
        giftbox_gross_weight = dfs.iloc[i][18]
        giftbox_net_weight = dfs.iloc[i][19]
        giftbox_weight_unit = dfs.iloc[i][20]
        giftbox_barcode = dfs.iloc[i][21]
        carton_gross_weight = dfs.iloc[i][22]
        carton_net_weight = dfs.iloc[i][23]
        carton_weight_unit = dfs.iloc[i][24]
        carton_barcode = dfs.iloc[i][25]
    
        brand_obj = Brand.objects.get(name="Geepas")

        
        base_product_obj = BaseProduct.objects.get(seller_sku=seller_sku)
        base_product_obj.base_product_name = product_title
        base_product_obj.brand=brand_obj
        base_product_obj.category=category
        base_product_obj.sub_category=sub_category
        base_product_obj.save()
        
        print("Cnt: ",cnt)
        cnt+=1

    except Exception as e:
        print(str(e))
        pass


from WAMSApp.models import *
from dealshub.models import *
prods = Product.objects.filter(base_product__brand__name="Geepas")
cnt=0
for prod in prods:
    try:
        category = prod.base_product.category
        category_obj , created = Category.objects.get_or_create(name=category)
        sub_category = prod.base_product.sub_category
        sub_category_obj , created = SubCategory.objects.get_or_create(name=sub_category, category=category_obj)
        DealsHubProduct.objects.create(product=prod, category=category_obj, sub_category=sub_category_obj, properties="{}")
        cnt +=1
        print("Cnt: ", cnt)
    except Exception as e:
        print(str(e))
        pass

from WAMSApp.models import *

channel_products = ChannelProduct.objects.all()
cnt=0
for channel_product in channel_products:
    try:
        amazon_uk_product = json.loads(channel_product.amazon_uk_product_json)
        amazon_uk_product["product_description"] = amazon_uk_product["product_description_amazon_uk"]
        channel_product.amazon_uk_product_json = json.dumps(amazon_uk_product) 
        channel_product.save()
        cnt+=1
        print("Cnt : ",cnt)
    except Exception as e:
        print(str(e))
        pass  

products = Product.objects.all()
cnt=0
for channel_product in products:
    try:
        amazon_uk_product = json.loads(channel_product.pfl_product_features)
        print(type(channel_product.pfl_product_features))
        print(amazon_uk_product)
        cnt+=1
        print("Cnt : ",cnt)
    except Exception as e:
        print(str(e))
        pass  
