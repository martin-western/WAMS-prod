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

    customer_id = models.CharField(max_length=200, default="",blank=True,null=True)
    fcm_id = models.TextField(default="{}")
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