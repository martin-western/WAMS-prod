from django.conf.urls import url
from SalesApp import views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [
    
    url(r'^login-submit/$', views.SalesAppLoginSubmit),
    url(r'^signup-submit/$', views.SalesAppSignUpSubmit),
    url(r'^search-product-by-brand/$', views.SearchProductByBrand),
    url(r'^product-change-in-favourites/$', views.ProductChangeInFavourites),
    url(r'^fetch-favourite-products/$', views.FetchFavouriteProducts),
    url(r'^fetch-product-list-by-category/$', views.FetchProductListByCategoryForSalesApp),
    url(r'^fetch-notification-list/$', views.FetchNotificationList),

    url(r'^fetch-product-details/$',views.FetchProductDetails),
    url(r'^fetch-bulk-product-details/$',views.FetchBulkProductDetails),
    url(r'^fetch-category-list-by-brand/$',views.FetchCategoryListByBrand),
    url(r'^fetch-categories-for-sales/$',views.FetchCategoriesForSales),
    url(r'^upload-category-sales-image/$',views.UploadCategorySalesImage),

    
##################### Notification Dashboard URLs ###################################

    url(r'^create-notification/$', views.CreateNotification),
    url(r'^get-notification-details/$', views.GetNotificationDeatils),
    url(r'^save-notification/$', views.SaveNotification),
    url(r'^upload-notification-image/$', views.UploadNotificationImage),
    url(r'^delete-notification-image/$', views.DeleteNotificationImage),
    url(r'^send-notification/$', views.SendNotification),
    url(r'^fetch-notification-list-for-admin/$', views.FetchNotificationListForAdmin),

]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
