from WAMSApp.models import *
from WAMSApp.utils import *

def generate_xml_for_post_product_data_amazon_uae(product_pk_list,seller_id):
    try:
         # Check if Cached
        xml_string = """<?xml version="1.0"?>
                        <AmazonEnvelope xsi:noNamespaceSchemaLocation="amzn-envelope.xsd"
                            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                            <Header>
                                <DocumentVersion>1.01</DocumentVersion>
                                <MerchantIdentifier>"""+seller_id+"""</MerchantIdentifier>
                            </Header>
                            <MessageType>Product</MessageType>
                            <PurgeAndReplace>false</PurgeAndReplace>"""
        
        for product_pk in product_pk_list:

            product_obj = Product.objects.get(pk=int(product_pk))
            message_id = str(product_pk)
            seller_sku = product_obj.base_product.seller_sku
            
            brand_name = ""
            product_id_type = ""
            product_id = ""

            try:
                brand_name = product_obj.base_product.brand.name
            except Exception as e:
                brand_name = ""

            try:
                product_id_type = product_obj.product_id_type.name
            except Exception as e:
                product_id_type = "EAN"

            try:
                product_id = str(product_obj.product_id)
            except Exception as e:
                product_id = ""

            amazon_uae_product = json.loads(product_obj.channel_product.amazon_uae_product_json)
            product_name = amazon_uae_product["product_name"]
            product_description = amazon_uae_product["product_description"]

            category = amazon_uae_product["category"]
            sub_category = amazon_uae_product["sub_category"]

            if(amazon_uae_product["recommended_browse_nodes"] != ""):
                amazon_uae_product["recommended_browse_nodes"] = get_recommended_browse_node(seller_sku,"Amazon UAE")

            product_obj.channel_product.amazon_uae_product_json = json.dumps(amazon_uae_product)
            product_obj.channel_product.save()

            xml_string += """<Message>
                                <MessageID>"""+ message_id +"""</MessageID>
                                <OperationType>Update</OperationType> 
                                <Product>
                                    <SKU>"""+ seller_sku +"""</SKU>
                                    <StandardProductID>
                                        <Type>"""+product_id_type+"""</Type>
                                        <Value>"""+product_id +"""</Value>
                                    </StandardProductID>
                                    <Condition>
                                        <ConditionType>New</ConditionType>
                                    </Condition>
                                    <DescriptionData>
                                        <Title>"""+ product_name + """</Title>
                                        <Brand>""" + brand_name +"""</Brand>
                                        <Manufacturer>""" + brand_name +"""</Manufacturer>"""
            
            if(amazon_uae_product["recommended_browse_nodes"] != ""):
                xml_string += """<RecommendedBrowseNode>"""+amazon_uae_product["recommended_browse_nodes"]+"""</RecommendedBrowseNode>"""

            xml_string += """</DescriptionData>"""

            if(category != "" and sub_category != ""):

                xml_string += """<ProductData>
                            <""" +category+""">
                                <ProductType>
                                    <"""+sub_category+""">
                                    </"""+sub_category+""">
                                </ProductType>
                            </""" +category+""">
                            </ProductData>"""


            xml_string += """</Product>
                            </Message> """

        xml_string += """</AmazonEnvelope>"""
        xml_string = xml_string.encode('utf-8')
        # print(xml_string)
        return xml_string

    except Exception as e:
        print(str(e))
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Generating XML for Post Product Data UAE: %s at %s", e, str(exc_tb.tb_lineno))
        return ""


def generate_xml_for_partial_update_product_amazon_uae(product_pk_list,seller_id):

    try:
         # Check if Cached
        xml_string = """<?xml version="1.0"?>
                        <AmazonEnvelope xsi:noNamespaceSchemaLocation="amzn-envelope.xsd"
                            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                            <Header>
                                <DocumentVersion>1.01</DocumentVersion>
                                <MerchantIdentifier>"""+seller_id+"""</MerchantIdentifier>
                            </Header>
                            <MessageType>Product</MessageType>
                            <PurgeAndReplace>false</PurgeAndReplace>"""
        
        for product_pk in product_pk_list:

            product_obj = Product.objects.get(pk=int(product_pk))
            message_id = str(product_pk)
            seller_sku = product_obj.base_product.seller_sku
            
            brand_name = ""
            product_id_type = ""
            product_id = ""

            try:
                brand_name = product_obj.base_product.brand.name
            except Exception as e:
                brand_name = ""

            try:
                product_id_type = product_obj.product_id_type.name
            except Exception as e:
                product_id_type = "EAN"

            try:
                product_id = str(product_obj.product_id)
            except Exception as e:
                product_id = ""

            amazon_uae_product_dict = json.loads(product_obj.channel_product.amazon_uae_product_json)
            product_name = amazon_uae_product_dict["product_name"]
            product_description = amazon_uae_product_dict["product_description"]

            base_dimensions_dict = json.loads(product_obj.base_product.dimensions)
            product_dimension_l_metric = base_dimensions_dict["product_dimension_l_metric"]
            product_dimension_b_metric = base_dimensions_dict["product_dimension_b_metric"]
            product_dimension_h_metric = base_dimensions_dict["product_dimension_h_metric"]

            product_dimension_l = str(base_dimensions_dict["product_dimension_l"])
            product_dimension_b = str(base_dimensions_dict["product_dimension_b"])
            product_dimension_h = str(base_dimensions_dict["product_dimension_h"])

            category = amazon_uae_product_dict["category"]
            sub_category = amazon_uae_product_dict["sub_category"]

            if(amazon_uae_product["recommended_browse_nodes"] != ""):
                amazon_uae_product_dict["recommended_browse_nodes"] = get_recommended_browse_node(seller_sku,"Amazon UAE")
            
            product_obj.channel_product.amazon_uae_product_json = json.dumps(amazon_uae_product_dict)
            product_obj.channel_product.save()

            xml_string += """<Message>
                                <MessageID>"""+ message_id +"""</MessageID>
                                <OperationType>PartialUpdate</OperationType> 
                                <Product>
                                    <SKU>"""+ seller_sku +"""</SKU>
                                    <DescriptionData>
                                        <Title>"""+ product_name + """</Title>
                                        <Brand>""" + brand_name +"""</Brand>
                                        <Manufacturer>""" + brand_name +"""</Manufacturer>
                                        <Description><![CDATA["""+product_description+"""]]></Description>"""

            for attribute in amazon_uae_product_dict["product_attribute_list"]:

                xml_string += """<BulletPoint><![CDATA["""+attribute+"""]]></BulletPoint>"""
            
            if(product_dimension_l != "" or product_dimension_b != "" or product_dimension_h != ""):
                xml_string += """<ItemDimensions>"""

            if(product_dimension_l != ""):
                xml_string += '<Length unitOfMeasure="'+product_dimension_l_metric+'">'+product_dimension_l+'</Length>'

            if(product_dimension_b != ""):
                xml_string += '<Width unitOfMeasure="'+product_dimension_b_metric+'">'+product_dimension_b+'</Width>'

            if(product_dimension_h != ""):
                xml_string += '<Height unitOfMeasure="'+product_dimension_h_metric+'">'+product_dimension_h+'</Height>'

            if(product_dimension_l != "" or product_dimension_b != "" or product_dimension_h != ""):
                xml_string += """</ItemDimensions>"""

            if(amazon_uae_product_dict["recommended_browse_nodes"] != ""):
                xml_string += """<RecommendedBrowseNode>"""+amazon_uae_product_dict["recommended_browse_nodes"]+"""</RecommendedBrowseNode>"""
                  
            xml_string += """</DescriptionData>"""

            if(category != "" and sub_category != ""):

                xml_string += """<ProductData>
                            <""" +category+""">
                                <ProductType>
                                    <"""+sub_category+""">
                                    </"""+sub_category+""">
                                </ProductType>
                            </""" +category+""">
                            </ProductData>"""

            xml_string += """</Product>
                            </Message> """

        xml_string +=  '</AmazonEnvelope>'
        print(xml_string)
        xml_string = xml_string.encode('utf-8')

        # print(xml_string)
        return xml_string

    except Exception as e:
        print(str(e))
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Generating XML for Partial Update Product UAE: %s at %s", e, str(exc_tb.tb_lineno))
        return ""


def generate_xml_for_price_data_amazon_uae(product_pk_list,seller_id):
    
    try:
        xml_string = """<?xml version="1.0" encoding="UTF-8"?>
                        <AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="amzn-envelope.xsd">
                        <Header>
                            <DocumentVersion>1.01</DocumentVersion>
                            <MerchantIdentifier>"""+ seller_id+ """</MerchantIdentifier>
                          </Header>
                          <MessageType>Price</MessageType>"""
        
        for product_pk in product_pk_list:

            product_obj = Product.objects.get(pk=int(product_pk))
            message_id = str(product_pk)
            seller_sku = product_obj.base_product.seller_sku
            amazon_uae_product = json.loads(product_obj.channel_product.amazon_uae_product_json)
            price = amazon_uae_product["now_price"]
            
            if price != "":
                price = float(price)
            else:
                price = 0
            
            xml_string += """<Message>
                            <MessageID>"""+ message_id+ """</MessageID>
                            <Price>
                              <SKU>"""+ seller_sku +  """</SKU> 
                              <StandardPrice currency="AED">""" + str(price) + """</StandardPrice>
                            </Price>
                          </Message>"""

        xml_string += """</AmazonEnvelope>"""
        xml_string = xml_string.encode('utf-8')
        
        return xml_string

    except Exception as e:
        print(str(e))
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Price Update XML UAE: %s at %s", e, str(exc_tb.tb_lineno))
        return ""

def generate_xml_for_inventory_data_amazon_uae(product_pk_list,seller_id):
    
    try:
        xml_string = """<?xml version="1.0" encoding="UTF-8"?>
                        <AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="amzn-envelope.xsd">
                          <Header>
                            <DocumentVersion>1.01</DocumentVersion>
                            <MerchantIdentifier>"""+ seller_id+ """</MerchantIdentifier>
                          </Header>
                          <MessageType>Inventory</MessageType>"""
        
        for product_pk in product_pk_list:

            product_obj = Product.objects.get(pk=int(product_pk))
            message_id = str(product_pk)
            seller_sku = product_obj.base_product.seller_sku
            amazon_uae_product = json.loads(product_obj.channel_product.amazon_uae_product_json)
            quantity = amazon_uae_product["stock"]

            if quantity != "":
                quantity = int(quantity)
            else:
                quantity = 0
            
            xml_string += """<Message>
                            <MessageID>"""+ message_id+ """</MessageID>
                            <OperationType>Update</OperationType>
                                <Inventory>
                                  <SKU>"""+ seller_sku+ """</SKU>
                                  <Quantity>""" + str(quantity) +"""</Quantity>
                                </Inventory>
                          </Message>"""

        xml_string += """</AmazonEnvelope>"""
        xml_string = xml_string.encode('utf-8')
        
        return xml_string

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Inventory Update XML UAE: %s at %s", e, str(exc_tb.tb_lineno))
        return ""

def generate_xml_for_delete_product_data_amazon_uae(seller_sku_list,seller_id):
    
    try:

        xml_string = """<?xml version="1.0"?>
                        <AmazonEnvelope xsi:noNamespaceSchemaLocation="amzn-envelope.xsd"
                            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                            <Header>
                                <DocumentVersion>1.01</DocumentVersion>
                                <MerchantIdentifier>"""+seller_id+"""</MerchantIdentifier>
                            </Header>
                            <MessageType>Product</MessageType>
                            <PurgeAndReplace>false</PurgeAndReplace>"""
        
        for seller_sku in seller_sku_list:

            xml_string += """<Message>
                            <MessageID>"""+ seller_sku+ """</MessageID>
                            <OperationType>Delete</OperationType>
                            <Product>
                              <SKU>"""+ seller_sku+ """</SKU>
                            </Product>
                          </Message>"""

        xml_string += """</AmazonEnvelope>"""
        xml_string = xml_string.encode('utf-8')
        
        return xml_string

    except Exception as e:
        print(str(e))
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Generating Delete XML UAE: %s at %s", e, str(exc_tb.tb_lineno))
        return ""

def generate_xml_for_product_image_amazon_uae(product_pk_list,seller_id):

    try:

        xml_string = """<?xml version="1.0"?>
                        <AmazonEnvelope xsi:noNamespaceSchemaLocation="amzn-envelope.xsd"
                            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                            <Header>
                                <DocumentVersion>1.01</DocumentVersion>
                                <MerchantIdentifier>"""+seller_id+"""</MerchantIdentifier>
                            </Header>
                            <MessageType>ProductImage</MessageType>
                            <PurgeAndReplace>false</PurgeAndReplace>"""
        message_id = 1

        for product_pk in product_pk_list:

            product_obj = Product.objects.get(pk=int(product_pk))
            seller_sku = product_obj.base_product.seller_sku
                            
            try:

                image_type = "Main"
                image_url = MainImages.objects.get(product=product_obj,channel__name="Amazon UAE").main_images.all()[0].image.image.url

                xml_string += '<Message>\
                <MessageID>'+str(message_id)+'</MessageID>\
                <OperationType>Update</OperationType>\
                <ProductImage>\
                    <SKU>'+seller_sku+'</SKU>\
                    <ImageType>'+image_type+'</ImageType>\
                    <ImageLocation>'+image_url+'</ImageLocation>\
                </ProductImage>\
                </Message>'

                message_id += 1

            except Exception as e:
                
                image_type = "Main"

                xml_string += '<Message>\
                <MessageID>'+str(message_id)+'</MessageID>\
                <OperationType>Delete</OperationType>\
                <ProductImage>\
                    <SKU>'+seller_sku+'</SKU>\
                    <ImageType>'+image_type+'</ImageType>\
                </ProductImage>\
                </Message>'

                message_id += 1

            try:

                count = 1

                for image_bucket in SubImages.objects.get(product=product_obj,channel__name="Amazon UAE").sub_images.all()[:8] :

                    image_type = "PT" + str(count)
                    image_url = image_bucket.image.image.url

                    xml_string += '<Message>\
                    <MessageID>'+str(message_id)+'</MessageID>\
                    <OperationType>Update</OperationType>\
                    <ProductImage>\
                        <SKU>'+seller_sku+'</SKU>\
                        <ImageType>'+image_type+'</ImageType>\
                        <ImageLocation>'+image_url+'</ImageLocation>\
                    </ProductImage>\
                    </Message>'

                    message_id += 1
                    count += 1

                for i in range(count,9):

                    image_type = "PT" + str(i)

                    xml_string += '<Message>\
                    <MessageID>'+str(message_id)+'</MessageID>\
                    <OperationType>Delete</OperationType>\
                    <ProductImage>\
                        <SKU>'+seller_sku+'</SKU>\
                        <ImageType>'+image_type+'</ImageType>\
                    </ProductImage>\
                    </Message>'

                    message_id += 1

            except Exception as e:
                print(e)
                pass

        xml_string +=  '</AmazonEnvelope>'
        xml_string = xml_string.encode('utf-8')
        
        return xml_string

    except Exception as e:
        print(str(e))
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Generating ImagesFeed XML UAE: %s at %s", e, str(exc_tb.tb_lineno))
        return ""