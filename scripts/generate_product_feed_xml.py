from WAMSApp.models import *
from dealshub.models import *

def generate_google_product_feed_xml():

    try:
        xml_string = '<?xml version="1.0"?>\n\
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:g="http://base.google.com/ns/1.0">\n\
        <title>Wigme Store</title>\n\
        <link rel="self" href="http://wigme.com"/>\n'

        for product_obj in DealsHubProduct.objects.filter(is_published=True)[:5]:

            try:
                image = product_obj.product.lifestyle_images.all()[0].image.url
            except Exception as e:
                try:
                    image = MainImages.objects.filter(product=product_obj.product)[0].main_images.all()[0].image.url
                except Exception as e:
                    image = Config.objects.all()[0].product_404_image.image.url

            xml_string += '<entry>\n\
            <g:item_group_id>'+str(product_obj.product.base_product.seller_sku)+'</g:item_group_id>\n\
            <g:id>'+str(product_obj.product.product_id)+'</g:id>\n\
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
        f = open("google_xml.xml","w")
        f.write(xml_string)
        f.close()

    except Exception as e:
        print(str(e))
        # exc_type, exc_obj, exc_tb = sys.exc_info()
        # logger.error("generate_google_product_feed_xml: %s at %s", e, str(exc_tb.tb_lineno))


def generate_facebook_product_feed_xml():

    try:
        xml_string = '<?xml version="1.0"?>\n\
        <rss xmlns="http://www.w3.org/2005/Atom" xmlns:g="http://base.google.com/ns/1.0">\n\
        <channel>\n\
        <title>Wigme Store</title>\n\
        <description>Product Feed for Facebook</description>\n \
        <link rel="self" href="http://wigme.com/">\n'

        for product_obj in DealsHubProduct.objects.filter(is_published=True)[:5]:

            try:
                image = product_obj.product.lifestyle_images.all()[0].image.url
            except Exception as e:
                try:
                    image = MainImages.objects.filter(product=product_obj.product)[0].main_images.all()[0].image.url
                except Exception as e:
                    image = Config.objects.all()[0].product_404_image.image.url

            xml_string += '<item>\n\
                <g:item_group_id>'+str(product_obj.product.base_product.seller_sku)+'</g:item_group_id>\n\
                <g:id>'+str(product_obj.product.product_id)+'</g:id>\n\
                <g:title>'+str(product_obj.product.product_name)+'</g:title>\n\
                <g:description>'+str(product_obj.product.product_description)+'</g:description>\n\
                <g:link>'+"https://www.wigme.com/product-description-new/"+str(product_obj.product.uuid)+'</g:link>\n\
                <g:image_link>'+str(image)+'</g:image_link>\n\
                <g:condition>'+"new"+'</g:condition>\n\
                <g:availability>'+"in stock"+'</g:availability>\n\
                <g:price>'+str(product_obj.now_price)+str(" AED")+'</g:price>\n\
                <g:mpn>'+str(product_obj.product.product_id)+'</g:mpn>\n\
                <g:brand>'+str(product_obj.product.base_product.brand.name)+'</g:brand>\n\
                </item>\n'

        xml_string += "</channel></rss>\n"
        f = open("facebook_xml.xml","w")
        f.write(xml_string)
        f.close()

    except Exception as e:
        print(str(e))
        # exc_type, exc_obj, exc_tb = sys.exc_info()
        # logger.error("generate_facebook_product_feed_xml: %s at %s", e, str(exc_tb.tb_lineno))

generate_facebook_product_feed_xml()