# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from SalesApp.models import *


class SalesAppUserAdmin(admin.ModelAdmin):
    list_display = ('username',)

class SalesAppUserAdmin(admin.ModelAdmin):
    list_display = ('username',)

admin.site.register(SalesAppUser, SalesAppUserAdmin)

admin.site.register(SalesAppUser, SalesAppUserAdmin)
