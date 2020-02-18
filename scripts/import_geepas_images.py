import json
import os
import sys
from io import BytesIO as StringIO
from WAMSApp.models import *
from PIL import Image as IMage
from os import listdir, walk
from os.path import isfile, join
import xlsxwriter
from django.core.files.uploadedfile import InMemoryUploadedFile

# filepath = "/home/ubuntu/Upload_Geepas_Images/MAIN_IMAGES"
# #filepath = "/home/nisarg/Desktop/IDENTIFIED/"

# all_f = []
# for (dirpath, dirnames, filenames) in walk(filepath):
#     for filename in filenames:
#         all_f.append((filename, dirpath+"/"+filename))

# workbook = xlsxwriter.Workbook('./files/csv/geepas-main_images-images.xlsx')
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
#         if Product.objects.filter(seller_sku__icontains=to_match).exists():
#             product_obj = Product.objects.filter(seller_sku__icontains=to_match)[0]
#             cnt += 1
#             print("Cnt: ", cnt)
#             thumb = IMage.open(filepath)
#             im_type = thumb.format
#             thumb_io = StringIO.StringIO()
#             thumb.save(thumb_io, format=im_type)

#             thumb_file = InMemoryUploadedFile(thumb_io, None, filepath, 'image/'+im_type, thumb_io.len, None)

#             image_obj , c= Image.objects.get_or_create(image=thumb_file)
#             image_bucket_obj, c= ImageBucket.objects.get_or_create(image=image_obj)
#             worksheet.write(rownum, 0,filename.encode("ascii", "ignore"))
#             worksheet.write(rownum, 1,"Identified")
#             worksheet.write(rownum, 2,product_obj.seller_sku.encode("ascii", "ignore"))
#             worksheet.write(rownum, 3,product_obj.product_name_sap.encode("ascii", "ignore"))
#             rownum = rownum+1
#             if c==True:
#                 product_obj.main_images.add(image_bucket_obj)
#             product_obj.save()
#             continue

#         else:
#             worksheet.write(rownum, 0,filename.encode("ascii", "ignore"))
#             worksheet.write(rownum, 1,"Not Identified")
#             rownum = rownum+1
#             print("No match!")

#     except Exception as e:
#         import sys
#         exc_type, exc_obj, exc_tb = sys.exc_info()
#         print("Error ", str(e), str(exc_tb.tb_lineno))
 
# workbook.close()

# filepath = "/home/ubuntu/Upload_Geepas_Images/TRANSPARENT_IMAGES"
# #filepath = "/home/nisarg/Desktop/IDENTIFIED/"

# all_f = []
# for (dirpath, dirnames, filenames) in walk(filepath):
#     for filename in filenames:
#         all_f.append((filename, dirpath+"/"+filename))

# workbook = xlsxwriter.Workbook('./files/csv/geepas-transparent-images.xlsx')
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
#         if Product.objects.filter(seller_sku__icontains=to_match).exists():
#             product_obj = Product.objects.filter(seller_sku__icontains=to_match)[0]
#             cnt += 1
#             print("Cnt: ", cnt)
#             thumb = IMage.open(filepath)
#             im_type = thumb.format
#             thumb_io = StringIO.StringIO()
#             thumb.save(thumb_io, format=im_type)

#             thumb_file = InMemoryUploadedFile(thumb_io, None, filepath, 'image/'+im_type, thumb_io.len, None)

#             image_obj , c= Image.objects.get_or_create(image=thumb_file)
#             if ImageBucket.objects.filter(image=image_obj).exists():
#                 image_bucket_obj= ImageBucket.objects.filter(image=image_obj)[0]
#                 dele+=1
#                 print("Cnt of delete ",dele)
#                 image_bucket_obj.delete()
#             worksheet.write(rownum, 0,filename.encode("ascii", "ignore"))
#             worksheet.write(rownum, 1,"Identified")
#             worksheet.write(rownum, 2,product_obj.seller_sku.encode("ascii", "ignore"))
#             worksheet.write(rownum, 3,product_obj.product_name_sap.encode("ascii", "ignore"))
#             rownum = rownum+1
#             product_obj.transparent_images.add(image_obj)
#             product_obj.save()
#             continue

#         else:
#             worksheet.write(rownum, 0,filename.encode("ascii", "ignore"))
#             worksheet.write(rownum, 1,"Not Identified")
#             rownum = rownum+1
#             print("No match!")

#     except Exception as e:
#         import sys
#         exc_type, exc_obj, exc_tb = sys.exc_info()
#         print("Error ", str(e), str(exc_tb.tb_lineno))
 
# workbook.close()

filepath = "/home/ubuntu/Upload_Geepas_Images/LIFESTYLE_IMAGES"
#filepath = "/home/nisarg/Desktop/IDENTIFIED/"

all_f = []
for (dirpath, dirnames, filenames) in walk(filepath):
    for filename in filenames:
        all_f.append((filename, dirpath+"/"+filename))

workbook = xlsxwriter.Workbook('./files/csv/geepas-lifestyle-images.xlsx')
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
        if Product.objects.filter(seller_sku__icontains=to_match).exists():
            product_obj = Product.objects.filter(seller_sku__icontains=to_match)[0]
            cnt += 1
            print("Cnt: ", cnt)
            thumb = IMage.open(filepath)
            im_type = thumb.format
            thumb_io = StringIO.StringIO()
            thumb.save(thumb_io, format=im_type)

            thumb_file = InMemoryUploadedFile(thumb_io, None, filepath, 'image/'+im_type, thumb_io.len, None)

            image_obj , c= Image.objects.get_or_create(image=thumb_file)
            if ImageBucket.objects.filter(image=image_obj).exists():
                image_bucket_obj= ImageBucket.objects.filter(image=image_obj)[0]
                dele+=1
                print("Cnt of delete ",dele)
                image_bucket_obj.delete()
            worksheet.write(rownum, 0,filename.encode("ascii", "ignore"))
            worksheet.write(rownum, 1,"Identified")
            worksheet.write(rownum, 2,product_obj.seller_sku.encode("ascii", "ignore"))
            worksheet.write(rownum, 3,product_obj.product_name_sap.encode("ascii", "ignore"))
            rownum = rownum+1
            if c==True:
                product_obj.lifestyle_images.add(image_obj)
            product_obj.save()
            continue

        else:
            worksheet.write(rownum, 0,filename.encode("ascii", "ignore"))
            worksheet.write(rownum, 1,"Not Identified")
            rownum = rownum+1
            print("No match!")

    except Exception as e:
        import sys
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error ", str(e), str(exc_tb.tb_lineno))
 
workbook.close()



# filepath = "/home/ubuntu/Upload_Geepas_Images/GIFTBOX_IMAGES"
# #filepath = "/home/nisarg/Desktop/IDENTIFIED/"

# all_f = []
# for (dirpath, dirnames, filenames) in walk(filepath):
#     for filename in filenames:
#         all_f.append((filename, dirpath+"/"+filename))

# workbook = xlsxwriter.Workbook('./files/csv/geepas-giftbox-images.xlsx')
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
#         if Product.objects.filter(seller_sku__icontains=to_match).exists():
#             product_obj = Product.objects.filter(seller_sku__icontains=to_match)[0]
#             cnt += 1
#             print("Cnt: ", cnt)
#             thumb = IMage.open(filepath)
#             im_type = thumb.format
#             thumb_io = StringIO.StringIO()
#             thumb.save(thumb_io, format=im_type)

#             thumb_file = InMemoryUploadedFile(thumb_io, None, filepath, 'image/'+im_type, thumb_io.len, None)

#             image_obj , c= Image.objects.get_or_create(image=thumb_file)
#             # if ImageBucket.objects.filter(image=image_obj).exists():
#             #     image_bucket_obj= ImageBucket.objects.filter(image=image_obj)[0]
#             #     dele+=1
#             #     print("Cnt of delete ",dele)
#             worksheet.write(rownum, 0,filename.encode("ascii", "ignore"))
#             worksheet.write(rownum, 1,"Identified")
#             worksheet.write(rownum, 2,product_obj.seller_sku.encode("ascii", "ignore"))
#             worksheet.write(rownum, 3,product_obj.product_name_sap.encode("ascii", "ignore"))
#             rownum = rownum+1
#             product_obj.giftbox_images.add(image_obj)
#             product_obj.save()
#             continue

#         else:
#             worksheet.write(rownum, 0,filename.encode("ascii", "ignore"))
#             worksheet.write(rownum, 1,"Not Identified")
#             rownum = rownum+1
#             print("No match!")

#     except Exception as e:
#         import sys
#         exc_type, exc_obj, exc_tb = sys.exc_info()
#         print("Error ", str(e), str(exc_tb.tb_lineno))
# workbook.close()