from WAMSApp.models import *
import csv
import urllib
import os
import json
from django.core.files import File
from WAMSApp.core_utils import *

import logging
import sys

logger = logging.getLogger(__name__)

def export_amazon_uk(products):
    try:

        fw = open("./files/csv/export-list-amazon-uk.csv", mode='w')
        writer = csv.writer(fw, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        
        
        with open('./WAMSApp/static/WAMSApp/csv/amazon_uk.csv','rt')as f:
            data = csv.reader(f)
            for row in data:
                writer.writerow(row)
        
        for product in products:
            common_row = ["" for i in range(214)]
            common_row[0] = product.feed_product_type
            common_row[1] = product.seller_sku
            common_row[2] = "" if product.brand==None else product.brand.name
            common_row[3] = product.product_id
            common_row[4] = product.product_id_type
            common_row[5] = product.product_name_amazon_uk
            common_row[6] = product.manufacturer
            common_row[7] = product.recommended_browse_nodes
            common_row[8] = "" if product.standard_price==None else str(product.standard_price)
            common_row[9] = "" if product.quantity==None else str(product.quantity)

            common_row[20] = product.parentage
            common_row[21] = product.parent_sku
            common_row[22] = product.relationship_type
            common_row[23] = product.variation_theme
            common_row[24] = product.update_delete
            
            common_row[26] = product.manufacturer_part_number
            common_row[27] = product.product_description_amazon_uk
            common_row[28] = product.wattage_metric
            key_product_features = json.loads(product.product_attribute_list_amazon_uk)
            row_cnt = 0
            if len(key_product_features) > 0:
                for key_product_feature in key_product_features[:5]:
                    common_row[32+row_cnt] = key_product_feature
                    row_cnt += 1

            common_row[37] = product.search_terms
            common_row[45] = "" if product.wattage==None else str(product.wattage)
            common_row[46] = "" if product.color==None else str(product.color)
            common_row[47] = "" if product.color_map==None else str(product.color_map)
            common_row[50] = "" if product.material_type==None else str(product.material_type)

            special_features = json.loads(product.special_features)
            row_cnt = 0
            if len(special_features) > 0:
                for special_feature in special_features[:5]:
                    common_row[51+row_cnt] = special_feature
                    row_cnt += 1

            # common_row[84] = product.item_width_metric
            # common_row[85] = "" if product.item_width==None else str(product.item_width)
            # common_row[86] = "" if product.item_height==None else str(product.item_height)
            common_row[84] = product.item_width_metric
            common_row[85] = "" if product.item_width==None else str(product.item_width)
            common_row[86] = "" if product.item_height==None else str(product.item_height)
            common_row[89] = product.item_height_metric
            # common_row[91] = product.item_length_metric
            # common_row[92] = "" if product.item_length==None else str(product.item_length)
            common_row[91] = product.item_length_metric
            common_row[92] = "" if product.item_length==None else str(product.item_length)
            # common_row[98] = "" if product.item_display_length==None else str(product.item_display_length)
            # common_row[99] = product.item_display_length_metric
            common_row[96] = "" if product.shipping_weight==None else str(product.shipping_weight)
            common_row[97] = product.shipping_weight_metric
            common_row[98] = "" if product.item_display_length==None else str(product.item_display_length)
            common_row[99] = product.item_display_length_metric
            # common_row[100] = "" if product.item_display_width==None else str(product.item_display_width) 
            # common_row[101] = product.item_display_width
            common_row[100] = "" if product.item_display_width==None else str(product.item_display_width) 
            common_row[101] = product.item_display_width_metric
            # common_row[102] = "" if product.item_display_height==None else str(product.item_display_height)
            # common_row[103] = product.item_display_height_metric
            common_row[102] = "" if product.item_display_height==None else str(product.item_display_height)
            common_row[103] = product.item_display_height_metric
            common_row[106] = "" if product.item_display_weight==None else str(product.item_display_weight)
            common_row[107] = product.item_display_weight_metric
            common_row[110] = "" if product.item_display_volume==None else str(product.item_display_volume)
            common_row[111] = product.item_display_volume_metric
            common_row[117] = product.package_weight_metric
            common_row[118] = product.package_height_metric
            common_row[119] = "" if product.package_weight==None else str(product.package_weight)
            common_row[120] = "" if product.package_length==None else str(product.package_length)
            common_row[121] = "" if product.package_width==None else str(product.package_width)
            common_row[122] = "" if product.package_height==None else str(product.package_height)

            common_row[165] = "" if product.item_weight==None else str(product.item_weight)
            common_row[166] = product.item_weight_metric
            common_row[187] = "" if product.sale_price==None else str(product.sale_price)
            #common_row[188] = str(product.sale_from)
            #common_row[189] = str(product.sale_end)
            common_row[190] = product.condition_type



            # Graphics Part
            #origin = "http://127.0.0.1:8000"
            if product.main_images.filter(is_main_image=True).count()>0:
                common_row[10] = str(product.main_images.filter(is_main_image=True)[0].image.image.url)
            image_cnt = 11
            for img in product.sub_images.filter(is_sub_image=True).order_by('sub_image_index')[:8]:
                common_row[image_cnt] = str(img.image.image.url)
                image_cnt += 1


            data_row_2 = []
            #logger.info("common_row: %s", str(common_row))
            for k in common_row:
                if k==None:
                    data_row_2.append("")
                elif isinstance(k, int)==False:
                    l = k.encode('utf-8').strip()
                    data_row_2.append(l)
                else:
                    data_row_2.append(k)

            writer.writerow(data_row_2)
        
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("export_amazon_uk: %s at %s", e, str(exc_tb.tb_lineno))





def update_product_full_amazon_uk(product_obj, row):
    
    product_obj.feed_product_type = row[0]
    product_obj.seller_sku = row[1]
    if row[2]!="":
        brand_obj = Brand.objects.create(name=row[2])
        product_obj.brand = brand_obj
    product_obj.product_id_type = row[4]
    product_obj.product_name_amazon_uk = row[5]
    product_obj.manufacturer = row[6]
    product_obj.recommended_browse_nodes = row[7]
    product_obj.standard_price = None if row[8]=="" else float(row[8])
    product_obj.quantity = None if row[9]=="" else int(row[9])
    product_obj.parentage = row[20]
    product_obj.parent_sku = row[21]
    product_obj.relationship_type = row[22]
    product_obj.variation_theme = row[23]
    product_obj.update_delete = row[24]
    product_obj.manufacturer_part_number = row[26]
    product_obj.product_description_amazon_uk = row[27]
    product_obj.wattage_metric = row[28]

    product_obj.search_terms = row[37]

    key_product_features = []
    for i in range(5):
        key_product_features.append(row[32+i])
    product_obj.product_attribute_list_amazon_uk = json.dumps(key_product_features)

    product_obj.search_terms = row[37]
    product_obj.wattage = None if row[45]=="" else float(row[45])
    product_obj.color = row[46]
    product_obj.color_map = row[47]
    product_obj.material_type = row[50]


    product_obj.item_width_metric = row[84]
    product_obj.item_width = None if row[85]=="" else float(row[85])
    product_obj.item_height = None if row[86]=="" else float(row[86])
    product_obj.item_height_metric = row[89]
    product_obj.item_length_metric = row[91]
    product_obj.item_length = None if row[92]=="" else float(row[92])
    product_obj.item_display_length = None if row[98]=="" else float(row[98])
    product_obj.item_display_length_metric = row[99]
    product_obj.item_display_width = None if row[100]=="" else float(row[100])
    product_obj.item_display_width_metric = row[101]
    product_obj.item_display_height = None if row[102]=="" else float(row[102])
    product_obj.item_display_height_metric = row[103]
    product_obj.item_display_weight = None if row[106]=="" else float(row[106])
    product_obj.item_display_weight_metric = row[107]
    product_obj.item_display_volume = None if row[110]=="" else float(row[110])
    product_obj.item_display_volume_metric = row[111]
    product_obj.package_weight_metric = row[117]

    product_obj.package_length_metric = row[118]
    product_obj.package_width_metric = row[118]
    product_obj.package_height_metric = row[118]

    product_obj.package_weight = None if row[119]=="" else float(row[119])
    product_obj.package_length = None if row[120]=="" else float(row[120])
    product_obj.package_width = None if row[121]=="" else float(row[121])
    product_obj.package_height = None if row[122]=="" else float(row[122])

    product_obj.item_weight = None if row[165]=="" else float(row[165])
    product_obj.item_weight_metric = row[166]
    product_obj.sale_price = None if row[187]=="" else float(row[187])
    #row[188] = str(product_obj.sale_from)
    #row[189] = str(product_obj.sale_end)
    product_obj.condition_type = row[190]


    # Graphics Part
    
    main_image_url = row[10]
    if main_image_url!="":
        filename = main_image_url.split("/")[-1]
        result = urllib.urlretrieve(main_image_url, filename)
        image_obj = Image.objects.create(image=File(open(result[0])))
        image_bucket_obj = ImageBucket.objects.create(image=image_obj, is_main_image=True)
        reset_main_images(product_obj)
        product_obj.main_images.add(image_bucket_obj)
        os.system("rm "+result[0])              # Remove temporary file



    ####################### Sub Images Part #######################
    reset_sub_images(product_obj)

    save_subimage(product_obj, row[11], 1)
    save_subimage(product_obj, row[12], 2)
    save_subimage(product_obj, row[13], 3)
    save_subimage(product_obj, row[14], 4)
    save_subimage(product_obj, row[15], 5)
    save_subimage(product_obj, row[16], 6)
    save_subimage(product_obj, row[17], 7)
    save_subimage(product_obj, row[18], 8)
    ####################### Sub Images Part ####################### 

    product_obj.save()


def update_product_partial_amazon_uk(product_obj, row):
    try:
        product_obj.feed_product_type = partial_overwrite(product_obj.feed_product_type, row[0], "str")
        product_obj.seller_sku = partial_overwrite(product_obj.seller_sku, row[1], "str")

        if row[2]!="":
            brand_obj, created = Brand.objects.get_or_create(name=row[2])
            product_obj.brand = brand_obj
        #product_obj.brand = partial_overwrite(product_obj.brand, row[2], "str")
        product_obj.product_id_type = partial_overwrite(product_obj.product_id_type, row[4], "str")
        product_obj.product_name_amazon_uk = partial_overwrite(product_obj.product_name_amazon_uk, row[5], "str")
        product_obj.manufacturer = partial_overwrite(product_obj.manufacturer, row[6], "str")
        product_obj.recommended_browse_nodes = partial_overwrite(product_obj.recommended_browse_nodes, row[7], "str")
        product_obj.standard_price = partial_overwrite(product_obj.standard_price, row[8], "float")
        product_obj.quantity = partial_overwrite(product_obj.quantity, row[9], "int")
        product_obj.parentage = partial_overwrite(product_obj.parentage, row[20], "str")
        product_obj.parent_sku = partial_overwrite(product_obj.parent_sku, row[21], "str")
        product_obj.relationship_type = partial_overwrite(product_obj.relationship_type, row[22], "str")
        product_obj.variation_theme = partial_overwrite(product_obj.variation_theme, row[23], "str")
        product_obj.update_delete = partial_overwrite(product_obj.update_delete, row[24], "str")
        product_obj.manufacturer_part_number = partial_overwrite(product_obj.manufacturer_part_number, row[26], "str")
        product_obj.product_description_amazon_uk = partial_overwrite(product_obj.product_description_amazon_uk, row[27], "str")
        product_obj.wattage_metric = partial_overwrite(product_obj.wattage_metric, row[28], "str")



        special_features = []
        for i in range(5):
            special_feature = row[51+i]
            if special_feature!="":
                special_features.append(special_feature)
        if len(special_features)>0:
            product_obj.special_features = json.dumps(special_features)

        key_product_features = []
        old_key_product_features = json.loads(product_obj.product_attribute_list_amazon_uk)
        if len(old_key_product_features) > 0:
            for i in range(len(old_key_product_features)):
                old_key_product_features[i] = partial_overwrite(old_key_product_features[i], row[32+i], "str")
        product_obj.product_attribute_list_amazon_uk = json.dumps(old_key_product_features)


        product_obj.search_terms = partial_overwrite(product_obj.search_terms, row[37], "str")
        product_obj.wattage = partial_overwrite(product_obj.wattage, row[45], "float")
        product_obj.color = partial_overwrite(product_obj.color, row[46], "str")
        product_obj.color_map = partial_overwrite(product_obj.color_map, row[47], "str")
        product_obj.material_type = partial_overwrite(product_obj.material_type, row[50], "str")


        product_obj.item_width_metric = partial_overwrite(product_obj.material_type, row[84], "str")
        product_obj.item_width = partial_overwrite(product_obj.item_width, row[85], "float")
        product_obj.item_height = partial_overwrite(product_obj.item_height, row[86], "float")
        product_obj.item_height_metric = partial_overwrite(product_obj.item_height_metric, row[89], "str")
        product_obj.item_length_metric = partial_overwrite(product_obj.item_length_metric, row[91], "str")
        product_obj.item_length = partial_overwrite(product_obj.item_length, row[92], "float")
        product_obj.shipping_weight = partial_overwrite(product_obj.shipping_weight, row[96], "float")
        product_obj.shipping_weight_metric = partial_overwrite(product_obj.shipping_weight_metric, row[97], "str")
        product_obj.item_display_length = partial_overwrite(product_obj.item_display_length, row[98], "float")
        product_obj.item_display_length_metric = partial_overwrite(product_obj.item_display_length_metric, row[99], "str")
        product_obj.item_display_width = partial_overwrite(product_obj.item_display_width, row[100], "float")
        product_obj.item_display_width_metric = partial_overwrite(product_obj.item_display_width_metric, row[101], "str")
        product_obj.item_display_height = partial_overwrite(product_obj.item_display_height, row[102], "float")
        product_obj.item_display_height_metric = partial_overwrite(product_obj.item_display_height_metric, row[103], "str")
        product_obj.item_display_weight = partial_overwrite(product_obj.item_display_weight, row[106], "float")
        product_obj.item_display_weight_metric = partial_overwrite(product_obj.item_display_weight_metric, row[107], "str")
        product_obj.item_display_volume = partial_overwrite(product_obj.item_display_volume, row[110], "float")
        product_obj.item_display_volume_metric = partial_overwrite(product_obj.item_display_volume_metric, row[111], "str")
        product_obj.package_weight_metric = partial_overwrite(product_obj.package_weight_metric, row[117], "str")

        product_obj.package_length_metric = partial_overwrite(product_obj.package_weight_metric, row[118], "str")
        product_obj.package_width_metric = partial_overwrite(product_obj.package_width_metric, row[118], "str")
        product_obj.package_height_metric = partial_overwrite(product_obj.package_height_metric, row[118], "str")

        product_obj.package_weight = partial_overwrite(product_obj.package_weight, row[119], "float")
        product_obj.package_length = partial_overwrite(product_obj.package_length, row[120], "float")
        product_obj.package_width = partial_overwrite(product_obj.package_width, row[121], "float")
        product_obj.package_height = partial_overwrite(product_obj.package_height, row[122], "float")

        product_obj.item_weight = partial_overwrite(product_obj.item_weight, row[165], "float")
        product_obj.item_weight_metric = partial_overwrite(product_obj.item_weight_metric, row[166], "str")
        product_obj.sale_price = partial_overwrite(product_obj.sale_price, row[187], "float")
        #row[188] = str(product_obj.sale_from)
        #row[189] = str(product_obj.sale_end)
        product_obj.condition_type = partial_overwrite(product_obj.condition_type, row[190], "str")


        # Graphics Part
        main_image_url = row[10]
        if main_image_url!="":
            filename = main_image_url.split("/")[-1]
            result = urllib.urlretrieve(main_image_url, filename)
            image_obj = Image.objects.create(image=File(open(result[0])))
            image_bucket_obj = ImageBucket.objects.create(image=image_obj, is_main_image=True)
            reset_main_images(product_obj)
            product_obj.main_images.add(image_bucket_obj)
            os.system("rm "+result[0])              # Remove temporary file


        ####################### Sub Images Part ####################### 

        reset_sub_images(product_obj)

        save_subimage(product_obj, row[11], 1)
        save_subimage(product_obj, row[12], 2)
        save_subimage(product_obj, row[13], 3)
        save_subimage(product_obj, row[14], 4)
        save_subimage(product_obj, row[15], 5)
        save_subimage(product_obj, row[16], 6)
        save_subimage(product_obj, row[17], 7)
        save_subimage(product_obj, row[18], 8)
        ####################### Sub Images Part #######################

        product_obj.save()
    except Exception as e:
        import sys
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error update_product_partial_amazon_uk", str(e), str(exc_tb.tb_lineno))


def update_product_missing_amazon_uk(product_obj, row):
    product_obj.feed_product_type = fill_missing(product_obj.feed_product_type, row[0], "str")
    product_obj.seller_sku = fill_missing(product_obj.seller_sku, row[1], "str")
    if row[2]!="" and product_obj.brand==None:
        brand_obj, created = Brand.objects.get_or_create(name=row[2])
        product_obj.brand = brand_obj
    #product_obj.brand = fill_missing(product_obj.brand, row[2], "str")
    product_obj.product_id_type = fill_missing(product_obj.product_id_type, row[4], "str")
    product_obj.product_name_amazon_uk = fill_missing(product_obj.product_name_amazon_uk, row[5], "str")
    product_obj.manufacturer = fill_missing(product_obj.manufacturer, row[6], "str")
    product_obj.recommended_browse_nodes = fill_missing(product_obj.recommended_browse_nodes, row[7], "str")
    product_obj.standard_price = fill_missing(product_obj.standard_price, row[8], "float")
    product_obj.quantity = fill_missing(product_obj.quantity, row[9], "int")
    product_obj.parentage = fill_missing(product_obj.parentage, row[20], "str")
    product_obj.parent_sku = fill_missing(product_obj.parent_sku, row[21], "str")
    product_obj.relationship_type = fill_missing(product_obj.relationship_type, row[22], "str")
    product_obj.variation_theme = fill_missing(product_obj.variation_theme, row[23], "str")
    product_obj.update_delete = fill_missing(product_obj.update_delete, row[24], "str")
    product_obj.manufacturer_part_number = fill_missing(product_obj.manufacturer_part_number, row[26], "str")
    product_obj.product_description_amazon_uk = fill_missing(product_obj.product_description_amazon_uk, row[27], "str")
    product_obj.wattage_metric = fill_missing(product_obj.wattage_metric, row[28], "str")
    

    key_product_features = []
    old_key_product_features = json.loads(product_obj.product_attribute_list_amazon_uk)
    if len(old_key_product_features) > 0:
        for i in range(len(old_key_product_features)):
            old_key_product_features[i] = fill_missing(old_key_product_features[i], row[32+i], "str")
    product_obj.product_attribute_list_amazon_uk = json.dumps(old_key_product_features)

    product_obj.search_terms = fill_missing(product_obj.search_terms, row[37], "str")
    product_obj.wattage = fill_missing(product_obj.wattage, row[45], "float")
    product_obj.color = fill_missing(product_obj.color, row[46], "str")
    product_obj.color_map = fill_missing(product_obj.color_map, row[47], "str")
    product_obj.material_type = fill_missing(product_obj.material_type, row[50], "str")


    product_obj.item_width_metric = fill_missing(product_obj.item_width_metric, row[84], "str")
    product_obj.item_width = fill_missing(product_obj.item_width, row[85], "float")
    product_obj.item_height = fill_missing(product_obj.item_height, row[86], "float")
    product_obj.item_height_metric = fill_missing(product_obj.item_height_metric, row[89], "str")
    product_obj.item_length_metric = fill_missing(product_obj.item_length_metric, row[91], "str")
    product_obj.item_length = fill_missing(product_obj.item_length, row[92], "float")
    product_obj.shipping_weight = fill_missing(product_obj.shipping_weight, row[96], "float")
    product_obj.shipping_weight_metric = fill_missing(product_obj.shipping_weight_metric, row[97], "str")
    product_obj.item_display_length = fill_missing(product_obj.item_display_length, row[98], "float")
    product_obj.item_display_length_metric = fill_missing(product_obj.item_display_length_metric, row[99], "str")
    product_obj.item_display_width = fill_missing(product_obj.item_display_width, row[100], "float")
    product_obj.item_display_width_metric = fill_missing(product_obj.item_display_width_metric, row[101], "float")
    product_obj.item_display_height = fill_missing(product_obj.item_display_height, row[102], "float")
    product_obj.item_display_height_metric = fill_missing(product_obj.item_display_height_metric, row[103], "str")
    product_obj.item_display_weight = fill_missing(product_obj.item_display_weight, row[106], "float")
    product_obj.item_display_weight_metric = fill_missing(product_obj.item_display_weight_metric, row[107], "str")
    product_obj.item_display_volume = fill_missing(product_obj.item_display_volume, row[110], "float")
    product_obj.item_display_volume_metric = fill_missing(product_obj.item_display_volume_metric, row[111], "str")
    product_obj.package_weight_metric = fill_missing(product_obj.package_weight_metric, row[117], "str")

    product_obj.package_length_metric = fill_missing(product_obj.package_weight_metric, row[118], "str")
    product_obj.package_width_metric = fill_missing(product_obj.package_width_metric, row[118], "str")
    product_obj.package_height_metric = fill_missing(product_obj.package_height_metric, row[118], "str")

    product_obj.package_weight = fill_missing(product_obj.package_weight, row[119], "float")
    product_obj.package_length = fill_missing(product_obj.package_length, row[120], "float")
    product_obj.package_width = fill_missing(product_obj.package_width, row[121], "float")
    product_obj.package_height = fill_missing(product_obj.package_height, row[122], "float")

    product_obj.item_weight = fill_missing(product_obj.item_weight, row[165], "float")
    product_obj.item_weight_metric = fill_missing(product_obj.item_weight_metric, row[166], "str")
    product_obj.sale_price = fill_missing(product_obj.sale_price, row[187], "float")
    #row[188] = str(product_obj.sale_from)
    #row[189] = str(product_obj.sale_end)
    product_obj.condition_type = fill_missing(product_obj.condition_type, row[190], "str")


    main_image_url = row[10]
    if main_image_url!="" and product_obj.main_images.filter(is_main_image=True).count()==0:
        filename = main_image_url.split("/")[-1]
        result = urllib.urlretrieve(main_image_url, filename)
        image_obj = Image.objects.create(image=File(open(result[0])))
        image_bucket_obj = ImageBucket.objects.create(image=image_obj, is_main_image=True)
        product_obj.main_images.add(image_bucket_obj)
        os.system("rm "+result[0])              # Remove temporary file


    ####################### Sub Images Part ####################### 

    reset_sub_images(product_obj)

    save_subimage(product_obj, row[11], 1)
    save_subimage(product_obj, row[12], 2)
    save_subimage(product_obj, row[13], 3)
    save_subimage(product_obj, row[14], 4)
    save_subimage(product_obj, row[15], 5)
    save_subimage(product_obj, row[16], 6)
    save_subimage(product_obj, row[17], 7)
    save_subimage(product_obj, row[18], 8)
    ####################### Sub Images Part ####################### 

    product_obj.save()


def create_new_product_amazon_uk(row):
    product_obj = Product.objects.create(product_id=row[3])
    product_obj.feed_product_type = row[0]
    product_obj.seller_sku = row[1]
    if row[2]!="":
        brand_obj, created = Brand.objects.get_or_create(name=row[2])
        product_obj.brand = brand_obj
    product_obj.product_id_type = row[4]
    product_obj.product_name_amazon_uk = row[5]
    product_obj.product_name_amazon_uae = row[5]
    product_obj.product_name_ebay = row[5]
    product_obj.product_name_sap = row[5]
    product_obj.manufacturer = row[6]
    product_obj.recommended_browse_nodes = row[7]
    product_obj.standard_price = None if row[8]=="" else float(row[8])
    product_obj.quantity = None if row[9]=="" else int(row[9])
    product_obj.parentage = row[20]
    product_obj.parent_sku = row[21]
    product_obj.relationship_type = row[22]
    product_obj.variation_theme = row[23]
    product_obj.update_delete = row[24]
    product_obj.manufacturer_part_number = row[26]
    product_obj.product_description_amazon_uk = row[27]
    product_obj.wattage_metric = row[28]


    special_features = []
    for i in range(5):
        special_feature = row[51+i]
        if special_feature!="":
            special_features.append(special_feature)
    product_obj.special_features = json.dumps(special_features)


    key_product_features = []
    for i in range(5):
        key_product_feature = row[32+i]
        if key_product_feature!="":  
            key_product_features.append(key_product_feature)
    product_obj.product_attribute_list_amazon_uk = json.dumps(key_product_features)


    product_obj.search_terms = row[37]
    product_obj.wattage = None if row[45]=="" else float(row[45])
    product_obj.color = row[46]
    product_obj.color_map = row[47]
    product_obj.material_type = row[50]


    product_obj.item_width_metric = row[84]
    product_obj.item_width = None if row[85]=="" else float(row[85])
    product_obj.item_height = None if row[86]=="" else float(row[86])
    product_obj.item_height_metric = row[89]
    product_obj.item_length_metric = row[91]
    product_obj.item_length = None if row[92]=="" else float(row[92])
    product_obj.shipping_weight = None if row[96]=="" else float(row[96])
    product_obj.shipping_weight_metric = row[97]
    product_obj.item_display_length = None if row[98]=="" else float(row[98])
    product_obj.item_display_length_metric = row[99]
    product_obj.item_display_width = None if row[100]=="" else float(row[100])
    product_obj.item_display_width_metric = row[101]
    product_obj.item_display_height = None if row[102]=="" else float(row[102])
    product_obj.item_display_height_metric = row[103]
    product_obj.item_display_weight = None if row[106]=="" else float(row[106])
    product_obj.item_display_weight_metric = row[107]
    product_obj.item_display_volume = None if row[110]=="" else float(row[110])
    product_obj.item_display_volume_metric = row[111]
    product_obj.package_weight_metric = row[117]

    product_obj.package_length_metric = row[118]
    product_obj.package_width_metric = row[118]
    product_obj.package_height_metric = row[118]

    product_obj.package_weight = None if row[119]=="" else float(row[119])
    product_obj.package_length = None if row[120]=="" else float(row[120])
    product_obj.package_width = None if row[121]=="" else float(row[121])
    product_obj.package_height = None if row[122]=="" else float(row[122])

    product_obj.item_weight = None if row[165]=="" else float(row[165])
    product_obj.item_weight_metric = row[166]
    product_obj.sale_price = None if row[187]=="" else float(row[187])
    #row[188] = str(product_obj.sale_from)
    #row[189] = str(product_obj.sale_end)
    product_obj.condition_type = row[190]



    # Graphics Part
    main_image_url = row[10]
    if main_image_url!="":
        filename = main_image_url.split("/")[-1]
        result = urllib.urlretrieve(main_image_url, filename)
        image_obj = Image.objects.create(image=File(open(result[0])))
        image_bucket_obj = ImageBucket.objects.create(image=image_obj, is_main_image=True)
        product_obj.main_images.add(image_bucket_obj)
        os.system("rm "+result[0])


    ####################### Sub Images Part ####################### 
    save_subimage(product_obj, row[11], 1)
    save_subimage(product_obj, row[12], 2)
    save_subimage(product_obj, row[13], 3)
    save_subimage(product_obj, row[14], 4)
    save_subimage(product_obj, row[15], 5)
    save_subimage(product_obj, row[16], 6)
    save_subimage(product_obj, row[17], 7)
    save_subimage(product_obj, row[18], 8)
    ####################### Sub Images Part ####################### 

    product_obj.save()


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
