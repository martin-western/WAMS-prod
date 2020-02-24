from dealshub.models import *
import pandas as pd
import json

path = "./Geepas Category Attributes.xlsx"
dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
rows = len(dfs.iloc[:])

mega_category_dict = {}
for i in range(rows):
    try:
        category = str(dfs.iloc[i][0]).strip()
        property_metric = str(dfs.iloc[i][1]).strip()
        value = str(dfs.iloc[i][2]).strip()
        if category not in mega_category_dict:
            mega_category_dict[category] = {}

        property_dict = mega_category_dict[category]
        if property_metric not in property_dict:
            property_dict[property_metric] = []
        property_dict[property_metric].append(value)
    except Exception as e:
        pass


all_categories = []
for category in mega_category_dict:
    category_metric_list = []
    for metric in mega_category_dict[category].keys():
        temp_dict = {}
        temp_dict["key"] = metric
        temp_dict["values"] = mega_category_dict[category][metric]
        category_metric_list.append(temp_dict)
    all_categories.append({category: category_metric_list})


for key in all_categories:
    category_name = key.keys()[0]
    category_obj = Category.objects.get(name=category_name)
    print(category_obj)



#print(json.dumps(all_categories, indent=4, sort_keys=True))

#print(json.dumps(mega_category_dict, indent=4, sort_keys=True))