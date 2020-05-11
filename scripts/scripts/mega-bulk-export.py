from WAMSApp.models import *
import os
import json
import sys

import logging
import sys
import xlsxwriter

workbook = xlsxwriter.Workbook('./files/csv/mega-bulk-export.xlsx')
worksheet = workbook.add_worksheet()

#products = Product.objects.filter(base_product__brand__name="geepas")
products = Product.objects.filter(pk=15331)

cnt = 0
for product in products[:5]:
    try:
        common_row = ["" for i in range(210)]
        cnt += 1
        common_row[0] = str(cnt)
        common_row[1] = product.product_id
        common_row[2] = product.product_name
        common_row[3] = str(product.base_product.brand)
        common_row[4] = str(product.base_product.category)
        common_row[5] = str(product.base_product.sub_category)
        common_row[6] = str(product.base_product.seller_sku)
        common_row[7] = str(product.base_product.manufacturer)
        common_row[8] = str(product.base_product.manufacturer_part_number)
        common_row[9] = str(product.product_id_type)
        common_row[10] = str(product.product_description)
        product_features = json.loads(product.pfl_product_features)[:5]
        for i in range(len(product_features)):
            common_row[11+i] = product_features[i]
        common_row[16] = str(product.color)
        common_row[17] = str(product.color_map)
        common_row[18] = str(product.material_type)
        common_row[19] = "" if product.standard_price==None else str(product.standard_price)
        common_row[20] = "" if product.quantity==None else str(product.quantity)
        common_row[21] = str(product.barcode_string)
        dimensions = json.loads(product.base_product.dimensions)


        common_row[22] = str(dimensions["export_carton_quantity_l"])
        common_row[23] = str(dimensions["export_carton_quantity_l_metric"])
        common_row[24] = str(dimensions["export_carton_quantity_b"])
        common_row[25] = str(dimensions["export_carton_quantity_b_metric"])
        common_row[26] = str(dimensions["export_carton_quantity_h"])
        common_row[27] = str(dimensions["export_carton_quantity_h_metric"])
        common_row[28] = str(dimensions["export_carton_crm_l"])
        common_row[29] = str(dimensions["export_carton_crm_l_metric"])
        common_row[30] = str(dimensions["export_carton_crm_b"])
        common_row[31] = str(dimensions["export_carton_crm_b_metric"])
        common_row[32] = str(dimensions["export_carton_crm_h"])
        common_row[33] = str(dimensions["export_carton_crm_h_metric"])
        common_row[34] = str(dimensions["product_dimension_l"])
        common_row[35] = str(dimensions["product_dimension_l_metric"])
        common_row[36] = str(dimensions["product_dimension_b"])
        common_row[37] = str(dimensions["product_dimension_b_metric"])
        common_row[38] = str(dimensions["product_dimension_h"])
        common_row[39] = str(dimensions["product_dimension_h_metric"])
        common_row[40] = str(dimensions["giftbox_l"])
        common_row[41] = str(dimensions["giftbox_l_metric"])
        common_row[42] = str(dimensions["giftbox_b"])
        common_row[43] = str(dimensions["giftbox_b_metric"])
        common_row[44] = str(dimensions["giftbox_h"])
        common_row[45] = str(dimensions["giftbox_h_metric"])

        try:
            main_images = MainImages.objects.get(product=product, is_sourced=True)
            main_image = main_images.main_images.all()[0]
            common_row[46] = main_image.image.image.url
        except Exception as e:
            pass

        try:
            sub_images = SubImages.objects.get(product=product, is_sourced=True)
            sub_images = sub_images.sub_images.all()[:5]
            iterr = 0
            for sub_image in sub_images:
                common_row[47+iterr] = sub_image.image.image.url
                iterr += 1
        except Exception as e:
            pass

        try:
            iterr = 0
            for image in product.white_background_images.all()[:5]:
                common_row[52+iterr] = image.image.url
                iterr += 1
        except Exception as e:
            pass

        try:            
            iterr = 0
            for image in product.pfl_images.all()[:5]:
                common_row[57+iterr] = image.image.url
                iterr += 1
        except Exception as e:
            pass

        try:
            iterr = 0
            for image in product.lifestyle_images.all()[:5]:
                common_row[62+iterr] = image.image.url
                iterr += 1
        except Exception as e:
            pass

        try:
            iterr = 0
            for image in product.certificate_images.all()[:5]:
                common_row[67+iterr] = image.image.url
                iterr += 1
        except Exception as e:
            pass

        try:
            iterr = 0
            for image in product.giftbox_images.all()[:5]:
                common_row[72+iterr] = image.image.url
                iterr += 1
        except Exception as e:
            pass

        try:
            iterr = 0
            for image in product.diecut_images.all()[:5]:
                common_row[77+iterr] = image.image.url
                iterr += 1
        except Exception as e:
            pass

        try:
            iterr = 0
            for image in product.aplus_content_images.all()[:5]:
                common_row[82+iterr] = image.image.url
                iterr += 1
        except Exception as e:
            pass

        try:
            iterr = 0
            for image in product.ads_images.all()[:5]:
                common_row[87+iterr] = image.image.url
                iterr += 1
        except Exception as e:
            pass

        try:
            iterr = 0
            for image in product.base_product.unedited_images.all()[:5]:
                common_row[92+iterr] = image.image.url
                iterr += 1
        except Exception as e:
            pass

        try:
            iterr = 0
            for image in product.transparent_images.all()[:5]:
                common_row[97+iterr] = image.image.url
                iterr += 1
        except Exception as e:
            pass
        ############################################ Amazon UK
        amazon_uk_product_json = json.loads(product.channel_product.amazon_uk_product_json)
        common_row[102] = str(product.channel_product.is_amazon_uk_product_created)
        common_row[103] = str(amazon_uk_product_json["product_name"])
        common_row[104] = str(amazon_uk_product_json["product_description"])
        attributes = amazon_uk_product_json["product_attribute_list"][:5]
        for i in range(len(attributes)):
            common_row[105+i] = str(attributes[i])
        common_row[110] = str(amazon_uk_product_json["category"])
        common_row[111] = str(amazon_uk_product_json["sub_category"])
        common_row[112] = str(amazon_uk_product_json["parentage"])
        common_row[113] = str(amazon_uk_product_json["parent_sku"])
        common_row[114] = str(amazon_uk_product_json["relationship_type"])
        common_row[115] = str(amazon_uk_product_json["variation_theme"])
        common_row[116] = str(amazon_uk_product_json["feed_product_type"])
        common_row[117] = str(amazon_uk_product_json["update_delete"])
        common_row[118] = str(amazon_uk_product_json["recommended_browse_nodes"])
        common_row[119] = str(amazon_uk_product_json["search_terms"])
        common_row[120] = str(amazon_uk_product_json["enclosure_material"])
        common_row[121] = str(amazon_uk_product_json["cover_material_type"])
        special_features = amazon_uk_product_json["special_features"][:5]
        for i in range(len(special_features)):
            common_row[122+i] = str(special_features[i])        
        common_row[127] = str(amazon_uk_product_json["sale_price"])
        common_row[128] = str(amazon_uk_product_json["sale_from"])
        common_row[129] = str(amazon_uk_product_json["sale_end"])
        common_row[130] = str(amazon_uk_product_json["wattage"])
        common_row[131] = str(amazon_uk_product_json["wattage_metric"])
        common_row[132] = str(amazon_uk_product_json["item_count"])
        common_row[133] = str(amazon_uk_product_json["item_count_metric"])
        common_row[134] = str(amazon_uk_product_json["item_condition_note"])
        common_row[135] = str(amazon_uk_product_json["max_order_quantity"])
        common_row[136] = str(amazon_uk_product_json["number_of_items"])
        common_row[137] = str(amazon_uk_product_json["condition_type"])
        dimensions = amazon_uk_product_json["dimensions"]
        common_row[138] = dimensions["package_length"]
        common_row[139] = dimensions["package_length_metric"]
        common_row[140] = dimensions["package_width"]
        common_row[141] = dimensions["package_width_metric"]
        common_row[142] = dimensions["package_height"]
        common_row[143] = dimensions["package_height_metric"]
        common_row[144] = dimensions["package_weight"]
        common_row[145] = dimensions["package_weight_metric"]
        #common_row[146] = dimensions["package_quantity"]
        common_row[147] = dimensions["shipping_weight"]
        common_row[148] = dimensions["shipping_weight_metric"]
        common_row[149] = dimensions["item_display_weight"]
        common_row[150] = dimensions["item_display_weight_metric"]
        common_row[151] = dimensions["item_display_volume"]
        common_row[152] = dimensions["item_display_volume_metric"]
        common_row[153] = dimensions["item_display_length"]
        common_row[154] = dimensions["item_display_length_metric"]
        common_row[155] = dimensions["item_display_width"]
        common_row[156] = dimensions["item_display_width_metric"]
        common_row[157] = dimensions["item_display_height"]
        common_row[158] = dimensions["item_display_height_metric"]
        common_row[159] = dimensions["item_weight"]
        common_row[160] = dimensions["item_weight_metric"]
        common_row[161] = dimensions["item_length"]
        common_row[162] = dimensions["item_length_metric"]
        common_row[163] = dimensions["item_width"]
        common_row[164] = dimensions["item_width_metric"]
        common_row[165] = dimensions["item_height"]
        common_row[166] = dimensions["item_height_metric"]

        #common_row[167] = amazon_verified
        amazon_uae_product_json = json.loads(product.channel_product.amazon_uae_product_json)
        common_row[168] = str(product.channel_product.is_amazon_uae_product_created)
        common_row[169] = amazon_uae_product_json["product_name"]
        common_row[170] = amazon_uae_product_json["product_description"]
        attributes = amazon_uae_product_json["product_attribute_list"][:5]
        for i in range(len(attributes)):
            common_row[171+i] = attributes[i]
        common_row[176] = amazon_uae_product_json["category"]
        common_row[177] = amazon_uae_product_json["sub_category"]
        common_row[178] = amazon_uae_product_json["feed_product_type"]
        common_row[179] = amazon_uae_product_json["recommended_browse_nodes"]
        common_row[180] = amazon_uae_product_json["update_delete"]
        #common_row[181] = amazon_verified
        ebay_product_json = json.loads(product.channel_product.ebay_product_json)
        common_row[182] = str(product.channel_product.is_ebay_product_created)
        common_row[183] = ebay_product_json["product_name"]
        common_row[184] = ebay_product_json["product_description"]
        attributes = ebay_product_json["product_attribute_list"][:5]
        for i in range(len(attributes)):
            common_row[185+i] = attributes[i]
        common_row[190] = ebay_product_json["category"]
        common_row[191] = ebay_product_json["sub_category"]
        #common_row[192] = ebay_verified
        noon_product_json = json.loads(product.channel_product.noon_product_json)
        common_row[193] = str(product.channel_product.is_noon_product_created)
        common_row[194] = noon_product_json["product_name"]
        common_row[195] = noon_product_json["product_description"]
        common_row[196] = noon_product_json["product_type"]
        common_row[197] = noon_product_json["product_subtype"]
        common_row[198] = noon_product_json["parent_sku"]
        common_row[199] = noon_product_json["category"]
        #common_row[200] = noon_product_json["subtitle"]
        common_row[201] = noon_product_json["model_number"]
        common_row[202] = noon_product_json["model_name"]
        attributes = noon_product_json["product_attribute_list"][:5]
        for i in range(len(attributes)):
            common_row[203+i] = attributes[i]
        common_row[208] = noon_product_json["msrp_ae"]
        common_row[209] = noon_product_json["msrp_ae_unit"]
        #common_row[210] = noon_verified
        colnum = 0
        for k in common_row:
            worksheet.write(cnt, colnum, k)
            colnum += 1
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error ", e, str(exc_tb.tb_lineno))

workbook.close()