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

cnt = 0
matched_images = 0
not_matched_images = 0
for filename, filepath in all_f:
    try:
        print("Cnt: ", cnt)
        to_match = filename.split(".")[0].split(" ")[0].strip().upper()
        if "(" in to_match and ")" in to_match:
            to_match = to_match.split("(")[0].strip()
        if to_match=="":
            not_matched_images += 1
            continue
        if Product.objects.filter(brand__name="krypton", product_id=to_match).exists():
            product_obj = Product.objects.filter(brand__name="krypton", product_id=to_match)[0]
            matched_images += 1
            continue
        elif Product.objects.filter(brand__name="krypton", product_id__icontains=to_match).exists():
            product_obj = Product.objects.filter(brand__name="krypton", product_id__icontains=to_match)[0]
            matched_images += 1
            continue
        else:
            not_matched_images += 1
            continue
        cnt += 1

    except Exception as e:
        import sys
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error ", str(e), str(exc_tb.tb_lineno))

print("Matched: ", matched_images)
print("UnMatched: ", not_matched_images)
