from django.conf.urls import url
from WAMSApp import views_sourcing as views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [

    url(r'^fetch-factory-details/$', views.FetchFactoryDetails),
    url(r'^fetch-factories/$', views.FetchFactoriesList),
    url(r'^fetch-products-from-factory/$', views.FetchProductsFromFactory),
    url(r'^fetch-factory-details/$', views.FetchFactoryDetails),
    url(r'^fetch-factory-details/$', views.FetchFactoryDetails),
    url(r'^fetch-factory-details/$', views.FetchFactoryDetails),
    url(r'^fetch-factory-details/$', views.FetchFactoryDetails),
    url(r'^fetch-factory-details/$', views.FetchFactoryDetails),


SaveFactoryDetails = SaveFactoryDetailsAPI.as_view()
FetchFactorywiseProductListing = FetchFactorywiseProductListingAPI.as_view()
UploadFactoryImage = UploadFactoryImageAPI.as_view()
ChangeGoLiveStatus = ChangeGoLiveStatusAPI.as_view()
DownloadPI = DownloadPIAPI.as_view()
DownloadPIBulk = DownloadPIBulkAPI.as_view()
GenerateDraftPILine = GenerateDraftPILineAPI.as_view()
FetchDraftProformaInvoice = FetchDraftProformaInvoiceAPI.as_view()
DeleteDraftLine = DeleteDraftLineAPI.as_view()
CreateDraftPIFromProductSelection = CreateDraftPIFromProductSelectionAPI.as_view()
FetchProformaInvoiceList = FetchProformaInvoiceListAPI.as_view()
FetchDraftProformaInvoicesCart = FetchDraftProformaInvoicesCartAPI.as_view()

]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

