import requests
import json
import logging
import datetime

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import AllowAny

from dealshub.models import *
from dealshub.constants import *
from dealshub.utils import *
from dealshub.algolia.utils import *

logger = logging.getLogger(__name__)

class CsrfExemptSessionAuthentication(SessionAuthentication):

    def enforce_csrf(self, request):
        return


class SearchWIG3API(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SearchWIG3API: %s", str(data))

            search_string = data.get("name", "").strip()
            super_category_name = data.get("superCategory", "").strip()
            category_name = data.get("category", "").strip()
            sub_category_name = data.get("subcategory", "").strip()
            brand_name = data.get("brand", "").strip()
            page_type = data.get("page_type", "").strip()
            
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group

            dealshub_user_obj = None
            is_user_authenticated = True
            if location_group_obj.is_b2b==True:
                b2b_user_obj = None
                logger.info("REQUEST USER::: %s", str(request.user))
                if request.user != None and str(request.user)!="AnonymousUser":
                    logger.info("REQUEST USER: %s", str(request.user))
                    b2b_user_obj = B2BUser.objects.get(username = request.user.username)
                    dealshub_user_obj = DealsHubUser.objects.get(username = request.user.username)
                is_user_authenticated = check_account_status(b2b_user_obj)

            page_description = ""
            seo_title = ""
            seo_keywords = ""
            seo_description = ""
            short_description = ""
            long_description = ""

            try:
                if page_type=="super_category":
                    seo_super_category_obj = SEOSuperCategory.objects.get(super_category__name=super_category_name, location_group=location_group_obj)
                    page_description = seo_super_category_obj.page_description
                    seo_title = seo_super_category_obj.seo_title
                    seo_keywords = seo_super_category_obj.seo_keywords
                    seo_description = seo_super_category_obj.seo_description
                    short_description = seo_super_category_obj.short_description
                    long_description = seo_super_category_obj.long_description
                elif page_type=="category":
                    seo_category_obj = SEOCategory.objects.filter(category__name=category_name, location_group=location_group_obj)[0]
                    page_description = seo_category_obj.page_description
                    seo_title = seo_category_obj.seo_title
                    seo_keywords = seo_category_obj.seo_keywords
                    seo_description = seo_category_obj.seo_description
                    short_description = seo_category_obj.short_description
                    long_description = seo_category_obj.long_description
                elif page_type=="sub_category":
                    seo_sub_category_obj = SEOSubCategory.objects.filter(sub_category__name=sub_category_name, location_group=location_group_obj)[0]
                    page_description = seo_sub_category_obj.page_description
                    seo_title = seo_sub_category_obj.seo_title
                    seo_keywords = seo_sub_category_obj.seo_keywords
                    seo_description = seo_sub_category_obj.seo_description
                    short_description = seo_sub_category_obj.short_description
                    long_description = seo_sub_category_obj.long_description
                elif page_type=="brand":
                    seo_brand_obj = SEOBrand.objects.get(brand__name=brand_name, location_group=location_group_obj, brand__organization__name="WIG")
                    page_description = seo_brand_obj.page_description
                    seo_title = seo_brand_obj.seo_title
                    seo_keywords = seo_brand_obj.seo_keywords
                    seo_description = seo_brand_obj.seo_description
                    short_description = seo_brand_obj.short_description
                    long_description = seo_brand_obj.long_description
                elif page_type=="brand_super_category":
                    brand_obj = Brand.objects.get(name=brand_name, organization__name="WIG")
                    super_category_obj = SuperCategory.objects.get(name=super_category_name)
                    brand_super_category_obj = BrandSuperCategory.objects.get(brand=brand_obj, super_category=super_category_obj, location_group=location_group_obj)
                    page_description = brand_super_category_obj.page_description
                    seo_title = brand_super_category_obj.seo_title
                    seo_keywords = brand_super_category_obj.seo_keywords
                    seo_description = brand_super_category_obj.seo_description
                    short_description = brand_super_category_obj.short_description
                    long_description = brand_super_category_obj.long_description
                elif page_type=="brand_category":
                    brand_obj = Brand.objects.get(name=brand_name, organization__name="WIG")
                    category_obj = Category.objects.get(name=category_name)
                    brand_category_obj = BrandCategory.objects.get(brand=brand_obj, category=category_obj, location_group=location_group_obj)
                    page_description = brand_category_obj.page_description
                    seo_title = brand_category_obj.seo_title
                    seo_keywords = brand_category_obj.seo_keywords
                    seo_description = brand_category_obj.seo_description
                    short_description = brand_category_obj.short_description
                    long_description = brand_category_obj.long_description
                elif page_type=="brand_sub_category":
                    brand_obj = Brand.objects.get(name=brand_name, organization__name="WIG")
                    sub_category_obj = SubCategory.objects.get(name=sub_category_name)
                    brand_sub_category_obj = BrandSubCategory.objects.get(brand=brand_obj, sub_category=sub_category_obj, location_group=location_group_obj)
                    page_description = brand_sub_category_obj.page_description
                    seo_title = brand_sub_category_obj.seo_title
                    seo_keywords = brand_sub_category_obj.seo_keywords
                    seo_description = brand_sub_category_obj.seo_description
                    short_description = brand_sub_category_obj.short_description
                    long_description = brand_sub_category_obj.long_description

                response["page_description"] = page_description
                response["seo_title"] = seo_title
                response["seo_keywords"] = seo_keywords
                response["seo_description"] = seo_description
                response["short_description"] = short_description
                response["long_description"] = long_description
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SearchWIG3API: %s at %s", e, str(exc_tb.tb_lineno))
                response["page_description"] = ""
                response["seo_title"] = ""
                response["seo_keywords"] = ""
                response["seo_description"] = ""
                response["short_description"] = ""
                response["long_description"] = ""

            search = {}

            dealshub_product_objs = DealsHubProduct.objects.filter(location_group=location_group_obj,product__base_product__seller_sku=search_string,is_published=True).exclude(now_price=0).exclude(stock=0)
            if dealshub_product_objs.count() != 0:
                products = get_dealshub_product_details(dealshub_product_objs,dealshub_user_obj)
                is_available = False
                response["is_available"] = is_available
                response["totalPages"] = 1
                response["total_products"] = len(products)
                search['products'] = products
                response['search'] = search
                response["is_user_authenticated"] = is_user_authenticated
                response['status'] = 200
                return Response(data=response)

            search_data = {}
            search_data["search_string"] = search_string
            search_data["locationGroupUuid"] = location_group_obj.uuid
            if super_category_name!="ALL":
                search_data["superCategory"] = super_category_name
            else:
                search_data["superCategory"] = ""
            if category_name!="ALL":
                search_data["category"] = category_name
            else:
                search_data["category"] = ""
            if sub_category_name!="":
                search_data["subCategory"] = sub_category_name
            else:
                search_data["subCategory"] = ""

            search_data["brands"] = data.get("brand_filter", [])
            search_data["page"] = int(data.get("page", 1)) - 1
            search_data["pageSize"] = 50

            # Ranking
            search_data["ranking"] = 0
            sort_filter = data.get("sort_filter",{})
            if sort_filter.get("price", "")=="high-to-low":
                search_data["ranking"] = 1
            if sort_filter.get("price", "")=="low-to-high":
                search_data["ranking"] = -1

            try:
                search_result = search_algolia_index(search_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SearchWIG3API: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            if not isinstance(search_result, dict):
                search_result = json.loads(search_result)

            hits = search_result["hits"]
            temp_pk_list = []
            for hit in hits:
                temp_pk_list.append(hit["pk"])
            dealshub_product_objs = DealsHubProduct.objects.filter(pk__in=temp_pk_list).prefetch_related('product').prefetch_related('product__base_product').prefetch_related('promotion')
            dealshub_product_objs = list(dealshub_product_objs)
            dealshub_product_objs.sort(key=lambda t: temp_pk_list.index(t.pk))

            products = get_dealshub_product_details(dealshub_product_objs, dealshub_user_obj)
            currency = location_group_obj.location.currency

            is_available = True
            if search_result["page"] == search_result["nbPages"]-1:
                is_available = False
            response["is_available"] = is_available
            response["totalPages"] = search_result["nbPages"]
            response["total_products"] = search_result["nbHits"]
            search['products'] = products
            response['search'] = search
            response["is_user_authenticated"] = is_user_authenticated
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchWIG3API: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


class SearchWIG3AutoCompleteAPI(APIView):

    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SearchWIG3AutoCompleteAPI: %s", str(data))

            search_string = data.get("name", "").strip()

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            website_group_obj = location_group_obj.website_group
            search = {}

            search_data = {}
            search_data["search_string"] = search_string
            search_data["pageSize"] = 5
            search_data["page"] = 0

            try:
                search_result = search_algolia_index(search_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SearchWIG3AutoCompleteAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            if not isinstance(search_result, dict):
                search_result = json.loads(search_result)

            temp_pk_list = []
            for hit in hits:
                temp_pk_list.append(search_result["pk"])
            dealshub_product_objs = DealsHubProduct.objects.filter(pk__in=temp_pk_list).prefetch_related('product').prefetch_related('product__base_product').prefetch_related('promotion')
            dealshub_product_objs = list(dealshub_product_objs)
            dealshub_product_objs.sort(key=lambda t: temp_pk_list.index(t.pk))

            ind=0
            dealshub_product_list = []
            for dealshub_product_obj in dealshub_product_objs:
                temp_dict = {}
                temp_dict["highlightResult"] = search_result[ind]["_highlightResult"]
                temp_dict["name"] = search_result[ind]["productName"]
                temp_dict["sellerSKU"] = search_result[ind]["sellerSKU"]
                temp_dict["brand"] = search_result[ind]["brand"]
                temp_dict["heroImageUrl"] = dealshub_product_obj.display_image_url
                ind+=1
                dealshub_product_list.append(temp_dict)

            try:
                suggestion_result = search_algolia_suggestions(search_data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("SearchWIG3AutoCompleteAPI: %s at %s", e, str(exc_tb.tb_lineno))
                return Response(data=response)

            if not isinstance(suggestion_result, dict):
                search_result = json.loads(suggestion_result)

            search['products'] = dealshub_product_list
            response['search'] = search
            response['suggestions'] =  suggestion_result["hits"]
            response['facets'] = search_result["facets"]
            response['total_products'] = search_result["nbHits"]
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchWIG3AutoCompleteAPI: %s at %s", e, str(exc_tb.tb_lineno))
        
        return Response(data=response)


SearchWIG3 = SearchWIG3API.as_view()

SearchWIG3AutoComplete = SearchWIG3AutoCompleteAPI.as_view()