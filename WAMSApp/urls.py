from django.conf.urls import url
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [
    url(r'^$', views.RedirectHome),
    url(r'^login/', views.Login),
    url(r'^login-submit/', views.LoginSubmit),
    url(r'^logout/', views.Logout),
    
    url(r'^fetch-constant-values/', views.FetchConstantValues),
    url(r'^create-new-product/', views.CreateNewProduct),



    url(r'^edit-product/(?P<pk>[\w-]+)/', views.EditProductPage),
    url(r'^fetch-product-details/', views.FetchProductDetails),
    url(r'^save-product/', views.SaveProduct),

    # url(r'^save-pfl-image/', views.SavePflImage),

    url(r'^products/', views.Products),
    url(r'^fetch-product-list/', views.FetchProductList),
    url(r'^fetch-export-list/', views.FetchExportList),
    url(r'^add-to-export/', views.AddToExport),

    url(r'^export-list/', views.ExportListPage),
    url(r'^fetch-export-product-list/', views.FetchExportProductList),
    url(r'^download-export-list/', views.DownloadExportList),

    url(r'^import-products/', views.ImportProducts),

    url(r'^upload-product-image/', views.UploadProductImage),

    url(r'^update-main-image/', views.UpdateMainImage),
    url(r'^update-sub-images/', views.UpdateSubImages),


    # Flyers and PFL
    url(r'^create-flyer/', views.CreateFlyer),
    url(r'^fetch-flyer-details/', views.FetchFlyerDetails),
    url(r'^create-pfl/', views.CreatePFL),
    url(r'^fetch-pfl-details/', views.FetchPFLDetails),
    url(r'^fetch-product-list-flyer-pfl/', views.FetchProductListFlyerPFL),
    url(r'^add-product-flyer-bucket/', views.AddProductFlyerBucket),
    url(r'^add-product-pfl-bucket/', views.AddProductPFLBucket),
    url(r'^fetch-product-details-flyer-pfl/', views.FetchProductDetailsFlyerPFL),   
    url(r'^save-flyer-template/', views.SaveFlyerTemplate),
    url(r'^save-pfl-template/', views.SavePFLTemplate),
    url(r'^upload-image-external-bucket-flyer/', views.UploadImageExternalBucketFlyer),
    url(r'^upload-image-external-bucket-pfl/', views.UploadImageExternalBucketPFL),


    url(r'^pfl/(?P<pk>[\w-]+)/', views.PFLPage),
    url(r'^pfl-dashboard/', views.PFLDashboardPage),
    url(r'^fetch-pfl-list/', views.FetchPFLList),


    url(r'^flyer/(?P<pk>[\w-]+)/', views.FlyerPage),
    url(r'^flyer-dashboard/', views.FlyerDashboardPage),
    url(r'^fetch-flyer-list/', views.FetchFlyerList),

    url(r'^upload-new-flyer-bg-image/', views.UploadNewFlyerBGImage),
    url(r'^download-images-s3/', views.DownloadImagesS3),
    url(r'^fetch-brands/', views.FetchBrands),      

    url(r'^save-pfl-in-bucket/', views.SavePFLInBucket),            
    url(r'^save-flyer-in-bucket/', views.SaveFlyerInBucket),            

    url(r'^verify-product/', views.VerifyProduct),

    url(r'^delete-image/', views.DeleteImage),

    url(r'^remove-product-from-export-list/', views.RemoveProductFromExportList),

    url(r'^download-product/', views.DownloadProduct),
    url(r'^ecommerce-listing/(?P<pk>[\w-]+)/', views.EcommerceListingPage),

]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

