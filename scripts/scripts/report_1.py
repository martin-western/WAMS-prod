from WAMSApp.models import *
import csv
import sys

product_objs = Product.objects.all()

fw = open("./files/csv/report-1-images-count.csv", mode='w')
writer = csv.writer(fw,
                    delimiter=',',
                    quotechar='"',
                    quoting=csv.QUOTE_MINIMAL)

row = ["Sr. No.",
       "Product ID",
       "Product Name",
       "Brand",
       "Main Images",
       "Sub Images",
       "PFL Images",
       "White Background Images",
       "Lifestyle Images",
       "Certificate Images",
       "Giftbox Images",
       "Diecut Images",
       "A+ Content Images",
       "Ads Images",
       "Unedited Images",
       "PFL Generated Images"]

writer.writerow(row)

cnt = 0
for product_obj in product_objs:
    try:
        break
        cnt += 1
        print("Cnt: ", cnt)
        row = [str(cnt),
               str(product_obj.product_id),
               product_obj.product_name_sap,
               str(product_obj.brand),
               str(product_obj.main_images.all().count()),
               str(product_obj.sub_images.all().count()),
               str(product_obj.pfl_images.all().count()),
               str(product_obj.white_background_images.all().count()),
               str(product_obj.lifestyle_images.all().count()),
               str(product_obj.certificate_images.all().count()),
               str(product_obj.giftbox_images.all().count()),
               str(product_obj.diecut_images.all().count()),
               str(product_obj.aplus_content_images.all().count()),
               str(product_obj.ads_images.all().count()),
               str(product_obj.unedited_images.all().count()),
               str(product_obj.pfl_generated_images.all().count())]

        data_row = []
        for k in row:
            l = k.encode('utf-8').strip()
            data_row.append(l)
        writer.writerow(data_row)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error pk:", product_obj.pk, str(e), str(exc_tb.tb_lineno))

fw.close()

#########################################################################


fw = open("./files/csv/report-1-images-boolean.csv", mode='w')
writer = csv.writer(fw,
                    delimiter=',',
                    quotechar='"',
                    quoting=csv.QUOTE_MINIMAL)

row = ["Sr. No.",
       "Product ID",
       "Product Name",
       "Brand",
       "Main Images",
       "Sub Images",
       "PFL Images",
       "White Background Images",
       "Lifestyle Images",
       "Certificate Images",
       "Giftbox Images",
       "Diecut Images",
       "A+ Content Images",
       "Ads Images",
       "Unedited Images",
       "PFL Generated Images"]



writer.writerow(row)

cnt = 0
for product_obj in product_objs:
    try:
        cnt += 1
        print("Cnt: ", cnt)
        row = [str(cnt),
               str(product_obj.product_id),
               product_obj.product_name_sap,
               str(product_obj.brand),
               str(product_obj.main_images.all().count()),
               str(product_obj.sub_images.all().count()),
               str(product_obj.pfl_images.all().count()),
               str(product_obj.white_background_images.all().count()),
               str(product_obj.lifestyle_images.all().count()),
               str(product_obj.certificate_images.all().count()),
               str(product_obj.giftbox_images.all().count()),
               str(product_obj.diecut_images.all().count()),
               str(product_obj.aplus_content_images.all().count()),
               str(product_obj.ads_images.all().count()),
               str(product_obj.unedited_images.all().count()),
               str(product_obj.pfl_generated_images.all().count())]

        data_row = []
        indexx = 0
        for k in row:
            indexx += 1
            l = k.encode('utf-8').strip()
            try:
                if indexx>4:
                    if int(l)>0:
                        l = "1"
                    else:
                        l = "0"
            except Exception as e:
                pass
            data_row.append(l)
        writer.writerow(data_row)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error pk:", product_obj.pk, str(e), str(exc_tb.tb_lineno))

fw.close()


##########################################################################


fw = open("./files/csv/report-1-form.csv", mode='w')
writer = csv.writer(fw,
                    delimiter=',',
                    quotechar='"',
                    quoting=csv.QUOTE_MINIMAL)


row = ["Sr. No.",
       "Product ID",
       "Product Name",
       "Brand",
       "product_name_sap",
       "product_name_amazon_uk",
       "product_name_amazon_uae",
       "product_name_ebay",

       "product_id",
       "product_id_type",
       "seller_sku",
       "category",
       "subtitle",
       "brand",
       "manufacturer",
       "manufacturer_part_number",
       "condition_type",
       "feed_product_type",
       "update_delete",
       "recommended_browse_nodes",

       "product_description_amazon_uk",
       "product_description_amazon_uae",
       "product_description_ebay",
       "product_attribute_list_amazon_uk",
       "product_attribute_list_amazon_uae",
       "product_attribute_list_ebay",
       "search_terms",
       "color_map",
       "color",
       "enclosure_material",
       "cover_material_type",
       "special_features",

       "package_length",
       "package_length_metric",
       "package_width",
       "package_width_metric",
       "package_height",
       "package_height_metric",
       "package_weight",
       "package_weight_metric",
       "shipping_weight",
       "shipping_weight_metric",
       "item_display_weight",
       "item_display_weight_metric",
       "item_display_volume",
       "item_display_volume_metric",
       "item_display_length",
       "item_display_length_metric",
       "item_weight",
       "item_weight_metric",
       "item_length",
       "item_length_metric",
       "item_width = False",
       "item_width_metric",
       "item_height",
       "item_height_metric",
       "item_display_width",
       "item_display_width_metric",
       "item_display_height",
       "item_display_height_metric",

       "item_condition_note",
       "max_order_quantity",
       "number_of_items",
       "wattage",
       "wattage_metric",
       "material_type",

       "parentage",
       "parent_sku",
       "relationship_type",
       "variation_theme",

       "standard_price",
       "quantity",
       "sale_price",
       "sale_from",
       "sale_end",

       "barcode",
       "barcode_string",
       "outdoor_price",

       "pfl_product_features"]

writer.writerow(row)

cnt = 0
for product_obj in product_objs:
    try:
        break
        #if product_obj.brand==None or str(product_obj.brand.organization)=="Nesto":
        #    continue
        cnt += 1
        print("Cnt: ", cnt)
        # Vital
        product_name_sap = False if product_obj.product_name_sap == "" else True
        product_name_amazon_uk = False if product_obj.product_name_amazon_uk == "" else True
        product_name_amazon_uae = False if product_obj.product_name_amazon_uae == "" else True
        product_name_ebay = False if product_obj.product_name_ebay == "" else True

        product_id = False if product_obj.product_id == "" else True
        product_id_type = False if product_obj.product_id_type == "" else True
        seller_sku = False if product_obj.seller_sku == "" else True
        category = False if product_obj.category == "" else True
        subtitle = False if product_obj.subtitle == "" else True
        brand = False if product_obj.brand == None else True
        manufacturer = False if product_obj.manufacturer == "" else True
        manufacturer_part_number = False if product_obj.manufacturer_part_number == "" else True
        condition_type = False if product_obj.condition_type == "" else True
        feed_product_type = False if product_obj.feed_product_type == "" else True
        update_delete = False if product_obj.update_delete == "" else True
        recommended_browse_nodes = False if product_obj.recommended_browse_nodes == "" else True

        # Information
        product_description_amazon_uk = False if product_obj.product_description_amazon_uk == "" else True
        product_description_amazon_uae = False if product_obj.product_description_amazon_uae == "" else True
        product_description_ebay = False if product_obj.product_description_ebay == "" else True

        product_attribute_list_amazon_uk = False if product_obj.product_attribute_list_amazon_uk == "[]" else True
        product_attribute_list_amazon_uae = False if product_obj.product_attribute_list_amazon_uae == "[]" else True
        product_attribute_list_ebay = False if product_obj.product_attribute_list_ebay == "[]" else True

        search_terms = False if product_obj.search_terms == "" else True
        color_map = False if product_obj.color_map == "" else True
        color = False if product_obj.color == "" else True
        enclosure_material = False if product_obj.enclosure_material == "" else True
        cover_material_type = False if product_obj.cover_material_type == "" else True
        special_features = False if product_obj.special_features == "[]" else True

        # Dimensions
        package_length = False if product_obj.package_length == None else True
        package_length_metric = False if product_obj.package_length_metric == "" else True
        package_width = False if product_obj.package_width == None else True
        package_width_metric = False if product_obj.package_width_metric == "" else True
        package_height = False if product_obj.package_height == None else True
        package_height_metric = False if product_obj.package_height_metric == "" else True
        package_weight = False if product_obj.package_weight == None else True
        package_weight_metric = False if product_obj.package_weight_metric == "" else True
        shipping_weight = False if product_obj.shipping_weight == None else True
        shipping_weight_metric = False if product_obj.shipping_weight_metric == "" else True
        item_display_weight = False if product_obj.item_display_weight == None else True
        item_display_weight_metric = False if product_obj.item_display_weight_metric == "" else True
        item_display_volume = False if product_obj.item_display_volume == None else True
        item_display_volume_metric = False if product_obj.item_display_volume_metric == "" else True
        item_display_length = False if product_obj.item_display_length == None else True
        item_display_length_metric = False if product_obj.item_display_length_metric == "" else True
        item_weight = False if product_obj.item_weight == None else True
        item_weight_metric = False if product_obj.item_weight_metric == "" else True
        item_length = False if product_obj.item_length == None else True
        item_length_metric = False if product_obj.item_length_metric == "" else True
        item_width = False if product_obj.item_width == None else True
        item_width_metric = False if product_obj.item_width_metric == "" else True
        item_height = False if product_obj.item_height == None else True
        item_height_metric = False if product_obj.item_height_metric == "" else True
        item_display_width = False if product_obj.item_display_width == None else True
        item_display_width_metric = False if product_obj.item_display_width_metric == "" else True
        item_display_height = False if product_obj.item_display_height == None else True
        item_display_height_metric = False if product_obj.item_display_height_metric == "" else True

        # Attributes
        item_condition_note = False if product_obj.item_condition_note == "" else True
        max_order_quantity = False if product_obj.max_order_quantity == None else True
        number_of_items = False if product_obj.number_of_items == None else True
        wattage = False if product_obj.wattage == None else True
        wattage_metric = False if product_obj.wattage_metric == "" else True
        material_type = False if product_obj.material_type == "" else True

        # Variation
        parentage = False if product_obj.parentage == "" else True
        parent_sku = False if product_obj.parent_sku == "" else True
        relationship_type = False if product_obj.relationship_type == "" else True
        variation_theme = False if product_obj.variation_theme == "" else True

        # Offer
        standard_price = False if product_obj.standard_price == None else True
        quantity = False if product_obj.quantity == None else True
        sale_price = False if product_obj.sale_price == None else True
        sale_from = False if product_obj.sale_from == "" else True
        sale_end = False if product_obj.sale_end == "" else True

        # Other info
        barcode = False if product_obj.barcode == None else True
        barcode_string = False if product_obj.barcode_string == "" else True
        outdoor_price = False if product_obj.outdoor_price == "" else True

        pfl_product_features = False if product_obj.pfl_product_features == "[]" else True

        row = [str(cnt),
               str(product_obj.product_id),
               product_obj.product_name_sap,
               str(product_obj.brand),
               str(product_name_sap),
               str(product_name_amazon_uk),
               str(product_name_amazon_uae),
               str(product_name_ebay),

               str(product_id),
               str(product_id_type),
               str(seller_sku),
               str(category),
               str(subtitle),
               str(brand),
               str(manufacturer),
               str(manufacturer_part_number),
               str(condition_type),
               str(feed_product_type),
               str(update_delete),
               str(recommended_browse_nodes),

               str(product_description_amazon_uk),
               str(product_description_amazon_uae),
               str(product_description_ebay),
               str(product_attribute_list_amazon_uk),
               str(product_attribute_list_amazon_uae),
               str(product_attribute_list_ebay),
               str(search_terms),
               str(color_map),
               str(color),
               str(enclosure_material),
               str(cover_material_type),
               str(special_features),

               str(package_length),
               str(package_length_metric),
               str(package_width),
               str(package_width_metric),
               str(package_height),
               str(package_height_metric),
               str(package_weight),
               str(package_weight_metric),
               str(shipping_weight),
               str(shipping_weight_metric),
               str(item_display_weight),
               str(item_display_weight_metric),
               str(item_display_volume),
               str(item_display_volume_metric),
               str(item_display_length),
               str(item_display_length_metric),
               str(item_weight),
               str(item_weight_metric),
               str(item_length),
               str(item_length_metric),
               str(item_width),
               str(item_width_metric),
               str(item_height),
               str(item_height_metric),
               str(item_display_width),
               str(item_display_width_metric),
               str(item_display_height),
               str(item_display_height_metric),

               str(item_condition_note),
               str(max_order_quantity),
               str(number_of_items),
               str(wattage),
               str(wattage_metric),
               str(material_type),

               str(parentage),
               str(parent_sku),
               str(relationship_type),
               str(variation_theme),

               str(standard_price),
               str(quantity),
               str(sale_price),
               str(sale_from),
               str(sale_end),

               str(barcode),
               str(barcode_string),
               str(outdoor_price),

               str(pfl_product_features)]
        
        data_row = []
        for k in row:
            l = k.encode('utf-8').strip()
            if l=="True":
                l = "1"
            elif l=="False":
                l = "0"
            data_row.append(l)
        writer.writerow(data_row)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error pk:", product_obj.pk, str(e), str(exc_tb.tb_lineno))

fw.close()

