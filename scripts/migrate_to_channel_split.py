from WAMSApp.models import *
import json
import urllib2

f = open("scripts/17012020.json", "r")
all_data_json = json.loads(f.read())
f.close()


Channel.objects.create(name="Amazon UK")
Channel.objects.create(name="Amazon UAE")
Channel.objects.create(name="Ebay")
Channel.objects.create(name="Noon")

MainImages.objects.create(is_sourced=True)
SubImages.objects.create(is_sourced=True)




image_pk_mapping = {}
image_cnt=0

for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.image":
            image_cnt+=1
            image_obj = Image.objects.create(image=data["fields"]["image"],
                                             mid_image=data["fields"]["mid_image"],
                                             thumbnail=data["fields"]["thumbnail"],
                                             description=data["fields"]["description"]
                                             )
            image_pk_mapping[data["pk"]] = image_obj.pk
            print("Image Cnt:", image_cnt)
    except Exception as e:
        print("Error Image", str(e))

organization_pk_mapping = {}
organization_cnt=0

for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.organization":
            organization_cnt+=1
            organization_obj = Organization.objects.create(name=data["fields"]["name"])
            organization_pk_mapping[data["pk"]] = organization_obj.pk
            print("Organization Cnt:", organization_cnt)
    except Exception as e:
        print("Error Organization", str(e))

brand_pk_mapping = {}
brand_cnt=0

for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.brand":
            brand_cnt+=1

            logo_pk = data["fields"]["logo"]["pk"]
            mapped_pk = image_pk_mapping[logo_pk]
            logo_obj = Image.objects.get(pk = mapped_pk)
            organization_pk = data["fields"]["organization"]["pk"]
            organization_mapped_pk = image_pk_mapping[organization_pk]
            organization_obj = Organization.objects.get(pk = organization_mapped_pk)

            brand_obj = Brand.objects.create(name=data["fields"]["name"],
                                             logo = logo_obj,
                                             organization=organization_obj
                                             )

            brand_pk_mapping[data["pk"]] = brand_obj.pk
            print("Brand Cnt:", brand_cnt)
    except Exception as e:
        print("Error Brnad", str(e))


category_pk_mapping = {}
category_cnt=0

for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.category":
            category_cnt+=1
            category_obj = Category.objects.create(name=data["fields"]["name"])
            category_pk_mapping[data["pk"]] = category_obj.pk
            print("Category Cnt:", category_cnt)
    except Exception as e:
        print("Error Category", str(e))

background_image_pk_mapping ={}
background_image_cnt=0

for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.backgroundimage":
            background_image_cnt+=1
            
            image_pk = data["fields"]["image"]["pk"]
            mapped_pk = image_pk_mapping[image_pk]
            image_obj = Image.objects.get(pk=mapped_pk)
            
            background_image_obj = BackgroundImage.objects.create(image=image_obj)
            background_image_pk_mapping[data["pk"]] = background_image_obj.pk
            
            print("Background Image Cnt:", background_image_cnt)
    except Exception as e:
        print("Error Background Image", str(e))

image_bucket_pk_mapping = {}
image_bucket_cnt=0

for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.imagebucket":
            image_bucket_cnt+=1
            
            image_pk = data["fields"]["image"]["pk"]
            mapped_pk = image_pk_mapping[image_pk]
            image_obj = Image.objects.get(pk=mapped_pk)
            description = data["fields"]["image"]["description"]
            is_main_image = data["fields"]["image"]["is_main_image"]
            is_sub_image = data["fields"]["image"]["is_sub_image"]
            sub_image_index = data["fields"]["image"]["sub_image_index"]
            
            image_bucket_obj = ImageBucket.objects.create(image=image_obj,
                                                          description=description,
                                                          is_main_image=is_main_image,
                                                          is_sub_image=is_sub_image,
                                                          sub_image_index=sub_image_index
                                                          )
            image_bucket_pk_mapping[data["pk"]] = image_bucket_obj.pk
            print("Image Bucket Cnt:", image_bucket_cnt)
    except Exception as e:
        print("Error Image Bucket", str(e))

product_pk_mapping = {}
product_cnt=0

for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.product":
            product_cnt+=1
            
            created_date = datetime.datetime.strptime(
                    data["fields"]["created_date"][:19], "%b %d, %Y")
            status = data["fields"]["status"]
            verified = data["fields"]["verified"]
            pfl_product_features = data["fields"]["pfl_product_features"]
            
            product_name_sap = data["fields"]["product_name_sap"]
            product_name_amazon_uk = data["fields"]["product_name_amazon_uk"]
            product_name_amazon_uae = data["fields"]["product_name_amazon_uae"]
            product_name_ebay = data["fields"]["product_name_ebay"]
            product_name_noon = data["fields"]["product_name_noon"]
            
            product_id = data["fields"]["product_id"]
            product_id_type = data["fields"]["product_id_type"]
            seller_sku = data["fields"]["seller_sku"]
            category = data["fields"]["category"]
            subtitle = data["fields"]["subtitle"]
            manufacturer = data["fields"]["manufacturer"]
            manufacturer_part_number = data["fields"]["manufacturer_part_number"]
            
            condition_type = data["fields"]["condition_type"]
            feed_product_type = data["fields"]["feed_product_type"]
            update_delete = data["fields"]["update_delete"]
            recommended_browse_nodes = data["fields"]["recommended_browse_nodes"]
            search_terms = data["fields"]["search_terms"]
            color_map = data["fields"]["color_map"]
            color = data["fields"]["color"]
            enclosure_material = data["fields"]["enclosure_material"]
            cover_material_type = data["fields"]["cover_material_type"]
            special_features = data["fields"]["special_features"]
            
            noon_product_type = data["fields"]["noon_product_type"]
            noon_product_subtype = data["fields"]["noon_product_subtype"]
            noon_model_number = data["fields"]["noon_model_number"]
            noon_model_name = data["fields"]["noon_model_name"]
            noon_msrp_ae = data["fields"]["noon_msrp_ae"]
            noon_msrp_ae_unit = data["fields"]["noon_msrp_ae_unit"]
            
            product_description_amazon_uk = data["fields"]["product_description_amazon_uk"]
            product_description_amazon_uae = data["fields"]["product_description_amazon_uae"]
            product_description_ebay = data["fields"]["product_description_ebay"]
            product_description_noon = data["fields"]["product_description_noon"]
            
            product_attribute_list_amazon_uk = data["fields"]["product_attribute_list_amazon_uk"]
            product_attribute_list_amazon_uae = data["fields"]["product_attribute_list_amazon_uae"]
            product_attribute_list_ebay = data["fields"]["product_attribute_list_ebay"]
            product_attribute_list_noon = data["fields"]["product_attribute_list_noon"]
            
            package_length = data["fields"]["package_length"]
            package_length_metric = data["fields"]["package_length_metric"]
            package_width = data["fields"]["package_width"]
            package_width_metric = data["fields"]["package_width_metric"]
            package_height = data["fields"]["package_height"]
            package_height_metric = data["fields"]["package_height_metric"]
            package_weight = data["fields"]["package_weight"]
            package_weight_metric = data["fields"]["package_weight_metric"]
            shipping_weight = data["fields"]["shipping_weight"]
            shipping_weight_metric = data["fields"]["shipping_weight_metric"]
            item_display_weight = data["fields"]["item_display_weight"]
            item_display_weight_metric = data["fields"]["item_display_weight_metric"]
            item_display_volume = data["fields"]["item_display_volume"]
            item_display_volume_metric = data["fields"]["item_display_volume_metric"]
            item_display_length = data["fields"]["item_display_length"]
            item_display_length_metric = data["fields"]["item_display_length_metric"]
            item_weight = data["fields"]["item_weight"]
            item_weight_metric = data["fields"]["item_weight_metric"]
            item_length = data["fields"]["item_length"]
            item_length_metric = data["fields"]["item_length_metric"]
            item_width = data["fields"]["item_width"]
            item_width_metric = data["fields"]["item_width_metric"]
            item_height = data["fields"]["item_height"]
            item_height_metric = data["fields"]["item_height_metric"]
            item_display_width = data["fields"]["item_display_width"]
            item_display_width_metric = data["fields"]["item_display_width_metric"]
            item_display_height = data["fields"]["item_display_height"]
            item_display_height_metric = data["fields"]["item_display_height_metric"]
            
            item_count = data["fields"]["item_count"]
            item_count_metric = data["fields"]["item_count_metric"]
            item_condition_note = data["fields"]["item_condition_note"]
            max_order_quantity = data["fields"]["max_order_quantity"]
            number_of_items = data["fields"]["number_of_items"]
            wattage = data["fields"]["wattage"]
            wattage_metric = data["fields"]["wattage_metric"]
            material_type = data["fields"]["material_type"]
            
            parentage = data["fields"]["parentage"]
            parent_sku = data["fields"]["parent_sku"]
            relationship_type = data["fields"]["relationship_type"]
            variation_theme = data["fields"]["variation_theme"]
            
            standard_price = data["fields"]["standard_price"]
            quantity = data["fields"]["quantity"]
            sale_price = data["fields"]["sale_price"]
            sale_from = data["fields"]["sale_from"]
            sale_end = data["fields"]["sale_end"]
            
            factory_notes = data["fields"]["factory_notes"]
            barcode_string = data["fields"]["barcode_string"]
            outdoor_price = data["fields"]["outdoor_price"]
            
            barcode_pk = data["fields"]["barcode"]["pk"]
            barcode_mapped_pk = image_pk_mapping[barcode_pk]
            barcode_obj = Image.objects.get(pk=barcode_mapped_pk)

            brand_pk = data["fields"]["brand"]["pk"]
            brand_mapped_pk = brand_pk_mapping[brand_pk]
            brand_obj = Brand.objects.get(pk=brand_mapped_pk)

            main_images = data["fields"]["main_images"]
            main_image_buckets = []
            for main_image in main_images:
                image_bucket_pk = main_image["pk"]
                mapped_image_bucket_pk = image_bucket_pk_mapping[image_bucket_pk]
                image_bucket_obj = ImageBucket.objects.get(pk=mapped_image_bucket_pk)
                main_image_buckets.append(image_bucket_obj)
            
            sub_images = data["fields"]["sub_images"]
            sub_image_buckets = []
            for sub_image in sub_images:
                image_bucket_pk = sub_image["pk"]
                mapped_image_bucket_pk = image_bucket_pk_mapping[image_bucket_pk]
                image_bucket_obj = ImageBucket.objects.get(pk=mapped_image_bucket_pk)
                sub_image_buckets.append(image_bucket_obj)            


            pfl_images = data["fields"]["pfl_images"]
            white_background_images = data["fields"]["white_background_images"]
            lifestyle_images = data["fields"]["lifestyle_images"]
            certificate_images = data["fields"]["certificate_images"]
            giftbox_images = data["fields"]["giftbox_images"]
            diecut_images = data["fields"]["diecut_images"]
            aplus_content_images = data["fields"]["aplus_content_images"]
            ads_images = data["fields"]["ads_images"]
            unedited_images = data["fields"]["unedited_images"]
            pfl_generated_images = data["fields"]["pfl_generated_images"]
            transparent_images = data["fields"]["transparent_images"]





            print("Product Cnt:", product_cnt)
    except Exception as e:
        print("Error Product Bucket", str(e))