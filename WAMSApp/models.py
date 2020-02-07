from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.db import models
from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

#from WAMSApp.utils import *

from PIL import Image as IMAGE
#from io import BytesIO as StringIO
from io import BytesIO
import logging
import sys
import json
import uuid

logger = logging.getLogger(__name__)

noon_product_json = {
    
    "product_name" : "",
    "product_type" : "",
    "product_subtype" : "",
    "parent_sku" : "",
    "category" : "",
    "sub_category" : "",
    "model_number" : "",
    "model_name" : "",
    "msrp_ae" : "",
    "msrp_ae_unit" : "",
    "product_description" : "",
    "product_attribute_list" : [],
    "created_date" : "",
    "is_active" : "",
    "http_link": ""
}

amazon_uk_product_json = {

    "product_name" : "",
    "product_description" : "",
    "product_attribute_list" : [],
    "category" : "",
    "sub_category" : "",
    "created_date" : "",
    "parentage" : "",
    "parent_sku" : "",
    "relationship_type" : "",
    "variation_theme" : "",
    "feed_product_type" : "",
    "update_delete" : "",
    "recommended_browse_nodes" : "",
    "search_terms" : "",
    "enclosure_material" : "",
    "cover_material_type" : "",
    "special_features" : [],
    "sale_price" : "",
    "sale_from" : "",
    "sale_end" :  "",
    "wattage" : "",
    "wattage_metric" : "",
    "item_count" : "",
    "item_count_metric" : "",
    "item_condition_note" : "",
    "max_order_quantity" : "",
    "number_of_items" : "",
    "condition_type" : "",
    "dimensions": {
        "package_length":"",
        "package_length_metric":"",
        "package_width":"",
        "package_width_metric":"",
        "package_height":"",
        "package_height_metric":"",
        "package_weight":"",
        "package_weight_metric":"",
        "package_quantity":"",
        "shipping_weight":"",
        "shipping_weight_metric":"",
        "item_display_weight":"",
        "item_display_weight_metric":"",
        "item_display_volume":"",
        "item_display_volume_metric":"",
        "item_display_length":"",
        "item_display_length_metric":"",
        "item_weight":"",
        "item_weight_metric":"",
        "item_length":"",
        "item_length_metric":"",
        "item_width":"",
        "item_width_metric":"",
        "item_height":"",
        "item_height_metric":"",
        "item_display_width":"",
        "item_display_width_metric":"",
        "item_display_height":"",
        "item_display_height_metric":""
    },
    "is_active" : "",
    "http_link": ""
}

amazon_uae_product_json = {

    "product_name" : "",
    "product_description" : "",
    "product_attribute_list" : [],
    "category" : "",
    "sub_category" : "",
    "created_date" : "",
    "feed_product_type" : "",
    "recommended_browse_nodes" : "",
    "update_delete" : "",
    "is_active" : "",
    "http_link": ""
}

ebay_product_json = {

    "category" : "",
    "sub_category" : "",
    "product_name" : "",
    "product_description" : "",
    "product_attribute_list" : [],
    "created_date" : "",
    "is_active" : "",
    "http_link": ""
}

base_dimensions_json = {
    "export_carton_quantity_l": "",
    "export_carton_quantity_l_metric": "",
    "export_carton_quantity_b": "",
    "export_carton_quantity_b_metric": "",
    "export_carton_quantity_h": "",
    "export_carton_quantity_h_metric": "",
    "export_carton_crm_l": "",
    "export_carton_crm_l_metric": "",
    "export_carton_crm_b": "",
    "export_carton_crm_b_metric": "",
    "export_carton_crm_h": "",
    "export_carton_crm_h_metric": "",
    "product_dimension_l": "",
    "product_dimension_l_metric": "",
    "product_dimension_b": "",
    "product_dimension_b_metric": "",
    "product_dimension_h": "",
    "product_dimension_h_metric": "",
    "giftbox_l": "",
    "giftbox_l_metric": "",
    "giftbox_b": "",
    "giftbox_b_metric": "",
    "giftbox_h": "",
    "giftbox_h_metric": ""
}

noon_product_json  = json.dumps(noon_product_json)
amazon_uk_product_json = json.dumps(amazon_uk_product_json)
amazon_uae_product_json = json.dumps(amazon_uae_product_json)
ebay_product_json = json.dumps(ebay_product_json)
base_dimensions_json = json.dumps(base_dimensions_json)

class ContentManager(User):

    image = models.ImageField(upload_to='',null=True,blank=True)
    contact_number = models.CharField(max_length=200, default="",null=True)

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.set_password(self.password)
        super(ContentManager, self).save(*args, **kwargs)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "ContentManager"
        verbose_name_plural = "ContentManagers"


class ContentExecutive(User):

    image = models.ImageField(upload_to='',null=True,blank=True)
    contact_number = models.CharField(max_length=200, default="",null=True)

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.set_password(self.password)
        super(ContentExecutive, self).save(*args, **kwargs)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "ContentExecutive"
        verbose_name_plural = "ContentExecutives"


class Image(models.Model):

    description = models.TextField(null=True, blank=True)
    image = models.ImageField(upload_to='')
    thumbnail = models.ImageField(upload_to='thumbnails', null=True, blank=True)
    mid_image = models.ImageField(upload_to='midsize', null=True, blank=True)

    class Meta:
        verbose_name = "Image"
        verbose_name_plural = "Images"

    def __str__(self):
        return str(self.image.url)

    def save(self, *args, **kwargs):
        try:  
            size = 128, 128
            thumb = IMAGE.open(self.image)
            thumb.thumbnail(size)
            infile = self.image.file.name
            im_type = thumb.format 
            thumb_io = BytesIO()
            thumb.save(thumb_io, format=im_type)

            thumb_file = InMemoryUploadedFile(thumb_io, None, infile, 'image/'+im_type, thumb_io.getbuffer().nbytes, None)

            self.thumbnail = thumb_file

            size2 = 512, 512
            thumb2 = IMAGE.open(self.image)
            thumb2.thumbnail(size2)
            thumb_io2 = BytesIO()
            thumb2.save(thumb_io2, format=im_type)

            thumb_file2 = InMemoryUploadedFile(thumb_io2, None, infile, 'image/'+im_type, thumb_io2.getbuffer().nbytes, None)

            self.mid_image = thumb_file2
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("save Image: %s at %s", e, str(exc_tb.tb_lineno))

        super(Image, self).save(*args, **kwargs)

class ImageBucket(models.Model):

    description = models.TextField(null=True, blank=True)
    image = models.ForeignKey(Image, null=True, blank=True, on_delete=models.CASCADE)
    is_main_image = models.BooleanField(default=False)
    is_sub_image = models.BooleanField(default=False)
    sub_image_index = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Image Bucket"
        verbose_name_plural = "Image Buckets"

    def __str__(self):
        return str(self.image)

    def save(self, *args, **kwargs):
        super(ImageBucket, self).save(*args, **kwargs)
        

class Organization(models.Model):

    name = models.CharField(unique=True, max_length=100)

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organization"

    def __str__(self):
        return str(self.name)


class Channel(models.Model):
    
    name = models.CharField(unique=True,max_length=200)
        
    class Meta:
        verbose_name = "Channel"
        verbose_name_plural = "Channels"

    def __str__(self):
        return str(self.name)


class Brand(models.Model):

    name = models.CharField(unique=True, max_length=100)
    logo = models.ForeignKey(Image, null=True, blank=True, on_delete=models.SET_NULL)
    organization = models.ForeignKey(Organization, null=True, blank=True)
 
    class Meta:
        verbose_name = "Brand"
        verbose_name_plural = "Brands"

    def __str__(self):
        return str(self.name)

class Category(models.Model):

    name = models.CharField(unique=True, max_length=250)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Category"

    def __str__(self):
        return str(self.name)


class ProductIDType(models.Model):

    name = models.CharField(unique=True, max_length=100)

    class Meta:
        verbose_name = "ProductIDType"
        verbose_name_plural = "ProductIDTypes"

    def __str__(self):
        return str(self.name)


class MaterialType(models.Model):

    name = models.CharField(unique=True, max_length=100)

    class Meta:
        verbose_name = "MaterialType"
        verbose_name_plural = "MaterialTypes"

    def __str__(self):
        return str(self.name)


class BaseProduct(models.Model):

    base_product_name = models.CharField(max_length=300)
    created_date = models.DateTimeField()
    modified_date = models.DateTimeField()
    seller_sku = models.CharField(max_length=200, unique=True)
    category = models.CharField(max_length=200, default="")
    sub_category = models.CharField(max_length=200, default="")
    subtitle = models.CharField(max_length=200, default="")
    brand = models.ForeignKey(Brand, null=True, blank=True, on_delete=models.SET_NULL)
    manufacturer = models.CharField(max_length=200, default="")
    manufacturer_part_number = models.CharField(max_length=200, default="")

    dimensions = models.TextField(blank=True, default=base_dimensions_json)
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "BaseProduct"
        verbose_name_plural = "BaseProducts"

    def __str__(self):
        return str(self.base_product_name)

    def save(self, *args, **kwargs):
        
        if self.pk == None:
            self.created_date = timezone.now()
            self.modified_date = timezone.now()
        else:
            self.modified_date = timezone.now()
        
        super(BaseProduct, self).save(*args, **kwargs)

auditlog.register(BaseProduct, exclude_fields=['modified_date' , 'created_date'])


class ChannelProduct(models.Model):
    
    # product = models.ForeignKey(Product,null=True, blank=True, related_name="product", on_delete=models.SET_NULL)
    noon_product_json = models.TextField(blank=True,default=noon_product_json)
    is_noon_product_created = models.BooleanField(default=False)
    amazon_uk_product_json = models.TextField(blank=True,default=amazon_uk_product_json)
    is_amazon_uk_product_created = models.BooleanField(default=False)
    amazon_uae_product_json = models.TextField(blank=True,default=amazon_uae_product_json)
    is_amazon_uae_product_created = models.BooleanField(default=False)
    ebay_product_json = models.TextField(blank=True,default=ebay_product_json)
    is_ebay_product_created = models.BooleanField(default=False)

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "ChannelProduct"
        verbose_name_plural = "ChannelProducts"

    def __str__(self):
        try:
            product = Product.objects.get(channel_product = self)
            return str(product.product_name)
        except Exception as e:
            return str(self.pk)

auditlog.register(ChannelProduct, exclude_fields = ['is_noon_product_created', 'is_amazon_uk_product_created',
                                                    'is_amazon_uae_product_created', 'is_ebay_product_created'])

class Product(models.Model):

    #MISC
    base_product = models.ForeignKey(BaseProduct,null=True,blank=True,on_delete=models.SET_NULL)
    product_name = models.CharField(max_length=300,null=True)
    product_id = models.CharField(max_length=200,null=True)
    product_id_type = models.ForeignKey(ProductIDType,null=True,blank=True,on_delete=models.SET_NULL)
    product_description = models.TextField(blank=True)
    created_date = models.DateTimeField()
    modified_date = models.DateTimeField()
    
    status = models.CharField(default="Pending", max_length=100)
    verified = models.BooleanField(default=False)
    uuid = models.CharField(null=True,max_length=200)
    factory_code = models.CharField(null=True,max_length=200)

    #PFL
    pfl_product_name = models.CharField(max_length=300, default="")
    pfl_product_features = models.TextField(default="[]")

    product_name_sap = models.CharField(max_length=300, default="")
    color_map = models.CharField(max_length=100, default="")
    color = models.CharField(max_length=100, default="")
    material_type = models.ForeignKey(MaterialType,null=True,blank=True,on_delete=models.SET_NULL)
    standard_price = models.FloatField(null=True, blank=True)
    quantity = models.IntegerField(null=True, blank=True)

    pfl_images = models.ManyToManyField(Image, related_name="pfl_images", blank=True)
    white_background_images = models.ManyToManyField(Image, related_name="white_background_images", blank=True)
    lifestyle_images = models.ManyToManyField(Image, related_name="lifestyle_images", blank=True)
    certificate_images = models.ManyToManyField(Image, related_name="certificate_images", blank=True)
    giftbox_images = models.ManyToManyField(Image, related_name="giftbox_images", blank=True)
    diecut_images = models.ManyToManyField(Image, related_name="diecut_images", blank=True)
    aplus_content_images = models.ManyToManyField(Image, related_name="aplus_content_images", blank=True)
    ads_images = models.ManyToManyField(Image, related_name="ads_images", blank=True)
    unedited_images = models.ManyToManyField(Image, related_name="unedited_images", blank=True)
    pfl_generated_images = models.ManyToManyField(Image , related_name="pfl_generated_images" , blank = True)
    transparent_images = models.ManyToManyField(Image , related_name="transparent_images" , blank = True)


    # Other info
    barcode = models.ForeignKey(Image, null=True, blank=True, on_delete=models.SET_NULL)
    barcode_string = models.CharField(max_length=100, default="")
    outdoor_price = models.FloatField(null=True, blank=True)

    channel_product = models.ForeignKey(ChannelProduct, null=True, blank=True, on_delete=models.SET_NULL)
    factory_notes = models.TextField(null=True,blank=True)
    history = AuditlogHistoryField()

    sap_cache = models.TextField(default="[]")
    sap_cache_time = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return str(self.product_name)


    def save(self, *args, **kwargs):
        
        if self.pk != None:
            self.modified_date = timezone.now()
        else:
            self.created_date = timezone.now()
            self.modified_date = timezone.now()
        
        if self.uuid == None:
            self.uuid = uuid.uuid4()

        if self.channel_product == None:
            channel_product_obj = ChannelProduct.objects.create()
            self.channel_product = channel_product_obj
        
        super(Product, self).save(*args, **kwargs)

auditlog.register(Product, exclude_fields=['modified_date' , 'created_date' , 'uuid', 'base_product'])

auditlog.register(Product.pfl_images.through)
auditlog.register(Product.white_background_images.through)
auditlog.register(Product.lifestyle_images.through)
auditlog.register(Product.certificate_images.through)
auditlog.register(Product.giftbox_images.through)
auditlog.register(Product.diecut_images.through)
auditlog.register(Product.aplus_content_images.through)
auditlog.register(Product.ads_images.through)
auditlog.register(Product.unedited_images.through)
auditlog.register(Product.pfl_generated_images.through)
auditlog.register(Product.transparent_images.through)

class MainImages(models.Model):

    product = models.ForeignKey(Product,null=True, blank=True, on_delete=models.SET_NULL)
    main_images = models.ManyToManyField(ImageBucket, related_name="main_images", blank=True)
    channel = models.ForeignKey(Channel,null=True, blank=True, on_delete=models.SET_NULL)
    is_sourced = models.BooleanField(default=False)

    history = AuditlogHistoryField()

    class Meta:
        verbose_name_plural = "MainImages"

    def __str__(self):
        return str(self.product.product_name)

auditlog.register(MainImages, exclude_fields = ['is_sourced'])
auditlog.register(MainImages.main_images.through)

class SubImages(models.Model):

    product = models.ForeignKey(Product,null=True, blank=True, related_name="product", on_delete=models.SET_NULL)
    sub_images = models.ManyToManyField(ImageBucket, related_name="sub_images", blank=True)
    channel = models.ForeignKey(Channel,null=True, blank=True, on_delete=models.SET_NULL)
    is_sourced = models.BooleanField(default=False)

    history = AuditlogHistoryField()

    class Meta:
        verbose_name_plural = "SubImages"

    def __str__(self):
        return str(self.product.product_name)
    
auditlog.register(SubImages, exclude_fields=['is_sourced'])
auditlog.register(SubImages.sub_images.through)

class Flyer(models.Model):

    name = models.CharField(default="SampleFlyer", max_length=200)
    product_bucket = models.ManyToManyField(Product, blank=True)
    template_data = models.TextField(null=True, blank=True)
    external_images_bucket = models.ManyToManyField(Image, blank=True)
    flyer_image = models.ForeignKey(Image, null=True, blank=True, related_name="flyer_images", on_delete=models.SET_NULL)
    background_images_bucket = models.ManyToManyField(Image, blank=True, related_name="background_images_bucket")
    brand = models.ForeignKey(Brand, null=True, blank=True, on_delete=models.SET_NULL)
    mode = models.CharField(max_length=100, default="A4 Portrait")

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Flyer"
        verbose_name_plural = "Flyers"

    def __str__(self):
        return str(self.name)

auditlog.register(Flyer, exclude_fields=['template_data','background_images_bucket'])
auditlog.register(Flyer.product_bucket.through)

class PFL(models.Model):

    name = models.CharField(default="SamplePFL", max_length=300)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL)
    product_image = models.ForeignKey(Image, null=True, blank=True, related_name="product_images", on_delete=models.SET_NULL)
    template_data = models.TextField(null=True, blank=True)
    external_images_bucket = models.ManyToManyField(Image, blank=True)

    class Meta:
        verbose_name = "PFL"
        verbose_name_plural = "PFL"

    def __str__(self):
        return str(self.name)


class ExportList(models.Model):

    title = models.CharField(default="SampleExportList", max_length=200)
    products = models.ManyToManyField(Product, blank=True)
    created_date = models.DateTimeField()
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    channel = models.ForeignKey(Channel,null=True,blank=True, on_delete=models.SET_NULL)

    history = AuditlogHistoryField()
    
    class Meta:
        verbose_name = "ExportList"
        verbose_name_plural = "ExportLists"

    def __str__(self):
        return str(self.title)

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.created_date = timezone.now()
        super(ExportList, self).save(*args, **kwargs)


auditlog.register(ExportList, exclude_fields=['created_date'])
auditlog.register(ExportList.products.through)

class Config(models.Model):

    product_404_image = models.ForeignKey(Image, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = "Config"
        verbose_name_plural = "Config"

    def __str__(self):
        return "Configuration"


class CustomPermission(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    brands = models.ManyToManyField(Brand, blank=True)
    channels = models.ManyToManyField(Channel, blank=True)

    class Meta:
        verbose_name = "CustomPermission"
        verbose_name_plural = "CustomPermissions"

    def __str__(self):
        return str(self.user)


class EbayCategory(models.Model):

    category_id = models.CharField(default="", max_length=100)
    name = models.CharField(default="", max_length=200)

    class Meta:
        verbose_name = "EbayCategory"
        verbose_name_plural = "EbayCategory"

    def __str__(self):
        return str(self.name)


class BackgroundImage(models.Model):

    image = models.ForeignKey(Image, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Background Image"
        verbose_name_plural = "Background Images"

    def __str__(self):
        return str(self.pk)

@receiver(post_save, sender=Product, dispatch_uid="create_pfl")
def update_stock(sender, instance, **kwargs):
    if PFL.objects.filter(product=instance).exists()==False:
        PFL.objects.create(product=instance, name=str(instance.product_name_sap)+"_PFL")







































































































