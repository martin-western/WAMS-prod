from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.db import models
from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

# from WAMSApp.models_sourcing import *

from PIL import Image as IMAGE
#from io import BytesIO as StringIO
from io import BytesIO
import logging
import sys
import json
import uuid

logger = logging.getLogger(__name__)






































































































