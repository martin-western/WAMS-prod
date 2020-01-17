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


cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.image":
            cnt+=1
            image_obj = Image.objects.create(image=data["fields"]["image"])
            image_pk_mapping[data["pk"]] = image_obj.pk
            print("Cnt:", cnt)
    except Exception as e:
        print("Error Image", str(e))

cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.brand":
            cnt+=1
            brand_obj = Brand.objects.create(name=data["fields"]["name"])
            brand_pk_mapping[data["pk"]] = brand_obj.pk
            print("Cnt:", cnt)
    except Exception as e:
        print("Error Brnad", str(e))

cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.organization":
            cnt+=1
            organization_obj = Organization.objects.create(name=data["fields"]["name"])
            organization_pk_mapping[data["pk"]] = organization_obj.pk
            print("Cnt:", cnt)
    except Exception as e:
        print("Error Organization", str(e))

cnt=0
for data in all_data_json:
    
    try:
        if data["model"] == "WAMSApp.category":
            cnt+=1
            category_obj = Category.objects.create(name=data["fields"]["name"])
            category_pk_mapping[data["pk"]] = category_obj.pk
            print("Cnt:", cnt)
    except Exception as e:
        print("Error Category", str(e))