from WAMSApp.models import *

colors_list = ["black", "white", "red", "green", "yellow", "blue", "pink", "gray", "brown", "orange", "purple"]

brand_list = Brand.objects.all().values_list("name",flat=True)

temp = []

for brand in brand_list:
	temp.append(str(brand).lower())
	
brand_list = temp	

total_count = Product.objects.all().count()

product_brand = []
product_sku = []
product_brand_and_sku = []

for product in Product.objects.all():

	names_list = str(product.product_name).lower().replace("_"," ").replace(","," ").replace("-"," ").replace("|"," ").split()

	flag_brand = 0

	for name in names_list:

		if(name in brand_list):

			flag_brand = 1
			break

	seller_sku_list = str(product.base_product.seller_sku).lower().replace("_"," ").replace(","," ").replace("-"," ").replace("|"," ").split()

	flag_sku = 0

	for seller_sku in seller_sku_list:

		if(seller_sku in names_list and seller_sku not in colors_list):

			flag_sku = 1
			break

	if(flag_brand):
		product_brand.append(product)

	if(flag_sku):
		product_sku.append(product)

	if(flag_sku and flag_brand):
		product_brand_and_sku.append(product)

print("Total Products:",total_count)

print("Products having Brand:",len(product_brand))

print("Products having SKU:",len(product_sku))

print("Products having Brand & SKU:",len(product_brand_and_sku))






