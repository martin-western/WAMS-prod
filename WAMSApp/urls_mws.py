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

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

"""
{'Id': {'value': 'B07H8N3Y9K'}, 'IdType': {'value': 'ASIN'}, 'status': {'value': 'Success'}, 'Products': {'Product': {'Identifiers': {'MarketplaceASIN': {'MarketplaceId': {'value': 'A1F83G8C2ARO7P'}, 'ASIN': {'value': 'B07H8N3Y9K'}}}, 'AttributeSets': {'ItemAttributes': {'lang': {'value': 'en-GB'}, 'Binding': {'value': 'Garden & Outdoors'}, 'Brand': {'value': 'Geepas'}, 'ItemDimensions': {'Height': {'value': '9.44881888800', 'Units': {'value': 'inches'}}, 'Length': {'value': '12.59842518400', 'Units': {'value': 'inches'}}, 'Width': {'value': '3.54330708300', 'Units': {'value': 'inches'}}}, 'Label': {'value': 'Geepas'}, 'ListPrice': {'Amount': {'value': '67.99'}, 'CurrencyCode': {'value': 'GBP'}}, 'Manufacturer': {'value': 'Geepas'}, 'Model': {'value': 'GT7672'}, 'NumberOfItems': {'value': '1'}, 'PackageDimensions': {'Height': {'value': '3.6220472404', 'Units': {'value': 'inches'}}, 'Length': {'value': '12.5984251840', 'Units': {'value': 'inches'}}, 'Width': {'value': '9.9212598324', 'Units': {'value': 'inches'}}, 'Weight': {'value': '4.8060773116', 'Units': {'value': 'pounds'}}}, 'PackageQuantity': {'value': '1'}, 'PartNumber': {'value': 'GT7672'}, 'ProductGroup': {'value': 'Lawn & Patio'}, 'ProductTypeName': {'value': 'OUTDOOR_LIVING'}, 'Publisher': {'value': 'Geepas'}, 'SmallImage': {'URL': {'value': 'http://ecx.images-amazon.com/images/I/41WlOLfHXOL._SL75_.jpg'}, 'Height': {'value': '75', 'Units': {'value': 'pixels'}}, 'Width': {'value': '75', 'Units': {'value': 'pixels'}}}, 'Studio': {'value': 'Geepas'}, 'Title': {'value': 'Geepas 13 Pcs Cordless Drill Driver with Hammer Function - A Universal DIY Tool for Use in A Wide Range of Construction and Repair Tasks'}}}, 'Relationships': {}, 'SalesRankings': {}}}} 

"""