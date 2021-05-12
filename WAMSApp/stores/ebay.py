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


def export_ebay(products):
    success_products = 0
    try:
        try:
            os.system("rm ./files/csv/export-list-ebay.xlsx")
        except Exception as e:
            logger.warning("Delete old xlsx %s", str(e))

        workbook = xlsxwriter.Workbook('./files/csv/export-list-ebay.xlsx')
        worksheet = workbook.add_worksheet()

        cell_format = workbook.add_format({'bold': True})
        cell_format.set_pattern(1)
        cell_format.set_bg_color('gray')

        headers = ["*Action(SiteID=UK|Country=GB|Currency=GBP|Version=941)",
                   "*Category",
                   "*Title",
                   "Subtitle",
                   "*Description",
                   "*ConditionID",
                   "PicURL",
                   "*Quantity",
                   "*Format",
                   "*StartPrice",
                   "*Duration",
                   "*Location",
                   "StoreCategory",
                   "*C:Brand",
                   "*C:MPN",
                   "Product:EAN",
                   "CustomLabel",
                   "ShippingProfileName",
                   "ReturnProfileName",
                   "PaymentProfileName"]

        colnum = 0
        for key in headers:
            worksheet.write(0, colnum, key, cell_format)
            colnum += 1

        rownum = 1
        for product in products:
            base_product = product.base_product
            channel_product = product.channel_product
            ebay_product = json.loads(channel_product.ebay_product_json)
            
            try:
                common_row = ["" for i in range(len(headers))]
                common_row[0] = "Add"
                common_row[1] = ebay_product["category"]
                common_row[2] = ebay_product["product_name"]
                #common_row[3] = str(ebay_product["subtitle"])
                common_row[4] = ebay_product["product_description"]
                common_row[5] = "1000"
                
                common_row[7] = "" if product.quantity==None else str(product.quantity)
                common_row[8] = "FixedPrice"
                common_row[9] = "" if product.standard_price==None else str(product.standard_price)
                common_row[10] = "GTC"
                common_row[11] = "Birmingham"
                common_row[12] = ""
                common_row[13] = "" if base_product.brand==None else str(base_product.brand.name)
                common_row[14] = str(base_product.manufacturer_part_number)
                common_row[15] = str(product.product_id)
                common_row[16] = str(base_product.seller_sku)
                common_row[17] = "24 Hour Delivery Service"
                common_row[18] = "Western International - Returns 30 days"
                common_row[19] = "Western International - Paypal"

                # Graphics Part
                images_link = []

                if product.best_images.count()>0:
                    try:
                        best_images_objs = product.get_best_images()
                        for best_images_obj in best_images_objs:
                            images_link.append(str(best_images_obj.image.url))
                        pic_url = "|".join(images_link)
                        common_row[6] = pic_url
                    except Exception as e:
                        pass
                else:
                    try:
                        main_images_list = ImageBucket.objects.none()
                        main_images_obj = MainImages.objects.get(product = product, channel__name="Ebay")
                        main_images_list = main_images_obj.main_images.distinct()
                        for main_image in main_images_list:
                            images_link.append(str(main_image.image.image.url))

                        if SubImages.objects.filter(product = product, channel__name="Ebay").exists():
                            sub_images_obj = SubImages.objects.get(product = product, channel__name="Ebay")
                            sub_images_list = sub_images_obj.sub_images.distinct()
                            for sub_image in sub_images_list:
                                images_link.append(str(sub_image.image.image.url))
                    
                        pic_url = "|".join(images_link)
                        common_row[6] = pic_url
                    except Exception as e:
                        pass

                colnum = 0
                for row in common_row:
                    worksheet.write(rownum, colnum, row)
                    colnum += 1
                rownum += 1
                success_products += 1
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("Loop export_ebay: %s at %s | Product PK: %s", e, str(
                    exc_tb.tb_lineno), str(product.pk))
        workbook.close()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("export_ebay: %s at %s", e, str(exc_tb.tb_lineno))

    return success_products
