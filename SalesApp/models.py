from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

import logging
import json
import uuid

from PIL import Image as IMAGE
from PIL import ExifTags
from io import BytesIO
from bs4 import BeautifulSoup

from WAMSApp.models import *
from SalesApp.utils import *
from django.core.cache import cache

logger = logging.getLogger(__name__)

class Notification(models.Model):
	
    image = models.ForeignKey('wamsapp.image', null=True, blank=True, on_delete=models.CASCADE)
    uuid = models.CharField(max_length=200, default="",blank=True,null=True)
    title = models.CharField(max_length=200, default="",blank=True,null=True)
    message = models.CharField(max_length=200, default="",blank=True,null=True)
    
    def save(self, *args, **kwargs):
        
        if self.pk == None:
            self.uuid = uuid.uuid4()
        
        super(Notification, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

class SalesAppUser(User):

    image = models.ForeignKey('wamsapp.image', null=True, blank=True, on_delete=models.CASCADE)
    customer_id = models.CharField(max_length=200, default="",blank=True,null=True)
    first_name = models.CharField(max_length=200, default="",blank=True,null=True)
    last_name = models.CharField(max_length=200, default="",blank=True,null=True)
    email_id = models.CharField(max_length=200, default="",blank=True,null=True)
    contact_number = models.CharField(max_length=200, default="",blank=True,null=True)
    country = models.CharField(max_length=200, default="",blank=True,null=True)
    favourite_products = models.ManyToManyField('wamsapp.product',blank=True)
    notifications = models.ManyToManyField(Notification,blank=True)
    
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