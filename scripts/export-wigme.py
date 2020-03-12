import urllib
import os
import json
import sys
import xlsxwriter
from WAMSApp.models import *

try:
    os.system("rm ./files/csv/export-wigme.xlsx")
except Exception as e:
    print("Error Delete old xlsx ", str(e))

workbook = xlsxwriter.Workbook('./files/csv/export-wigme.xlsx')
worksheet = workbook.add_worksheet()

row = ["Product Type",
       "Product Name (EN)",
       "Product Name (AR)",
       "Product Name (Tagalog)",
       "Product Model",
       "Wigme SKU",
       "Product Brand",
       "Brand Code",
       "Category",
       "Sub Category",
       "Third Level Category",
       "Product Description (EN)",
       "Product Description (AR)",
       "Product Description (Tagalog)",
       "Description Short (EN)",
       "Description Short (AR)",
       "Description Short (Tagalog)",
       "SEO Description",
       "SEO Keywords",
       "Local Keywords",
       "Sections",
       "Wigme Assured",
       "Quantity",
       "Shipping Charge",
       "Warranty In Months",
       "Buyer",
       "Supplier",
       "Active Status",
       "Price (AED)",
       "Special Price (AED)",
       "Cost (AED)",
       "Availability (AED)",
       "Delivery Time",
       "MOQ",
       "MOQ Price",
       "Customer Rating",
       "Discount",
       "Material",
       "Ideal For",
       "Pack Of",
       "Features",
       "Capacity",
       "Capacity Unit",
       "Launch Year",
       "Country Of Origin",
       "Size",
       "Size Unit",
       "Product Length (CM)",
       "Product Height (CM)",
       "Product Width/Depth (CM)",
       "Product Weight (KG)",
       "Shipping Length (CM)",
       "Shipping Height (CM)",
       "Shipping Width/Depth (CM)",
       "Shipping Weight (KG)",
       "Main Image Link",
       "Image 1",
       "Image 2",
       "Image 3",
       "Image 4",
       "Image 5"]

cnt = 0
colnum = 0
for k in row:
    worksheet.write(cnt, colnum, k)
    colnum += 1

products = Product.objects.filter(base_product__brand__name="krypton")

for product in products:
    try:
        cnt += 1
        base_product = product.base_product
        channel_product = product.channel_product
        amazon_uk_product = json.loads(channel_product.amazon_uk_product_json)
        common_row = ["" for i in range(61)]
        common_row[1] = product.product_name
        common_row[5] = base_product.seller_sku
        common_row[11] = product.product_description
        common_row[37] = "" if product.material_type==None else str(product.material_type.name)
        common_row[40] = "||".join(amazon_uk_product["product_attribute_list"])
        common_row[47] = "" if str(amazon_uk_product["dimensions"]["item_length"])=="None" else str(amazon_uk_product["dimensions"]["item_length"]) + " "+str(amazon_uk_product["dimensions"]["item_length_metric"])
        common_row[48] = "" if str(amazon_uk_product["dimensions"]["item_height"])=="None" else str(amazon_uk_product["dimensions"]["item_height"]) + " "+str(amazon_uk_product["dimensions"]["item_height_metric"])
        common_row[49] = "" if str(amazon_uk_product["dimensions"]["item_width"])=="None" else str(amazon_uk_product["dimensions"]["item_width"]) + " "+str(amazon_uk_product["dimensions"]["item_width_metric"])
        common_row[50] = "" if str(amazon_uk_product["dimensions"]["item_weight"])=="None" else str(amazon_uk_product["dimensions"]["item_weight"]) + " "+str(amazon_uk_product["dimensions"]["item_weight_metric"])
        common_row[51] = "" if str(amazon_uk_product["dimensions"]["package_length"])=="None" else str(amazon_uk_product["dimensions"]["package_length"]) + " "+str(amazon_uk_product["dimensions"]["package_length_metric"])
        common_row[52] = "" if str(amazon_uk_product["dimensions"]["package_height"])=="None" else str(amazon_uk_product["dimensions"]["package_height"]) + " "+str(amazon_uk_product["dimensions"]["package_height_metric"])
        common_row[53] = "" if str(amazon_uk_product["dimensions"]["package_width"])=="None" else str(amazon_uk_product["dimensions"]["package_width"]) + " "+str(amazon_uk_product["dimensions"]["package_width_metric"])
        common_row[54] = "" if str(amazon_uk_product["dimensions"]["shipping_weight"])=="None" else str(amazon_uk_product["dimensions"]["shipping_weight"]) + " "+str(amazon_uk_product["dimensions"]["shipping_weight_metric"])
        # Graphics Part
        try:
            main_image_url = None
            main_images_obj = MainImages.objects.get(product = product, is_sourced=True)
            if main_images_obj.main_images.filter(is_main_image=True).count() > 0:
                main_image_obj = main_images_obj.main_images.filter(is_main_image=True)[0]
                main_image_url = main_image_obj.image.image.url
                common_row[55] = str(main_image_url)
        except Exception as e:
            pass
        try:
            image_cnt = 0
            sub_images_obj = SubImages.objects.get(product = product, is_sourced=True)
            for img in sub_images_obj.sub_images.filter(is_sub_image=True).order_by('sub_image_index')[:5]:
                common_row[56+image_cnt] = "" if main_image_url==None else str(img.image.image.url)
                image_cnt += 1
        except Exception as e:
            pass
        colnum = 0
        for k in common_row:
            worksheet.write(cnt, colnum, k)
            colnum += 1
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Loop wigme export", e, str(exc_tb.tb_lineno), str(product.pk))

workbook.close()