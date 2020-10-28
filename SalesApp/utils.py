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

def convert_to_ascii(s):
    
    s = s.replace(u'\u2013', "-").replace(u'\u2019', "'").replace(u'\u2018', "'").replace(u'\u201d','"').replace(u'\u201c','"')
    s = s.encode("ascii", "ignore")
    
    return s

def convert_to_datetime(date_str):
    date_str = date_str[:-1] + "+0400"
    return date_str

def send_firebase_notifications(fcm_ids,notification_info):

	registration_ids = fcm_ids
	message_title = notification_info["title"]
	message_body = "Hope you're having fun this weekend, don't forget to check today's news"
	result = push_service.notify_multiple_devices(registration_ids=registration_ids, message_title=message_title, message_body=message_body)

	print(result)