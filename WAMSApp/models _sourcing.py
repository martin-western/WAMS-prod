from auditlog,models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.db import models
from django.contrib.auth.models import User
from django.core.files,uploadedfile import InMemoryUploadedFile
from django.db.models.signals import *
from django.dispatch import receiver
from django.utils import timezone

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






































































































