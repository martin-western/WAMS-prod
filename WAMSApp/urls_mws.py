from django.conf.urls import url
from WAMSApp import views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [

############################## MWS URLS #########################################

############ Amazon UK ###############

    url(r'^push-products-amazon-uk/$',views.PushProductsAmazonUK),
    url(r'^push-products-inventory-amazon-uk/$',views.PushProductsInventoryAmazonUK),
    url(r'^push-products-price-amazon-uk/$',views.PushProductsPriceAmazonUK),
    url(r'^get-matching-products-amazon-uk/$',views.GetMatchingProductsAmazonUK),
    url(r'^get-pricing-of-products-amazon-uk/$',views.GetPricingProductsAmazonUK),
    url(r'^get-product-inventory-amazon-uk/$',views.GetProductInventoryAmazonUK),
    url(r'^fetch-price-and-stock-periodically-amazon-uk',views.FetchPriceAndStockAmazonUK), 
    url(r'^push-product-images-amazon-uk',views.PushProductImagesAmazonUK),

########### Amazon UAE ###############

    url(r'^push-products-amazon-uae/$',views.PushProductsAmazonUAE),
    url(r'^push-products-inventory-amazon-uae/$',views.PushProductsInventoryAmazonUAE),
    url(r'^push-products-price-amazon-uae/$',views.PushProductsPriceAmazonUAE),
    url(r'^get-matching-products-amazon-uae/$',views.GetMatchingProductsAmazonUAE),
    url(r'^get-pricing-of-products-amazon-uae/$',views.GetPricingProductsAmazonUAE),
    url(r'^get-product-inventory-amazon-uae/$',views.GetProductInventoryAmazonUAE),
    url(r'^fetch-price-and-stock-periodically-amazon-uae',views.FetchPriceAndStockAmazonUAE), 
    url(r'^push-product-images-amazon-uae',views.PushProductImagesAmazonUAE),

########## Feed Reports ##############

    url(r'^fetch-report-list/$',views.FetchReportList),
    url(r'^fetch-report-details/$',views.FetchReportDetails),
    url(r'^refresh-report-status/$',views.RefreshReportStatus),

######### Orders #####################


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
