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