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


from WAMSApp.models import Product, Image, Organization, Category, SubCategory
from dealshub.synchronization import *

logger = logging.getLogger(__name__)


class DealsHubProduct(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=True)
    was_price = models.FloatField(default=0)
    now_price = models.FloatField(default=0)
    properties = models.TextField(null=True, blank=True, default="{}")
    is_published = models.BooleanField(default=False)

    class Meta:
        verbose_name = "DealsHub Product"
        verbose_name_plural = "DealsHub Products"

    def __str__(self):
        return str(self.product)
        

class Section(models.Model):

    uuid = models.CharField(max_length=200, unique=True)
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=300, default="")
    is_published = models.BooleanField(default=False)
    listing_type = models.CharField(default="Carousel", max_length=200)
    products = models.ManyToManyField(Product, blank=True)
    created_date = models.DateTimeField()
    modified_date = models.DateTimeField() 
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
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return str(self.name)


class Banner(models.Model):

    uuid = models.CharField(max_length=200, unique=True)
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL)
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
    http_link = models.TextField(default="")
    banner = models.ForeignKey(Banner, on_delete=models.CASCADE)

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
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=200, default="")
    categories = models.ManyToManyField(Category, blank=True)
    image_links = models.ManyToManyField(ImageLink, blank=True)

    def __str__(self):
        return str(self.organization)

    def save(self, *args, **kwargs):
        
        if self.uuid == None or self.uuid=="":
            self.uuid = str(uuid.uuid4())
        
        super(DealsHubHeading, self).save(*args, **kwargs)