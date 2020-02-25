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
    category_name = list(key.keys())[0]
    category_name_match = category_name
    if category_name.lower()=="kettel":
        category_name_match = "kettle"
    if category_name.lower()=="dosa maker":
        category_name_match = "Crepe &Dosa Maker"
    if category_name.lower()=="showcase":
        category_name_match = "show case"
    if category_name.lower()=="decorative lamp":
        category_name_match = "desk lamp"
    try:
        if Category.objects.filter(name=category_name_match).exists():
            category_obj = Category.objects.get(name__iexact=category_name_match.lower())
            property_data = key[category_name]
            category_obj.property_data = json.dumps(property_data)
            category_obj.save()
        else:
            print(category_name)
    except Exception as e:
        print(category_name)



#print(json.dumps(all_categories, indent=4, sort_keys=True))

#print(json.dumps(mega_category_dict, indent=4, sort_keys=True))