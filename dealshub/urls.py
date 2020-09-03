from django.conf.urls import url
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect


urlpatterns = [
    url(r'^fetch-product-details/$', views.FetchProductDetails),
    url(r'^fetch-section-products/$', views.FetchSectionProducts),
    url(r'^fetch-super-categories/$', views.FetchSuperCategories),
    url(r'^fetch-heading-categories/$', views.FetchHeadingCategories),

    url(r'^search/$', views.Search),

    url(r'^create-admin-category/$', views.CreateAdminCategory),
    url(r'^update-admin-category/$', views.UpdateAdminCategory),
    url(r'^delete-admin-category/$', views.DeleteAdminCategory),
    url(r'^publish-admin-category/$', views.PublishAdminCategory),
    url(r'^unpublish-admin-category/$', views.UnPublishAdminCategory),

    url(r'^section-bulk-upload/$', views.SectionBulkUpload),
    url(r'^add-product-to-section/$', views.AddProductToSection),
    url(r'^delete-product-from-section/$', views.DeleteProductFromSection),

    url(r'^fetch-banner-types/$', views.FetchBannerTypes),
    url(r'^create-banner/$', views.CreateBanner),
    url(r'^update-banner-name/$', views.UpdateBannerName),
    url(r'^delete-banner/$', views.DeleteBanner),
    url(r'^publish-banner/$', views.PublishBanner),
    url(r'^unpublish-banner/$', views.UnPublishBanner),
    url(r'^add-banner-image/$', views.AddBannerImage),
    url(r'^update-banner-image/$', views.UpdateBannerImage),
    url(r'^delete-banner-image/$', views.DeleteBannerImage),
    url(r'^delete-unit-banner/$', views.DeleteUnitBanner),

    url(r'^publish-dealshub-product/$', views.PublishDealsHubProduct),
    url(r'^unpublish-dealshub-product/$', views.UnPublishDealsHubProduct),
    url(r'^publish-dealshub-products/$', views.PublishDealsHubProducts),
    url(r'^unpublish-dealshub-products/$', views.UnPublishDealsHubProducts),

    url(r'^activate-cod-dealshub-product/$', views.ActivateCODDealsHubProduct),
    url(r'^deactivate-cod-dealshub-product/$', views.DeactivateCODDealsHubProduct),

    url(r'^fetch-dealshub-admin-sections/$', views.FetchDealshubAdminSections),
    url(r'^save-dealshub-admin-sections-order/$', views.SaveDealshubAdminSectionsOrder),

    url(r'^search-section-products-autocomplete/$', views.SearchSectionProductsAutocomplete),
    url(r'^search-products-autocomplete/$', views.SearchProductsAutocomplete),
    url(r'^search-products/$', views.SearchProducts),

    url(r'^fetch-dealshub-price/$', views.FetchDealshubPrice),

    url(r'^fetch-company-profile-dealshub/$', views.FetchCompanyProfileDealshub),
    url(r'^fetch-website-group-brands/$', views.FetchWebsiteGroupBrands),

    url(r'^add-product-to-unit-banner/$', views.AddProductToUnitBanner),
    url(r'^delete-product-from-unit-banner/$', views.DeleteProductFromUnitBanner),
    url(r'^fetch-unit-banner-products/$', views.FetchUnitBannerProducts),

    url(r'^add-unit-banner-hovering-image/$', views.AddUnitBannerHoveringImage),
    url(r'^fetch-unit-banner-hovering-image/$', views.FetchUnitBannerHoveringImage),

    url(r'^add-section-hovering-image/$', views.AddSectionHoveringImage),
    url(r'^fetch-section-hovering-image/$', views.FetchSectionHoveringImage),

    url(r'^delete-hovering-image/$',views.DeleteHoveringImage),

    url(r'^update-super-category-image/$', views.UpdateSuperCategoryImage),
    url(r'^update-unit-banner/$', views.UpdateUnitBanner),

    url(r'^address/fetch-shipping-address-list/$', views.FetchShippingAddressList),
    url(r'^address/edit-shipping-address/$', views.EditShippingAddress),
    url(r'^address/create-shipping-address/$', views.CreateShippingAddress),
    url(r'^address/create-offline-shipping-address/$', views.CreateOfflineShippingAddress),
    url(r'^address/delete-shipping-address/$', views.DeleteShippingAddress),

    url(r'^cart/add-to-cart/$', views.AddToCart),
    url(r'^cart/add-to-offline_cart/$',views.AddToOfflineCart),
    url(r'^cart/fetch-cart-details/$', views.FetchCartDetails),
    url(r'^cart/fetch-offline-cart-details/$',views.FetchOfflineCartDetails),
    url(r'^cart/update-cart-details/$', views.UpdateCartDetails),
    url(r'^cart/remove-from-cart/$', views.RemoveFromCart),

    url(r'^checkout/select-address/$', views.SelectAddress),
    url(r'^checkout/select-offline-address/$', views.SelectOfflineAddress),
    url(r'^checkout/select-payment-mode/$', views.SelectPaymentMode),
    url(r'^checkout/fetch-active-order-details/$', views.FetchActiveOrderDetails),
    url(r'^checkout/place-order/$', views.PlaceOrder),
    url(r'^checkout/place-offline-order/$',views.PlaceOfflineOrder),
    url(r'^checkout/place-online-order/$',views.PlaceOnlineOrder),
    url(r'^checkout/cancel-order/$', views.CancelOrder),
    url(r'^order/fetch-order-list/$', views.FetchOrderList),
    url(r'^order/fetch-order-list-admin/$', views.FetchOrderListAdmin),
    url(r'^order/fetch-order-details/$', views.FetchOrderDetails),

    url(r'^payment/fetch-token-request-parameters/$', views.FetchTokenRequestParameters),
    url(r'^payment/make-purchase-request/$', views.MakePurchaseRequest),
    # url(r'^payment/fetch-installment-plans/$', views.FetchInstallmentPlans),
    # url(r'^payment/make-purchase-request-installment/$', views.MakePurchaseRequestInstallment),

    url(r'^payment/calculate-signature/$', views.CalculateSignature),

    url(r'^user/create-offline-customer/$', views.CreateOfflineCustomer),
    url(r'^user/update-offline-user-profile/$', views.UpdateOfflineUserProfile),
    url(r'^user/search-customer-autocomplete/$', views.SearchCustomerAutocomplete),
    url(r'^user/fetch-offline-user-profile/$', views.FetchOfflineUserProfile),
    url(r'^user/fetch-user-profile/$', views.FetchUserProfile),
    url(r'^user/update-user-profile/$', views.UpdateUserProfile),

    url(r'^fetch-customer-list/$', views.FetchCustomerList),
    url(r'^fetch-customer-details/$', views.FetchCustomerDetails),
    url(r'^fetch-customer-orders/$', views.FetchCustomerOrders),

    url(r'^payfort/payment-notification/$',views.PaymentNotification),

    url(r'^fetch-orders-for-warehouse-manager/$', views.FetchOrdersForWarehouseManager),
    url(r'^set-shipping-method/$', views.SetShippingMethod),
    url(r'^set-orders-status/$', views.SetOrdersStatus),
    url(r'^cancel-orders/$', views.CancelOrders),

    url(r'^download-orders/$', views.DownloadOrders),
    url(r'^upload-orders/$', views.UploadOrders),
    url(r'^apply-voucher-code/$', views.ApplyVoucherCode),
    url(r'^remove-voucher-code/$', views.RemoveVoucherCode),

    url(r'^apply-offline-voucher-code/$', views.ApplyOfflineVoucherCode),
    url(r'^remove-offline-voucher-code/$', views.RemoveOfflineVoucherCode),

    url(r'^contact-us-send-email/$', views.ContactUsSendEmail),

    url(r'^fetch-user-existance/$', views.FetchUserExistance),
    url(r'^set-pin-login/$', views.SetPinLogin),
    url(r'^verify-pin-sms-login/$', views.VerifyPinSMSLogin),

    url(r'^update-user-email/$', views.UpdateUserEmail),

    url(r'^add-review/$', views.AddReview),
    url(r'^add-rating/$', views.AddRating),
    url(r'^update-rating/$', views.UpdateRating),
    url(r'^add-admin-comment/$', views.AddAdminComment),
    url(r'^update-admin-comment/$', views.UpdateAdminComment),
    url(r'^add-upvote/$', views.AddUpvote),
    url(r'^delete-upvote/$', views.DeleteUpvote),
    url(r'^fetch-review/$', views.FetchReview),
    url(r'^fetch-product-reviews/$', views.FetchProductReviews),
    url(r'^delete-user-review-image/$', views.DeleteUserReviewImage),
    url(r'^delete-user-review/$', views.DeleteUserReview),

    url(r'^create-voucher/$', views.CreateVoucher),
    url(r'^update-voucher/$', views.UpdateVoucher),    
    url(r'^fetch-vouchers/$', views.FetchVouchers),
    url(r'^delete-voucher/$', views.DeleteVoucher),
    url(r'^publish-voucher/$', views.PublishVoucher),
    url(r'^unpublish-voucher/$', views.UnPublishVoucher),

    url(r'^fetch-order-analytics-params/$', views.FetchOrderAnalyticsParams),
    url(r'^make-payment-network-global/$',views.MakePaymentNetworkGlobal),

    url(r'^fetch-postaplus-tracking/$',views.FetchPostaPlusTracking),

    url(r'^wish-list/add-to-wish-list/$', views.AddToWishList),
    url(r'^wish-list/remove-from-wish-list/$', views.RemoveFromWishList),
    url(r'^wish-list/fetch-wish-list/$', views.FetchWishList),

    url(r'^fetch-postaplus-details/$',views.FetchPostaPlusDetails),
]
