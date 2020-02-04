from django.db import models
from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

# from WAMSApp.utils import *

from django.db.models.signals import pre_delete

from PIL import Image as IMAGE
#import StringIO
import logging
import sys
import json
import uuid


from WAMSApp.models import Product
from dealshub.synchronization import *

logger = logging.getLogger(__name__)


class Category(models.Model):
    name = models.CharField(max_length=256, blank=True, default='')
    description = models.CharField(max_length=256, blank=True, default='')
    category_id = models.CharField(max_length=256, blank=True, default='')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"


class SubCategory(models.Model):
    category = models.ForeignKey(
        Category, related_name="sub_categories", blank=True, default='', on_delete=models.CASCADE)
    name = models.CharField(max_length=256, blank=True, default='')
    desription = models.CharField(max_length=256, blank=True, default='')
    sub_category_id = models.CharField(max_length=256, blank=True, default='')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Sub-category"
        verbose_name_plural = "Sub Categories"


class Property(models.Model):
    subcategory = models.ForeignKey(
        SubCategory, blank=True, default="" , on_delete=models.CASCADE, related_name='properties')
    label = models.CharField(max_length=256, blank=True, default='')
    description = models.CharField(max_length=256, blank=True, default='')

    def __str__(self):
        return self.label

    class Meta:
        verbose_name = "Property"
        verbose_name_plural = "Properties"


class PossibleValues(models.Model):
    prop = models.ForeignKey(Property, blank=True,
                             default='', on_delete=models.CASCADE)
    name = models.CharField(max_length=256, blank=True, default='')
    lable = models.CharField(max_length=256, blank=True, default='')
    value = models.CharField(max_length=256, blank=True, default='')
    unit = models.CharField(max_length=256, blank=True, default='')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Possible Value"
        verbose_name_plural = "Possible Values"


class DealsHubProduct(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, blank=True,null=True)
    sub_category = models.ForeignKey(
        SubCategory, on_delete=models.CASCADE, blank=True, null=True)
    properties = models.TextField(null=True, blank=True, default="")

    class Meta:
        verbose_name = "DealsHub Product"
        verbose_name_plural = "DealsHub Products"

    def save(self, *args, **kwargs):

        # write synchroization call here
        #add_product_in_dealshub(self.product.uuid)
        """
        properties = self.sub_category.properties.all()
        temp_dict = {}
        for property in properties:
            key = str(property.label)
            temp_dict[key] = ""
        self.properties = json.dumps(temp_dict)
        """
        super(DealsHubProduct, self).save(*args, **kwargs)
        

@receiver(pre_delete, sender=DealsHubProduct)
def update_dealshub_product_table(sender, instance, **kwargs):
    #success = delete_product_in_dealshub(instance.product.uuid)
    pass
