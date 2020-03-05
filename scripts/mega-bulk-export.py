from WAMSApp.models import *
import os
import json

import logging
import sys
import xlsxwriter

workbook = xlsxwriter.Workbook('./files/csv/mega-bulk-export.xlsx')
worksheet = workbook.add_worksheet()

cell_format = workbook.add_format({'bold': True})
cell_format.set_pattern(1)
cell_format.set_bg_color('yellow')

products = Product.objects.filter(base_product__organization__name="geepas")

cnt = 0
for product in products:
    try:
        common_row = ["" for i in range(176)]
        cnt += 1
        common_row[0] = cnt
        common_row[1] = product.product_id
        common_row[2] = product.product_name
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.category)
        common_row[3] = str(product.base_product.sub_category)
        common_row[3] = str(product.base_product.seller_sku)
        common_row[3] = str(product.base_product.manufacturer)
        common_row[3] = str(product.base_product.manufacturer_part_number)
        common_row[3] = str(product.product_id_type)
        common_row[3] = str(product.product_description)

        product_features = json.loads(product.pfl_product_features)[:5]
        for i in range(product_features):
        	common_row[3+i] = product_features[i]

        common_row[3] = str(product.color)
        common_row[3] = str(product.color_map)
        common_row[3] = str(product.material_type)
        common_row[3] = str(product.standard_price)
        common_row[3] = str(product.quantity)
        common_row[3] = str(product.barcode_string)

        dimensions = json.loads(product.base_product.dimensions)

        common_row[3] = str(dimensions["export_carton_quantity_l"])
        common_row[3] = str(dimensions["export_carton_quantity_l_metric"])
        common_row[3] = str(dimensions["export_carton_quantity_b"])
        common_row[3] = str(dimensions["export_carton_quantity_b_metric"])
        common_row[3] = str(dimensions["export_carton_quantity_h"])
        common_row[3] = str(dimensions["export_carton_quantity_h_metric"])
        common_row[3] = str(dimensions["export_carton_crm_l"])
        common_row[3] = str(dimensions["export_carton_crm_l_metric"])
        common_row[3] = str(dimensions["export_carton_crm_b"])
        common_row[3] = str(dimensions["export_carton_crm_b_metric"])
        common_row[3] = str(dimensions["export_carton_crm_h_metric"])
        common_row[3] = str(dimensions["product_dimension_h"])
        common_row[3] = str(dimensions["product_dimension_h_metric"])
        common_row[3] = str(dimensions["giftbox_l"])
        common_row[3] = str(dimensions["giftbox_l_metric"])
        common_row[3] = str(dimensions["giftbox_b"])
        common_row[3] = str(dimensions["giftbox_b_metric"])
        common_row[3] = str(dimensions["giftbox_h"])
        common_row[3] = str(dimensions["giftbox_h_metric"])

        main_images = MainImages.objects.get(product=product, is_sourced=True)
        main_image = main_images.main_images.all()[0]
        common_row[] = main_image.image.image.url

		sub_images = SubImages.objects.get(product=product, is_sourced=True)
        sub_images = sub_images.sub_images.all()[:5]
        for sub_image in sub_images:
			common_row[] = sub_image.image.image.url

		for image in product.white_background_images.all()[:5]:
			common_row[] = image.image.url

		for image in product.pfl_images.all()[:5]:
			common_row[] = image.image.url

		for image in product.lifestyle_images.all()[:5]:
			common_row[] = image.image.url

		for image in product.certificate_images.all()[:5]:
			common_row[] = image.image.url

		for image in product.giftbox_images.all()[:5]:
			common_row[] = image.image.url

		for image in product.diecut_images.all()[:5]:
			common_row[] = image.image.url




        common_row[3] = str(product.)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
        common_row[3] = str(product.base_product.brand)
