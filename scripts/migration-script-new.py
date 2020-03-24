# This is a one time migration script. Run this after deleting db and migrations

from WAMSApp.models import *
from dealshub.models import *
import json
import urllib.request, urllib.error, urllib.parse
import datetime
import os

f = open("scripts/23032020.json", "r")
all_data_json = json.loads(f.read())
f.close()


image_pk_mapping = {}
if os.path.exists("files/i1mage_pk_mapping.txt"):
    f = open("files/image_pk_mapping.txt","r")
    temp = json.loads(f.read())
    for key in temp:
        image_pk_mapping[int(key)] = temp[key]
    f.close()
else:
    cnt=0
    for data in all_data_json: 
        try:
            if data["model"] == "WAMSApp.image":
                cnt+=1
                image_obj = Image.objects.create(image=data["fields"]["image"],
                                                 mid_image=data["fields"]["mid_image"],
                                                 thumbnail=data["fields"]["thumbnail"],
                                                 description=data["fields"]["description"])
                image_pk_mapping[data["pk"]] = image_obj.pk
                
                if cnt%1000==0:
                    print("Image Cnt:", cnt)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(("Error Image %s at %s", str(e), str(exc_tb.tb_lineno)))

    f = open("files/image_pk_mapping.txt","w")
    f.write(json.dumps(image_pk_mapping))
    f.close()



organization_pk_mapping = {}
cnt = 0
for data in all_data_json:
    try:
        if data["model"] == "WAMSApp.organization":
            cnt+=1
            logo_obj = None
            if data["fields"]["logo"]!=None:
                logo_obj = Image.objects.get(pk=image_pk_mapping[data["fields"]["logo"]])
            organization_obj = Organization.objects.create(name=data["fields"]["name"],
                                                           contact_info=data["fields"]["contact_info"],
                                                           address=data["fields"]["address"],
                                                           logo=logo_obj,
                                                           primary_color=data["fields"]["primary_color"],
                                                           secondary_color=data["fields"]["secondary_color"],
                                                           facebook_link=data["fields"]["facebook_link"],
                                                           twitter_link=data["fields"]["twitter_link"],
                                                           instagram_link=data["fields"]["instagram_link"],
                                                           youtube_link=data["fields"]["youtube_link"])
            organization_pk_mapping[data["pk"]] = organization_obj.pk
            print(("Organization Cnt:", cnt))

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error in Organization %s at %s", str(e), str(exc_tb.tb_lineno)))


brand_pk_mapping = {}
cnt=0
for data in all_data_json:
    try:
        if data["model"] == "WAMSApp.brand":
            cnt+=1

            logo_obj = None
            if data["fields"]["logo"]!=None:
                logo_obj = Image.objects.get(pk=image_pk_mapping[data["fields"]["logo"]])

            organization_obj = None
            if data["fields"]["organization"]!=None:
                organization_obj = Organization.objects.get(pk=organization_pk_mapping[data["fields"]["organization"]])

            brand_obj = Brand.objects.create(name=data["fields"]["name"],
                                             logo = logo_obj,
                                             organization=organization_obj)

            brand_pk_mapping[data["pk"]] = int(brand_obj.pk)
            if cnt%100==0:
                print(("Brand Cnt:", cnt))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error in Brand %s at %s", str(e), str(exc_tb.tb_lineno)))


f = open("files/brand_pk_mapping.txt","w")
f.write(json.dumps(brand_pk_mapping))
f.close()

category_pk_mapping = {}
cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "dealshub.category":
            cnt+=1
            
            organization_obj = None
            if data["fields"]["organization"]!=None:
                organization_obj = Organization.objects.get(pk=organization_pk_mapping[data["fields"]["organization"]])

            category_obj = Category.objects.create(name=data["fields"]["name"],
                                                   description=data["fields"]["description"],
                                                   uuid=data["fields"]["category_id"],
                                                   organization=organization_obj,
                                                   property_data=data["fields"]["property_data"])

            category_pk_mapping[data["pk"]] = category_obj.pk
            print(("Category Cnt:", cnt))
    except Exception as e:
        print(("Error Category", str(e)))

f = open("files/category_pk_mapping.txt","w")
f.write(json.dumps(category_pk_mapping))
f.close()



subcategory_pk_mapping = {}
cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "dealshub.subcategory":
            cnt+=1
            category_obj = Category.objects.get(pk=category_pk_mapping[data["fields"]["category"]])
            subcategory_obj = SubCategory.objects.create(name=data["fields"]["name"],
                                                         description="",
                                                         uuid=data["fields"]["sub_category_id"],
                                                         category=category_obj,
                                                         property_data=data["fields"]["property_data"])

            subcategory_pk_mapping[data["pk"]] = subcategory_obj.pk
            print(("SubCategory Cnt:", cnt))
    except Exception as e:
        print(("Error SubCategory", str(e)))

f = open("files/subcategory_pk_mapping.txt","w")
f.write(json.dumps(subcategory_pk_mapping))
f.close()



background_image_pk_mapping ={}
cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.backgroundimage":
            cnt+=1
            
            image_obj = Image.objects.get(pk=image_pk_mapping[data["fields"]["image"]])
            
            background_image_obj = BackgroundImage.objects.create(image=image_obj)
            background_image_pk_mapping[data["pk"]] = background_image_obj.pk
            
            print("Background Image Cnt:", cnt)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error Background Image %s at %s", str(e), str(exc_tb.tb_lineno)))

f = open("files/background_image_pk_mapping.txt","w")
f.write(json.dumps(background_image_pk_mapping))
f.close()

image_bucket_pk_mapping = {}
cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.imagebucket":
            cnt+=1
            
            image_obj = Image.objects.get(pk=image_pk_mapping[data["fields"]["image"]])

            description = data["fields"]["description"]
            is_main_image = data["fields"]["is_main_image"]
            is_sub_image = data["fields"]["is_sub_image"]
            sub_image_index = data["fields"]["sub_image_index"]
            
            image_bucket_obj = ImageBucket.objects.create(image=image_obj,
                                                          description=description,
                                                          is_main_image=is_main_image,
                                                          is_sub_image=is_sub_image,
                                                          sub_image_index=sub_image_index)
            image_bucket_pk_mapping[data["pk"]] = image_bucket_obj.pk
            if cnt%1000==0:
                print(("Image Bucket Cnt:", cnt))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error in Image Bucket %s at %s", str(e), str(exc_tb.tb_lineno)))

f = open("files/image_bucket_pk_mapping.txt","w")
f.write(json.dumps(image_bucket_pk_mapping))
f.close()


base_product_pk_mapping = {}
cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.baseproduct":
            cnt+=1

            base_product_name = data["fields"]["base_product_name"]
            seller_sku = data["fields"]["seller_sku"]
            category = data["fields"]["category"]
            sub_category = data["fields"]["sub_category"]
            brand = data["fields"]["brand"]
            manufacturer = data["fields"]["manufacturer"]
            manufacturer_part_number = data["fields"]["manufacturer_part_number"]
            unedited_images = data["fields"]["unedited_images"]
            dimensions = data["fields"]["dimensions"]

            category_obj = None
            if category!="":
                category_obj = Category.objects.get(name=category)
            
            sub_category_obj = None
            if sub_category!="":
                sub_category_obj = SubCategory.objects.get(name=sub_category, category=category_obj)

            brand_obj = None
            if brand!=None:
                brand_obj = Brand.objects.get(pk=brand_pk_mapping[brand])

            base_product_obj = BaseProduct.objects.create(base_product_name=base_product_name,
                                                          seller_sku=seller_sku,
                                                          category=category_obj,
                                                          sub_category=sub_category_obj,
                                                          brand=brand_obj,
                                                          manufacturer=manufacturer,
                                                          manufacturer_part_number=manufacturer_part_number,
                                                          dimensions=dimensions)
            
            for unedited_image in unedited_images:
                unedited_image_obj = Image.objects.get(pk=image_pk_mapping[unedited_image])
                base_product_obj.unedited_images.add(unedited_image_obj)

            base_product_obj.save()

            base_product_pk_mapping[data["pk"]] = base_product_obj.pk
            if cnt%1000==0:
                print(("Base Product Cnt:", cnt))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error in Base Product %s at %s", str(e), str(exc_tb.tb_lineno)))

f = open("files/base_product_pk_mapping.txt","w")
f.write(json.dumps(base_product_pk_mapping))
f.close()



channel_pk_mapping = {}
cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.channel":
            cnt+=1

            name = data["fields"]["name"]

            channel_obj = Channel.objects.create(name=name)

            channel_pk_mapping[data["pk"]] = channel_obj.pk
            print("Channel Cnt:", cnt)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error in Channel %s at %s", str(e), str(exc_tb.tb_lineno)))

f = open("files/channel_pk_mapping.txt","w")
f.write(json.dumps(channel_pk_mapping))
f.close()



material_type_pk_mapping = {}
cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.materialtype":
            cnt+=1

            name = data["fields"]["name"]

            material_type_obj = MaterialType.objects.create(name=name)

            material_type_pk_mapping[data["pk"]] = material_type_obj.pk
            print("Material Type Cnt:", cnt)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error in Channel %s at %s", str(e), str(exc_tb.tb_lineno)))

f = open("files/material_type_pk_mapping.txt","w")
f.write(json.dumps(material_type_pk_mapping))
f.close()



product_id_type_pk_mapping = {}
cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.productidtype":
            cnt+=1

            name = data["fields"]["name"]

            product_id_type_obj = ProductIDType.objects.create(name=name)

            product_id_type_pk_mapping[data["pk"]] = product_id_type_obj.pk
            print(("Product ID Type Cnt:", cnt))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error in Product ID Type %s at %s", str(e), str(exc_tb.tb_lineno)))

f = open("files/product_id_type_pk_mapping.txt","w")
f.write(json.dumps(product_id_type_pk_mapping))
f.close()




channel_product_pk_mapping = {}
cnt=0

for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.channelproduct":
            cnt+=1

            noon_product_json = data["fields"]["noon_product_json"]
            is_noon_product_created = data["fields"]["is_noon_product_created"]
            amazon_uk_product_json = data["fields"]["amazon_uk_product_json"]
            is_amazon_uk_product_created = data["fields"]["is_amazon_uk_product_created"]
            amazon_uae_product_json = data["fields"]["amazon_uae_product_json"]
            is_amazon_uae_product_created = data["fields"]["is_amazon_uae_product_created"]
            ebay_product_json = data["fields"]["ebay_product_json"]
            is_ebay_product_created = data["fields"]["is_ebay_product_created"]

            channel_product_obj = ChannelProduct.objects.create(noon_product_json=noon_product_json,
                                                                is_noon_product_created=is_noon_product_created,
                                                                amazon_uk_product_json=amazon_uk_product_json,
                                                                is_amazon_uk_product_created=is_amazon_uk_product_created,
                                                                amazon_uae_product_json=amazon_uae_product_json,
                                                                is_amazon_uae_product_created=is_amazon_uae_product_created,
                                                                ebay_product_json=ebay_product_json,
                                                                is_ebay_product_created=is_ebay_product_created)

            channel_product_pk_mapping[data["pk"]] = channel_product_obj.pk
            if cnt%1000==0:
                print("Channel Product Cnt:", cnt)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error in Channel Product %s at %s", str(e), str(exc_tb.tb_lineno)))

f = open("files/channel_product_pk_mapping.txt","w")
f.write(json.dumps(channel_product_pk_mapping))
f.close()



product_pk_mapping = {}
cnt=0

for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.product":
            cnt+=1

            base_product = data["fields"]["base_product"]
            product_name = data["fields"]["product_name"]
            product_id = data["fields"]["product_id"]
            product_id_type = data["fields"]["product_id_type"]
            product_description = data["fields"]["product_description"]
            
            status = "Pending"
            verified = False
            uuid = data["fields"]["uuid"]

            #PFL
            pfl_product_name = data["fields"]["pfl_product_name"]
            pfl_product_features = data["fields"]["pfl_product_features"]

            product_name_sap = data["fields"]["product_name_sap"]
            color_map = data["fields"]["color_map"]
            color = data["fields"]["color"]
            material_type = data["fields"]["material_type"]
            standard_price = data["fields"]["standard_price"]
            currency = data["fields"]["currency"]
            quantity = data["fields"]["quantity"]



            pfl_images = data["fields"]["pfl_images"]
            white_background_images = data["fields"]["white_background_images"]
            lifestyle_images = data["fields"]["lifestyle_images"]
            certificate_images = data["fields"]["certificate_images"]
            giftbox_images = data["fields"]["giftbox_images"]
            diecut_images = data["fields"]["diecut_images"]
            aplus_content_images = data["fields"]["aplus_content_images"]
            ads_images = data["fields"]["ads_images"]
            pfl_generated_images = data["fields"]["pfl_generated_images"]
            transparent_images = data["fields"]["transparent_images"]



            # Other info
            barcode = data["fields"]["barcode"]
            barcode_string = data["fields"]["barcode_string"]
            outdoor_price = data["fields"]["outdoor_price"]

            channel_product = data["fields"]["channel_product"]
            factory_notes = data["fields"]["factory_notes"]

            no_of_images_for_filter = data["fields"]["no_of_images_for_filter"]

            factory = data["fields"]["factory"]

            barcode_obj = None
            try:
                barcode_obj = Image.objects.get(pk=image_pk_mapping[barcode])
            except Exception as e:
                pass

            material_type_obj = None
            try:
                material_type_obj = MaterialType.objects.get(pk=material_type_pk_mapping[material_type])
            except Exception as e:
                pass

            base_product_obj = BaseProduct.objects.get(pk=base_product_pk_mapping[base_product])

            dynamic_form_attributes = {}
            try:
                property_data = json.loads(base_product_obj.category.property_data)
                for prop_data in property_data:
                    dynamic_form_attributes[prop_data["key"]] = {
                        "type": "dropdown",
                        "labelText": prop_data["key"].title(),
                        "value": "",
                        "options": prop_data["values"]
                    }
            except Exception as e:
                pass

            factory_obj = None

            channel_product_obj = ChannelProduct.objects.get(pk=channel_product_pk_mapping[channel_product])
            
            product_obj = Product.objects.create(base_product=base_product_obj,
                                                 product_name=product_name,
                                                 product_id=product_id,
                                                 product_id_type=product_id_type_obj,
                                                 product_description=product_description,
                                                 status=status,
                                                 verified=verified,
                                                 uuid=uuid,
                                                 pfl_product_name=pfl_product_name,
                                                 pfl_product_features=pfl_product_features,
                                                 product_name_sap=product_name_sap,
                                                 color_map=color_map,
                                                 color=color,
                                                 material_type=material_type_obj,
                                                 standard_price=standard_price,
                                                 currency=currency,
                                                 quantity=quantity,
                                                 barcode=barcode_obj,
                                                 barcode_string=barcode_string,
                                                 outdoor_price=outdoor_price,
                                                 channel_product=channel_product_obj,
                                                 factory_notes=factory_notes,
                                                 no_of_images_for_filter=no_of_images_for_filter,
                                                 factory=factory_obj,
                                                 dynamic_form_attributes=json.dumps(dynamic_form_attributes))


            for image_pk in pfl_images:
                image_obj = Image.objects.get(pk=image_pk_mapping[image_pk])
                product_obj.pfl_images.add(image_obj)
            for image_pk in white_background_images:
                image_obj = Image.objects.get(pk=image_pk_mapping[image_pk])
                product_obj.white_background_images.add(image_obj)
            for image_pk in lifestyle_images:
                image_obj = Image.objects.get(pk=image_pk_mapping[image_pk])
                product_obj.lifestyle_images.add(image_obj)
            for image_pk in certificate_images:
                image_obj = Image.objects.get(pk=image_pk_mapping[image_pk])
                product_obj.certificate_images.add(image_obj)
            for image_pk in giftbox_images:
                image_obj = Image.objects.get(pk=image_pk_mapping[image_pk])
                product_obj.giftbox_images.add(image_obj)
            for image_pk in diecut_images:
                image_obj = Image.objects.get(pk=image_pk_mapping[image_pk])
                product_obj.diecut_images.add(image_obj)
            for image_pk in aplus_content_images:
                image_obj = Image.objects.get(pk=image_pk_mapping[image_pk])
                product_obj.aplus_content_images.add(image_obj)
            for image_pk in ads_images:
                image_obj = Image.objects.get(pk=image_pk_mapping[image_pk])
                product_obj.ads_images.add(image_obj)
            for image_pk in pfl_generated_images:
                image_obj = Image.objects.get(pk=image_pk_mapping[image_pk])
                product_obj.pfl_generated_images.add(image_obj)
            for image_pk in transparent_images:
                image_obj = Image.objects.get(pk=image_pk_mapping[image_pk])
                product_obj.transparent_images.add(image_obj)

            product_obj.save()

            is_published = False
            if str(base_product_obj.brand)=="geepas":
                is_published = True
            DealsHubProduct.objects.create(product=product_obj, is_published=is_published)

            product_pk_mapping[data["pk"]] = product_obj.pk
            if cnt%1000==0:
                print(("Product Cnt:", cnt))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error in Product %s at %s", str(e), str(exc_tb.tb_lineno)))

f = open("files/product_pk_mapping.txt","w")
f.write(json.dumps(product_pk_mapping))
f.close()







main_images_pk_mapping = {}
cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.mainimages":
            cnt+=1

            product_obj = Product.objects.get(pk=product_pk_mapping[data["fields"]["product"]])
            is_sourced = data["fields"]["is_sourced"]
            channel_obj = None
            if data["fields"]["channel"]!=None:
                channel_obj = Channel.objects.get(pk=channel_pk_mapping[data["fields"]["channel"]])

            main_images_obj = MainImages.objects.create(product=product_obj,
                                                        channel=channel_obj,
                                                        is_sourced=is_sourced)

            for image_bucket_pk in data["fields"]["main_images"]:
                image_bucket_obj = ImageBucket.objects.get(pk=image_bucket_pk_mapping[image_bucket_pk])
                main_images_obj.main_images.add(image_bucket_obj)

            main_images_obj.save()

            main_images_pk_mapping[data["pk"]] = main_images_obj.pk
            print(("Main Images Cnt:", cnt))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error in Main Images %s at %s", str(e), str(exc_tb.tb_lineno)))

f = open("files/main_images_pk_mapping.txt","w")
f.write(json.dumps(main_images_pk_mapping))
f.close()




sub_images_pk_mapping = {}
cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.subimages":
            cnt+=1

            product_obj = Product.objects.get(pk=product_pk_mapping[data["fields"]["product"]])
            is_sourced = data["fields"]["is_sourced"]
            channel_obj = None
            if data["fields"]["channel"]!=None:
                channel_obj = Channel.objects.get(pk=channel_pk_mapping[data["fields"]["channel"]])

            sub_images_obj = SubImages.objects.create(product=product_obj,
                                                      channel=channel_obj,
                                                      is_sourced=is_sourced)

            for image_bucket_pk in data["fields"]["sub_images"]:
                image_bucket_obj = ImageBucket.objects.get(pk=image_bucket_pk_mapping[image_bucket_pk])
                sub_images_obj.sub_images.add(image_bucket_obj)

            sub_images_obj.save()

            sub_images_pk_mapping[data["pk"]] = sub_images_obj.pk
            print(("Sub Images Cnt:", cnt))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error in SubImages %s at %s", str(e), str(exc_tb.tb_lineno)))

f = open("files/sub_images_pk_mapping.txt","w")
f.write(json.dumps(sub_images_pk_mapping))
f.close()







flyer_pk_mapping = {}
cnt=0

for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.flyer":
            cnt+=1
            
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

            flyer_obj = Flyer.objects.create(name=name,
                                             template_data=template_data,
                                             mode=mode,
                                             brand=brand_obj,
                                             flyer_image=flyer_image_obj)

            for product in products:
                flyer_obj.product_bucket.add(product)

            for external_image in external_images:
                flyer_obj.external_images_bucket.add(external_image)

            for background_image in background_images:
                flyer_obj.background_images_bucket.add(background_image)

            flyer_obj.save()

            flyer_pk_mapping[data["pk"]] = flyer_obj.pk
            print(("Flyer Cnt:", cnt))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error Flyer %s at %s", str(e), str(exc_tb.tb_lineno)))

f = open("files/flyer_pk_mapping.txt","w")
f.write(json.dumps(flyer_pk_mapping))
f.close()



for data in all_data_json: 
    try:
        if data["model"] == "WAMSApp.config":
            image_obj = Image.objects.get(pk=image_pk_mapping[data["fields"]["product_404_image"]])
            Config.objects.create(product_404_image=image_obj)
            break
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error Config %s at %s", str(e), str(exc_tb.tb_lineno)))



datapoint_pk_mapping = {}
cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.datapoint":
            cnt+=1

            datapoint_obj = DataPoint.objects.create(name=data["fields"]["name"], variable=data["fields"]["variable"])

            datapoint_pk_mapping[data["pk"]] = datapoint_obj.pk
            print(("DataPoint Cnt:", cnt))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error in DataPoint %s at %s", str(e), str(exc_tb.tb_lineno)))

f = open("files/datapoint_pk_mapping.txt","w")
f.write(json.dumps(datapoint_pk_mapping))
f.close()








##############################################################################


section_pk_mapping = {}
cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "dealshub.section":
            cnt+=1

            organization_obj = Organization.objects.get(pk=organization_pk_mapping[data["fields"]["organization"]])

            section_obj = Section.objects.create(name=data["fields"]["name"],
                                                 organization=organization_obj,
                                                 is_published=data["fields"]["is_published"],
                                                 listing_type=data["fields"]["listing_type"],
                                                 order_index=data["fields"]["order_index"])
            for product_pk in data["fields"]["products"]:
                product_obj = Product.objects.get(pk=product_pk_mapping[product_pk])
                section_obj.products.add(product_obj)
            section_obj.save()

            section_pk_mapping[data["pk"]] = section_obj.pk
            print(("Section Cnt:", cnt))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error in Section %s at %s", str(e), str(exc_tb.tb_lineno)))

f = open("files/section_pk_mapping.txt","w")
f.write(json.dumps(section_pk_mapping))
f.close()





banner_type_pk_mapping = {}
cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "dealshub.bannertype":
            cnt+=1

            organization_obj = Organization.objects.get(pk=organization_pk_mapping[data["fields"]["organization"]])

            banner_type_obj = BannerType.objects.create(name=data["fields"]["name"],
                                                        organization=organization_obj,
                                                        display_name=data["fields"]["display_name"],
                                                        limit=data["fields"]["limit"])

            banner_type_pk_mapping[data["pk"]] = banner_type_obj.pk
            print(("BannerType Cnt:", cnt))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error in BannerType %s at %s", str(e), str(exc_tb.tb_lineno)))

f = open("files/banner_type_pk_mapping.txt","w")
f.write(json.dumps(banner_type_pk_mapping))
f.close()





banner_pk_mapping = {}
cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "dealshub.banner":
            cnt+=1

            organization_obj = Organization.objects.get(pk=organization_pk_mapping[data["fields"]["organization"]])

            banner_type_obj = BannerType.objects.get(pk=banner_type_pk_mapping[data["fields"]["banner_type"]])
            banner_obj = Banner.objects.create(banner_type=banner_type_obj,
                                               organization=organization_obj,
                                               is_published=data["fields"]["is_published"],
                                               order_index=data["fields"]["order_index"])

            banner_pk_mapping[data["pk"]] = banner_obj.pk
            print(("Banner Cnt:", cnt))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error in Banner %s at %s", str(e), str(exc_tb.tb_lineno)))

f = open("files/banner_pk_mapping.txt","w")
f.write(json.dumps(banner_pk_mapping))
f.close()














unit_banner_image_pk_mapping = {}
cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "dealshub.unitbannerimage":
            cnt+=1

            image_obj = Image.objects.get(pk=image_pk_mapping[data["fields"]["image"]])

            banner_obj = Banner.objects.get(pk=banner_pk_mapping[data["fields"]["banner"]])
            unit_banner_image_obj = UnitBannerImage.objects.create(image=image_obj,
                                                                   http_link=data["fields"]["http_link"],
                                                                   banner=banner_obj)

            unit_banner_image_pk_mapping[data["pk"]] = unit_banner_image_obj.pk
            print(("Unit Banner Image Cnt:", cnt))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error in Unit Banner Image %s at %s", str(e), str(exc_tb.tb_lineno)))

f = open("files/unit_banner_image_pk_mapping.txt","w")
f.write(json.dumps(unit_banner_image_pk_mapping))
f.close()




image_link_pk_mapping = {}
cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "dealshub.imagelink":
            cnt+=1

            image_obj = Image.objects.get(pk=image_pk_mapping[data["fields"]["image"]])
            image_link_obj = ImageLink.objects.create(image=image_obj,
                                                      http_link=data["fields"]["http_link"])

            image_link_pk_mapping[data["pk"]] = image_link_obj.pk
            print(("Image Link Cnt:", cnt))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error in Image Link %s at %s", str(e), str(exc_tb.tb_lineno)))

f = open("files/image_link_pk_mapping.txt","w")
f.write(json.dumps(image_link_pk_mapping))
f.close()




dealshub_heading_pk_mapping = {}
cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "dealshub.dealshubheading":
            cnt+=1
            organization_obj = Organization.objects.get(pk=organization_pk_mapping[data["fields"]["organization"]])
            
            dealshub_heading_obj = DealsHubHeading.objects.create(name=data["fields"]["name"],
                                                                  organization=organization_obj)

            for image_link_pk in data["fields"]["image_links"]:
                image_link_obj = ImageLink.objects.get(pk=image_link_pk_mapping[image_link_pk])
                dealshub_heading_obj.image_links.add(image_link_obj)

            for category_pk in data["fields"]["categories"]:
                category_obj = Category.objects.get(pk=category_pk_mapping[category_pk])
                dealshub_heading_obj.categories.add(category_obj)

            dealshub_heading_obj.save()

            dealshub_heading_pk_mapping[data["pk"]] = dealshub_heading_obj.pk
            print(("Image Link Cnt:", cnt))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(("Error in DealsHubHeading %s at %s", str(e), str(exc_tb.tb_lineno)))

f = open("files/dealshub_heading_pk_mapping.txt","w")
f.write(json.dumps(dealshub_heading_pk_mapping))
f.close()