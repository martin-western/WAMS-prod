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
brand_pk_mapping = {}
organization_pk_mapping = {}
category_pk_mapping = {}


image_cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.image":
            image_cnt+=1
            image_obj = Image.objects.create(image=data["fields"]["image"])
            image_pk_mapping[data["pk"]] = image_obj.pk
            print("Image Cnt:", image_cnt)
    except Exception as e:
        print("Error Image", str(e))

brand_cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.brand":
            brand_cnt+=1
            brand_obj = Brand.objects.create(name=data["fields"]["name"])
            brand_pk_mapping[data["pk"]] = brand_obj.pk
            print("Cnt:", brand_cnt)
    except Exception as e:
        print("Error Brnad", str(e))

organization_cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.organization":
            organization_cnt+=1
            organization_obj = Organization.objects.create(name=data["fields"]["name"])
            organization_pk_mapping[data["pk"]] = organization_obj.pk
            print("Cnt:", organization_cnt)
    except Exception as e:
        print("Error Organization", str(e))

category_cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.category":
            category_cnt+=1
            category_obj = Category.objects.create(name=data["fields"]["name"])
            category_pk_mapping[data["pk"]] = category_obj.pk
            print("Cnt:", category_cnt)
    except Exception as e:
        print("Error Category", str(e))