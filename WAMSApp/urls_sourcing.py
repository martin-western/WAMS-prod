from django.conf.urls import url
from WAMSApp import views_sourcing as views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [

    url(r'^fetch-factory-list/$', views.FetchFactoryList),
    url(r'^fetch-factory-details/$', views.FetchFactoryDetails),
    url(r'^fetch-product-listing-for-pi/$', views.FetchProductListingForPI),

    url(r'^save-factory-details/$', views.SaveFactoryDetails),
    url(r'^upload-factory-images/$', views.UploadFactoryImages),

    url(r'^download-bulk-pi/$', views.DownloadBulkPI),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)