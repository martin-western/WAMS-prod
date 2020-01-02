from WAMSApp.models import *
import csv
import urllib
import json
import os
from django.core.files import File
from WAMSApp.core_utils import *
import sys
import logging
logger = logging.getLogger(__name__)

def export_amazon_uae(products):
    try:
        fw = open("./files/csv/export-list-amazon-uae.csv", mode='w')
        writer = csv.writer(fw, delimiter=',', quotechar='"',
                            quoting=csv.QUOTE_MINIMAL)

        with open('./WAMSApp/static/WAMSApp/csv/amazon_uae.csv', 'rt')as f:
            data = csv.reader(f)
            for row in data:
                writer.writerow(row)

        for product in products:
            base_product = product.base_product
            channel_product = product.channel_product
            amazon_uae_product = json.loads(channel_product.amazon_uae_product_json)
            common_row = ["" for i in range(25)]
            common_row[0] = "UAE"
            common_row[1] = amazon_uae_product["feed_product_type"]
            common_row[2] = base_product.seller_sku
            common_row[3] = "" if base_product.brand==None else base_product.brand.name
            common_row[4] = product.product_id
            common_row[5] = product.product_id_type
            common_row[6] = product.product_name_amazon_uae
            common_row[7] = product.manufacturer
            common_row[8] = product.product_description_amazon_uae
            common_row[9] = product.manufacturer_part_number
            bullet_points = ""
            product_attribute_list = json.loads(
                product.product_attribute_list_amazon_uae)
            for product_attribute in product_attribute_list:
                #bullet_points += "\xe2\x80\xa2 " + product_attribute + "\n"
                bullet_points += "- " + product_attribute + "\n"


            common_row[10] = bullet_points
            common_row[11] = product.recommended_browse_nodes
            common_row[12] = product.standard_price
            common_row[13] = product.quantity
            common_row[14] = product.update_delete

            common_row[16] = "" if product.package_height == None else str(
                product.package_height)
            common_row[17] = "" if product.package_length == None else str(
                product.package_length)
            common_row[18] = product.package_length_metric
            common_row[19] = "" if product.package_width == None else str(
                product.package_width)
            #common_row[20] = product.fulfillment_centre_id
            #common_row[21] = product.package_dimension_unit_of_measure
            common_row[22] = "" if product.package_weight == None else str(
                product.package_weight)
            common_row[23] = product.package_weight_metric
            common_row[24] = product.quantity

            # Graphics Part
            if product.main_images.filter(is_main_image=True).count() > 0:
                common_row[15] = str(product.main_images.filter(is_main_image=True)[0].image.image.url)


            data_row_2 = []
            #logger.info("common_row: %s", str(common_row))
            for k in common_row:
                if k==None:
                    data_row_2.append("")
                elif isinstance(k, int)==False and isinstance(k, float)==False:
                    l = k.encode('utf-8').strip()
                    data_row_2.append(l)
                else:
                    data_row_2.append(k)

            writer.writerow(data_row_2)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("export_amazon_uae: %s at %s", e, str(exc_tb.tb_lineno))

def update_product_full_amazon_uae(product_obj, row):

    product_obj.feed_product_type = row[1]
    product_obj.seller_sku = row[2]

    brand_obj, created = Brand.objects.get_or_create(name=row[3])
    product_obj.brand = brand_obj
    product_obj.product_id = row[4]
    product_obj.product_id_type = row[5]
    product_obj.product_name_amazon_uae = row[6]
    product_obj.manufacturer = row[7]
    product_obj.product_description_amazon_uae = row[8]
    product_obj.manufacturer_part_number = row[9]

    bullet_points = filter(None, row[10].replace("\n", "").split("\xe2\x80\xa2"))
    product_obj.product_attribute_list_amazon_uae = json.dumps(bullet_points)

    product_obj.recommended_browse_nodes = row[11]
    product_obj.standard_price = None if row[12] == "" else float(row[12])
    product_obj.quantity = None if row[13] == "" else int(row[13])
    product_obj.update_delete = row[14]

    product_obj.package_height = None if row[16] == "" else float(row[16])
    product_obj.package_length = None if row[17] == "" else float(row[17])
    product_obj.package_length_metric = row[18]
    product_obj.package_width = None if row[19] == "" else float(row[19])
    #product_obj.fulfillment_centre_id = row[20]
    #product_obj.package_dimension_unit_of_measure = row[21]
    product_obj.package_weight = None if row[22] == "" else float(row[22])
    product_obj.package_weight_metric = row[23]
    product_obj.quantity = None if row[24] == "" else int(row[24])

    # Graphics Part

    main_image_url = row[15]
    if main_image_url != "":
        filename = main_image_url.split("/")[-1]
        result = urllib.urlretrieve(main_image_url, filename)
        image_obj = Image.objects.create(image=File(open(result[0])))
        image_bucket_obj = ImageBucket.objects.create(
            image=image_obj, is_main_image=True)
        reset_main_images(product_obj)
        product_obj.main_images.add(image_bucket_obj)
        os.system("rm " + result[0])              # Remove temporary file

    product_obj.save()


def update_product_partial_amazon_uae(product_obj, row):
    try:
        product_obj.feed_product_type = partial_overwrite(
            product_obj.feed_product_type, row[1], "str")
        product_obj.seller_sku = partial_overwrite(
            product_obj.seller_sku, row[2], "str")
        if row[3]!="":
            brand_obj, created = Brand.objects.get_or_create(name=row[3])
            product_obj.brand = brand_obj
        product_obj.product_id = partial_overwrite(
            product_obj.product_id, row[4], "str")
        product_obj.product_id_type = partial_overwrite(
            product_obj.product_id_type, row[5], "str")
        product_obj.product_name_amazon_uae = partial_overwrite(
            product_obj.product_name_amazon_uae, row[6], "str")
        product_obj.manufacturer = partial_overwrite(
            product_obj.manufacturer, row[7], "str")
        product_obj.product_description_amazon_uae = partial_overwrite(
            product_obj.product_description_amazon_uae, row[8], "str")
        product_obj.manufacturer_part_number = partial_overwrite(
            product_obj.manufacturer_part_number, row[9], "str")

        # product_obj.product_attribute_list_amazon_uae = partial_overwrite(
        #     product_obj.product_attribute_list_amazon_uae, row[10], "str")

        if row[10]!="":
            bullet_points = filter(None, row[10].replace("\n", "").split("\xe2\x80\xa2"))
            product_obj.product_attribute_list_amazon_uae = json.dumps(bullet_points)

        product_obj.recommended_browse_nodes = partial_overwrite(
            product_obj.recommended_browse_nodes, row[11], "str")
        product_obj.standard_price = partial_overwrite(
            product_obj.standard_price, row[12], "float")
        product_obj.quantity = partial_overwrite(
            product_obj.quantity, row[13], "int")
        product_obj.update_delete = partial_overwrite(
            product_obj.update_delete, row[14], "str")

        product_obj.package_height = partial_overwrite(
            product_obj.package_height, row[16], "float")
        product_obj.package_length = partial_overwrite(
            product_obj.package_length, row[17], "float")
        product_obj.package_length_metric = partial_overwrite(
            product_obj.package_length_metric, row[18], "str")
        product_obj.package_width = partial_overwrite(
            product_obj.package_width, row[19], "float")
        #product_obj.fulfillment_centre_id = row[20]
        #product_obj.package_dimension_unit_of_measure = row[21]
        product_obj.package_weight = partial_overwrite(
            product_obj.package_weight, row[22], "float")
        product_obj.package_weight_metric = partial_overwrite(
            product_obj.package_weight_metric, row[23], "str")
        #product_obj.package_quantity = partial_overwrite(product_obj.package_quantity, row[24], "int")

        # Graphics Part
        main_image_url = row[15]
        if main_image_url != "":
            filename = main_image_url.split("/")[-1]
            result = urllib.urlretrieve(main_image_url, filename)
            image_obj = Image.objects.create(image=File(open(result[0])))
            image_bucket_obj = ImageBucket.objects.create(
                image=image_obj, is_main_image=True)

            reset_main_images(product_obj)
            product_obj.main_images.add(image_bucket_obj)
            os.system("rm " + result[0])              # Remove temporary file

        product_obj.save()

    except Exception as e:
        import sys
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error update_product_partial_amazon_uae",
              str(e), str(exc_tb.tb_lineno))


def update_product_missing_amazon_uae(product_obj, row):

    product_obj.feed_product_type = fill_missing(
        product_obj.feed_product_type, row[1], "str")
    product_obj.seller_sku = fill_missing(
        product_obj.seller_sku, row[2], "str")

    if row[3]!="" and product_obj.brand==None:
        brand_obj, created = Brand.objects.get_or_create(name=row[3])
        product_obj.brand = brand_obj
    product_obj.product_id = fill_missing(
        product_obj.product_id, row[4], "str")
    product_obj.product_id_type = fill_missing(
        product_obj.product_id_type, row[5], "str")
    product_obj.product_name_amazon_uae = fill_missing(
        product_obj.product_name_amazon_uae, row[6], "str")
    product_obj.manufacturer = fill_missing(
        product_obj.manufacturer, row[7], "str")
    product_obj.product_description_amazon_uae = fill_missing(
        product_obj.product_description_amazon_uae, row[8], "str")
    product_obj.manufacturer_part_number = fill_missing(
        product_obj.manufacturer_part_number, row[9], "str")

    # product_obj.product_attribute_list_amazon_uae = fill_missing(
    #     product_obj.product_attribute_list_amazon_uae, row[10], "str")

    if product_obj.product_attribute_list_amazon_uae=="[]":
        bullet_points = filter(None, row[10].replace("\n", "").split("\xe2\x80\xa2"))
        product_obj.product_attribute_list_amazon_uae = json.dumps(bullet_points)


    product_obj.recommended_browse_nodes = fill_missing(
        product_obj.recommended_browse_nodes, row[11], "str")
    product_obj.standard_price = fill_missing(
        product_obj.standard_price, row[12], "float")
    product_obj.quantity = fill_missing(product_obj.quantity, row[13], "int")
    product_obj.update_delete = fill_missing(
        product_obj.update_delete, row[14], "str")

    product_obj.package_height = fill_missing(
        product_obj.package_height, row[16], "float")
    product_obj.package_length = fill_missing(
        product_obj.package_length, row[17], "float")
    product_obj.package_length_metric = fill_missing(
        product_obj.package_length_metric, row[18], "str")
    product_obj.package_width = fill_missing(
        product_obj.package_width, row[19], "float")
    #product_obj.fulfillment_centre_id = row[20]
    #product_obj.package_dimension_unit_of_measure = row[21]
    product_obj.package_weight = fill_missing(
        product_obj.package_weight, row[22], "float")
    product_obj.package_weight_metric = fill_missing(
        product_obj.package_weight_metric, row[23], "str")
    #product_obj.package_quantity = fill_missing(product_obj.package_quantity, row[24], "int")

    # Graphics Part
    main_image_url = row[15]
    if main_image_url != "" and product_obj.main_images.filter(is_main_image=True).count() == 0:
        filename = main_image_url.split("/")[-1]
        result = urllib.urlretrieve(main_image_url, filename)
        image_obj = Image.objects.create(image=File(open(result[0])))
        image_bucket_obj = ImageBucket.objects.create(
            image=image_obj, is_main_image=True)
        product_obj.main_images.add(image_bucket_obj)
        os.system("rm " + result[0])              # Remove temporary file

    product_obj.save()


def create_new_product_amazon_uae(row):
    product_obj = Product.objects.create(product_id=row[4],
                                         product_attribute_list_amazon_uk="[]",
                                         product_attribute_list_amazon_uae="[]",
                                         product_attribute_list_ebay="[]",
                                         special_features="[]")

    product_obj.feed_product_type = row[1]
    product_obj.seller_sku = row[2]
    if row[3]!="":
        brand_obj, created = Brand.objects.get_or_create(name=row[3])
        product_obj.brand = brand_obj
    product_obj.product_id_type = row[5]
    product_obj.product_name_amazon_uae = row[6]
    product_obj.product_name_amazon_uk = row[6]
    product_obj.product_name_ebay = row[6]
    product_obj.product_name_sap = row[6]
    product_obj.manufacturer = row[7]
    product_obj.product_description_amazon_uae = row[8]
    product_obj.product_description_amazon_uk = row[8]
    product_obj.product_description_ebay = row[8]
    product_obj.manufacturer_part_number = row[9]


    bullet_points = filter(None, row[10].replace("\n", "").split("\xe2\x80\xa2"))
    product_obj.product_attribute_list_amazon_uae = json.dumps(bullet_points)
    product_obj.product_attribute_list_amazon_uk = json.dumps(bullet_points)
    product_obj.product_attribute_list_ebay = json.dumps(bullet_points)

    product_obj.recommended_browse_nodes = row[11]
    product_obj.standard_price = None if row[12] == "" else float(row[12])
    product_obj.quantity = None if row[13] == "" else int(row[13])
    product_obj.update_delete = row[14]

    product_obj.package_height = None if row[16] == "" else float(row[16])
    product_obj.package_length = None if row[17] == "" else float(row[17])
    product_obj.package_length_metric = row[18]
    product_obj.package_width = None if row[19] == "" else float(row[19])
    #product_obj.fulfillment_centre_id = row[20]
    #product_obj.package_dimension_unit_of_measure = row[21]
    product_obj.package_weight = None if row[22] == "" else float(row[22])
    product_obj.package_weight_metric = row[23]
    #product_obj.package_quantity = None if row[24]=="" else int(row[24])

    # Graphics Part

    main_image_url = row[15]
    if main_image_url != "":
        filename = main_image_url.split("/")[-1]
        result = urllib.urlretrieve(main_image_url, filename)
        image_obj = Image.objects.create(image=File(open(result[0])))
        image_bucket_obj = ImageBucket.objects.create(
            image=image_obj, is_main_image=True)
        reset_main_images(product_obj)
        product_obj.main_images.add(image_bucket_obj)
        os.system("rm " + result[0])              # Remove temporary file

    product_obj.save()


def import_amazon_uae(import_rule, import_file):
    try:
        data = csv.reader(import_file)
        cnt = 0
        for row in data:
            cnt += 1
            if cnt >= 4:
                try:
                    product_id = row[4]
                    print("Cnt is ", cnt)
                    if Product.objects.filter(product_id=product_id).exists():
                        product_obj = Product.objects.get(
                            product_id=product_id)
                        if import_rule == "Full":
                            update_product_full_amazon_uae(product_obj, row)
                        elif import_rule == "Partial":
                            update_product_partial_amazon_uae(product_obj, row)
                        elif import_rule == "Missing":
                            update_product_missing_amazon_uae(product_obj, row)
                    else:   # Does not exist. Create new product
                        create_new_product_amazon_uae(row)
                except Exception as e:
                    print("Error for row index ", cnt, str(e))

    except Exception as e:
        print("import_amazon_uae error!", str(e))
