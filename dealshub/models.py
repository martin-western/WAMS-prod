from django.db import models
from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from django.db.models.signals import pre_delete

from PIL import Image as IMAGE
import logging
import sys
import json
import uuid


from WAMSApp.models import Product, Image, WebsiteGroup, Category

logger = logging.getLogger(__name__)

address_lines = ["", "", "", ""]

class Promotion(models.Model):
    
    uuid = models.CharField(max_length=200, unique=True)
    promotion_tag = models.CharField(max_length=100, default="")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    def __str__(self):
        return str(self.uuid)

    def save(self, *args, **kwargs):

        if self.uuid == None or self.uuid=="":
            self.uuid = str(uuid.uuid4())

        super(Promotion, self).save(*args, **kwargs)

class DealsHubProduct(models.Model):
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=True)
    was_price = models.FloatField(default=0)
    now_price = models.FloatField(default=0)
    promotional_price = models.FloatField(default=0)
    stock = models.IntegerField(default=0)
    is_cod_allowed = models.BooleanField(default=True)
    properties = models.TextField(null=True, blank=True, default="{}")
    promotion = models.ForeignKey(Promotion,null=True,blank=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        verbose_name = "DealsHub Product"
        verbose_name_plural = "DealsHub Products"

    def __str__(self):
        return str(self.product)


class Section(models.Model):

    uuid = models.CharField(max_length=200, unique=True)
    website_group = models.ForeignKey(WebsiteGroup, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=300, default="")
    is_published = models.BooleanField(default=False)
    listing_type = models.CharField(default="Carousel", max_length=200)
    products = models.ManyToManyField(Product, blank=True)
    created_date = models.DateTimeField()
    modified_date = models.DateTimeField()
    promotion = models.ForeignKey(Promotion,null=True,blank=True)
    created_by = models.ForeignKey(User, related_name="created_by", null=True, blank=True, on_delete=models.SET_NULL)
    modified_by = models.ForeignKey(User, related_name="modified_by", null=True, blank=True, on_delete=models.SET_NULL)
    order_index = models.IntegerField(default=4)

    class Meta:
        verbose_name = "Section"
        verbose_name_plural = "Sections"

    def save(self, *args, **kwargs):
        
        if self.pk == None:
            self.created_date = timezone.now()
            self.modified_date = timezone.now()
        else:
            self.modified_date = timezone.now()

        if self.uuid == None or self.uuid == "":
            self.uuid = str(uuid.uuid4())
        
        super(Section, self).save(*args, **kwargs)


class BannerType(models.Model):

    name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=100, default="")
    limit = models.IntegerField(default=1)
    website_group = models.ForeignKey(WebsiteGroup, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return str(self.name)


class Banner(models.Model):

    uuid = models.CharField(max_length=200, unique=True)
    name = models.CharField(max_length=100, default="")
    website_group = models.ForeignKey(WebsiteGroup, null=True, blank=True, on_delete=models.SET_NULL)
    is_published = models.BooleanField(default=False)
    created_date = models.DateTimeField()
    modified_date = models.DateTimeField()
    created_by = models.ForeignKey(User, related_name="banner_created_by", null=True, blank=True, on_delete=models.SET_NULL)
    modified_by = models.ForeignKey(User, related_name="banner_modified_by", null=True, blank=True, on_delete=models.SET_NULL)
    order_index = models.IntegerField(default=1)
    banner_type = models.ForeignKey(BannerType, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.uuid)

    def save(self, *args, **kwargs):
        
        if self.pk == None:
            self.created_date = timezone.now()
            self.modified_date = timezone.now()
        else:
            self.modified_date = timezone.now()

        if self.uuid == None or self.uuid == "":
            self.uuid = str(uuid.uuid4())
        
        super(Banner, self).save(*args, **kwargs)      


class UnitBannerImage(models.Model):

    uuid = models.CharField(max_length=200, unique=True)
    image = models.ForeignKey(Image, on_delete=models.SET_NULL, null=True)
    mobile_image = models.ForeignKey(Image, related_name="mobile_image", on_delete=models.SET_NULL, null=True)
    http_link = models.TextField(default="")
    banner = models.ForeignKey(Banner, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, blank=True)
    promotion = models.ForeignKey(Promotion,null=True,blank=True)

    def __str__(self):
        return str(self.uuid)

    def save(self, *args, **kwargs):

        if self.uuid == None or self.uuid=="":
            self.uuid = str(uuid.uuid4())
        
        super(UnitBannerImage, self).save(*args, **kwargs)


class ImageLink(models.Model):

    uuid = models.CharField(max_length=200, unique=True)
    image = models.ForeignKey(Image, on_delete=models.CASCADE, null=True)
    http_link = models.TextField(default="")

    def save(self, *args, **kwargs):
        
        if self.uuid == None or self.uuid=="":
            self.uuid = str(uuid.uuid4())
        
        super(ImageLink, self).save(*args, **kwargs)


class DealsHubHeading(models.Model):

    uuid = models.CharField(max_length=200, unique=True)
    website_group = models.ForeignKey(WebsiteGroup, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=200, default="")
    categories = models.ManyToManyField(Category, blank=True)
    image_links = models.ManyToManyField(ImageLink, blank=True)

    def __str__(self):
        return str(self.name)

    def save(self, *args, **kwargs):
        
        if self.uuid == None or self.uuid=="":
            self.uuid = str(uuid.uuid4())
        
        super(DealsHubHeading, self).save(*args, **kwargs)


class Address(models.Model):

    MR, MISS, MRS, MS, DR = ('Mr', 'Miss', 'Mrs', 'Ms', 'Dr')
    TITLE_CHOICES = (
        (MR, "Mr"),
        (MISS, "Miss"),
        (MRS, "Mrs"),
        (MS, "Ms"),
        (DR, "Dr"),
    )
    title = models.CharField(max_length=64, choices=TITLE_CHOICES, blank=True)

    first_name = models.CharField(max_length=255, default="", blank=True)
    last_name = models.CharField(max_length=255, default="", blank=True)

    address_lines = models.TextField(default=json.dumps(address_lines), blank=True)

    state = models.CharField(default="", max_length=255, blank=True)
    postcode = models.CharField(default="", max_length=64, blank=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    contact_number = models.CharField(max_length=100, default="", blank=True)

    date_created = models.DateTimeField(auto_now_add=True)

    is_shipping = models.BooleanField(default=True)
    is_billing = models.BooleanField(default=True)

    is_deleted = models.BooleanField(default=False)

    TAGS = (
        ("home", "home"),
        ("work", "work"),
        ("other", "other")
    )
    tag = models.CharField(max_length=64, choices=TAGS, default="home")

    uuid = models.CharField(max_length=200, default="")

    def get_address(self):
        address_str = self.title
        address_str += self.first_name + ' ' + self.last_name + ' '
        for line in json.loads(self.address):
            address_str += line + " "
        address_str += self.state + ' ' + self.postcode
        address_str += str(self.contact_number)
        return address_str

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())

        super(Address, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "Address"
        verbose_name_plural = "Addresses"


class Cart(models.Model):

    owner = models.ForeignKey('DealsHubUser', on_delete=models.CASCADE)
    uuid = models.CharField(max_length=200, default="")
    order = models.ForeignKey('Order', null=True, blank=True, on_delete=models.SET_NULL)

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())

        super(Cart, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"


class UnitCart(models.Model):

    cart = models.ForeignKey('Cart', on_delete=models.CASCADE)
    product = models.ForeignKey(DealsHubProduct, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    price = models.FloatField(default=None, null=True, blank=True)
    currency = models.CharField(max_length=100, default='AED')
    
    date_created = models.DateTimeField(auto_now_add=True)

    uuid = models.CharField(max_length=200, default="")

    ACTIVE, WISHLIST = ('active', 'wishlist')
    CART_TYPE = (
        (ACTIVE, "active"),
        (WISHLIST, "wishlist")
    )

    cart_type = models.CharField(max_length=100, choices=CART_TYPE, default="active")

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())

        super(UnitCart, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "Unit Cart"
        verbose_name_plural = "Unit Carts"


class Order(models.Model):
    bundleid = models.CharField(max_length=100, default="")
    owner = models.ForeignKey('DealsHubUser', on_delete=models.CASCADE)
    uuid = models.CharField(max_length=200, default="")
    date_created = models.DateTimeField(auto_now_add=True)
    shipping_address = models.ForeignKey(Address, null=True, blank=True, on_delete=models.CASCADE)
    payment_mode = models.CharField(default="COD", max_length=100)
    to_pay = models.FloatField(default=0)
    order_placed_date = models.DateTimeField(null=True, default=timezone.now)

    PENDING, PAID, FAILED = ('pending', 'paid', 'failed')
    PAYMENT_STATUS = (
        (PENDING, "pending"),
        (PAID, "paid"),
        (FAILED, "failed")
    )
    payment_status = models.CharField(max_length=100, choices=PAYMENT_STATUS, default="pending")
    payment_info = models.TextField(default="{}")
    merchant_reference = models.CharField(max_length=200, default="")


    NOT_PLACED_ORDER, PLACED_ORDER = ('notplacedorder', 'placedorder')
    ORDER_TYPE = (
        (NOT_PLACED_ORDER, "notplacedorder"),
        (PLACED_ORDER, "placedorder")
    )
    order_type = models.CharField(max_length=100, choices=ORDER_TYPE, default="notplacedorder")

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())
            self.bundleid = "wig"+str(uuid.uuid4())[:5]

        super(Order, self).save(*args, **kwargs)


class UnitOrder(models.Model):
    orderid = models.CharField(max_length=100, default="")
    CURRENT_STATUS = (
        ("ordered", "ordered"),
        ("shipped", "shipped"),
        ("intransit", "intransit"),
        ("delivered", "delivered"),
        ("cancelled", "cancelled")
    )
    current_status = models.CharField(max_length=100, choices=CURRENT_STATUS, default="ordered")

    CURRENT_STATUS_ADMIN = (
        ("pending", "pending"),
        ("cancelled", "cancelled"),
        ("approved", "approved"),
        ("picked", "picked"),
        ("dispatched", "dispatched"),
        ("delivered", "delivered"),
        ("delivery failed", "delivery failed"),
    )
    current_status_admin = models.CharField(max_length=100, choices=CURRENT_STATUS_ADMIN, default="pending")

    cancelling_note = models.TextField(default="")

    SHIPPING_METHOD = (
        ("pending", "pending"),
        ("WIG Fleet", "WIG Fleet"),
        ("TFM", "TFM")
    )
    shipping_method = models.CharField(max_length=100, choices=SHIPPING_METHOD, default="pending")

    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(DealsHubProduct, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    price = models.FloatField(default=None, null=True, blank=True)
    currency = models.CharField(max_length=100, default='AED')
    uuid = models.CharField(max_length=200, default="")

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())
            self.orderid = "wig"+str(uuid.uuid4())[:5]

        super(UnitOrder, self).save(*args, **kwargs)


class UnitOrderStatus(models.Model):
    unit_order = models.ForeignKey(UnitOrder, on_delete=models.CASCADE)
    STATUS = (
        ("ordered", "ordered"),
        ("shipped", "shipped"),
        ("intransit", "intransit"),
        ("delivered", "delivered"),
        ("cancelled", "cancelled")
    )
    status = models.CharField(max_length=100, choices=STATUS, default="ordered")

    STATUS_ADMIN = (
        ("pending", "pending"),
        ("cancelled", "cancelled"),
        ("approved", "approved"),
        ("picked", "picked"),
        ("dispatched", "dispatched"),
        ("delivered", "delivered"),
        ("delivery failed", "delivery failed"),
    )
    status_admin = models.CharField(max_length=100, choices=STATUS_ADMIN, default="pending")

    date_created = models.DateTimeField(auto_now_add=True)
    uuid = models.CharField(max_length=200, default="")

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())

        super(UnitOrderStatus, self).save(*args, **kwargs)


class DealsHubUser(User):

    contact_number = models.CharField(default="", max_length=50)
    date_created = models.DateTimeField(null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    contact_verified = models.BooleanField(default=False)
    verification_code = models.CharField(default="", max_length=50)
    website_group = models.CharField(default="", max_length=100)
    
    class Meta:
        verbose_name = "DealsHubUser"
        verbose_name_plural = "DealsHubUser"

    def save(self, *args, **kwargs):

        if self.pk == None:
            self.date_created = timezone.now()
        
        super(DealsHubUser, self).save(*args, **kwargs)


class AdminReviewComment(models.Model):

    uuid = models.CharField(max_length=200,  unique=True)
    username = models.CharField(max_length=200)
    display_name = models.CharField(max_length=200)
    comment =  models.TextField(max_length=500)
    created_date = models.DateTimeField(null=True, blank=True)
    modified_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(self.uuid)

    def save(self, *args, **kwargs):

        if self.pk == None:
            self.created_date = timezone.now()
            self.modified_date = timezone.now()
        else:
            self.modified_date = timezone.now()

        if self.uuid == None or self.uuid=="":
            self.uuid = str(uuid.uuid4())

        super(AdminReviewComment, self).save(*args, **kwargs)


class ReviewContent(models.Model):

    uuid = models.CharField(max_length=200, unique=True)
    subject = models.CharField(max_length=400, default="")
    content = models.TextField(max_length=500)
    upvoted_users = models.ManyToManyField(DealsHubUser, blank=True)
    admin_comment = models.ForeignKey(AdminReviewComment, default=None, null=True, blank=True,on_delete=models.SET_DEFAULT)

    def __str__(self):
        return str(self.uuid)

    def save(self, *args, **kwargs):

        if self.uuid == None or self.uuid=="":
            self.uuid = str(uuid.uuid4())

        super(ReviewContent, self).save(*args, **kwargs)


class Review(models.Model):

    uuid = models.CharField(max_length=200,  unique=True)
    dealshub_user = models.ForeignKey(DealsHubUser,on_delete=models.CASCADE)
    product = models.ForeignKey(DealsHubProduct, on_delete=models.CASCADE)
    rating = models.IntegerField(default=0)
    content = models.ForeignKey(ReviewContent, default=None, null=True, blank=True,on_delete=models.SET_DEFAULT)
    created_date = models.DateTimeField(blank=True)
    modified_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(self.uuid)

    def save(self, *args, **kwargs):

        if self.pk == None:
            self.created_date = timezone.now()
            self.modified_date = timezone.now()
        else:
            self.modified_date = timezone.now()

        if self.uuid == None or self.uuid=="":
            self.uuid = str(uuid.uuid4())

        super(Review, self).save(*args, **kwargs)
