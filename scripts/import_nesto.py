import json
import pandas as pd
import os
import sys
import StringIO
from WAMSApp.models import *
from PIL import Image as IMage
from django.core.files.uploadedfile import InMemoryUploadedFile

filename = "./scripts/Nesto.xlsx"
dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]

rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

print dfs.iloc[0]

BASE_PATH = "/home/nisarg/Desktop/thumbs/"
CURR_PATH = os.getcwd()

organization_obj, created = Organization.objects.get_or_create(name="Nesto")

not_inserted = []
nesto_images_error = []
article_id_error = []

cnt = 0
rows = 23
os.chdir(BASE_PATH)
for i in range(rows):
    try:
        cnt += 1
        print cnt
        article_id = str(dfs.iloc[i][0])
        product_name = str(dfs.iloc[i][1].encode('ascii', errors='ignore'))
        brand = str(dfs.iloc[i][2])
        measure = str(dfs.iloc[i][3])
        unit = str(dfs.iloc[i][4])
        barcode = str(dfs.iloc[i][5])

        if brand.lower() in ["", "none", "null"]:
            brand = "Nesto"

        if Product.objects.filter(product_id=article_id).exists():
            not_inserted.append({"article_id": str(article_id), "i":str(i)})
            continue

        brand_obj = None
        if Brand.objects.filter(name=brand.lower()).exists():
            brand_obj = Brand.objects.get(name=brand.lower())
        else:
            brand_obj = Brand.objects.create(name=brand.lower(),
                                             organization=organization_obj)

        product_obj = Product.objects.create(product_name_sap=product_name,
                                             product_name_amazon_uk=product_name,
                                             product_id=article_id,
                                             brand=brand_obj,
                                             barcode_string=barcode)


        if unit in ["Bag", "Box", "Dzn", "Mah", "Pieces", "packet", "pieces"]:
            # unit is of type unit count
            if unit=="pieces":
                unit = "Pieces"
            try:
                product_obj.item_count = float(measure)
                product_obj.item_count_metric = unit
                product_obj.save()
            except Exception as e:
                print("Error with units, article_id: ", article_id)
                article_id_error.append({"product_pk": product_obj.pk})
        elif unit in ["Cl", "Gal", "Litre", "Oz", "ml"]:
            # unit is of type Volume
            if unit=="Cl":
                unit = "cl"
            elif unit=="Litre":
                unit = "litres"
            elif unit=="Oz":
                unit = "OZ"
            try:
                product_obj.item_display_volume = float(measure)
                product_obj.item_display_volume_metric = unit
            except Exception as e:
                print("Error with units, article_id: ", article_id)
                article_id_error.append({"product_pk": product_obj.pk})
        elif unit in ["Cm", "Ft", "Mt", "Sq ft", "Inches", "mm"]:
            # unit is of type Length
            if unit=="Cm":
                unit = "CM"
            elif unit=="Ft":
                unit = "FT"
            elif unit=="Mt":
                unit = "M"
            elif unit=="Inches":
                unit = "IN"
            elif unit=="mm":
                unit = "MM"

            try:
                product_obj.item_length = float(measure)
                product_obj.item_length_metric = unit
            except Exception as e:
                print("Error with units, article_id: ", article_id)
                article_id_error.append({"product_pk": product_obj.pk})
        elif unit in ["Kg", "Mg", "gm", "lbs"]:
            # unit is of type Weight
            if unit=="Kg":
                unit = "KG"
            elif unit=="lbs":
                unit = "LB"
            elif unit=="Mg":
                unit = "MG"
            elif unit=="gm":
                unit = "GR"
            try:
                product_obj.item_weight = float(measure)
                product_obj.item_weight_metric = unit
            except Exception as e:
                print("Error with units, article_id: ", article_id)
                article_id_error.append({"product_pk": product_obj.pk})


        try:
            filepath = None
            try:
                filepath = str(dfs.iloc[i][6])
                if os.path.exists(filepath) == False:
                    pattern = "".join(filepath.split(".")[0:-1])+"*"
                    if len(glob.glob(pattern))>0:
                        filepath = glob.glob(pattern)[0]
                    else:
                        pattern = pattern[:len(pattern)/2]+"*"
                        if len(glob.glob(pattern))>0:
                            filepath = glob.glob(pattern)[0]
                        else:
                            nesto_images_error.append({"article_id": str(article_id), "i":str(i), "file":str(dfs.iloc[i][6])})
            except Exception as e:
                nesto_images_error.append({"article_id": str(article_id), "i":str(i), "file":str(dfs.iloc[i][6])})
                print("Error images", str(e))


            if os.path.exists(filepath) == True:
                thumb = IMage.open(filepath)
                im_type = thumb.format
                thumb_io = StringIO.StringIO()
                thumb.save(thumb_io, format=im_type)

                thumb_file = InMemoryUploadedFile(thumb_io, None, filepath, 'image/'+im_type, thumb_io.len, None)

                image_obj = Image.objects.create(image=thumb_file)
                image_bucket_obj = ImageBucket.objects.create(image=image_obj, is_main_image=True)
                product_obj.main_images.add(image_bucket_obj)
                product_obj.save()

        except Exception as e:
            nesto_images_error.append({"article_id": str(article_id), "i":str(i), "file":str(dfs.iloc[i][6])})
            print("Error images", str(e))

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error: %s at %s", e, str(exc_tb.tb_lineno))


os.chdir(CURR_PATH)

f = open("not_inserted.txt", "w")
f.write(json.dumps(not_inserted))
f.close()


f = open("nesto_images_error.txt", "w")
f.write(json.dumps(nesto_images_error))
f.close()


f = open("article_id_error.txt", "w")
f.write(json.dumps(article_id_error))
f.close()
