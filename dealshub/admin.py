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


class BannerTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'limit', 'website_group')


class DealsHubUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'contact_verified', 'verification_code', 'date_created')


class CartAdmin(admin.ModelAdmin):
    list_display = ('owner', 'merchant_reference')

class FastCartAdmin(admin.ModelAdmin):
    list_display = ('owner', 'merchant_reference')


class WishListAdmin(admin.ModelAdmin):
	list_display = ('owner',)


class OrderRequestAdmin(admin.ModelAdmin):
	list_display = ('bundleid','owner','date_created')


class BlogPostAdmin(admin.ModelAdmin):
	list_display = ('title',)


class BlogSectionTypeAdmin(admin.ModelAdmin):
	list_display = ('name','limit')

class BlogSectionAdmin(admin.ModelAdmin):
	list_display = ('name','blog_section_type','order_index')


admin.site.register(DealsHubProduct, DealsHubProductAdmin)
admin.site.register(Section, SectionAdmin)
admin.site.register(BannerType, BannerTypeAdmin)
admin.site.register(Banner)
admin.site.register(UnitBannerImage)
admin.site.register(Address)
admin.site.register(UnitCart)
admin.site.register(Cart, CartAdmin)
admin.site.register(FastCart, FastCartAdmin)
admin.site.register(DealsHubUser, DealsHubUserAdmin)
admin.site.register(OrderRequest,OrderRequestAdmin)
admin.site.register(UnitOrderRequest)
admin.site.register(UnitOrder)
admin.site.register(Order)
admin.site.register(Location)
admin.site.register(LocationGroup)
admin.site.register(Voucher)
admin.site.register(WishList,WishListAdmin)
admin.site.register(UnitWishList)
admin.site.register(B2BUser)
admin.site.register(BlogPost,BlogPostAdmin)
admin.site.register(BlogSectionType,BlogSectionTypeAdmin)
admin.site.register(BlogSection,BlogSectionAdmin)
admin.site.register(OrderMailRequest)