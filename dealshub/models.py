from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

import logging
import json
import uuid

from WAMSApp.models import *
from dealshub.core_utils import *

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


class Voucher(models.Model):

    uuid = models.CharField(max_length=200,default="",unique=True)
    voucher_code = models.CharField(max_length=50,unique=True)
    start_time = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)

    VOUCHERS_TYPE = (
        ("PD","PERCENTAGE_DISCOUNT"),
        ("FD","FIXED_DISCOUNT"),
        ("SD","SHIPPING_DISCOUNT"),
    )

    voucher_type = models.CharField(max_length=50, choices=VOUCHERS_TYPE, default="PD")
    percent_discount = models.FloatField(default=0)
    fixed_discount = models.FloatField(default=0)
    maximum_discount = models.FloatField(default=0)
    customer_usage_limit = models.IntegerField(default=0)
    maximum_usage_limit = models.IntegerField(default=0)
    minimum_purchase_amount = models.IntegerField(default=0)
    total_usage = models.IntegerField(default=0)
    location_group = models.ForeignKey(LocationGroup, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return str(self.uuid)

    def is_expired(self):
        if timezone.now() >= self.start_time and timezone.now() <= self.end_time:
            if maximum_usage_limit==0:
                return False
            if total_usage>=maximum_usage_limit:
                return True
            return False
        return True

    def get_discounted_price(self, total):
        if self.voucher_type=="SD":
            return total
        if self.voucher_type=="FD" and total>=self.minimum_purchase_amount:
            return (total-self.fixed_discount)
        if self.voucher_type=="PD" and total>=self.minimum_purchase_amount:
            return round((total-(total*self.percent_discount/100)), 2)

    def save(self, *args, **kwargs):

        if self.uuid == None or self.uuid=="":
            self.uuid = str(uuid.uuid4())

        super(Voucher, self).save(*args, **kwargs)


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
    location_group = models.ForeignKey(LocationGroup, null=True, blank=True, on_delete=models.SET_NULL)
    uuid = models.CharField(max_length=200, default="", unique=True)

    class Meta:
        verbose_name = "DealsHub Product"
        verbose_name_plural = "DealsHub Products"

    def __str__(self):
        return str(self.product)

    def get_currency(self):
        return str(self.location_group.location.currency)

    def get_category(self):
        if self.base_product_obj.category!=None:
            return str(self.product.base_product_obj.category)
        return ""

    def get_sub_category(self):
        if self.base_product_obj.sub_category!=None:
            return str(self.product.base_product_obj.sub_category)
        return ""

    def get_name(self):
        return str(self.product.product_name)

    def get_product_id(self):
        return str(self.product.product_id)

    def get_brand(self):
        return str(self.product.base_product.brand)

    def get_seller_sku(self):
        return str(self.product.base_product.seller_sku)

    def get_warranty(self):
        return str(self.product.warranty)

    def get_actual_price(self):
        if self.promotion==None:
            return self.now_price
        if check_valid_promotion(self.promotion)!=None:
            return self.promotional_price
        return self.now_price

    def get_main_image_url(self):
        main_images_list = ImageBucket.objects.none()
        main_images_objs = MainImages.objects.filter(product=self.product)
        for main_images_obj in main_images_objs:
            main_images_list |= main_images_obj.main_images.all()
        main_images_list = main_images_list.distinct()
        if main_images_list.all().count()>0:
            return main_images_list.all()[0].image.mid_image.url
        return Config.objects.all()[0].product_404_image.image.url

    def get_display_image_url(self):
        lifestyle_image_objs = self.product.lifestyle_images.all()
        if lifestyle_image_objs.exists():
            return lifestyle_image_objs[0].mid_image.url
        return self.get_main_image_url()

    def save(self, *args, **kwargs):
        
        if self.uuid == None or self.uuid == "":
            self.uuid = str(uuid.uuid4())
        
        super(DealsHubProduct, self).save(*args, **kwargs)


class Section(models.Model):

    uuid = models.CharField(max_length=200, unique=True)
    location_group = models.ForeignKey(LocationGroup, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=300, default="")
    is_published = models.BooleanField(default=False)
    listing_type = models.CharField(default="Carousel", max_length=200)

    products = models.ManyToManyField(DealsHubProduct, blank=True)
    hovering_banner_image = models.ForeignKey(Image, related_name="section_hovering_banner_image", on_delete=models.SET_NULL, null=True,blank=True)

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
    location_group = models.ForeignKey(LocationGroup, null=True, blank=True, on_delete=models.SET_NULL)
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

    products = models.ManyToManyField(DealsHubProduct, blank=True)
    hovering_banner_image = models.ForeignKey(Image, related_name="unit_hovering_banner_image", on_delete=models.SET_NULL, null=True,blank=True)

    promotion = models.ForeignKey(Promotion,null=True,blank=True)

    def __str__(self):
        return str(self.uuid)

    def save(self, *args, **kwargs):

        if self.uuid == None or self.uuid=="":
            self.uuid = str(uuid.uuid4())
        
        super(UnitBannerImage, self).save(*args, **kwargs)


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

    user = models.ForeignKey('DealsHubUser', on_delete=models.CASCADE)

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

    location_group = models.ForeignKey(LocationGroup, null=True, blank=True, on_delete=models.SET_NULL)

    uuid = models.CharField(max_length=200, default="")

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())

        super(Address, self).save(*args, **kwargs)

    def get_country(self):
        return str(self.location_group.location.country)

    def get_shipping_address(self):
        return self.first_name + " " + self.last_name + "\n" + json.loads(self.address_lines)[0] + "\n"+json.loads(self.address_lines)[1] + "\n"+json.loads(self.address_lines)[2] + "\n"+json.loads(self.address_lines)[3] + "\n"+self.state

    class Meta:
        verbose_name = "Address"
        verbose_name_plural = "Addresses"


class Cart(models.Model):

    owner = models.ForeignKey('DealsHubUser', on_delete=models.CASCADE)
    uuid = models.CharField(max_length=200, default="")
    location_group = models.ForeignKey(LocationGroup, null=True, blank=True, on_delete=models.SET_NULL)
    voucher = models.ForeignKey(Voucher, null=True, blank=True, on_delete=models.SET_NULL)
    shipping_address = models.ForeignKey(Address, null=True, blank=True, on_delete=models.CASCADE)
    payment_mode = models.CharField(default="COD", max_length=100)
    to_pay = models.FloatField(default=0)
    merchant_reference = models.CharField(max_length=200, default="")
    payment_info = models.TextField(default="{}")

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())

        super(Cart, self).save(*args, **kwargs)

    def get_subtotal(self):
        unit_cart_objs = UnitCart.objects.filter(cart=self)
        subtotal = 0
        for unit_cart_obj in unit_cart_objs:
            subtotal += float(unit_cart_obj.product.get_actual_price())*float(unit_cart_obj.quantity)
        return subtotal

    def get_delivery_fee(self):
        subtotal = self.get_subtotal()
        if self.voucher!=None and self.voucher.is_expired()==False and is_voucher_limt_exceeded_for_customer(self.owner, self.voucher)==False:
            if self.voucher_type=="SD":
                return 0
            subtotal = self.voucher.get_discounted_price(subtotal)

        if subtotal < self.location_group.free_delivery_threshold:
            return self.location_group.delivery_fee
        return 0

    def get_total_amount(self):
        subtotal = self.get_subtotal()
        subtotal = self.voucher.get_discounted_price(subtotal)
        delivery_fee = self.get_delivery_fee()
        return subtotal+delivery_fee

    def get_vat(self):
        total = self.get_total_amount()
        return round((total_amount - total_amount/1.05), 2)

    def is_cod_allowed(self):
        unit_cart_objs = UnitCart.objects.filter(cart=self)
        for unit_cart_obj in unit_cart_objs:
            if unit_cart_obj.product.is_cod_allowed==False:
                return False
        return True

    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"


class UnitCart(models.Model):

    cart = models.ForeignKey('Cart', on_delete=models.CASCADE)
    product = models.ForeignKey(DealsHubProduct, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    
    date_created = models.DateTimeField(auto_now_add=True)
    uuid = models.CharField(max_length=200, default="")

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())

        super(UnitCart, self).save(*args, **kwargs)

    def get_date_created(self):
        return str(timezone.localtime(self.date_created).strftime("%d %b, %Y"))

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

    PENDING, PAID = ('pending', 'paid')
    PAYMENT_STATUS = (
        (PENDING, "pending"),
        (PAID, "paid")
    )
    payment_status = models.CharField(max_length=100, choices=PAYMENT_STATUS, default="pending")
    payment_info = models.TextField(default="{}")
    merchant_reference = models.CharField(max_length=200, default="")

    voucher = models.ForeignKey(Voucher,null=True,default=None,blank=True,on_delete=models.SET_NULL)
    location_group = models.ForeignKey(LocationGroup, null=True, blank=True, on_delete=models.SET_NULL)

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())
            self.bundleid = "wig"+str(uuid.uuid4())[:5]

        super(Order, self).save(*args, **kwargs)

    def get_date_created(self):
        return str(timezone.localtime(self.date_created).strftime("%d %b, %Y"))

    def get_time_created(self):
        return str(timezone.localtime(self.date_created).strftime("%I:%M %p"))

    def get_subtotal(self):
        unit_order_objs = UnitOrder.objects.filter(order=self)
        subtotal = 0
        for unit_order_obj in unit_order_objs:
            subtotal += float(unit_order_obj.price)*float(unit_order_obj.quantity)
        return subtotal

    def get_delivery_fee(self):
        subtotal = self.get_subtotal()
        if self.voucher!=None:
            if self.voucher_type=="SD":
                return 0
            subtotal = self.voucher.get_discounted_price(subtotal)

        if subtotal < self.location_group.free_delivery_threshold:
            return self.location_group.delivery_fee
        return 0

    def get_cod_charge(self):
        if self.payment_mode=="COD":
            return order_obj.location_group.cod_charge
        return 0

    def get_total_amount(self):
        subtotal = self.get_subtotal()
        subtotal = self.voucher.get_discounted_price(subtotal)
        delivery_fee = self.get_delivery_fee()
        cod_charge = self.get_cod_charge()
        return subtotal+delivery_fee+cod_charge

    def get_vat(self):
        total = self.get_total_amount()
        return round((total_amount - total_amount/1.05), 2)


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

    def get_date_created(self):
        return str(timezone.localtime(self.date_created).strftime("%d %b, %Y"))

    def get_time_created(self):
        return str(timezone.localtime(self.date_created).strftime("%I:%M %p"))


class DealsHubUser(User):

    contact_number = models.CharField(default="", max_length=50)
    date_created = models.DateTimeField(null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    contact_verified = models.BooleanField(default=False)
    verification_code = models.CharField(default="", max_length=50)
    website_group = models.ForeignKey(WebsiteGroup, null=True, blank=True, on_delete=models.SET_NULL)
    
    class Meta:
        verbose_name = "DealsHubUser"
        verbose_name_plural = "DealsHubUser"

    def save(self, *args, **kwargs):

        if self.pk == None:
            self.date_created = timezone.now()
        
        super(DealsHubUser, self).save(*args, **kwargs)


class AdminReviewComment(models.Model):

    uuid = models.CharField(max_length=200, unique=True)
    user = models.ForeignKey(OmnyCommUser, on_delete=models.CASCADE)
    comment =  models.TextField(default="")
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

    uuid = models.CharField(max_length=200, unique=True)
    dealshub_user = models.ForeignKey(DealsHubUser, on_delete=models.CASCADE)
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