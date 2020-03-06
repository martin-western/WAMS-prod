from django.conf.urls import url, include
from django.contrib import admin
from rest_framework_jwt.views import obtain_jwt_token

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'', include('WAMSApp.urls')),
    url(r'^sourcing/', include('WAMSApp.urls_sourcing')),
    url(r'^dealshub/', include('dealshub.urls')),
    url(r'^token-auth/', obtain_jwt_token)
]
