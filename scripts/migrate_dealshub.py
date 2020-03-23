from WAMSApp.models import *
import json
import pandas as pd
import StringIO
from PIL import Image as IMage
from django.core.files.uploadedfile import InMemoryUploadedFile
import urllib2


path = "/home/ubuntu/WAMS-prod/WAMS/amazon-uk-products.xlsx"
dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
dfs = dfs.fillna('')    
rows = len(dfs.iloc[:])

for i in range(rows):
    try :
        if i<194:
            continue
        seller_sku = dfs.iloc[i][1].encode('utf-8').strip()
        product_obj = Product.objects.get(seller_sku=seller_sku)
        main_image_urls = []
        if type(dfs.iloc[i][14]) == unicode:
            main_image_urls.append(dfs.iloc[i][14].encode('utf-8').strip())
        if type(dfs.iloc[i][15]) == unicode:
            main_image_urls.append(dfs.iloc[i][15].encode('utf-8').strip())
        if type(dfs.iloc[i][16]) == unicode:
            main_image_urls.append(dfs.iloc[i][16].encode('utf-8').strip())
        if type(dfs.iloc[i][17]) == unicode:
            main_image_urls.append(dfs.iloc[i][17].encode('utf-8').strip())
        if type(dfs.iloc[i][18]) == unicode:
            main_image_urls.append(dfs.iloc[i][18].encode('utf-8').strip())
        if type(dfs.iloc[i][19]) == unicode:
            main_image_urls.append(dfs.iloc[i][19].encode('utf-8').strip())
        # print(main_image_urls)
        for url in main_image_urls:
            url = url[ : -1]
            url = url+'1'
            infile = url.split("/")[-1] # Extract filename from url
            thumb = IMage.open(urllib2.urlopen(url))
            im_type = thumb.format
            thumb_io = StringIO.StringIO()
            thumb.save(thumb_io, format=im_type)
            thumb_file = InMemoryUploadedFile(thumb_io, None, infile, 'image/'+im_type, thumb_io.len, None)
            image_obj = Image.objects.create(image=thumb_file)
            image_bucket_obj = ImageBucket.objects.create(
                                    image=image_obj)
            product_obj.main_images.add(image_bucket_obj)

        product_obj.main_images.all()[0].is_main_image=True
        product_obj.save()
        print("Reached Here  ",i,"  ",seller_sku)
    except Exception as e:
        import sys
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Excel index: %s , error: %s at %s", str(i), str(e), str(exc_tb.tb_lineno))
        pass


from WAMSApp.models import *
from dealshub.models import *

DealsHubProduct.objects.filter(product__base_product__brand__name="Geepas").update(is_published=True)
cnt=0
for p in ps:
    p.is_published=True
    p.save()
    cnt+=1
    print("Cnt : ",cnt)


from WAMSApp.models import Product
from dealshub.models import DealsHubProduct, Category, SubCategory
prods = Product.objects.filter(base_product__brand__name="Geepas")
for prod in prods:
    category_obj = None
    category = prod.base_product.category
    if category!="":
        category_obj, created = Category.objects.get_or_create(name=category)
    sub_category_obj = None
    sub_category = prod.base_product.sub_category
    if sub_category!="":
        sub_category_obj, created = SubCategory.objects.get_or_create(name=sub_category, category=category_obj)
    d = DealsHubProduct.objects.filter(product=prod)[0]
    d.category = category_obj
    d.sub_category = sub_category_obj
    d.save()

from WAMSApp.models import *
from WAMSApp.utils import *

Ps = Product.objects.all()
cnt=0
for p in Ps:
    p.no_of_images_for_filter = has_atleast_one_image(p)
    p.save()
    cnt+=1
    print("Cnt : ", cnt)

for i in p:
    k = json.loads(i.pfl_product_features)
    if not isinstance(k,list):
            k = k[1:-1]
            k = list(k.split(","))
            for t in range(len(k)):
                k[t] = k[t].replace("'","")
            k = json.dumps(k)
            i.pfl_product_features = k
            i.save()

C = ChannelProduct.objects.filter(is_amazon_uk_product_created=True)
for c in C:
    uk = json.loads(c.amazon_uk_product_json)
    p = Product.objects.get(channel_product=c)
    p.pfl_product_features = json.dumps(uk["product_attribute_list"])
    p.save()
