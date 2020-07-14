from django.conf.urls import url
from WAMSApp import views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [

#################################################################################

############################## MWS URLS #########################################

################################################################################# 

    url(r'^push-products-amazon-uk/$',views.PushProductsAmazonUK),
    url(r'^push-products-amazon-uae/$',views.PushProductsAmazonUAE),
    url(r'^push-products-inventory-amazon-uae/$',views.PushProductsInventoryAmazonUAE),
    url(r'^push-products-price-amazon-uae/$',views.PushProductsPriceAmazonUAE),
    
    url(r'^get-matching-products-amazon-uk/$',views.GetMatchingProductsAmazonUKMWS),
    url(r'^get-pricing-of-products-amazon-uk/$',views.GetPricingProductsAmazonUKMWS),

    url(r'^get-matching-products-amazon-uae/$',views.GetMatchingProductsAmazonUAEMWS),
    url(r'^get-pricing-of-products-amazon-uae/$',views.GetPricingProductsAmazonUAEMWS),
    url(r'^get-product-inventory-amazon-uae/$',views.GetProductInventoryAmazonUAE),

    url(r'^get-push-products-result-amazon-uk/$',views.GetPushProductsResultAmazonUK),
    
    url(r'^fetch-report-list/$',views.FetchReportList),
    url(r'^fetch-report-details/$',views.FetchReportDetails),
    url(r'^refresh-report-status/$',views.RefreshReportStatus),

    url(r'^fetch-orders-periodically/$',views.FetchOrdersPeriodically),   
    url(r'^fetch-price-and-stock-periodically-amazon-uae',views.FetchPriceAndStockAmazonUAE), 

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
