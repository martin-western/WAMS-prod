from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

import logging
import json
import uuid

from WAMSApp.models import *
from dealshub.core_utils import *
from django.core.cache import cache

logger = logging.getLogger(__name__)

address_lines = ["", "", "", ""]


def is_voucher_limt_exceeded_for_customer(dealshub_user_obj, voucher_obj):
    if voucher_obj.customer_usage_limit==0:
        return False
    if Order.objects.filter(owner=dealshub_user_obj, voucher=voucher_obj).count()<voucher_obj.customer_usage_limit:
        return False
    return True

class SearchKeyword(models.Model):
    word = models.CharField(default="", max_length=200)
    created_date = models.DateTimeField()
    location_group = models.ForeignKey(LocationGroup, blank=True, null=True, on_delete=models.SET_NULL)

    def save(self, *args, **kwargs):
        
        if self.pk == None:
            self.created_date = timezone.now()
        
        super(SearchKeyword, self).save(*args, **kwargs)

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
    voucher_code = models.CharField(max_length=50)
    start_time = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)
    description = models.TextField(default="")

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
    is_deleted = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    location_group = models.ForeignKey(LocationGroup, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return str(self.uuid)

    def is_expired(self):
        if self.is_deleted==True or self.is_published==False:
            return True
        if timezone.now() >= self.start_time and timezone.now() <= self.end_time:
            if self.maximum_usage_limit==0:
                return False
            if self.total_usage>=self.maximum_usage_limit:
                return True
            return False
        return True

    def is_eligible(self, subtotal):
        if subtotal>=self.minimum_purchase_amount:
            return True
        return False

    def get_discounted_price(self, subtotal):
        if self.voucher_type=="SD":
            return subtotal
        if self.voucher_type=="FD" and subtotal>=self.minimum_purchase_amount:
            return (subtotal-self.fixed_discount)
        if self.voucher_type=="PD" and subtotal>=self.minimum_purchase_amount:
            discount = min(self.maximum_discount, round(subtotal*self.percent_discount/100, 2))
            return (subtotal-discount)
        return subtotal

    def get_voucher_discount(self, subtotal):
        if self.voucher_type=="SD":
            return self.location_group.delivery_fee
        if self.voucher_type=="FD" and subtotal>=self.minimum_purchase_amount:
            return self.fixed_discount
        if self.voucher_type=="PD" and subtotal>=self.minimum_purchase_amount:
            discount = min(self.maximum_discount, round(subtotal*self.percent_discount/100, 2))
            return discount
        return 0

    def get_voucher_discount_vat(self, voucher_discount):
        if self.location_group.vat==0:
            return 0
        vat_divider = 1+(self.location_group.vat/100)
        return round(voucher_discount - voucher_discount/vat_divider, 2) 

    def get_voucher_discount_without_vat(self, voucher_discount):
        vat_divider = 1+(self.location_group.vat/100)
        return round(voucher_discount/vat_divider, 2) 

    def save(self, *args, **kwargs):

        if self.uuid == None or self.uuid=="":
            self.uuid = str(uuid.uuid4())

        super(Voucher, self).save(*args, **kwargs)


class DealsHubProductManager(models.Manager):

    def get_queryset(self):
        return super(DealsHubProductManager, self).get_queryset().exclude(is_deleted=True)


class DealsHubProductRecoveryManager(models.Manager):

    def get_queryset(self):
        return super(DealsHubProductRecoveryManager, self).get_queryset()


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
    category = models.ForeignKey(Category, null=True, blank=True, default=None, on_delete=models.SET_NULL)
    sub_category = models.ForeignKey(SubCategory, null=True, blank=True, default=None, on_delete=models.SET_NULL)
    uuid = models.CharField(max_length=200, default="")

    is_deleted = models.BooleanField(default=False)
    objects = DealsHubProductManager()
    recovery = DealsHubProductRecoveryManager()

    class Meta:
        verbose_name = "DealsHub Product"
        verbose_name_plural = "DealsHub Products"

    def __str__(self):
        return str(self.product)

    def get_currency(self):
        return str(self.location_group.location.currency)

    def get_category(self):
        if self.category!=None:
            return str(self.category)
        return ""

    def get_sub_category(self):
        if self.sub_category!=None:
            return str(self.sub_category)
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

    def get_weight(self):
        return float(self.product.weight)

    def get_material(self):
        if self.product.material_type==None:
            return "NA"
        return str(self.product.material_type)

    def get_color(self):
        if self.product.color=="":
            return "NA"
        return self.product.color

    def get_dimensions(self):
        dimensions = json.loads(self.product.base_product.dimensions)
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

    def get_faqs(self):
        return json.loads(self.product.faqs)

    def get_how_to_use(self):
        return json.loads(self.product.how_to_use)

    def get_actual_price(self):
        if self.promotion==None:
            return self.now_price
        if check_valid_promotion(self.promotion)==True:
            return self.promotional_price
        return self.now_price

    def get_main_image_url(self):
        cached_url = cache.get("main_url_"+str(self.uuid), "has_expired")
        if cached_url!="has_expired":
            return cached_url
        main_images_list = ImageBucket.objects.none()
        main_images_objs = MainImages.objects.filter(product=self.product)
        for main_images_obj in main_images_objs:
            main_images_list |= main_images_obj.main_images.all()
        main_images_list = main_images_list.distinct()
        if main_images_list.all().count()>0:
            main_image_url = main_images_list.all()[0].image.mid_image.url
            cache.set("main_url_"+str(self.uuid), main_image_url)
            return main_image_url
        main_image_url = Config.objects.all()[0].product_404_image.image.url
        cache.set("main_url_"+str(self.uuid), main_image_url)
        return main_image_url

    def get_display_image_url(self):
        cached_url = cache.get("display_url_"+str(self.uuid), "has_expired")
        if cached_url!="has_expired":
            return cached_url
        lifestyle_image_objs = self.product.lifestyle_images.all()
        if lifestyle_image_objs.exists():
            display_image_url = lifestyle_image_objs[0].mid_image.url
            cache.set("display_url_"+str(self.uuid), display_image_url)
            return display_image_url
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


class WishList(models.Model):

    owner = models.ForeignKey('DealsHubUser', on_delete=models.CASCADE)
    uuid = models.CharField(max_length=200, default="")
    location_group = models.ForeignKey(LocationGroup, null=True, blank=True, on_delete=models.SET_NULL)
    modified_date = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())

        modified_date = timezone.now()
        super(WishList, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "Wish List"
        verbose_name_plural = "Wish Lists"


class UnitWishList(models.Model):

    wish_list = models.ForeignKey('WishList', on_delete=models.CASCADE)
    product = models.ForeignKey(DealsHubProduct, on_delete=models.CASCADE)
    
    date_created = models.DateTimeField(auto_now_add=True)
    uuid = models.CharField(max_length=200, default="")

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())

        super(UnitWishList, self).save(*args, **kwargs)

    def get_date_created(self):
        return str(timezone.localtime(self.date_created).strftime("%d %b, %Y"))

    class Meta:
        verbose_name = "Unit Wish List"
        verbose_name_plural = "Unit Wish Lists"


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
    modified_date = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())

        self.modified_date = timezone.now()
        super(Cart, self).save(*args, **kwargs)

    def get_subtotal(self):
        unit_cart_objs = UnitCart.objects.filter(cart=self)
        subtotal = 0
        for unit_cart_obj in unit_cart_objs:
            subtotal += float(unit_cart_obj.product.get_actual_price())*float(unit_cart_obj.quantity)
        return subtotal

    def get_delivery_fee(self, cod=False, offline=False):
        subtotal = self.get_subtotal()
        if subtotal==0:
            return 0
        if (cod==False or offline==True) and self.voucher!=None and self.voucher.is_expired()==False and is_voucher_limt_exceeded_for_customer(self.owner, self.voucher)==False:
            if self.voucher.voucher_type=="SD":
                return 0
            subtotal = self.voucher.get_discounted_price(subtotal)

        if subtotal < self.location_group.free_delivery_threshold:
            return self.location_group.delivery_fee
        return 0

    def get_total_amount(self, cod=False, offline=False):
        subtotal = self.get_subtotal()
        if subtotal==0:
            return 0
        if (cod==False or offline==True) and self.voucher!=None and self.voucher.is_expired()==False and is_voucher_limt_exceeded_for_customer(self.owner, self.voucher)==False:
            subtotal = self.voucher.get_discounted_price(subtotal)
        delivery_fee = self.get_delivery_fee(cod, offline)
        if cod==True:
            subtotal += self.location_group.cod_charge
        return subtotal+delivery_fee

    def get_vat(self, cod=False, offline=False):
        total_amount = self.get_total_amount(cod, offline)
        if self.location_group.vat==0:
            return 0
        vat_divider = 1+(self.location_group.vat/100)
        return round((total_amount - total_amount/vat_divider), 2)

    def get_currency(self):
        return str(self.location_group.location.currency)

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
    is_order_offline = models.BooleanField(default=False)
    order_placed_date = models.DateTimeField(null=True, default=timezone.now)

    PENDING, PAID = ('pending', 'paid')
    PAYMENT_STATUS = (
        (PENDING, "pending"),
        (PAID, "paid")
    )
    payment_status = models.CharField(max_length=100, choices=PAYMENT_STATUS, default="pending")
    payment_info = models.TextField(default="{}")
    merchant_reference = models.CharField(max_length=200, default="")

    postaplus_info = models.TextField(default="{}")
    is_postaplus = models.BooleanField(default=False)

    voucher = models.ForeignKey(Voucher,null=True,default=None,blank=True,on_delete=models.SET_NULL)
    location_group = models.ForeignKey(LocationGroup, null=True, blank=True, on_delete=models.SET_NULL)

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())
            order_prefix = ""
            try:
                order_prefix = json.loads(self.location_group.website_group.conf)["order_prefix"]
            except Exception as e:
                pass
            self.bundleid = order_prefix + str(uuid.uuid4())[:5]

        super(Order, self).save(*args, **kwargs)

    def get_date_created(self):
        return str(timezone.localtime(self.order_placed_date).strftime("%d %b, %Y"))

    def get_time_created(self):
        return str(timezone.localtime(self.order_placed_date).strftime("%I:%M %p"))

    def get_currency(self):
        return str(self.location_group.location.currency)

    def get_subtotal(self):
        unit_order_objs = UnitOrder.objects.filter(order=self)
        subtotal = 0
        for unit_order_obj in unit_order_objs:
            subtotal += float(unit_order_obj.price)*float(unit_order_obj.quantity)
        return subtotal

    def get_subtotal_vat(self):
        if self.location_group.vat==0:
            return 0
        vat_divider = 1+(self.location_group.vat/100)
        subtotal = self.get_subtotal()
        return round(subtotal - subtotal/vat_divider, 2)

    def get_subtotal_without_vat(self):
        subtotal = self.get_subtotal()
        vat_divider = 1+(self.location_group.vat/100)
        return str(round(subtotal/vat_divider, 2))

    def get_delivery_fee(self):
        subtotal = self.get_subtotal()
        if self.voucher!=None:
            if self.voucher.voucher_type=="SD":
                return 0
            subtotal = self.voucher.get_discounted_price(subtotal)

        if subtotal < self.location_group.free_delivery_threshold:
            return self.location_group.delivery_fee
        return 0

    def get_delivery_fee_vat(self):
        if self.location_group.vat==0:
            return 0
        vat_divider = 1+(self.location_group.vat/100)
        delivery_fee = self.get_delivery_fee()
        return round(delivery_fee - delivery_fee/vat_divider, 2)

    def get_delivery_fee_without_vat(self):
        delivery_fee = self.get_delivery_fee()
        vat_divider = 1+(self.location_group.vat/100)
        return str(round(delivery_fee/vat_divider, 2))

    def get_cod_charge(self):
        if self.payment_mode=="COD":
            return self.location_group.cod_charge
        return 0

    def get_cod_charge_vat(self):
        if self.location_group.vat==0:
            return 0
        vat_divider = 1+(self.location_group.vat/100)
        cod_fee = self.get_cod_charge()
        return round(cod_fee - cod_fee/vat_divider, 2)

    def get_cod_charge_without_vat(self):
        cod_fee = self.get_cod_charge()
        vat_divider = 1+(self.location_group.vat/100)
        return str(round(cod_fee/vat_divider, 2))

    def get_total_amount(self):
        subtotal = self.get_subtotal()
        if self.voucher!=None and self.voucher.is_expired()==False and is_voucher_limt_exceeded_for_customer(self.owner, self.voucher)==False:
            subtotal = self.voucher.get_discounted_price(subtotal)
        delivery_fee = self.get_delivery_fee()
        cod_charge = self.get_cod_charge()
        return subtotal+delivery_fee+cod_charge

    def get_vat(self):
        total_amount = self.get_total_amount()
        if self.location_group.vat==0:
            return 0
        vat_divider = 1+(self.location_group.vat/100)
        return round((total_amount - total_amount/vat_divider), 2)

    def get_website_link(self):
        return self.location_group.website_group.link

    def get_customer_full_name(self):
        return self.shipping_address.first_name + " " + self.shipping_address.last_name

    def get_customer_first_name(self):
        return self.shipping_address.first_name

    def get_email_website_logo(self):
        if self.location_group.website_group.footer_logo!=None:
            return self.location_group.website_group.footer_logo.image.url
        if self.location_group.website_group.logo!=None:
            return self.location_group.website_group.logo.image.url
        return ""


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

    def get_subtotal(self):
        return float(self.price)*float(self.quantity)

    def get_price_without_vat(self):
        vat_divider = 1 + (self.order.location_group.vat/100)
        return round(self.price/vat_divider, 2)

    def get_total_vat(self):
        if self.order.location_group.vat==0:
            return 0
        vat_divider = 1 + (self.order.location_group.vat/100)
        temp_total = self.get_subtotal()
        return round(temp_total - temp_total/vat_divider, 2)

    def get_subtotal_without_vat(self):
        temp_total = self.get_subtotal()
        vat_divider = 1 + (self.order.location_group.vat/100)
        return  round(temp_total/vat_divider, 2)

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())
            order_prefix = ""
            try:
                order_prefix = json.loads(self.order.location_group.website_group.conf)["order_prefix"]
            except Exception as e:
                pass
            self.orderid = order_prefix + str(uuid.uuid4())[:5]

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


class FastCart(models.Model):

    owner = models.ForeignKey('DealsHubUser', on_delete=models.CASCADE)
    uuid = models.CharField(max_length=200, default="")
    location_group = models.ForeignKey(LocationGroup, null=True, blank=True, on_delete=models.SET_NULL)
    voucher = models.ForeignKey(Voucher, null=True, blank=True, on_delete=models.SET_NULL)
    shipping_address = models.ForeignKey(Address, null=True, blank=True, on_delete=models.CASCADE)
    payment_mode = models.CharField(default="COD", max_length=100)
    to_pay = models.FloatField(default=0)
    merchant_reference = models.CharField(max_length=200, default="")
    payment_info = models.TextField(default="{}")
    modified_date = models.DateTimeField(null=True, blank=True)
    product = models.ForeignKey(DealsHubProduct, null=True, blank=True, on_delete=models.SET_NULL)
    quantity = models.IntegerField(default=1)

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())

        self.modified_date = timezone.now()
        super(FastCart, self).save(*args, **kwargs)

    def get_subtotal(self):
        subtotal = float(self.product.get_actual_price())*float(self.quantity)
        return subtotal

    def get_delivery_fee(self, cod=False):
        subtotal = self.get_subtotal()
        if subtotal==0:
            return 0
        if cod==False and self.voucher!=None and self.voucher.is_expired()==False and is_voucher_limt_exceeded_for_customer(self.owner, self.voucher)==False:
            if self.voucher.voucher_type=="SD":
                return 0
            subtotal = self.voucher.get_discounted_price(subtotal)

        if subtotal < self.location_group.free_delivery_threshold:
            return self.location_group.delivery_fee
        return 0

    def get_total_amount(self, cod=False):
        subtotal = self.get_subtotal()
        if subtotal==0:
            return 0
        if cod==False and self.voucher!=None and self.voucher.is_expired()==False and is_voucher_limt_exceeded_for_customer(self.owner, self.voucher)==False:
            subtotal = self.voucher.get_discounted_price(subtotal)
        delivery_fee = self.get_delivery_fee(cod)
        if cod==True:
            subtotal += self.location_group.cod_charge
        return subtotal+delivery_fee

    def get_vat(self, cod=False):
        total_amount = self.get_total_amount(cod)
        if self.location_group.vat==0:
            return 0
        vat_divider = 1+(self.location_group.vat/100)
        return round((total_amount - total_amount/vat_divider), 2)

    def get_currency(self):
        return str(self.location_group.location.currency)

    def is_cod_allowed(self):
        if self.product.is_cod_allowed==False:
            return False
        return True

    class Meta:
        verbose_name = "FastCart"
        verbose_name_plural = "FastCarts"


class DealsHubUser(User):

    contact_number = models.CharField(default="", max_length=50)
    date_created = models.DateTimeField(null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    contact_verified = models.BooleanField(default=False)
    verification_code = models.CharField(default="", max_length=50)
    is_pin_set = models.BooleanField(default=False)
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
    images = models.ManyToManyField(Image, blank=True)
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
