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
            base_product = product.base_product
            channel_product = product.channel_product
            noon_product = json.loads(channel_product.noon_product_json)
            
            try:
                common_row = ["" for i in range(len(dfs.iloc[3][:]))]
                common_row[0] = "kitchen_dining"

                common_row[1] = noon_product["product_type"]
                common_row[2] = noon_product["product_subtype"]
                
                common_row[3] = product.product_id
                common_row[4] = base_product.seller_sku
                # common_row[5] = noon_product["parent_sku"]
                common_row[6] = "" if base_product.brand==None else str(base_product.brand.name)
                common_row[7] = noon_product["product_name"]
                common_row[8] = "china"
                common_row[9] = noon_product["model_number"]
                common_row[10] = noon_product["model_name"]
                common_row[11] = str(product.color)
                common_row[12] = str(product.color_map)
                # dimensions = json.loads(base_product.dimensions)
                # common_row[13] = "" if base_product.item_length==None else str(base_product.item_length)
                # common_row[14] = str(base_product.item_length_metric)

                if product.material_type != None:
                    common_row[26] = str(product.material_type.name)

                feature1 = ""
                feature2 = ""
                feature3 = ""

                try:
                    feature1 = noon_product["product_attribute_list"][0]
                except Exception as e:
                    pass

                try:
                    feature2 = noon_product["product_attribute_list"][1]
                except Exception as e:
                    pass

                try:
                    feature3 = noon_product["product_attribute_list"][2]
                except Exception as e:
                    pass

                common_row[44] = feature1
                common_row[45] = feature2
                common_row[46] = feature3

                # Graphics Part
                main_image_url = None
                
                try:

                    main_images_list = ImageBucket.objects.none()
                    main_images_obj = MainImages.objects.get(product = product, channel__name="Noon")
                    
                    main_images_list |= main_images_obj.main_images.all()

                    main_images_list = main_images_list.distinct()
                    
                    main_image_url = main_images_list[0].image.image.url
                except Exception as e:
                    pass

                common_row[49] = main_image_url


                img_cnt = 0
                
                try:
                    sub_images_obj = SubImages.objects.get(product = product, channel__name="Noon")

                    sub_images_list = sub_images_obj.sub_images.distinct()

                    for sub_image in sub_images_list:
                        common_row[50+img_cnt] = str(sub_image.image.image.url)
                        img_cnt += 1
                        
                except Exception as e:
                    pass
                
                common_row[65] = "" if noon_product["msrp_ae"]==None else noon_product["msrp_ae"]
                common_row[66] =  noon_product["msrp_ae_unit"]

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