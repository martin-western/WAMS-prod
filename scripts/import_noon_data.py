import pandas as pd 
from WAMSApp.models import *
import json

filename = "scripts/Noon_data.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]
rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

dfs = dfs.fillna("")
cnt=0

for i in range(rows):
    
    print(i)
    
    try:
        seller_sku = str(dfs.iloc[i,0])
        noon_sku = str(dfs.iloc[i,1])
        

        
    	cnt+=1

    except Exception as e:
        print(str(e))
        pass

print("Cnt : ",cnt)


