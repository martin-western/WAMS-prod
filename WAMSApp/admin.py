from django.contrib import admin
from django.contrib.auth.models import Group, User
from WAMSApp.models import *

# admin.site.unregister(Group)
# admin.site.unregister(User)

class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'product_id')

class BaseProductAdmin(admin.ModelAdmin):
    list_display = ('base_product_name', 'seller_sku')

class FlyerAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand')

class MainImagesAdmin(admin.ModelAdmin):
    list_display = ('product', 'channel')

class SubImagesAdmin(admin.ModelAdmin):
    list_display = ('product', 'channel')

admin.site.register(OmnyCommUser)
admin.site.register(Product, ProductAdmin)
admin.site.register(ExportList)
admin.site.register(Image)
admin.site.register(MaterialType)
admin.site.register(Category)
admin.site.register(SubCategory)
admin.site.register(Brand)
admin.site.register(ProductIDType)
admin.site.register(ImageBucket)
admin.site.register(PFL)
admin.site.register(Flyer, FlyerAdmin)
admin.site.register(Config)
admin.site.register(CustomPermission)
admin.site.register(Organization)
admin.site.register(EbayCategory)
admin.site.register(BaseProduct, BaseProductAdmin)
admin.site.register(Channel)
admin.site.register(ChannelProduct)
admin.site.register(MainImages, MainImagesAdmin)
admin.site.register(SubImages, SubImagesAdmin)
admin.site.register(BackgroundImage)
admin.site.register(RequestHelp)
admin.site.register(DataPoint)

admin.site.register(PhoneNumber)
admin.site.register(OperatingHour)
admin.site.register(Bank)
admin.site.register(Factory)
admin.site.register(SourcingProduct)
admin.site.register(ProformaInvoice)
admin.site.register(DraftProformaInvoice)
admin.site.register(DraftProformaInvoiceLine)
