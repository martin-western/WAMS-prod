from WAMSApp.models import *
from SalesApp.constants import *

import datetime
from django.utils import timezone

import hashlib
import random
import sys
import logging
import os
import json
import requests
import xlsxwriter
import threading

from django.core.mail import send_mail, get_connection
from django.core.mail import EmailMultiAlternatives
from django.core.mail import EmailMessage
from django.template import loader

logger = logging.getLogger(__name__)

