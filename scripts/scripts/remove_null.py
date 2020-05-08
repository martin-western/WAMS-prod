from WAMSApp.models import *

product_objs = Product.objects.all()

cnt = 1
for product_obj in product_objs:
    print cnt
    cnt += 1
    if product_obj.package_length_metric=="null":
        product_obj.package_length_metric = ""

    if product_obj.package_length_metric=="null":
        product_obj.package_length_metric = ""

    if product_obj.package_width_metric=="null":
        product_obj.package_width_metric = ""

    if product_obj.package_height_metric=="null":
        product_obj.package_height_metric = ""

    if product_obj.package_weight_metric=="null":
        product_obj.package_weight_metric = ""

    if product_obj.shipping_weight_metric=="null":
        product_obj.shipping_weight_metric = ""

    if product_obj.item_display_weight_metric=="null":
        product_obj.item_display_weight_metric = ""

    if product_obj.item_display_volume_metric=="null":
        product_obj.item_display_volume_metric = ""

    if product_obj.item_display_length_metric=="null":
        product_obj.item_display_length_metric = ""

    if product_obj.item_weight_metric=="null":
        product_obj.item_weight_metric = ""

    if product_obj.item_length_metric=="null":
        product_obj.item_length_metric = ""
    
    if product_obj.item_width_metric=="null":
        product_obj.item_width_metric = ""

    if product_obj.item_height_metric=="null":
        product_obj.item_height_metric = ""

    if product_obj.item_display_width_metric=="null":
        product_obj.item_display_width_metric = ""

    if product_obj.item_display_height_metric=="null":
        product_obj.item_display_height_metric = ""

    if product_obj.wattage_metric=="null":
        product_obj.wattage_metric = ""

    product_obj.save()