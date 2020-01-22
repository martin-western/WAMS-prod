import json
import os
import sys
from io import BytesIO as StringIO
from WAMSApp.models import *
from PIL import Image as IMage
from os import listdir, walk
from os.path import isfile, join
from django.core.files.uploadedfile import InMemoryUploadedFile

filepath = "/home/ubuntu/IDENTIFIED/"
#filepath = "/home/nisarg/Desktop/IDENTIFIED/"

all_f = []
for (dirpath, dirnames, filenames) in walk(filepath):
    for filename in filenames:
        all_f.append((filename, dirpath+"/"+filename))

print len(all_f)

cnt = 0
nesto_images_identified_product_pk = []

for filename, filepath in all_f:
    cnt += 1
    print("Cnt: ", cnt)
    try:
        #print filename.split(".")[0]
        to_match = filename.split(".")[0].strip()
        if "(" in to_match and ")" in to_match:
            to_match = to_match.split("(")[0].strip()
        if to_match=="":
            continue
        if Product.objects.filter(brand__organization__name="nesto", product_name_sap=to_match).exists():
            product_obj = Product.objects.filter(brand__organization__name="nesto", product_name_sap=to_match)[0]

            #thumb = IMage.open(filepath)
            #im_type = thumb.format
            #thumb_io = StringIO.StringIO()
            #thumb.save(thumb_io, format=im_type)

            #thumb_file = InMemoryUploadedFile(thumb_io, None, filepath, 'image/'+im_type, thumb_io.len, None)

            #image_obj = Image.objects.create(image=thumb_file)
            #image_bucket_obj = ImageBucket.objects.create(image=image_obj)
            #product_obj.main_images.add(image_bucket_obj)
            #product_obj.save()
            nesto_images_identified_product_pk.append(product_obj.pk)
            continue
        elif Product.objects.filter(brand__organization__name="nesto", product_name_sap__icontains=to_match).exists():
            if len(to_match.split())==1:
                pass
            
            product_obj = Product.objects.filter(brand__organization__name="nesto", product_name_sap__icontains=to_match)[0]
            
            #thumb = IMage.open(filepath)
            #im_type = thumb.format
            #thumb_io = StringIO.StringIO()
            #thumb.save(thumb_io, format=im_type)

            #thumb_file = InMemoryUploadedFile(thumb_io, None, filepath, 'image/'+im_type, thumb_io.len, None)

            #image_obj = Image.objects.create(image=thumb_file)
            #image_bucket_obj = ImageBucket.objects.create(image=image_obj)
            #product_obj.main_images.add(image_bucket_obj)
            #product_obj.save()
            nesto_images_identified_product_pk.append(product_obj.pk)
            continue
        words = to_match.split()
        total_words = len(words)
        temp_to_match = to_match
        total_words -= 1
        while total_words>1 and Product.objects.filter(brand__organization__name="nesto", product_name_sap__icontains=temp_to_match).exists()==False:
            temp_to_match = " ".join(words[:total_words])
            total_words -= 1
        if Product.objects.filter(brand__organization__name="nesto", product_name_sap__icontains=temp_to_match).exists():
            product_obj = Product.objects.filter(brand__organization__name="nesto", product_name_sap__icontains=temp_to_match)[0]
            
            #thumb = IMage.open(filepath)
            #im_type = thumb.format
            #thumb_io = StringIO.StringIO()
            #thumb.save(thumb_io, format=im_type)

            #thumb_file = InMemoryUploadedFile(thumb_io, None, filepath, 'image/'+im_type, thumb_io.len, None)

            #image_obj = Image.objects.create(image=thumb_file)
            #image_bucket_obj = ImageBucket.objects.create(image=image_obj)
            #product_obj.main_images.add(image_bucket_obj)
            #product_obj.save()
            nesto_images_identified_product_pk.append(product_obj.pk)
        else:
            print("No match!")

    except Exception as e:
        import sys
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error ", str(e), str(exc_tb.tb_lineno))

f = open("nesto_images_identified.txt", "w")
import json
f.write(json.dumps(nesto_images_identified_product_pk))
f.close()
