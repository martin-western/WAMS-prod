def get_price_range(price):
    if(price < 50):
        return "0-50"
    elif(price < 200):
        return "50-200"
    elif(price < 500):
        return "200-500"
    else:
        return "500+"

def replace_and(string):
    return string.replace("&", "&amp;")

def get_additional_images_url_string(product_obj):
    additional_images_url_string = ""
    try:
        for im in product_obj.product.lifestyle_images.all()[1:3]:
            additional_images_url_string += "<g:additional_image_link>"+str(im.mid_image.url)+"</g:additional_image_link>\n"
    except Exception as e:
        pass
    return additional_images_url_string

def get_image_url_string(image_url):
    return '<g:image_link>'+str(image_url)+'</g:image_link>\n'

def get_color_string(product_obj):
    if(product_obj.product.color!=""):
        return ""
    color_string =  '<g:color>'+replace_and(product_obj.product.color)+'</g:color>\n'
    return color_string

def get_material_string(product_obj):
    if(product_obj.product.material_type == None or product_obj.product.material_type.name == ""):
        return ""
    material_string =  '<g:material>'+replace_and(product_obj.product.material_type.name)+'</g:material>\n'
    return material_string

def get_product_type_string(product_obj):
    product_type_string = ""
    try:
        product_type_string = '<g:product_type>'+replace_and(product_obj.product.base_product.category.super_category.name)+' &gt; '+replace_and(product_obj.product.base_product.category.name)+' &gt; '+replace_and(product_obj.product.base_product.sub_category.name)+'</g:product_type>\n'
    except Exception as e:
        product_type_string = ""
    return product_type_string

def get_item_group_id_string(product_obj):
    item_group_id_string = ""
    if(Product.objects.filter(base_product=product_obj.product.base_product).count() > 1):
        item_group_id_string = '<g:item_group_id>'+str(product_obj.get_seller_sku())+'</g:item_group_id>\n'
    return item_group_id_string

def get_availability_string(product_obj):
    if(product_obj.stock==0):
        return '<g:availability>out of stock</g:availability>\n'
    return '<g:availability>in stock</g:availability>\n'

def get_description_string(product_obj):
    from bs4 import BeautifulSoup
    import unicodedata
    description = product_obj.product.product_description
    soup = BeautifulSoup(description)
    description = unicodedata.normalize("NFKD", soup.get_text())
    description = replace_and(description)
    if description.strip()=="":
        description = product_name = product_obj.get_name().strip().lower()
    return '<g:description>'+str(description)+'</g:description>\n'

def get_product_name_algo(product_name):
    product_name_new = ""
    prev = ""
    for char in product_name:
        if(char.isdigit() or char.isalpha() or char == " "):
            if(char == " "):
                if(prev == "-"):
                    continue
                char = "-"
            product_name_new += char
            prev = char
    product_name_new = product_name_new.strip('-')
    return product_name_new

def get_product_title_string(product_name):
    return '<g:title>'+replace_and(product_name[:130].title())+'</g:title>\n'

def get_g_id_string(product_obj):
    g_id = product_obj.product.product_id
    if g_id==None or str(g_id)=="":
        g_id = product_obj.uuid.replace("-", "")[:40]
    return '<g:id>'+str(g_id)+'</g:id>\n'

def get_product_link_string(product_obj):
    product_name_algo = get_product_name_algo(product_obj)
    return '<g:link>'+"https://www.wigme.com/"+ product_name_algo +"-productId"+str(product_obj.product.uuid)+'</g:link>\n'

def get_price_range_string(product_obj):
    return '<g:custom_label_0>'+str(get_price_range(product_obj.now_price))+'</g:custom_label_0>\n'

def get_now_price_string(product_obj):
    return '<g:sale_price>'+str(product_obj.now_price)+" "+product_obj.get_currency()+'</g:sale_price>\n'

def get_was_price_string(product_obj):
    return '<g:price>'+str(product_obj.was_price)+" "+product_obj.get_currency()+'</g:price>\n'

def get_mpn_string(product_obj):
    return '<g:mpn>'+str(product_obj.product.product_id)+'</g:mpn>\n'

def get_brand_string(product_obj):
    return '<g:brand>'+str(product_obj.get_brand())+'</g:brand>\n'

def generate_product_feed_xml():
    from WAMSApp.models import MainImages, Product, Config, LocationGroup
    from dealshub.models import DealsHubProduct
    
    import unicodedata
    import sys
    dummy_image_404 = Config.objects.all()[0].product_404_image.image.url
    try:
        cnt = 0
        a_cnt = 0
        xml_string = '<?xml version="1.0"?>\n\
                          <rss xmlns:g="http://base.google.com/ns/1.0" version="2.0">\n\
                              <channel>\n\
                                  <title>Wigme Store</title>\n\
                                  <link rel="self" href="http://wigme.com"/>\n'
        for product_obj in DealsHubProduct.objects.filter(is_published=True, product__base_product__brand__in=website_group_obj.brands.all(), location_group=LocationGroup.objects.first()).exclude(now_price=0).exclude(stock=0):
            cnt += 1
            print("cnt ", cnt)
            
            image_url = product_obj.get_display_image_url()
            if image_url==dummy_image_404:
                continue

            a_cnt += 1

            image_url_string = get_image_url_string(image_url)
            additional_images_url_string = get_additional_images_url(product_obj)
            color_string = get_color_string(product_obj)
            material_string = get_material_string(product_obj)
            product_type_string = get_product_type_string(product_obj)
            item_group_id_string = get_item_group_id_string(product_obj)

            product_name = product_obj.get_name().strip().lower()
            
            product_name_title_string = get_product_title_string(product_name)
            availability_string = get_availability_string(product_obj)
            description_string = get_description_string(product_obj)
            g_id_string = get_g_id_string(product_obj)
            product_link_string = get_product_link_string(product_obj)
            price_range_string = get_price_range_string(product_obj)
            now_price_string = get_now_price_string(product_obj)
            was_price_string = get_was_price_string(product_obj)
            mpn_string = get_mpn_string(product_obj)
            brand_string = get_brand_string(product_obj)

            ##############################################
            xml_string += '<item>\n'
            xml_string += item_group_id_string
            xml_string += material_string
            xml_string += product_type_string
            xml_string += color_string
            xml_string += g_id_string
            xml_string += product_name_title_string
            xml_string += description_string
            xml_string += product_link_string
            xml_string += image_url_string
            xml_string += additional_images_url_string
            xml_string += '<g:condition>new</g:condition>\n'
            xml_string += price_range_string
            xml_string += availability_string
            xml_string += was_price_string
            xml_string += now_price_string
            xml_string += mpn_string
            xml_string += brand_string
            xml_string += '</item>\n'

        xml_string += '</channel>\n\
                    </rss>'
        f = open("product_feed_xml.xml","w")
        f.write(xml_string)
        f.close()
        print("xml feed prod cnt: ", a_cnt)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("FetchProductDetailsAPI: %s at %s", str(e), str(exc_tb.tb_lineno))

generate_product_feed_xml()