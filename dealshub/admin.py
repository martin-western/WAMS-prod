# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from dealshub.models import *


class DealsHubProductAdmin(admin.ModelAdmin):
    list_display = ('product',)


class DealshubAdminSectionOrderAdmin(admin.ModelAdmin):
    list_display = ('dealshub_banner_index', 'homepage_schedular_index', 'full_banner_ad_index', 'category_grid_banner_index')


class SectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'order_index')


class DealsHubUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'contact_verified', 'verification_code', 'date_created')


class CartAdmin(admin.ModelAdmin):
    list_display = ('owner', 'merchant_reference')

class FastCartAdmin(admin.ModelAdmin):
    list_display = ('owner', 'merchant_reference')


admin.site.register(DealsHubProduct, DealsHubProductAdmin)
admin.site.register(Section, SectionAdmin)
admin.site.register(BannerType)
admin.site.register(Banner)
admin.site.register(UnitBannerImage)
admin.site.register(Address)
admin.site.register(UnitCart)
admin.site.register(Cart, CartAdmin)
admin.site.register(FastCart, FastCartAdmin)
admin.site.register(DealsHubUser, DealsHubUserAdmin)
admin.site.register(UnitOrder)
admin.site.register(Order)
admin.site.register(Location)
admin.site.register(LocationGroup)
admin.site.register(Voucher)
admin.site.register(WishList)
admin.site.register(UnitWishList)