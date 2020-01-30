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

logger = logging.getLogger(__name__)

def export_amazon_uk(products):
    success_products = 0
    try:

        try:
            os.system("rm ./files/csv/export-list-amazon-uk.xlsx")
        except Exception as e:
            logger.warning("Delete old xlsx %s", str(e))

        workbook = xlsxwriter.Workbook('./files/csv/export-list-amazon-uk.xlsx')
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
                    worksheet.write(rownum, colnum, rowdata.decode('utf-8'), cell_format)
                    colnum += 1
                rownum += 1
        
        for product in products:
            try:
                base_product = product.base_product
                channel_product = product.channel_product
                amazon_uk_product = json.loads(channel_product.amazon_uk_product_json)

                common_row = ["" for i in range(213)]
                common_row[0] = base_product.seller_sku
                common_row[1] = "" if base_product.brand==None else base_product.brand.name
                common_row[2] = product.product_id
                common_row[3] = product.product_id_type.name
                common_row[4] = amazon_uk_product["product_name"]
                common_row[5] = base_product.manufacturer
                common_row[6] = amazon_uk_product["recommended_browse_nodes"]
                common_row[7] = "" if product.standard_price==None else str(product.standard_price)
                common_row[8] = "" if product.quantity==None else str(product.quantity)

                common_row[19] = amazon_uk_product["parentage"]
                common_row[20] = amazon_uk_product["parent_sku"]
                common_row[21] = amazon_uk_product["relationship_type"]
                common_row[22] = amazon_uk_product["variation_theme"]
                common_row[23] = amazon_uk_product["update_delete"]
                
                common_row[25] = base_product.manufacturer_part_number
                common_row[26] = amazon_uk_product["product_description"]
                common_row[27] = amazon_uk_product["wattage_metric"]
                key_product_features = amazon_uk_product["product_attribute_list"]
                row_cnt = 0
                if len(key_product_features) > 0:
                    for key_product_feature in key_product_features[:5]:
                        common_row[31+row_cnt] = key_product_feature
                        row_cnt += 1

                common_row[36] = amazon_uk_product["search_terms"]
                common_row[44] = "" if amazon_uk_product["wattage"]==None else str(amazon_uk_product["wattage"])
                common_row[45] = "" if product.color==None else str(product.color)
                common_row[46] = "" if product.color_map==None else str(product.color_map)
                common_row[49] = "" if product.material_type==None else str(product.material_type.name)

                special_features = json.loads(product.special_features)
                row_cnt = 0
                if len(special_features) > 0:
                    for special_feature in special_features[:5]:
                        common_row[50+row_cnt] = special_feature
                        row_cnt += 1

                common_row[83] = base_product.item_width_metric
                common_row[84] = "" if base_product.item_width==None else str(base_product.item_width)
                common_row[85] = "" if base_product.item_height==None else str(base_product.item_height)
                common_row[88] = base_product.item_height_metric
                common_row[90] = base_product.item_length_metric
                common_row[91] = "" if base_product.item_length==None else str(base_product.item_length)
                common_row[95] = "" if base_product.shipping_weight==None else str(base_product.shipping_weight)
                common_row[96] = base_product.shipping_weight_metric
                common_row[97] = "" if base_product.item_display_length==None else str(base_product.item_display_length)
                common_row[98] = base_product.item_display_length_metric
                common_row[99] = "" if base_product.item_display_width==None else str(base_product.item_display_width) 
                common_row[100] = base_product.item_display_width_metric
                common_row[101] = "" if base_product.item_display_height==None else str(base_product.item_display_height)
                common_row[102] = base_product.item_display_height_metric
                common_row[105] = "" if base_product.item_display_weight==None else str(base_product.item_display_weight)
                common_row[106] = base_product.item_display_weight_metric
                common_row[109] = "" if base_product.item_display_volume==None else str(base_product.item_display_volume)
                common_row[110] = base_product.item_display_volume_metric
                common_row[116] = base_product.package_weight_metric
                common_row[117] = base_product.package_height_metric
                common_row[118] = "" if base_product.package_weight==None else str(base_product.package_weight)
                common_row[119] = "" if base_product.package_length==None else str(base_product.package_length)
                common_row[120] = "" if base_product.package_width==None else str(base_product.package_width)
                common_row[121] = "" if base_product.package_height==None else str(base_product.package_height)

                common_row[164] = "" if base_product.item_weight==None else str(base_product.item_weight)
                common_row[165] = base_product.item_weight_metric
                common_row[186] = "" if amazon_uk_product["sale_price"]==None else str(amazon_uk_product["sale_price"])
                common_row[187] = str(amazon_uk_product["sale_from"])
                common_row[188] = str(amazon_uk_product["sale_end"])
                common_row[189] = amazon_uk_product["condition_type"]



                # Graphics Part
                main_image_url = None
                main_images_obj = MainImages.objects.get(product = product, channel="Amazon UK")
                
                if main_images_obj.main_images.filter(is_main_image=True).count() > 0:
                    main_image_obj = main_images_obj.main_images.filter(is_main_image=True)[0]
                    main_image_url = main_image_obj.image.image.url
        
                common_row[9] = str(main_image_url)
                
                image_cnt = 10
                sub_images_objs = SubImages.objects.filter(product = product, is_sourced=True)
                
                for sub_images_obj in sub_images_objs:
                    if sub_images_obj.sub_images.filter(is_sub_image=True).count() > 0:
                        for img in sub_images_obj.sub_images.filter(is_sub_image=True).order_by('sub_image_index')[:8]:
                            common_row[image_cnt] = str(img.image.image.url)
                            image_cnt += 1

                data_row_2 = []
                for k in common_row:
                    if k==None:
                        data_row_2.append("")
                    elif isinstance(k, int)==False:
                        l = k.encode('utf-8').strip()
                        data_row_2.append(l)
                    else:
                        data_row_2.append(k)

                colnum = 0
                for k in data_row_2:
                    worksheet.write(rownum, colnum, k.encode("ascii", "ignore"))
                    colnum += 1
                rownum += 1
                success_products += 1
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("Loop export_amazon_uk: %s at %s | Product PK: %s", e, str(exc_tb.tb_lineno), str(product.pk))
        workbook.close()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("export_amazon_uk: %s at %s", e, str(exc_tb.tb_lineno))

    return success_products


