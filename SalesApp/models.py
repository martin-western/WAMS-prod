from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

import logging
import json
import uuid

from WAMSApp.models import *
from SalesApp.utils import *
from django.core.cache import cache

logger = logging.getLogger(__name__)

class SalesAppUser(User):

    customer_id = models.CharField(max_length=200,blank=True,null=True)
    fcm_id_list = models.TextField(default="")
    contact_number = models.CharField(max_length=200, default="",blank=True,null=True)
    country = models.CharField(max_length=200, default="",blank=True,null=True)
    favourite_products = models.ManyToManyField(Product,blank=True)
    
    def save(self, *args, **kwargs):
        
        if self.pk == None:
            self.set_password(self.password)
            self.customer_id = str(uuid.uuid4()).split("-")[0]
        
        super(SalesAppUser, self).save(*args, **kwargs)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "SalesAppUser"
        verbose_name_plural = "SalesAppUsers"

class Notification(models.Model):

    notification_id = models.CharField(max_length=200,blank=True,null=True)
    title = models.CharField(max_length=200,unique=True)
    subtitle = models.CharField(max_length=200, default="",blank=True,null=True)
    body = models.CharField(max_length=200)
    expiry_date = models.DateTimeField()
    image = models.ForeignKey(Image, null=True, blank=True, on_delete=models.CASCADE)
    STATUS = (
        ("Pending", "Pending"),
        ("Sent", "Sent"),
        ("Failed", "Failed")
    )
    status = models.CharField(max_length=100, choices=SAP_STATUS, default="Pending")
    
    def save(self, *args, **kwargs):
        
        if self.pk == None:
            self.notification_id = str(uuid.uuid4()).split("-")[0]
        
        super(Notification, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def get_image_url(self):
        cached_url = cache.get("main_url_"+str(self.uuid), "has_expired")
        if cached_url!="has_expired":
            return cached_url
        main_images_list = ImageBucket.objects.none()
        main_images_objs = MainImages.objects.filter(product=self)
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
