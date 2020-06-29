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
    url(r'^fetch-super-categories/$', views.FetchSuperCategories),

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
    url(r'^update-banner-name/$', views.UpdateBannerName),
    url(r'^fetch-banner/$', views.FetchBanner),
    url(r'^delete-banner/$', views.DeleteBanner),
    url(r'^publish-banner/$', views.PublishBanner),
    url(r'^unpublish-banner/$', views.UnPublishBanner),
    url(r'^update-link-banner/$', views.UpdateLinkBanner),
    url(r'^add-banner-image/$', views.AddBannerImage),
    url(r'^update-banner-image/$', views.UpdateBannerImage),
    url(r'^delete-banner-image/$', views.DeleteBannerImage),
    url(r'^delete-unit-banner/$', views.DeleteUnitBanner),

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

    url(r'^fetch-bulk-product-info/$', views.FetchBulkProductInfo), # Converted into Function
    url(r'^fetch-bulk-product-price/$', views.FetchBulkProductPrice),

    url(r'^fetch-website-group-brands/$', views.FetchWebsiteGroupBrands),   
    url(r'^generate-stock-price-report/$', views.GenerateStockPriceReport),   

    url(r'^add-product-to-unit-banner/$', views.AddProductToUnitBanner),
    url(r'^delete-product-from-unit-banner/$', views.DeleteProductFromUnitBanner),
    url(r'^fetch-unit-banner-products/$', views.FetchUnitBannerProducts),

    url(r'^search-category-autocomplete/$', views.SearchCategoryAutocomplete),
    url(r'^add-category-to-website-group/$', views.AddCategoryToWebsiteGroup),
    url(r'^remove-category-from-website-group/$', views.RemoveCategoryFromWebsiteGroup),
    url(r'^update-category-image/$', views.UpdateCategoryImage),
    url(r'^update-super-category-image/$', views.UpdateSuperCategoryImage),
    url(r'^update-promotional-price/$', views.UpdatePromotionalPrice),
    url(r'^update-unit-banner/$', views.UpdateUnitBanner),

    url(r'^refresh-stock/$', views.RefreshStock), # Added into Function
]

##################################################### 

# DealsHub project

#####################################################

urlpatterns += [
    url(r'^api/dealshub/v1.0/address/fetch-shipping-address-list/$', views.FetchShippingAddressList),
    url(r'^api/dealshub/v1.0/address/edit-shipping-address/$', views.EditShippingAddress),
    url(r'^api/dealshub/v1.0/address/create-shipping-address/$', views.CreateShippingAddress),
    url(r'^api/dealshub/v1.0/address/delete-shipping-address/$', views.DeleteShippingAddress),

    url(r'^api/dealshub/v1.0/product/fetch-product-details/$', views.FetchProductDetails),
    url(r'^api/dealshub/v1.0/product/fetch-categories/$', views.FetchCategories),
    url(r'^api/dealshub/v1.0/product/search/$', views.Search),

    url(r'^api/dealshub/v1.0/cart/add-to-cart/$', views.AddToCart),
    url(r'^api/dealshub/v1.0/cart/fetch-cart-details/$', views.FetchCartDetails),
    url(r'^api/dealshub/v1.0/cart/update-cart-details/$', views.UpdateCartDetails),
    url(r'^api/dealshub/v1.0/cart/remove-from-cart/$', views.RemoveFromCart),

    url(r'^api/dealshub/v1.0/cart/add-to-wishlist/$', views.AddToWishlist),
    url(r'^api/dealshub/v1.0/cart/fetch-wishlist-details/$', views.FetchWishlistDetails),
    url(r'^api/dealshub/v1.0/cart/remove-from-wishlist/$', views.RemoveFromWishlist),

    url(r'^api/dealshub/v1.0/checkout/select-address/$', views.SelectAddress),
    url(r'^api/dealshub/v1.0/checkout/select-payment-mode/$', views.SelectPaymentMode),
    url(r'^api/dealshub/v1.0/checkout/fetch-active-order-details/$', views.FetchActiveOrderDetails),
    url(r'^api/dealshub/v1.0/checkout/place-order/$', views.PlaceOrder),
    url(r'^api/dealshub/v1.0/checkout/cancel-order/$', views.CancelOrder),
    url(r'^api/dealshub/v1.0/order/fetch-order-list/$', views.FetchOrderList),
    url(r'^api/dealshub/v1.0/order/fetch-order-list-admin/$', views.FetchOrderListAdmin),
    url(r'^api/dealshub/v1.0/order/fetch-order-details/$', views.FetchOrderDetails),

    url(r'^api/dealshub/v1.0/payment/fetch-token-request-parameters/$', views.FetchTokenRequestParameters),
    url(r'^api/dealshub/v1.0/payment/make-purchase-request/$', views.MakePurchaseRequest),
    url(r'^api/dealshub/v1.0/payment/fetch-installment-plans/$', views.FetchInstallmentPlans),
    url(r'^api/dealshub/v1.0/payment/make-purchase-request-installment/$', views.MakePurchaseRequestInstallment),

    url(r'^api/dealshub/v1.0/payment/calculate-signature/$', views.CalculateSignature),

    url(r'^api/dealshub/v1.0/user/fetch-user-profile/$', views.FetchUserProfile),
    url(r'^api/dealshub/v1.0/user/update-user-profile/$', views.UpdateUserProfile),

    url(r'^api/dealshub/v1.0/fetch-customer-list/$', views.FetchCustomerList),
    url(r'^api/dealshub/v1.0/fetch-customer-details/$', views.FetchCustomerDetails),
    url(r'^api/dealshub/v1.0/fetch-customer-orders/$', views.FetchCustomerOrders),

    url(r'^payfort/payment-transaction/$',views.PaymentTransaction),
    url(r'^payfort/payment-notification/$',views.PaymentNotification),

    
    url(r'^api/dealshub/v1.0/fetch-orders-for-account-manager/$', views.FetchOrdersForAccountManager),
    url(r'^api/dealshub/v1.0/fetch-orders-for-warehouse-manager/$', views.FetchOrdersForWarehouseManager),
    url(r'^api/dealshub/v1.0/set-shipping-method/$', views.SetShippingMethod),
    url(r'^api/dealshub/v1.0/set-orders-status/$', views.SetOrdersStatus),
    url(r'^api/dealshub/v1.0/cancel-orders/$', views.CancelOrders),

    url(r'^api/dealshub/v1.0/download-orders/$', views.DownloadOrders),
    url(r'^api/dealshub/v1.0/upload-orders/$', views.UploadOrders),


    url(r'^api/dealshub/v1.0/contact-us-send-email/$', views.ContactUsSendEmail),

    url(r'^api/dealshub/v1.0/send-otp-sms/$', views.SendOTPSMS),
    url(r'^api/dealshub/v1.0/verify-otp-sms/$', views.VerifyOTPSMS),

    url(r'^api/dealshub/v1.0/send-otp-sms-login/$', views.SendOTPSMSLogin),
    url(r'^api/dealshub/v1.0/verify-otp-sms-login/$', views.VerifyOTPSMSLogin),

    url(r'^api/dealshub/v1.0/update-user-email/$', views.UpdateUserEmail),

    url(r'^api/dealshub/v1.0/add-review/$', views.AddReview),
    url(r'^api/dealshub/v1.0/add-rating/$', views.AddRating),
    url(r'^api/dealshub/v1.0/update-rating/$', views.UpdateRating),
    url(r'^api/dealshub/v1.0/add-admin-comment/$', views.AddAdminComment),
    url(r'^api/dealshub/v1.0/update-admin-comment/$', views.UpdateAdminComment),
    url(r'^api/dealshub/v1.0/add-upvote/$', views.AddUpvote),
    url(r'^api/dealshub/v1.0/delete-upvote/$', views.DeleteUpvote),
    url(r'^api/dealshub/v1.0/fetch-review/$', views.FetchReview),
    url(r'^api/dealshub/v1.0/fetch-product-reviews/$', views.FetchProductReviews),
    url(r'^api/dealshub/v1.0/delete-user-review/$', views.DeleteUserReview)
]
