from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

import logging
import json
import uuid
import threading

from WAMSApp.models import *
from dealshub.core_utils import *
from WAMSApp.sap.SAP_constants import *
from django.core.cache import cache
#from dealshub.algolia.utils import *
from algoliasearch.search_client import SearchClient
from dealshub.algolia.constants import *

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


def add_product_to_index(dealshub_product_obj):

    client = SearchClient.create(APPLICATION_KEY, ADMIN_KEY)
    index = client.init_index(DEALSHUBPRODUCT_ALGOLIA_INDEX)
    
    try:
        # logger.info("add_product_to_index: %s", str(dealshub_product_obj.__dict__))
        dealshub_product_dict = {}
        dealshub_product_dict["locationGroup"] = dealshub_product_obj.location_group.uuid
        dealshub_product_dict["objectID"] = dealshub_product_obj.uuid
        dealshub_product_dict["productName"] = dealshub_product_obj.get_name()
        dealshub_product_dict["category"] = [dealshub_product_obj.get_category()]
        dealshub_product_dict["superCategory"] = [dealshub_product_obj.get_super_category()]
        dealshub_product_dict["subCategory"] = [dealshub_product_obj.get_sub_category()]
        dealshub_product_dict["brand"] = dealshub_product_obj.get_brand()
        dealshub_product_dict["sellerSKU"] = dealshub_product_obj.get_seller_sku()
        dealshub_product_dict["isPublished"] = dealshub_product_obj.is_published
        dealshub_product_dict["price"] = dealshub_product_obj.now_price
        dealshub_product_dict["stock"] = dealshub_product_obj.stock
        dealshub_product_dict["pk"] = dealshub_product_obj.pk

        additional_category_hierarchy = dealshub_product_obj.get_additional_category_hierarchy()
        dealshub_product_dict["subCategory"].extend(additional_category_hierarchy["additional_sub_categories"])
        dealshub_product_dict["category"].extend(additional_category_hierarchy["additional_categories"])
        dealshub_product_dict["superCategory"].extend(additional_category_hierarchy["additional_super_categories"])

        index.save_object(dealshub_product_dict, {'autoGenerateObjectIDIfNotExist': False})
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("add_product_to_index: %s at %s", e, str(exc_tb.tb_lineno))


class DealsHubProductManager(models.Manager):

    def get_queryset(self):
        return super(DealsHubProductManager, self).get_queryset().exclude(is_deleted=True)


class DealsHubProductRecoveryManager(models.Manager):

    def get_queryset(self):
        return super(DealsHubProductRecoveryManager, self).get_queryset()


class DealsHubProduct(models.Model):

    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=True)
    product_name = models.CharField(max_length=200, default="")
    product_name_ar = models.CharField(max_length=200,default="")
    product_description = models.TextField(default="", blank=True)
    product_description_ar = models.TextField(default="", blank=True)
    was_price = models.FloatField(default=0)
    now_price = models.FloatField(default=0)
    promotional_price = models.FloatField(default=0)
    stock = models.IntegerField(default=0)
    allowed_qty = models.IntegerField(default=1000)
    moq = models.IntegerField(default=5)
    is_cod_allowed = models.BooleanField(default=True)
    properties = models.TextField(null=True, blank=True, default="{}")
    promotion = models.ForeignKey(Promotion,null=True,blank=True)
    is_published = models.BooleanField(default=False)
    location_group = models.ForeignKey(LocationGroup, null=True, blank=True, on_delete=models.SET_NULL)
    category = models.ForeignKey(Category, null=True, blank=True, default=None, on_delete=models.SET_NULL)
    sub_category = models.ForeignKey(SubCategory, null=True, blank=True, default=None, on_delete=models.SET_NULL)
    additional_sub_categories = models.ManyToManyField(SubCategory, related_name="additional_sub_categories", blank=True)
    url = models.CharField(max_length=200, default="")
    uuid = models.CharField(max_length=200, default="")
    page_description = models.TextField(default="")
    seo_title = models.TextField(default="")
    seo_keywords = models.TextField(default="")
    seo_description = models.TextField(default="")
    search_keywords = models.TextField(default="")

    warranty = models.CharField(max_length=100, default="")

    is_promo_restricted = models.BooleanField(default=False)
    is_new_arrival = models.BooleanField(default=False)
    is_on_sale = models.BooleanField(default=False)
    is_promotional = models.BooleanField(default=False)

    is_bestseller = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)

    is_deleted = models.BooleanField(default=False)
    objects = DealsHubProductManager()
    recovery = DealsHubProductRecoveryManager()
    is_notified = models.BooleanField(default=False)

    moq_cohort1 = models.IntegerField(default=5)
    moq_cohort2 = models.IntegerField(default=5)
    moq_cohort3 = models.IntegerField(default=5)
    moq_cohort4 = models.IntegerField(default=5)
    moq_cohort5 = models.IntegerField(default=5)

    now_price_cohort1 = models.FloatField(default=0)
    now_price_cohort2 = models.FloatField(default=0)
    now_price_cohort3 = models.FloatField(default=0)
    now_price_cohort4 = models.FloatField(default=0)
    now_price_cohort5 = models.FloatField(default=0)

    promotional_price_cohort1 = models.FloatField(default=0)
    promotional_price_cohort2 = models.FloatField(default=0)
    promotional_price_cohort3 = models.FloatField(default=0)
    promotional_price_cohort4 = models.FloatField(default=0)
    promotional_price_cohort5 = models.FloatField(default=0)

    display_image_url = models.TextField(default="")

    class Meta:
        verbose_name = "DealsHub Product"
        verbose_name_plural = "DealsHub Products"

    def __str__(self):
        return str(self.product)

    def get_currency(self):
        return str(self.location_group.location.currency)

    def get_super_category(self,language = "en"):
        if self.category!=None:
            if self.category.super_category!=None:
                if language == "en":
                    return str(self.category.super_category)
                else:
                    return str(self.category.super_category.name_ar)
        return ""

    def get_category(self,language = "en"):
        if self.category!=None:
            if language == "en":
                return str(self.category)
            else:
                return str(self.category.name_ar)
        return ""

    def get_sub_category(self,language = "en"):
        if self.sub_category!=None:
            if language == "en":
                return str(self.sub_category)
            else:
                return str(self.sub_category.name_ar)
        return ""

    def get_additional_category_hierarchy(self):
        temp_dict = {}
        additional_sub_categories = []
        additional_categories = []
        additional_super_categories = []
        additional_sub_categories_objs = self.additional_sub_categories.prefetch_related('category').prefetch_related('category__super_category').all()
        for additional_sub_category_obj in additional_sub_categories_objs:
            if additional_sub_category_obj != None:
                additional_sub_categories.append(str(additional_sub_category_obj))
                additional_category_obj = additional_sub_category_obj.category
                if additional_category_obj != None:
                    additional_categories.append(str(additional_category_obj))
                    additional_super_category_obj = additional_category_obj.super_category
                    if additional_super_category_obj != None:
                        additional_super_categories.append(str(additional_super_category_obj))
        temp_dict["additional_sub_categories"] = additional_sub_categories
        temp_dict["additional_categories"] = additional_categories
        temp_dict["additional_super_categories"] = additional_super_categories

        return temp_dict

    def get_name(self,language = "en"):
        if language == "ar":
            return str(self.product_name_ar)
        return str(self.product_name)

    def get_description(self,language = "en"):
        if self.product_description!="":
            if language == "en":
                return str(self.product_description)
            else:
                return str(self.product_description_ar)
        return str(self.product.product_description)

    def get_product_id(self):
        return str(self.product.product_id)

    def get_brand(self,language = "en"):
        try:
            if language == "ar":
                return str(self.product.base_product.brand.name_ar)
            return str(self.product.base_product.brand.name)
        except Exception as e:
            return ""

    def get_seller_sku(self):
        return str(self.product.base_product.seller_sku)

    def get_warranty(self):
        return str(self.warranty)

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

    def get_target_age_range(self):
        return str(self.product.target_age_range)
    
    def get_capacity(self):
        if str(self.product.capacity)=="":
            return "NA"
        return self.product.capacity + self.product.capacity_unit
    
    def get_size(self):
        if str(self.product.size)=="":
            return "NA"
        return self.product.size + self.product.size_unit

    def get_faqs(self):
        return json.loads(self.product.faqs)

    def get_how_to_use(self):
        return json.loads(self.product.how_to_use)

    def get_moq(self,dealshub_user_obj=None):
        if self.location_group.is_b2b == True:
            if dealshub_user_obj == None:
                return self.moq
            b2b_user_obj = B2BUser.objects.get(username=dealshub_user_obj.username)
            cohort = b2b_user_obj.cohort
            if cohort == "1":
                return self.moq_cohort1
            elif cohort == "2":
                return self.moq_cohort2
            elif cohort == "3":
                return self.moq_cohort3
            elif cohort == "4":
                return self.moq_cohort4
            elif cohort == "5":
                return self.moq_cohort5
        return self.moq

    def get_b2b_price(self,cohort):
        if cohort == "1":
            return self.now_price_cohort1
        elif cohort == "2":
            return self.now_price_cohort2
        elif cohort == "3":
            return self.now_price_cohort3
        elif cohort == "4":
            return self.now_price_cohort4
        elif cohort == "5":
            return self.now_price_cohort5
        return self.now_price

    def get_now_price(self,dealshub_user_obj=None):
        if self.location_group.is_b2b==True:
            if dealshub_user_obj == None:
                return 0
            b2b_user_obj = B2BUser.objects.get(username=dealshub_user_obj.username)
            if check_account_status(b2b_user_obj)==True:
                return  self.get_b2b_price(b2b_user_obj.cohort)
            return 0
        return self.now_price

    def get_was_price(self,dealshub_user_obj=None):
        if self.location_group.is_b2b==True:
            if dealshub_user_obj == None:
                return 0
            b2b_user_obj = B2BUser.objects.get(username=dealshub_user_obj.username)
            if check_account_status(b2b_user_obj)==True:
                return self.was_price
            return 0
        return self.was_price

    def get_b2b_promotional_price(self,cohort):
        if cohort == "1":
            return self.promotional_price_cohort1
        elif cohort == "2":
            return self.promotional_price_cohort2
        elif cohort == "3":
            return self.promotional_price_cohort3
        elif cohort == "4":
            return self.promotional_price_cohort4
        elif cohort == "5":
            return self.promotional_price_cohort5
        return self.promotional_price

    def get_promotional_price(self,dealshub_user_obj=None):
        if self.location_group.is_b2b == True:
            if dealshub_user_obj == None:
                return 0
            b2b_user_obj = B2BUser.objects.get(username=dealshub_user_obj.username)
            if check_account_status(b2b_user_obj)==True:
                return self.get_b2b_promotional_price(b2b_user_obj.cohort)
            return 0
        return self.promotional_price

    def get_actual_price(self,dealshub_user_obj=None):
        if self.location_group.is_b2b == False:
            if self.promotion==None:
                return self.now_price
            if check_valid_promotion(self.promotion)==True:
                return self.promotional_price
            return self.now_price
        else:
            if dealshub_user_obj == None:
                return 0
            b2b_user_obj = B2BUser.objects.get(username = dealshub_user_obj.username)
            if check_account_status(b2b_user_obj) == False:
                return 0
            cohort = b2b_user_obj.cohort

            if self.promotion == None:
                return self.get_b2b_price(cohort)
            if check_valid_promotion(self.promotion)==True:
                return self.get_b2b_promotional_price(cohort)
            return self.get_b2b_price(cohort)

    def get_actual_price_for_customer(self, dealshub_user_obj):
        if self.is_promo_restricted==False or self.promotion==None:
            return self.get_actual_price(dealshub_user_obj)

        if check_valid_promotion(self.promotion)==True:
            promotional_price = self.get_actual_price(dealshub_user_obj)
            if UnitOrder.objects.filter(order__owner=dealshub_user_obj, product=self, price=promotional_price).exists()==False:
                return self.get_actual_price(dealshub_user_obj)

        if self.location_group.is_b2b==True:
            b2b_user_obj = B2BUser.objects.get(username=dealshub_user_obj.username)
            if check_account_status(b2b_user_obj) == False:
                return 0
            cohort = b2b_user_obj.cohort
            return self.get_b2b_price(cohort)
        return self.now_price

    def is_user_eligible_for_promotion(self, dealshub_user_obj):
        if self.is_promo_restricted==False:
            return False
        if self.promotion==None:
            return False
        if check_valid_promotion(self.promotion)==True:
            promotional_price = self.promotional_price
            if UnitOrder.objects.filter(order__owner=dealshub_user_obj, product=self, price=promotional_price).exists()==False:
                return True
        return False

    def is_promo_restriction_note_required(self, dealshub_user_obj):
        if self.is_promo_restricted==False:
            return False
        if self.promotion==None:
            return False
        if check_valid_promotion(self.promotion)==True:
            promotional_price = self.promotional_price
            if UnitOrder.objects.filter(order__owner=dealshub_user_obj, product=self, price=promotional_price).exists()==False:
                return False
            return True
        return False

    def get_allowed_qty(self):
        return min(self.stock, self.allowed_qty)

    def get_main_image_url(self):
        # cached_url = cache.get("main_url_"+str(self.uuid), "has_expired")
        # if cached_url!="has_expired":
        #     return cached_url
        main_images_list = ImageBucket.objects.none()
        main_images_objs = MainImages.objects.filter(product=self.product)
        for main_images_obj in main_images_objs:
            main_images_list |= main_images_obj.main_images.all()
        main_images_list = main_images_list.distinct()
        if main_images_list.all().count()>0:
            main_image_url = main_images_list.all()[0].image.mid_image.url
            #cache.set("main_url_"+str(self.uuid), main_image_url)
            return main_image_url
        main_image_url = Config.objects.all()[0].product_404_image.image.url
        #cache.set("main_url_"+str(self.uuid), main_image_url)
        return main_image_url

    def get_display_image_url(self):
        # cached_url = cache.get("display_url_"+str(self.uuid), "has_expired")
        # if cached_url!="has_expired":
        #     return cached_url
        lifestyle_image_objs = self.product.lifestyle_images.all()
        if lifestyle_image_objs.exists():
            display_image_url = lifestyle_image_objs[0].mid_image.url
            #cache.set("display_url_"+str(self.uuid), display_image_url)
            return display_image_url
        return self.get_main_image_url()

    def get_optimized_display_image_url(self):
        try:
            # cached_url = cache.get("optimized_display_url_"+str(self.uuid), "has_expired")
            # if cached_url!="has_expired":
            #     return cached_url
            lifestyle_image_objs = self.product.lifestyle_images.all()
            if lifestyle_image_objs.exists():
                display_image_url = lifestyle_image_objs[0].thumbnail.url
                #cache.set("optimized_display_url_"+str(self.uuid), display_image_url)
                return display_image_url
        except Exception as e:
            pass
        return self.get_main_image_url()

    def get_search_keywords(self):
        try:
            search_keywords = self.search_keywords.split(",")
            return filter(None, search_keywords)
        except Exception as e:
            return []

    def set_search_keywords(self, search_tags):
        try:
            if len(search_tags)>0:
                search_keywords = ","+",".join(search_tags)+","
                self.search_keywords = search_keywords
                super(DealsHubProduct, self).save()
        except Exception as e:
            pass


    def save(self, *args, **kwargs):
        
        if self.uuid == None or self.uuid == "":
            self.uuid = str(uuid.uuid4())[:8]

        if self.search_keywords=="":
            try:
                search_keywords = []
                if self.category!=None:
                    search_keywords.append(self.category.name)
                if self.sub_category!=None:
                    search_keywords.append(self.sub_category.name)
                search_keywords.append(self.get_seller_sku())
                name = self.get_name()
                name = remove_stopwords_core(name)
                name = name.replace(",", "").strip()
                if name!="":
                    search_keywords.append(name)
                    # 2 words
                    words = name.split(" ")
                    if len(words)>=2:
                        for i in range(len(words)-1):
                            string = " ".join(words[i:i+2])
                            search_keywords.append(string.strip())
                    # 1 word
                    words = name.split(" ")
                    for word in words:
                        if is_number(word.strip())==False:
                            search_keywords.append(word.strip())
                search_keywords = ","+",".join(search_keywords)+","
                self.search_keywords = search_keywords
            except Exception as e:
                pass
        
        if seo_title == "":
            self.seo_title = self.product_name

        if seo_keywords == "":
            self.seo_keywords = json.dumps(sorted(list(set(self.product_description.split(" "))),key=len,reverse=True)[:30])

        if self.url=="":
            try:
                url = self.product_name.strip()[:50].replace(" ", "-").lower()
                seller_sku = self.get_seller_sku().lower()
                if seller_sku not in url:
                    url += "-"+seller_sku
                url = url.replace("/", "-")
                self.url = url
            except Exception as e:
                pass

        try:
            if self.location_group.name in ["WIGMe - UAE","WIGme - Dubai"]:
                logger.info("Update DealsHubProduct to Index: %s",str(self))
                p1 = threading.Thread(target = add_product_to_index, args=(self,))
                p1.start()
                logger.info("Update DealsHubProduct P1 STARTED: %s",str(self))
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Save method DealsHubProduct: %s at %s", e, str(exc_tb.tb_lineno))

        self.display_image_url = self.get_display_image_url()
        self.was_price = round(float(self.was_price), 2)
        self.now_price = round(float(self.now_price), 2)
        self.promotional_price = round(float(self.promotional_price), 2)
        self.now_price_cohort1 = round(float(self.now_price_cohort1), 2)
        self.now_price_cohort2 = round(float(self.now_price_cohort2), 2)
        self.now_price_cohort3 = round(float(self.now_price_cohort3), 2)
        self.now_price_cohort4 = round(float(self.now_price_cohort4), 2)
        self.now_price_cohort5 = round(float(self.now_price_cohort5), 2)
        self.promotional_price_cohort1 = round(float(self.promotional_price_cohort1), 2)
        self.promotional_price_cohort2 = round(float(self.promotional_price_cohort2), 2)
        self.promotional_price_cohort3 = round(float(self.promotional_price_cohort3), 2)
        self.promotional_price_cohort4 = round(float(self.promotional_price_cohort4), 2)
        self.promotional_price_cohort5 = round(float(self.promotional_price_cohort5), 2)

        super(DealsHubProduct, self).save(*args, **kwargs)


class Section(models.Model):

    uuid = models.CharField(max_length=200, unique=True)
    location_group = models.ForeignKey(LocationGroup, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=300, default="")
    name_ar = models.CharField(max_length=300, default="")
    is_published = models.BooleanField(default=False)
    listing_type = models.CharField(default="Carousel", max_length=200)
    parent_banner = models.ForeignKey('Banner', null=True, blank=True, on_delete=models.CASCADE)

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

        if self.location_group !=None:
            refresh_section_cache(self.location_group.uuid)
        
        if self.pk == None:
            self.created_date = timezone.now()
            self.modified_date = timezone.now()
        else:
            self.modified_date = timezone.now()

        if self.uuid == None or self.uuid == "":
            self.uuid = str(uuid.uuid4())
        
        super(Section, self).save(*args, **kwargs)

    def get_name(self, language="en"):
        if language=="ar" and self.name_ar!="":
            return self.name_ar
        return self.name


class CustomProductSection(models.Model):

    product = models.ForeignKey(DealsHubProduct, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    order_index = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Custom ProductSection"
        verbose_name_plural = "Custom ProductSections"


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
    parent = models.ForeignKey('Banner', null=True, blank=True, on_delete=models.CASCADE)
    is_nested = models.BooleanField(default=False)

    def __str__(self):
        return str(self.uuid)

    def save(self, *args, **kwargs):
        
        if self.location_group !=None:
            refresh_section_cache(self.location_group.uuid)

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
    image_ar = models.ForeignKey(Image, on_delete=models.SET_NULL,related_name="image_ar", null=True)
    mobile_image_ar = models.ForeignKey(Image, related_name="mobile_image_ar", on_delete=models.SET_NULL, null=True)

    products = models.ManyToManyField(DealsHubProduct, blank=True)
    hovering_banner_image = models.ForeignKey(Image, related_name="unit_hovering_banner_image", on_delete=models.SET_NULL, null=True,blank=True)

    promotion = models.ForeignKey(Promotion,null=True,blank=True)

    def __str__(self):
        return str(self.uuid)

    def save(self, *args, **kwargs):

        if self.banner!=None and self.banner.location_group!=None:
            refresh_section_cache(self.banner.location_group.uuid)

        if self.uuid == None or self.uuid=="":
            self.uuid = str(uuid.uuid4())
        
        super(UnitBannerImage, self).save(*args, **kwargs)


class CustomProductUnitBanner(models.Model):

    product = models.ForeignKey(DealsHubProduct, on_delete=models.CASCADE)
    unit_banner = models.ForeignKey(UnitBannerImage, on_delete=models.CASCADE)
    order_index = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Custom ProductUnitBanner"
        verbose_name_plural = "Custom ProductUnitBanners"


class AddressManager(models.Manager):
    
    def get_queryset(self):
        return super(AddressManager, self).get_queryset().exclude(is_deleted=True)


class AddressRecoveryManager(models.Manager):

    def get_queryset(self):
        return super(AddressRecoveryManager, self).get_queryset()


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

    emirates = models.CharField(max_length=100, default="", blank=True)
    neighbourhood = models.CharField(max_length=100, default="", blank=True)

    date_created = models.DateTimeField(auto_now_add=True)

    is_shipping = models.BooleanField(default=True)
    is_billing = models.BooleanField(default=True)

    objects = AddressManager()
    recovery = AddressRecoveryManager()

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

        if Address.objects.filter(user=self.user).count()>100:
            return

        super(Address, self).save(*args, **kwargs)

    def get_country(self):
        return str(self.location_group.location.country)

    def get_shipping_address(self):
        return self.first_name + " " + self.last_name + "\n" + json.loads(self.address_lines)[0] + "\n"+json.loads(self.address_lines)[1] + "\n"+json.loads(self.address_lines)[2] + "\n"+json.loads(self.address_lines)[3] + "\n"+self.state+"\n"+self.neighbourhood+"\n"+self.emirates

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
    reference_medium = models.CharField(max_length=200,default="")
    offline_delivery_fee = models.FloatField(default=0)
    offline_cod_charge = models.FloatField(default=0)
    additional_note = models.TextField(default="", blank=True)

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())

        self.modified_date = timezone.now()
        super(Cart, self).save(*args, **kwargs)

    def get_subtotal(self, offline=False):
        unit_cart_objs = UnitCart.objects.filter(cart=self)
        subtotal = 0
        for unit_cart_obj in unit_cart_objs:
            if offline==True:
                subtotal += float(unit_cart_obj.offline_price)*float(unit_cart_obj.quantity)
            else:
                subtotal += float(unit_cart_obj.product.get_actual_price_for_customer(self.owner))*float(unit_cart_obj.quantity)
        return round(subtotal, 2)

    def get_delivery_fee(self, cod=False, offline=False, calculate=True):
        if calculate==False:
            return self.offline_delivery_fee
        subtotal = self.get_subtotal(offline=offline)
        if subtotal==0:
            return 0
        if (self.location_group.is_voucher_allowed_on_cod==True or cod==False or offline==True) and self.voucher!=None and self.voucher.is_expired()==False and is_voucher_limt_exceeded_for_customer(self.owner, self.voucher)==False:
            if self.voucher.voucher_type=="SD":
                return 0
            subtotal = self.voucher.get_discounted_price(subtotal)
        if subtotal < self.location_group.free_delivery_threshold:
            return round(self.location_group.delivery_fee,2)
        return 0

    def get_cod_charge(self, cod=False, offline=False):
        if cod==False:
            return 0
        return round(float(self.offline_cod_charge),2) if offline==True else round(float(self.location_group.cod_charge),2)

    def get_total_amount(self, cod=False, offline=False, delivery_fee_calculate=True):
        subtotal = self.get_subtotal(offline=offline)
        if subtotal==0:
            return 0
        if (self.location_group.is_voucher_allowed_on_cod==True or cod==False or offline==True) and self.voucher!=None and self.voucher.is_expired()==False and is_voucher_limt_exceeded_for_customer(self.owner, self.voucher)==False:
            subtotal = self.voucher.get_discounted_price(subtotal)
        delivery_fee = self.get_delivery_fee(cod=cod, offline=offline, calculate=delivery_fee_calculate)
        cod_charge = self.get_cod_charge(cod=cod, offline=offline)
        return round(subtotal+delivery_fee+cod_charge, 2)

    def get_vat(self, cod=False, offline=False, delivery_fee_calculate=True):
        total_amount = self.get_total_amount(cod=cod, offline=offline, delivery_fee_calculate=delivery_fee_calculate)
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
    offline_price = models.FloatField(default=0)

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


class OrderRequest(models.Model):

    bundleid = models.CharField(max_length=100,default="")
    owner = models.ForeignKey('DealsHubUser',on_delete = models.CASCADE)
    uuid = models.CharField(max_length = 200,default="")
    date_created = models.DateTimeField(auto_now_add=True)
    shipping_address = models.ForeignKey(Address, null=True, blank=True, on_delete=models.CASCADE)
    payment_mode = models.CharField(max_length=50, default="COD")
    location_group = models.ForeignKey(LocationGroup, null=True, blank=True, on_delete=models.SET_NULL)
    voucher = models.ForeignKey(Voucher, null=True, blank=True, on_delete=models.SET_NULL)
    merchant_reference = models.CharField(max_length=200, default="")
    to_pay = models.FloatField(default=0)
    real_to_pay = models.FloatField(default=0)
    delivery_fee = models.FloatField(default=0)
    cod_charge = models.FloatField(default=0)
    additional_note = models.TextField(default="", blank=True)
    admin_note = models.TextField(default="", blank=True)
    REQUEST_STATUS = (
        ('Approved','Approved'),
        ('Rejected','Rejected'),
        ('Pending','Pending')
        )
    request_status = models.CharField(max_length=50, choices=REQUEST_STATUS, default="Pending")
    is_placed = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())
            if self.bundleid=="":
                order_prefix = ""
                order_cnt = 1
                try:
                    order_prefix = json.loads(self.location_group.website_group.conf)["order_req_prefix"]
                    order_req_cnt = OrderRequest.objects.filter(location_group=self.location_group).count()+1
                except Exception as e:
                    pass
                self.bundleid = order_prefix + "-"+str(order_cnt)+"-"+str(uuid.uuid4())[:5]

        super(OrderRequest, self).save(*args, **kwargs)

    def get_customer_full_name(self):
        return self.shipping_address.first_name + " " + self.shipping_address.last_name

    def get_customer_first_name(self):
        return self.shipping_address.first_name

    def get_date_created(self):
        return str(timezone.localtime(self.date_created).strftime("%d %b, %Y"))

    def get_time_created(self):
        return str(timezone.localtime(self.date_created).strftime("%I:%M %p"))

    def get_currency(self):
        return str(self.location_group.location.currency)

    def get_email_website_logo(self):
        if self.location_group.website_group.footer_logo!=None:
            return self.location_group.website_group.footer_logo.image.url
        if self.location_group.website_group.logo!=None:
            return self.location_group.website_group.logo.image.url
        return ""

    def get_website_link(self):
        return self.location_group.website_group.link

    def get_subtotal(self):
        unit_order_request_objs = UnitOrderRequest.objects.filter(order_request=self).exclude(request_status="Rejected")
        subtotal = 0
        for unit_order_request_obj in unit_order_request_objs:
            subtotal += float(unit_order_request_obj.final_price)*float(unit_order_request_obj.final_quantity)
        return round(subtotal,2)

    def get_delivery_fee(self, cod=False):
        subtotal = self.get_subtotal()
        if subtotal==0:
            return 0
        if (self.location_group.is_voucher_allowed_on_cod==True or cod==False) and self.voucher!=None and self.voucher.is_expired()==False and is_voucher_limt_exceeded_for_customer(self.owner, self.voucher)==False:
            if self.voucher.voucher_type=="SD":
                return 0
            subtotal = self.voucher.get_discounted_price(subtotal)
        if subtotal < self.location_group.free_delivery_threshold:
            return round(self.location_group.delivery_fee, 2)
        return 0

    def get_total_amount(self, cod=False):
        subtotal = self.get_subtotal()
        if subtotal==0:
            return 0
        if (self.location_group.is_voucher_allowed_on_cod==True or cod==False) and self.voucher!=None and self.voucher.is_expired()==False and is_voucher_limt_exceeded_for_customer(self.owner, self.voucher)==False:
            subtotal = self.voucher.get_discounted_price(subtotal)
        delivery_fee = self.get_delivery_fee(cod=cod)
        cod_charge = self.get_cod_charge(cod=cod)
        return round(subtotal+delivery_fee+cod_charge, 2)

    def get_cod_charge(self, cod=False):
        if cod==False:
            return 0
        return float(self.location_group.cod_charge)

    def get_vat(self, cod=False):
        total_amount = self.get_total_amount(cod)
        if self.location_group.vat==0:
            return 0
        vat_divider = 1+(self.location_group.vat/100)
        return round((total_amount - total_amount/vat_divider), 2)

    class Meta:
        verbose_name = "Order Request"
        verbose_name_plural = "Order Requests"


class UnitOrderRequest(models.Model):

    order_request = models.ForeignKey(OrderRequest, on_delete=models.CASCADE)
    uuid = models.CharField(max_length=200,default="")
    product = models.ForeignKey(DealsHubProduct, on_delete=models.CASCADE)
    initial_quantity = models.IntegerField(default=0)
    initial_price = models.FloatField(default=0)
    final_quantity = models.IntegerField(default=0)
    final_price = models.FloatField(default=0)
    date_created = models.DateTimeField(auto_now_add=True)
    order_req_id = models.CharField(max_length=100,default="")

    REQUEST_STATUS = (
        ('Approved','Approved'),
        ('Rejected','Rejected'),
        ('Pending','Pending')
        )
    request_status = models.CharField(max_length=50,choices=REQUEST_STATUS, default="Pending")

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())
            self.final_quantity = self.initial_quantity
            self.final_price = self.initial_price
            order_req_prefix = ""
            try:
                order_req_prefix = json.loads(self.order_request.location_group.website_group.conf)["order_req_prefix"]
            except Exception as e:
                pass
            self.order_req_id = order_req_prefix + str(uuid.uuid4())[:5]

        super(UnitOrderRequest, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "Unit Order Request"
        verbose_name_plural = "Unit Order Requests"        


class Order(models.Model):

    bundleid = models.CharField(max_length=100, default="")
    owner = models.ForeignKey('DealsHubUser', on_delete=models.CASCADE)
    uuid = models.CharField(max_length=200, default="")
    date_created = models.DateTimeField(auto_now_add=True)
    shipping_address = models.ForeignKey(Address, null=True, blank=True, on_delete=models.CASCADE)
    payment_mode = models.CharField(default="COD", max_length=100)
    to_pay = models.FloatField(default=0)
    real_to_pay = models.FloatField(default=0)
    delivery_fee = models.FloatField(default=0)
    cod_charge = models.FloatField(default=0)
    is_order_offline = models.BooleanField(default=False)
    order_placed_date = models.DateTimeField(null=True, default=timezone.now)
    CALL_STATUS = (
        ("Unconfirmed", "Unconfirmed"),
        ("Confirmed", "Confirmed"),
        ("No Response", "No Response")
    )
    call_status = models.CharField(max_length=100, choices=CALL_STATUS, default="Unconfirmed")

    logix_tracking_reference = models.CharField(default="", max_length=100)

    PENDING, PAID = ('cod', 'paid')
    PAYMENT_STATUS = (
        (PENDING, "cod"),
        (PAID, "paid")
    )
    payment_status = models.CharField(max_length=100, choices=PAYMENT_STATUS, default="cod")
    payment_info = models.TextField(default="{}")
    merchant_reference = models.CharField(max_length=200, default="")
    offline_sales_person = models.ForeignKey(OmnyCommUser, on_delete=models.SET_NULL, null=True, default=None)

    postaplus_info = models.TextField(default="{}")
    is_postaplus = models.BooleanField(default=False)

    additional_note = models.TextField(default="", blank=True)
    admin_note = models.TextField(default="",blank=True)
    reference_medium = models.CharField(max_length=200, default="")
    voucher = models.ForeignKey(Voucher,null=True,default=None,blank=True,on_delete=models.SET_NULL)
    location_group = models.ForeignKey(LocationGroup, null=True, blank=True, on_delete=models.SET_NULL)
    cheque_images = models.ManyToManyField(Image, related_name="cheque_images", blank=True)
    cheque_approved = models.BooleanField(default=False)

    sap_final_billing_info = models.TextField(default="{}")
    SAP_STATUS = (
        ("Pending", "Pending"),
        ("In GRN", "In GRN"),
        ("GRN Conflict","GRN Conflict"),
        ("Success", "Success"),
        ("Failed", "Failed"),
        ("Manual", "Manual")
    )
    sap_status = models.CharField(max_length=100, choices=SAP_STATUS, default="Pending")

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())
            if self.bundleid=="":
                order_prefix = ""
                order_cnt = 1
                try:
                    order_prefix = json.loads(self.location_group.website_group.conf)["order_prefix"]
                    order_cnt = Order.objects.filter(location_group=self.location_group).count()+1
                except Exception as e:
                    pass
                self.bundleid = order_prefix + "-"+str(order_cnt)+"-"+str(uuid.uuid4())[:5]

        super(Order, self).save(*args, **kwargs)

    def get_date_created(self):
        return str(timezone.localtime(self.order_placed_date).strftime("%d %b, %Y"))

    def get_time_created(self):
        return str(timezone.localtime(self.order_placed_date).strftime("%I:%M %p"))

    def get_currency(self):
        return str(self.location_group.location.currency)

    def get_subtotal(self, is_real=False):
        unit_order_objs = UnitOrder.objects.filter(order=self)
        if is_real==True:
            unit_order_objs = unit_order_objs.exclude(current_status_admin="cancelled")
        subtotal = 0
        for unit_order_obj in unit_order_objs:
            subtotal += float(unit_order_obj.price)*float(unit_order_obj.quantity)
        return round(subtotal, 2)

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

    def get_delivery_fee_update(self, cod=False, offline=False):
        subtotal = self.get_subtotal()
        if subtotal==0:
            return 0
        if self.voucher!=None:
            if self.voucher.voucher_type=="SD":
                return 0
            subtotal = self.voucher.get_discounted_price(subtotal)

        if subtotal < self.location_group.free_delivery_threshold:
            return self.location_group.delivery_fee
        return 0

    def get_delivery_fee(self):
        return self.delivery_fee

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
        return self.cod_charge

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

    def get_total_amount(self, is_real=False):
        subtotal = self.get_subtotal(is_real)
        if subtotal==0:
            return 0
        if self.voucher!=None:
            subtotal = self.voucher.get_discounted_price(subtotal)
        delivery_fee = self.get_delivery_fee()
        cod_charge = self.get_cod_charge()
        return round(subtotal+delivery_fee+cod_charge, 2)

    def get_vat(self, is_real=False):
        total_amount = self.get_total_amount(is_real=is_real)
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

    def get_customer_id_for_final_sap_billing(self):
        shipping_method = UnitOrder.objects.filter(order=self)[0].shipping_method.lower()
        if shipping_method=="wig fleet" and self.payment_status.lower()=="cod":
            return CUSTOMER_ID_FINAL_BILLING_WIG_COD
        if shipping_method=="wig fleet" and self.payment_status.lower()=="paid":
            return CUSTOMER_ID_FINAL_BILLING_WIG_ONLINE
        if shipping_method=="grand gaadi" and self.payment_status.lower()=="cod":
            return CUSTOMER_ID_FINAL_BILLING_GRAND_GAADI_COD
        if shipping_method=="grand gaadi" and self.payment_status.lower()=="paid":
            return CUSTOMER_ID_FINAL_BILLING_GRAND_GAADI_ONLINE
        if shipping_method=="sendex" and self.payment_status.lower()=="cod":
            return CUSTOMER_ID_FINAL_BILLING_SENDEX_COD
        if shipping_method=="sendex" and self.payment_status.lower()=="paid":
            return CUSTOMER_ID_FINAL_BILLING_SENDEX_ONLINE
        if shipping_method=="standard" and self.payment_status.lower()=="cod":
            return CUSTOMER_ID_FINAL_BILLING_STANDARD_COD
        if shipping_method=="standard" and self.payment_status.lower()=="paid":
            return CUSTOMER_ID_FINAL_BILLING_STANDARD_ONLINE

    def get_total_quantity(self):
        total_quantity = 0
        unit_order_objs = UnitOrder.objects.filter(order=self).exclude(current_status_admin="cancelled")
        for unit_order_obj in unit_order_objs:
            total_quantity += unit_order_obj.quantity
        return total_quantity


class UnitOrder(models.Model):

    orderid = models.CharField(max_length=100, default="")
    CURRENT_STATUS = (
        ("ordered", "ordered"),
        ("shipped", "shipped"),
        ("intransit", "intransit"),
        ("delivered", "delivered"),
        ("cancelled", "cancelled"),
        ("returned", "returned")
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
        ("returned", "returned")
    )
    current_status_admin = models.CharField(max_length=100, choices=CURRENT_STATUS_ADMIN, default="pending")

    cancelling_note = models.TextField(default="")

    SHIPPING_METHOD = (
        ("pending", "pending"),
        ("WIG Fleet", "WIG Fleet"),
        ("TFM", "TFM")
    )
    shipping_method = models.CharField(max_length=100, choices=SHIPPING_METHOD, default="pending")

    cancelled_by_user = models.BooleanField(default=False)
    cancellation_request_action_taken = models.BooleanField(default=False)
    user_cancellation_note = models.CharField(max_length=255,default="")
    user_cancellation_status = models.CharField(max_length=100,default="")

    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(DealsHubProduct, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    price = models.FloatField(default=None, null=True, blank=True)
    uuid = models.CharField(max_length=200, default="")

    sap_intercompany_info = models.TextField(default="{}")
    order_information = models.TextField(default="{}")
    SAP_STATUS = (
        ("Pending", "Pending"),
        ("In GRN", "In GRN"),
        ("GRN Done", "GRN Done"),
        ("GRN Conflict", "GRN Conflict"),
        ("Failed", "Failed")
    )
    sap_status = models.CharField(max_length=100, choices=SAP_STATUS, default="Pending")
    grn_filename = models.CharField(max_length=100, default="")
    grn_filename_exists = models.BooleanField(default=False)

    def get_subtotal(self):
        return round(float(self.price)*float(self.quantity), 2)

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

    def get_subtotal_without_vat_custom_qty(self, qty):
        temp_total = float(self.price)*float(qty)
        vat_divider = 1 + (self.order.location_group.vat/100)
        return round(temp_total/vat_divider, 2)

    def get_sap_intercompany_order_qty(self):
        try:
            intercompany_sales_info = json.loads(self.order_information)["intercompany_sales_info"]
            qty = float(intercompany_sales_info["qty"])
            return qty
        except Exception as e:
            return ""

    def get_sap_final_order_qty(self):
        try:
            final_billing_info = json.loads(self.order_information)["final_billing_info"]
            qty = float(final_billing_info["qty"])
            return qty
        except Exception as e:
            return ""

    def get_sap_intercompany_order_id(self):
        try:
            intercompany_sales_info = json.loads(self.order_information)["intercompany_sales_info"]
            order_id = intercompany_sales_info["order_id"]
            return order_id
        except Exception as e:
            return ""

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
        ("cancelled", "cancelled"),
        ("returned", "returned")
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
        ("returned", "returned")
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


class VersionOrder(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    uuid = models.CharField(max_length=200, default="")
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(OmnyCommUser, on_delete=models.SET_NULL, null=True)
    change_information = models.TextField(default="{}")

    def __str__(self):
        return str(self.uuid)

    def save(self, *args, **kwargs):

        if self.pk == None or self.uuid=="":
            self.uuid = str(uuid.uuid4())

        super(VersionOrder, self).save(*args, **kwargs)

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
    additional_note = models.TextField(default="", blank=True)

    def save(self, *args, **kwargs):
        if self.pk == None:
            self.uuid = str(uuid.uuid4())

        self.modified_date = timezone.now()
        super(FastCart, self).save(*args, **kwargs)

    def get_subtotal(self):
        subtotal = float(self.product.get_actual_price_for_customer(self.owner))*float(self.quantity)
        return round(subtotal, 2)

    def get_delivery_fee(self, cod=False):
        subtotal = self.get_subtotal()
        if subtotal==0:
            return 0
        if (self.location_group.is_voucher_allowed_on_cod==True or cod==False) and self.voucher!=None and self.voucher.is_expired()==False and is_voucher_limt_exceeded_for_customer(self.owner, self.voucher)==False:
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
        if (self.location_group.is_voucher_allowed_on_cod==True or cod==False) and self.voucher!=None and self.voucher.is_expired()==False and is_voucher_limt_exceeded_for_customer(self.owner, self.voucher)==False:
            subtotal = self.voucher.get_discounted_price(subtotal)
        delivery_fee = self.get_delivery_fee(cod)
        if cod==True:
            subtotal += self.location_group.cod_charge
        return round(subtotal+delivery_fee, 2)

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
    otp_attempts = models.IntegerField(default=0)
    user_token = models.CharField(default="", max_length=200)

    class Meta:
        verbose_name = "DealsHubUser"
        verbose_name_plural = "DealsHubUser"

    def save(self, *args, **kwargs):

        if self.pk == None:
            self.date_created = timezone.now()
        
        super(DealsHubUser, self).save(*args, **kwargs)


class B2BUser(DealsHubUser):
    company_name = models.CharField(default="None",max_length=250)
    interested_categories = models.ManyToManyField(Category,blank = True)
    vat_certificate = models.FileField(upload_to = 'vat_certificate',null=True, blank=True)
    trade_license = models.FileField(upload_to = 'trade_license',null=True,blank=True)
    passport_copy = models.FileField(upload_to = 'passport_copy',null=True,blank=True)
    vat_certificate_images = models.ManyToManyField(Image, related_name="vat_certificate_images", blank=True)
    trade_license_images = models.ManyToManyField(Image, related_name="trade_license_images", blank=True)
    passport_copy_images = models.ManyToManyField(Image, related_name="passport_copy_images", blank=True)
    vat_certificate_id = models.CharField(default="",max_length=250)
    trade_license_id = models.CharField(default="",max_length=250)
    passport_copy_id = models.CharField(default="",max_length=250)

    STATUS_OPTIONS = (
        ('Pending','Pending'),
        ('Approved','Approved'),
        ('Rejected','Rejected'),
    )

    vat_certificate_status = models.CharField(max_length=30, choices=STATUS_OPTIONS,default='Pending')
    trade_license_status = models.CharField(max_length=30, choices=STATUS_OPTIONS, default='Pending')
    passport_copy_status = models.CharField(max_length=30, choices=STATUS_OPTIONS, default='Pending')
    is_signup_completed = models.BooleanField(default=False)

    cohort = models.CharField(max_length=50, default="",blank=True)
    conf = models.TextField(default = "{}")

    class Meta:
        verbose_name = "B2BUser"

    def save(self,*args,**kwargs):
        super(B2BUser,self).save(*args,**kwargs)


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


class ReviewManager(models.Manager):
    
    def get_queryset(self):
        return super(ReviewManager, self).get_queryset().exclude(is_deleted=True)


class ReviewRecoveryManager(models.Manager):

    def get_queryset(self):
        return super(ReviewRecoveryManager, self).get_queryset()


class Review(models.Model):

    uuid = models.CharField(max_length=200, unique=True)
    dealshub_user = models.ForeignKey(DealsHubUser, null=True, default=None, on_delete=models.CASCADE)
    product = models.ForeignKey(DealsHubProduct, on_delete=models.CASCADE)
    rating = models.IntegerField(default=0)
    content = models.ForeignKey(ReviewContent, default=None, null=True, blank=True,on_delete=models.SET_DEFAULT)
    created_date = models.DateTimeField(default=timezone.now, blank=True)
    modified_date = models.DateTimeField(null=True, blank=True)

    is_deleted = models.BooleanField(default=False)
    is_fake = models.BooleanField(default=False)
    fake_oc_user = models.ForeignKey(OmnyCommUser, default=None, null=True, on_delete=models.SET_NULL)
    fake_customer_name = models.CharField(max_length=200, default="")
    is_published = models.BooleanField(default=True)

    objects = ReviewManager()
    recovery = ReviewRecoveryManager()

    def __str__(self):
        return str(self.uuid)

    def save(self, *args, **kwargs):

        # if self.pk == None:
        #     self.created_date = timezone.now()
        #     self.modified_date = timezone.now()
        # else:
        #     self.modified_date = timezone.now()
        self.modified_date = timezone.now()
        if self.uuid == None or self.uuid=="":
            self.uuid = str(uuid.uuid4())

        super(Review, self).save(*args, **kwargs)


class BlogPost(models.Model):

    title = models.TextField(default="",blank=True)
    headline = models.CharField(max_length=255,default="",blank=True)
    author = models.CharField(max_length=200,default="",blank=True)
    body = models.TextField(default="")
    date_created = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False)
    cover_image = models.ForeignKey(Image,null=True,blank=True,related_name="cover_image")
    blog_images = models.ManyToManyField(Image,blank=True,related_name="blog_images")
    uuid = models.CharField(max_length=200,unique=True)
    views = models.IntegerField(default=0)
    location_group = models.ForeignKey(LocationGroup,null=True, blank=True,on_delete=models.SET_NULL)
    products = models.ManyToManyField(DealsHubProduct,blank=True,related_name='products')

    def __str__(self):
        return str(self.title)

    def get_cover_image(self):
        if self.cover_image!=None and self.cover_image!="":
            return self.cover_image.image.url
        return ""

    def get_publish_date(self):
        return str(timezone.localtime(self.date_created).strftime("%d %b, %Y"))

    def save(self, *args, **kwargs):
        if self.uuid==None or self.uuid == "":
            self.uuid = str(uuid.uuid4())[:8]

        super(BlogPost,self).save(*args,**kwargs)


class BlogSectionType(models.Model):

    name = models.CharField(max_length=200,unique=True,default="")
    display_name = models.CharField(max_length=200,default="")
    limit = models.IntegerField(default=5)

    def __str__(self):
        return str(self.name)


class BlogSection(models.Model):

    name = models.CharField(max_length=200,blank=True,default="")
    blog_posts = models.ManyToManyField(BlogPost, blank=True)
    is_published = models.BooleanField(default=False)
    order_index = models.IntegerField(default=1)
    uuid = models.CharField(max_length=200,unique=True)
    date_created = models.DateTimeField()
    modified_date = models.DateTimeField()
    blog_section_type = models.ForeignKey(BlogSectionType,on_delete=models.CASCADE)
    section_image = models.ForeignKey(Image,null=True,blank=True)
    location_group = models.ForeignKey(LocationGroup,null=True, blank=True,on_delete=models.SET_NULL)

    def save(self, *args, **kwargs):
        if self.pk==None:
            self.uuid = str(uuid.uuid4())
            self.date_created = timezone.now()
            self.modified_date = timezone.now()
        else:
            self.modified_date = timezone.now()

        super(BlogSection,self).save(*args,**kwargs)

