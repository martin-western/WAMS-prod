import pandas as pd
from WAMSApp.models import *
from dealshub.models import *
import urllib
from PIL import Image as IMAGE
import requests
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile

filename = "scripts/Parajohn_products.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]
rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

dfs = dfs.fillna("")
cnt=0

brand_obj, c = Brand.objects.get_or_create(name="Parajohn")

for i in range(5):
    
    print(i)

    try :

        product_name = str(dfs.iloc[i][1])
        seller_sku = str(dfs.iloc[i][3])
        super_category = str(dfs.iloc[i][7])
        category = str(dfs.iloc[i][8])
        sub_category = str(dfs.iloc[i][9])
        product_description = str(dfs.iloc[i][10])
        material = str(dfs.iloc[i][12])

        main_image_url = str(dfs.iloc[i][24])

        if "https" not in main_image_url:
            main_image_url = "https:/"+main_image_url

        sub_image_urls = []

        sub_image_url1 = str(dfs.iloc[i][25])

        if sub_image_url1 != "":
            if "https" not in sub_image_url1:
                sub_image_url1 = "https:/"+sub_image_url1
                sub_image_urls.append(sub_image_url1)

        sub_image_url2 = str(dfs.iloc[i][26])

        if sub_image_url2 != "":
            if "https" not in sub_image_url2:
                sub_image_url2 = "https:/"+sub_image_url2
                sub_image_urls.append(sub_image_url2)

        sub_image_url3 = str(dfs.iloc[i][27])

        if sub_image_url3 != "":
            if "https" not in sub_image_url3:
                sub_image_url3 = "https:/"+sub_image_url3
                sub_image_urls.append(sub_image_url3)

        sub_image_url4 = str(dfs.iloc[i][28])

        if sub_image_url4 != "":
            if "https" not in sub_image_url4:
                sub_image_url4 = "https:/"+sub_image_url4
                sub_image_urls.append(sub_image_url4)

        sub_image_url5 = str(dfs.iloc[i][29])

        if sub_image_url5 != "":
            if "https" not in sub_image_url5:
                sub_image_url5 = "https:/"+sub_image_url5
                sub_image_urls.append(sub_image_url5)

        sub_image_url6 = str(dfs.iloc[i][30])

        if sub_image_url6 != "":
            if "https" not in sub_image_url6:
                sub_image_url6 = "https:/"+sub_image_url6
                sub_image_urls.append(sub_image_url6)

        sub_image_url7 = str(dfs.iloc[i][31])

        if sub_image_url7 != "":
            if "https" not in sub_image_url7:
                sub_image_url7 = "https:/"+sub_image_url7
                sub_image_urls.append(sub_image_url7)

        sub_image_url8 = str(dfs.iloc[i][32])

        if sub_image_url8 != "":
            if "https" not in sub_image_url8:
                sub_image_url8 = "https:/"+sub_image_url8
                sub_image_urls.append(sub_image_url8)

        sub_image_url9 = str(dfs.iloc[i][33])

        if sub_image_url9 != "":
            if "https" not in sub_image_url9:
                sub_image_url9 = "https:/"+sub_image_url9
                sub_image_urls.append(sub_image_url9)

        super_category_obj , c= SuperCategory.objects.get_or_create(name=super_category)
        category_obj , c= Category.objects.get_or_create(name=category, super_category=super_category_obj)
        sub_category_obj , c= SubCategory.objects.get_or_create(name=sub_category, category=category_obj)
        material_type_obj , c= MaterialType.objects.get_or_create(name=material)

        base_product , created = BaseProduct.objects.get_or_create(seller_sku=seller_sku)
        base_product.base_product_name = product_name
        base_product.brand = brand_obj
        base_product.category = category_obj
        base_product.sub_category = sub_category_obj

        base_product.save()

        if Product.objects.filter(base_product=base_product).exists():
            product_obj = Product.objects.filter(base_product=base_product)[0]
        else:
            product_obj = Product.objects.create(base_product=base_product)

        product_obj.product_name = product_name
        product_obj.product_description = product_description
        product_obj.material_type = material_type_obj

        product_obj.save()

        dh_product = DealsHubProduct.objects.create(product=product_obj)

        size = 512, 512 
        response = requests.get(main_image_url)
        thumb = IMAGE.open(BytesIO(response.content))
        thumb.thumbnail(size)
        infile = str(main_image_url.split("/")[-1]) 
        im_type = thumb.format 
        thumb_io = BytesIO()
        thumb.save(thumb_io, format=im_type)
        thumb_file = InMemoryUploadedFile(thumb_io, None, infile, 'image/'+im_type, thumb_io.getbuffer().nbytes, None)
        image_obj = Image.objects.create(image=thumb_file)
        image_bucket_obj = ImageBucket.objects.create(image=image_obj)

        main_images_objs = []

        main_images_obj,c = MainImages.objects.get_or_create(product = product_obj,is_sourced=True)
        main_images_objs.append(main_images_obj)

        chan = Channel.objects.get(name="Amazon UK")
        main_images_obj,c = MainImages.objects.get_or_create(product = product_obj,channel=chan)
        main_images_objs.append(main_images_obj)

        chan = Channel.objects.get(name="Amazon UAE")
        main_images_obj,c = MainImages.objects.get_or_create(product = product_obj,channel=chan)
        main_images_objs.append(main_images_obj)
        
        chan = Channel.objects.get(name="Noon")
        main_images_obj,c = MainImages.objects.get_or_create(product = product_obj,channel=chan)
        main_images_objs.append(main_images_obj)
        
        chan = Channel.objects.get(name="Ebay")
        main_images_obj,c = MainImages.objects.get_or_create(product = product_obj,channel=chan)
        main_images_objs.append(main_images_obj)
        
        for main_images_obj in main_images_objs:
            main_images_obj.main_images.clear()
            main_images_obj.main_images.add(image_bucket_obj)
            main_images_obj.save()

        sub_images_objs = []
        
        sub_images_obj,c = SubImages.objects.get_or_create(product = product_obj,is_sourced=True)
        sub_images_objs.append(sub_images_obj)

        chan = Channel.objects.get(name="Amazon UK")
        sub_images_obj,c = SubImages.objects.get_or_create(product = product_obj,channel=chan)
        sub_images_objs.append(sub_images_obj)

        chan = Channel.objects.get(name="Amazon UAE")
        sub_images_obj,c = SubImages.objects.get_or_create(product = product_obj,channel=chan)
        sub_images_objs.append(sub_images_obj)
        
        chan = Channel.objects.get(name="Noon")
        sub_images_obj,c = SubImages.objects.get_or_create(product = product_obj,channel=chan)
        sub_images_objs.append(sub_images_obj)
        
        chan = Channel.objects.get(name="Ebay")
        sub_images_obj,c = SubImages.objects.get_or_create(product = product_obj,channel=chan)
        sub_images_objs.append(sub_images_obj)
        
        for sub_image_url in sub_image_urls:

            size = 512, 512 
            response = requests.get(sub_image_url)
            thumb = IMAGE.open(BytesIO(response.content))
            thumb.thumbnail(size)
            infile = str(sub_image_url.split("/")[-1]) 
            im_type = thumb.format 
            thumb_io = BytesIO()
            thumb.save(thumb_io, format=im_type)
            thumb_file = InMemoryUploadedFile(thumb_io, None, infile, 'image/'+im_type, thumb_io.getbuffer().nbytes, None)
            image_obj = Image.objects.create(image=thumb_file)
            image_bucket_obj = ImageBucket.objects.create(image=image_obj)
            
            for sub_images_obj in sub_images_objs:
                sub_images_obj.sub_images.add(image_bucket_obj)
                sub_images_obj.save()
    
    except Exception as e:
        print(str(e))
        pass
