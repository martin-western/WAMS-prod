from django.conf.urls import url
from WAMSApp import views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [

############################## SAP Automation #########################################

    url(r'^fetch-price-and-stock/$',views.FetchPriceAndStock),
    url(r'^transfer-stock-to-holding/$',views.HoldingTransfer),
    url(r'^bulk-transfer-to-holding/$',views.BulkHoldingTransfer),
    url(r'^fetch-product-holding-details/$',views.FetchProductHoldingDetails),
    url(r'^update-product-holding-details/$',views.UpdateProductHoldingDetails),
    url(r'^fetch-sap-attributes/$',views.FetchSAPAttributes),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
