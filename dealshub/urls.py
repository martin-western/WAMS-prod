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

    url(r'^search/$', views.Search),

    url(r'^create-admin-category/$', views.CreateAdminCategory),
    url(r'^fetch-admin-categories/$', views.FetchAdminCategories),
    url(r'^update-admin-category/$', views.UpdateAdminCategory),
    url(r'^delete-admin-category/$', views.DeleteAdminCategory),
    url(r'^publish-admin-category/$', views.PublishAdminCategory),

    url(r'^unpublish-admin-category/$', views.UnPublishAdminCategory),
    url(r'^section-bulk-upload/$', views.SectionBulkUpload),
    url(r'^add-product-to-section/$', views.AddProductToSection),

    url(r'^fetch-banner-types/$', views.FetchBannerTypes),
    url(r'^create-banner/$', views.CreateBanner),
    url(r'^fetch-banner/$', views.FetchBanner),
    url(r'^delete-banner/$', views.DeleteBanner),
    url(r'^publish-banner/$', views.PublishBanner),
    url(r'^unpublish-banner/$', views.UnPublishBanner),
    url(r'^update-link-banner/$', views.UpdateLinkBanner),
    url(r'^add-banner-image/$', views.AddBannerImage),
    url(r'^delete-banner-image/$', views.DeleteBannerImage),

    url(r'^publish-dealshub-product/$', views.PublishDealsHubProduct),
    url(r'^unpublish-dealshub-product/$', views.UnPublishDealsHubProduct),
    url(r'^publish-dealshub-products/$', views.PublishDealsHubProducts),
    url(r'^unpublish-dealshub-products/$', views.UnPublishDealsHubProducts),

    url(r'^delete-product-from-section/$', views.DeleteProductFromSection),

    url(r'^fetch-heading-data/$', views.FetchHeadingData),
    url(r'^fetch-heading-data-admin/$', views.FetchHeadingDataAdmin),
    url(r'^delete-heading/$', views.DeleteHeading),
    url(r'^fetch-heading-category-list/$', views.FetchHeadingCategoryList),
    url(r'^create-heading-data/$', views.CreateHeadingData),
    url(r'^save-heading-data/$', views.SaveHeadingData),
    url(r'^upload-image-heading/$', views.UploadImageHeading),
    url(r'^update-image-heading-link/$', views.UpdateImageHeadingLink),
    url(r'^delete-image-heading/$', views.DeleteImageHeading),

    url(r'^fetch-user-website-group/$', views.FetchUserWebsiteGroup),

    url(r'^fetch-dealshub-admin-sections/$', views.FetchDealshubAdminSections),
    url(r'^save-dealshub-admin-sections-order/$', views.SaveDealshubAdminSectionsOrder),

    url(r'^search-section-products-autocomplete/$', views.SearchSectionProductsAutocomplete),
    url(r'^search-products-autocomplete/$', views.SearchProductsAutocomplete),

    url(r'^fetch-dealshub-price/$', views.FetchDealshubPrice),

    url(r'^fetch-company-profile-dealshub/$', views.FetchCompanyProfileDealshub),

    url(r'^fetch-bulk-product-info/$', views.FetchBulkProductInfo),  

    url(r'^fetch-website-group-brands/$', views.FetchWebsiteGroupBrands),   
    url(r'^generate-stock-price-report/$', views.GenerateStockPriceReport),   

    url(r'^add-product-to-unit-banner/$', views.AddProductToUnitBanner),
    url(r'^delete-product-from-unit-banner/$', views.DeleteProductFromUnitBanner),
    url(r'^fetch-unit-banner-products/$', views.FetchUnitBannerProducts),
]
