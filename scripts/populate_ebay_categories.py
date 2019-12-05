import pandas as pd
from WAMSApp.models import *

filename = "./scripts/EbayCategory.xlsx"
dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]

rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

print dfs.iloc[0]

cnt = 0
for i in range(rows):
    try:
        cnt += 1
        print cnt
        category_id = str(dfs.iloc[i][0])
        name = str(dfs.iloc[i][1].encode('ascii', errors='ignore'))
        
        if EbayCategory.objects.filter(category_id=category_id).exists():
        	continue

        EbayCategory.objects.create(category_id=category_id, name=name)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error: %s at %s", e, str(exc_tb.tb_lineno))