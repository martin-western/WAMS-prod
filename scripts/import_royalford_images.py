import json
import os
import sys
from io import BytesIO 
from WAMSApp.models import *
from PIL import Image as IMage
from os import listdir, walk
from os.path import isfile, join
import xlsxwriter
from django.core.files.uploadedfile import InMemoryUploadedFile

filepath = "/home/ubuntu/ROYALFORD_IMAGES/MAIN_IMAGES"
# #filepath = "/home/nisarg/Desktop/IDENTIFIED/"

all_f = []
for (dirpath, dirnames, filenames) in walk(filepath):
    for filename in filenames:
        all_f.append((filename, dirpath+"/"+filename))

workbook = xlsxwriter.Workbook('./files/csv/royalford-main_images-images.xlsx')
worksheet = workbook.add_worksheet()
product_pk = {}
rownum =0

cnt = 0
dele=0
for filename, filepath in all_f:
     
    try:
        #print filename.split(".")[0]
        to_match = filename.split(".")[0].strip()
        if "(" in to_match and ")" in to_match:
            to_match = to_match.split("(")[0].strip()
        if "_" in to_match:
            to_match = to_match.split("_")[0].strip()
        if "-" in to_match:
            to_match = to_match.split("-")[0].strip()
        if to_match=="":
            continue
        print(to_match)
        
        if BaseProduct.objects.filter(seller_sku__icontains=to_match).exists():
            product_obj = Product.objects.filter(base_product=BaseProduct.objects.filter(seller_sku__icontains=to_match)[0])[0]
            cnt += 1
            print("Cnt: ", cnt)
            thumb = IMage.open(filepath)
            im_type = thumb.format
            thumb_io = BytesIO()
            thumb.save(thumb_io, format=im_type)

            thumb_file = InMemoryUploadedFile(thumb_io, None, filepath, 'image/'+im_type, thumb_io.getbuffer().nbytes, None)

            image_obj = Image.objects.create(image=thumb_file)
            image_bucket_obj = ImageBucket.objects.create(image=image_obj)
            worksheet.write(rownum, 0,filename)
            worksheet.write(rownum, 1,"Identified")
            worksheet.write(rownum, 2,product_obj.base_product.seller_sku)
            worksheet.write(rownum, 3,product_obj.product_name_sap)
            rownum = rownum+1
            
            main_images_objs = []
            
            main_images_obj,c = MainImages.objects.get_or_create(product = product_obj,is_sourced=True)
            main_images_objs.append(main_images_obj)

            chan = Channel.objects.get(name="Amazon UK")
            main_images_obj,c = MainImages.objects.get_or_create(product = product_obj,channel=chan)
            main_images_objs.append(main_images_obj)

            chan = Channel.objects.get(name="Amazon UAE")
            main_images_obj,c = MainImages.objects.get_or_create(product = product_obj,channel=chan)
            main_images_objs.append(main_images_obj)
            
            chan = Channel.objects.get(name="Noon")
            main_images_obj,c = MainImages.objects.get_or_create(product = product_obj,channel=chan)
            main_images_objs.append(main_images_obj)
            
            chan = Channel.objects.get(name="Ebay")
            main_images_obj,c = MainImages.objects.get_or_create(product = product_obj,channel=chan)
            main_images_objs.append(main_images_obj)
            
            for main_images_obj in main_images_objs:
                if product_obj.pk not in product_pk:
                    main_images_obj.main_images.clear()
                    product_pk[product_obj.pk] = 1
                main_images_obj.main_images.clear()
                main_images_obj.main_images.add(image_bucket_obj)
                main_images_obj.save()
                    
            product_obj.save()
            continue

        else:
            worksheet.write(rownum, 0,filename)
            worksheet.write(rownum, 1,"Not Identified")
            rownum = rownum+1
            print("No match!")

    except Exception as e:
        import sys
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error ", str(e), str(exc_tb.tb_lineno))

workbook.close()


product_pk = {}
filepath = "/home/ubuntu/ROYALFORD_IMAGES/SUB_IMAGES"
#filepath = "/home/nisarg/Desktop/IDENTIFIED/"

all_f = []
for (dirpath, dirnames, filenames) in walk(filepath):
    for filename in filenames:
        all_f.append((filename, dirpath+"/"+filename))

workbook = xlsxwriter.Workbook('./files/csv/royalford-sub-images.xlsx')
worksheet = workbook.add_worksheet()
nesto_images_identified_product_pk = []
rownum =0

cnt = 0
dele=0
for filename, filepath in all_f:
     
    try:
        #print filename.split(".")[0]
        to_match = filename.split(".")[0].strip()
        if "(" in to_match and ")" in to_match:
            to_match = to_match.split("(")[0].strip()
        if "_" in to_match:
            to_match = to_match.split("_")[0].strip()
        if "-" in to_match:
            to_match = to_match.split("-")[0].strip()
        if to_match=="":
            continue
        print(to_match)
        
        if BaseProduct.objects.filter(seller_sku__icontains=to_match).exists():
            product_obj = Product.objects.filter(base_product=BaseProduct.objects.filter(seller_sku__icontains=to_match)[0])[0]
            cnt += 1
            print("Cnt: ", cnt)
            
            thumb = IMage.open(filepath)
            im_type = thumb.format
            thumb_io = BytesIO()
            thumb.save(thumb_io, format=im_type)

            thumb_file = InMemoryUploadedFile(thumb_io, None, filepath, 'image/'+im_type, thumb_io.getbuffer().nbytes, None)

            image_obj = Image.objects.create(image=thumb_file)
            image_bucket_obj= ImageBucket.objects.create(image=image_obj)
            worksheet.write(rownum, 0,filename)
            worksheet.write(rownum, 1,"Identified")
            worksheet.write(rownum, 2,product_obj.base_product.seller_sku)
            worksheet.write(rownum, 3,product_obj.product_name_sap)
            rownum = rownum+1
            
            sub_images_objs = []
            
            sub_images_obj,c = SubImages.objects.get_or_create(product = product_obj,is_sourced=True)
            sub_images_objs.append(sub_images_obj)

            chan = Channel.objects.get(name="Amazon UK")
            sub_images_obj,c = SubImages.objects.get_or_create(product = product_obj,channel=chan)
            sub_images_objs.append(sub_images_obj)

            chan = Channel.objects.get(name="Amazon UAE")
            sub_images_obj,c = SubImages.objects.get_or_create(product = product_obj,channel=chan)
            sub_images_objs.append(sub_images_obj)
            
            chan = Channel.objects.get(name="Noon")
            sub_images_obj,c = SubImages.objects.get_or_create(product = product_obj,channel=chan)
            sub_images_objs.append(sub_images_obj)
            
            chan = Channel.objects.get(name="Ebay")
            sub_images_obj,c = SubImages.objects.get_or_create(product = product_obj,channel=chan)
            sub_images_objs.append(sub_images_obj)
            
            for sub_images_obj in sub_images_objs:
                if product_obj.pk not in product_pk:
                    sub_images_obj.sub_images.clear()
                    product_pk[product_obj.pk] = 1
                sub_images_obj.sub_images.add(image_bucket_obj)
                sub_images_obj.save()

            product_obj.save()
            continue

        else:
            worksheet.write(rownum, 0,filename)
            worksheet.write(rownum, 1,"Not Identified")
            rownum = rownum+1
            print("No match!")

    except Exception as e:
        import sys
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error ", str(e), str(exc_tb.tb_lineno))

 
workbook.close()

product_pk = {}
filepath = "/home/ubuntu/ROYALFORD_IMAGES/LIFESTYLE_IMAGES"
#filepath = "/home/nisarg/Desktop/IDENTIFIED/"

all_f = []
for (dirpath, dirnames, filenames) in walk(filepath):
    for filename in filenames:
        all_f.append((filename, dirpath+"/"+filename))

workbook = xlsxwriter.Workbook('./files/csv/royalford-lifestyle-images.xlsx')
worksheet = workbook.add_worksheet()
nesto_images_identified_product_pk = []
rownum =0

cnt = 0
dele=0
for filename, filepath in all_f:
     
    try:
        #print filename.split(".")[0]
        to_match = filename.split(".")[0].strip()
        if "(" in to_match and ")" in to_match:
            to_match = to_match.split("(")[0].strip()
        if "_" in to_match:
            to_match = to_match.split("_")[0].strip()
        if "-" in to_match:
            to_match = to_match.split("-")[0].strip()
        if to_match=="":
            continue

        print(to_match)
        
        if BaseProduct.objects.filter(seller_sku__icontains=to_match).exists():
            product_obj = Product.objects.filter(base_product=BaseProduct.objects.filter(seller_sku__icontains=to_match)[0])[0]
            cnt += 1
            print("Cnt: ", cnt)
            
            thumb = IMage.open(filepath)
            im_type = thumb.format
            thumb_io = BytesIO()
            thumb.save(thumb_io, format=im_type)

            thumb_file = InMemoryUploadedFile(thumb_io, None, filepath, 'image/'+im_type, thumb_io.getbuffer().nbytes, None)

            image_obj= Image.objects.create(image=thumb_file)
            worksheet.write(rownum, 0,filename)
            worksheet.write(rownum, 1,"Identified")
            worksheet.write(rownum, 2,product_obj.base_product.seller_sku)
            worksheet.write(rownum, 3,product_obj.product_name_sap)
            rownum = rownum+1
            
            
            if product_obj.pk not in product_pk:
                product_obj.lifestyle_images.clear()
                product_pk[product_obj.pk] = 1
            product_obj.lifestyle_images.add(image_obj)
                    
            product_obj.save()
            continue

        else:
            worksheet.write(rownum, 0,filename)
            worksheet.write(rownum, 1,"Not Identified")
            rownum = rownum+1
            print("No match!")

    except Exception as e:
        import sys
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error ", str(e), str(exc_tb.tb_lineno))
 
workbook.close()


product_pk = {}
filepath = "/home/ubuntu/ROYALFORD_IMAGES/GIFTBOX_IMAGES"
#filepath = "/home/nisarg/Desktop/IDENTIFIED/"

all_f = []
for (dirpath, dirnames, filenames) in walk(filepath):
    for filename in filenames:
        all_f.append((filename, dirpath+"/"+filename))

workbook = xlsxwriter.Workbook('./files/csv/royalford-giftbox-images.xlsx')
worksheet = workbook.add_worksheet()
nesto_images_identified_product_pk = []
rownum =0

cnt = 0
dele=0
for filename, filepath in all_f:
     
    try:
        #print filename.split(".")[0]
        to_match = filename.split(".")[0].strip()
        if "(" in to_match and ")" in to_match:
            to_match = to_match.split("(")[0].strip()
        if "_" in to_match:
            to_match = to_match.split("_")[0].strip()
        if "-" in to_match:
            to_match = to_match.split("-")[0].strip()
        if to_match=="":
            continue

        print(to_match)
        
        if BaseProduct.objects.filter(seller_sku__icontains=to_match).exists():
            product_obj = Product.objects.filter(base_product=BaseProduct.objects.filter(seller_sku__icontains=to_match)[0])[0]
            cnt += 1
            print("Cnt: ", cnt)
            
            thumb = IMage.open(filepath)
            im_type = thumb.format
            thumb_io = BytesIO()
            thumb.save(thumb_io, format=im_type)

            thumb_file = InMemoryUploadedFile(thumb_io, None, filepath, 'image/'+im_type, thumb_io.getbuffer().nbytes, None)

            image_obj= Image.objects.create(image=thumb_file)
            worksheet.write(rownum, 0,filename)
            worksheet.write(rownum, 1,"Identified")
            worksheet.write(rownum, 2,product_obj.base_product.seller_sku)
            worksheet.write(rownum, 3,product_obj.product_name_sap)
            rownum = rownum+1
            
            
            if product_obj.pk not in product_pk:
                product_obj.giftbox_images.clear()
                product_pk[product_obj.pk] = 1
            product_obj.giftbox_images.add(image_obj)
                   
            product_obj.save()
            continue

        else:
            worksheet.write(rownum, 0,filename)
            worksheet.write(rownum, 1,"Not Identified")
            rownum = rownum+1
            print("No match!")

    except Exception as e:
        import sys
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error ", str(e), str(exc_tb.tb_lineno))
 
workbook.close()

# product_pk = {}
# filepath = "/home/ubuntu/ROYALFORD_IMAGES/TRANSPERANT_IMAGES"
# #filepath = "/home/nisarg/Desktop/IDENTIFIED/"

# all_f = []
# for (dirpath, dirnames, filenames) in walk(filepath):
#     for filename in filenames:
#         all_f.append((filename, dirpath+"/"+filename))

# workbook = xlsxwriter.Workbook('./files/csv/royalford-transparent-images.xlsx')
# worksheet = workbook.add_worksheet()
# nesto_images_identified_product_pk = []
# rownum =0

# cnt = 0
# dele=0
# for filename, filepath in all_f:
     
#     try:
#         #print filename.split(".")[0]
#         to_match = filename.split(".")[0].strip()
#         if "(" in to_match and ")" in to_match:
#             to_match = to_match.split("(")[0].strip()
#         if "_" in to_match:
#             to_match = to_match.split("_")[0].strip()
#         if "-" in to_match:
#             to_match = to_match.split("-")[0].strip()
#         if to_match=="":
#             continue

#         print(to_match)
        
#         if BaseProduct.objects.filter(seller_sku__icontains=to_match).exists():
#             product_obj = Product.objects.filter(base_product=BaseProduct.objects.filter(seller_sku__icontains=to_match)[0])[0]
#             cnt += 1
#             print("Cnt: ", cnt)
            
#             thumb = IMage.open(filepath)
#             im_type = thumb.format
#             thumb_io = BytesIO()
#             thumb.save(thumb_io, format=im_type)

#             thumb_file = InMemoryUploadedFile(thumb_io, None, filepath, 'image/'+im_type, thumb_io.getbuffer().nbytes, None)

#             image_obj= Image.objects.create(image=thumb_file)
#             worksheet.write(rownum, 0,filename)
#             worksheet.write(rownum, 1,"Identified")
#             worksheet.write(rownum, 2,product_obj.base_product.seller_sku)
#             worksheet.write(rownum, 3,product_obj.product_name_sap)
#             rownum = rownum+1
            
#             if product_obj.pk not in product_pk:
#                 product_obj.transparent_images.clear()
#                 product_pk[product_obj.pk] = 1
#             product_obj.transparent_images.add(image_obj)
                    
#             product_obj.save()
#             continue

#         else:
#             worksheet.write(rownum, 0,filename)
#             worksheet.write(rownum, 1,"Not Identified")
#             rownum = rownum+1
#             print("No match!")

#     except Exception as e:
#         import sys
#         exc_type, exc_obj, exc_tb = sys.exc_info()
#         print("Error ", str(e), str(exc_tb.tb_lineno))
 
# workbook.close()
