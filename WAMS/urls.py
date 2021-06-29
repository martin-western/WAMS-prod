from django.conf.urls import url, include
from django.contrib import admin
from rest_framework_jwt.views import obtain_jwt_token,refresh_jwt_token
from dealshub import views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'', include('WAMSApp.urls')),
    url(r'', include('WAMSApp.nesto.urls_nesto')),
    url(r'^sourcing/', include('WAMSApp.sourcing.urls_sourcing')),
    url(r'^mws/', include('WAMSApp.mws.urls_mws')),
    url(r'^noon-integration/', include('WAMSApp.stores.urls_noon_integration')),
    url(r'^dealshub/', include('dealshub.urls')),
    url(r'^token-auth/', obtain_jwt_token),
    url(r'refresh-auth',refresh_jwt_token)
    url(r'^payfort/payment-transaction/$',views.PaymentTransaction),
    url(r'^sap/',include('WAMSApp.sap.urls_SAP')),
    url(r'^sales-app/', include('SalesApp.urls')),
]
