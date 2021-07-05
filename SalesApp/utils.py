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

SERVER_TOKEN = "AAAAW2sMgmc:APA91bEAA0ee0EBOvBZo8u3HfPC5NVAhlJLF8duV9rvpah522XK42HW5kPaO2cltOHoVW3AT4vAWY_0W_1CYRYYto5tepjXVVHnOODTMVj_ipQHLlEoAzPmGIalLuY5Vfr94cxS7KQLT"

def convert_to_ascii(s):
    
    s = s.replace(u'\u2013', "-").replace(u'\u2019', "'").replace(u'\u2018', "'").replace(u'\u201d','"').replace(u'\u201c','"')
    s = s.encode("ascii", "ignore")
    
    return s

def convert_to_datetime(date_str):
    date_str = date_str[:-1] + "+0400"
    return date_str

def send_firebase_notifications(fcm_ids,notification_info):

	try :
		
		message_title = notification_info["title"]
		message_subtitle = notification_info["subtitle"]
		message_body = notification_info["body"]
		message_image = notification_info["image"]
		
		headers = {
		        'Content-Type': 'application/json',
		        'Authorization': 'key=' + SERVER_TOKEN,
		      }

		body = {
		          'notification': {
		          					"title": message_title,
		                            "subtitle" : message_subtitle,
		                            "body" : message_body,
		                            "image" : message_image
		                            },
		          'registration_ids':
		              fcm_ids,
		          'priority': 'high'
		        #   'data': dataPayLoad,
		        }
		response = requests.post("https://fcm.googleapis.com/fcm/send",headers = headers, data=json.dumps(body), timeout=10)

		return response

	except Exception as e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		logger.error("send_firebase_notifications: %s at %s", e, str(exc_tb.tb_lineno))
		return []