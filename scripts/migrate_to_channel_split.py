from WAMSApp.models import *
from dealshub.models import *
import json
import urllib.request, urllib.error, urllib.parse
import datetime
import os

f = open("scripts/06032020.json", "r")
all_data_json = json.loads(f.read())
f.close()

image_pk_mapping = {}
if os.path.exists("files/i1mage_pk_mapping.txt"):
    f_image = open("files/image_pk_mapping.txt","r")
    temp = json.loads(f_image.read())
    for key in image_pk_mapping:
        image_pk_mapping[int(key)] = int(image_pk_mapping[key])
    f_image.close()
else:
    image_cnt=0
    for data in all_data_json:
        
        try:
            if data["model"] == "WAMSApp.image":
                image_cnt+=1
                image_obj, created = Image.objects.get_or_create(image=data["fields"]["image"],
                                                 mid_image=data["fields"]["mid_image"],
                                                 thumbnail=data["fields"]["thumbnail"],
                                                 description=data["fields"]["description"]
                                                 )
                image_pk_mapping[data["pk"]] = image_obj.pk
                #print("Image Cnt:", image_cnt)
                #if image_cnt%1000==0:
                print(("Image Cnt:", image_cnt))
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(("Error Image %s at %s", str(e), str(exc_tb.tb_lineno)))

    f_image = open("files/image_pk_mapping.txt","w")
    image_pk_mapping_json = json.dumps(image_pk_mapping)
    f_image.write(image_pk_mapping_json)
    f_image.close()


organization_pk_mapping = {}
organization_cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.organization":
            organization_cnt+=1
            organization_obj, created = Organization.objects.get_or_create(name=data["fields"]["name"])
            organization_pk_mapping[int(data["pk"])] = int(organization_obj.pk)
            print(("Organization Cnt:", organization_cnt))
    except Exception as e:
        print(("Error Organization", str(e)))


brand_pk_mapping = {}
brand_cnt=0

for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.brand":
            brand_cnt+=1

            logo_pk = data["fields"]["logo"]
            logo_obj = None
            if logo_pk!=None:
                logo_pk = int(logo_pk)
                mapped_pk = image_pk_mapping[logo_pk]
                logo_obj = Image.objects.get(pk = mapped_pk)

            organization_pk = data["fields"]["organization"]
            organization_obj = None
            if organization_pk!=None:
                organization_pk = int(organization_pk)
                organization_mapped_pk = organization_pk_mapping[organization_pk]
                organization_obj = Organization.objects.get(pk = organization_mapped_pk)

            brand_obj, created = Brand.objects.get_or_create(name=data["fields"]["name"],
                                             logo = logo_obj,
                                             organization=organization_obj
                                             )

            brand_pk_mapping[int(data["pk"])] = int(brand_obj.pk)
            if brand_cnt%1000==0:
                print(("Brand Cnt:", brand_cnt))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error in Brand %s at %s", str(e), str(exc_tb.tb_lineno)))


f_brand = open("files/brand_pk_mapping.txt","w")
brand_pk_mapping_json = json.dumps(brand_pk_mapping)
f_brand.write(brand_pk_mapping_json)
f_brand.close()

category_pk_mapping = {}
category_cnt=0

for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.category":
            category_cnt+=1
            category_obj, created = Category.objects.get_or_create(name=data["fields"]["name"])
            category_pk_mapping[int(data["pk"])] = int(category_obj.pk)
            if category_cnt%1000==0:
                print(("Category Cnt:", category_cnt))
    except Exception as e:
        print(("Error Category", str(e)))

f_category = open("files/category_pk_mapping.txt","w")
category_pk_mapping_json = json.dumps(category_pk_mapping)
f_category.write(category_pk_mapping_json)
f_category.close()

background_image_pk_mapping ={}
background_image_cnt=0

for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.backgroundimage":
            background_image_cnt+=1
            
            image_pk = data["fields"]["image"]
            image_obj = None
            if image_pk!=None:
                image_pk = int(image_pk)
                mapped_pk = image_pk_mapping[image_pk]
                image_obj = Image.objects.get(pk=mapped_pk)
            
            background_image_obj, created = BackgroundImage.objects.get_or_create(image=image_obj)
            background_image_pk_mapping[int(data["pk"])] = int(background_image_obj.pk)
            
            print(("Background Image Cnt:", background_image_cnt))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error Background Image %s at %s", str(e), str(exc_tb.tb_lineno)))

f_background_image = open("files/background_image_pk_mapping.txt","w")
background_image_pk_mapping_json = json.dumps(background_image_pk_mapping)
f_background_image.write(background_image_pk_mapping_json)
f_background_image.close()

image_bucket_pk_mapping = {}
image_bucket_cnt=0

for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.imagebucket":
            image_bucket_cnt+=1
            
            image_pk = int(data["fields"]["image"])
            mapped_pk = image_pk_mapping[image_pk]
            image_obj = Image.objects.get(pk=mapped_pk)

            description = data["fields"]["description"]
            is_main_image = data["fields"]["is_main_image"]
            is_sub_image = data["fields"]["is_sub_image"]
            sub_image_index = data["fields"]["sub_image_index"]
            
            image_bucket_obj, created = ImageBucket.objects.get_or_create(image=image_obj,
                                                          description=description,
                                                          is_main_image=is_main_image,
                                                          is_sub_image=is_sub_image,
                                                          sub_image_index=sub_image_index
                                                          )
            image_bucket_pk_mapping[int(data["pk"])] = int(image_bucket_obj.pk)
            if image_bucket_cnt%1000==0:
                print(("Image Bucket Cnt:", image_bucket_cnt))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error in Image Bucket %s at %s", str(e), str(exc_tb.tb_lineno)))

f_image_bucket = open("files/image_bucket_pk_mapping.txt","w")
image_bucket_pk_mapping_json = json.dumps(image_bucket_pk_mapping)
f_image_bucket.write(image_bucket_pk_mapping_json)
f_image_bucket.close()

product_pk_mapping = {}
product_cnt=0

seller_sku_dict = {}
for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.product":
            product_cnt+=1

            seller_sku = data["fields"]["seller_sku"]

            if seller_sku=="":
                seller_sku = "UNDEFINED_"+str(product_cnt)

            if seller_sku not in seller_sku_dict:
                seller_sku_dict[seller_sku] = 1
            else:
                seller_sku_dict[seller_sku] += 1
                continue
            
            created_date = datetime.datetime.now().strftime("%Y-%m-%d")

            try:
                created_date = datetime.datetime.strptime(
                    data["fields"]["created_date"][:10], "%Y-%m-%d")
            except Exception as e:
                print(str(e))
                pass

            status = data["fields"]["status"]
            verified = data["fields"]["verified"]
            pfl_product_name = data["fields"]["pfl_product_name"]
            pfl_product_features = data["fields"]["pfl_product_features"]
            
            product_name_sap = data["fields"]["product_name_sap"]
            product_name_amazon_uk = data["fields"]["product_name_amazon_uk"]
            product_name_amazon_uae = data["fields"]["product_name_amazon_uae"]
            product_name_ebay = data["fields"]["product_name_ebay"]
            product_name_noon = data["fields"]["product_name_noon"]
            
            product_id = data["fields"]["product_id"]
            product_id_type = data["fields"]["product_id_type"]
            #seller_sku = data["fields"]["seller_sku"]
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
            special_features = json.loads(data["fields"]["special_features"])
            
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
            
            product_attribute_list_amazon_uk = json.loads(data["fields"]["product_attribute_list_amazon_uk"])
            product_attribute_list_amazon_uae = json.loads(data["fields"]["product_attribute_list_amazon_uae"])
            product_attribute_list_ebay = json.loads(data["fields"]["product_attribute_list_ebay"])
            product_attribute_list_noon = json.loads(data["fields"]["product_attribute_list_noon"])
            
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
    
            no_of_images_for_filter = 0

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
            if standard_price!=None:
                standard_price = float(standard_price)
            quantity = data["fields"]["quantity"]
            if quantity!=None:
                quantity = int(quantity)
            sale_price = data["fields"]["sale_price"]
            sale_from = data["fields"]["sale_from"]
            sale_end = data["fields"]["sale_end"]
            
            factory_notes = data["fields"]["factory_notes"]
            barcode_string = data["fields"]["barcode_string"]
            outdoor_price = data["fields"]["outdoor_price"]
            
            barcode_pk = data["fields"]["barcode"]
            barcode_obj = None
            if barcode_pk!=None:
                barcode_mapped_pk = image_pk_mapping[barcode_pk]
                barcode_obj = Image.objects.get(pk=barcode_mapped_pk)


            brand_pk = data["fields"]["brand"]
            brand_obj = None
            if brand_pk!=None:
                brand_mapped_pk = brand_pk_mapping[brand_pk]
                brand_obj = Brand.objects.get(pk=brand_mapped_pk)

            main_images = data["fields"]["main_images"]
            main_image_buckets = []
            for main_image in main_images:
                no_of_images_for_filter += 1
                image_bucket_pk = main_image
                mapped_image_bucket_pk = image_bucket_pk_mapping[image_bucket_pk]
                image_bucket_obj = ImageBucket.objects.get(pk=mapped_image_bucket_pk)
                main_image_buckets.append(image_bucket_obj)
            
            sub_images = data["fields"]["sub_images"]
            sub_image_buckets = []
            for sub_image in sub_images:
                no_of_images_for_filter += 1
                image_bucket_pk = sub_image
                mapped_image_bucket_pk = image_bucket_pk_mapping[image_bucket_pk]
                image_bucket_obj = ImageBucket.objects.get(pk=mapped_image_bucket_pk)
                sub_image_buckets.append(image_bucket_obj)            


            pfl_images = data["fields"]["pfl_images"]
            pfl_images_objs = []
            for pfl_image in pfl_images:
                image_pk = pfl_image
                mapped_pfl_image_pk = image_pk_mapping[image_pk]
                image_obj = Image.objects.get(pk=mapped_pfl_image_pk)
                pfl_images_objs.append(image_obj)
            
            white_background_images = data["fields"]["white_background_images"]
            white_background_images_objs = []
            for white_background_image in white_background_images:
                no_of_images_for_filter += 1
                image_pk = white_background_image
                mapped_white_background_image_pk = image_pk_mapping[image_pk]
                image_obj = Image.objects.get(pk=mapped_white_background_image_pk)
                white_background_images_objs.append(image_obj)

            lifestyle_images = data["fields"]["lifestyle_images"]
            lifestyle_images_objs = []
            for lifestyle_image in lifestyle_images:
                no_of_images_for_filter += 1
                image_pk = lifestyle_image
                mapped_lifestyle_image_pk = image_pk_mapping[image_pk]
                image_obj = Image.objects.get(pk=mapped_lifestyle_image_pk)
                lifestyle_images_objs.append(image_obj)

            certificate_images = data["fields"]["certificate_images"]
            certificate_images_objs = []
            for certificate_image in certificate_images:
                image_pk = certificate_image
                mapped_certificate_image_pk = image_pk_mapping[image_pk]
                image_obj = Image.objects.get(pk=mapped_certificate_image_pk)
                certificate_images_objs.append(image_obj)

            giftbox_images = data["fields"]["giftbox_images"]
            giftbox_images_objs = []
            for giftbox_image in giftbox_images:
                no_of_images_for_filter += 1
                image_pk = giftbox_image
                mapped_giftbox_image_pk = image_pk_mapping[image_pk]
                image_obj = Image.objects.get(pk=mapped_giftbox_image_pk)
                giftbox_images_objs.append(image_obj)

            diecut_images = data["fields"]["diecut_images"]
            diecut_images_objs = []
            for diecut_image in diecut_images:
                image_pk = diecut_image
                mapped_diecut_image_pk = image_pk_mapping[image_pk]
                image_obj = Image.objects.get(pk=mapped_diecut_image_pk)
                diecut_images_objs.append(image_obj)

            aplus_content_images = data["fields"]["aplus_content_images"]
            aplus_content_images_objs = []
            for aplus_content_image in aplus_content_images:
                image_pk = aplus_content_image
                mapped_aplus_content_image_pk = image_pk_mapping[image_pk]
                image_obj = Image.objects.get(pk=mapped_aplus_content_image_pk)
                aplus_content_images_objs.append(image_obj)

            ads_images = data["fields"]["ads_images"]
            ads_images_objs = []
            for ads_image in ads_images:
                image_pk = ads_image
                mapped_ads_image_pk = image_pk_mapping[image_pk]
                image_obj = Image.objects.get(pk=mapped_ads_image_pk)
                ads_images_objs.append(image_obj)

            unedited_images = data["fields"]["unedited_images"]
            unedited_images_objs = []
            for unedited_image in unedited_images:
                image_pk = unedited_image
                mapped_unedited_image_pk = image_pk_mapping[image_pk]
                image_obj = Image.objects.get(pk=mapped_unedited_image_pk)
                unedited_images_objs.append(image_obj)

            pfl_generated_images = data["fields"]["pfl_generated_images"]
            pfl_generated_images_objs = []
            for pfl_generated_image in pfl_generated_images:
                image_pk = pfl_generated_image
                mapped_pfl_generated_image_pk = image_pk_mapping[image_pk]
                image_obj = Image.objects.get(pk=mapped_pfl_generated_image_pk)
                pfl_generated_images_objs.append(image_obj)

            transparent_images = data["fields"]["transparent_images"]
            transparent_images_objs = []
            for transparent_image in transparent_images:
                no_of_images_for_filter += 1
                image_pk = transparent_image
                mapped_transparent_image_pk = image_pk_mapping[image_pk]
                image_obj = Image.objects.get(pk=mapped_transparent_image_pk)
                transparent_images_objs.append(image_obj)

            base_product_obj,created = BaseProduct.objects.get_or_create(seller_sku=seller_sku,
                                                          brand=brand_obj,
                                                          base_product_name=product_name_sap,
                                                          created_date=created_date,
                                                          category=category,
                                                          sub_category=subtitle,
                                                          manufacturer=manufacturer,
                                                          manufacturer_part_number=manufacturer_part_number
                                                          )

            base_dimensions ={}
            base_dimensions_json = {
                "export_carton_quantity_l": "",
                "export_carton_quantity_l_metric": "",
                "export_carton_quantity_b": "",
                "export_carton_quantity_b_metric": "",
                "export_carton_quantity_h": "",
                "export_carton_quantity_h_metric": "",
                "export_carton_crm_l": "",
                "export_carton_crm_l_metric": "",
                "export_carton_crm_b": "",
                "export_carton_crm_b_metric": "",
                "export_carton_crm_h": "",
                "export_carton_crm_h_metric": "",
                "product_dimension_l": item_length,
                "product_dimension_l_metric": item_length_metric,
                "product_dimension_b": item_width,
                "product_dimension_b_metric": item_width_metric,
                "product_dimension_h": item_height,
                "product_dimension_h_metric": item_height_metric,
                "giftbox_l": package_length,
                "giftbox_l_metric": package_length_metric,
                "giftbox_b": package_width,
                "giftbox_b_metric": package_width_metric,
                "giftbox_h": package_height,
                "giftbox_h_metric": package_height_metric
            }

            base_product_obj.dimensions = json.dumps(base_dimensions)

            product_id_type_obj , created = ProductIDType.objects.get_or_create(name=product_id_type)
            material_type_obj , created = MaterialType.objects.get_or_create(name=material_type)

            product_obj,created = Product.objects.get_or_create(base_product=base_product_obj,
                                                 product_name=product_name_sap,
                                                 product_description=product_description_amazon_uk,
                                                 product_id=product_id,
                                                 product_id_type=product_id_type_obj,
                                                 created_date=created_date,
                                                 status=status,
                                                 verified=bool(verified),
                                                 pfl_product_name=pfl_product_name,
                                                 pfl_product_features=pfl_product_features,
                                                 product_name_sap=product_name_sap,
                                                 color_map=color_map,
                                                 color=color,
                                                 standard_price=standard_price,
                                                 quantity=quantity,
                                                 material_type=material_type_obj,
                                                 barcode=barcode_obj,
                                                 barcode_string=barcode_string,
                                                 outdoor_price=outdoor_price,
                                                 no_of_images_for_filter = no_of_images_for_filter,
                                                 factory_notes=factory_notes
                                                 )

            channel_product_obj = product_obj.channel_product

            amazon_uk_product = json.loads(channel_product_obj.amazon_uk_product_json)
            amazon_uae_product = json.loads(channel_product_obj.amazon_uae_product_json)
            ebay_product = json.loads(channel_product_obj.ebay_product_json)
            noon_product = json.loads(channel_product_obj.noon_product_json)

            amazon_uk_product["product_name"] = product_name_amazon_uk
            amazon_uk_product["category"] = category
            amazon_uk_product["sub_category"] = subtitle
            amazon_uk_product["created_date"] = str(created_date)
            amazon_uk_product["condition_type"] = condition_type
            amazon_uk_product["feed_product_type"] = feed_product_type
            amazon_uk_product["update_delete"] = update_delete
            amazon_uk_product["recommended_browse_nodes"] = recommended_browse_nodes
            amazon_uk_product["search_terms"] = search_terms
            amazon_uk_product["enclosure_material"] = enclosure_material
            amazon_uk_product["cover_material_type"] = cover_material_type
            amazon_uk_product["special_features"] = special_features
            amazon_uk_product["product_description"] = product_description_amazon_uk
            if product_description_amazon_uk != None and product_description_amazon_uk != "":
                channel_product_obj.is_amazon_uk_product_created=True
            amazon_uk_product["item_count"] = item_count
            amazon_uk_product["item_count_metric"] = item_count_metric
            amazon_uk_product["item_condition_note"] = item_condition_note
            amazon_uk_product["max_order_quantity"] = max_order_quantity
            amazon_uk_product["number_of_items"] = number_of_items
            amazon_uk_product["wattage"] = wattage
            amazon_uk_product["wattage_metric"] = wattage_metric
            amazon_uk_product["parentage"] = parentage
            amazon_uk_product["parent_sku"] = parent_sku
            amazon_uk_product["relationship_type"] = relationship_type
            amazon_uk_product["variation_theme"] = variation_theme
            amazon_uk_product["sale_price"] = sale_price
            amazon_uk_product["sale_from"] = sale_from
            amazon_uk_product["sale_end"] = sale_end
            amazon_uk_product["product_attribute_list"] = product_attribute_list_amazon_uk
            
            dimensions = {}
            dimensions["package_length"] = package_length
            dimensions["package_length_metric"] = package_length_metric
            dimensions["package_width"] = package_width
            dimensions["package_width_metric"] = package_width_metric
            dimensions["package_height"] = package_height
            dimensions["package_height_metric"] = package_height_metric
            dimensions["package_weight"] = package_weight
            dimensions["package_weight_metric"] = package_weight_metric
            dimensions["shipping_weight"] = shipping_weight
            dimensions["shipping_weight_metric"] = shipping_weight_metric
            dimensions["item_display_weight"] = item_display_weight
            dimensions["item_display_weight_metric"] = item_display_weight_metric
            dimensions["item_display_volume"] = item_display_volume
            dimensions["item_display_volume_metric"] = item_display_volume_metric
            dimensions["item_display_length"] = item_display_length
            dimensions["item_display_length_metric"] = item_display_length_metric
            dimensions["item_weight"] = item_weight
            dimensions["item_weight_metric"] = item_weight_metric
            dimensions["item_length"] = item_length
            dimensions["item_length_metric"] = item_length_metric
            dimensions["item_width"] = package_length
            dimensions["item_width_metric"] = item_width_metric
            dimensions["item_height"] = item_height
            dimensions["item_height_metric"] = item_height_metric
            dimensions["item_display_width"] = item_display_width
            dimensions["item_display_width_metric"] = item_display_width_metric
            dimensions["item_display_height"] = item_display_height
            dimensions["item_display_height_metric"] = item_display_height_metric
            
            amazon_uk_product["dimensions"] = dimensions
            channel_product_obj.amazon_uk_product_json = json.dumps(amazon_uk_product)

            amazon_uae_product["product_name"] = product_name_amazon_uae
            amazon_uae_product["category"] = category
            amazon_uae_product["sub_category"] = subtitle
            amazon_uae_product["product_description"] = product_description_amazon_uae
            if product_description_amazon_uae != None and product_description_amazon_uae != "":
                channel_product_obj.is_amazon_uae_product_created=True
            amazon_uae_product["product_attribute_list"] = product_attribute_list_amazon_uae
            amazon_uae_product["created_date"] = str(created_date)
            amazon_uae_product["feed_product_type"] = feed_product_type
            amazon_uae_product["recommended_browse_nodes"] = recommended_browse_nodes
            amazon_uae_product["update_delete"] = update_delete
            
            channel_product_obj.amazon_uae_product_json = json.dumps(amazon_uae_product)

            noon_product["product_name"] = product_name_noon
            noon_product["category"] = category
            noon_product["sub_category"] = subtitle
            noon_product["subtitle"] = subtitle
            noon_product["product_description"] = product_description_noon
            if product_description_noon != None and product_description_noon != "":
                channel_product_obj.is_noon_product_created=True
            noon_product["product_attribute_list"] = product_attribute_list_noon
            noon_product["created_date"] = str(created_date)
            noon_product["product_type"] = noon_product_type
            noon_product["product_subtype"] = noon_product_subtype
            noon_product["model_number"] = noon_model_number
            noon_product["model_name"] = noon_model_name
            noon_product["msrp_ae"] = noon_msrp_ae
            noon_product["msrp_ae_unit"] = noon_msrp_ae_unit
            
            channel_product_obj.noon_product_json = json.dumps(noon_product)
            
            ebay_product["product_name"] = product_name_ebay
            ebay_product["category"] = category
            ebay_product["sub_category"] = subtitle
            ebay_product["product_description"] = product_description_ebay
            if product_description_ebay != None and product_description_ebay != "":
                channel_product_obj.is_ebay_product_created=True
            ebay_product["product_attribute_list"] = product_attribute_list_noon
            ebay_product["created_date"] = str(created_date)
            ebay_product["category"] = category

            channel_product_obj.ebay_product_json = json.dumps(ebay_product)
            
            main_images_objs = []
            sub_images_objs = []

            main_images_objs.append(MainImages.objects.create(product=product_obj,is_sourced=True))
            
            sub_images_objs.append(SubImages.objects.create(product=product_obj,is_sourced=True))
            
            channel_obj,created = Channel.objects.get_or_create(name="Amazon UK")
            main_images_objs.append(MainImages.objects.create(product=product_obj,channel=channel_obj))
            sub_images_objs.append(SubImages.objects.create(product=product_obj,channel=channel_obj))
            
            channel_obj,created = Channel.objects.get_or_create(name="Amazon UAE")
            main_images_objs.append(MainImages.objects.create(product=product_obj,channel=channel_obj))
            sub_images_objs.append(SubImages.objects.create(product=product_obj,channel=channel_obj))
            
            channel_obj,created = Channel.objects.get_or_create(name="Ebay")
            main_images_objs.append(MainImages.objects.create(product=product_obj,channel=channel_obj))
            sub_images_objs.append(SubImages.objects.create(product=product_obj,channel=channel_obj))
            
            channel_obj,created = Channel.objects.get_or_create(name="Noon")
            main_images_objs.append(MainImages.objects.create(product=product_obj,channel=channel_obj))
            sub_images_objs.append(SubImages.objects.create(product=product_obj,channel=channel_obj))

            for main_images_obj in main_images_objs:
                for main_image_bucket in main_image_buckets:
                    main_images_obj.main_images.add(main_image_bucket)

            for sub_images_obj in sub_images_objs:
                for sub_image_bucket in sub_image_buckets:
                    sub_images_obj.sub_images.add(sub_image_bucket)

            for pfl_image in pfl_images_objs:
                product_obj.pfl_images.add(pfl_image)
            
            for white_background_image in white_background_images_objs:
                product_obj.white_background_images.add(white_background_image)
            
            for lifestyle_image in lifestyle_images_objs:
                product_obj.lifestyle_images.add(lifestyle_image)
            
            for certificate_image in certificate_images_objs:
                product_obj.certificate_images.add(certificate_image)
            
            for giftbox_image in giftbox_images_objs:
                product_obj.giftbox_images.add(giftbox_image)
            
            for diecut_image in diecut_images_objs:
                product_obj.diecut_images.add(diecut_image)
            
            for aplus_content_image in aplus_content_images_objs:
                product_obj.aplus_content_images.add(aplus_content_image)
            
            for ads_image in ads_images_objs:
                product_obj.ads_images.add(ads_image)
            
            for unedited_image in unedited_images_objs:
                base_product_obj.unedited_images.add(unedited_image)
            
            for pfl_generated_image in pfl_generated_images_objs:
                product_obj.pfl_generated_images.add(pfl_generated_image)
            
            for transparent_image in transparent_images_objs:
                product_obj.transparent_images.add(transparent_image)

            main_images_obj.save()
            sub_images_obj.save()

            base_product_obj.save()
            product_obj.save()
            channel_product_obj.save()

            DealsHubProduct.objects.create(product=product_obj)

            product_pk_mapping[data["pk"]] = product_obj.pk
            #if product_cnt%1000==0:
            print(("Product Cnt:", product_cnt))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error in Product %s at %s", str(e), str(exc_tb.tb_lineno)))

f_product = open("files/product_pk_mapping.txt","w")
product_pk_mapping_json = json.dumps(product_pk_mapping)
f_product.write(product_pk_mapping_json)
f_product.close()

f_sku = open("files/duplicate_seller_sku.txt","w")
seller_sku_json = json.dumps(seller_sku_dict)
f_sku.write(seller_sku_json)
f_sku.close()

flyer_pk_mapping = {}
flyer_cnt=0

for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.flyer":
            flyer_cnt+=1
            
            name = data["fields"]["name"]
            template_data = data["fields"]["template_data"]
            mode = data["fields"]["mode"]
            
            brand_pk = data["fields"]["brand"]
            brand_mapped_pk = brand_pk_mapping[brand_pk]
            brand_obj = Brand.objects.get(pk=int(brand_mapped_pk))

            flyer_image_pk = data["fields"]["flyer_image"]
            flyer_image_obj = None
            if flyer_image_pk!=None:
                mapped_pk = image_pk_mapping[flyer_image_pk]
                flyer_image_obj = Image.objects.get(pk = mapped_pk)

            product_bucket = data["fields"]["product_bucket"]
            products = []
            for product in product_bucket:
                product_pk = product
                mapped_product_pk = product_pk_mapping[product_pk]
                product_obj = Product.objects.get(pk=mapped_product_pk)
                products.append(product_obj)

            external_images_bucket = data["fields"]["external_images_bucket"]
            external_images = []
            for external_image in external_images_bucket:
                external_image_pk = external_image
                mapped_external_image_pk = image_pk_mapping[external_image_pk]
                external_image_obj = Image.objects.get(pk=mapped_external_image_pk)
                external_images.append(external_image_obj)

            background_images_bucket = data["fields"]["background_images_bucket"]
            background_images = []
            for background_image in background_images_bucket:
                background_image_pk = background_image
                mapped_background_image_pk = image_pk_mapping[background_image_pk]
                background_image_obj = Image.objects.get(pk=mapped_background_image_pk)
                background_images.append(background_image_obj)

            flyer_obj,created = Flyer.objects.get_or_create(name=name,
                                             template_data=template_data,
                                             mode=mode,
                                             brand=brand_obj,
                                             flyer_image=flyer_image_obj
                                             )

            for product in products:
                flyer_obj.product_bucket.add(product)

            for external_image in external_images:
                flyer_obj.external_images_bucket.add(external_image)

            for background_image in background_images:
                flyer_obj.background_images_bucket.add(background_image)

            flyer_obj.save()

            flyer_pk_mapping[data["pk"]] = flyer_obj.pk
            print(("Flyer Cnt:", flyer_cnt))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error Flyer %s at %s", str(e), str(exc_tb.tb_lineno)))

f_flyer = open("files/flyer_pk_mapping.txt","w")
flyer_pk_mapping_json = json.dumps(flyer_pk_mapping)
f_flyer.write(flyer_pk_mapping_json)
f_flyer.close()

prods = Product.objects.filter(base_product__brand__name="Geepas")
for prod in prods:
    category_obj = None
    category = prod.base_product.category
    if category!="":
        category_obj, created = Category.objects.get_or_create(name=category)
    sub_category_obj = None
    sub_category = prod.base_product.sub_category
    if sub_category!="":
        sub_category_obj, created = SubCategory.objects.get_or_create(name=sub_category, category=category_obj)
    d = DealsHubProduct.objects.filter(product=prod)[0]
    d.category = category_obj
    d.sub_category = sub_category_obj
    d.save()

DealsHubProduct.objects.filter(product__base_product__brand__name="Geepas").update(is_published=True)
