from WAMSApp.models import *
import csv
import urllib
import json
import os
from django.core.files import File
from WAMSApp.core_utils import *
import sys
import logging
import xlsxwriter

logger = logging.getLogger(__name__)

def export_amazon_uae(products):
    try:
        try:
            os.system("rm ./files/csv/export-list-amazon-uae.xlsx")
        except Exception as e:
            logger.warning("Delete old xlsx %s", str(e))

        workbook = xlsxwriter.Workbook('./files/csv/export-list-amazon-uae.xlsx')
        worksheet = workbook.add_worksheet()

        cell_format = workbook.add_format({'bold': True})
        cell_format.set_pattern(1)
        cell_format.set_bg_color('yellow')

        rownum = 0
        colnum = 0
        with open('./WAMSApp/static/WAMSApp/csv/amazon_uae.csv','rt')as f:
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
                amazon_uae_product = json.loads(channel_product.amazon_uae_product_json)
                
                common_row = ["" for i in range(25)]
                common_row[0] = "UAE"
                common_row[1] = amazon_uae_product["feed_product_type"]
                common_row[2] = base_product.seller_sku
                common_row[3] = "" if base_product.brand==None else base_product.brand.name
                common_row[4] = product.product_id
                common_row[5] = str(product.product_id_type)
                common_row[6] = amazon_uae_product["product_name"]
                common_row[7] = base_product.manufacturer
                common_row[8] = amazon_uae_product["product_description"]
                common_row[9] = base_product.manufacturer_part_number
                bullet_points = ""
                product_attribute_list = amazon_uae_product["product_attribute_list"]
                for product_attribute in product_attribute_list:
                    #bullet_points += "\xe2\x80\xa2 " + product_attribute + "\n"
                    bullet_points += "- " + product_attribute + "\n"


                common_row[10] = bullet_points
                common_row[11] = amazon_uae_product["recommended_browse_nodes"]
                common_row[12] = product.standard_price
                common_row[13] = product.quantity
                common_row[14] = amazon_uae_product["update_delete"]

                dimensions = json.loads(base_product.dimensions)
                common_row[16] = dimensions["giftbox_h"]
                common_row[17] = dimensions["giftbox_l"]
                common_row[18] = dimensions["giftbox_l_metric"]
                common_row[19] = dimensions["giftbox_b"]
                #common_row[20] = base_product.fulfillment_centre_id
                #common_row[21] = base_product.package_dimension_unit_of_measure
                # common_row[22] = "" if base_product.package_weight == None else str(
                #     base_product.package_weight)
                # common_row[23] = base_product.package_weight_metric
                # common_row[24] = base_product.package_quantity

                # Graphics Part
                main_image_url = None
                
                try:

                    main_images_list = ImageBucket.objects.none()
                    main_images_obj = MainImages.objects.get(product = product, channel__name="Amazon UAE")
                    
                    main_images_list |= main_images_obj.main_images.all()

                    main_images_list = main_images_list.distinct()
                    
                    main_image_url = main_images_list[0].image.image.url
                except Exception as e:
                    pass

                common_row[15] = str(main_image_url)

                data_row_2 = []
                #logger.info("common_row: %s", str(common_row))
                for k in common_row:
                    if k==None:
                        data_row_2.append("")
                    else:
                        data_row_2.append(k)

                colnum = 0
                for k in data_row_2:
                    worksheet.write(rownum, colnum, k)
                    colnum += 1
                rownum += 1
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("export_amazon_uae: %s at %s", e, str(exc_tb.tb_lineno))

        workbook.close()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("export_amazon_uae: %s at %s", e, str(exc_tb.tb_lineno))

def update_product_full_amazon_uae(product_obj, row):

    base_product = product_obj.base_product
    channel_product = product_obj.channel_product
    amazon_uae_product = json.loads(channel_product.amazon_uae_product_json)

    amazon_uae_product["feed_product_type"] = row[1]
    base_product.seller_sku = row[2]

    brand_obj, created = Brand.objects.get_or_create(name=row[3])
    base_product.brand = brand_obj
    product_obj.product_id = row[4]
    product_obj.product_id_type = row[5]
    amazon_uae_product["product_name"] = row[6]
    base_product.manufacturer = row[7]
    amazon_uae_product["product_description"] = row[8]
    base_product.manufacturer_part_number = row[9]

    bullet_points = filter(None, row[10].replace("\n", "").split("\xe2\x80\xa2"))
    amazon_uae_product["product_attribute_list"] = bullet_points

    amazon_uae_product["recommended_browse_nodes"] = row[11]
    product_obj.standard_price = None if row[12] == "" else float(row[12])
    product_obj.quantity = None if row[13] == "" else int(row[13])
    amazon_uae_product["update_delete"] = row[14]

    base_product.package_height = None if row[16] == "" else float(row[16])
    base_product.package_length = None if row[17] == "" else float(row[17])
    base_product.package_length_metric = row[18]
    base_product.package_width = None if row[19] == "" else float(row[19])
    #product_obj.fulfillment_centre_id = row[20]
    #product_obj.package_dimension_unit_of_measure = row[21]
    base_product.package_weight = None if row[22] == "" else float(row[22])
    base_product.package_weight_metric = row[23]
    base_product.package_quantity = None if row[24] == "" else int(row[24])

    # Graphics Part

    main_image_url = row[15]
    if main_image_url != "":
        filename = main_image_url.split("/")[-1]
        result = urllib.urlretrieve(main_image_url, filename)
        image_obj = Image.objects.create(image=File(open(result[0])))
        image_bucket_obj = ImageBucket.objects.create(
            image=image_obj, is_main_image=True)
        reset_main_images(product_obj)
        main_images_obj , created = MainImages.objects.get_or_create(product=product_obj,channel="Amazon UAE")
        main_images_obj.main_images.add(image_bucket_obj)
        os.system("rm " + result[0])              # Remove temporary file

    channel_product.amazon_uae_product_json = json.dumps(amazon_uae_product)
    channel_product.save()
    product_obj.save()


def update_product_partial_amazon_uae(product_obj, row):
    try:
        base_product = product_obj.base_product
        channel_product = product_obj.channel_product
        amazon_uae_product = json.loads(channel_product.amazon_uae_product_json)
        
        amazon_uae_product["feed_product_type"] = partial_overwrite(
            amazon_uae_product["feed_product_type"], row[1], "str")
        base_product.seller_sku = partial_overwrite(
            base_product.seller_sku, row[2], "str")
        if row[3]!="":
            brand_obj, created = Brand.objects.get_or_create(name=row[3])
            base_product.brand = brand_obj
        product_obj.product_id = partial_overwrite(
            product_obj.product_id, row[4], "str")
        product_obj.product_id_type = partial_overwrite(
            product_obj.product_id_type, row[5], "str")
        amazon_uae_product["product_name"] = partial_overwrite(
            amazon_uae_product["product_name"], row[6], "str")
        base_product.manufacturer = partial_overwrite(
            base_product.manufacturer, row[7], "str")
        amazon_uae_product["product_description"] = partial_overwrite(
            amazon_uae_product["product_description"], row[8], "str")
        base_product.manufacturer_part_number = partial_overwrite(
            base_product.manufacturer_part_number, row[9], "str")

        # product_obj.product_attribute_list_amazon_uae = partial_overwrite(
        #     product_obj.product_attribute_list_amazon_uae, row[10], "str")

        if row[10]!="":
            bullet_points = filter(None, row[10].replace("\n", "").split("\xe2\x80\xa2"))
            amazon_uae_product["product_attribute_list"] = bullet_points

        amazon_uae_product["recommended_browse_nodes"] = partial_overwrite(
            amazon_uae_product["recommended_browse_nodes"], row[11], "str")
        product_obj.standard_price = partial_overwrite(
            product_obj.standard_price, row[12], "float")
        product_obj.quantity = partial_overwrite(
            product_obj.quantity , row[13], "int")
        amazon_uae_product["update_delete"] = partial_overwrite(
            amazon_uae_product["update_delete"], row[14], "str")

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
        product_obj.package_quantity = partial_overwrite(
            product_obj.package_quantity, row[24], "int")

        # Graphics Part
        main_image_url = row[15]
        if main_image_url != "":
            filename = main_image_url.split("/")[-1]
            result = urllib.urlretrieve(main_image_url, filename)
            image_obj = Image.objects.create(image=File(open(result[0])))
            image_bucket_obj = ImageBucket.objects.create(
                image=image_obj, is_main_image=True)

            reset_main_images(product_obj)
            main_images_obj , created = MainImages.objects.get_or_create(product=product_obj,channel="Amazon UAE")
            main_images_obj.main_images.add(image_bucket_obj)
            os.system("rm " + result[0])              # Remove temporary file

        channel_product.amazon_uae_product_json = json.dumps(amazon_uae_product)
        channel_product.save()
        product_obj.save()
        base_product.save()

    except Exception as e:
        import sys
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error update_product_partial_amazon_uae",
              str(e), str(exc_tb.tb_lineno))


def update_product_missing_amazon_uae(product_obj, row):

    base_product = product_obj.base_product
    channel_product = product_obj.channel_product
    amazon_uae_product = json.loads(channel_product.amazon_uae_product_json)
    
    amazon_uae_product["feed_product_type"] = fill_missing(
        amazon_uae_product["feed_product_type"], row[1], "str")
    base_product.seller_sku = fill_missing(
        base_product.seller_sku, row[2], "str")
    if row[3]!="":
        brand_obj, created = Brand.objects.get_or_create(name=row[3])
        base_product.brand = brand_obj
    product_obj.product_id = fill_missing(
        product_obj.product_id, row[4], "str")
    product_obj.product_id_type = fill_missing(
        product_obj.product_id_type, row[5], "str")
    amazon_uae_product["product_name"] = fill_missing(
        amazon_uae_product["product_name"], row[6], "str")
    base_product.manufacturer = fill_missing(
        base_product.manufacturer, row[7], "str")
    amazon_uae_product["product_description"] = fill_missing(
        amazon_uae_product["product_description"], row[8], "str")
    base_product.manufacturer_part_number = fill_missing(
        base_product.manufacturer_part_number, row[9], "str")

    # product_obj.product_attribute_list_amazon_uae = partial_overwrite(
    #     product_obj.product_attribute_list_amazon_uae, row[10], "str")

    if row[10]!="":
        bullet_points = filter(None, row[10].replace("\n", "").split("\xe2\x80\xa2"))
        amazon_uae_product["product_attribute_list"] = bullet_points

    amazon_uae_product["recommended_browse_nodes"] = fill_missing(
        amazon_uae_product["recommended_browse_nodes"], row[11], "str")
    product_obj.standard_price = fill_missing(
        product_obj.standard_price, row[12], "float")
    product_obj.quantity = fill_missing(
        product_obj.quantity , row[13], "int")
    amazon_uae_product["update_delete"] = fill_missing(
        amazon_uae_product["update_delete"], row[14], "str")

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
    product_obj.package_quantity = fill_missing(
        product_obj.package_quantity, row[24], "int")
    #product_obj.package_quantity = fill_missing(product_obj.package_quantity, row[24], "int")

    # Graphics Part
    main_image_url = row[15]
    if main_image_url != "" and product_obj.main_images.filter(is_main_image=True).count() == 0:
        filename = main_image_url.split("/")[-1]
        result = urllib.urlretrieve(main_image_url, filename)
        image_obj = Image.objects.create(image=File(open(result[0])))
        image_bucket_obj = ImageBucket.objects.create(
            image=image_obj, is_main_image=True)
        main_images_obj , created = MainImages.objects.get_or_create(product=product_obj,channel="Amazon UAE")

        main_images_obj.main_images.add(image_bucket_obj)
        os.system("rm " + result[0])              # Remove temporary file

    channel_product.amazon_uae_product_json = json.dumps(amazon_uae_product)
    channel_product.save()
    product_obj.save()
    base_product.save()


def create_new_product_amazon_uae(row):

    base_product_obj = BaseProduct.objects.create(seller_sku=row[2],
                                                  base_product_name= row[6])

    product_obj = Product.objects.create(product_id=row[4],
                                         base_product = base_product_obj)

    dealshub_product_obj = DealshubProduct.objects.create(product=product_obj)

    channel_product_obj = product_obj.channel_product

    amazon_uae_product = json.loads(channel_product_obj.amazon_uae_product_json)

    if row[3]!="":
        brand_obj, created = Brand.objects.get_or_create(name=row[3])
        base_product_obj.brand = brand_obj

    amazon_uae_product["feed_product_type"] = row[1]

    if row[5] != "":
        product_id_type_obj ,  created = ProductIDType.objects.get_or_create(name=row[5])
        product_obj.product_id_type = product_id_type_obj,

    amazon_uae_product["product_name"] = row[6]
    base_product_obj.manufacturer = row[7]
    amazon_uae_product["product_description"] = row[8]
    base_product_obj.manufacturer_part_number = row[9]


    bullet_points = filter(None, row[10].replace("\n", "").split("\xe2\x80\xa2"))
    amazon_uae_product["product_attribute_list"] = bullet_points
    
    amazon_uae_product["recommended_browse_nodes"] = row[11]
    product_obj.standard_price = None if row[12] == "" else float(row[12])
    product_obj.quantity = None if row[13] == "" else int(row[13])
    amazon_uae_product["update_delete"] = row[14]

    base_product_obj.package_height = None if row[16] == "" else float(row[16])
    base_product_obj.package_length = None if row[17] == "" else float(row[17])
    base_product_obj.package_length_metric = row[18]
    base_product_obj.package_width = None if row[19] == "" else float(row[19])
    #product_obj.fulfillment_centre_id = row[20]
    #product_obj.package_dimension_unit_of_measure = row[21]
    base_product_obj.package_weight = None if row[22] == "" else float(row[22])
    base_product_obj.package_weight_metric = row[23]
    base_product_obj.package_quantity = None if row[24]=="" else int(row[24])

    # Graphics Part

    main_image_url = row[15]
    if main_image_url != "":
        filename = main_image_url.split("/")[-1]
        result = urllib.urlretrieve(main_image_url, filename)
        image_obj = Image.objects.create(image=File(open(result[0])))
        image_bucket_obj = ImageBucket.objects.create(
            image=image_obj, is_main_image=True)
        reset_main_images(product_obj)
        main_images_obj , created = MainImages.objects.get_or_create(product=product_obj,channel="Amazon UAE")
        main_images_obj.main_images.add(image_bucket_obj)
        main_images_obj.save()
        os.system("rm " + result[0])              # Remove temporary file

    base_product_obj.save()
    product_obj.save()
    channel_product_obj.amazon_uae_product_json = json.dumps(amazon_uae_product)
    channel_product_obj.save()


def import_amazon_uae(import_rule, import_file, organization_obj):
    try:
        data = csv.reader(import_file)
        cnt = 0
        for row in data:
            cnt += 1
            if cnt >= 4:
                try:
                    product_id = row[4]
                    print("Cnt is ", cnt)
                    if Product.objects.filter(product_id=product_id, base_product__brand__organization=organization_obj).exists():
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
