from django.conf.urls import url
from WAMSApp import views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [

############################## SAP Automation #########################################


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
