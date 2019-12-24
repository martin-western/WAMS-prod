from django.db import models
from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


from PIL import Image as IMage
import StringIO
import logging
import sys
import json

logger = logging.getLogger(__name__)

####################################################

def compress(image_path):
    try:
        im = IMage.open(image_path)
        basewidth = 1024
        wpercent = (basewidth / float(im.size[0]))
        hsize = int((float(im.size[1]) * float(wpercent)))
        im = im.resize((basewidth, hsize), IMage.ANTIALIAS)
        im.save(image_path, optimize=True, quality=100)
    except Exception as e:
        print("Error", str(e))
###################################################


class ContentManager(User):

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
            thumb = IMage.open(self.image)
            thumb.thumbnail(size)
            infile = self.image.file.name
            im_type = thumb.format 
            thumb_io = StringIO.StringIO()
            thumb.save(thumb_io, format=im_type)

            thumb_file = InMemoryUploadedFile(thumb_io, None, infile, 'image/'+im_type, thumb_io.len, None)

            self.thumbnail = thumb_file




            size2 = 512, 512
            thumb2 = IMage.open(self.image)
            thumb2.thumbnail(size2)
            thumb_io2 = StringIO.StringIO()
            thumb2.save(thumb_io2, format=im_type)

            thumb_file2 = InMemoryUploadedFile(thumb_io2, None, infile, 'image/'+im_type, thumb_io2.len, None)

            self.mid_image = thumb_file2
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("save Image: %s at %s", e, str(exc_tb.tb_lineno))

        super(Image, self).save(*args, **kwargs)
        #compress("."+self.image.url)



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
        #compress("."+self.image.image.url)


class Organization(models.Model):

    name = models.CharField(unique=True, max_length=100)

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organization"

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


class Product(models.Model):

    #MISC
    created_date = models.DateTimeField()
    status = models.CharField(default="Pending", max_length=100)
    verified = models.BooleanField(default=False)

    #PFL
    pfl_product_name = models.CharField(max_length=250, default="")
    pfl_product_features = models.TextField(default="[]")

    #Vital
    product_name_sap = models.CharField(max_length=300, default="")
    product_name_amazon_uk = models.CharField(max_length=300, default="")
    product_name_amazon_uae = models.CharField(max_length=300, default="")
    product_name_ebay = models.CharField(max_length=300, default="")
    product_name_noon = models.CharField(max_length=300, default="")

    product_id = models.CharField(max_length=100, unique=True)
    product_id_type = models.CharField(max_length=100, default="")
    seller_sku = models.CharField(max_length=100, default="")
    category = models.CharField(max_length=300, default="")
    subtitle = models.CharField(max_length=300, default="")
    brand = models.ForeignKey(Brand, null=True, blank=True, on_delete=models.SET_NULL)
    manufacturer = models.CharField(max_length=200, default="")
    manufacturer_part_number = models.CharField(max_length=200, default="")
    condition_type = models.CharField(max_length=100, default="New")
    feed_product_type = models.CharField(max_length=100, default="")
    update_delete = models.CharField(max_length=100, default="Update")
    recommended_browse_nodes = models.CharField(max_length=100, default="")
    noon_product_type = models.CharField(default="", max_length=200)
    noon_product_subtype = models.CharField(default="", max_length=200)
    noon_model_number = models.CharField(default="", max_length=100)
    noon_model_name = models.CharField(default="", max_length=300)


    noon_msrp_ae = models.IntegerField(null=True, blank=True, default=None)
    noon_msrp_ae_unit = models.CharField(max_length=100, default="")


    #Information
    product_description_amazon_uk = models.TextField(default="")
    product_description_amazon_uae = models.TextField(default="")
    product_description_ebay = models.TextField(default="")
    product_description_noon = models.TextField(default="")

    product_attribute_list_amazon_uk = models.TextField(default="[]")
    product_attribute_list_amazon_uae = models.TextField(default="[]")
    product_attribute_list_ebay = models.TextField(default="[]")
    product_attribute_list_noon = models.TextField(default="[]")

    search_terms = models.CharField(max_length=300, default="")
    color_map = models.CharField(max_length=100, default="")
    color = models.CharField(max_length=100, default="")
    enclosure_material = models.CharField(max_length=100, default="")
    cover_material_type = models.CharField(max_length=100, default="")
    special_features = models.TextField(default="[]")


    #Dimensions
    package_length = models.FloatField(null=True, blank=True)
    package_length_metric = models.CharField(max_length=100, default="")
    package_width = models.FloatField(null=True, blank=True)
    package_width_metric = models.CharField(max_length=100, default="")
    package_height = models.FloatField(null=True, blank=True)
    package_height_metric = models.CharField(max_length=100, default="")
    package_weight = models.FloatField(null=True, blank=True)
    package_weight_metric = models.CharField(max_length=100, default="")
    shipping_weight = models.FloatField(null=True, blank=True)
    shipping_weight_metric = models.CharField(max_length=100, default="")
    item_display_weight = models.FloatField(null=True, blank=True)
    item_display_weight_metric = models.CharField(max_length=100, default="")
    item_display_volume = models.FloatField(null=True, blank=True)
    item_display_volume_metric = models.CharField(max_length=100, default="")
    item_display_length = models.FloatField(null=True, blank=True)
    item_display_length_metric = models.CharField(max_length=100, default="")
    item_weight = models.FloatField(null=True, blank=True)
    item_weight_metric = models.CharField(max_length=100, default="")
    item_length = models.FloatField(null=True, blank=True)
    item_length_metric = models.CharField(max_length=100, default="")
    item_width = models.FloatField(null=True, blank=True) 
    item_width_metric = models.CharField(max_length=100, default="")
    item_height = models.FloatField(null=True, blank=True)
    item_height_metric = models.CharField(max_length=100, default="")
    item_display_width = models.FloatField(null=True, blank=True)
    item_display_width_metric = models.CharField(max_length=100, default="")
    item_display_height = models.FloatField(null=True, blank=True)
    item_display_height_metric = models.CharField(max_length=100, default="")
    item_count = models.FloatField(null=True, blank=True)
    item_count_metric = models.CharField(max_length=100, default="")


    #Attributes
    item_condition_note = models.TextField(default="")
    max_order_quantity = models.IntegerField(null=True, blank=True)
    number_of_items = models.IntegerField(null=True, blank=True)
    wattage = models.FloatField(null=True, blank=True)
    wattage_metric = models.CharField(max_length=100, default="")
    material_type = models.CharField(max_length=100, default="")


    #Variation
    parentage = models.CharField(max_length=100, default="")
    parent_sku = models.CharField(max_length=100, default="")
    relationship_type = models.CharField(max_length=100, default="")
    variation_theme = models.CharField(max_length=100, default="")


    #Offer
    standard_price = models.FloatField(null=True, blank=True)
    quantity = models.IntegerField(null=True, blank=True)
    sale_price = models.FloatField(null=True, blank=True)
    sale_from = models.DateField(null=True, blank=True)
    sale_end = models.DateField(null=True, blank=True)


    #Graphics
    main_images = models.ManyToManyField(ImageBucket, related_name="main_images", blank=True)
    sub_images = models.ManyToManyField(ImageBucket, related_name="sub_images", blank=True)
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

    # Other info
    barcode = models.ForeignKey(Image, null=True, blank=True, on_delete=models.SET_NULL)
    barcode_string = models.CharField(max_length=100, default="")
    outdoor_price = models.FloatField(null=True, blank=True)

    factory_notes = models.TextField(default="[]")
    
    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return str(self.product_id)


    def save(self, *args, **kwargs):
        if self.pk == None:
            self.created_date = timezone.now()
        super(Product, self).save(*args, **kwargs)




class Flyer(models.Model):

    name = models.CharField(default="SampleFlyer", max_length=300)
    product_bucket = models.ManyToManyField(Product, blank=True)
    template_data = models.TextField(null=True, blank=True)
    """
    {
        "row": 4,
        "column": 3,
        "data": [
            [{"image_pk":2, "product_title": "Geepas Juicer", "price":100}, {}, {}],
            [{}, {}, {}]
        ]
    }
    """
    external_images_bucket = models.ManyToManyField(Image, blank=True)
    flyer_image = models.ForeignKey(Image, null=True, blank=True, related_name="flyer_images", on_delete=models.SET_NULL)
    background_images_bucket = models.ManyToManyField(Image, blank=True, related_name="background_images_bucket")
    brand = models.ForeignKey(Brand, null=True, blank=True, on_delete=models.SET_NULL)
    mode = models.CharField(max_length=100, default="A4 Portrait")

    class Meta:
        verbose_name = "Flyer"
        verbose_name_plural = "Flyers"

    def __str__(self):
        return str(self.name)


class PFL(models.Model):

    name = models.CharField(default="SamplePFL", max_length=300)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL)
    product_image = models.ForeignKey(Image, null=True, blank=True, related_name="product_images", on_delete=models.SET_NULL)
   
    external_images_bucket = models.ManyToManyField(Image, blank=True)

    class Meta:
        verbose_name = "PFL"
        verbose_name_plural = "PFL"

    def __str__(self):
        return str(self.name)


class ExportList(models.Model):

    title = models.CharField(default="SampleExportList", max_length=300)
    products = models.ManyToManyField(Product, blank=True)
    created_date = models.DateTimeField()
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = "ExportList"
        verbose_name_plural = "ExportLists"

    def __str__(self):
        return str(self.title)

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.created_date = timezone.now()
        super(ExportList, self).save(*args, **kwargs)



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

    class Meta:
        verbose_name = "CustomPermission"
        verbose_name_plural = "CustomPermissions"

    def __str__(self):
        return str(self.user)


class EbayCategory(models.Model):

    category_id = models.CharField(default="", max_length=100)
    name = models.CharField(default="", max_length=300)

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
