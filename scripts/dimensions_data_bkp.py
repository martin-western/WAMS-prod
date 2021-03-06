import pandas as pd
from WAMSApp.models import *
import xlsxwriter

filename = "scripts/dimensions_geepas.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet2"]
rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

workbook = xlsxwriter.Workbook('scripts/not-identified-dimensions_geepas.xlsx')
worksheet = workbook.add_worksheet()
rownum =0

cnt=0
metric = "CM"

for i in range(rows):
    try:
        seller_sku_main = dfs.iloc[i][3]
        product_dimension_l = dfs.iloc[i][6]
        product_dimension_b = dfs.iloc[i][7]
        product_dimension_h = dfs.iloc[i][8]
        giftbox_l = dfs.iloc[i][9]
        giftbox_b = dfs.iloc[i][10]
        giftbox_h = dfs.iloc[i][11]
        export_carton_cbm_l = dfs.iloc[i][12]
        export_carton_cbm_b = dfs.iloc[i][13]
        export_carton_cbm_h = dfs.iloc[i][14]
        
        # print(seller_sku_main)
        seller_sku = seller_sku_main.split(" ")[0]

        base_product = BaseProduct.objects.get(seller_sku=seller_sku)

        base_dimensions = json.loads(base_product.dimensions)
        base_dimensions["product_dimension_l"] = product_dimension_l
        base_dimensions["product_dimension_l_metric"] = metric
        base_dimensions["product_dimension_b"] = product_dimension_b
        base_dimensions["product_dimension_b_metric"] = metric
        base_dimensions["product_dimension_h"] = product_dimension_h
        base_dimensions["product_dimension_h_metric"] = metric
        base_dimensions["giftbox_l"] = giftbox_l
        base_dimensions["giftbox_l_metric"] = metric
        base_dimensions["giftbox_b"] = giftbox_b
        base_dimensions["giftbox_b_metric"] = metric
        base_dimensions["giftbox_h"] = giftbox_h
        base_dimensions["giftbox_h_metric"] = metric
        base_dimensions["export_carton_cbm_l"] = export_carton_cbm_l
        base_dimensions["export_carton_cbm_l_metric"] = metric
        base_dimensions["export_carton_cbm_b"] = export_carton_cbm_b
        base_dimensions["export_carton_cbm_b_metric"] = metric
        base_dimensions["export_carton_cbm_h"] = export_carton_cbm_h
        base_dimensions["export_carton_cbm_h_metric"] = metric

        base_dimensions = json.dumps(base_dimensions)

        # print(base_dimensions)

        base_product.dimensions = base_dimensions
        base_product.save()
        
        print("Cnt: ",cnt)
        cnt+=1

    except Exception as e:
        # print(seller_sku_main)
        worksheet.write(rownum, 0,seller_sku_main)
        rownum+=1
        print(str(e))
        pass

workbook.close()