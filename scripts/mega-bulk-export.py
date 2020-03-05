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
