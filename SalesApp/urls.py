from django.conf.urls import url
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [
    
    url(r'^login-submit/$', views.LoginSubmit),
    url(r'^signup-submit/$', views.SignUpSubmit),
    url(r'^search-product-by-brand/$', views.SearchProductByBrand),
    url(r'^product-add-to-favourite/$', views.ProductAddToFavourites),

]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
