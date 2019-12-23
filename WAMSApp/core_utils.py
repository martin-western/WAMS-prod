from WAMSApp.models import *

from django.core.files.base import ContentFile

from PIL import Image as IMAGE

import logging
import sys
import imghdr
import base64
import six
import uuid   

logger = logging.getLogger(__name__)

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
    images_count = prod_obj.main_images.all().count() + prod_obj.sub_images.all().count()
    images_count += prod_obj.white_background_images.all().count()
    images_count += prod_obj.lifestyle_images.all().count()
    if(images_count>0):
        check=True
    return check

def custom_permission_filter_products(user):

    try:
        permission_obj = CustomPermission.objects.get(user__username=user.username)
        brands = permission_obj.brands.all()
        product_objs = Product.objects.filter(brand__in=brands)
        return product_objs
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("custom_permission_filter_products: %s at %s", e, str(exc_tb.tb_lineno))
        return []


def custom_permission_filter_brands(user):

    try:
        permission_obj = CustomPermission.objects.get(user__username=user.username)
        brands = permission_obj.brands.all()
        return brands
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("custom_permission_filter_brands: %s at %s", e, str(exc_tb.tb_lineno))
        return []

def custom_permission_filter_channels(user):

    try:
        permission_obj = CustomPermission.objects.get(user__username=user.username)
        channels = permission_obj.channels.all()
        return channels
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("custom_permission_filter_channels: %s at %s", e, str(exc_tb.tb_lineno))
        return []


def custom_permission_filter_pfls(user):

    try:
        permission_obj = CustomPermission.objects.get(user__username=user.username)
        brands = permission_obj.brands.all()
        pfl_objs = PFL.objects.filter(product__brand__in=brands)
        return pfl_objs
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("custom_permission_filter_pfls: %s at %s", e, str(exc_tb.tb_lineno))
        return []

def create_response_images_flyer_pfl(images):

    temp_list = []
    for image in images:
        temp_dict = {}
        try:
            temp_dict["url"] = image.mid_image.url
        except Exception as e:
            temp_dict["url"] = image.image.url
        temp_dict["pk"] = image.pk
        temp_list.append(temp_dict)
    return temp_list


def create_response_images_flyer_pfl_main_sub(images):

    temp_list = []
    for image in images:
        temp_dict = {}
        try:
            temp_dict["url"] = image.image.mid_image.url
        except Exception as e:
            temp_dict["url"] = image.image.image.url
        temp_dict["pk"] = image.image.pk
        temp_list.append(temp_dict)
    return temp_list


def create_response_images(images):

    temp_list = []
    for image in images:
        temp_dict = {}
        temp_dict["main-url"] = image.image.url
        try:
            temp_dict["thumbnail-url"] = image.thumbnail.url
        except Exception as e:
            logger.warning("No thumbnail for image with pk %s", str(image.pk))
            temp_dict["thumbnail-url"] = image.image.url

        try:
            temp_dict["midimage-url"] = image.mid_image.url
        except Exception as e:
            logger.warning("No mid_image for image with pk %s", str(image.pk))
            temp_dict["midimage-url"] = image.image.url

        temp_dict["pk"] = image.pk
        temp_list.append(temp_dict)
    return temp_list


def create_response_images_main_sub_delete(images):

    temp_list = []
    for image in images:
        temp_dict = {}
        temp_dict["main-url"] = image.image.image.url

        try:
            temp_dict["thumbnail-url"] = image.image.thumbnail.url
        except Exception as e:
            logger.warning("No thumbnail for image with pk %s", str(image.image.pk))
            temp_dict["thumbnail-url"] = image.image.image.url

        try:
            temp_dict["midimage-url"] = image.image.mid_image.url
        except Exception as e:
            logger.warning("No mid_image for image with pk %s", str(image.image.pk))
            temp_dict["midimage-url"] = image.image.image.url

        temp_dict["pk"] = image.image.pk
        temp_list.append(temp_dict)
    return temp_list


def create_response_images_main(images):

    temp_list = []
    for image in images:
        temp_dict = {}
        temp_dict["main-url"] = image.image.image.url

        try:
            temp_dict["thumbnail-url"] = image.image.thumbnail.url
        except Exception as e:
            logger.warning("No thumbnail for main image with pk %s", str(image.pk))
            temp_dict["thumbnail-url"] = image.image.image.url

        try:
            temp_dict["midimage-url"] = image.image.mid_image.url
        except Exception as e:
            logger.warning("No mid_image for main image with pk %s", str(image.pk))
            temp_dict["midimage-url"] = image.image.image.url

        temp_dict["pk"] = image.pk
        temp_dict["is_main_image"] = image.is_main_image
        temp_list.append(temp_dict)
    return temp_list


def create_response_images_sub(images):

    temp_list = []
    for image in images:
        temp_dict = {}
        temp_dict["main-url"] = image.image.image.url

        try:
            temp_dict["thumbnail-url"] = image.image.thumbnail.url
        except Exception as e:
            logger.warning("No thumbnail for sub image with pk %s", str(image.pk))
            temp_dict["thumbnail-url"] = image.image.image.url

        try:
            temp_dict["midimage-url"] = image.image.mid_image.url
        except Exception as e:
            logger.warning("No mid_image for sub image with pk %s", str(image.pk))
            temp_dict["midimage-url"] = image.image.image.url

        temp_dict["pk"] = image.pk
        temp_dict["is_sub_image"] = image.is_sub_image
        temp_dict["sub_image_index"] = image.sub_image_index
        temp_list.append(temp_dict)
    return temp_list
    

def partial_overwrite(old_value, new_value, data_type):
    
    if new_value=="" or new_value==None:
        return old_value

    if data_type=="str":
        return str(new_value)
    elif data_type=="float":
        return float(new_value)
    elif data_type=="int":
        return int(new_value)


def fill_missing(old_value, new_value, data_type):

    if old_value!="" and old_value!=None:
        return old_value

    if new_value=="" or new_value == None:
        return old_value

    if data_type=="str":
        return str(new_value)
    elif data_type=="float":
        return float(new_value)
    elif data_type=="int":
        return int(new_value)


def save_subimage(product_obj, image_url, index):
    
    try:
        if image_url!="":
            filename = image_url.split("/")[-1]
            result = urllib.urlretrieve(image_url, filename)
            image_obj = Image.objects.create(image=File(open(result[0])))
            image_bucket_obj = ImageBucket.objects.create(image=image_obj, is_sub_image=True, sub_image_index=index)
            product_obj.sub_images.add(image_bucket_obj)
            os.system("rm "+result[0])              # Remove temporary file
            product_obj.save()
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error save_subimage: %s at %s", e, str(exc_tb.tb_lineno))
        
def reset_sub_images(product_obj):
    for img in product_obj.sub_images.filter(is_sub_image=True):
        img.is_sub_image = False
        img.sub_image_index = 0
        img.save()

def reset_main_images(product_obj):
    for img in product_obj.main_images.filter(is_main_image=True):
        img.is_main_image = False
        img.save()

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
