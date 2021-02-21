from django.conf.urls import url
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [
    
    url(r'^github-webhook/$', views.GithubWebhook),

    url(r'^create-new-base-product/$', views.CreateNewBaseProduct),
    url(r'^create-new-product/$', views.CreateNewProduct),

    url(r'^fetch-product-details/$', views.FetchProductDetails),
    url(r'^fetch-base-product-details/$', views.FetchBaseProductDetailsAPI),
    url(r'^save-product/$', views.SaveProduct),

    # url(r'^save-pfl-image/', views.SavePflImage),

    url(r'^fetch-product-list/$', views.FetchProductList),
    
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
    url(r'^copy-best-images/$', views.CopyBestImages),
    url(r'^delete-image/$', views.DeleteImage),
    url(r'^remove-image/$', views.RemoveImage),
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
    url(r'^bulk-update-dealshub-product-publish-status/$', views.BulkUpdateDealshubProductPublishStatus),
    url(r'^fetch-dealshub-product-details/$',views.FetchDealshubProductDetails),
    url(r'^save-dealshub-product-details/$',views.SaveDealshubProductDetails),

    url(r'^fetch-audit-logs-by-user/$',views.FetchAuditLogsByUser), 
    url(r'^fetch-audit-logs/$',views.FetchAuditLogs), 
    url(r'^create-request-help/$',views.CreateRequestHelp),    

    url(r'^fetch-channel-product-list/$',views.FetchChannelProductList),

    url(r'^fetch-location-group-list/$', views.FetchLocationGroupList),

    url(r'^save-company-profile/$',views.SaveCompanyProfile),
    url(r'^upload-company-logo/$',views.UploadCompanyLogo),
    url(r'^upload-company-footer-logo/$',views.UploadCompanyFooterLogo),
    url(r'^fetch-company-profile/$',views.FetchCompanyProfile),

    url(r'^refresh-page-price-and-stock/$',views.RefreshPagePriceAndStock),
    url(r'^refresh-product-price-and-stock/$',views.RefreshProductPriceAndStock),
    
    url(r'^upload-bulk-export/$',views.UploadBulkExport),
    url(r'^search-bulk-export/$',views.SearchBulkExport),
    url(r'^fetch-data-points/$',views.FetchDataPoints),
    url(r'^fetch-data-points-for-upload/$',views.FetchDataPointsForUpload),
    url(r'^download-bulk-export/$',views.DownloadBulkExport),
    url(r'^transfer-bulk-channel/$',views.TransferBulkChannel),
    url(r'^fetch-all-categories/$',views.FetchAllCategories),

    url(r'^create-export-template/$',views.CreateExportTemplate),
    url(r'^fetch-export-templates/$',views.FetchExportTemplates),
    url(r'^delete-export-template/$',views.DeleteExportTemplate),

    url(r'^check-section-permissions/$',views.CheckSectionPermissions),

    url(r'^create-oc-report/$',views.CreateOCReport),
    url(r'^create-seo-report/$',views.CreateSEOReport),
    url(r'^bulk-upload-seo-details/$',views.BulkUploadSEODetails),
    url(r'^create-content-report/$',views.CreateContentReport),
    url(r'^fetch-oc-report-permissions/$',views.FetchOCReportPermissions),
    url(r'^fetch-oc-report-list/$',views.FetchOCReportList),
    url(r'^download-dynamic-excel-template/$',views.DownloadDynamicExcelTemplate),

    url(r'^bulk-upload-dynamic-excel/$',views.BulkUploadDynamicExcel),
    
    url(r'^fetch-statistics/$',views.FetchStatistics),
    url(r'^update-channel-product-stock-and-price/$',views.UpdateChannelProductStockandPrice),

    url(r'^bulk-update-noon-product-price/$',views.BulkUpdateNoonProductPrice),
    url(r'^bulk-update-noon-product-stock/$',views.BulkUpdateNoonProductStock),
    url(r'^bulk-update-noon-product-price-and-stock/$',views.BulkUpdateNoonProductPriceAndStock),

    url(r'^bulk-update-amazon-uae-product-price/$',views.BulkUpdateAmazonUAEProductPrice),
    url(r'^bulk-update-amazon-uae-product-stock/$',views.BulkUpdateAmazonUAEProductStock),
    url(r'^bulk-update-amazon-uae-product-price-and-stock/$',views.BulkUpdateAmazonUAEProductPriceAndStock),

    url(r'^bulk-update-amazon-uk-product-price/$',views.BulkUpdateAmazonUKProductPrice),
    url(r'^bulk-update-amazon-uk-product-stock/$',views.BulkUpdateAmazonUKProductStock),
    url(r'^bulk-update-amazon-uk-product-price-and-stock/$',views.BulkUpdateAmazonUKProductPriceAndStock),

    url(r'^fetch-category-list/$',views.FetchCategoryList),
    url(r'^update-category-mapping/$',views.UpdateCategoryMapping),

    url(r'^admin/fetch-admin-super-categories/$', views.FetchAdminSuperCategories),
    url(r'^admin/fetch-admin-categories/$', views.FetchAdminCategories),
    url(r'^admin/fetch-admin-sub-categories/$', views.FetchAdminSubCategories),
    url(r'^admin/update-admin-super-category-details/$', views.UpdateAdminSuperCategoryDetails),
    url(r'^admin/update-admin-category-details/$', views.UpdateAdminCategoryDetails),
    url(r'^admin/update-admin-sub-category-details/$', views.UpdateAdminSubCategoryDetails),
    url(r'^admin/add-new-admin-super-category/$', views.AddNewAdminSuperCategory),
    url(r'^admin/add-new-admin-category/$', views.AddNewAdminCategory),
    url(r'^admin/add-new-admin-sub-category/$', views.AddNewAdminSubCategory),

    url(r'^secure-delete-product/$',views.SecureDeleteProduct),
    url(r'^logout-ocuser/$',views.LogoutOCUser),

    url(r'^create-nesto-product/$',views.CreateNestoProduct),
    url(r'^update-nesto-product/$',views.UpdateNestoProduct),
    url(r'^fetch-nesto-product-details/$',views.FetchNestoProductDetails),
    url(r'^fetch-nesto-product-list/$',views.FetchNestoProductList),
    url(r'^add-nesto-product-images/$',views.AddNestoProductImages),
    url(r'^remove-nesto-product-image/$',views.RemoveNestoProductImage),
    url(r'^search-nesto-product-autocomplete/$',views.SearchNestoProductAutoComplete),
    url(r'^fetch-linked-nesto-products/$',views.FetchLinkedNestoProducts),
    url(r'^link-nesto-product/$',views.LinkNestoProduct),
    url(r'^unlink-nesto-product/$',views.UnLinkNestoProduct),
    url(r'^fetch-nesto-brands/$', views.FetchNestoBrands)
    
]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)