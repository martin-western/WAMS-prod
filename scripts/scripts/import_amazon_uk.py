from WAMSApp.models import *
import pandas as pd
import json


import_rule = "Partial"

filename = "scripts/56.xlsx"
dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]

rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

index_mapping = {}
for i in range(columns):
    index_mapping[dfs.iloc[0][i]] = i

# print json.dumps(index_mapping, indent=4, sort_keys=True)


def get_value(i, key):
    value = ""
    if key in index_mapping:
        value = dfs.iloc[i][index_mapping[key]]
    return value


def create_new_product_amazon_uk(i):
    try:
        product_id = dfs.iloc[i][index_mapping["external_product_id"]]
        feed_product_type = get_value(i, "feed_product_type")
        seller_sku = get_value(i, "item_sku")
        brand = get_value(i, "brand_name")
        product_id_type = get_value(i, "product_id_type")
        product_name = get_value(i, "item_name")
        manufacturer = get_value(i, "manufacturer")
        recommended_browse_nodes = get_value(i, "recommended_browse_nodes")
        standard_price = get_value(i, "standard_price")
        quantity = get_value(i, "quantity")
        parentage = get_value(i, "parent_child")
        parent_sku = get_value(i, "parent_sku")
        relationship_type = get_value(i, "relationship_type")
        variation_theme = get_value(i, "variation_theme")
        update_delete = get_value(i, "update_delete")
        manufacturer_part_number = get_value(i, "manufacturer_part_number")
        product_description = get_value(i, "product_description")
        wattage_metric = get_value(i, "wattage_unit_of_measure")

        bullet_point1 = get_value(i, "bullet_point1")
        bullet_point2 = get_value(i, "bullet_point2")
        bullet_point3 = get_value(i, "bullet_point3")
        bullet_point4 = get_value(i, "bullet_point4")
        bullet_point5 = get_value(i, "bullet_point5")
        search_terms = get_value(i, "generic_keywords")
        wattage = get_value(i, "wattage")
        color = get_value(i, "color_name")
        color_map = get_value(i, "color_name")
        material_type = get_value(i, "material_type")
        special_features1 = get_value(i, "special_features1")
        special_features2 = get_value(i, "special_features2")
        special_features3 = get_value(i, "special_features3")
        special_features4 = get_value(i, "special_features4")
        special_features5 = get_value(i, "special_features5")

        item_width_metric = get_value(i, "item_width_unit_of_measure")
        item_width = get_value(i, "item_width")
        item_height = get_value(i, "item_height")
        item_height_metric = get_value(i, "item_height_metric")
        item_dimensions_unit_of_measure = get_value(
            i, "item_dimensions_unit_of_measure")
        item_length_metric = get_value(i, "item_length_unit_of_measure")
        item_length = get_value(i, "item_length")
        shipping_weight = get_value(i, "website_shipping_weight")
        shipping_weight_metric = get_value(
            i, "website_shipping_weight_unit_of_measure")
        item_display_length = get_value(i, "item_display_length")
        item_display_length_metric = get_value(
            i, "item_display_length_unit_of_measure")
        item_display_width = get_value(i, "item_display_width")
        item_display_width_metric = get_value(i, "item_display_width_metric")
        item_display_height = get_value(i, "item_display_height")
        item_display_height_metric = get_value(
            i, "item_display_height_unit_of_measure")
        item_display_weight = get_value(i, "item_display_weight")
        item_display_weight_metric = get_value(
            i, "item_display_weight_unit_of_measure")
        item_display_volume = get_value(i, "item_display_volume")
        item_display_volume_metric = get_value(
            i, "item_display_volume_unit_of_measure")
        package_weight_metric = get_value(i, "package_weight_unit_of_measure")
        package_dimensions_metric = get_value(
            i, "package_dimensions_unit_of_measure")
        package_weight = get_value(i, "package_weight")
        package_length = get_value(i, "package_length")
        package_width = get_value(i, "package_width")
        package_height = get_value(i, "package_height")

        item_weight = get_value(i, "item_weight")
        item_weight_metric = get_value(i, "item_weight_unit_of_measure")
        number_of_items = get_value(i, "number_of_items")
        max_order_quantity = get_value(i, "max_order_quantity")
        sale_price = get_value(i, "sale_price")
        sale_from = get_value(i, "sale_from_date")
        sale_end = get_value(i, "sale_end_date")
        condition_type = get_value(i, "condition_type")
        condition_note = get_value(i, "condition_note")

        Product.objects.create(product_id=product_id,
                               feed_product_type=feed_product_type,
                               seller_sku=seller_sku,
                               brand=brand,
                               product_id_type=product_id_type,
                               product_name_sap=product_name,
                               product_name_amazon_uk=product_name,
                               product_name_amazon_uae=product_name,
                               product_name_ebay=product_name,
                               manufacturer=manufacturer,
                               recommended_browse_nodes=recommended_browse_nodes,
                               standard_price=standard_price,
                               quantity=quantity,
                               parentage=parentage,
                               parent_sku=parent_sku,
                               relationship_type=relationship_type,
                               variation_theme=variation_theme,
                               update_delete=variation_theme,
                               manufacturer_part_number=manufacturer_part_number,
                               product_description=product_description,
                               wattage_metric=wattage_metric,
                               product_attribute_list_amazon_uk=product_attribute_list,
                               product_attribute_list_amazon_uae=product_attribute_list,
                               product_attribute_list_ebay=product_attribute_list,
                               search_terms=search_terms,
                               wattage=wattage,
                               color=color,
                               color_map=color_map,
                               material_type=material_type,
                               special_features=special_features,
                               item_width_metric=item_width_metric,
                               item_width=item_width,
                               item_height=item_height,
                               item_height_metric=item_height_metric,
                               item_length=item_length,
                               item_length_metric=item_length_metric,
                               shipping_weight=shipping_weight,
                               shipping_weight_metric=shipping_weight_metric,
                               item_display_length=item_display_length,
                               item_display_length_metric=item_display_length_metric,
                               item_display_width=item_display_width,
                               item_display_width_metric=item_display_width_metric,
                               item_display_height=item_display_height,
                               item_display_height_metric=item_display_height_metric,
                               item_display_weight=item_display_weight,
                               item_display_weight_metric=item_display_weight_metric,
                               item_display_volume=item_display_volume,
                               item_display_volume_metric=item_display_volume_metric,
                               package_weight_metric=package_weight_metric,
                               package_dimensions_metric=package_dimensions_metric,
                               package_weight=package_weight,
                               package_length=package_length,
                               package_width=package_width,
                               package_height=package_height,
                               item_weight=item_weight,
                               item_weight_metric=item_weight_metric,
                               number_of_items=number_of_items,
                               max_order_quantity=max_order_quantity,
                               sale_price=sale_price,
                               sale_from=sale_from,
                               sale_end=sale_end,
                               condition_type=condition_type,
                               condition_note=condition_note,
                               status="Pending",
                               verified=False)

  
try:
    for i in range(1, rows+1):
        try:
            product_id = dfs.iloc[i][index_mapping["external_product_id"]]
            if Product.objects.filter(product_id=product_id).exists():
                product_obj = Product.objects.get(product_id=product_id)
                if import_rule == "Partial":
                    update_product_partial_amazon_uk(i)
                elif import_rule == "Missing":
                    update_product_missing_amazon_uk(i)
            else:   # Does not exist. Create new product
                create_new_product_amazon_uk(i)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print("Error for row index: %s at %s", e, str(exc_tb.tb_lineno))
except Exception as e:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    print("import_amazon_uk: %s at %s", e, str(exc_tb.tb_lineno))
