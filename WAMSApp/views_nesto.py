from WAMSApp.models import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view

from django.db.models import Q
from django.core.paginator import Paginator
from django.core.files.storage import default_storage

import logging
import json
import pandas as pd
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
            about_brand = data["about_brand"]

            sub_category_uuid = data.get("sub_category_uuid","")

            organization_obj = Organization.objects.get(name="Nesto Group")

            custom_permission_obj = CustomPermission.objects.get(user__username=request.user.username)

            brand_obj, created = Brand.objects.get_or_create(name=brand, organization=organization_obj)
            brand_obj.description = about_brand
            brand_obj.save()
            if created==True:
                custom_permission_obj.brands.add(brand_obj)
                custom_permission_obj.save()
            
            sub_category_obj = None
            if sub_category_uuid!="":
                sub_category_obj = SubCategory.objects.get(uuid=sub_category_uuid)

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
                                                            product_status=product_status,
                                                            sub_category=sub_category_obj)


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
            about_brand = data["about_brand"]

            sub_category_uuid = data.get("sub_category_uuid","")
            sub_category_obj = None
            if sub_category_uuid!="":
                sub_category_obj = SubCategory.objects.get(uuid=sub_category_uuid)

            organization_obj = Organization.objects.get(name="Nesto Group")

            custom_permission_obj = CustomPermission.objects.get(user__username=request.user.username)

            brand_obj, created = Brand.objects.get_or_create(name=brand, organization=organization_obj)
            brand_obj.description = about_brand
            brand_obj.save()
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
            nesto_product_obj.sub_category = sub_category_obj
            nesto_product_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UpdateNestoProductAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchNestoProductDetailsAPI(APIView):

    def get_images_list(self, image_objs):
        images_list = []
        for image_obj in image_objs:
            try:
                temp_dict = {}
                temp_dict["original_image"] = image_obj.image.url
                temp_dict["mid_image"] = image_obj.mid_image.url
                temp_dict["thumbnail_image"] = image_obj.thumbnail.url
                temp_dict["pk"] = image_obj.pk
                images_list.append(temp_dict)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("FetchNestoProductDetailsAPI get_images_list: %s at %s", e, str(exc_tb.tb_lineno))
        return images_list

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

            if nesto_product_obj.sub_category!=None:
                response["sub_category"] = nesto_product_obj.sub_category.name
                response["sub_category_uuid"] = nesto_product_obj.sub_category.uuid
                response["category"] = nesto_product_obj.sub_category.category.name
                response["category_uuid"] = nesto_product_obj.sub_category.category.uuid
                response["super_category"] = nesto_product_obj.sub_category.category.super_category.name
                response["super_category_uuid"] = nesto_product_obj.sub_category.category.super_category.uuid


            front_images = self.get_images_list(nesto_product_obj.front_images.all())
            back_images = self.get_images_list(nesto_product_obj.back_images.all())
            side_images = self.get_images_list(nesto_product_obj.side_images.all())
            nutrition_images = self.get_images_list(nesto_product_obj.nutrition_images.all())
            product_content_images = self.get_images_list(nesto_product_obj.product_content_images.all())
            supplier_images = self.get_images_list(nesto_product_obj.supplier_images.all())
            lifestyle_images = self.get_images_list(nesto_product_obj.lifestyle_images.all())
            ads_images = self.get_images_list(nesto_product_obj.ads_images.all())
            box_images = self.get_images_list(nesto_product_obj.box_images.all())
            highlight_images = self.get_images_list(nesto_product_obj.highlight_images.all())

            images = {
                "front_images": front_images,
                "back_images": back_images,
                "side_images": side_images,
                "nutrition_images": nutrition_images,
                "product_content_images": product_content_images,
                "highlight_images": highlight_images,
                "box_images": box_images,
                "ads_images": ads_images,
                "lifestyle_images": lifestyle_images,
                "supplier_images": supplier_images
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
                        elif image_type=="supplier":
                            if has_image=="1":
                                nesto_product_objs = nesto_product_objs.exclude(supplier_images_count=0)
                            elif has_image=="0":
                                nesto_product_objs = nesto_product_objs.filter(supplier_images_count=0)
                        elif image_type=="lifestyle":
                            if has_image=="1":
                                nesto_product_objs = nesto_product_objs.exclude(lifestyle_images_count=0)
                            elif has_image=="0":
                                nesto_product_objs = nesto_product_objs.filter(lifestyle_images_count=0)
                        elif image_type=="ads":
                            if has_image=="1":
                                nesto_product_objs = nesto_product_objs.exclude(ads_images_count=0)
                            elif has_image=="0":
                                nesto_product_objs = nesto_product_objs.filter(ads_images_count=0)
                        elif image_type=="box":
                            if has_image=="1":
                                nesto_product_objs = nesto_product_objs.exclude(box_images_count=0)
                            elif has_image=="0":
                                nesto_product_objs = nesto_product_objs.filter(box_images_count=0)
                        elif image_type=="highlight":
                            if has_image=="1":
                                nesto_product_objs = nesto_product_objs.exclude(highlight_images_count=0)
                            elif has_image=="0":
                                nesto_product_objs = nesto_product_objs.filter(highlight_images_count=0)
                        
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
                    if nesto_product_obj.sub_category!=None:
                        temp_dict["sub_category"] = nesto_product_obj.sub_category.name
                        temp_dict["category"] = nesto_product_obj.sub_category.category.name
                        temp_dict["super_category"] = nesto_product_obj.sub_category.category.super_category.name
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
                elif image_type=="supplier":
                    nesto_product_obj.supplier_images.add(image_obj) 
                    nesto_product_obj.supplier_images_count = nesto_product_obj.supplier_images.all().count()
                elif image_type=="lifestyle":
                    nesto_product_obj.lifestyle_images.add(image_obj) 
                    nesto_product_obj.lifestyle_images_count = nesto_product_obj.lifestyle_images.all().count()
                elif image_type=="ads":
                    nesto_product_obj.ads_images.add(image_obj) 
                    nesto_product_obj.ads_images_count = nesto_product_obj.ads_images.all().count()
                elif image_type=="box":
                    nesto_product_obj.box_images.add(image_obj) 
                    nesto_product_obj.box_images_count = nesto_product_obj.box_images.all().count()
                elif image_type=="highlight":
                    nesto_product_obj.highlight_images.add(image_obj) 
                    nesto_product_obj.highlight_images_count = nesto_product_obj.highlight_images.all().count()
                
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
            nesto_product_obj.product_content_images_count = nesto_product_obj.product_content_images.all().count()
            nesto_product_obj.supplier_images_count = nesto_product_obj.supplier_images.all().count()
            nesto_product_obj.lifestyle_images_count = nesto_product_obj.lifestyle_images.all().count()
            nesto_product_obj.ads_images_count = nesto_product_obj.ads_images.all().count()
            nesto_product_obj.box_images_count = nesto_product_obj.box_images.all().count()
            nesto_product_obj.highlight_images_count = nesto_product_obj.highlight_images.all().count()
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
                temp_dict["about_brand"] = brand_obj.description
                temp_dict["name_ar"] = brand_obj.name_ar
                temp_dict["pk"] = brand_obj.pk
                brand_name_list.append(temp_dict)

            response['brand_list'] = brand_name_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchNestoBrandsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class BulkUploadNestoProductsAPI(APIView):
    
    def post(self, request, *args, **kwargs):
    
        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("BulkUploadNestoProductsAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)
            
            path = default_storage.save('tmp/bulk-upload-nesto-products.xlsx', data["import_file"])
            path = "http://cdn.omnycomm.com.s3.amazonaws.com/"+path

            try:
                dfs = pd.read_excel(path, sheet_name=None)["Sheet1"]
                dfs = dfs.fillna("")
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("BulkUploadNestoProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))
                response['status'] = 1
                response['message'] = "the sheet_file or sheet_name is not proper"
                return Response(data=response)
            
            static_headers = ["Article No *","Barcode","UOM","Article Name *","Language Key *","Brand *","Weight/Volume","Country of Origin *","Storage Condition","Warning","Preparation and Usage","Allergic Information","About Brand *","Highlights *(Rich Text)","Product Description (Details) *","Nutrition facts *(Rich Text)","Ingredients *"]

            if len(dfs.columns) != len(static_headers):
                response["status"] = 2
                response["message"] = "the sheet has more number of colomns then expected"
                return Response(data=response)
            
            logger.info("check %s", len(dfs.columns))

            flag = 0
            for col in list(dfs.columns.values):
                if col != static_headers[i]:
                    flag=1
                    break
            
            if flag==1:
                response["status"] = 3
                response["message"] = "the order or naming of the headers not according to the sample template"
                return Response(data=response)
            
            organization_obj = Organization.objects.get(name="Nesto Group")
            rows = len(dfs.iloc[:])
            cnt = 0
            excel_errors = []
            for i in range(1,rows):
                try:
                    cnt += 1
                    article_no = "" if str(dfs.iloc[i][0]).strip()=="nan" else str(dfs.iloc[i][0]).strip()
                    barcode = "" if str(dfs.iloc[i][1]).strip()=="nan" else str(dfs.iloc[i][1]).strip()
                    uom = "" if str(dfs.iloc[i][2]).strip()=="nan" else str(dfs.iloc[i][2]).strip()
                    article_name = "" if str(dfs.iloc[i][3]).strip()=="nan" else str(dfs.iloc[i][3]).strip()
                    language_key = "" if str(dfs.iloc[i][4]).strip()=="nan" else str(dfs.iloc[i][4]).strip()
                    brand_name = "" if str(dfs.iloc[i][5]).strip()=="nan" else str(dfs.iloc[i][5]).strip()
                    weight_volume = "" if str(dfs.iloc[i][6]).strip()=="nan" else str(dfs.iloc[i][6]).strip()
                    country_of_origin = "" if str(dfs.iloc[i][7]).strip()=="nan" else str(dfs.iloc[i][7]).strip()
                    storage_condition = "" if str(dfs.iloc[i][8]).strip()=="nan" else str(dfs.iloc[i][8]).strip()
                    warning = "" if str(dfs.iloc[i][9]).strip()=="nan" else str(dfs.iloc[i][9]).strip()
                    prep_and_usage = "" if str(dfs.iloc[i][10]).strip()=="nan" else str(dfs.iloc[i][10]).strip()
                    allergic_info = "" if str(dfs.iloc[i][11]).strip()=="nan" else str(dfs.iloc[i][11]).strip()
                    about_brand = "" if str(dfs.iloc[i][12]).strip()=="nan" else str(dfs.iloc[i][12]).strip()
                    highlights = "" if str(dfs.iloc[i][13]).strip()=="nan" else str(dfs.iloc[i][13]).strip()
                    prod_description = "" if str(dfs.iloc[i][14]).strip()=="nan" else str(dfs.iloc[i][14]).strip()
                    nutrition_facts = "" if str(dfs.iloc[i][15]).strip()=="nan" else str(dfs.iloc[i][15]).strip()
                    ingredients = "" if str(dfs.iloc[i][16]).strip()=="nan" else str(dfs.iloc[i][16]).strip()
                    product_status = ""
                    if article_no!="" and barcode!="" and article_name!="":
                        product_status = "not ecommerce"
                    if product_status=="not ecommerce" and brand_name!="" and language_key!="" and weight_volume!="" and country_of_origin!="" and storage_condition!="" and allergic_info!="" and  nutrition_facts!="" and  ingredients!="":
                        product_status = "ecommerce"
                    if product_status=="ecommerce" and uom!="" and about_brand!="" and prod_description!="":
                        product_status = "rich"
                    return_days = "7"
                    nesto_product_objs = NestoProduct.objects.filter(barcode=barcode)
                    if nesto_product_objs.count()==0:
                        brand_obj, created = Brand.objects.get_or_create(name=brand_name, organization=organization_obj)
                        brand_obj.description = about_brand
                        brand_obj.save()
                        nesto_product_obj = NestoProduct.objects.create(article_number=article_no,
                                                                        barcode=barcode,
                                                                        uom=uom,
                                                                        language_key=language_key,
                                                                        product_name=article_name,
                                                                        product_name_ecommerce=article_name,
                                                                        brand=brand_obj,
                                                                        weight_volume=weight_volume,
                                                                        country_of_origin=country_of_origin,
                                                                        storage_condition=storage_condition,
                                                                        preparation_and_usage=prep_and_usage,
                                                                        allergic_information=allergic_info,
                                                                        highlights=highlights,
                                                                        product_description=prod_description,
                                                                        nutrition_facts=nutrition_facts,
                                                                        ingredients=ingredients,
                                                                        product_status=product_status,
                                                                        return_days=return_days
                                                                        )
                    elif nesto_product_objs.count()==1:
                        nesto_product_obj = nesto_product_objs[0]
                        nesto_product_obj.article_number = article_no
                        nesto_product_obj.uom = uom
                        nesto_product_obj.language_key = language_key
                        nesto_product_obj.product_name = article_name
                        nesto_product_obj.product_name_ecommerce = article_name
                        brand_obj , created = Brand.objects.get_or_create(name=brand_name, organization=organization_obj)
                        brand_obj.description = about_brand
                        brand_obj.save()
                        nesto_product_obj.brand = brand_obj
                        nesto_product_obj.weight_volume=weight_volume
                        nesto_product_obj.country_of_origin=country_of_origin
                        nesto_product_obj.storage_condition=storage_condition
                        nesto_product_obj.preparation_and_usage=prep_and_usage
                        nesto_product_obj.allergic_information=allergic_info
                        nesto_product_obj.highlights=highlights
                        nesto_product_obj.product_description=prod_description
                        nesto_product_obj.nutrition_facts=nutrition_facts
                        nesto_product_obj.ingredients=ingredients
                        nesto_product_obj.product_status=product_status
                        nesto_product_obj.return_days=return_days
                        nesto_product_obj.save()
                    else:
                        excel_errors.append({
                            "article_no":barcode,
                            "message":"barcode is not unique"
                        })
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("BulkUploadNestoProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))
           
            response['excel_errors'] = excel_errors
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("BulkUploadNestoProductsAPI: %s at %s", e, str(exc_tb.tb_lineno))

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

BulkUploadNestoProducts = BulkUploadNestoProductsAPI.as_view()