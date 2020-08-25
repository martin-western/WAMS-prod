from django.conf.urls import url, include
from django.contrib import admin
from rest_framework_jwt.views import obtain_jwt_token
from dealshub import views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'', include('WAMSApp.urls')),
    url(r'^sourcing/', include('WAMSApp.urls_sourcing')),
    url(r'^mws/', include('WAMSApp.urls_mws')),
    url(r'^noon-integration/', include('WAMSApp.urls_noon_integration')),
    url(r'^dealshub/', include('dealshub.urls')),
    url(r'^token-auth/', obtain_jwt_token),
    url(r'^payfort/payment-transaction/$',views.PaymentTransaction),
    url(r'^sap/$',include('WAMSApp.urls_SAP')),
]
