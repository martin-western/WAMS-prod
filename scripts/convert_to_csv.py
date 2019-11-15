import json
import csv

f = open("all_data_04112019.json", "r")
all_data_json = json.loads(f.read().encode('utf-8'))
f.close()


fw = open("all_data.csv", mode='w')
writer = csv.writer(fw, delimiter=',', quotechar='"',
                    quoting=csv.QUOTE_MINIMAL)


row = ["id",
       "item_sku",
       "product_id",
       "title",
       "brand_name",
       "created_at",
       "updated_at",
       "bullet_point",
       "country",
       "external_product_id_type",
       "feed_product_type",
       "fulfillment_center_id",
       "manufacturer",
       "standard_price",
       "product_description",
       "recommended_browse_nodes",
       "quantity",
       "part_number",
       "package_dimensions_unit_of_measure",
       "package_height",
       "package_length",
       "package_length_measurement",
       "package_weight",
       "package_weight_measurement",
       "package_width",
       "package_width_measurement",
       "ads_0",
       "ads_1",
       "ads_2",
       "ads_3",
       "ads_4",
       "ads_5",
       "ads_6",
       "ads_7",
       "certificate_0",
       "diecut_0",
       "diecut_1",
       "giftbox_0",
       "giftbox_1",
       "item_package_quantity",
       "lifestyle_0",
       "lifestyle_1",
       "lifestyle_2",
       "lifestyle_3",
       "lifestyle_4",
       "lifestyle_5",
       "lifestyle_6",
       "lifestyle_7",
       "main",
       "pfl_0",
       "pfl_1",
       "pfl_2",
       "pfl_3",
       "pfl_4",
       "pfl_5",
       "pfl_6",
       "pfl_7",
       "product_attributes_1",
       "product_attributes_2",
       "product_attributes_3",
       "product_attributes_4",
       "product_attributes_5",
       "product_attributes_6",
       "product_attributes_7",
       "product_attributes_8",
       "product_attributes_9",
       "product_attributes_10",
       "product_attributes_11",
       "product_attributes_12",
       "product_attributes_13",
       "product_attributes_14",
       "product_attributes_15",
       "product_attributes_16",
       "product_attributes_17",
       "sub_0",
       "sub_1",
       "sub_2",
       "sub_3",
       "sub_4",
       "sub_5",
       "sub_6",
       "sub_7",
       "unedited_0",
       "unedited_1",
       "unedited_2",
       "unedited_3",
       "unedited_4",
       "unedited_5",
       "unedited_6",
       "unedited_7",
       "update_delete",
       "white_background_0",
       "white_background_1",
       "white_background_2",
       "white_background_3",
       "verified",
       "Ingredients"]

writer.writerow(row)
err_cnt = 0
for data in all_data_json:
    try:
        data_row  = 98*[""]
        for key in data:
            if key=="":
                continue
            try:
                if key=="meta":
                    if data["meta"] != None:
                        meta = json.loads(data["meta"])
                        if meta is None:
                            continue
                        for k in meta:
                            if k=="" or k=="Contains_Food_or_Beverage" or k=="White Glove Service required" or k=="Directions" or k=="White_Glove_Service_required" or k=="Unit_of_measure_of_package_weight" or k=="Contains Food or Beverage" or k=="Unit of measure of package weight":
                                continue
                            val = meta[k]
                            if val==None:
                                continue
                            try:
                                val = val.replace("\xb0", "")
                                val = val.replace("\u2019", "")
                                val = val.replace("\\u2019", "")
                                val = val.replace("\u2022", "")
                            except Exception as e:
                                pass
                            data_row[row.index(k)] = val
                else:
                    val = data[key]
                    if val==None:
                        continue
                    try:
                        val = val.replace("\xb0", "")
                        val = val.replace("\u2019", "")
                        val = val.replace("\\u2019", "")
                        val = val.replace("\u2022", "")
                    except Exception as e:
                        pass
                    data_row[row.index(key)] = val
            except Exception as e:
                import sys
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print("Error1 ", str(e), str(exc_tb.tb_lineno))

        data_row_2 = []
        for k in data_row:
            if isinstance(k, int)==False:
                l = k.encode('utf-8').strip()
                data_row_2.append(l)
            else:
                data_row_2.append(k)

        writer.writerow(data_row_2)
    except Exception as e:
        import sys
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error2 ", str(e), str(exc_tb.tb_lineno))
        err_cnt += 1
print(err_cnt)