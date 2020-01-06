from django.core.files.base import ContentFile

from PIL import Image as IMAGE

import logging
import sys
import imghdr
import base64
import six
import uuid

from WAMSApp.models import *

logger = logging.getLogger(__name__)

def custom_permission_filter_base_products(user):

    try:
        permission_obj = CustomPermission.objects.get(user__username=user.username)
        brands = permission_obj.brands.all()
        base_product_objs = BaseProduct.objects.filter(brand__in=brands)
        
        return base_product_objs
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("custom_permission_filter_base_products: %s at %s", e, str(exc_tb.tb_lineno))
        return []

def custom_permission_filter_products(user):

    try:
        permission_obj = CustomPermission.objects.get(user__username=user.username)
        brands = permission_obj.brands.all()
        base_product_objs = BaseProduct.objects.filter(brand__in=brands)
        
        product_objs_list = Product.objects.none()
        
        for base_product_obj in base_product_objs:
            product_objs_list |= Product.objects.filter(base_product=base_product_obj)
            
        return product_objs_list
    
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
            temp_dict["high-res-url"] = image.image.url
        except Exception as e:
            temp_dict["url"] = image.image.url
            temp_dict["high-res-url"] = image.image.url
        temp_dict["pk"] = image.pk
        temp_list.append(temp_dict)
    return temp_list


def create_response_images_flyer_pfl_main_sub(images):

    temp_list = []
    for image in images:
        temp_dict = {}
        try:
            temp_dict["url"] = image.image.mid_image.url
            temp_dict["high-res-url"] = image.image.image.url
        except Exception as e:
            temp_dict["url"] = image.image.image.url
            temp_dict["high-res-url"] = image.image.image.url
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


def save_subimage(product_obj, image_url, index, channel):
    
    try:
        if image_url!="":
            filename = image_url.split("/")[-1]
            result = urllib.urlretrieve(image_url, filename)
            image_obj = Image.objects.create(image=File(open(result[0])))
            image_bucket_obj = ImageBucket.objects.create(image=image_obj, is_sub_image=True, sub_image_index=index)
            
            if channel==None:
                sub_images_obj , created = SubImages.objects.get_or_create(product=product_obj,is_sourced=True)
            else:
                channel_obj = Channel.objects.get(name=channel)
                sub_images_obj , created = SubImages.objects.get_or_create(product=product_obj,channel=channel_obj)
            
            sub_images_obj.sub_images.add(image_bucket_obj)
            os.system("rm "+result[0])              # Remove temporary file
            sub_images_obj.save()
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error save_subimage: %s at %s", e, str(exc_tb.tb_lineno))
        
def reset_sub_images(product_obj):
    sub_images_objs = SubImages.objects.get(product=product_obj)
    
    sub_images_list = []
    for sub_images_obj in sub_images_objs:
        sub_images_list += sub_images_list.sub_images.filter(is_sub_image=True)
    
    sub_images_list = set(sub_images_list)
    
    for img in sub_images_list:
        img.is_sub_image = False
        img.save()

def reset_main_images(product_obj):
    main_images_objs = MainImages.objects.get(product=product_obj)
    
    main_images_list = []
    for main_images_obj in main_images_objs:
        main_images_list += main_images_obj.main_images.filter(is_main_image=True)
    
    main_images_list = set(main_images_list)
    
    for img in main_images_list:
        img.is_main_image = False
        img.save()

