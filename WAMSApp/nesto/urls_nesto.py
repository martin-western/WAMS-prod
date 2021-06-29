from django.conf.urls import url
from . import views_nesto as views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect


urlpatterns = [

    url(r'^create-nesto-product/$',views.CreateNestoProduct),
    url(r'^delete-nesto-product-store/$',views.DeleteNestoProductStore),
    url(r'^update-nesto-product/$',views.UpdateNestoProduct),
    url(r'^fetch-nesto-store-list/$',views.FetchNestoStoreList),
    url(r'^fetch-nesto-product-details/$',views.FetchNestoProductDetails),
    url(r'^fetch-nesto-product-list/$',views.FetchNestoProductList),
    url(r'^add-nesto-product-images/$',views.AddNestoProductImages),
    url(r'^remove-nesto-product-image/$',views.RemoveNestoProductImage),
    url(r'^search-nesto-product-autocomplete/$',views.SearchNestoProductAutoComplete),
    url(r'^fetch-linked-nesto-products/$',views.FetchLinkedNestoProducts),
    url(r'^link-nesto-product/$',views.LinkNestoProduct),
    url(r'^unlink-nesto-product/$',views.UnLinkNestoProduct),
    url(r'^fetch-nesto-brands/$', views.FetchNestoBrands),
    url(r'^fetch-nesto-brand-details/$', views.FetchNestoBrandDetails),

    url(r'^update-nesto-brand/$', views.UpdateNestoBrand),
    url(r'^create-nesto-brand/$', views.CreateNestoBrand),
    url(r'^delete-nesto-brand/$', views.DeleteNestoBrand),
    url(r'^add-nesto-brand-image/$', views.AddNestoBrandImage),
    url(r'^remove-nesto-brand-image/$', views.RemoveNestoBrandImage),
    url(r'^fetch-nesto-activity-logs/$', views.FetchNestoActivityLogs),

    url(r'^bulk-upload-nesto-products/$', views.BulkUploadNestoProducts),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)