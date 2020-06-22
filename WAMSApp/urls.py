from django.conf.urls import url
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [

    url(r'^create-new-base-product/$', views.CreateNewBaseProduct),
    url(r'^create-new-product/$', views.CreateNewProduct),

    url(r'^fetch-product-details/$', views.FetchProductDetails),
    url(r'^fetch-base-product-details/$', views.FetchBaseProductDetailsAPI),
    url(r'^save-product/$', views.SaveProduct),

    # url(r'^save-pfl-image/', views.SavePflImage),

    url(r'^fetch-product-list/$', views.FetchProductList),
    url(r'^updated-fetch-product-list/$', views.UpdatedFetchProductList),
    
    url(r'^fetch-export-list/$', views.FetchExportList),
    url(r'^add-to-export/$', views.AddToExport),

    url(r'^fetch-export-product-list/$', views.FetchExportProductList),
    url(r'^download-export-list/$', views.DownloadExportList),

    url(r'^import-products/$', views.ImportProducts),

    url(r'^upload-product-image/$', views.UploadProductImage),

    url(r'^update-main-image/$', views.UpdateMainImage),
    url(r'^update-sub-images/$', views.UpdateSubImages),


    # Flyers and PFL
    url(r'^create-flyer/$', views.CreateFlyer),
    url(r'^fetch-flyer-details/$', views.FetchFlyerDetails),
    url(r'^create-pfl/$', views.CreatePFL),
    url(r'^fetch-pfl-details/$', views.FetchPFLDetails),
    url(r'^fetch-product-list-flyer-pfl/$', views.FetchProductListFlyerPFL),
    url(r'^add-product-flyer-bucket/$', views.AddProductFlyerBucket),
    url(r'^add-product-pfl-bucket/$', views.AddProductPFLBucket),
    url(r'^fetch-product-details-flyer-pfl/$',
        views.FetchProductDetailsFlyerPFL),
    url(r'^save-flyer-template/$', views.SaveFlyerTemplate),
    url(r'^save-pfl-template/$', views.SavePFLTemplate),
    url(r'^upload-image-external-bucket-flyer/$',
        views.UploadImageExternalBucketFlyer),
    url(r'^upload-image-external-bucket-pfl/$',
        views.UploadImageExternalBucketPFL),

    url(r'^fetch-pfl-list/$', views.FetchPFLList),


    url(r'^flyer/(?P<pk>[\w-]+)/$', views.FlyerPage),
    url(r'^fetch-flyer-list/$', views.FetchFlyerList),

    url(r'^upload-new-flyer-bg-image/$', views.UploadNewFlyerBGImage),
    url(r'^upload-flyer-tag/$', views.UploadFlyerTag),
    url(r'^upload-flyer-price-tag/$', views.UploadFlyerPriceTag),
    url(r'^download-images-s3/$', views.DownloadImagesS3),
    url(r'^fetch-brands/$', views.FetchBrands),

    url(r'^save-pfl-in-bucket/$', views.SavePFLInBucket),
    url(r'^save-flyer-in-bucket/$', views.SaveFlyerInBucket),

    url(r'^verify-product/$', views.VerifyProduct),
    url(r'^lock-product/$', views.LockProduct),
    url(r'^delete-image/$', views.DeleteImage),
    url(r'^remove-product-from-export-list/$',views.RemoveProductFromExportList),
    url(r'^download-product/$', views.DownloadProduct),

    url(r'^upload-flyer-external-images/$', views.UploadFlyerExternalImages),
    url(r'^upload-pfl-external-images/$', views.UploadPFLExternalImages),


    url(r'^save-channel-product-amazon-uk/$',views.SaveAmazonUKChannelProduct),
    url(r'^save-channel-product-amazon-uae/$',views.SaveAmazonUAEChannelProduct),
    url(r'^save-channel-product-ebay/$',views.SaveEbayChannelProduct),
    url(r'^save-channel-product-noon/$',views.SaveNoonChannelProduct),

    url(r'^fetch-channel-product/$',views.FetchChannelProduct),

    url(r'save-base-product/$', views.SaveBaseProduct),
    
    url(r'^sap-integration/$',views.SapIntegration),
    url(r'^fetch-user-profile/$',views.FetchUserProfile),

    url(r'^fetch-dealshub-products/$',views.FetchDealsHubProducts),
    url(r'^update-dealshub-product/$',views.UpdateDealshubProduct),
    url(r'^bulk-update-dealshub-product-price/$',views.BulkUpdateDealshubProductPrice),
    url(r'^bulk-update-dealshub-product-stock/$',views.BulkUpdateDealshubProductStock),

    url(r'^fetch-audit-logs-by-user/$',views.FetchAuditLogsByUser), 
    url(r'^fetch-audit-logs/$',views.FetchAuditLogs), 
    url(r'^create-request-help/$',views.CreateRequestHelp),    

    url(r'^fetch-channel-product-list/$',views.FetchChannelProductList),

    url(r'^save-company-profile/$',views.SaveCompanyProfile),
    url(r'^upload-company-logo/$',views.UploadCompanyLogo),
    url(r'^fetch-company-profile/$',views.FetchCompanyProfile),

    url(r'^refresh-page-price-and-stock/$',views.RefreshPagePriceAndStock),
    url(r'^refresh-product-price-and-stock/$',views.RefreshProductPriceAndStock),
    url(r'^fetch-product-details-sales-integration/$',views.FetchProductDetailsSalesIntegration),
    url(r'^fetch-bulk-product-details-sales-integration/$',views.FetchBulkProductDetailsSalesIntegration),

    url(r'^move-to-main-images/$',views.MoveToMainImages),
    url(r'^move-to-sub-images/$',views.MoveToSubImages),

    url(r'^generate-reports/$',views.GenerateReports),

    url(r'^upload-bulk-export/$',views.UploadBulkExport),
    url(r'^search-bulk-export/$',views.SearchBulkExport),
    url(r'^fetch-data-points/$',views.FetchDataPoints),
    url(r'^download-bulk-export/$',views.DownloadBulkExport),
    url(r'^transfer-bulk-channel/$',views.TransferBulkChannel),
    url(r'^fetch-all-categories/$',views.FetchAllCategories),
    url(r'^fetch-company-credentials/$',views.FetchCompanyCredentials),

    url(r'^fetch-orders-for-account-manager/$',views.FetchOrdersForAccountManager),
    url(r'^fetch-orders-for-warehouse-manager/$',views.FetchOrdersForWarehouseManager),
    url(r'^fetch-shipping-method/$',views.FetchShippingMethod),
    url(r'^set-shipping-method/$',views.SetShippingMethod),
    url(r'^set-orders-status/$',views.SetOrdersStatus),
    url(r'^cancel-orders/$',views.CancelOrders),

    url(r'^download-orders/$',views.DownloadOrders),
    url(r'^upload-orders/$',views.UploadOrders),

    url(r'^check-section-permissions/$',views.CheckSectionPermissions),
    url(r'^fetch-page-permissions/$',views.FetchPagePermissions),


    url(r'^create-oc-report/$',views.CreateOCReport),
    url(r'^fetch-oc-report-permissions/$',views.FetchOCReportPermissions),
    url(r'^fetch-oc-report-list/$',views.FetchOCReportList),

    url(r'^fetch-statistics/$',views.FetchStatistics),
    url(r'^update-channel-product-stock-and-price/$',views.UpdateChannelProductStockandPrice),
    url(r'^bulk-update-channel-product-price/$',views.BulkUpdateChannelProductPrice),
    url(r'^bulk-update-channel-product-stock/$',views.BulkUpdateChannelProductStock),



]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

