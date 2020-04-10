from django.conf.urls import url
from WAMSApp import views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [

#################################################################################

############################## MWS URLS ########################################

################################################################################# 

    url(r'^get-matching-products-amazon-uk-mws/$',views.GetMatchingProductsAmazonUKMWS),
    url(r'^get-matching-products-amazon-uae-mws/$',views.GetMatchingProductsAmazonUAEMWS),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)