from WAMSApp.models import *
import csv
import json
import sys



def create_image_list(images):
    import json
    images_list = []
    for image in images:
        images_list.append(image.image.url)
    return json.dumps(images_list)



product_objs = Product.objects.all()

fw = open("./files/csv/product-copy-images.csv", mode='w')
writer = csv.writer(fw,
                    delimiter=',',
                    quotechar='"',
                    quoting=csv.QUOTE_MINIMAL)

row = ["Sr. No.",
       "Product ID",
       "Product Name",
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


        main_images = product_obj.main_images.all()
        main_images_list = []
        for image in main_images:
            main_images_list.append(image.image.image.url)
        main_images_list = json.dumps(main_images_list)

        sub_images = product_obj.sub_images.all()
        sub_images_list = []
        for image in sub_images:
            sub_images_list.append(image.image.image.url)
        sub_images_list = json.dumps(sub_images_list)

        pfl_images_list = create_image_list(product_obj.pfl_images.all())
        white_background_images_list = create_image_list(product_obj.white_background_images.all())
        lifestyle_images_list = create_image_list(product_obj.lifestyle_images.all())
        certificate_images_list = create_image_list(product_obj.certificate_images.all())
        giftbox_images_list = create_image_list(product_obj.giftbox_images.all())
        diecut_images_list = create_image_list(product_obj.diecut_images.all())
        aplus_content_images_list = create_image_list(product_obj.aplus_content_images.all())
        ads_images_list = create_image_list(product_obj.ads_images.all())
        unedited_images_list = create_image_list(product_obj.unedited_images.all())
        pfl_generated_images_list = create_image_list(product_obj.pfl_generated_images.all())


        row = [str(cnt),
               str(product_obj.product_id),
               product_obj.product_name_sap,
               str(main_images_list),
               str(sub_images_list),
               str(pfl_images_list),
               str(white_background_images_list),
               str(lifestyle_images_list),
               str(certificate_images_list),
               str(giftbox_images_list),
               str(diecut_images_list),
               str(aplus_content_images_list),
               str(ads_images_list),
               str(unedited_images_list),
               str(pfl_generated_images_list)]

        data_row = []
        for k in row:
            l = k.encode('utf-8').strip()
            data_row.append(l)
        #writer.writerow(data_row)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error pk:", product_obj.pk, str(exc_tb.tb_lineno), str(e))

fw.close()


##########################################################################


fw = open("./files/csv/product-copy-form.csv", mode='w')
writer = csv.writer(fw,
                    delimiter=',',
                    quotechar='"',
                    quoting=csv.QUOTE_MINIMAL)


row = ["Sr. No.",
       "Product ID",
       "Product Name",
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

       "barcode_string",
       "outdoor_price",

       "pfl_product_features"]

writer.writerow(row)

cnt = 0
for product_obj in product_objs:
    try:
        cnt += 1

        # Vital
        product_name_sap = product_obj.product_name_sap
        product_name_amazon_uk = product_obj.product_name_amazon_uk
        product_name_amazon_uae = product_obj.product_name_amazon_uae
        product_name_ebay = product_obj.product_name_ebay

        product_id = product_obj.product_id
        product_id_type = product_obj.product_id_type
        seller_sku = product_obj.seller_sku
        category = product_obj.category
        subtitle = product_obj.subtitle
        brand = "-" if product_obj.brand==None else product_obj.brand.name 
        manufacturer = product_obj.manufacturer
        manufacturer_part_number = product_obj.manufacturer_part_number
        condition_type = product_obj.condition_type
        feed_product_type = product_obj.feed_product_type
        update_delete = product_obj.update_delete
        recommended_browse_nodes = product_obj.recommended_browse_nodes

        # Information
        product_description_amazon_uk = product_obj.product_description_amazon_uk
        product_description_amazon_uae = product_obj.product_description_amazon_uae
        product_description_ebay = product_obj.product_description_ebay

        product_attribute_list_amazon_uk = product_obj.product_attribute_list_amazon_uk
        product_attribute_list_amazon_uae = product_obj.product_attribute_list_amazon_uae
        product_attribute_list_ebay = product_obj.product_attribute_list_ebay

        search_terms = product_obj.search_terms
        color_map = product_obj.color_map
        color = product_obj.color
        enclosure_material = product_obj.enclosure_material
        cover_material_type = product_obj.cover_material_type
        special_features = product_obj.special_features

        # Dimensions
        package_length = "" if product_obj.package_length==None else str(product_obj.package_length)
        package_length_metric = product_obj.package_length_metric
        package_width = "" if product_obj.package_width==None else str(product_obj.package_width)
        package_width_metric = product_obj.package_width_metric
        package_height = "" if product_obj.package_height==None else str(product_obj.package_height) 
        package_height_metric = product_obj.package_height_metric
        package_weight = "" if product_obj.package_weight==None else str(product_obj.package_weight) 
        package_weight_metric = product_obj.package_weight_metric
        shipping_weight = "" if product_obj.shipping_weight==None else str(product_obj.shipping_weight) 
        shipping_weight_metric = product_obj.shipping_weight_metric
        item_display_weight = "" if product_obj.item_display_weight==None else str(product_obj.item_display_weight) 
        item_display_weight_metric = product_obj.item_display_weight_metric
        item_display_volume = "" if product_obj.item_display_volume==None else str(product_obj.item_display_volume) 
        item_display_volume_metric = product_obj.item_display_volume_metric
        item_display_length = "" if product_obj.item_display_length==None else str(product_obj.item_display_length) 
        item_display_length_metric = product_obj.item_display_length_metric
        item_weight = "" if product_obj.item_weight==None else str(product_obj.item_weight) 
        item_weight_metric = product_obj.item_weight_metric
        item_length = "" if product_obj.item_length==None else str(product_obj.item_length) 
        item_length_metric = product_obj.item_length_metric
        item_width = "" if product_obj.item_width==None else str(product_obj.item_width) 
        item_width_metric = product_obj.item_width_metric
        item_height = "" if product_obj.item_height==None else str(product_obj.item_height) 
        item_height_metric = product_obj.item_height_metric
        item_display_width = "" if product_obj.item_display_width==None else str(product_obj.item_display_width) 
        item_display_width_metric = product_obj.item_display_width_metric
        item_display_height = "" if product_obj.item_display_height==None else str(product_obj.item_display_height) 
        item_display_height_metric = product_obj.item_display_height_metric

        # Attributes
        item_condition_note = product_obj.item_condition_note
        max_order_quantity = "" if product_obj.max_order_quantity==None else str(product_obj.max_order_quantity)
        number_of_items = "" if product_obj.number_of_items==None else str(product_obj.number_of_items) 
        wattage = "" if product_obj.wattage==None else str(product_obj.wattage) 
        wattage_metric = product_obj.wattage_metric
        material_type = product_obj.material_type

        # Variation
        parentage = product_obj.parentage
        parent_sku = product_obj.parent_sku
        relationship_type = product_obj.relationship_type
        variation_theme = product_obj.variation_theme

        # Offer
        standard_price = "" if product_obj.standard_price==None else str(product_obj.standard_price) 
        quantity = "" if product_obj.quantity==None else str(product_obj.quantity) 
        sale_price = "" if product_obj.sale_price==None else str(product_obj.sale_price) 
        sale_from = str(product_obj.sale_from)
        sale_end = str(product_obj.sale_end)

        # Other info
        barcode_string = product_obj.barcode_string
        outdoor_price = "" if product_obj.outdoor_price==None else str(product_obj.outdoor_price)

        pfl_product_features = product_obj.pfl_product_features

        row = [str(cnt),
               str(product_obj.product_id),
               product_obj.product_name_sap,
               product_name_sap,
               product_name_amazon_uk,
               product_name_amazon_uae,
               product_name_ebay,

               product_id,
               product_id_type,
               seller_sku,
               category,
               subtitle,
               brand,
               manufacturer,
               manufacturer_part_number,
               condition_type,
               feed_product_type,
               update_delete,
               recommended_browse_nodes,

               product_description_amazon_uk,
               product_description_amazon_uae,
               product_description_ebay,
               product_attribute_list_amazon_uk,
               product_attribute_list_amazon_uae,
               product_attribute_list_ebay,
               search_terms,
               color_map,
               color,
               enclosure_material,
               cover_material_type,
               special_features,

               package_length,
               package_length_metric,
               package_width,
               package_width_metric,
               package_height,
               package_height_metric,
               package_weight,
               package_weight_metric,
               shipping_weight,
               shipping_weight_metric,
               item_display_weight,
               item_display_weight_metric,
               item_display_volume,
               item_display_volume_metric,
               item_display_length,
               item_display_length_metric,
               item_weight,
               item_weight_metric,
               item_length,
               item_length_metric,
               item_width,
               item_width_metric,
               item_height,
               item_height_metric,
               item_display_width,
               item_display_width_metric,
               item_display_height,
               item_display_height_metric,

               item_condition_note,
               max_order_quantity,
               number_of_items,
               wattage,
               wattage_metric,
               material_type,

               parentage,
               parent_sku,
               relationship_type,
               variation_theme,

               standard_price,
               quantity,
               sale_price,
               sale_from,
               sale_end,

               barcode_string,
               outdoor_price,

               pfl_product_features]
       
        len_row = len(row)
        data_row = []
        for k in row:
            l = k.encode('utf-8').strip()
            data_row.append(l)
        len_data_row = len(data_row)
        if len_row!=len_data_row:
            print("Mismatch error!")
        #writer.writerow(data_row)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error pk:", product_obj.pk, str(exc_tb.tb_lineno), str(e))

fw.close()

