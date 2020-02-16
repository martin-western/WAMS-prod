from io import BytesIO
from PIL import Image as IMage
from django.core.files.uploadedfile import InMemoryUploadedFile
import urllib.request
from WAMSApp.models import *
from dealshub.models import *
import pandas as pd
import numpy as np
import json
path = "upload-dealshub/Urban_Garments/Flat.File.Clothing.ae - NEW.xlsm"
dfs = pd.read_excel(path, sheet_name=None)["Template"]
rows = len(dfs.iloc[:])
org = Organization.objects.get(name="Urban Garments")
cnt=0
for i in range(2, rows):
    try:
        category = dfs.iloc[i][0]
        seller_sku = dfs.iloc[i][1]
        brand_name = dfs.iloc[i][2]
        # product_id = dfs.iloc[i][3]
        # product_id_type = dfs.iloc[i][4]
        # product_id_type = "EAN"
        product_name = dfs.iloc[i][5]
        product_description = dfs.iloc[i][6]
        material_type = dfs.iloc[i][7]
        recommended_browse_nodes = dfs.iloc[i][12]
        standard_price = dfs.iloc[i][42]
        quantity = dfs.iloc[i][43]
        url = dfs.iloc[i][47]
        url2 = dfs.iloc[i][64]
        manufacturer_part_number = dfs.iloc[i][79]
        bullet_point1 = dfs.iloc[i][98]
        bullet_point2 = dfs.iloc[i][99]
        bullet_point3 = dfs.iloc[i][100]
        bullet_point4 = dfs.iloc[i][101]
        bullet_point5 = dfs.iloc[i][102]
        search_terms = dfs.iloc[i][103]
        brand , c= Brand.objects.get_or_create(name=brand_name,organization=org)
        # image_obj , c= Image.objects.get_or_create(image)
        # brand = Brand.objects.create(name=brand_name,organization=org)
        material_type , created = MaterialType.objects.get_or_create(name=material_type)
        base_product_obj , c= BaseProduct.objects.get_or_create(seller_sku=seller_sku,
                                                      manufacturer_part_number=manufacturer_part_number,
                                                      manufacturer=manufacturer_name,
                                                      base_product_name=product_name,
                                                      category=category)
        base_product_obj.brand=brand
        base_product_obj.save()
        product_obj,c = Product.objects.get_or_create(base_product = base_product_obj,
                                             material_type=material_type,
                                             standard_price=standard_price,
                                             quantity=quantity)
        product_obj.product_name=product_name
        product_obj.save()
        try:
            req = urllib.request.Request(
                url, 
                data=None, 
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
                }
            )
            f = urllib.request.urlopen(req)
            infile = url.split("/")[-1] # Extract filename from url
            thumb = IMage.open(f)
            im_type = thumb.format
            thumb_io = BytesIO()
            thumb.save(thumb_io, format=im_type)
            thumb_file = InMemoryUploadedFile(thumb_io, None, infile, 'image/'+im_type, thumb_io.getbuffer().nbytes, None)
            image_obj , c= Image.objects.get_or_create(image=thumb_file)
            image_bucket_obj,c = ImageBucket.objects.get_or_create(image=image_obj,is_main_image=True)
            main_image_obj,c = MainImages.objects.get_or_create(product = product_obj,is_sourced=True)
            main_image_obj.main_images.add(image_bucket_obj)
            main_image_obj.save()
            channel_obj = Channel.objects.get(name="Amazon UK")
            main_image_obj , c= MainImages.objects.get_or_create(product = product_obj,channel=channel_obj)
            main_image_obj.main_images.add(image_bucket_obj)
            main_image_obj.save()
        except Exception as e:
            print(str(e))
            pass
        try:
            req = urllib.request.Request(
                url2, 
                data=None, 
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
                }
            )
            f = urllib.request.urlopen(req)
            infile = url2.split("/")[-1] # Extract filename from url
            thumb = IMage.open(f)
            im_type = thumb.format
            thumb_io = BytesIO()
            thumb.save(thumb_io, format=im_type)
            thumb_file = InMemoryUploadedFile(thumb_io, None, infile, 'image/'+im_type, thumb_io.getbuffer().nbytes, None)
            image_obj , c= Image.objects.get_or_create(image=thumb_file)
            image_bucket_obj,c = ImageBucket.objects.get_or_create(image=image_obj,is_main_image=True)
            main_image_obj,c = MainImages.objects.get_or_create(product = product_obj,is_sourced=True)
            main_image_obj.main_images.add(image_bucket_obj)
            main_image_obj.save()
            channel_obj = Channel.objects.get(name="Amazon UK")
            main_image_obj , c= MainImages.objects.get_or_create(product = product_obj,channel=channel_obj)
            main_image_obj.main_images.add(image_bucket_obj)
            main_image_obj.save()
        except Exception as e:
            print(str(e))
            pass
        channel_product = product_obj.channel_product
        amazon_uk = json.loads(channel_product.amazon_uk_product_json)
        amazon_uk["product_description"] = product_description
        amazon_uk["recommended_browse_nodes"] = recommended_browse_nodes
        amazon_uk["search_terms"] = search_terms
        if type(bullet_point1) == str:
            amazon_uk["product_attribute_list"].append(bullet_point1)
        if type(bullet_point2) == str:
            amazon_uk["product_attribute_list"].append(bullet_point2)
        if type(bullet_point3) == str:
            amazon_uk["product_attribute_list"].append(bullet_point3)
        if type(bullet_point4) == str:
            amazon_uk["product_attribute_list"].append(bullet_point4)
        if type(bullet_point5) == str:
            amazon_uk["product_attribute_list"].append(bullet_point5)
        channel_product.amazon_uk_product_json = json.dumps(amazon_uk)
        channel_product.is_amazon_uk_product_created = True
        channel_product.save()
        cnt+=1
        print("Cnt : ",cnt)
    except Exception as e:
        print(str(e))
        pass