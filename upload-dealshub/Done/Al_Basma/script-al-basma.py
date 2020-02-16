import pandas as pd

path = "upload-dealshub/Al_Basma/Flat.File.Home.ae.xlsm"
dfs = pd.read_excel(path, sheet_name=None)["Template"]
rows = len(dfs.iloc[:])

for i in range(2, rows):
    seller_sku = dfs.iloc[i][1]
    brand_name = dfs.iloc[i][2]
    product_id = dfs.iloc[i][3]
    #product_id_type = dfs.iloc[i][4]
    product_id_type = "EAN"
    product_name = dfs.iloc[i][5]
    manufacturer_name = dfs.iloc[i][6]
    product_description = dfs.iloc[i][7]
    manufacturer_part_number = dfs.iloc[i][8]
    recommended_browse_nodes = dfs.iloc[i][14]
    standard_price = dfs.iloc[i][15]
    quantity = dfs.iloc[i][16]
    main_image_url = dfs.iloc[i][17]

    bullet_point1 = dfs.iloc[i][44]
    bullet_point2 = dfs.iloc[i][45]
    bullet_point3 = dfs.iloc[i][46]
    bullet_point4 = dfs.iloc[i][47]
    bullet_point5 = dfs.iloc[i][48]
    search_terms = dfs.iloc[i][49]

    print("seller_sku", seller_sku)
    print("brand_name", brand_name)
    print("product_id", product_id)
    print("product_id_type", product_id_type)
    print("product_name", product_name)
    print("manufacturer_name", manufacturer_name)
    print("product_description", product_description)
    print("manufacturer_part_number", manufacturer_part_number)
    print("recommended_browse_nodes", recommended_browse_nodes)
    print("standard_price", standard_price)
    print("quantity", quantity)
    print("main_image_url", main_image_url)

    print("bullet_point1", bullet_point1)
    print("bullet_point2", bullet_point2)    
    print("bullet_point3", bullet_point3)
    print("bullet_point4", bullet_point4)
    print("bullet_point5", bullet_point5)
    print("search_terms", search_terms)

    

    print("\n\n\n")