from WAMSApp.models import *
from django.db.models import Count

duplicates = Product.objects.values("product_id").annotate(Count('product_id')).filter(product_id__count__gt=1).exclude(product_id="")

cnt =0

for duplicate in duplicates:

    product_name = ""
    max_len_product_name = 0
    product_description = ""
    max_len_product_description = 0
    product_id = ""
    barcode_string = product_id
    pfl_product_features = []
    min_price = 0.0
    max_price = 0.0
    
    product_objs = Product.objects.filter(product_id=duplicate["product_id"])
    final_prod_obj = product_objs[0]

    flag=0
    for p in product_objs:
        if(len(p.product_name)>max_len_product_name):
            max_len_product_name = len(p.product_name)
            product_name = p.product_name

        if(len(p.product_description)>max_len_product_description):
            max_len_product_description = len(p.product_description)
            product_description = p.product_description

        pfl_features = json.loads(p.pfl_product_features)

        if(len(pfl_features) >len(pfl_product_features)):
            pfl_product_features = pfl_features

        if p.min_price != min_price:
            min_price = p.min_price

        if p.max_price != max_price:
            max_price = p.max_price

        if p.no_of_images_for_filter > 0 and flag==0:
            final_prod_obj = p
            flag=1
        elif p.no_of_images_for_filter >0:
            flag=2
    
    if flag==2:
        final_prod_obj = None

    if final_prod_obj != None:
        
        final_prod_obj.product_name = product_name
        final_prod_obj.product_description = product_description
        final_prod_obj.product_name_sap = product_name
        final_prod_obj.pfl_product_name = product_name
        final_prod_obj.barcode_string = product_id
        final_prod_obj.min_price = min_price
        final_prod_obj.max_price = max_price
        final_prod_obj.pfl_product_features = json.dumps(pfl_product_features)


        try :
            category = final_prod_obj.base_product.category.name
        except Exception as e:
            category = ""

        try :
            sub_category = final_prod_obj.base_product.sub_category.name
        except Exception as e:
            sub_category = ""

        channel_product_obj = ChannelProduct.objects.get(product=final_prod_obj)

        uk = json.loads(channel_product_obj.amazon_uk_product_json)
        
        uk["product_name"] = product_name
        uk["product_description"] = product_description
        uk["category"] = category
        uk["sub_category"] = sub_category
        
        channel_product_obj.amazon_uk_product_json = json.dumps(uk)
        channel_product_obj.is_amazon_uk_product_created = True

        uae = json.loads(channel_product_obj.amazon_uae_product_json)
        
        uae["product_name"] = product_name
        uae["product_description"] = product_description
        uae["category"] = category
        uae["sub_category"] = sub_category

        channel_product_obj.amazon_uae_product_json = json.dumps(uae)
        channel_product_obj.is_amazon_uae_product_created = True

        ebay = json.loads(channel_product_obj.ebay_product_json)
        
        ebay["product_name"] = product_name
        ebay["product_description"] = product_description
        ebay["category"] = category
        ebay["sub_category"] = sub_category

        channel_product_obj.ebay_product_json = json.dumps(ebay)
        channel_product_obj.is_ebay_product_created = True

        noon = json.loads(channel_product_obj.noon_product_json)
        
        noon["product_name"] = product_name
        noon["product_description"] = product_description
        noon["category"] = category
        noon["sub_category"] = sub_category

        channel_product_obj.noon_product_json = json.dumps(noon)
        channel_product_obj.is_noon_product_created = True

        channel_product_obj.save()

        # print(final_prod_obj.__dict__)
        final_prod_obj.save()
        

        for p in product_objs:
            if p.pk != final_prod_obj.pk:
                chan = ChannelProduct.objects.get(product=p)
                cnt +=1
                # print(p.no_of_images_for_filter)
                # print(p.base_product.brand.name)
                chan.delete()
                p.delete()

print("Cnt :",cnt)