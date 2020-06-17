from WAMSApp.models import *
import json
import pandas as pd
import xlsxwriter


path = "scripts/All_Listings_Report.xlsx"
dfs = pd.read_excel(path, sheet_name=None)["All Products Listed on Amazon"]
dfs = dfs.fillna('')    
rows = len(dfs.iloc[:])
cnt=0

# workbook = xlsxwriter.Workbook('./files/csv/amazon_listings_report.xlsx')
# worksheet = workbook.add_worksheet()
# rownum =0

# worksheet.write(rownum, 0,"Seller SKU")
# worksheet.write(rownum, 1,"ASIN")
# worksheet.write(rownum, 2,"Product Name")
# worksheet.write(rownum, 3,"Price")
# worksheet.write(rownum, 4,"Quantity")
# worksheet.write(rownum, 5,"Status on Amazon")
# worksheet.write(rownum, 6,"Matched/Not Matched")
# worksheet.write(rownum, 7,"SKU on OmnyComm")
# worksheet.write(rownum, 8,"Product Name on OmnyComm")

for i in range(rows):
    
    try:
        seller_sku = str(dfs.iloc[i][0]).strip()
        product_asin = str(dfs.iloc[i][1]).strip()
        product_name = str(dfs.iloc[i][2]).strip()
        price = str(dfs.iloc[i][5]).strip()
        quantity = str(dfs.iloc[i][6]).strip()
        status = str(dfs.iloc[i][16]).strip()

        # worksheet.write(rownum, 0,seller_sku)
        # worksheet.write(rownum, 1,product_asin)
        # worksheet.write(rownum, 2,product_name)
        # worksheet.write(rownum, 3,price)
        # worksheet.write(rownum, 4,quantity)
        # worksheet.write(rownum, 5,status)

        
        prod = Product.objects.get(base_product__seller_sku__icontains=seller_sku)
        channel_prod = prod.channel_product
        amazon_uae_product = json.loads(channel_prod.amazon_uae_product_json)
        if status=="Active":
            amazon_uae_product["status"] = "active"
        elif status=="Inactive" :
            amazon_uae_product["status"] = "listed"
        else:
            amazon_uae_product["status"] = "incomplete"

        amazon_uae_product["was_price"] = price
        amazon_uae_product["now_price"] = price
        amazon_uae_product["stock"] = quantity
        amazon_uae_product["ASIN"] = product_asin
        channel_prod.amazon_uae_product_json = json.dumps(amazon_uae_product)
        channel_prod.save()
        # worksheet.write(rownum, 6,"Matched")
        # worksheet.write(rownum, 7,prod.base_product.seller_sku)
        # worksheet.write(rownum, 8,prod.product_name)

        cnt+=1
        print("Cnt :",cnt)

    except Exception as e:
        # worksheet.write(rownum, 6,"Not Matched")
        pass

print("Cnt :",cnt)
# workbook.close()