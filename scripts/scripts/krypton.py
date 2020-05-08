import csv
import json
from WAMSApp.models import *

fname = "scripts/KRYPTON.csv"

f = open(fname, "r")
data = csv.reader(f)

cnt = 0
for row in data:
    try:
    	cnt += 1
    	print("Cnt: ", cnt)
        seller_sku = row[0]
        manufacturer_part_number = row[1]
        brand_name = row[2]
        item_name = row[3]
        bullet_points = row[4]
        search_terms = row[6]

        bullet_points = filter(
            None, bullet_points.replace("\n", "").split("•"))
        product_attribute_list = []
        for bullet_point in bullet_points:
            product_attribute_list.append(bullet_point.strip())

        product_attribute_list_amazon_uk = json.dumps(product_attribute_list)
        product_attribute_list_amazon_uae = json.dumps(product_attribute_list)
        product_attribute_list_ebay = json.dumps(product_attribute_list)

        product_id = "KR_" + seller_sku

        

        brand_obj, created = Brand.objects.get_or_create(name="Krypton")

        Product.objects.create(product_id=product_id,
                               seller_sku=seller_sku,
                               manufacturer_part_number=manufacturer_part_number,
                               product_name_sap=item_name,
                               product_name_amazon_uk=item_name,
                               product_name_amazon_uae=item_name,
                               product_name_ebay=item_name,
                               brand=brand_obj,
                               search_terms=search_terms,
                               product_attribute_list_amazon_uk=product_attribute_list_amazon_uk,
                               product_attribute_list_amazon_uae=product_attribute_list_amazon_uae,
                               product_attribute_list_ebay=product_attribute_list_ebay)

    except Exception as e:
        print("Error ", str(e))


f.close()
