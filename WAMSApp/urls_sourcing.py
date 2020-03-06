from django.conf.urls import url
from WAMSApp import views_sourcing as views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [

    
FetchFactoryDetails = FetchFactoryDetailsAPI.as_view() 

FetchFactoriesList = FetchFactoriesListAPI.as_view()

FetchProductsFromFactory = FetchProductsFromFactoryAPI.as_view()

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

