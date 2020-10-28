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

SERVER_TOKEN = "AAAARH4JrjU:APA91bEi1uAlKWWMNnX7pCwXs2RBoAnLahZ0MAT92jOp80lE25Cbjn03iXHxNZeNvuMlYZYYKjXtmw21rz8IJEEGYHUS8khTiNzUgn61x_HFBQM78Q9QUNismYfmsc8B8WVrWRkTlX8S"

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
	message_subtitle = notification_info["subtitle"]
	message_body = notification_info["body"]
	message_image = notification_info["image"]
	
	headers = {
	        'Content-Type': 'application/json',
	        'Authorization': 'key=' + SERVER_TOKEN,
	      }

	body = {
	          'notification': {
	          					"title": "Sample Title for notification -OmnyComm 5",
	                            "subtitle" : "Sampe Subtitle for notification - OmnyComm 5",
	                            "body" : "Sampe Body for notification - OmnyComm 5",
	                            "image" : "https://cdn.omnycomm.com/l.jpeg"
	                            },
	          'registration_ids':
	              registration_ids,
	          'priority': 'high',
	        #   'data': dataPayLoad,
	        }
	response = requests.post("https://fcm.googleapis.com/fcm/send",headers = headers, data=json.dumps(body))

	return response