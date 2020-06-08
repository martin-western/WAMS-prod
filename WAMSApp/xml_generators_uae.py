from WAMSApp.models import *

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

            try:
                brand_name = product_obj.base_product.brand.name
            except Exception as e:
                brand_name = ""

            try:
                product_id_type = product_obj.product_id_type.name
            except Exception as e:
                product_id_type = ""

            product_id = product_obj.product_id
            amazon_uae_product = json.loads(product_obj.channel_product.amazon_uae_product_json)
            product_name = amazon_uae_product["product_name"]
            product_description = amazon_uae_product["product_description"]

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
                                    </DescriptionData>
                                </Product>
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
            price = amazon_uae_product["price"]
            
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
            quantity = amazon_uae_product["quantity"]

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

