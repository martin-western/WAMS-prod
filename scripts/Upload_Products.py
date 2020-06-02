import pandas as pd
from WAMSApp.models import *
from dealshub.models import *

filename = "scripts/Products_Upload.xlsx"

dfs_list = []
dfs_list.append(pd.read_excel(filename, sheet_name=None)["ROYAL FORD"])
dfs_list.append(pd.read_excel(filename, sheet_name=None)["KRYPTON"])
dfs_list.append(pd.read_excel(filename, sheet_name=None)["OLSENMARK"])

brands = []

b = Brand.objects.get(name="Royalford")
brands.append(b)
b = Brand.objects.get(name="Krypton")
brands.append(b)
b = Brand.objects.get(name="Olsenmark")
brands.append(b)

index = -1
for dfs in dfs_list:  
    index+=1
    try:
        print("New")
        print()
        print()
        rows = len(dfs.iloc[:])
        columns = len(dfs.iloc[0][:])

        dfs.fillna("")
        cnt =0

        for i in range(rows):
            
            try:
                category = str(dfs.iloc[i,0])
                if category == 0 or category =='0':
                    category = ""

                sub_category = str(dfs.iloc[i,1])
                if sub_category == 0 or sub_category =='0':
                    sub_category = ""

                seller_sku = str(dfs.iloc[i,2])
                product_name = str(dfs.iloc[i,3])
                product_id = str(dfs.iloc[i,4])
                
                if category != "":
                    category , c = Category.objects.get_or_create(name=category)
                else:
                    category= None

                if sub_category != "":
                    sub_category , c = SubCategory.objects.get_or_create(name=sub_category,category=category)
                else:
                    sub_category= None

                base_product_obj ,c = BaseProduct.objects.get_or_create(seller_sku=seller_sku)
                product_obj ,c = Product.objects.get_or_create(base_product=base_product_obj,
                                                                product_id=product_id)

                dealshub_product , c= DealsHubProduct.objects.get_or_create(product=product_obj)
                base_product_obj.base_product_name=product_name
                base_product_obj.brand=brands[index]
                base_product_obj.category=category
                base_product_obj.sub_category=sub_category
                product_obj.product_name = product_name
                product_obj.barcode_string = product_id

                # base_product_obj.save()
                product_obj.save()
                cnt +=1
                print("Cnt :",cnt)

            except Exception as e:
                # print(category)
                # print(sub_category)
                # print(str(e))
                pass

    except Exception as e:
        print(str(e))
        pass