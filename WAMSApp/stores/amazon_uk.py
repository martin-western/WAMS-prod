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
                common_row[1] = "" if base_product.brand==None else base_product.brand.name
                common_row[2] = product.product_id
                common_row[3] = str(product.product_id_type)
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

                
                try:
                    special_features = json.loads(amazon_uk_product["special_features"])
                except Exception as e:
                    special_features = amazon_uk_product["special_features"]
                logger.info("special_features: %s", str(special_features))
                row_cnt = 0
                if len(special_features) > 0:
                    for special_feature in special_features[:5]:
                        logger.info("special_features iter %s", special_feature)
                        common_row[50+row_cnt] = special_feature
                        row_cnt += 1
                
                
                common_row[83] = amazon_uk_product["dimensions"]["item_width_metric"]
                common_row[84] = amazon_uk_product["dimensions"]["item_width"]
                common_row[85] = amazon_uk_product["dimensions"]["item_height"]
                common_row[88] = amazon_uk_product["dimensions"]["item_height_metric"]
                common_row[90] = amazon_uk_product["dimensions"]["item_length_metric"]
                common_row[91] = amazon_uk_product["dimensions"]["item_length"]
                common_row[95] = amazon_uk_product["dimensions"]["shipping_weight"]
                common_row[96] = amazon_uk_product["dimensions"]["shipping_weight_metric"]
                common_row[97] = amazon_uk_product["dimensions"]["item_display_length"]
                common_row[98] = amazon_uk_product["dimensions"]["item_display_length_metric"]
                common_row[99] = amazon_uk_product["dimensions"]["item_display_width"] 
                common_row[100] = amazon_uk_product["dimensions"]["item_display_width_metric"]
                common_row[101] = amazon_uk_product["dimensions"]["item_display_height"]
                common_row[102] = amazon_uk_product["dimensions"]["item_display_height_metric"]
                common_row[105] = amazon_uk_product["dimensions"]["item_display_weight"]
                common_row[106] = amazon_uk_product["dimensions"]["item_display_weight_metric"]
                common_row[109] = amazon_uk_product["dimensions"]["item_display_volume"]
                common_row[110] = amazon_uk_product["dimensions"]["item_display_volume_metric"]
                common_row[116] = amazon_uk_product["dimensions"]["package_weight_metric"]
                common_row[117] = amazon_uk_product["dimensions"]["package_height_metric"]
                common_row[118] = amazon_uk_product["dimensions"]["package_weight"]
                common_row[119] = amazon_uk_product["dimensions"]["package_length"]
                common_row[120] = amazon_uk_product["dimensions"]["package_width"]
                common_row[121] = amazon_uk_product["dimensions"]["package_height"]

                common_row[164] = amazon_uk_product["dimensions"]["item_weight"]
                common_row[165] = amazon_uk_product["dimensions"]["item_weight_metric"]
                common_row[186] = "" if amazon_uk_product["sale_price"]==None else str(amazon_uk_product["sale_price"])
                common_row[187] = str(amazon_uk_product["sale_from"])
                common_row[188] = str(amazon_uk_product["sale_end"])
                common_row[189] = amazon_uk_product["condition_type"]
                
                
                # Graphics Part
                try:
                    main_image_url = None
                    main_images_obj = MainImages.objects.get(product = product, channel__name="Amazon UK")
                
                    if main_images_obj.main_images.filter(is_main_image=True).count() > 0:
                        main_image_obj = main_images_obj.main_images.filter(is_main_image=True)[0]
                        main_image_url = main_image_obj.image.image.url
        
                    common_row[9] = str(main_image_url)
                except Exception as e:
                    pass

                try:
                    image_cnt = 10
                    sub_images_objs = SubImages.objects.filter(product = product, channel__name="Amazon UK")

                    for sub_images_obj in sub_images_objs:
                        if sub_images_obj.sub_images.filter(is_sub_image=True).count() > 0:
                            for img in sub_images_obj.sub_images.filter(is_sub_image=True).order_by('sub_image_index')[:8]:
                                common_row[image_cnt] = str(img.image.image.url)
                                image_cnt += 1
                except Exception as e:
                    pass

                data_row_2 = []
                for k in common_row:
                    if k==None:
                        data_row_2.append("")
                    elif isinstance(k, int)==False:
                        l = k
                        data_row_2.append(l)
                    else:
                        data_row_2.append(k)

                colnum = 0
                for k in data_row_2:
                    worksheet.write(rownum, colnum, k)
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


def update_product_full_amazon_uk(product_obj, row):
    
    base_product = product_obj.base_product
    channel_product = product_obj.channel_product
    amazon_uk_product = json.loads(channel_product.amazon_uk_product_json)

    amazon_uk_product["feed_product_type"] = row[0]
    base_product.seller_sku = row[1]
    
    if row[2]!="":
        brand_obj = Brand.objects.create(name=row[2])
        base_product.brand = brand_obj
    
    if row[4]!="":
        product_id_type_obj , created = ProductIDType.objects.get_or_create(name = row[4])
        base_product.product_id_type = product_id_type_obj

    amazon_uk_product["product_name"] = row[5]
    base_product.manufacturer = row[6]
    amazon_uk_product["recommended_browse_nodes"] = row[7]
    product_obj.standard_price = None if row[8]=="" else float(row[8])
    product_obj.quantity = None if row[9]=="" else int(row[9])
    amazon_uk_product["parentage"] = row[20]
    amazon_uk_product["parent_sku"] = row[21]
    amazon_uk_product["relationship_type"] = row[22]
    amazon_uk_product["variation_theme"] = row[23]
    amazon_uk_product["update_delete"] = row[24]
    base_product.manufacturer_part_number = row[26]
    amazon_uk_product["product_description"] = row[27]
    amazon_uk_product["wattage_metric"] = row[28]

    amazon_uk_product["search_terms"] = row[37]

    key_product_features = []
    for i in range(5):
        key_product_features.append(row[32+i])
    
    amazon_uk_product["product_attribute_list"] = key_product_features

    amazon_uk_product["search_terms"] = row[37]
    amazon_uk_product["wattage"] = None if row[45]=="" else float(row[45])
    product_obj.color = row[46]
    product_obj.color_map = row[47]

    if row[50]!="":
        material_type_obj , created= MaterialType.objects.get_or_create(name=row[50])
        product_obj.material_type = material_type_obj


    base_product.item_width_metric = row[84]
    base_product.item_width = None if row[85]=="" else float(row[85])
    base_product.item_height = None if row[86]=="" else float(row[86])
    base_product.item_height_metric = row[89]
    base_product.item_length_metric = row[91]
    base_product.item_length = None if row[92]=="" else float(row[92])
    base_product.item_display_length = None if row[98]=="" else float(row[98])
    base_product.item_display_length_metric = row[99]
    base_product.item_display_width = None if row[100]=="" else float(row[100])
    base_product.item_display_width_metric = row[101]
    base_product.item_display_height = None if row[102]=="" else float(row[102])
    base_product.item_display_height_metric = row[103]
    base_product.item_display_weight = None if row[106]=="" else float(row[106])
    base_product.item_display_weight_metric = row[107]
    base_product.item_display_volume = None if row[110]=="" else float(row[110])
    base_product.item_display_volume_metric = row[111]
    base_product.package_weight_metric = row[117]

    base_product.package_length_metric = row[118]
    base_product.package_width_metric = row[118]
    base_product.package_height_metric = row[118]

    base_product.package_weight = None if row[119]=="" else float(row[119])
    base_product.package_length = None if row[120]=="" else float(row[120])
    base_product.package_width = None if row[121]=="" else float(row[121])
    base_product.package_height = None if row[122]=="" else float(row[122])

    base_product.item_weight = None if row[165]=="" else float(row[165])
    base_product.item_weight_metric = row[166]
    amazon_uk_product["sale_price"] = None if row[187]=="" else float(row[187])
    amazon_uk_product["sale_from"] = None if row[188]=="" else float(row[188])
    amazon_uk_product["sale_end"] = None if row[189]=="" else float(row[189])
    #row[188] = str(product_obj.sale_from)
    #row[189] = str(product_obj.sale_end)
    amazon_uk_product["condition_type"] = row[190]


    # Graphics Part
    
    main_image_url = row[10]
    if main_image_url!="":
        filename = main_image_url.split("/")[-1]
        result = urllib.urlretrieve(main_image_url, filename)
        image_obj = Image.objects.create(image=File(open(result[0])))
        image_bucket_obj = ImageBucket.objects.create(image=image_obj, is_main_image=True)
        reset_main_images(product_obj)
        main_images_obj , created = MainImages.objects.get_or_create(product=product_obj,channel="Amazon UK")
        main_images_obj.main_images.add(image_bucket_obj)
        main_images_obj.save()
        os.system("rm "+result[0])              # Remove temporary file



    ####################### Sub Images Part #######################
    reset_sub_images(product_obj)

    channel_name = "Amazon UK"
    save_subimage(product_obj, row[11], 1 , channel_name)
    save_subimage(product_obj, row[12], 2 , channel_name)
    save_subimage(product_obj, row[13], 3 , channel_name)
    save_subimage(product_obj, row[14], 4 , channel_name)
    save_subimage(product_obj, row[15], 5 , channel_name)
    save_subimage(product_obj, row[16], 6 , channel_name)
    save_subimage(product_obj, row[17], 7 , channel_name)
    save_subimage(product_obj, row[18], 8 , channel_name)
    ####################### Sub Images Part ####################### 

    base_product.save()
    product_obj.save()
    channel_product.amazon_uk_product_json = json.dumps(amazon_uk_product)
    channel_product.save()


def update_product_partial_amazon_uk(product_obj, row):
    try:
        
        base_product = product_obj.base_product
        channel_product = product_obj.channel_product
        amazon_uk_product = json.loads(channel_product.amazon_uk_product_json)

        amazon_uk_product["feed_product_type"] = partial_overwrite(amazon_uk_product["feed_product_type"], row[0], "str")
        base_product.seller_sku = partial_overwrite(base_product.seller_sku, row[1], "str")

        if row[2]!="":
            brand_obj, created = Brand.objects.get_or_create(name=row[2])
            base_product.brand = brand_obj
        #product_obj.brand = partial_overwrite(product_obj.brand, row[2], "str")
        
        if row[4]!="":
            product_id_type_obj , created = ProductIDType.objects.get_or_create(name = row[4])
            base_product.product_id_type.name = partial_overwrite(product_id_type_obj.name, row[4], "str")
            product_id_type_obj.save()
            
        amazon_uk_product["product_name"] = partial_overwrite(amazon_uk_product["product_name"], row[5], "str")
        base_product.manufacturer = partial_overwrite(base_product.manufacturer, row[6], "str")
        amazon_uk_product["recommended_browse_nodes"] = partial_overwrite(amazon_uk_product["recommended_browse_nodes"], row[7], "str")
        product_obj.standard_price = partial_overwrite(product_obj.standard_price, row[8], "float")
        product_obj.quantity = partial_overwrite(product_obj.quantity, row[9], "int")
        amazon_uk_product["parentage"] = partial_overwrite(amazon_uk_product["parentage"], row[20], "str")
        amazon_uk_product["parent_sku"] = partial_overwrite(amazon_uk_product["parent_sku"], row[21], "str")
        amazon_uk_product["relationship_type"] = partial_overwrite(amazon_uk_product["relationship_type"], row[22], "str")
        amazon_uk_product["variation_theme"] = partial_overwrite(amazon_uk_product["variation_theme"], row[23], "str")
        amazon_uk_product["update_delete"] = partial_overwrite(amazon_uk_product["update_delete"], row[24], "str")
        base_product.manufacturer_part_number = partial_overwrite(base_product.manufacturer_part_number, row[26], "str")
        amazon_uk_product["product_description"] = partial_overwrite(amazon_uk_product["product_description"], row[27], "str")
        amazon_uk_product["wattage_metric"] = partial_overwrite(amazon_uk_product["wattage_metric"], row[28], "str")



        special_features = []
        for i in range(5):
            special_feature = row[51+i]
            if special_feature!="":
                special_features.append(special_feature)
        if len(special_features)>0:
            amazon_uk_product["special_features"] = special_features

        key_product_features = []
        old_key_product_features = json.loads(product_obj.product_attribute_list_amazon_uk)
        if len(old_key_product_features) > 0:
            for i in range(len(old_key_product_features)):
                old_key_product_features[i] = partial_overwrite(old_key_product_features[i], row[32+i], "str")
        
        amazon_uk_product["product_attribute_list"] = old_key_product_features


        amazon_uk_product["search_terms"] = partial_overwrite(amazon_uk_product["search_terms"], row[37], "str")
        amazon_uk_product["wattage"] = partial_overwrite(amazon_uk_product["wattage"], row[45], "float")
        product_obj.color = partial_overwrite(product_obj.color, row[46], "str")
        product_obj.color_map = partial_overwrite(product_obj.color_map, row[47], "str")
        
        if row[50] != "":
            material_type_obj = MaterialType.objects.get_or_create(name=row[50])
            product_obj.material_type.name = partial_overwrite(material_type_obj.name, row[50], "str")


        base_product.item_width_metric = partial_overwrite(base_product.material_type, row[84], "str")
        base_product.item_width = partial_overwrite(base_product.item_width, row[85], "float")
        base_product.item_height = partial_overwrite(base_product.item_height, row[86], "float")
        base_product.item_height_metric = partial_overwrite(base_product.item_height_metric, row[89], "str")
        base_product.item_length_metric = partial_overwrite(base_product.item_length_metric, row[91], "str")
        base_product.item_length = partial_overwrite(base_product.item_length, row[92], "float")
        base_product.shipping_weight = partial_overwrite(base_product.shipping_weight, row[96], "float")
        base_product.shipping_weight_metric = partial_overwrite(base_product.shipping_weight_metric, row[97], "str")
        base_product.item_display_length = partial_overwrite(base_product.item_display_length, row[98], "float")
        base_product.item_display_length_metric = partial_overwrite(base_product.item_display_length_metric, row[99], "str")
        base_product.item_display_width = partial_overwrite(base_product.item_display_width, row[100], "float")
        base_product.item_display_width_metric = partial_overwrite(base_product.item_display_width_metric, row[101], "str")
        base_product.item_display_height = partial_overwrite(base_product.item_display_height, row[102], "float")
        base_product.item_display_height_metric = partial_overwrite(base_product.item_display_height_metric, row[103], "str")
        base_product.item_display_weight = partial_overwrite(base_product.item_display_weight, row[106], "float")
        base_product.item_display_weight_metric = partial_overwrite(base_product.item_display_weight_metric, row[107], "str")
        base_product.item_display_volume = partial_overwrite(base_product.item_display_volume, row[110], "float")
        base_product.item_display_volume_metric = partial_overwrite(base_product.item_display_volume_metric, row[111], "str")
        base_product.package_weight_metric = partial_overwrite(base_product.package_weight_metric, row[117], "str")

        base_product.package_length_metric = partial_overwrite(base_product.package_weight_metric, row[118], "str")
        base_product.package_width_metric = partial_overwrite(base_product.package_width_metric, row[118], "str")
        base_product.package_height_metric = partial_overwrite(base_product.package_height_metric, row[118], "str")

        base_product.package_weight = partial_overwrite(base_product.package_weight, row[119], "float")
        base_product.package_length = partial_overwrite(base_product.package_length, row[120], "float")
        base_product.package_width = partial_overwrite(base_product.package_width, row[121], "float")
        base_product.package_height = partial_overwrite(base_product.package_height, row[122], "float")

        base_product.item_weight = partial_overwrite(base_product.item_weight, row[165], "float")
        base_product.item_weight_metric = partial_overwrite(base_product.item_weight_metric, row[166], "str")
        
        #row[188] = str(product_obj.sale_from)
        #row[189] = str(product_obj.sale_end)
        amazon_uk_product["sale_price"] = partial_overwrite(amazon_uk_product["sale_price"], row[187], "float")
        amazon_uk_product["sale_from"] = partial_overwrite(amazon_uk_product["sale_from"], row[188], "str")
        amazon_uk_product["sale_end"] = partial_overwrite(amazon_uk_product["sale_end"], row[189], "str")
        amazon_uk_product["condition_type"] = partial_overwrite(amazon_uk_product["condition_type"], row[190], "str")


        # Graphics Part
        main_image_url = row[10]
        if main_image_url!="":
            filename = main_image_url.split("/")[-1]
            result = urllib.urlretrieve(main_image_url, filename)
            image_obj = Image.objects.create(image=File(open(result[0])))
            image_bucket_obj = ImageBucket.objects.create(image=image_obj, is_main_image=True)
            reset_main_images(product_obj)
            main_images_obj , created = MainImages.objects.get_or_create(product=product_obj,channel="Amazon UK")
            main_images_obj.main_images.add(image_bucket_obj)
            os.system("rm "+result[0])              # Remove temporary file


        ####################### Sub Images Part ####################### 

        reset_sub_images(product_obj)

        channel_name = "Amazon UK"
        save_subimage(product_obj, row[11], 1 , channel_name)
        save_subimage(product_obj, row[12], 2 , channel_name)
        save_subimage(product_obj, row[13], 3 , channel_name)
        save_subimage(product_obj, row[14], 4 , channel_name)
        save_subimage(product_obj, row[15], 5 , channel_name)
        save_subimage(product_obj, row[16], 6 , channel_name)
        save_subimage(product_obj, row[17], 7 , channel_name)
        save_subimage(product_obj, row[18], 8 , channel_name)
        ####################### Sub Images Part #######################

        base_product.save()
        product_obj.save()
        channel_product.amazon_uk_product_json = json.dumps(amazon_uk_product)
        channel_product.save()

    except Exception as e:
        import sys
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error update_product_partial_amazon_uk", str(e), str(exc_tb.tb_lineno))


def update_product_missing_amazon_uk(product_obj, row):
    
    base_product = product_obj.base_product
    channel_product = product_obj.channel_product
    amazon_uk_product = json.loads(channel_product.amazon_uk_product_json)

    amazon_uk_product["feed_product_type"] = fill_missing(amazon_uk_product["feed_product_type"], row[0], "str")
    base_product.seller_sku = fill_missing(base_product.seller_sku, row[1], "str")

    if row[2]!="":
        brand_obj, created = Brand.objects.get_or_create(name=row[2])
        base_product.brand = brand_obj
    #product_obj.brand = fill_missing(product_obj.brand, row[2], "str")
    
    if row[4]!="":
        product_id_type_obj , created = ProductIDType.objects.get_or_create(name = row[4])
        base_product.product_id_type.name = fill_missing(product_id_type_obj.name, row[4], "str")
        product_id_type_obj.save()
        
    amazon_uk_product["product_name"] = fill_missing(amazon_uk_product["product_name"], row[5], "str")
    base_product.manufacturer = fill_missing(base_product.manufacturer, row[6], "str")
    amazon_uk_product["recommended_browse_nodes"] = fill_missing(amazon_uk_product["recommended_browse_nodes"], row[7], "str")
    product_obj.standard_price = fill_missing(product_obj.standard_price, row[8], "float")
    product_obj.quantity = fill_missing(product_obj.quantity, row[9], "int")
    amazon_uk_product["parentage"] = fill_missing(amazon_uk_product["parentage"], row[20], "str")
    amazon_uk_product["parent_sku"] = fill_missing(amazon_uk_product["parent_sku"], row[21], "str")
    amazon_uk_product["relationship_type"] = fill_missing(amazon_uk_product["relationship_type"], row[22], "str")
    amazon_uk_product["variation_theme"] = fill_missing(amazon_uk_product["variation_theme"], row[23], "str")
    amazon_uk_product["update_delete"] = fill_missing(amazon_uk_product["update_delete"], row[24], "str")
    base_product.manufacturer_part_number = fill_missing(base_product.manufacturer_part_number, row[26], "str")
    amazon_uk_product["product_description"] = fill_missing(amazon_uk_product["product_description"], row[27], "str")
    amazon_uk_product["wattage_metric"] = fill_missing(amazon_uk_product["wattage_metric"], row[28], "str")



    special_features = []
    for i in range(5):
        special_feature = row[51+i]
        if special_feature!="":
            special_features.append(special_feature)
    if len(special_features)>0:
        amazon_uk_product["special_features"] = special_features

    key_product_features = []
    old_key_product_features = json.loads(product_obj.product_attribute_list_amazon_uk)
    if len(old_key_product_features) > 0:
        for i in range(len(old_key_product_features)):
            old_key_product_features[i] = fill_missing(old_key_product_features[i], row[32+i], "str")
    
    amazon_uk_product["product_attribute_list"] = old_key_product_features


    amazon_uk_product["search_terms"] = fill_missing(amazon_uk_product["search_terms"], row[37], "str")
    amazon_uk_product["wattage"] = fill_missing(amazon_uk_product["wattage"], row[45], "float")
    product_obj.color = fill_missing(product_obj.color, row[46], "str")
    product_obj.color_map = fill_missing(product_obj.color_map, row[47], "str")
    
    if row[50] != "":
        material_type_obj = MaterialType.objects.get_or_create(name=row[50])
        product_obj.material_type.name = fill_missing(material_type_obj.name, row[50], "str")


    base_product.item_width_metric = fill_missing(base_product.material_type, row[84], "str")
    base_product.item_width = fill_missing(base_product.item_width, row[85], "float")
    base_product.item_height = fill_missing(base_product.item_height, row[86], "float")
    base_product.item_height_metric = fill_missing(base_product.item_height_metric, row[89], "str")
    base_product.item_length_metric = fill_missing(base_product.item_length_metric, row[91], "str")
    base_product.item_length = fill_missing(base_product.item_length, row[92], "float")
    base_product.shipping_weight = fill_missing(base_product.shipping_weight, row[96], "float")
    base_product.shipping_weight_metric = fill_missing(base_product.shipping_weight_metric, row[97], "str")
    base_product.item_display_length = fill_missing(base_product.item_display_length, row[98], "float")
    base_product.item_display_length_metric = fill_missing(base_product.item_display_length_metric, row[99], "str")
    base_product.item_display_width = fill_missing(base_product.item_display_width, row[100], "float")
    base_product.item_display_width_metric = fill_missing(base_product.item_display_width_metric, row[101], "str")
    base_product.item_display_height = fill_missing(base_product.item_display_height, row[102], "float")
    base_product.item_display_height_metric = fill_missing(base_product.item_display_height_metric, row[103], "str")
    base_product.item_display_weight = fill_missing(base_product.item_display_weight, row[106], "float")
    base_product.item_display_weight_metric = fill_missing(base_product.item_display_weight_metric, row[107], "str")
    base_product.item_display_volume = fill_missing(base_product.item_display_volume, row[110], "float")
    base_product.item_display_volume_metric = fill_missing(base_product.item_display_volume_metric, row[111], "str")
    base_product.package_weight_metric = fill_missing(base_product.package_weight_metric, row[117], "str")

    base_product.package_length_metric = fill_missing(base_product.package_weight_metric, row[118], "str")
    base_product.package_width_metric = fill_missing(base_product.package_width_metric, row[118], "str")
    base_product.package_height_metric = fill_missing(base_product.package_height_metric, row[118], "str")

    base_product.package_weight = fill_missing(base_product.package_weight, row[119], "float")
    base_product.package_length = fill_missing(base_product.package_length, row[120], "float")
    base_product.package_width = fill_missing(base_product.package_width, row[121], "float")
    base_product.package_height = fill_missing(base_product.package_height, row[122], "float")

    base_product.item_weight = fill_missing(base_product.item_weight, row[165], "float")
    base_product.item_weight_metric = fill_missing(base_product.item_weight_metric, row[166], "str")
    
    #row[188] = str(product_obj.sale_from)
    #row[189] = str(product_obj.sale_end)
    amazon_uk_product["sale_price"] = fill_missing(amazon_uk_product["sale_price"], row[187], "float")
    amazon_uk_product["sale_from"] = fill_missing(amazon_uk_product["sale_from"], row[188], "str")
    amazon_uk_product["sale_end"] = fill_missing(amazon_uk_product["sale_end"], row[189], "str")
    amazon_uk_product["condition_type"] = fill_missing(amazon_uk_product["condition_type"], row[190], "str")


    # Graphics Part
    main_image_url = row[10]
    if main_image_url!="":
        filename = main_image_url.split("/")[-1]
        result = urllib.urlretrieve(main_image_url, filename)
        image_obj = Image.objects.create(image=File(open(result[0])))
        image_bucket_obj = ImageBucket.objects.create(image=image_obj, is_main_image=True)
        reset_main_images(product_obj)
        main_images_obj , created = MainImages.objects.get_or_create(product=product_obj,channel="Amazon UK")
        main_images_obj.main_images.add(image_bucket_obj)
        os.system("rm "+result[0])              # Remove temporary file


    ####################### Sub Images Part ####################### 

    reset_sub_images(product_obj)

    channel_name = "Amazon UK"
    save_subimage(product_obj, row[11], 1 , channel_name)
    save_subimage(product_obj, row[12], 2 , channel_name)
    save_subimage(product_obj, row[13], 3 , channel_name)
    save_subimage(product_obj, row[14], 4 , channel_name)
    save_subimage(product_obj, row[15], 5 , channel_name)
    save_subimage(product_obj, row[16], 6 , channel_name)
    save_subimage(product_obj, row[17], 7 , channel_name)
    save_subimage(product_obj, row[18], 8 , channel_name)
    ####################### Sub Images Part #######################

    base_product.save()
    product_obj.save()
    channel_product.amazon_uk_product_json = json.dumps(amazon_uk_product)
    channel_product.save()


def create_new_product_amazon_uk(row):
    
    base_product_obj = BaseProduct.objects.create(seller_sku=row[1],
                                                  base_product_name= row[5])

    product_obj = Product.objects.create(product_id=row[3],
                                         base_product = base_product_obj)

    dealshub_product_obj = DealsHubProduct.objects.create(product=product_obj)

    channel_product_obj = product_obj.channel_product

    amazon_uk_product = json.loads(channel_product_obj.amazon_uk_product_json)

    amazon_uk_product["feed_product_type"] = row[0]

    if row[2]!="":
        brand_obj, created = Brand.objects.get_or_create(name=row[2])
        base_product_obj.brand = brand_obj
    
    if row[5]!="":
        product_id_type_obj, created = ProductIDType.objects.get_or_create(name=row[4])
        product_obj.product_id_type =product_id_type_obj

    amazon_uk_product["product_name"] = row[5]
    base_product_obj.manufacturer = row[6]
    amazon_uk_product["recommended_browse_nodes"] = row[7]
    product_obj.standard_price = None if row[8]=="" else float(row[8])
    product_obj.quantity = None if row[9]=="" else int(row[9])
    amazon_uk_product["parentage"] = row[20]
    amazon_uk_product["parent_sku"] = row[21]
    amazon_uk_product["relationship_type"] = row[22]
    amazon_uk_product["variation_theme"] = row[23]
    amazon_uk_product["update_delete"] = row[24]
    base_product_obj.manufacturer_part_number = row[26]
    amazon_uk_product["product_description"] = row[27]
    amazon_uk_product["wattage_metric"] = row[28]


    special_features = []
    for i in range(5):
        special_feature = row[51+i]
        if special_feature!="":
            special_features.append(special_feature)
    amazon_uk_product["special_features"] = special_features


    key_product_features = []
    for i in range(5):
        key_product_feature = row[32+i]
        if key_product_feature!="":  
            key_product_features.append(key_product_feature)
    amazon_uk_product["product_attribute_list"] = key_product_features


    amazon_uk_product["search_terms"] = row[37]
    amazon_uk_product["wattage"] = None if row[45]=="" else float(row[45])
    product_obj.color = row[46]
    product_obj.color_map = row[47]
    
    if row[50] != "":
        material_type_obj , created = MaterialType.objects.get_or_create(name=row[50])
        product_obj.material_type = material_type_obj

    base_product_obj.item_width_metric = row[84]
    base_product_obj.item_width = None if row[85]=="" else float(row[85])
    base_product_obj.item_height = None if row[86]=="" else float(row[86])
    base_product_obj.item_height_metric = row[89]
    base_product_obj.item_length_metric = row[91]
    base_product_obj.item_length = None if row[92]=="" else float(row[92])
    base_product_obj.shipping_weight = None if row[96]=="" else float(row[96])
    base_product_obj.shipping_weight_metric = row[97]
    base_product_obj.item_display_length = None if row[98]=="" else float(row[98])
    base_product_obj.item_display_length_metric = row[99]
    base_product_obj.item_display_width = None if row[100]=="" else float(row[100])
    base_product_obj.item_display_width_metric = row[101]
    base_product_obj.item_display_height = None if row[102]=="" else float(row[102])
    base_product_obj.item_display_height_metric = row[103]
    base_product_obj.item_display_weight = None if row[106]=="" else float(row[106])
    base_product_obj.item_display_weight_metric = row[107]
    base_product_obj.item_display_volume = None if row[110]=="" else float(row[110])
    base_product_obj.item_display_volume_metric = row[111]
    base_product_obj.package_weight_metric = row[117]

    base_product_obj.package_length_metric = row[118]
    base_product_obj.package_width_metric = row[118]
    base_product_obj.package_height_metric = row[118]

    base_product_obj.package_weight = None if row[119]=="" else float(row[119])
    base_product_obj.package_length = None if row[120]=="" else float(row[120])
    base_product_obj.package_width = None if row[121]=="" else float(row[121])
    base_product_obj.package_height = None if row[122]=="" else float(row[122])

    base_product_obj.item_weight = None if row[165]=="" else float(row[165])
    base_product_obj.item_weight_metric = row[166]
    

    #row[188] = str(product_obj.sale_from)
    #row[189] = str(product_obj.sale_end)
    amazon_uk_product["sale_price"] = None if row[187]=="" else float(row[187])
    amazon_uk_product["sale_from"] = None if row[188]=="" else float(row[188])
    amazon_uk_product["sale_end"] = None if row[189]=="" else float(row[189])
    amazon_uk_product["condition_type"] = row[190]



    # Graphics Part
    main_image_url = row[10]
    if main_image_url!="":
        filename = main_image_url.split("/")[-1]
        result = urllib.urlretrieve(main_image_url, filename)
        image_obj = Image.objects.create(image=File(open(result[0])))
        image_bucket_obj = ImageBucket.objects.create(image=image_obj, is_main_image=True)
        reset_main_images(product_obj)
        main_images_obj , created = MainImages.objects.get_or_create(product=product_obj,channel="Amazon UK")
        main_images_obj.main_images.add(image_bucket_obj)
        main_images_obj.save()
        os.system("rm "+result[0])


    ####################### Sub Images Part ####################### 

    channel_name = "Amazon UK"
    save_subimage(product_obj, row[11], 1 , channel_name)
    save_subimage(product_obj, row[12], 2 , channel_name)
    save_subimage(product_obj, row[13], 3 , channel_name)
    save_subimage(product_obj, row[14], 4 , channel_name)
    save_subimage(product_obj, row[15], 5 , channel_name)
    save_subimage(product_obj, row[16], 6 , channel_name)
    save_subimage(product_obj, row[17], 7 , channel_name)
    save_subimage(product_obj, row[18], 8 , channel_name)
    ####################### Sub Images Part ####################### 

    base_product_obj.save()
    product_obj.save()
    channel_product_obj.amazon_uk_product_json = json.dumps(amazon_uk_product)
    channel_product.save()


def import_amazon_uk(import_rule, import_file):
    try:
        data = csv.reader(import_file)
        cnt = 0
        for row in data:
            cnt += 1
            if cnt>=4:
                try:
                    product_id=row[3]
                    logger.info("Adding product %s", str(cnt))
                    if Product.objects.filter(product_id=product_id).exists():
                        product_obj = Product.objects.get(product_id=product_id)
                        if import_rule=="Full":
                            update_product_full_amazon_uk(product_obj, row)
                        elif import_rule=="Partial":
                            update_product_partial_amazon_uk(product_obj, row)
                        elif import_rule=="Missing":
                            update_product_missing_amazon_uk(product_obj, row)
                    else:   # Does not exist. Create new product
                        create_new_product_amazon_uk(row)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("Error for row index: %s at %s", e, str(exc_tb.tb_lineno))

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("import_amazon_uk: %s at %s", e, str(exc_tb.tb_lineno))
