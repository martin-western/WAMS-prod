from WAMSApp.models import *
import csv
import urllib
import os
import json
from django.core.files import File
from WAMSApp.core_utils import *

import logging
import sys
import xlsxwriter
import pandas as pd

logger = logging.getLogger(__name__)

def export_noon(products):
    success_products = 0
    try:
        try:
            os.system("rm ./files/csv/export-list-noon.xlsx")
        except Exception as e:
            pass
            #logger.warning("Delete old xlsx %s", str(e))

        workbook = xlsxwriter.Workbook('./files/csv/export-list-noon.xlsx')
        worksheet = workbook.add_worksheet()

        # cell_format = workbook.add_format({'bold': True})
        # cell_format.set_pattern(1)
        # cell_format.set_bg_color('white')

        worksheet.write(0, 0, "14-Nov-2019")
        worksheet.write(1, 0, "Template Name")
        worksheet.write(1, 1, "hl_kitchen_dining")

        filename = "./WAMSApp/static/WAMSApp/xlsx/noon_template.xlsx"
        dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]

        for i in range(len(dfs.iloc[3][:])):
            worksheet.write(4, i, "" if str(dfs.iloc[3][i])=="nan" else str(dfs.iloc[3][i]))
            worksheet.write(5, i, "" if str(dfs.iloc[4][i])=="nan" else str(dfs.iloc[4][i]))
            worksheet.write(6, i, "" if str(dfs.iloc[5][i])=="nan" else str(dfs.iloc[5][i]))
            worksheet.write(7, i, "" if str(dfs.iloc[6][i])=="nan" else str(dfs.iloc[6][i]))

        rownum = 8
        for product in products:
            try:
                common_row = ["" for i in range(len(dfs.iloc[3][:]))]
                common_row[0] = "kitchen_dining"

                common_row[1] = str(product.noon_product_type)
                common_row[2] = str(product.noon_product_subtype)
                
                common_row[3] = str(product.product_id)
                common_row[4] = str(product.seller_sku)
                common_row[5] = str(product.parent_sku)
                common_row[6] = "" if product.brand==None else str(product.brand.name)
                common_row[7] = str(product.product_name_noon)
                common_row[8] = "china"
                common_row[9] = str(product.noon_model_number)
                common_row[10] = str(product.noon_model_name)
                common_row[11] = str(product.color)
                common_row[12] = str(product.color_map)
                common_row[13] = "" if product.item_length==None else str(product.item_length)
                common_row[14] = str(product.item_length_metric)

                common_row[26] = str(product.material_type)

                feature1 = ""
                feature2 = ""
                feature3 = ""

                try:
                    feature1 = json.loads(product.product_attribute_list_noon)[0]
                except Exception as e:
                    pass

                try:
                    feature2 = json.loads(product.product_attribute_list_noon)[1]
                except Exception as e:
                    pass

                try:
                    feature3 = json.loads(product.product_attribute_list_noon)[2]
                except Exception as e:
                    pass


                common_row[44] = feature1
                common_row[45] = feature2
                common_row[46] = feature3



                # Graphics Part
                main_image_url = ""
                if product.main_images.filter(is_main_image=True).count() > 0:
                    main_image_url = str(product.main_images.filter(is_main_image=True)[0].image.image.url)

                common_row[49] = main_image_url


                img_cnt = 0
                for image in product.main_images.filter(is_sub_image=True).order_by('sub_image_index')[:6]:
                    common_row[50+img_cnt] = str(image.image.image.url)
                    img_cnt += 1

                common_row[65] = "" if product.noon_msrp_ae==None else str(product.noon_msrp_ae)
                common_row[66] = str(product.noon_msrp_ae_unit)

                colnum = 0
                for row in common_row:
                    worksheet.write(rownum, colnum, row)
                    colnum += 1
                rownum += 1
                success_products += 1
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("Loop export_noon: %s at %s | Product PK: %s", e, str(
                    exc_tb.tb_lineno), str(product.pk))
        workbook.close()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("export_noon: %s at %s", e, str(exc_tb.tb_lineno))

    return success_products