from WAMSApp.models import *
import json
import urllib2

f = open("scripts/all_data_04112019.json", "r")
all_data_json = json.loads(f.read())
f.close()

all_keys = {}
sample_data = {}
brand_keys = {}
iterr = 0

Product.objects.all().delete()
Image.objects.all().delete()
ImageBucket.objects.all().delete()

for data in all_data_json:
    iterr += 1
    print(iterr)
    try:
        product_id = data["product_id"]
        item_sku = data["item_sku"]
        country = data["country"]
        brand_name = data["brand_name"]
        verified = data["verified"]
        created_at = data["created_at"]
        updated_at = data["updated_at"]

        print("")
        print("")
        print("")
        print("")
        print("")
        print("")
        print("Product ID: ", product_id)

        prod_obj = Product.objects.create(product_id=product_id,
                                          product_attribute_list_amazon_uk="[]",
                                          product_attribute_list_amazon_uae="[]",
                                          product_attribute_list_ebay="[]",
                                          pfl_product_features="[]",
                                          special_features="[]")
        prod_obj.seller_sku = item_sku
        # if verified == 1:
        #     prod_obj.status = "Verified"
        #     prod_obj.verified = True
        prod_obj.status = "Pending"
        prod_obj.verified = False

        brand_obj = None
        if brand_name != "" and brand_name != "null":
            brand_obj, created = Brand.objects.get_or_create(name=brand_name)
            prod_obj.brand = brand_obj

        meta = json.loads(data["meta"])
        if meta is not None:

            if "title" in meta:
                prod_obj.product_name_sap = meta["title"]
                prod_obj.product_name_amazon_uk = meta["title"]
                prod_obj.product_name_amazon_uae = meta["title"]
                prod_obj.product_name_ebay = meta["title"]

            if "bullet_point" in meta:
                bullet_points = filter(
                    None, meta["bullet_point"].split("\u2022"))
                prod_obj.special_features = json.dumps(bullet_points)
            else:
                prod_obj.special_features = "[]"

            if "external_product_id_type" in meta:
                prod_obj.product_id_type = meta["external_product_id_type"]

            if "feed_product_type" in meta:
                prod_obj.feed_product_type = meta["feed_product_type"]

            if "manufacturer" in meta:
                prod_obj.manufacturer = meta["manufacturer"]

            if "package_height" in meta and meta["package_height"] != "":
                prod_obj.package_height = float(meta["package_height"])

            if "package_length" in meta and meta["package_length"] != "":
                prod_obj.package_length = float(meta["package_length"])

            if "package_length_measurement" in meta:
                prod_obj.package_length_metric = meta[
                    "package_length_measurement"]

            if "package_weight" in meta and meta["package_weight"] != "":
                prod_obj.package_weight = float(meta["package_weight"])

            if "package_weight_measurement" in meta:
                prod_obj.package_weight_metric = meta[
                    "package_weight_measurement"]

            if "package_width" in meta and meta["package_width"] != "":
                prod_obj.package_width = float(meta["package_width"])

            if "package_width_measurement" in meta:
                prod_obj.package_width_metric = meta[
                    "package_width_measurement"]

            if "update_delete" in meta:
                prod_obj.update_delete = meta["update_delete"]

            if "part_number" in meta:
                prod_obj.manufacturer_part_number = meta["part_number"]

            if "product_description" in meta:
                prod_obj.product_description_amazon_uk = meta[
                    "product_description"]
                prod_obj.product_description_amazon_uae = meta[
                    "product_description"]
                prod_obj.product_description_ebay = meta["product_description"]

            product_attributes = []
            for k in range(1, 18):
                if "product_attributes_" + str(k) in meta:
                    product_attributes.append(
                        meta["product_attributes_" + str(k)])
            prod_obj.product_attribute_list_amazon_uk = json.dumps(
                product_attributes)
            prod_obj.product_attribute_list_amazon_uae = json.dumps(
                product_attributes)
            prod_obj.product_attribute_list_ebay = json.dumps(
                product_attributes)

            if "recommended_browse_nodes" in meta:
                prod_obj.recommended_browse_nodes = meta[
                    "recommended_browse_nodes"]

            if "quantity" in meta and meta["quantity"] != "":
                prod_obj.quantity = int(meta["quantity"])

            if "main" in meta and meta["main"] != "":
                s3_url = meta["main"].split("/")[-1]
                s3_url = urllib2.unquote(s3_url)
                image_obj = Image.objects.create(image=s3_url)
                image_bucket_obj = ImageBucket.objects.create(
                    image=image_obj, is_main_image=True)
                prod_obj.main_images.add(image_bucket_obj)

            for k in range(8):
                key = "sub_" + str(k)
                if key in meta and meta[key] != "":
                    s3_url = meta[key].split("/")[-1]
                    s3_url = urllib2.unquote(s3_url)
                    image_obj = Image.objects.create(image=s3_url)
                    image_bucket_obj = ImageBucket.objects.create(
                        image=image_obj, sub_image_index=(k + 1), is_sub_image=True)
                    prod_obj.sub_images.add(image_bucket_obj)

            for k in range(8):
                key = "lifestyle_" + str(k)
                if key in meta and meta[key] != "":
                    s3_url = meta[key].split("/")[-1]
                    s3_url = urllib2.unquote(s3_url)
                    image_obj = Image.objects.create(image=s3_url)
                    prod_obj.lifestyle_images.add(image_obj)

            for k in range(8):
                key = "pfl_" + str(k)
                if key in meta and meta[key] != "":
                    s3_url = meta[key].split("/")[-1]
                    s3_url = urllib2.unquote(s3_url)
                    image_obj = Image.objects.create(image=s3_url)
                    prod_obj.pfl_images.add(image_obj)

            for k in range(8):
                key = "unedited_" + str(k)
                if key in meta and meta[key] != "":
                    s3_url = meta[key].split("/")[-1]
                    s3_url = urllib2.unquote(s3_url)
                    image_obj = Image.objects.create(image=s3_url)
                    prod_obj.unedited_images.add(image_obj)

            for k in range(2):
                key = "diecut_" + str(k)
                if key in meta and meta[key] != "":
                    s3_url = meta[key].split("/")[-1]
                    s3_url = urllib2.unquote(s3_url)
                    image_obj = Image.objects.create(image=s3_url)
                    prod_obj.diecut_images.add(image_obj)

            for k in range(2):
                key = "giftbox_" + str(k)
                if key in meta and meta[key] != "":
                    s3_url = meta[key].split("/")[-1]
                    s3_url = urllib2.unquote(s3_url)
                    image_obj = Image.objects.create(image=s3_url)
                    prod_obj.giftbox_images.add(image_obj)

            for k in range(4):
                key = "white_background_" + str(k)
                if key in meta and meta[key] != "":
                    s3_url = meta[key].split("/")[-1]
                    s3_url = urllib2.unquote(s3_url)
                    image_obj = Image.objects.create(image=s3_url)
                    prod_obj.white_background_images.add(image_obj)

            key = "certificate_0"
            if key in meta and meta[key] != "":
                s3_url = meta[key].split("/")[-1]
                s3_url = urllib2.unquote(s3_url)
                image_obj = Image.objects.create(image=s3_url)
                prod_obj.certificate_images.add(image_obj)

            prod_obj.save()

    except Exception as e:
        import sys
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error ", str(e), str(exc_tb.tb_lineno))
