from django.conf.urls import url
from SalesApp import views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [
    
    url(r'^login-submit/$', views.SalesAppLoginSubmit),
    url(r'^signup-submit/$', views.SalesAppSignUpSubmit),
    url(r'^search-product-by-brand/$', views.SearchProductByBrand),
    url(r'^product-change-in-favourites/$', views.ProductChangeInFavourites),
    url(r'^fetch-favourite-products/$', views.FetchFavouriteProducts),
    
    url(r'^create-notification/$', views.CreateNotification),
    url(r'^get-notification-details/$', views.GetNotificationDeatils),
    url(r'^edit-notification/$', views.EditNotification),
    url(r'^send-notification/$', views.SendNotification),
    url(r'^fetch-notification-list/$', views.FetchNotificationList),

]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
