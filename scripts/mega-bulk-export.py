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

rownum = 0
colnum = 0
with open('./WAMSApp/static/WAMSApp/csv/amazon_uk.csv','rt')as f:
    data = csv.reader(f)
    for row in data:
        colnum = 0
        for rowdata in row:
            worksheet.write(rownum, colnum, rowdata, cell_format)
            colnum += 1
        rownum += 1

for product in products:
    try:
        base_product = product.base_product
        channel_product = product.channel_product
        amazon_uk_product = json.loads(channel_product.amazon_uk_product_json)

        common_row = ["" for i in range(213)]
        common_row[0] = base_product.seller_sku 