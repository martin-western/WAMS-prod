from django.conf.urls import url
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect


urlpatterns = [
    url(r'^fetch-product-details/$', views.FetchProductDetails),
    url(r'^fetch-sections-products/$', views.FetchSectionsProducts),
    url(r'^fetch-sections-products-limit/$', views.FetchSectionsProductsLimit),
    url(r'^fetch-section-products/$', views.FetchSectionProducts),
    url(r'^fetch-categories/$', views.FetchCategories),

    url(r'^fetch-category-grid-banner-cards/$',
        views.FetchCategoryGridBannerCards),

    url(r'^fetch-dashboard-banner-details/$', views.FetchDashboardBannerDetails),
    url(r'^fetch-batch-discount-deals/$', views.FetchBatchDiscountDeals),
    url(r'^fetch-special-discount-product/$',
        views.FetchSpecialDiscountProduct),
    url(r'^fetch-schedular-products/$', views.FetchSchedularProducts),
    url(r'^fetch-featured-products/$', views.FetchFeaturedProducts),
    url(r'^fetch-on-sale-products/$', views.FetchOnSaleProducts),
    url(r'^fetch-top-rated-products/$', views.FetchTopRatedProducts),
    url(r'^fetch-brands-carousel/$', views.FetchBrandsCarousel),
    url(r'^search/$', views.Search),

    url(r'^create-admin-category/$', views.CreateAdminCategory),
    url(r'^fetch-admin-categories/$', views.FetchAdminCategories),
    url(r'^update-admin-category/$', views.UpdateAdminCategory),
    url(r'^delete-admin-category/$', views.DeleteAdminCategory),
    url(r'^publish-admin-category/$', views.PublishAdminCategory),

    url(r'^unpublish-admin-category/$', views.UnPublishAdminCategory),
    url(r'^section-bulk-upload/$', views.SectionBulkUpload),

    url(r'^create-deals-banner/$', views.CreateDealsBanner),
    url(r'^fetch-deals-banner/$', views.FetchDealsBanner),
    url(r'^delete-deals-banner/$', views.DeleteDealsBanner),
    url(r'^publish-deals-banner/$', views.PublishDealsBanner),
    url(r'^unpublish-deals-banner/$', views.UnPublishDealsBanner),

    url(r'^create-full-banner-ad/$', views.CreateFullBannerAd),
    url(r'^fetch-full-banner-ad/$', views.FetchFullBannerAd),
    url(r'^delete-full-banner-ad/$', views.DeleteFullBannerAd),
    url(r'^publish-full-banner-ad/$', views.PublishFullBannerAd),
    url(r'^unpublish-full-banner-ad/$', views.UnPublishFullBannerAd),

    url(r'^create-dealshub-product/$', views.CreateDealsHubProduct),
    url(r'^publish-dealshub-product/$', views.PublishDealsHubProduct),
    url(r'^unpublish-dealshub-product/$', views.UnPublishDealsHubProduct),

    url(r'^create-category-grid-banner/$', views.CreateCategoryGridBanner),
    url(r'^fetch-category-grid-banner/$', views.FetchCategoryGridBanner),
    url(r'^delete-category-grid-banner/$', views.DeleteCategoryGridBanner),

    url(r'^delete-product-from-section/$', views.DeleteProductFromSection),   
]