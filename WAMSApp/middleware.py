from django.contrib.auth.middleware import get_user
from django.utils.functional import SimpleLazyObject
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseForbidden, HttpResponse
from WAMSApp.models import *

class JWTAuthenticationMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user = SimpleLazyObject(lambda:self.__class__.get_jwt_user(request))
        return self.get_response(request)

    @staticmethod
    def get_jwt_user(request):
        user = get_user(request)
        if user.is_authenticated:
            return user
        jwt_authentication = JSONWebTokenAuthentication()
        if jwt_authentication.get_jwt_value(request):
            user, jwt = jwt_authentication.authenticate(request)
        return user


class JWTBlackListTokenCheck(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        return self.process_request(request)
    
    def process_request(self,request):
        if request.user.is_authenticated and request.META["HTTP_AUTHORIZATION"]!= None:
            token = request.META["HTTP_AUTHORIZATION"].split(" ")[1]
            if BlackListToken.objects.filter(token=token).exists()==False:
                return self.get_response(request)
            return HttpResponseForbidden("token not valid")
        return self.get_response(request)