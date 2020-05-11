from WAMSApp.models import *

product_objs = Product.objects.all()

def json_clean(json_dump_string):
    import json
    from WAMSApp.core_utils import *
    json_load_string = json.loads(json_dump_string)
    for i in range(len(json_load_string)):
        json_load_string[i] = convert_to_ascii(json_load_string[i])
    return json.dumps(json_load_string)

cnt = 0
for product_obj in product_objs:
    from WAMSApp.core_utils import *
    cnt += 1
    print cnt
    product_obj.pfl_product_name = convert_to_ascii(product_obj.pfl_product_name)
    product_obj.product_name_sap = convert_to_ascii(product_obj.product_name_sap)
    product_obj.product_name_amazon_uk = convert_to_ascii(product_obj.product_name_amazon_uk)
    product_obj.product_name_amazon_uae = convert_to_ascii(product_obj.product_name_amazon_uae)
    product_obj.product_name_ebay = convert_to_ascii(product_obj.product_name_ebay)
    product_obj.subtitle = convert_to_ascii(product_obj.subtitle)
    product_obj.product_description_amazon_uk = convert_to_ascii(product_obj.product_description_amazon_uk)
    product_obj.product_description_amazon_uae = convert_to_ascii(product_obj.product_description_amazon_uae)
    product_obj.product_description_ebay = convert_to_ascii(product_obj.product_description_ebay)
    product_obj.item_condition_note = convert_to_ascii(product_obj.item_condition_note)

    product_obj.pfl_product_features = json_clean(product_obj.pfl_product_features)
    product_obj.product_attribute_list_amazon_uk = json_clean(product_obj.product_attribute_list_amazon_uk)
    product_obj.product_attribute_list_amazon_uae = json_clean(product_obj.product_attribute_list_amazon_uae)
    product_obj.product_attribute_list_ebay = json_clean(product_obj.product_attribute_list_ebay)
    product_obj.special_features = json_clean(product_obj.special_features)
    product_obj.save()