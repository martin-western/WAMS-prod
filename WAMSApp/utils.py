from WAMSApp.models import *
import csv
import urllib
import os
from django.core.files import File
from WAMSApp.core_utils import *
from WAMSApp.amazon_uk import *
from WAMSApp.amazon_uae import *
from WAMSApp.ebay import *
from WAMSApp.noon import *
from WAMSApp.serializers import UserSerializer


def my_jwt_response_handler(token, user=None, request=None):
    return {
        'token': token,
        'user': UserSerializer(user, context={'request': request}).data
    }

def compress(image_path):
    
    try:
        im = IMAGE.open(image_path)
        basewidth = 1024
        wpercent = (basewidth / float(im.size[0]))
        hsize = int((float(im.size[1]) * float(wpercent)))
        im = im.resize((basewidth, hsize), IMAGE.ANTIALIAS)
        im.save(image_path, optimize=True, quality=100)
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("compress image: %s at %s", e, str(exc_tb.tb_lineno))

def convert_to_ascii(s):
    
    s = s.replace(u'\u2013', "-").replace(u'\u2019', "'").replace(u'\u2018', "'").replace(u'\u201d','"').replace(u'\u201c','"')
    s = s.encode("ascii", "ignore")
    return s

def has_atleast_one_image(prod_obj):
    
    check = False
    images_count = 0

    main_images_objs = MainImages.objects.filter(product=prod_obj)
    for main_images_obj in main_images_objs:
        images_count += main_images_obj.main_images.all().count()

    sub_images_objs = SubImages.objects.filter(product=prod_obj)
    for sub_images_obj in sub_images_objs:
        images_count += sub_images_obj.sub_images.all().count()

    images_count += prod_obj.white_background_images.all().count()
    images_count += prod_obj.lifestyle_images.all().count()
    
    if(images_count>0):
        check=True
    return check

def get_file_extension(file_name, decoded_file):

        extension = imghdr.what(file_name, decoded_file)
        extension = "jpg" if extension == "jpeg" else extension

        return extension

def decode_base64_file(data):

    if isinstance(data, six.string_types):
        if 'data:' in data and ';base64,' in data:
            header, data = data.split(';base64,')

        try:
            decoded_file = base64.b64decode(data)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error Invalid Image : %s at %s", e, str(exc_tb.tb_lineno))
                
        file_name = str(uuid.uuid4())[:12]
        file_extension = get_file_extension(file_name, decoded_file)

        complete_file_name = "%s.%s" % (file_name, file_extension, )

        return ContentFile(decoded_file, name=complete_file_name)
