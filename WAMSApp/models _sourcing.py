from auditlog,models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.db import models
from django.contrib.auth.models import User
from django.core.files,uploadedfile import InMemoryUploadedFile
from django.db.models.signals import *
from django.dispatch import receiver
from django.utils import timezone

from WAMSApp.models import *
from PIL import Image as IMAGE
from io import BytesIO
import logging
import sys
import json
import uuid

logger = logging.getLogger(__name__)

class SourcingUserProduct(object):
    
    is_pr_ready = models.BooleanField(default=False)
    go_live = models.BooleanField(default=False)
    size = models.CharField(max_length=300, null=True, blank=True)
    weight = models.CharField(max_length=300, null=True, blank=True)
    weight_metric = models.CharField(max_length=300, null=True, blank=True)
    design = models.CharField(max_length=300, null=True, blank=True)
    pkg_inner = models.CharField(max_length=300, null=True, blank=True)
    pkg_m_ctn = models.CharField(max_length=300, null=True, blank=True)
    p_ctn_cbm = models.CharField(max_length=300, null=True, blank=True)
    ttl_ctn = models.CharField(max_length=300, null=True, blank=True)
    ttl_cbm = models.CharField(max_length=300, null=True, blank=True)
    ship_lot_number = models.CharField(max_length=300, null=True, blank=True)
    giftbox_die_cut = models.CharField(max_length=300, null=True, blank=True)
    spare_part_name = models.CharField(max_length=300, null=True, blank=True)
    spare_part_qty = models.IntegerField(null=True)
    delivery_days = models.IntegerField(default=0, null=True)
    
    class Meta:
        verbose_name = "SourcingUserProduct"
        verbose_name_plural = "SourcingUserProducts"

class Bank(models.Model): ### As it is in WAMS

    name = models.CharField(max_length=300, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    account_number = models.CharField(max_length=300, null=True, blank=True)
    ifsc_code = models.CharField(max_length=300, null=True, blank=True)
    swift_code = models.CharField(max_length=300, null=True, blank=True)
    branch_code = models.CharField(max_length=300, null=True, blank=True)

    class Meta:
        verbose_name = "Bank"
        verbose_name_plural = "Banks"

    def __str__(self):
        return str(self.name)

    def save(self, *args, **kwargs):
        super(Bank, self).save(*args, **kwargs)


class Factory(models.Model):  ### As it is in WAMS

    business_card = models.ForeignKey(Image, null=True, blank=True, on_delete=models.SET_NULL, related_name="business_card")
    phone_numbers = models.ManyToManyField(PhoneNumber, blank=True)
    factory_emailid = models.CharField(max_length=300, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    operating_hours = models.ManyToManyField(OperatingHour, blank=True)
    bank_details = models.ForeignKey(Bank, null=True, blank=True, on_delete=models.SET_NULL, related_name="related_factory")
    average_delivery_days = models.IntegerField(null=True, blank=True)
    average_turn_around_time = models.IntegerField(null=True, blank=True)
    logo = models.ForeignKey(Image, null=True, blank=True, on_delete=models.SET_NULL)
    contact_person_name = models.CharField(max_length=300, null=True, blank=True)
    contact_person_emailid = models.CharField(max_length=300, null=True, blank=True)
    contact_person_mobile_no = models.CharField(max_length=300, null=True, blank=True)
    social_media_tag = models.CharField(max_length=300, null=True, blank=True)
    social_media_tag_information = models.CharField(max_length=300, null=True, blank=True)
    loading_port = models.CharField(max_length=300, null=True, blank=True)
    location = models.CharField(max_length=300, null=True, blank=True)
    created_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "BaseFactory"
        verbose_name_plural = "BaseFactories"


class ProformaInvoice(models.Model): #### As it is in WAMS
    products = models.ManyToManyField(SourcingUserProduct, blank=True)
    proforma_pdf = models.FileField(blank=True, null=True, default=None)
    payment_terms = models.CharField(max_length=500, null=True, blank=True)
    advance = models.CharField(max_length=500, default='adv', blank=True)
    inco_terms = models.CharField(max_length=500, default="", blank=True)
    ttl_cntrs = models.CharField(max_length=500, default="", blank=True)
    delivery_terms = models.CharField(max_length=500, default="", blank=True)
    factory = models.ForeignKey(
        SourcingUserFactory, null=True, blank=True, on_delete=models.SET_NULL)
    created_date = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = "Proforma Invoice"
        verbose_name_plural = "Proforma Invoices"


class DraftProformaInvoice(models.Model): ### As it is in WAMS
    lines = models.CharField(max_length=500, default="", blank=True)
    created_date = models.DateTimeField(auto_now=True, null=True, blank=True)   

    class Meta:
        verbose_name = "Draft Proforma Invoice"
        verbose_name_plural = "Draft Proforma Invoices"


class DraftProformaInvoiceLine(models.Model): ### As it is in WAMS
    sourcing_user_product = models.ForeignKey(
        SourcingUserProduct, null=True, blank=True, on_delete=models.SET_NULL, related_name='sourcing_user_products')
    sourcing_user_factory = models.ForeignKey(
        SourcingUserFactory, blank=True, null=True, on_delete=models.SET_NULL, related_name='sourcing_user_factory')
    quantity = models.CharField(max_length=500, default="", blank=True)
    draft_proforma_invoice = models.ForeignKey(
        DraftProformaInvoice, null=True, blank=True, on_delete=models.SET_NULL, related_name='sourcing_user_products')

    class Meta:
        verbose_name = "Draft Proforma Invoice Line"
        verbose_name_plural = "Draft Proforma Invoice Lines"






































































































