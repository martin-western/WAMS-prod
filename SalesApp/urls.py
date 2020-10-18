from django.conf.urls import url
from SalesApp import views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [
    
    url(r'^login-submit/$', views.SalesAppLoginSubmit),
    url(r'^signup-submit/$', views.SignUpSubmit),
    url(r'^search-product-by-brand/$', views.SearchProductByBrand),
    url(r'^product-change-in-favourites/$', views.ProductChangeInFavourites),
    url(r'^fetch-favourite-products/$', views.FetchFavouriteProducts),

]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
