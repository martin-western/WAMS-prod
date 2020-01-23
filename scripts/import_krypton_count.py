import json
import os
import sys
from io import BytesIO as StringIO
from WAMSApp.models import *
from PIL import Image as IMage
from os import listdir, walk
from os.path import isfile, join
from django.core.files.uploadedfile import InMemoryUploadedFile
import xlsxwriter


filepaths = []
filepaths.append("/home/ubuntu/KRYPTON_SIDD/Diecut")
filepaths.append("/home/ubuntu/KRYPTON_SIDD/Giftbox")
filepaths.append("/home/ubuntu/KRYPTON_SIDD/Images")
filepaths.append("/home/ubuntu/KRYPTON_SIDD/PFL")
#filepath = "/home/nisarg/Desktop/IDENTIFIED/"

all_f = []
for filepath in filepaths:
    for (dirpath, dirnames, filenames) in walk(filepath):
        for filename in filenames:
            all_f.append((filename, dirpath+"/"+filename))

print len(all_f)


workbook = xlsxwriter.Workbook('./files/csv/identified-krypton.xlsx')
worksheet = workbook.add_worksheet()
rownum=0
worksheet.write(rownum, 0,"filename")
worksheet.write(rownum, 1,"product_name_sap")
worksheet.write(rownum, 2,"product_id")
worksheet.write(rownum, 3,"seller_sku")
rownum = rownum+1

workbook2 = xlsxwriter.Workbook('./files/csv/not-identified-krypton.xlsx')
worksheet2 = workbook2.add_worksheet()
rownum2=0
worksheet2.write(rownum2, 0,"filename")
rownum2 = rownum2+1

images_names = []
matched_images_names = []

cnt = 0
cnt2=0
krypton_images_identified_product_pk = []

for filename, filepath in all_f:
    try:
        images_names.append(filename.split(".")[0].split(" ")[0])
           
        to_match = filename.split(".")[0].split(" ")[0].strip().upper()
        if "(" in to_match and ")" in to_match:
            to_match = to_match.split("(")[0].strip()
        if to_match=="":
            continue
        if Product.objects.filter(brand__name="krypton", product_id=to_match).exists():
            product_obj = Product.objects.filter(brand__name="krypton", product_id=to_match)[0]
            # print(product_obj.__dict__)
            worksheet.write(rownum, 0,filename.encode("ascii", "ignore"))
            worksheet.write(rownum, 1,product_obj.product_name_sap.encode("ascii", "ignore"))
            worksheet.write(rownum, 2,product_obj.product_id.encode("ascii", "ignore"))
            worksheet.write(rownum, 3,product_obj.seller_sku.encode("ascii", "ignore"))
            rownum = rownum+1
            #thumb = IMage.open(filepath)
            #im_type = thumb.format
            #thumb_io = StringIO.StringIO()
            #thumb.save(thumb_io, format=im_type)

            #thumb_file = InMemoryUploadedFile(thumb_io, None, filepath, 'image/'+im_type, thumb_io.len, None)

            #image_obj = Image.objects.create(image=thumb_file)
            #image_bucket_obj = ImageBucket.objects.create(image=image_obj)
            #product_obj.main_images.add(image_bucket_obj)
            #product_obj.save()
            cnt += 1
           
            matched_images_names.append(filename.split(".")[0].split(" ")[0])
            krypton_images_identified_product_pk.append(product_obj.pk)
            continue
        elif Product.objects.filter(brand__name="krypton", product_id__icontains=to_match).exists():
            if len(to_match.split())==1:
                pass
            
            product_obj = Product.objects.filter(brand__name="krypton", product_id__icontains=to_match)[0]
            
            #thumb = IMage.open(filepath)
            #im_type = thumb.format
            #thumb_io = StringIO.StringIO()
            #thumb.save(thumb_io, format=im_type)

            #thumb_file = InMemoryUploadedFile(thumb_io, None, filepath, 'image/'+im_type, thumb_io.len, None)

            #image_obj = Image.objects.create(image=thumb_file)
            #image_bucket_obj = ImageBucket.objects.create(image=image_obj)
            #product_obj.main_images.add(image_bucket_obj)
            #product_obj.save()
            cnt += 1
            
            worksheet.write(rownum, 0,filename.encode("ascii", "ignore"))
            worksheet.write(rownum, 1,product_obj.product_name_sap.encode("ascii", "ignore"))
            worksheet.write(rownum, 2,product_obj.product_id.encode("ascii", "ignore"))
            worksheet.write(rownum, 3,product_obj.seller_sku.encode("ascii", "ignore"))
            rownum = rownum+1
            matched_images_names.append(filename.split(".")[0].split(" ")[0])
            krypton_images_identified_product_pk.append(product_obj.pk)
            continue

        else:
            cnt2 +=1
            worksheet2.write(rownum2, 0,filename.encode("ascii", "ignore"))
            rownum2 = rownum2 + 1
            continue

    except Exception as e:
        import sys
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error ", str(e), str(exc_tb.tb_lineno))

images_names = set(images_names)
matched_images_names = set(matched_images_names)
print("Cnt: ", cnt)
print("Cnt2: ", cnt2)
print("images_names: ", len(images_names))
print("matched_images_names: ", len(matched_images_names))

f = open("krypton_images_identified.txt", "w")
import json
f.write(json.dumps(krypton_images_identified_product_pk))
f.close()
workbook.close()
workbook2.close()