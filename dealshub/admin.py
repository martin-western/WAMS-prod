# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from dealshub.models import *

# Register your models here.

admin.site.register(Category)
#admin.site.register(PossibleValues)


# class PropertyInline(admin.TabularInline):
#     model = Property
#     extra = 0
#     min_num = 1


# class SubCategoryAdmin(admin.ModelAdmin):
#     inlines = [PropertyInline]


admin.site.register(SubCategory)


# class PossibleValuesInline(admin.TabularInline):
#     model = PossibleValues
#     fields = ['prop', 'name', 'lable', 'value', 'unit']
#     extra = 0
#     min_num = 1


# class PropertyAdmin(admin.ModelAdmin):
#     inlines = [PossibleValuesInline]


class DealsHubProductAdmin(admin.ModelAdmin):
    list_display = ('product', 'category')


class DealshubAdminSectionOrderAdmin(admin.ModelAdmin):
    list_display = ('dealshub_banner_index', 'homepage_schedular_index', 'full_banner_ad_index', 'category_grid_banner_index')


class SectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'order_index')


#admin.site.register(Property, PropertyAdmin)
admin.site.register(DealsHubProduct, DealsHubProductAdmin)
admin.site.register(Section, SectionAdmin)
admin.site.register(DealsBanner)
admin.site.register(FullBannerAd)
admin.site.register(DealsHubHeading)
admin.site.register(ImageLink)
admin.site.register(DealshubAdminSectionOrder, DealshubAdminSectionOrderAdmin)
admin.site.register(CategoryGridBanner)
admin.site.register(HomePageSchedular)