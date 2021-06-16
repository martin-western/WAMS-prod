from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

import logging
import json
import uuid
import datetime

from WAMSApp.models import *
from SalesApp.utils import *
from django.core.cache import cache

logger = logging.getLogger(__name__)

class SalesAppUser(User):

    customer_id = models.CharField(max_length=200,blank=True,null=True)
    fcm_id = models.TextField(default="")
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
    expiry_date = models.DateTimeField(null=True,blank=True)
    image = models.ForeignKey(Image, null=True, blank=True, on_delete=models.CASCADE)
    STATUS = (
        ("Pending", "Pending"),
        ("Sent", "Sent"),
        ("Failed", "Failed")
    )
    status = models.CharField(max_length=100, choices=STATUS, default="Pending")
    
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
        
        image_url = ""

        try:
            image_url = self.image.mid_image.url
        except Exception as e:
            try:
                image_url = self.image.image.url
            except Exception as e:
                image_url = ""
        
        return image_url

    def get_expiry_date(self):
        
        expiry_date = self.expiry_date
        
        if expiry_date != "" and expiry_date != None:
            expiry_date = str(timezone.localtime(self.expiry_date).strftime("%d %b, %Y %I:%M %p"))
            return expiry_date

        return ""

