from WAMSApp.models import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view

from django.db.models import Q
from django.core.paginator import Paginator

import logging
import json
logger = logging.getLogger(__name__)


class CreateNestoProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data
            logger.info("CreateNestoProductAPI: %s", str(data))

            # if request.user.has_perm('WAMSApp.add_mestoproduct') == False:
            #     logger.warning("CreateNestoProductAPI Restricted Access!")
            #     response['status'] = 403
            #     return Response(data=response)

            if not isinstance(data, dict):
                data = json.loads(data)

            article_number = data["article_number"]
            product_name = data["product_name"]
            product_name_ecommerce = data["product_name_ecommerce"]
            barcode = data["barcode"]
            uom = data["uom"]
            language_key = data["language_key"]
            brand = data["brand"]
            weight_volume = data["weight_volume"]

            country_of_origin = data["country_of_origin"]
            highlights = data["highlights"]
            storage_condition = data["storage_condition"]
            preparation_and_usage = data["preparation_and_usage"]
            allergic_information = data["allergic_information"]
            product_description = data["product_description"]
            dimensions = data["dimensions"]
            nutrition_facts = data["nutrition_facts"]
            ingredients = data["ingredients"]
            return_days = data["return_days"]
            product_status = data["product_status"]

            organization_obj = Organization.objects.get(name="Nesto Group")

            custom_permission_obj = CustomPermission.objects.get(user__username=request.user.username)

            brand_obj, created = Brand.objects.get_or_create(name=brand, organization=organization_obj)
            if created==True:
                custom_permission_obj.brands.add(brand_obj)
                custom_permission_obj.save()

            nesto_product_obj = NestoProduct.objects.create(article_number=article_number,
                                                            product_name=product_name,
                                                            product_name_ecommerce=product_name_ecommerce,
                                                            barcode=barcode,
                                                            uom=uom,
                                                            language_key=language_key,
                                                            brand=brand_obj,
                                                            weight_volume=weight_volume,
                                                            country_of_origin=country_of_origin,
                                                            highlights=highlights,
                                                            storage_condition=storage_condition,
                                                            preparation_and_usage=preparation_and_usage,
                                                            allergic_information=allergic_information,
                                                            product_description=product_description,
                                                            dimensions=json.dumps(dimensions),
                                                            nutrition_facts=nutrition_facts,
                                                            ingredients=ingredients,
                                                            return_days=return_days,
                                                            product_status=product_status)

            response["product_uuid"] = nesto_product_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateNestoProductAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UpdateNestoProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data
            logger.info("UpdateNestoProductAPI: %s", str(data))

            # if request.user.has_perm('WAMSApp.add_nestoproduct') == False:
            #     logger.warning("CreateNestoProductAPI Restricted Access!")
            #     response['status'] = 403
            #     return Response(data=response)

            if not isinstance(data, dict):
                data = json.loads(data)

            product_uuid = data["product_uuid"]

            nesto_product_obj = NestoProduct.objects.get(uuid=product_uuid)

            article_number = data["article_number"]
            product_name = data["product_name"]
            product_name_ecommerce = data["product_name_ecommerce"]
            barcode = data["barcode"]
            uom = data["uom"]
            language_key = data["language_key"]
            brand = data["brand"]
            weight_volume = data["weight_volume"]

            country_of_origin = data["country_of_origin"]
            highlights = data["highlights"]
            storage_condition = data["storage_condition"]
            preparation_and_usage = data["preparation_and_usage"]
            allergic_information = data["allergic_information"]
            product_description = data["product_description"]
            dimensions = data["dimensions"]
            nutrition_facts = data["nutrition_facts"]
            ingredients = data["ingredients"]
            return_days = data["return_days"]
            product_status = data["product_status"]

            organization_obj = Organization.objects.get(name="Nesto Group")

            custom_permission_obj = CustomPermission.objects.get(user__username=request.user.username)

            brand_obj, created = Brand.objects.get_or_create(name=brand, organization=organization_obj)
            if created==True:
                custom_permission_obj.brands.add(brand_obj)
                custom_permission_obj.save()

            nesto_product_obj.article_number=article_number
            nesto_product_obj.product_name=product_name
            nesto_product_obj.product_name_ecommerce=product_name_ecommerce
            nesto_product_obj.barcode=barcode
            nesto_product_obj.uom=uom
            nesto_product_obj.language_key=language_key
            nesto_product_obj.brand=brand_obj
            nesto_product_obj.weight_volume=weight_volume
            nesto_product_obj.country_of_origin=country_of_origin
            nesto_product_obj.highlights=highlights
            nesto_product_obj.storage_condition=storage_condition
            nesto_product_obj.preparation_and_usage=preparation_and_usage
            nesto_product_obj.allergic_information=allergic_information
            nesto_product_obj.product_description=product_description
            nesto_product_obj.dimensions=json.dumps(dimensions)
            nesto_product_obj.nutrition_facts=nutrition_facts
            nesto_product_obj.ingredients=ingredients
            nesto_product_obj.return_days=return_days
            nesto_product_obj.product_status = product_status
            nesto_product_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateNestoProductAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchNestoProductDetailsAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data
            logger.info("FetchNestoProductDetailsAPI: %s", str(data))

            # if request.user.has_perm('WAMSApp.add_nestoproduct') == False:
            #     logger.warning("FetchNestoProductDetailsAPI Restricted Access!")
            #     response['status'] = 403
            #     return Response(data=response)

            if not isinstance(data, dict):
                data = json.loads(data)

            product_uuid = data["product_uuid"]

            nesto_product_obj = NestoProduct.objects.get(uuid=product_uuid)

            response["article_number"] = nesto_product_obj.article_number
            response["product_name"] = nesto_product_obj.product_name
            response["product_name_ecommerce"] = nesto_product_obj.product_name_ecommerce
            response["barcode"] = nesto_product_obj.barcode
            response["uom"] = nesto_product_obj.uom
            response["language_key"] = nesto_product_obj.language_key
            response["brand"] = nesto_product_obj.brand.name
            response["about_brand"] = nesto_product_obj.brand.description
            response["weight_volume"] = nesto_product_obj.weight_volume
            response["country_of_origin"] = nesto_product_obj.country_of_origin
            response["highlights"] = nesto_product_obj.highlights
            response["storage_condition"] = nesto_product_obj.storage_condition
            response["preparation_and_usage"] = nesto_product_obj.preparation_and_usage
            response["allergic_information"] = nesto_product_obj.allergic_information
            response["product_description"] = nesto_product_obj.product_description
            response["dimensions"] = json.loads(nesto_product_obj.dimensions)
            response["nutrition_facts"] = nesto_product_obj.nutrition_facts
            response["ingredients"] = nesto_product_obj.ingredients
            response["return_days"] = nesto_product_obj.return_days

            front_images = []
            for image_obj in nesto_product_obj.front_images.all():
                try:
                    temp_dict = {}
                    temp_dict["original_image"] = image_obj.image.url
                    temp_dict["mid_image"] = image_obj.mid_image.url
                    temp_dict["thumbnail_image"] = image_obj.thumbnail.url
                    temp_dict["pk"] = image_obj.pk
                    front_images.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchNestoProductDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

            back_images = []
            for image_obj in nesto_product_obj.back_images.all():
                try:
                    temp_dict = {}
                    temp_dict["original_image"] = image_obj.image.url
                    temp_dict["mid_image"] = image_obj.mid_image.url
                    temp_dict["thumbnail_image"] = image_obj.thumbnail.url
                    temp_dict["pk"] = image_obj.pk
                    back_images.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchNestoProductDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

            side_images = []
            for image_obj in nesto_product_obj.side_images.all():
                try:
                    temp_dict = {}
                    temp_dict["original_image"] = image_obj.image.url
                    temp_dict["mid_image"] = image_obj.mid_image.url
                    temp_dict["thumbnail_image"] = image_obj.thumbnail.url
                    temp_dict["pk"] = image_obj.pk
                    side_images.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchNestoProductDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

            nutrition_images = []
            for image_obj in nesto_product_obj.nutrition_images.all():
                try:
                    temp_dict = {}
                    temp_dict["original_image"] = image_obj.image.url
                    temp_dict["mid_image"] = image_obj.mid_image.url
                    temp_dict["thumbnail_image"] = image_obj.thumbnail.url
                    temp_dict["pk"] = image_obj.pk
                    nutrition_images.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchNestoProductDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

            product_content_images = []
            for image_obj in nesto_product_obj.product_content_images.all():
                try:
                    temp_dict = {}
                    temp_dict["original_image"] = image_obj.image.url
                    temp_dict["mid_image"] = image_obj.mid_image.url
                    temp_dict["thumbnail_image"] = image_obj.thumbnail.url
                    temp_dict["pk"] = image_obj.pk
                    product_content_images.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchNestoProductDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

            images = {
                "front_images": front_images,
                "back_images": back_images,
                "side_images": side_images,
                "nutrition_images": nutrition_images,
                "product_content_images": product_content_images
            }

            response["images"] = images
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchNestoProductDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchNestoProductListAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data
            logger.info("FetchNestoProductListAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            filter_parameters = data.get("filter_parameters", {})
            search_list = data.get("tags",[])

            nesto_product_objs = NestoProduct.objects.all()

            if "brand_name" in filter_parameters:
                if filter_parameters["brand_name"]!="":
                    nesto_product_objs = nesto_product_objs.filter(brand__name=filter_parameters["brand_name"])
            
            if len(search_list)>0:
                temp_nesto_product_objs = NestoProduct.objects.none()
                for search_string in search_list:
                    search_string = search_string.strip()
                    temp_nesto_product_objs |= nesto_product_objs.filter(Q(article_number__icontains=search_string) | Q(product_name__icontains=search_string) | Q(barcode__icontains=search_string) | Q(uuid__icontains=search_string) | Q(product_name_ecommerce__icontains=search_string))
                nesto_product_objs = temp_nesto_product_objs.distinct()
            
            if "product_status" in filter_parameters:
                product_status = filter_parameters["product_status"]
                if product_status!="all":
                    nesto_product_objs = nesto_product_objs.filter(product_status=product_status)

            if "has_image" in filter_parameters:
                has_image = filter_parameters["has_image"]
                if has_image!="":
                    if "image_type" in filter_parameters:
                        image_type = filter_parameters["image_type"]
                        if image_type=="all":
                            if has_image=="1":
                                nesto_product_objs = nesto_product_objs.exclude(front_images_count=0, back_images_count=0, side_images_count=0, nutrition_images_count=0, product_content_images_count=0)
                            elif has_image=="0":
                                nesto_product_objs = nesto_product_objs.filter(front_images_count=0, back_images_count=0, side_images_count=0, nutrition_images_count=0, product_content_images_count=0)
                        elif image_type=="front":
                            if has_image=="1":
                                nesto_product_objs = nesto_product_objs.exclude(front_images_count=0)
                            elif has_image=="0":
                                nesto_product_objs = nesto_product_objs.filter(front_images_count=0)
                        elif image_type=="back":
                            if has_image=="1":
                                nesto_product_objs = nesto_product_objs.exclude(back_images_count=0)
                            elif has_image=="0":
                                nesto_product_objs = nesto_product_objs.filter(back_images_count=0)
                        elif image_type=="side":
                            if has_image=="1":
                                nesto_product_objs = nesto_product_objs.exclude(side_images_count=0)
                            elif has_image=="0":
                                nesto_product_objs = nesto_product_objs.filter(side_images_count=0)
                        elif image_type=="nutrition":
                            if has_image=="1":
                                nesto_product_objs = nesto_product_objs.exclude(nutrition_images_count=0)
                            elif has_image=="0":
                                nesto_product_objs = nesto_product_objs.filter(nutrition_images_count=0)
                        elif image_type=="product_content":
                            if has_image=="1":
                                nesto_product_objs = nesto_product_objs.exclude(product_content_images_count=0)
                            elif has_image=="0":
                                nesto_product_objs = nesto_product_objs.filter(product_content_images_count=0)
                        
            total_products = nesto_product_objs.count()

            page = int(data.get('page', 1))
            paginator = Paginator(nesto_product_objs, 20)
            nesto_product_objs = paginator.page(page)

            product_list = []

            for nesto_product_obj in nesto_product_objs:
                try:
                    temp_dict = {}
                    temp_dict["product_uuid"] = nesto_product_obj.uuid
                    temp_dict["article_number"] = nesto_product_obj.article_number
                    temp_dict["product_name"] = nesto_product_obj.product_name
                    temp_dict["product_name_ecommerce"] = nesto_product_obj.product_name_ecommerce
                    temp_dict["barcode"] = nesto_product_obj.barcode
                    temp_dict["uom"] = nesto_product_obj.uom
                    temp_dict["language_key"] = nesto_product_obj.language_key
                    temp_dict["brand"] = nesto_product_obj.brand.name
                    temp_dict["about_brand"] = nesto_product_obj.brand.description
                    temp_dict["weight_volume"] = nesto_product_obj.weight_volume
                    temp_dict["country_of_origin"] = nesto_product_obj.country_of_origin
                    temp_dict["highlights"] = nesto_product_obj.highlights
                    temp_dict["storage_condition"] = nesto_product_obj.storage_condition
                    temp_dict["preparation_and_usage"] = nesto_product_obj.preparation_and_usage
                    temp_dict["allergic_information"] = nesto_product_obj.allergic_information
                    temp_dict["product_description"] = nesto_product_obj.product_description
                    temp_dict["dimensions"] = json.loads(nesto_product_obj.dimensions)
                    temp_dict["nutrition_facts"] = nesto_product_obj.nutrition_facts
                    temp_dict["ingredients"] = nesto_product_obj.ingredients
                    temp_dict["return_days"] = nesto_product_obj.return_days
                    temp_dict["product_status"] = nesto_product_obj.product_status
                    front_images = []
                    for image_obj in nesto_product_obj.front_images.all():
                        try:
                            temp_dict2 = {}
                            temp_dict2["original_image"] = image_obj.image.url
                            temp_dict2["mid_image"] = image_obj.mid_image.url if image_obj.mid_image!=None else ""
                            temp_dict2["thumbnail_image"] = image_obj.thumbnail.url
                            temp_dict2["pk"] = image_obj.pk
                            front_images.append(temp_dict2)
                        except Exception as e:
                            exc_type, exc_obj, exc_tb = sys.exc_info()
                            logger.error("FetchNestoProductListAPI: %s at %s", e, str(exc_tb.tb_lineno))
                    temp_dict["front_images"] = front_images
                    product_list.append(temp_dict)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("FetchNestoProductListAPI: %s at %s", e, str(exc_tb.tb_lineno))
            
            is_available = True
            if int(paginator.num_pages) == int(page):
                is_available = False

            response["is_available"] = is_available
            response["total_products"] = int(total_products)
            response["products"] = product_list
            response["price_type"] = False 
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchNestoProductListAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddNestoProductImagesAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data
            logger.info("AddNestoProductImagesAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_uuid = data["product_uuid"]
            nesto_product_obj = NestoProduct.objects.get(uuid=product_uuid)

            image_type = data["image_type"]
            image_count = int(data["image_count"])
            for i in range(image_count):
                image_obj = Image.objects.create(image=data["image_"+str(i)])

                if image_type=="front":
                    nesto_product_obj.front_images.add(image_obj)
                    nesto_product_obj.front_images_count = nesto_product_obj.front_images.all().count()
                elif image_type=="back":
                    nesto_product_obj.back_images.add(image_obj)
                    nesto_product_obj.back_images_count = nesto_product_obj.back_images.all().count()
                elif image_type=="side":
                    nesto_product_obj.side_images.add(image_obj)
                    nesto_product_obj.side_images_count = nesto_product_obj.side_images.all().count()
                elif image_type=="nutrition":
                    nesto_product_obj.nutrition_images.add(image_obj)
                    nesto_product_obj.nutrition_images_count = nesto_product_obj.nutrition_images.all().count()
                elif image_type=="product_content":
                    nesto_product_obj.product_content_images.add(image_obj) 
                    nesto_product_obj.product_content_images_count = nesto_product_obj.product_content_images.all().count()

            nesto_product_obj.save()
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddNestoProductImagesAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class RemoveNestoProductImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data
            logger.info("RemoveNestoProductImageAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            product_uuid = data["product_uuid"]

            image_pk = data["image_pk"]
            image_obj = Image.objects.get(pk=image_pk)
            image_obj.delete()

            nesto_product_obj = NestoProduct.objects.get(uuid=product_uuid)
            nesto_product_obj.front_images_count = nesto_product_obj.front_images.all().count()
            nesto_product_obj.back_images_count = nesto_product_obj.back_images.all().count()
            nesto_product_obj.side_images_count = nesto_product_obj.side_images.all().count()
            nesto_product_obj.nutrition_images_count = nesto_product_obj.nutrition_images.all().count()
            nesto_product_obj.product_content_images_count = nesto_product_obj.front_images.all().count()
            nesto_product_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("RemoveNestoProductImageAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SearchNestoProductAutoCompleteAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data
            logger.info("SearchNestoProductAutoCompleteAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            search_string = data["searchString"]
            product_uuid = data["product_uuid"]
            link_type = data["link_type"]

            search_nesto_product_objs = NestoProduct.objects.filter(Q(article_number__icontains=search_string) | Q(product_name__icontains=search_string) | Q(barcode__icontains=search_string))
            

            nesto_product_obj = NestoProduct.objects.get(uuid=product_uuid)
            linked_product_uuid_list = []
            if link_type=="substitute":
                linked_product_uuid_list = list(nesto_product_obj.substitute_products.all().values_list("uuid").distinct())
            elif link_type=="cross_selling":
                linked_product_uuid_list = list(nesto_product_obj.cross_selling_products.all().values_list("uuid").distinct())
            elif link_type=="upselling_products":
                linked_product_uuid_list = list(nesto_product_obj.upselling_products.all().values_list("uuid").distinct())

            search_nesto_product_objs = search_nesto_product_objs.exclude(uuid__in=linked_product_uuid_list)[:10]

            nesto_product_list = []
            for search_nesto_product_obj in search_nesto_product_objs:
                temp_dict = {}
                temp_dict["name"] = search_nesto_product_obj.product_name
                temp_dict["barcode"] = search_nesto_product_obj.barcode
                temp_dict["uuid"] = search_nesto_product_obj.uuid
                nesto_product_list.append(temp_dict)

            response['nesto_product_list'] = nesto_product_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchNestoProductAutoCompleteAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)
            

class FetchLinkedNestoProductsAPI(APIView):

    def post(self, request, *args, **kwargs):
    
        response = {}
        response['status'] = 500
        
        try:
            data = request.data
            logger.info("FetchLinkedNestoProductsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_uuid = data["product_uuid"]

            nesto_product_obj = NestoProduct.objects.get(uuid=product_uuid)

            linked_nesto_products = {}

            substitute_products = []
            substitute_product_objs = nesto_product_obj.substitute_products.all()
            for substitute_product_obj in substitute_product_objs:
                temp_dict = {}
                temp_dict["name"] = substitute_product_obj.product_name
                temp_dict["article_number"] = substitute_product_obj.article_number
                temp_dict["barcode"] = substitute_product_obj.barcode
                temp_dict["image"] = substitute_product_obj.front_images.all()[0].image.url if substitute_product_obj.front_images.all().exists() else ""
                temp_dict["uuid"] = substitute_product_obj.uuid
                substitute_products.append(temp_dict)
            linked_nesto_products["substitute_products"] = substitute_products

            upselling_products = []
            upselling_product_objs = nesto_product_obj.upselling_products.all()
            for upselling_product_obj in upselling_product_objs:
                temp_dict = {}
                temp_dict["name"] = upselling_product_obj.product_name
                temp_dict["article_number"] = upselling_product_obj.article_number
                temp_dict["barcode"] = upselling_product_obj.barcode
                temp_dict["image"] = upselling_product_obj.front_images.all()[0].image.url if upselling_product_obj.front_images.all().exists() else ""
                temp_dict["uuid"] = upselling_product_obj.uuid
                upselling_products.append(temp_dict)
            linked_nesto_products["upselling_products"] = upselling_products

            cross_selling_products = []
            cross_selling_product_objs = nesto_product_obj.cross_selling_products.all()
            for cross_selling_product_obj in cross_selling_product_objs:
                temp_dict = {}
                temp_dict["name"] = cross_selling_product_obj.product_name
                temp_dict["article_number"] = cross_selling_product_obj.article_number
                temp_dict["barcode"] = cross_selling_product_obj.barcode
                temp_dict["image"] = cross_selling_product_obj.front_images.all()[0].image.url if cross_selling_product_obj.front_images.all().exists() else ""
                temp_dict["uuid"] = cross_selling_product_obj.uuid
                cross_selling_products.append(temp_dict)
            linked_nesto_products["cross_selling_products"] = cross_selling_products

            response["linked_nesto_products"] = linked_nesto_products
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchLinkedNestoProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class LinkNestoProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data
            logger.info("LinkNestoProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_uuid = data["product_uuid"]
            linked_product_uuid = data["linked_product_uuid"]
            
            nesto_product_obj = NestoProduct.objects.get(uuid=product_uuid)
            linked_nesto_product_obj = NestoProduct.objects.get(uuid=linked_product_uuid)
            link_type = data["link_type"]

            if link_type=="substitute":
                nesto_product_obj.substitute_products.add(linked_nesto_product_obj)
            elif link_type=="cross_selling":
                nesto_product_obj.cross_selling_products.add(linked_nesto_product_obj)
            elif link_type=="upselling_products":
                nesto_product_obj.upselling_products.add(linked_nesto_product_obj)
            nesto_product_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("LinkNestoProductAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UnLinkNestoProductAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data
            logger.info("UnLinkNestoProductAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            product_uuid = data["product_uuid"]
            linked_product_uuid = data["linked_product_uuid"]
            
            nesto_product_obj = NestoProduct.objects.get(uuid=product_uuid)
            linked_nesto_product_obj = NestoProduct.objects.get(uuid=linked_product_uuid)
            link_type = data["link_type"]

            if link_type=="substitute":
                nesto_product_obj.substitute_products.remove(linked_nesto_product_obj)
            elif link_type=="cross_selling":
                nesto_product_obj.cross_selling_products.remove(linked_nesto_product_obj)
            elif link_type=="upselling_products":
                nesto_product_obj.upselling_products.remove(linked_nesto_product_obj)
            nesto_product_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UnLinkNestoProductAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchNestoBrandsAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data
            logger.info("FetchNestoBrandsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            organization_obj = Organization.objects.get(name="Nesto Group")
            brand_objs = Brand.objects.filter(organization=organization_obj)

            brand_name_list = []
            for brand_obj in brand_objs:
                temp_dict = {}
                temp_dict["name"] = brand_obj.name
                temp_dict["name_ar"] = brand_obj.name_ar
                temp_dict["pk"] = brand_obj.pk
                brand_name_list.append(temp_dict)

            response['brand_list'] = brand_name_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchNestoBrandsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


CreateNestoProduct = CreateNestoProductAPI.as_view()

UpdateNestoProduct = UpdateNestoProductAPI.as_view()

FetchNestoProductDetails = FetchNestoProductDetailsAPI.as_view()

FetchNestoProductList = FetchNestoProductListAPI.as_view()

AddNestoProductImages = AddNestoProductImagesAPI.as_view()

RemoveNestoProductImage = RemoveNestoProductImageAPI.as_view()

SearchNestoProductAutoComplete = SearchNestoProductAutoCompleteAPI.as_view()

FetchLinkedNestoProducts = FetchLinkedNestoProductsAPI.as_view()

LinkNestoProduct = LinkNestoProductAPI.as_view()

UnLinkNestoProduct = UnLinkNestoProductAPI.as_view()

FetchNestoBrands = FetchNestoBrandsAPI.as_view()