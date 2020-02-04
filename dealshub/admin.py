# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from dealshub.models import *

# Register your models here.

admin.site.register(Category)
admin.site.register(PossibleValues)


class PropertyInline(admin.TabularInline):
    model = Property
    extra = 0
    min_num = 1


class SubCategoryAdmin(admin.ModelAdmin):
    inlines = [PropertyInline]


admin.site.register(SubCategory, SubCategoryAdmin)


class PossibleValuesInline(admin.TabularInline):
    model = PossibleValues
    fields = ['prop', 'name', 'lable', 'value', 'unit']
    extra = 0
    min_num = 1


class PropertyAdmin(admin.ModelAdmin):
    inlines = [PossibleValuesInline]


class DealsHubProductAdmin(admin.ModelAdmin):
    list_display = ('product', 'category')

admin.site.register(Property, PropertyAdmin)
admin.site.register(DealsHubProduct, DealsHubProductAdmin)
admin.site.register(Section)