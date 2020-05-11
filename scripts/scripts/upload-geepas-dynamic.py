import json
import os
import sys
from io import BytesIO as StringIO
from WAMSApp.models import *
from PIL import Image as IMage
from os import listdir, walk
from os.path import isfile, join
from django.core.files.uploadedfile import InMemoryUploadedFile

#filepath = "/home/ubuntu/wetransfer/SUB_IMAGES"
filepath = "LIFESTYLE_IMAGES"


all_f = []
for (dirpath, dirnames, filenames) in walk(filepath):
    for filename in filenames:
        all_f.append((filename, dirpath+"/"+filename))


size = 1024, 1024
cnt = 0
err_cnt = 0
image_information = []
product_dict = {}
for f in all_f:
    try:
        cnt += 1
        print(cnt)
        filename = f[0]
        filepath = f[1]
        seller_sku = filename.split(".")[0].split("_")[0]
        #index = int(filename.split(".")[0].split("_")[1])
        #print filename, seller_sku, index
        product_obj = Product.objects.get(base_product__seller_sku=seller_sku)

        
        if product_obj.pk not in product_dict:
            product_dict[product_obj.pk] = 1
            product_obj.lifestyle_images.clear()
        

        
        thumb = IMAGE.open(filepath)
        thumb.thumbnail(size)
        im_type = thumb.format 
        thumb_io = BytesIO()
        thumb.save(thumb_io, format=im_type)
        thumb_file = InMemoryUploadedFile(thumb_io, None, filename, 'image/'+im_type, thumb_io.getbuffer().nbytes, None)
        image_obj = Image.objects.create(image=thumb_file)
        

        """
        temp_dict = {}
        main_image_list = []
        for main_image in product_obj.transparent_images.all():
            main_image_list.append(main_image.pk)
        temp_dict[product_obj.pk] = main_image_list
        image_information.append(temp_dict)
        """

        #product_obj.sub_images.add(image_bucket_obj)
        #product_obj.save()

        #product_obj.main_images.add(image_bucket_obj)
        #product_obj.save()

        product_obj.lifestyle_images.add(image_obj)
        product_obj.save()

    except Exception as e:
        err_cnt += 1
        filename = f[0]
        seller_sku = filename.split(".")[0].split("_")[0]
        #print("ERROR  ", f[0])
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error ", str(e), str(exc_tb.tb_lineno))
        #print(seller_sku)

print(err_cnt)
