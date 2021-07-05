import pandas as pd
from WAMSApp.models import *
from dealshub.models import *
import urllib
from PIL import Image as IMAGE
import requests
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile

filename = "scripts/Krypton_Data_Hari.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]
dfs.loc[:, 'Updated/Not Found'] = ""

rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])
dfs = dfs.fillna("")

cnt=0
brand_obj = Brand.objects.get(name="Krypton")

for i in range(rows):
    print(i)
    try:
        
        seller_sku = str(dfs.iloc[i,0])
        product_name = str(dfs.iloc[i,1])
        product_description = str(dfs.iloc[i,2])
        featurs_list = str(dfs.iloc[i,3])
        product_id = str(dfs.iloc[i,4])

        if product_id != "":
            product_id = product_id.split(".")
            product_id = product_id[0] 
            product_id = str(int(product_id))
        
        super_category = str(dfs.iloc[i,5])

        if super_category == "Tools & Home Improvement":
            super_category= "Home Tools"

        category = str(dfs.iloc[i,6])
        sub_category = str(dfs.iloc[i,7])
        
        pl = dfs.iloc[i,9]
        if pl != "":
            pl = float(pl)

        ph = dfs.iloc[i,10]
        if ph != "":
            ph = float(ph)

        pb = dfs.iloc[i,11]
        if pb != "":
            pb = float(pb)

        iw = dfs.iloc[i,12]
        if iw != "":
            iw = float(iw)

        gl = dfs.iloc[i,13]
        if gl != "":
            gl = float(gl)

        gh = dfs.iloc[i,14]
        if gh != "":
            gh = float(gh)

        gb = dfs.iloc[i,15]
        if gb != "":
            gb = float(gb)

        sw = dfs.iloc[i,16]
        if sw != "":
            sw = float(sw)


        featurs_list = featurs_list.split("•")[1:]
        for f in range(len(featurs_list)):
            featurs_list[f] = featurs_list[f].replace("\n","").lstrip()
        
        base_dimensions_json = {
            "export_carton_quantity_l": "",
            "export_carton_quantity_l_metric": "",
            "export_carton_quantity_b": "",
            "export_carton_quantity_b_metric": "",
            "export_carton_quantity_h": "",
            "export_carton_quantity_h_metric": "",
            "export_carton_crm_l": "",
            "export_carton_crm_l_metric": "",
            "export_carton_crm_b": "",
            "export_carton_crm_b_metric": "",
            "export_carton_crm_h": "",
            "export_carton_crm_h_metric": "",
            "product_dimension_l": pl,
            "product_dimension_l_metric": "cm",
            "product_dimension_b": pb,
            "product_dimension_b_metric": "cm",
            "product_dimension_h": ph,
            "product_dimension_h_metric": "cm",
            "giftbox_l": gl,
            "giftbox_l_metric": "cm",
            "giftbox_b": gb,
            "giftbox_b_metric": "cm",
            "giftbox_h": gh,
            "giftbox_h_metric": "cm"
        }

        base_product , c = BaseProduct.objects.get_or_create(seller_sku=seller_sku)
        base_product.brand=brand_obj
        product , c = Product.objects.get_or_create(base_product=base_product)
        channel_product  = product.channel_product
        uk = json.loads(channel_product.amazon_uk_product_json)
        uae = json.loads(channel_product.amazon_uae_product_json)
        ebay = json.loads(channel_product.ebay_product_json)
        noon = json.loads(channel_product.noon_product_json)
        dh , c = DealsHubProduct.objects.get_or_create(product=product)

        if super_category != "":
            super_category , c = SuperCategory.objects.get_or_create(name=super_category)
        else:
            super_category = None

        if category != "":
            category , c = Category.objects.get_or_create(name=category,super_category=super_category)
            category.super_category=super_category
            category.save()
        else:
            category = None
        
        if sub_category != "":
            sub_category , c = SubCategory.objects.get_or_create(name=sub_category,category=category)
            sub_category.category=category
            sub_category.save()
        else:
            sub_category = None

        if category != None:
            base_product.category=category
            uk["category"] = category.name
            uae["category"] = category.name
            ebay["category"] = category.name
            noon["category"] = category.name

        if sub_category != None:
            base_product.sub_category=sub_category
            uk["sub_category"] = sub_category.name
            uae["sub_category"] = sub_category.name
            ebay["sub_category"] = sub_category.name
            noon["sub_category"] = sub_category.name

        if product_name != "":
            base_product.base_product_name = product_name
            product.product_name = product_name
            uk["product_name"] = product_name
            uae["product_name"] = product_name
            ebay["product_name"] = product_name
            noon["product_name"] = product_name
        
        if product_description != "":
            product.product_description = product_description
            channel_product.is_amazon_uk_product_created = True
            channel_product.is_amazon_uae_product_created = True
            channel_product.is_ebay_product_created = True
            channel_product.is_noon_product_created = True
            uk["product_description"] = product_description
            uae["product_description"] = product_description
            ebay["product_description"] = product_description
            noon["product_description"] = product_description

        if product_id != "":
            product.product_id = product_id
            product.barcode_string = product_id
            
        if len(featurs_list) != 0:
            uk["product_attribute_list"] = featurs_list
            uae["product_attribute_list"] = featurs_list
            ebay["product_attribute_list"] = featurs_list
            noon["product_attribute_list"] = featurs_list
            attribute_list = json.dumps(featurs_list)
            product.pfl_product_features = attribute_list

        uk["dimensions"]["shipping_weight"] = sw
        uk["dimensions"]["shipping_weight_metric"] = "kg"
        uk["dimensions"]["item_weight"] = iw
        uk["dimensions"]["item_weight_metric"] = "kg"
        base_product.dimensions = json.dumps(base_dimensions_json)

        channel_product.amazon_uk_product_json = json.dumps(uk)
        channel_product.amazon_uae_product_json = json.dumps(uae)
        channel_product.ebay_product_json = json.dumps(ebay)
        channel_product.noon_product_json = json.dumps(noon)
        base_product.save()
        product.save()
        channel_product.save()

        main_images_obj,c = MainImages.objects.get_or_create(product = product,is_sourced=True)
        
        if main_images_obj.main_images.all().count()==0:

            print(seller_sku)
            print(product_id)

            main_image_url = str(dfs.iloc[i][17])
            print(main_image_url)

            if main_image_url != "":
                if "http" not in main_image_url and "Https" not in main_image_url:
                    main_image_url = "https:/"+main_image_url
                if "drive" in main_image_url:
                    main_image_url = main_image_url.replace("open","uc")

            print(main_image_url)

            sub_image_urls = []

            sub_image_url1 = str(dfs.iloc[i][18])

            if sub_image_url1 != "":
                if "http" not in sub_image_url1 and "Https" not in sub_image_url1:
                    sub_image_url1 = "https:/"+sub_image_url1
                if "drive" in sub_image_url1:
                    sub_image_url1 = sub_image_url1.replace("open","uc")
                sub_image_urls.append(sub_image_url1)

            sub_image_url2 = str(dfs.iloc[i][19])

            if sub_image_url2 != "":
                if "http" not in sub_image_url2 and "Https" not in sub_image_url2:
                    sub_image_url2 = "https:/"+sub_image_url2
                if "drive" in sub_image_url2:
                    sub_image_url2 = sub_image_url2.replace("open","uc")
                sub_image_urls.append(sub_image_url2)

            sub_image_url3 = str(dfs.iloc[i][20])

            if sub_image_url3 != "":
                if "http" not in sub_image_url3 and "Https" not in sub_image_url3:
                    sub_image_url3 = "https:/"+sub_image_url3
                if "drive" in sub_image_url3:
                    sub_image_url3 = sub_image_url3.replace("open","uc")
                sub_image_urls.append(sub_image_url3)

            sub_image_url4 = str(dfs.iloc[i][21])

            if sub_image_url4 != "":
                if "http" not in sub_image_url4 and "Https" not in sub_image_url4:
                    sub_image_url4 = "https:/"+sub_image_url4
                if "drive" in sub_image_url4:
                    sub_image_url4 = sub_image_url4.replace("open","uc")
                sub_image_urls.append(sub_image_url4)

            sub_image_url5 = str(dfs.iloc[i][22])

            if sub_image_url5 != "":
                if "http" not in sub_image_url5 and "Https" not in sub_image_url5:
                    sub_image_url5 = "https:/"+sub_image_url5
                if "drive" in sub_image_url5:
                    sub_image_url5 = sub_image_url5.replace("open","uc")
                sub_image_urls.append(sub_image_url5)

            sub_image_url6 = str(dfs.iloc[i][23])

            if sub_image_url6 != "":
                if "http" not in sub_image_url5 and "Https" not in sub_image_url6:
                    sub_image_url6 = "https:/"+sub_image_url6
                if "drive" in sub_image_url6:
                    sub_image_url6 = sub_image_url6.replace("open","uc")
                sub_image_urls.append(sub_image_url6)

            if main_image_url != "":
                size = 512, 512 
                response = requests.get(main_image_url, timeout=10)
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

                main_images_obj,c = MainImages.objects.get_or_create(product = product,is_sourced=True)
                main_images_objs.append(main_images_obj)

                chan = Channel.objects.get(name="Amazon UK")
                main_images_obj,c = MainImages.objects.get_or_create(product = product,channel=chan)
                main_images_objs.append(main_images_obj)

                chan = Channel.objects.get(name="Amazon UAE")
                main_images_obj,c = MainImages.objects.get_or_create(product = product,channel=chan)
                main_images_objs.append(main_images_obj)
                
                chan = Channel.objects.get(name="Noon")
                main_images_obj,c = MainImages.objects.get_or_create(product = product,channel=chan)
                main_images_objs.append(main_images_obj)
                
                chan = Channel.objects.get(name="Ebay")
                main_images_obj,c = MainImages.objects.get_or_create(product = product,channel=chan)
                main_images_objs.append(main_images_obj)
                
                for main_images_obj in main_images_objs:
                    main_images_obj.main_images.clear()
                    main_images_obj.main_images.add(image_bucket_obj)
                    main_images_obj.save()

            sub_images_objs = []
            
            sub_images_obj,c = SubImages.objects.get_or_create(product = product,is_sourced=True)
            sub_images_objs.append(sub_images_obj)

            chan = Channel.objects.get(name="Amazon UK")
            sub_images_obj,c = SubImages.objects.get_or_create(product = product,channel=chan)
            sub_images_objs.append(sub_images_obj)

            chan = Channel.objects.get(name="Amazon UAE")
            sub_images_obj,c = SubImages.objects.get_or_create(product = product,channel=chan)
            sub_images_objs.append(sub_images_obj)
            
            chan = Channel.objects.get(name="Noon")
            sub_images_obj,c = SubImages.objects.get_or_create(product = product,channel=chan)
            sub_images_objs.append(sub_images_obj)
            
            chan = Channel.objects.get(name="Ebay")
            sub_images_obj,c = SubImages.objects.get_or_create(product = product,channel=chan)
            sub_images_objs.append(sub_images_obj)
            
            for sub_image_url in sub_image_urls:

                size = 512, 512 
                response = requests.get(sub_image_url, timeout=10)
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

        dfs.loc[i, 'Updated/Not Found'] = "Updated"
        cnt+=1
        # print("Cnt : ",cnt)

    except Exception as e:
        print(str(e))
        dfs.loc[i, 'Updated/Not Found'] = "Not Found"
        pass

dfs.to_excel(filename,index=False)