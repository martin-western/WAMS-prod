from WAMSApp.models import *
import json
import urllib2
import datetime


f = open("scripts/17012020.json", "r")
all_data_json = json.loads(f.read())
f.close()

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
            organization_obj = Organization.objects.create(name=data["fields"]["name"])
            organization_pk_mapping[data["pk"]] = organization_obj.pk
            print("Organization Cnt:", organization_cnt)
    except Exception as e:
        print("Error Organization", str(e))

f_organization = open("files/organization_pk_mapping.txt","w")
organization_pk_mapping_json = json.dumps(organization_pk_mapping)
f_organization.write(organization_pk_mapping_json)
f_organization.close()


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
            category_obj = Category.objects.create(name=data["fields"]["name"])
            category_pk_mapping[data["pk"]] = category_obj.pk
            print("Category Cnt:", category_cnt)
    except Exception as e:
        print("Error Category", str(e))

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
            
            image_pk = data["fields"]["image"]["pk"]
            mapped_pk = image_pk_mapping[image_pk]
            image_obj = Image.objects.get(pk=mapped_pk)
            
            background_image_obj = BackgroundImage.objects.create(image=image_obj)
            background_image_pk_mapping[data["pk"]] = background_image_obj.pk
            
            print("Background Image Cnt:", background_image_cnt)
    except Exception as e:
        print("Error Background Image", str(e))

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

f_image_bucket = open("files/image_bucket_pk_mapping.txt","w")
image_bucket_pk_mapping_json = json.dumps(image_bucket_pk_mapping)
f_image_bucket.write(image_bucket_pk_mapping_json)
f_image_bucket.close()

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
            pfl_product_name = data["fields"]["pfl_product_name"]
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

            base_product_obj = BaseProduct.objects.create(seller_sku=seller_sku,
                                                          brand=brand_obj,
                                                          base_product_name=product_name_sap,
                                                          created_date=created_date,
                                                          category=category,
                                                          subtitle=subtitle,
                                                          manufacturer=manufacturer,
                                                          manufacturer_part_number=manufacturer_part_number
                                                          )

            product_id_type_obj , created = ProductIDType.objects.get_or_create(name=product_id_type)
            material_type_obj , created = MaterialType.objects.get_or_create(name=material_type)

            product_obj = Product.objects.create(base_product=base_product_obj,
                                                 product_name=product_name_sap,
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
                                                 standard_price=float(standard_price),
                                                 quantity=int(quantity),
                                                 material_type=material_type_obj,
                                                 barcode=barcode_obj,
                                                 barcode_string=barcode_string,
                                                 outdoor_price=outdoor_price,
                                                 factory_notes=factory_notes
                                                 )

            channel_product_obj = product_obj.channel_product

            amazon_uk_product = json.loads(channel_product_obj.amazon_uk_product_json)
            amazon_uae_product = json.loads(channel_product_obj.amazon_uae_product_json)
            ebay_product = json.loads(channel_product_obj.ebay_product_json)
            noon_product = json.loads(channel_product_obj.noon_product_json)

            amazon_uk_product["product_name"] = product_name_amazon_uk
            amazon_uk_product["created_date"] = created_date
            amazon_uk_product["condition_type"] = condition_type
            amazon_uk_product["feed_product_type"] = feed_product_type
            amazon_uk_product["update_delete"] = update_delete
            amazon_uk_product["recommended_browse_nodes"] = recommended_browse_nodes
            amazon_uk_product["search_terms"] = search_terms
            amazon_uk_product["enclosure_material"] = enclosure_material
            amazon_uk_product["cover_material_type"] = cover_material_type
            amazon_uk_product["special_features"] = special_features
            amazon_uk_product["product_description_amazon_uk"] = product_description_amazon_uk
            if product_description_amazon_uk != None or product_description_amazon_uk != "":
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
            amazon_uae_product["product_description"] = product_description_amazon_uae
            if product_description_amazon_uae != None or product_description_amazon_uae != "":
                channel_product_obj.is_amazon_uae_product_created=True
            amazon_uae_product["product_attribute_list"] = product_attribute_list_amazon_uae
            amazon_uae_product["created_date"] = created_date
            amazon_uae_product["feed_product_type"] = feed_product_type
            amazon_uae_product["recommended_browse_nodes"] = recommended_browse_nodes
            amazon_uae_product["update_delete"] = update_delete
            
            channel_product_obj.amazon_uae_product_json = json.dumps(amazon_uae_product)

            noon_product["product_name"] = product_name_noon
            noon_product["product_description"] = product_description_noon
            if product_description_noon != None or product_description_noon != "":
                channel_product_obj.is_noon_product_created=True
            noon_product["product_attribute_list"] = product_attribute_list_noon
            noon_product["created_date"] = created_date
            noon_product["product_type"] = noon_product_type
            noon_product["product_subtype"] = noon_product_subtype
            noon_product["model_number"] = noon_model_number
            noon_product["model_name"] = noon_model_name
            noon_product["msrp_ae"] = noon_msrp_ae
            noon_product["msrp_ae_unit"] = noon_msrp_ae_unit
            
            channel_product_obj.noon_product_json = json.dumps(noon_product)
            
            ebay_product["product_name"] = product_name_ebay
            ebay_product["product_description"] = product_description_ebay
            if product_description_ebay != None or product_description_ebay != "":
                channel_product_obj.is_ebay_product_created=True
            ebay_product["product_attribute_list"] = product_attribute_list_noon
            ebay_product["created_date"] = created_date
            ebay_product["category"] = category

            channel_product_obj.ebay_product_json = json.dumps(ebay_product)
            
            main_images_obj = MainImages.objects.create(product=product_obj,is_sourced=True)

            for main_image_bucket in main_image_buckets:
                main_images_obj.main_images.add(main_image_bucket)

            sub_images_obj = SubImages.objects.create(product=product_obj,is_sourced=True)

            for sub_image_bucket in sub_image_buckets:
                sub_images_obj.sub_images.add(sub_image_bucket)

            product_obj["pfl_images"] = pfl_images
            product_obj["white_background_images"] = white_background_images
            product_obj["lifestyle_images"] = lifestyle_images
            product_obj["certificate_images"] = certificate_images
            product_obj["giftbox_images"] = giftbox_images
            product_obj["diecut_images"] = diecut_images
            product_obj["aplus_content_images"] = aplus_content_images
            product_obj["ads_images"] = ads_images
            product_obj["unedited_images"] = unedited_images
            product_obj["pfl_generated_images"] = pfl_generated_images
            product_obj["transparent_images"] = transparent_images

            main_images_obj.save()
            sub_images_obj.save()

            base_product_obj.save()
            product_obj.save()
            channel_product_obj.save()

            product_pk_mapping[data["pk"]] = product_obj.pk
            print("Product Cnt:", product_cnt)
    except Exception as e:
        print("Error Product Bucket", str(e))

f_product = open("files/product_pk_mapping.txt","w")
product_pk_mapping_json = json.dumps(product_pk_mapping)
f_product.write(product_pk_mapping_json)
f_product.close()

flyer_pk_mapping = {}
flyer_cnt=0

for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.flyer":
            flyer_cnt+=1
            
            name = data["fields"]["name"]
            template_data = data["fields"]["template_data"]
            mode = data["fields"]["mode"]
            
            brand_pk = data["fields"]["brand"]["pk"]
            brand_mapped_pk = brand_pk_mapping[brand_pk]
            brand_obj = Brand.objects.get(pk=brand_mapped_pk)

            flyer_image_pk = data["fields"]["flyer_image"]["pk"]
            mapped_pk = image_pk_mapping[logo_pk]
            flyer_image_obj = Image.objects.get(pk = mapped_pk)

            product_bucket = data["fields"]["product_bucket"]
            products = []
            for product in product_bucket:
                product_pk = product["pk"]
                mapped_product_pk = product_pk_mapping[product_pk]
                product_obj = Product.objects.get(pk=mapped_product_pk)
                products.append(product_obj)

            external_images_bucket = data["fields"]["external_images_bucket"]
            external_images = []
            for external_image in external_images_bucket:
                external_image_pk = external_image["pk"]
                mapped_external_image_pk = image_pk_mapping[external_image_pk]
                external_image_obj = Image.objects.get(pk=mapped_external_image_pk)
                external_images.append(external_image_obj)

            background_images_bucket = data["fields"]["background_images_bucket"]
            background_images = []
            for background_image in background_images_bucket:
                background_image_pk = background_image["pk"]
                mapped_background_image_pk = image_pk_mapping[background_image_pk]
                background_image_obj = Image.objects.get(pk=mapped_background_image_pk)
                background_images.append(background_image_obj)

            flyer_obj = Flyer.objects.create(name=name,
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
            print("Flyer Cnt:", flyer_cnt)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error Flyer %s at %s", str(e), str(exc_tb.tb_lineno))

f_flyer = open("files/flyer_pk_mapping.txt","w")
flyer_pk_mapping_json = json.dumps(flyer_pk_mapping)
f_flyer.write(flyer_pk_mapping_json)
f_flyer.close()
