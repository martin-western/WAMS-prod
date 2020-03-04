from django.conf.urls import url
from WAMSApp import views_sourcing as views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [

    url(r'^fetch-factories/$', views.FetchFactories),
    url(r'^add-new-factory/$', views.AddNewFactory),
    url(r'^fetch-factory-details/$', views.FetchFactoryDetails),
    url(r'^fetch-constants/$', views.FetchConstants),
    url(r'^add-new-product/$', views.AddNewProduct),

    url(r'^upload-factories-and-products/$', views.UploadFactoriesProducts),


    url(r'^fetch-product-details/$', views.FetchProductDetails),
    url(r'^save-phone-numbers/$', views.SavePhoneNumbers),
    url(r'^save-address/$', views.SaveAddress),
    url(r'^save-factory-name/$', views.SaveFactoryName),
    url(r'^save-product-details/$', views.SaveProductDetails),
    url(r'^save-business-card/$', views.SaveBusinessCard),
    url(r'^upload-product-image/$', views.UploadProductImage),
    url(r'^delete-image/$', views.DeleteImage),
    url(r'^upload-attachment/$', views.UploadAttachment),
    url(r'^delete-attachment/$', views.DeleteAttachment),

    url(r'^fetch-product-cards/$', views.FetchProductCards),
    url(r'^save-factory-details/$', views.SaveFactoryDetails),

    url(r'^export-factories/$', views.ExportFactories),

    url(r'^search-factories/$', views.SearchFactories),
    url(r'^search-products/$', views.SearchProducts),
    url(r'^share-factory/$', views.ShareFactory),
    url(r'^send-factory-share-email/$', views.SendFactoryShareEmail),
    url(r'^fetch-factory-name-from-uuid/$', views.FetchFactoryNameFromUUID),

    url(r'^fetch-factory-for-sourcing-user/$',
        views.FetchFactoryForSourcingUser),


    url(r'^fetch-factories-for-sourcing-user/$',
        views.FetchFactoriesForSourcingUser),

    url(r'^fetch-sourcing-user-details/$', views.FetchSourcingUserDetails),

    url(r'^fetch-products-from-factory/$', views.FetchProductsFromFactory),
    url(r'^save-factory-product-details/$', views.SaveFactoryProductDetails),
    url(r'^share-product/$', views.ShareProduct),

    url(r'^fetch-shared-products-for-factory/$',
        views.FetchSharedProductsForFactory),
    url(r'^fetch-draft-proforma-invoice/$', views.FetchDraftProformaInvoice),
    url(r'^download-pi-bulk/$', views.DownloadPIBulk),
    # download-pi-bulk` create-draft-pi-from-product-selection
    url(r'^create-draft-pi-from-product-selection/$',
        views.CreateDraftPIFromProductSelection),




    url(r'^save-sourcing-product-details/$',
        views.SaveSourcingProductDetails),

    url(r'^save-sourcing-factory-details/$', views.SaveSourcingFactoryDetails),

    url(r'^fetch-factorywise-product-listing/$',
        views.FetchFactorywiseProductListing),



    url(r'^fetch-factory-product-details/$', views.FetchFactoryProductDetails),
    url(r'^fetch-sourcing-product-details/$',
        views.FetchSourcingProductDetails),

    url(r'^upload-factory-product-image/$', views.UploadFactoryProductImage),

    url(r'^upload-factory-image/$', views.UploadFactoryImage),


    url(r'^search-factories/$', views.SearchFactories),
    url(r'^search-factories-by-date/$', views.SearchFactoriesByDate),
    url(r'^search-products/$', views.SearchProducts),

    url(r'^change-go-live-status/$', views.ChangeGoLiveStatus),
    url(r'^download-pi/$', views.DownloadPI),
    url(r'^generate-draft-pi-line/$', views.GenerateDraftPILine),
    # generate-draft-pi-line   generate-pi-in-bulk
    url(r'^upload-factories-and-products-sourcing-users/$',
        views.UploadFactoriesProductsFromSourcing),
    url(r'^upload-sourcing-user-product-image/$',
        views.UploadSourcingProductProductImage),

    url(r'^delete-draft-line/$',
        views.DeleteDraftLine),
    url(r'^proforma-invoices-list/$',
        views.FetchProformaInvoiceList),

    url(r'^fetch-draft-proforma-invoice-cart/$',
        views.FetchDraftProformaInvoicesCart),

    #

]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

