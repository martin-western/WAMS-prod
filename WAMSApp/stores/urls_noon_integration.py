from django.conf.urls import url
from WAMSApp import views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [

#################################################################################

######################## Noon Integration URLS ##################################

################################################################################# 

    url(r'^push-price/$',views.PushPrice),
    url(r'^push-stock/$',views.PushStock),
    

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
