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

