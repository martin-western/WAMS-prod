import mysql.connector
import json

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="QwErTyASDFG!@#$098KJH)(*><",
    database="geepas")

mycursor = mydb.cursor()

mycursor.execute("SELECT * FROM product_details_list")

myresult = mycursor.fetchall()

all_data_json = []
f = open("all_data_04112019.json", "w")
for data in myresult:
    temp_dict = {}
    temp_dict["id"] = data[0]
    temp_dict["item_sku"] = data[1]
    temp_dict["country"] = data[2]
    temp_dict["product_id"] = data[3]
    temp_dict["title"] = data[4]
    temp_dict["brand_name"] = data[5]
    temp_dict["meta"] = data[6]
    temp_dict["channel_name"] = data[7]
    temp_dict["is_updated"] = data[8]
    temp_dict["verified"] = data[9]
    temp_dict["created_at"] = str(data[10])
    temp_dict["updated_at"] = str(data[11])
    all_data_json.append(temp_dict)

f.write(json.dumps(all_data_json))
f.close()











# 120, 
# 'RF1080-RB3.5', 
# 'UAE', 
# '6294009904108', 
# 'Royalford RF1080 Melamine Rice Bowl, 3.5 ', 
# 'Royalford', 
# {
#     "id": "120", 
#     "main": "https://wig-wams-s3-bucket.s3.ap-south-1.amazonaws.com/1568900956RF1080.jpg",
#     "sub_0":"",
#     "white_background_0":""
#     "title": "Royalford RF1080 Melamine Rice Bowl, 3.5 ", 
#     "country": "UAE", 
#     "item_sku": "RF1080-RB3.5", 
#     "quantity": "0", 
#     "Directions": "", 
#     "brand_name": "Royalford", 
#     "product_id": "6294009904108", 
#     "Ingredients": "", 
#     "part_number": "RF1080-RB3.5", 
#     "bullet_point": "", 
#     "manufacturer": "Royalford", 
#     "package_width": "", 
#     "update_delete": "", 
#     "package_height": "", 
#     "package_length": "", 
#     "package_weight": "", 
#     "standard_price": "", 
#     "feed_product_type": "Tableware", 
#     "product_description": "", 
#     "product_attributes_1": "", 
#     "product_attributes_2": " Intricate golden design\\n ", 
#     "product_attributes_3": " Crafted from melamine\\n ", 
#     "product_attributes_4": " Sturdy and durable", 
#     "fulfillment_center_id": "", 
#     "item_package_quantity": "", 
#     "external_product_id_type": "EAN", 
#     "recommended_browse_nodes": "", 
#     "Contains_Food_or_Beverage": "", 
#     "package_width_measurement": "", 
#     "package_length_measurement": "", 
#     "package_weight_measurement": "", 
#     "White_Glove_Service_required": "", 
#     "Unit_of_measure_of_package_weight": "", 
#     "package_dimensions_unit_of_measure": ""
# }
# None
# None
# 1
# datetime.datetime(2019, 9, 18, 11, 19, 55)
# datetime.datetime(2019, 9, 19, 13, 49, 24))


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







# mycursor.execute("describe product_details_list")
# mycursor.execute("select count(*) from product_details_list")



# mysqldump -u root -p geepas > 04112019.sql