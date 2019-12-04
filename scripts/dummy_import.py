import json
import pandas as pd
import os
import sys
import StringIO
import glob
from WAMSApp.models import *
from PIL import Image as IMage
from django.core.files.uploadedfile import InMemoryUploadedFile

filename = "./scripts/Nesto.xlsx"
dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]

rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

print dfs.iloc[0]

nesto_images_error = []

cnt = 0
os.chdir("/home/nisarg/Desktop/thumbs/")

for i in range(rows):
    try:
        cnt += 1
        #print cnt
        article_id = str(dfs.iloc[i][0])
        product_name = str(dfs.iloc[i][1].encode('ascii', errors='ignore'))
        brand = str(dfs.iloc[i][2])
        measure = str(dfs.iloc[i][3])
        unit = str(dfs.iloc[i][4])
        barcode = str(dfs.iloc[i][5])

        try:
            filepath = str(dfs.iloc[i][6])
            if os.path.exists(filepath) == False:
                pattern = "".join(filepath.split(".")[0:-1])+"*"
                #print "Pattern:", pattern
                if len(glob.glob(pattern))>0:
                    print filepath, glob.glob(pattern)[0]
                else:
                    pattern = pattern[:len(pattern)/2]+"*"
                    if len(glob.glob(pattern))>0:
                        print filepath, glob.glob(pattern)[0]
                    else:  
                        nesto_images_error.append({"article_id": str(article_id), "i":str(i), "file":str(dfs.iloc[i][6])})                
        except Exception as e:
            nesto_images_error.append({"article_id": str(article_id), "i":str(i), "file":str(dfs.iloc[i][6])})
            print("Error images", str(e))

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error: %s at %s", e, str(exc_tb.tb_lineno))


os.chdir("/home/nisarg/Desktop/WAMS/")
f = open("nesto_images_error.txt", "w")
f.write(json.dumps(nesto_images_error))
f.close()
