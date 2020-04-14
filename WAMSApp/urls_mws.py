from django.conf.urls import url
from WAMSApp import views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [

#################################################################################

############################## MWS URLS #########################################

################################################################################# 

    url(r'^get-matching-products-amazon-uk/$',views.GetMatchingProductsAmazonUKMWS),
    url(r'^get-pricing-of-products-amazon-uk/$',views.GetPricingProductsAmazonUKMWS),
    
    url(r'^get-matching-products-amazon-uae/$',views.GetMatchingProductsAmazonUAEMWS),
    url(r'^get-pricing-of-products-amazon-uae/$',views.GetPricingProductsAmazonUAEMWS),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

"""
{'Id': {'value': 'B07H8N3Y9K'}, 'IdType': {'value': 'ASIN'}, 'status': {'value': 'Success'}, 'Products': {'Product': {'Identifiers': {'MarketplaceASIN': {'MarketplaceId': {'value': 'A1F83G8C2ARO7P'}, 'ASIN': {'value': 'B07H8N3Y9K'}}}, 'AttributeSets': {'ItemAttributes': {'lang': {'value': 'en-GB'}, 'Binding': {'value': 'Garden & Outdoors'}, 'Brand': {'value': 'Geepas'}, 'ItemDimensions': {'Height': {'value': '9.44881888800', 'Units': {'value': 'inches'}}, 'Length': {'value': '12.59842518400', 'Units': {'value': 'inches'}}, 'Width': {'value': '3.54330708300', 'Units': {'value': 'inches'}}}, 'Label': {'value': 'Geepas'}, 'ListPrice': {'Amount': {'value': '67.99'}, 'CurrencyCode': {'value': 'GBP'}}, 'Manufacturer': {'value': 'Geepas'}, 'Model': {'value': 'GT7672'}, 'NumberOfItems': {'value': '1'}, 'PackageDimensions': {'Height': {'value': '3.6220472404', 'Units': {'value': 'inches'}}, 'Length': {'value': '12.5984251840', 'Units': {'value': 'inches'}}, 'Width': {'value': '9.9212598324', 'Units': {'value': 'inches'}}, 'Weight': {'value': '4.8060773116', 'Units': {'value': 'pounds'}}}, 'PackageQuantity': {'value': '1'}, 'PartNumber': {'value': 'GT7672'}, 'ProductGroup': {'value': 'Lawn & Patio'}, 'ProductTypeName': {'value': 'OUTDOOR_LIVING'}, 'Publisher': {'value': 'Geepas'}, 'SmallImage': {'URL': {'value': 'http://ecx.images-amazon.com/images/I/41WlOLfHXOL._SL75_.jpg'}, 'Height': {'value': '75', 'Units': {'value': 'pixels'}}, 'Width': {'value': '75', 'Units': {'value': 'pixels'}}}, 'Studio': {'value': 'Geepas'}, 'Title': {'value': 'Geepas 13 Pcs Cordless Drill Driver with Hammer Function - A Universal DIY Tool for Use in A Wide Range of Construction and Repair Tasks'}}}, 'Relationships': {}, 'SalesRankings': {}}}} 







<?xml version="1.0"?>
<AmazonEnvelope xsi:noNamespaceSchemaLocation="amzn-envelope.xsd"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <Header>
        <DocumentVersion>1.01</DocumentVersion>
        <MerchantIdentifier>A3DNFJ8JVFH39T</MerchantIdentifier>
    </Header>
    <MessageType>Product</MessageType>
    <PurgeAndReplace>false</PurgeAndReplace>
    <Message>
        <MessageID>1</MessageID>
        <OperationType>Update</OperationType> 
        <Product>
            <SKU>RF1666-G</SKU>
            <StandardProductID>
                <Type>ASIN</Type>
                <Value>B07MWYBV31</Value>
            </StandardProductID>
            <Condition>
                <ConditionType>New</ConditionType>
            </Condition>
        </Product>
    </Message>
    <Message>
        <MessageID>2</MessageID>
        <OperationType>Update</OperationType>
        <Product>
            <SKU>115280</SKU>
            <StandardProductID>
                <Type>ASIN</Type>
                <Value>B008KYQ8V8</Value>
            </StandardProductID>
            <Condition>
                <ConditionType>New</ConditionType>
            </Condition>
        </Product>
    </Message>
    <Message>
        <MessageID>3</MessageID>
        <OperationType>Update</OperationType>
        <Product>
            <SKU>1018125</SKU>
            <StandardProductID>
                <Type>ASIN</Type>
                <Value>B07QFQLGC8</Value>
            </StandardProductID>
            <Condition>
                <ConditionType>New</ConditionType>
            </Condition>
        </Product>
    </Message>
    <Message>
        <MessageID>3</MessageID>
        <OperationType>Update</OperationType>
        <Product>
            <SKU>253299</SKU>
            <StandardProductID>
                <Type>UPC</Type>
                <Value>313131313131</Value>
            </StandardProductID>
            <Condition>
                <ConditionType>New</ConditionType>
            </Condition>
        </Product>
    </Message>

</AmazonEnvelope>

"""