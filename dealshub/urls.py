from django.conf.urls import url
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect


urlpatterns = [
    url(r'^fetch-product-details/$', views.FecthProductDetails),
    url(r'^fetch-carousel/$', views.FetchCarousel),
    url(r'^fetch-categories/$', views.FetchCategories),

    url(r'^fetch-category-grid-banner-cards/$',
        views.FetchCategoryGridBannerCards),

    url(r'^fetch-dashboard-banner-details/$', views.FetchDashboardBannerDetails),
    url(r'^fetch-banner-deals/$', views.FetchBannerDeals),
    url(r'^fetch-batch-discount-deals/$', views.FetchBatchDiscountDeals),
    url(r'^fetch-special-discount-product/$',
        views.FetchSpecialDiscountProduct),
    url(r'^fetch-schedular-products/$', views.FetchSchedularProducts),
    url(r'^fetch-featured-products/$', views.FetchFeaturedProducts),
    url(r'^fetch-on-sale-products/$', views.FetchOnSaleProducts),
    url(r'^fetch-top-rated-products/$', views.FetchTopRatedProducts),
    url(r'^search/$', views.Search),

    url(r'^create-admin-category/$', views.CreateAdminCategory),
    url(r'^fetch-admin-categories/$', views.FetchAdminCategories),
    url(r'^update-admin-category/$', views.UpdateAdminCategory),
    url(r'^delete-admin-category/$', views.DeleteAdminCategory),
    url(r'^publish-admin-category/$', views.PublishAdminCategory),

]
