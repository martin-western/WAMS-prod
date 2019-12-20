from WAMSApp.models import *
import logging
import sys

logger = logging.getLogger(__name__)

def convert_to_ascii(s):
    s = s.replace(u'\u2013', "-").replace(u'\u2019', "'").replace(u'\u2018', "'").replace(u'\u201d','"').replace(u'\u201c','"')
    s = s.encode("ascii", "ignore")
    return s


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
    if new_value=="":
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

    if new_value=="":
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
        import sys
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error save_subimage", str(e), str(exc_tb.tb_lineno))


def reset_sub_images(product_obj):
    for img in product_obj.sub_images.filter(is_sub_image=True):
        img.is_sub_image = False
        img.sub_image_index = 0
        img.save()


def reset_main_images(product_obj):
    for img in product_obj.main_images.filter(is_main_image=True):
        img.is_main_image = False
        img.save()
