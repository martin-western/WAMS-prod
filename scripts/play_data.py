import json
f = open("all_data_04112019.json", "r")
all_data_json = json.loads(f.read())
f.close()

all_keys = {}

duplicate_products = {}


for data in all_data_json:

    try:
        product_id = data["product_id"]
        # item_sku = data["item_sku"]
        # country = data["country"]
        # brand_name = data["brand_name"]
        # verified = data["verified"]
        # created_at = data["created_at"]
        # updated_at = data["updated_at"]

        if product_id not in duplicate_products:
            duplicate_products[product_id] = 1
        else:
            duplicate_products[product_id] += 1


        meta = json.loads(data["meta"])
        if meta!=None and "main" in meta and meta["main"]!=None and meta["main"]!="":
            print meta["main"].split("/")[-1]
        
            # "certificate_0": 1,
            # "diecut_0": 563, 
            # "diecut_1": 8, 
            # "giftbox_0": 296, 
            # "giftbox_1": 9,
            # "lifestyle_0": 199, 
            # "lifestyle_1": 78, 
            # "lifestyle_2": 59, 
            # "lifestyle_3": 47, 
            # "lifestyle_4": 31, 
            # "lifestyle_5": 18, 
            # "lifestyle_6": 14, 
            # "lifestyle_7": 8, 
            # "main": 4282,
            # "pfl_0": 2925, 
            # "pfl_1": 2, 
            # "pfl_2": 1, 
            # "pfl_3": 1, 
            # "pfl_4": 1, 
            # "pfl_5": 1, 
            # "pfl_6": 1, 
            # "pfl_7": 1,  
            # "sub_0": 1297, 
            # "sub_1": 906, 
            # "sub_2": 537, 
            # "sub_3": 299, 
            # "sub_4": 173, 
            # "sub_5": 92, 
            # "sub_6": 44, 
            # "sub_7": 27, 
            # "unedited_0": 623, 
            # "unedited_1": 320, 
            # "unedited_2": 212, 
            # "unedited_3": 131, 
            # "unedited_4": 78, 
            # "unedited_5": 62, 
            # "unedited_6": 44, 
            # "unedited_7": 30, 
            # "white_background_0": 442, 
            # "white_background_1": 2, 
            # "white_background_2": 1, 
            # "white_background_3": 1

    except Exception as e:
        import sys
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error ", str(e), str(exc_tb.tb_lineno))


for key in duplicate_products:
    if duplicate_products[key]>1:
        print(str(key) + " - " + str(duplicate_products[key]))

#print(json.dumps(all_keys, indent=4, sort_keys=True))
#print(json.dumps(sample_data, indent=4, sort_keys=True))
#print(json.dumps(brand_keys, indent=4, sort_keys=True))

# 'id',
# 'item_sku', 
# 'country', 
# 'product_id', 
# 'title', 
# 'brand_name', 
# 'meta',
# 'channel_name', 
# 'is_updated', 
# 'verified',
# 'created_at', 
# 'updated_at'