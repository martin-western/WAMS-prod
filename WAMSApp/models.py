from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.db import models
from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from PIL import Image as IMAGE
from PIL import ExifTags
from io import BytesIO
from bs4 import BeautifulSoup

import logging
import sys
import json
import uuid

logger = logging.getLogger(__name__)

noon_product_json = {

    "product_name" : "",
    "noon_sku" : "",
    "partner_sku" : "",
    "partner_barcode" : "",
    "psku_code":"",
    "category" : "",
    "subtitle" : "",
    "sub_category" : "",
    "model_number" : "",
    "model_name" : "",
    "msrp_ae" : "",
    "msrp_ae_unit" : "",
    "product_description" : "",
    "product_attribute_list" : [],
    "created_date" : "",
    "status" : "Inactive",
    "http_link": "",
    "was_price":0.0,
    "sale_price":0.0,
    "sale_start":"",
    "sale_end":"",
    "stock":0,
    "warranty":""
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
    "ASIN" : "",
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
    "status" : "Inactive",
    "http_link": "",
    "now_price":0.0,
    "was_price":0.0,
    "stock":0
}

amazon_uae_product_json = {

    "product_name" : "",
    "product_description" : "",
    "product_attribute_list" : [],
    "category" : "",
    "sub_category" : "",
    "created_date" : "",
    "feed_product_type" : "",
    "ASIN" : "",
    "recommended_browse_nodes" : "",
    "update_delete" : "",
    "status" : "Inactive",
    "http_link": "",
    "sale_price":0.0,
    "was_price":0.0,
    "stock":0
}

ebay_product_json = {

    "category" : "",
    "sub_category" : "",
    "product_name" : "",
    "product_description" : "",
    "product_attribute_list" : [],
    "created_date" : "",
    "status" : "Inactive",
    "http_link": "",
    "now_price":0.0,
    "was_price":0.0,
    "stock":0
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


class Location(models.Model):

    name = models.CharField(max_length=200, default="")
    country = models.CharField(max_length=200, default="UAE")
    uuid = models.CharField(max_length=200, default="")
    currency = models.CharField(max_length=20, default="AED")
    payfort_multiplier = models.IntegerField(default=1)

    def __str__(self):
        return str(self.name)

    def save(self, *args, **kwargs):

        if self.uuid == None or self.uuid=="":
            self.uuid = str(uuid.uuid4())

        super(Location, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "Location"


class LocationGroup(models.Model):

    name = models.CharField(max_length=100, default="")
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    website_group = models.ForeignKey('WebsiteGroup', on_delete=models.CASCADE)
    delivery_fee = models.FloatField(default=0)
    free_delivery_threshold = models.FloatField(default=100)
    cod_charge = models.FloatField(default=5)
    vat = models.FloatField(default=5)
    email_info = models.TextField(default="{}")
    mshastra_info = models.TextField(default="{}")
    postaplus_info = models.TextField(default="{}")
    uuid = models.CharField(max_length=200, default="")

    def __str__(self):
        return str(self.name)

    def save(self, *args, **kwargs):

        if self.uuid == None or self.uuid=="":
            self.uuid = str(uuid.uuid4())

        super(LocationGroup, self).save(*args, **kwargs)

    def get_email_host(self):
        return json.loads(self.email_info)["host"]

    def get_email_port(self):
        return int(json.loads(self.email_info)["port"])

    def get_support_email_id(self):
        return json.loads(self.email_info)["support"]["email_id"]

    def get_support_email_password(self):
        return json.loads(self.email_info)["support"]["password"]

    def get_order_from_email_id(self):
        return json.loads(self.email_info)["order"]["email_id"]

    def get_order_from_email_password(self):
        return json.loads(self.email_info)["order"]["password"]

    def get_order_to_email_list(self):
        return json.loads(self.email_info)["order_to_list"]

    def get_order_cc_email_list(self):
        return json.loads(self.email_info)["order_cc_list"]

    def get_order_bcc_email_list(self):
        return json.loads(self.email_info)["order_bcc_list"]

    def get_email_website_logo(self):
        if self.website_group.footer_logo!=None:
            return self.website_group.footer_logo.image.url
        if self.website_group.logo!=None:
            return self.website_group.logo.image.url
        return ""

    def get_email_content(self):
        return json.loads(self.website_group.conf)["email_content"]

    class Meta:
        verbose_name = "LocationGroup"
        verbose_name_plural = "LocationGroup"


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
            
            def rotate_image(image):
                try:
                    exif=dict(image._getexif().items())
                    orientation = 0
                    for index in ExifTags.TAGS.keys():
                        if ExifTags.TAGS[index] =='Orientation':
                            orientation = index
                            break

                    if orientation!= 0 and exif[orientation] == 6:
                        image = image.rotate(270)
                    elif orientation!= 0 and exif[orientation] == 3:
                        image = image.rotate(180)
                    elif orientation!= 0 and exif[orientation] == 8:
                        image = image.rotate(90)
                    elif orientation!= 0 and exif[orientation] == 2:
                        image = image.transpose(Image.FLIP_LEFT_RIGHT)
                    elif orientation!= 0 and exif[orientation] == 5:
                        image = image.transpose(Image.FLIP_LEFT_RIGHT)
                        image = image.rotate(270)
                    elif orientation!= 0 and exif[orientation] == 4:
                        image = image.transpose(Image.FLIP_LEFT_RIGHT)
                        image = image.rotate(180)
                    elif orientation!= 0 and exif[orientation] == 7:
                        image = image.transpose(Image.FLIP_LEFT_RIGHT)
                        image = image.rotate(90)
                    return image
                except Exception as e:
                    return image

            size = 128, 128
            thumb = IMAGE.open(self.image)
            thumb.thumbnail(size)
            infile = self.image.file.name
            im_type = thumb.format 
            thumb_io = BytesIO()
            thumb = rotate_image(thumb)
            thumb.save(thumb_io, im_type)

            thumb_file = InMemoryUploadedFile(thumb_io, None, infile, 'image/'+im_type, thumb_io.getbuffer().nbytes, None)
            self.thumbnail = thumb_file

            size2 = 512, 512
            thumb2 = IMAGE.open(self.image)
            thumb2.thumbnail(size2)
            thumb_io2 = BytesIO()
            thumb2 = rotate_image(thumb2)
            thumb2.save(thumb_io2, format=im_type)

            thumb_file2 = InMemoryUploadedFile(thumb_io2, None, infile, 'image/'+im_type, thumb_io2.getbuffer().nbytes, None)

            self.mid_image = thumb_file2
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Save Image: %s at %s", e, str(exc_tb.tb_lineno))

        super(Image, self).save(*args, **kwargs)

class Bank(models.Model): 

    name = models.CharField(max_length=300, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    account_number = models.CharField(max_length=300, null=True, blank=True)
    ifsc_code = models.CharField(max_length=300, null=True, blank=True)
    swift_code = models.CharField(max_length=300, null=True, blank=True)
    branch_code = models.CharField(max_length=300, null=True, blank=True)

    class Meta:
        verbose_name = "Bank"
        verbose_name_plural = "Banks"

    def __str__(self):
        return str(self.name)

    def save(self, *args, **kwargs):
        super(Bank, self).save(*args, **kwargs)

class OmnyCommUser(User):

    image = models.ForeignKey(Image, null=True, blank=True, on_delete=models.CASCADE)
    contact_number = models.CharField(max_length=200, default="",blank=True,null=True)
    designation = models.CharField(max_length=200, default="Content Manager",blank=True,null=True)
    permission_list = models.TextField(default="[]")
    website_group = models.ForeignKey("WebsiteGroup", null=True, blank=True, on_delete=models.SET_NULL)

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.set_password(self.password)
        super(OmnyCommUser, self).save(*args, **kwargs)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "OmnyCommUser"
        verbose_name_plural = "OmnyCommUser"
        

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
    logo = models.ForeignKey(Image, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organization"

    def __str__(self):
        return str(self.name)


class SuperCategory(models.Model):

    name = models.CharField(max_length=256, blank=True, default='')
    description = models.CharField(max_length=256, blank=True, default='')
    uuid = models.CharField(max_length=256, blank=True, default='')
    image = models.ForeignKey(Image, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Super Category"
        verbose_name_plural = "Super Categories"

    def save(self, *args, **kwargs):
        
        if self.pk == None:
            self.uuid = str(uuid.uuid4())
        
        super(SuperCategory, self).save(*args, **kwargs)


class Category(models.Model):

    super_category = models.ForeignKey(SuperCategory, blank=True, default=None, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=256, blank=True, default='')
    description = models.CharField(max_length=256, blank=True, default='')
    uuid = models.CharField(max_length=256, blank=True, default='')
    property_data = models.TextField(default="[]", blank=True)
    image = models.ForeignKey(Image, null=True, blank=True, on_delete=models.SET_NULL)
    mobile_app_image = models.ForeignKey(Image, related_name="mobile_app_image", null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        
        if self.pk == None:
            self.uuid = str(uuid.uuid4())
        
        super(Category, self).save(*args, **kwargs)


class SubCategory(models.Model):

    category = models.ForeignKey(Category, related_name="sub_categories", blank=True, default='', on_delete=models.CASCADE)
    name = models.CharField(max_length=256, blank=True, default='')
    description = models.CharField(max_length=256, blank=True, default='')
    uuid = models.CharField(max_length=256, blank=True, default='')
    property_data = models.TextField(default="[]", blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Sub Category"
        verbose_name_plural = "Sub Categories"

    def save(self, *args, **kwargs):
        
        if self.pk == None:
            self.uuid = str(uuid.uuid4())
        
        super(SubCategory, self).save(*args, **kwargs)


class Channel(models.Model):
    
    name = models.CharField(unique=True,max_length=200)
    channel_charges = models.TextField(blank=True,default="[]")
        
    class Meta:
        verbose_name = "Channel"
        verbose_name_plural = "Channels"

    def __str__(self):
        return str(self.name)


class Brand(models.Model):

    name = models.CharField(max_length=100)
    logo = models.ForeignKey(Image, null=True, blank=True, on_delete=models.SET_NULL)
    organization = models.ForeignKey(Organization, null=True, blank=True)
 
    class Meta:
        verbose_name = "Brand"
        verbose_name_plural = "Brands"

    def __str__(self):
        return str(self.name)


class WebsiteGroup(models.Model):

    link = models.CharField(max_length=100, default="")
    name = models.CharField(max_length=100, unique=True)
    brands = models.ManyToManyField(Brand, blank=True)
    categories = models.ManyToManyField(Category, blank=True)
    super_categories = models.ManyToManyField(SuperCategory, blank=True)

    contact_info = models.CharField(max_length=100,blank=True, default='')
    address = models.TextField(blank=True, default='')
    email_info = models.CharField(max_length=100,blank=True, default='')
    logo = models.ForeignKey(Image, null=True, blank=True, on_delete=models.SET_NULL)
    footer_logo = models.ForeignKey(Image, related_name="footer_logo", null=True, blank=True, on_delete=models.SET_NULL)
    primary_color = models.CharField(max_length=100,default = "#000000")
    secondary_color = models.CharField(max_length=100,default = "#FFFFFF")
    navbar_text_color = models.CharField(max_length=100,default = "#FFFFFF")

    facebook_link = models.CharField(max_length=100,blank=True, default='')
    twitter_link = models.CharField(max_length=100,blank=True, default='')
    instagram_link = models.CharField(max_length=100,blank=True, default='')
    youtube_link = models.CharField(max_length=100,blank=True, default='')
    linkedin_link = models.CharField(max_length=100,blank=True, default='')
    crunchbase_link = models.CharField(max_length=100,blank=True, default='')

    conf = models.TextField(default="{}")

    payment_credentials = models.TextField(default="{}")

    class Meta:
        verbose_name = "WebsiteGroup"
        verbose_name_plural = "WebsiteGroup"

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


class BaseProductManager(models.Manager):

    def get_queryset(self):
        return super(BaseProductManager, self).get_queryset().exclude(is_deleted=True)


class BaseProductRecoveryManager(models.Manager):

    def get_queryset(self):
        return super(BaseProductRecoveryManager, self).get_queryset()


class BaseProduct(models.Model):

    base_product_name = models.CharField(max_length=300)
    created_date = models.DateTimeField()
    modified_date = models.DateTimeField()
    seller_sku = models.CharField(max_length=200, unique=True)
    category = models.ForeignKey(Category, null=True, blank=True, default=None, on_delete=models.SET_NULL)
    sub_category = models.ForeignKey(SubCategory, null=True, blank=True, default=None, on_delete=models.SET_NULL)
    brand = models.ForeignKey(Brand, null=True, blank=True, on_delete=models.SET_NULL)
    manufacturer = models.CharField(max_length=200, default="")
    manufacturer_part_number = models.CharField(max_length=200, default="")
    unedited_images = models.ManyToManyField(Image, related_name="unedited_images", blank=True)

    dimensions = models.TextField(blank=True, default=base_dimensions_json)
    history = AuditlogHistoryField()

    is_deleted = models.BooleanField(default=False)

    objects = BaseProductManager()
    recovery = BaseProductRecoveryManager()

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

auditlog.register(BaseProduct, exclude_fields=['modified_date' , 'created_date' , 'pk'])
auditlog.register(BaseProduct.unedited_images.through)


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


class ProductManager(models.Manager):

    def get_queryset(self):
        return super(ProductManager, self).get_queryset().exclude(is_deleted=True)


class ProductRecoveryManager(models.Manager):

    def get_queryset(self):
        return super(ProductRecoveryManager, self).get_queryset()


class Product(models.Model):

    #MISC
    base_product = models.ForeignKey(BaseProduct,null=True,blank=True,on_delete=models.SET_NULL)
    product_name = models.CharField(max_length=300,null=True)
    product_id = models.CharField(max_length=200,null=True)
    product_id_type = models.ForeignKey(ProductIDType,null=True,blank=True,on_delete=models.SET_NULL)
    product_description = models.TextField(blank=True)
    created_date = models.DateTimeField()
    modified_date = models.DateTimeField()
   

    is_bundle_product = models.BooleanField(default=False) 
    status = models.CharField(default="Pending", max_length=100)
    verified = models.BooleanField(default=False)
    partially_verified = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)
    uuid = models.CharField(null=True,max_length=200)

    #PFL
    pfl_product_name = models.CharField(max_length=300, default="")
    pfl_product_features = models.TextField(default="[]")

    product_name_sap = models.CharField(max_length=300, default="")
    color_map = models.CharField(max_length=100, default="")
    color = models.CharField(max_length=100, default="")
    material_type = models.ForeignKey(MaterialType,null=True,blank=True,on_delete=models.SET_NULL)
    standard_price = models.FloatField(null=True, blank=True)
    weight = models.FloatField(default=0.0)
    
    currency = models.CharField(max_length=100, default="")
    quantity = models.IntegerField(null=True, blank=True)

    pfl_images = models.ManyToManyField(Image, related_name="pfl_images", blank=True)
    white_background_images = models.ManyToManyField(Image, related_name="white_background_images", blank=True)
    lifestyle_images = models.ManyToManyField(Image, related_name="lifestyle_images", blank=True)
    certificate_images = models.ManyToManyField(Image, related_name="certificate_images", blank=True)
    giftbox_images = models.ManyToManyField(Image, related_name="giftbox_images", blank=True)
    diecut_images = models.ManyToManyField(Image, related_name="diecut_images", blank=True)
    aplus_content_images = models.ManyToManyField(Image, related_name="aplus_content_images", blank=True)
    ads_images = models.ManyToManyField(Image, related_name="ads_images", blank=True)
    pfl_generated_images = models.ManyToManyField(Image , related_name="pfl_generated_images" , blank = True)
    transparent_images = models.ManyToManyField(Image , related_name="transparent_images" , blank = True)
    best_images = models.ManyToManyField(Image , through='ProductImage', related_name="best_images" , blank = True)


    # Other info
    barcode = models.ForeignKey(Image, null=True, blank=True, on_delete=models.SET_NULL)
    barcode_string = models.CharField(max_length=100, default="")
    outdoor_price = models.FloatField(null=True, blank=True)

    channel_product = models.ForeignKey(ChannelProduct, null=True, blank=True, on_delete=models.SET_NULL)
    factory_notes = models.TextField(null=True,blank=True)
    history = AuditlogHistoryField()

    no_of_images_for_filter = models.IntegerField(default=0)
    dynamic_form_attributes = models.TextField(default="{}")

    min_price = models.FloatField(default=0)
    max_price = models.FloatField(default=0)

    warranty = models.CharField(max_length=100, default="One Year")

    faqs = models.TextField(default="[]")
    how_to_use = models.TextField(default="[]")

    is_deleted = models.BooleanField(default=False)

    objects = ProductManager()
    recovery = ProductRecoveryManager()

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return str(self.product_name)

    def get_non_html_description(self):
        non_html_description = BeautifulSoup(self.product_description).text
        return non_html_description

    def get_dimensions(self):
        dimensions = json.loads(self.base_product.dimensions)
        dimensions_string = "NA"
        try:
            dimensions_string = dimensions["product_dimension_l"]+" "+dimensions["product_dimension_l_metric"]+" x "
            dimensions_string += dimensions["product_dimension_b"]+" "+dimensions["product_dimension_b_metric"]+" x "
            dimensions_string += dimensions["product_dimension_h"]+" "+dimensions["product_dimension_h_metric"]
            if dimensions["product_dimension_l"]=="" or dimensions["product_dimension_b"]=="" or dimensions["product_dimension_h"]=="":
                dimensions_string = "NA"
        except Exception as e:
            pass
        return dimensions_string

    def get_best_images(self):
        image_ids = ProductImage.objects.filter(product=self).order_by('number').values_list('image', flat=True).distinct()
        image_objs = Image.objects.filter(id__in=image_ids)
        return image_objs

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

        channel_product_obj = self.channel_product
        try:
            noon_product_json_temp = json.loads(channel_product_obj.noon_product_json)
            amazon_uk_product_json_temp = json.loads(channel_product_obj.amazon_uk_product_json)
            amazon_uae_product_json_temp = json.loads(channel_product_obj.amazon_uae_product_json)
            ebay_product_json_temp = json.loads(channel_product_obj.ebay_product_json)

            if noon_product_json_temp["product_name"]=="":
                noon_product_json_temp["product_name"] = str(self.product_name.decode("utf-8"))
            if noon_product_json_temp["product_description"]=="":
                noon_product_json_temp["product_description"] = "" if self.product_description==None else str(self.product_description.decode("utf-8"))
            if noon_product_json_temp["category"]=="":
                noon_product_json_temp["category"] = "" if self.base_product.category==None else str(self.base_product.category)
            if noon_product_json_temp["sub_category"]=="":
                noon_product_json_temp["sub_category"] = "" if self.base_product.sub_category==None else str(self.base_product.sub_category)

            if amazon_uk_product_json_temp["product_name"]=="":
                amazon_uk_product_json_temp["product_name"] = str(self.product_name.decode("utf-8"))
            if amazon_uk_product_json_temp["product_description"]=="":
                amazon_uk_product_json_temp["product_description"] = "" if self.product_description==None else str(self.product_description.decode("utf-8"))
            if amazon_uk_product_json_temp["category"]=="":
                amazon_uk_product_json_temp["category"] = "" if self.base_product.category==None else str(self.base_product.category)
            if amazon_uk_product_json_temp["sub_category"]=="":
                amazon_uk_product_json_temp["sub_category"] = "" if self.base_product.sub_category==None else str(self.base_product.sub_category)

            if amazon_uae_product_json_temp["product_name"]=="":
                amazon_uae_product_json_temp["product_name"] = str(self.product_name.decode("utf-8"))
            if amazon_uae_product_json_temp["product_description"]=="":
                amazon_uae_product_json_temp["product_description"] = "" if self.product_description==None else str(self.product_description.decode("utf-8"))
            if amazon_uae_product_json_temp["category"]=="":
                amazon_uae_product_json_temp["category"] = "" if self.base_product.category==None else str(self.base_product.category)
            if amazon_uae_product_json_temp["sub_category"]=="":
                amazon_uae_product_json_temp["sub_category"] = "" if self.base_product.sub_category==None else str(self.base_product.sub_category)

            if ebay_product_json_temp["product_name"]=="":
                ebay_product_json_temp["product_name"] = str(self.product_name.decode("utf-8"))
            if ebay_product_json_temp["product_description"]=="":
                ebay_product_json_temp["product_description"] = "" if self.product_description==None else str(self.product_description.decode("utf-8"))
            if ebay_product_json_temp["category"]=="":
                ebay_product_json_temp["category"] = "" if self.base_product.category==None else str(self.base_product.category)
            if ebay_product_json_temp["sub_category"]=="":
                ebay_product_json_temp["sub_category"] = "" if self.base_product.sub_category==None else str(self.base_product.sub_category)

            channel_product_obj.noon_product_json = json.dumps(noon_product_json_temp)
            channel_product_obj.amazon_uk_product_json = json.dumps(amazon_uk_product_json_temp)
            channel_product_obj.amazon_uae_product_json = json.dumps(amazon_uae_product_json_temp)
            channel_product_obj.ebay_product_json = json.dumps(ebay_product_json_temp)
            channel_product_obj.save()
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Channel Product pulling default value: %s at %s", e, str(exc_tb.tb_lineno))

        if self.product_id != None and self.product_id != "":
            if self.product_id_type!=None and self.product_id_type.name=="ARTICLE":
                pass
            else:
                if len(self.product_id)==10:
                    self.product_id_type = ProductIDType.objects.get(name="ASIN")
                elif len(self.product_id)==12:
                    self.product_id_type = ProductIDType.objects.get(name="UPC")
                elif len(self.product_id)==13:
                    self.product_id_type = ProductIDType.objects.get(name="EAN")
                else:
                    self.product_id_type = None
        
        super(Product, self).save(*args, **kwargs)

auditlog.register(Product, exclude_fields=['modified_date' , 
                                           'created_date' , 
                                           'uuid', 
                                           'base_product',
                                           'no_of_images_for_filter'])

auditlog.register(Product.pfl_images.through)
auditlog.register(Product.white_background_images.through)
auditlog.register(Product.lifestyle_images.through)
auditlog.register(Product.certificate_images.through)
auditlog.register(Product.giftbox_images.through)
auditlog.register(Product.diecut_images.through)
auditlog.register(Product.aplus_content_images.through)
auditlog.register(Product.ads_images.through)
auditlog.register(Product.pfl_generated_images.through)
auditlog.register(Product.transparent_images.through)


class ProductImage(models.Model):

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    image = models.ForeignKey(Image, on_delete=models.CASCADE)
    number = models.IntegerField(default=1)

    class Meta:
        ordering = ('number',)


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

auditlog.register(MainImages, exclude_fields = ['is_sourced','pk'])
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
    
auditlog.register(SubImages, exclude_fields=['is_sourced' , 'pk'])
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
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    created_date = models.DateTimeField(null=True, blank=True)

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Flyer"
        verbose_name_plural = "Flyers"

    def __str__(self):
        return str(self.name)

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.created_date = timezone.now()
        super(Flyer, self).save(*args, **kwargs)

auditlog.register(Flyer, exclude_fields=['template_data','background_images_bucket' , 'created_date', 'pk'])
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


auditlog.register(ExportList, exclude_fields=['created_date' , 'pk'])
auditlog.register(ExportList.products.through)

class Report(models.Model):

    feed_submission_id = models.CharField(max_length=200)
    operation_type = models.CharField(max_length=200)
    status = models.CharField(default="In Progress",max_length=200)
    is_read = models.BooleanField(default=False)
    products = models.ManyToManyField(Product, blank=True)
    created_date = models.DateTimeField()
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    channel = models.ForeignKey(Channel,null=True,blank=True, on_delete=models.SET_NULL)

    history = AuditlogHistoryField()
    
    class Meta:
        verbose_name = "Report"
        verbose_name_plural = "Reports"

    def __str__(self):
        return str(self.feed_submission_id)

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.created_date = timezone.now()
        super(Report, self).save(*args, **kwargs)


auditlog.register(Report, exclude_fields=['pk','is_read '])
auditlog.register(Report.products.through)


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
    mws_functions = models.TextField(default="{}")
    noon_functions = models.TextField(default="{}")
    price = models.TextField(default="{}")
    stock = models.TextField(default="{}")
    oc_reports = models.TextField(default="[]")
    verify_product = models.BooleanField(default=False)
    delete_product = models.BooleanField(default=False)
    page_list = models.TextField(default="[]")
    location_groups = models.ManyToManyField(LocationGroup, blank=True)
    organization = models.ForeignKey(Organization,blank=True,null=True,on_delete=models.SET_NULL)

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

class AmazonUKCategory(models.Model):

    category_id = models.CharField(default="", max_length=100)
    name = models.CharField(default="", max_length=200)

    class Meta:
        verbose_name = "AmazonUKCategory"
        verbose_name_plural = "AmazonUKCategory"

    def __str__(self):
        return str(self.name)

class AmazonUAECategory(models.Model):

    category_id = models.CharField(default="", max_length=100)
    name = models.CharField(default="", max_length=200)

    class Meta:
        verbose_name = "AmazonUAECategory"
        verbose_name_plural = "AmazonUAECategory"

    def __str__(self):
        return str(self.name)

class NoonCategory(models.Model):

    category_id = models.CharField(default="", max_length=100)
    name = models.CharField(default="", max_length=200)

    class Meta:
        verbose_name = "NoonCategory"
        verbose_name_plural = "NoonCategory"

    def __str__(self):
        return str(self.name)

class BackgroundImage(models.Model):

    image = models.ForeignKey(Image, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Background Image"
        verbose_name_plural = "Background Images"

    def __str__(self):
        return str(self.pk)


class RequestHelp(models.Model):

    uuid = models.CharField(default="", max_length=200, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField(default="")
    created_date = models.DateTimeField()
    page = models.CharField(default="NA", max_length=200)

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.created_date = timezone.now()
            self.uuid = str(uuid.uuid4())
        super(RequestHelp, self).save(*args, **kwargs)

@receiver(post_save, sender=Product, dispatch_uid="create_pfl")
def update_stock(sender, instance, **kwargs):
    if PFL.objects.filter(product=instance).exists()==False:
        PFL.objects.create(product=instance, name=str(instance.product_name_sap)+"_PFL")


##############################################################################################

#  Sourcing Module Models

##############################################################################################


# class SourcingProduct(models.Model):
    
#     price = models.FloatField(default=0, null=True, blank=True)
#     currency = models.CharField(max_length=300, null=True, blank=True)
#     other_info = models.TextField(null=True, blank=True)
#     minimum_order_qty = models.IntegerField(null=True, blank=True)
#     order_qty = models.IntegerField(null=True, blank=True)
#     qty_metric = models.CharField(max_length=300, null=True, blank=True)
#     inner_box_qty = models.IntegerField(null=True, blank=True)
#     is_pr_ready = models.BooleanField(default=False)
#     go_live = models.BooleanField(default=False)
#     size = models.CharField(max_length=300, null=True, blank=True)
#     weight = models.CharField(max_length=300, null=True, blank=True)
#     weight_metric = models.CharField(max_length=300, null=True, blank=True)
#     design = models.CharField(max_length=300, null=True, blank=True)
#     pkg_inner = models.CharField(max_length=300, null=True, blank=True)
#     pkg_m_ctn = models.CharField(max_length=300, null=True, blank=True)
#     p_ctn_cbm = models.CharField(max_length=300, null=True, blank=True)
#     ttl_ctn = models.CharField(max_length=300, null=True, blank=True)
#     ttl_cbm = models.CharField(max_length=300, null=True, blank=True)
#     ship_lot_number = models.CharField(max_length=300, null=True, blank=True)
#     giftbox_die_cut = models.CharField(max_length=300, null=True, blank=True)
#     spare_part_name = models.CharField(max_length=300, null=True, blank=True)
#     spare_part_qty = models.IntegerField(null=True)
#     delivery_days = models.IntegerField(default=0, null=True)
#     created_by = models.ForeignKey(OmnyCommUser,blank=True)
    
#     product = models.ForeignKey(Product,blank=True,null=True, on_delete=models.SET_NULL)
    
#     class Meta:
#         verbose_name = "SourcingProduct"
#         verbose_name_plural = "SourcingProducts"

#     def __str__(self):
#         return str(self.product)


class ProformaInvoiceBundle(models.Model):
    
    proforma_zip = models.FileField(blank=True, null=True, default=None)
    created_date = models.DateTimeField(null=True, blank=True)
    uuid = models.CharField(max_length=200, unique=True)

    class Meta:
        verbose_name = "Proforma Invoice Bundle"
        verbose_name_plural = "Proforma Invoice Bundle"

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.created_date = timezone.now()
            self.uuid = str(uuid.uuid4())
        super(ProformaInvoiceBundle, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.created_date.strftime("%d %b, %Y, %H:%M"))


class ProformaInvoice(models.Model): 
    
    proforma_pdf = models.FileField(blank=True, null=True, default=None)
    payment_terms = models.CharField(max_length=250, null=True, blank=True)
    advance = models.CharField(max_length=250, default="", blank=True)
    inco_terms = models.CharField(max_length=250, default="", blank=True)
    ttl_cntrs = models.CharField(max_length=250, default="", blank=True)
    delivery_terms = models.CharField(max_length=250, default="", blank=True)
    # factory = models.ForeignKey(Factory, null=True, blank=True, on_delete=models.SET_NULL)
    proforma_invoice_bundle = models.ForeignKey(ProformaInvoiceBundle, default=None, blank=True, on_delete=models.CASCADE)
    invoice_number = models.CharField(max_length=250, default="", blank=True)
    invoice_date = models.DateTimeField(null=True, blank=True)
    discharge_port = models.CharField(default="", max_length=100)
    vessel_details = models.CharField(default="", max_length=100)
    vessel_final_destination = models.CharField(default="", max_length=100)
    ship_lot_number = models.CharField(default="", max_length=100)
    important_notes = models.TextField(default="")
    terms_and_condition = models.TextField(default="")
    uuid = models.CharField(max_length=200, unique=True)

    class Meta:
        verbose_name = "Proforma Invoice"
        verbose_name_plural = "Proforma Invoices"

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())
        super(ProformaInvoice, self).save(*args, **kwargs)


class UnitProformaInvoice(models.Model):
    
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1, blank=True)
    proforma_invoice = models.ForeignKey(ProformaInvoice, default=None, blank=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Unit Proforma Invoice"
        verbose_name_plural = "Unit Proforma Invoice"

    def __str__(self):
        return str(self.product)+" - "+str(self.quantity)

class DataPoint(models.Model):

    name = models.CharField(max_length=200, default="")
    variable = models.CharField(max_length=200, default="", unique=True)

    def __str__(self):
        return self.name


class ExportTemplate(models.Model):

    name = models.CharField(max_length=200, default="")
    data_points = models.ManyToManyField(DataPoint, blank=True)
    user = models.ForeignKey(OmnyCommUser, blank=True, on_delete=models.CASCADE)
    uuid = models.CharField(max_length=200, default="")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        
        if self.pk == None:
            self.uuid = str(uuid.uuid4())
        
        super(ExportTemplate, self).save(*args, **kwargs)


class TagBucket(models.Model):

    image = models.ForeignKey(Image, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Tag Image"
        verbose_name_plural = "Tag Images"

    def __str__(self):
        return str(self.image.image.url)


class PriceTagBucket(models.Model):

    image = models.ForeignKey(Image, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Price Tag Image"
        verbose_name_plural = "Price Tag Images"

    def __str__(self):
        return str(self.image.image.url)


class OCReport(models.Model):

    name = models.CharField(max_length=200, default="")
    created_date = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(OmnyCommUser, blank=True)
    is_processed = models.BooleanField(default=False)
    completion_date = models.DateTimeField(null=True, blank=True)
    note = models.TextField(default="")
    filename = models.CharField(max_length=200, default="")
    uuid = models.CharField(max_length=200, default="")
    organization = models.ForeignKey(Organization,blank=True,null=True,on_delete=models.SET_NULL)

    class Meta:
        verbose_name = "OC Report"
        verbose_name_plural = "OC Report"

    def __str__(self):
        return str(self.name)

    def save(self, *args, **kwargs):
        
        if self.pk == None:
            self.created_date = timezone.now()
            self.uuid = str(uuid.uuid4())
        
        super(OCReport, self).save(*args, **kwargs)

item_price_json = {

    "Principal" : "",
    "Shipping" : "",
    "Tax" : "",
    "ShippingTax" : "",
    "CODFee" : "",
}

item_price_json = json.dumps(item_price_json)

class AmazonOrder(models.Model):

    amazon_order_id = models.CharField(max_length=200)
    order_date = models.DateTimeField(blank=True)
        
    payment_method = models.CharField(max_length=200, default="")
    order_status = models.CharField(max_length=200, default="")
    amount = models.FloatField(blank=True,null=True)
    currency = models.CharField(max_length=200, default="")

    shipment_service = models.CharField(max_length=200, default="")
    latest_ship_date = models.DateTimeField(blank=True,null=True)
    earliest_ship_date = models.DateTimeField(blank=True,null=True)
    earliest_delivery_date = models.DateTimeField(blank=True,null=True)
    shipped_items = models.IntegerField(blank=True,null=True)
    unshipped_items = models.IntegerField(blank=True,null=True)
    total_items = models.IntegerField(blank=True,null=True)

    buyer_name = models.CharField(max_length=200, default="")
    address = models.TextField(default="")
    city = models.CharField(max_length=200, default="")
    country_code = models.CharField(max_length=200,blank=True)

    channel = models.ForeignKey(Channel, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Amazon Order"
        verbose_name_plural = "Amazon Orders"

    def __str__(self):
        return str(self.amazon_order_id)


class AmazonItem(models.Model):

    amazon_order = models.ForeignKey(AmazonOrder, on_delete=models.CASCADE)
    amazon_order_item_code = models.CharField(max_length=200, default="")
    sku = models.CharField(max_length=200, default="")
    name = models.TextField(default="")
    quantity = models.IntegerField(blank=True)
    item_price_json = models.TextField(default=item_price_json)
    amount = models.FloatField(blank=True,null=True)
    
    class Meta:
        verbose_name = "Amazon Item"
        verbose_name_plural = "Amazon Items"

    def __str__(self):
        return str(self.amazon_order_item_code)

class Factory(models.Model):

    name = models.CharField(max_length=200, default="")
    code = models.CharField(max_length=200, default="")
    uuid = models.CharField(max_length=200, default="",blank=True)
    address = models.TextField(default="")
    image = models.ForeignKey(Image,on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Factory"
        verbose_name_plural = "Factories"

    def __str__(self):
        return str(self.name)

    def save(self, *args, **kwargs):
        
        if self.pk == None:
            self.uuid = str(uuid.uuid4())
        
        super(Factory, self).save(*args, **kwargs)


class FactoryUser(User):

    image = models.ForeignKey(Image,on_delete=models.SET_NULL, null=True, blank=True)
    contact_number = models.CharField(max_length=200, default="")
    designation = models.CharField(max_length=200, default="", null=True, blank=True)
    permission_list = models.TextField(default="[]")
    factory = models.ForeignKey(Factory, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Factory User"
        verbose_name_plural = "Factory Users"

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.set_password(self.password)
        super(FactoryUser, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.username)


class FactoryProduct(models.Model):

    uuid = models.CharField(max_length=200, default="", blank=True)
    product_name = models.CharField(max_length=200, default="")
    product_description = models.TextField(default="", blank=True, null=True)
    factory = models.ForeignKey(Factory, on_delete=models.SET_NULL, null=True, blank=True)
    manufacturer_part_number = models.CharField(max_length=200, default="")
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    manufacturer = models.CharField(max_length=200, default="")
    category = models.ForeignKey(Category,on_delete=models.SET_NULL, null=True, blank=True)
    sub_category = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, blank=True)
    images = models.ManyToManyField(Image, blank=True)
    color_map = models.CharField(max_length=100, default="")
    color = models.CharField(max_length=100, default="")
    material_type = models.ForeignKey(MaterialType, null=True, blank=True, on_delete=models.SET_NULL)
    moq = models.CharField(max_length=200, default="")
    factory_notes = models.TextField(null=True, blank=True, default="")
    features = models.TextField(default="[]")
    dimensions = models.TextField(default=base_dimensions_json, blank=True)

    class Meta:
        verbose_name = "Factory Product"
        verbose_name_plural = "Factory Products"

    def __str__(self):
        return str(self.product_name)

    def save(self, *args, **kwargs):
        
        if self.pk == None:
            self.uuid = str(uuid.uuid4())
        
        super(FactoryProduct, self).save(*args, **kwargs)


class SapSuperCategory(models.Model):

    super_category = models.CharField(max_length=200,default="")

    class Meta:
        verbose_name = "SAP Super Category"
        verbose_name_plural = "SAP Super Categories"

    def __str__(self):
        return str(self.super_category)


class SapCategory(models.Model):

    category = models.CharField(max_length=200,default="")
    super_category = models.ForeignKey(SapSuperCategory,null=True,on_delete=models.SET_NULL)

    class Meta:
        verbose_name = "SAP Category"
        verbose_name_plural = "SAP Categories"

    def __str__(self):
        return str(self.category)

class SapSubCategory(models.Model):

    sub_category = models.CharField(max_length=200,default="")
    category = models.ForeignKey(SapCategory,null=True,on_delete=models.SET_NULL)

    class Meta:
        verbose_name = "SAP Sub Category"
        verbose_name_plural = "SAP Sub Categories"

    def __str__(self):
        return str(self.sub_category)

class CategoryMapping(models.Model):

    sap_sub_category = models.ForeignKey(SapSubCategory,null=True,on_delete=models.SET_NULL)
    atp_threshold = models.FloatField(default=100)
    holding_threshold = models.FloatField(default=5)
    recommended_browse_node = models.CharField(max_length=200,default="")

    class Meta:
        verbose_name = "Category Mapping"
        verbose_name_plural = "Category Mappings"

    def __str__(self):
        return str(self.recommended_browse_node)