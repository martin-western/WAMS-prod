from WAMSApp.models import *
from dealshub.models import *

import requests

def check_size(url):

    response = requests.head(url, allow_redirects=True)
    size = response.headers.get('content-length', 0)
    
    if(size > 8000000):
         return False
    return True

def generate_product_feed_xml():

    try:
        xml_string = '<?xml version="1.0"?>\n\
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:g="http://base.google.com/ns/1.0">\n\
        <title>Wigme Store</title>\n\
        <link rel="self" href="http://wigme.com"/>\n'

        for product_obj in DealsHubProduct.objects.filter(is_published=True)[:5]:

            try:
                if(check_size(product_obj.product.lifestyle_images.all()[0].image.url)==True):
                    image = product_obj.product.lifestyle_images.all()[0].image.url
                else:
                    image = product_obj.product.lifestyle_images.all()[0].mid_image.url
            except Exception as e:
                try:
                    if(check_size(MainImages.objects.filter(product=product_obj.product)[0].main_images.all()[0].image.url)):
                        image = MainImages.objects.filter(product=product_obj.product)[0].main_images.all()[0].image.url
                    else:
                        image = MainImages.objects.filter(product=product_obj.product)[0].main_images.all()[0].mid_image.url
                except Exception as e:
                    image = Config.objects.all()[0].product_404_image.image.url

            if(product_obj.product.color!=""):
                color_string =  '       <g:color>'+product_obj.product.color+'</g:color>\n'
            else:
                color_string = ""

            try:
                product_type = '        <g:product_type>'+str(product_obj.product.base_product.category.super_category).replace("&","&amp;")+' &gt; '+str(product_obj.product.base_product.category).replace("&","&amp;")+' &gt; '+str(product_obj.product.base_product.sub_category).replace("&","&amp;")+'</g:product_type>\n'
            except Exception as e:
                product_type = ""

            if(Product.objects.filter(base_product=product_obj.product.base_product).count() > 1):
                item_group_id = '       <g:item_group_id>'+str(product_obj.product.base_product.seller_sku)+'</g:item_group_id>\n'
            else:
                item_group_id = ""

            ##############################################

            xml_string += '    <entry>\n'

            if(item_group_id!=""):
                xml_string += item_group_id
            if(product_type !=""):
                xml_string += product_type
            if(color_string!=""):
                xml_string += color_string

            xml_string += '        <g:id>'+str(product_obj.product.product_id)+'</g:id>\n\
        <g:title>'+str(product_obj.product.product_name)+'</g:title>\n\
        <g:description>'+str(product_obj.product.product_description)+'</g:description>\n\
        <g:link>'+"https://www.wigme.com/product-description-new/"+str(product_obj.product.uuid)+'</g:link>\n\
        <g:image_link>'+str(image)+'</g:image_link>\n\
        <g:condition>'+"new"+'</g:condition>\n\
        <g:availability>'+"in stock"+'</g:availability>\n\
        <g:price>'+str(product_obj.now_price)+str(" AED")+'</g:price>\n\
        <g:mpn>'+str(product_obj.product.product_id)+'</g:mpn>\n\
        <g:brand>'+str(product_obj.product.base_product.brand.name)+'</g:brand>\n\
    </entry>\n'

        xml_string += "</feed>\n"
        f = open("product_feed_xml.xml","w")
        f.write(xml_string)
        f.close()

    except Exception as e:
        print(str(e))

generate_product_feed_xml()
