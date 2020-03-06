from django.conf.urls import url
from WAMSApp import views_sourcing as views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [

    url(r'^fetch-factory-details/$', views.FetchFactoryDetails),
    url(r'^fetch-factories/$', views.FetchFactoriesList),
    url(r'^fetch-products-from-factory/$', views.FetchProductsFromFactory),
    url(r'^save-factory-details/$', views.SaveFactoryDetails),
    url(r'^fetch-factorywise-products/$', views.FetchFactorywiseProductListing),
    url(r'^upload-factory-image/$', views.UploadFactoryImage),
    

    url(r'^fetch-draft-proforma-invoice/$', views.FetchDraftProformaInvoice),
    url(r'^download-pi-bulk/$', views.DownloadPIBulk),
    url(r'^create-draft-pi-from-product-selection/$',views.CreateDraftPIFromProductSelection),


    url(r'^change-go-live-status/$', views.ChangeGoLiveStatus),
    url(r'^download-pi/$', views.DownloadPI),
    url(r'^delete-draft-line/$',views.DeleteDraftLine),
    url(r'^proforma-invoices-list/$',views.FetchProformaInvoiceList),
    url(r'^draft-proforma-invoices/$', views.DraftProformaInvoices),
    url(r'^fetch-draft-proforma-invoice-cart/$',views.FetchDraftProformaInvoicesCart),


]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

