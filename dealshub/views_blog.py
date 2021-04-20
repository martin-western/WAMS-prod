import requests
import json
import logging
import datetime

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import AllowAny

from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models import Count
from django.conf import settings

from WAMSApp.models import *
from dealshub.models import *
from WAMSApp.utils import activitylog

logger = logging.getLogger(__name__)

class CsrfExemptSessionAuthentication(SessionAuthentication):

    def enforce_csrf(self, request):
        return


class CreateBlogPostAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("CreateBlogPostAPI: %s",str(data))
            if not isinstance(data,dict):
                data = json.loads(data)

            title = data["title"]
            headline = data["headline"] 
            body = data["body"]
            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)

            blog_post_obj = BlogPost.objects.create(
                title=title,
                headline=headline,
                location_group = location_group_obj,
                body=body)
            response["blogPostUuid"] = blog_post_obj.uuid
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateBlogPostAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class EditBlogPostAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("EditBlogPostAPI: %s",str(data))
            if not isinstance(data,dict):
                data = json.loads(data)

            title = data["title"]
            headline = data["headline"]
            body = data["body"]
            blog_post_uuid = data["blogPostUuid"]
            is_cover_image = data.get("isCoverImage",False)     

            blog_post_obj = BlogPost.objects.get(uuid=blog_post_uuid)

            blog_post_obj.title = title
            blog_post_obj.headline = headline
            blog_post_obj.body = body

            if is_cover_image:
                cover_image = data["coverImage"]
                image_obj = Image.objects.create(image=cover_image)
                blog_post_obj.cover_image = image_obj
            blog_post_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("EditBlogPostAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class UploadBlogPostImageAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("UploadBlogPostImageAPI: %s",str(data))
            if not isinstance(data,dict):
                data = json.loads(data)

            blog_post_image = data["blogPostImage"]
            image_obj = Image.objects.create(image=blog_post_image)

            response["imageUrl"] = image_obj.image.url
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UploadBlogPostImageAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class ModifyBlogPostStatusAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("ModifyBlogPostStatusAPI: %s",str(data))
            if not isinstance(data,dict):
                data = json.loads(data)

            blog_post_obj = BlogPost.objects.get(uuid=data["blogPostUuid"])
            blog_post_obj.is_published = data["isPublished"]
            blog_post_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ModifyBlogPostStatusAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddProductToBlogPostAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddProductToBlogPostAPI: %s",str(data))
            if not isinstance(data,dict):
                data = json.loads(data)

            blog_post_obj = BlogPost.objects.get(uuid=data["blogPostUuid"])
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=data["uuid"])
            blog_post_obj.products.add(dealshub_product_obj)
            blog_post_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddProductToBlogPostAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class RemoveProductFromBlogPostAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("RemoveProductFromBlogPostAPI: %s",str(data))
            if not isinstance(data,dict):
                data = json.loads(data)

            blog_post_obj = BlogPost.objects.get(uuid=data["blogPostUuid"])
            dealshub_product_obj = DealsHubProduct.objects.get(uuid=data["uuid"])
            blog_post_obj.products.remove(dealshub_product_obj)
            blog_post_obj.save()

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("RemoveProductFromBlogPostAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchBlogPostListAPI(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchBlogPostListAPI: %s",str(data))
            if not isinstance(data.json):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            blog_post_objs = BlogPost.objects.filter(location_group__uuid=location_group_uuid)

            blog_post_list = []

            for blog_post_obj in blog_post_objs:
                temp_dict = {}
                temp_dict["title"] = blog_post_obj.title
                temp_dict["headline"] = blog_post_obj.headline
                temp_dict["body"] = blog_post_obj.body
                temp_dict["uuid"] = blog_post_obj.uuid
                temp_dict["is_published"] = blog_post_obj.is_published
                temp_dict["cover_image"] = blog_post_obj.get_cover_image()

                blog_post_list.append(temp_dict)

            response["blogPostList"] = blog_post_list
            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchBlogPostListAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchBlogSectionTypesAPI(APIView):
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchBlogSectionTypesAPI: %s",str(data))
            if not isinstance(data.json):
                data = json.loads(data)

            blog_section_type_objs = BlogSectionType.objects.all()

            blog_section_types = blog_section_type_objs.values_list('name')

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchBlogSectionTypesAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class CreateBlogSectionAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("CreateBlogSectionAPI: %s",str(data))
            if not isinstance(data.json):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            location_group_obj = LocationGroup.objects.get(uuid=location_group_uuid)
            blog_section_type = data["BlogSectionType"]
            blog_section_type_obj = BlogSectionType.objects.filter(display_name=blog_section_type)

            blog_section_obj = BlogSection.objects.create(
                name=blog_section_name,
                order_index=order_index,
                location_group=location_group_obj,
                blog_section_type=blog_section_type_obj)

            response["BlogSectionUuid"] = blog_section_obj.uuid
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CreateBlogSectionAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class EditBlogSectionAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("EditBlogSectionAPI: %s",str(data))
            if not isinstance(data.json):
                data = json.loads(data)

            section_image = data.get("sectionImage","")
            section_name = data["sectionName"]

            blog_section_obj = BlogSection.objects.get(uuid=data["BlogSectionUuid"])
            blog_section_obj.name = section_name
            if section_image!="":
                image_obj = Image.objects.create(image=section_image)
                blog_section_obj.section_image = image_obj
            blog_section_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("EditBlogSectionAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class AddBlogPostToBlogSectionAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("AddBlogPostToBlogSectionAPI: %s",str(data))
            if not isinstance(data.json):
                data = json.loads(data)

            blog_section_obj = BlogSection.objects.get(uuid=data["blogSectionUuid"])
            blog_post_obj = BlogPost.objects.get(uuid=data["blogPostUuid"])
            blog_section_obj.blog_posts.add(blog_post_obj)
            blog_section_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("AddBlogPostToBlogSectionAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class RemoveBlogPostFromBlogSectionAPI(APIView):

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("RemoveBlogPostFromBlogSectionAPI: %s",str(data))
            if not isinstance(data.json):
                data = json.loads(data)

            blog_section_obj = BlogSection.objects.get(uuid=data["blogSectionUuid"])
            blog_post_obj = BlogPost.objects.get(uuid=data["blogPostUuid"])
            blog_section_obj.blog_posts.remove(blog_post_obj)
            blog_section_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("RemoveBlogPostFromBlogSectionAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class ModifyBlogSectionStatusAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("ModifyBlogSectionStatusAPI: %s",str(data))
            if not isinstance(data.json):
                data = json.loads(data)

            blog_section_obj = BlogSection.objects.get(uuid=data["BlogSectionUuid"])
            blog_section_obj.is_published = data["is_published"]
            blog_section_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("ModifyBlogSectionStatusAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SaveBlogSectionOrderIndexAPI(APIView):
    
    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SaveBlogSectionOrderIndexAPI: %s",str(data))
            if not isinstance(data.json):
                data = json.loads(data)

            # blog_section_obj = BlogSection.objects.get(uuid=data["BlogSectionUuid"])
            # blog_section_obj.is_published = data["is_published"]
            # blog_section_obj.save()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SaveBlogSectionOrderIndexAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchBlogSectionListAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,) 
    permission_classes = [AllowAny]    

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchBlogSectionListAPI: %s",str(data))
            if not isinstance(data.json):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            blog_section_objs = BlogSection.objects.filter(location_group__uuid=location_group_uuid).order_by(order_index)

            section_list = []
            for blog_section_obj in blog_section_objs:
                temp_dict = {}
                temp_dict["sectionName"] = blog_section_obj.name
                temp_dict["sectionType"] = str(blog_section_obj.blog_section_type)
                temp_dict["sectionImageUrl"] = ""
                if blog_section_obj.section_image!=None:
                    temp_dict["sectionImageUrl"] = blog_section_obj.section_image.image.url
                temp_dict["orderIndex"] = blog_section_obj.order_index
                temp_dict["is_published"] = blog_section_obj.is_published
                temp_dict["sectionBlogPosts"] = []
                blog_post_objs = blog_section_obj.products.filter(is_published=True)
                for blog_post_obj in blog_post_objs:
                    temp_dict2 = {}
                    temp_dict2["title"] = blog_post_obj.title
                    temp_dict2["author"] = blog_post_obj.author
                    temp_dict2["coverImageUrl"] = ""
                    if blog_post_obj.cover_image!=None:
                        temp_dict2["coverImageUrl"] = blog_post_obj.cover_image.image.url
                    temp_dict["sectionBlogPosts"].append(temp_dict2)
                section_list.append(temp_dict)

            response["section_list"] = section_list
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchBlogSectionListAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class SearchBlogPostAutoCompleteAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,) 
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("SearchBlogPostAutoCompleteAPI: %s",str(data))
            if not isinstance(data.json):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            blog_section_objs = BlogSection.objects.filter(location_group__uuid=location_group_uuid).filter(is_published=True).order_by(order_index)
            search_string = data["search_string"]

            blog_post_objs = BlogPost.objects.filter(location_group__uuid=location_group_uuid,is_published=True).filter(Q(title__icontains=search_string) | Q(author__icontains=search_string))
            blog_post_list = []
            for blog_post_obj in blog_post_objs:
                temp_dict = {}
                temp_dict["uuid"] = blog_post_obj.uuid
                temp_dict["title"] = blog_post_obj.title
                temp_dict["author"] = blog_post_obj.author
                blog_post_list.append(temp_dict)

            response["blogPostList"] = blog_post_list
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("SearchBlogPostAutoCompleteAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchBlogSectionHomePageAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,) 
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchBlogSectionHomePageAPI: %s",str(data))
            if not isinstance(data.json):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            blog_section_objs = BlogSection.objects.filter(location_group__uuid=location_group_uuid).filter(is_published=True).order_by(order_index)

            section_list = []
            for blog_section_obj in blog_section_objs:
                temp_dict = {}
                temp_dict["sectionName"] = blog_section_obj.name
                temp_dict["sectionType"] = str(blog_section_obj.blog_section_type)
                temp_dict["sectionImageUrl"] = ""
                if blog_section_obj.section_image!=None:
                    temp_dict["sectionImageUrl"] = blog_post_obj.section_image.image.url
                temp_dict["sectionBlogPosts"] = []
                blog_post_objs = blog_section_obj.products.filter(is_published=True)
                for blog_post_obj in blog_post_objs:
                    temp_dict2 = {}
                    temp_dict2["title"] = blog_post_obj.title
                    temp_dict2["body"] = blog_post_obj.body
                    temp_dict2["author"] = blog_post_obj.author
                    temp_dict2["coverImageUrl"] = ""
                    if blog_post_obj.section_image.cover_image!=None:
                        temp_dict2["coverImageUrl"] = blog_post_obj.cover_image.image.url
                    temp_dict["sectionBlogPosts"].append(temp_dict2)
                section_list.append(temp_dict)

            response["section_list"] = section_list
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchBlogSectionHomePageAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchBlogPostDetailsAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,) 
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchBlogPostDetailsAPI: %s",str(data))
            if not isinstance(data.json):
                data = json.loads(data)

            blog_post_obj = BlogPost.objects.get(uuid=data["blogPostUuid"])

            if blog_post_obj.is_published==False:
                response["message"] = "Blog Unpublished"
                return Response(data=response)
            response["author"] = blog_post_obj.author
            response["title"] = blog_post_obj.title
            response["body"] = blog_post_obj.body
            response["cover_image"] = blog_post_obj.get_cover_image()

            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchBlogPostDetailsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


class FetchAllBlogPostsAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,) 
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        try:
            data = request.data
            logger.info("FetchAllBlogPostsAPI: %s",str(data))
            if not isinstance(data.json):
                data = json.loads(data)

            location_group_uuid = data["locationGroupUuid"]
            blog_post_objs = BlogPost.objects.filter(location_group__uuid=location_group_uuid,is_published=True).order_by('date_created')

            blog_post_list = []
            for blog_post_obj in blog_section_objs:
                temp_dict = {}
                temp_dict["title"] = blog_post_obj.title
                temp_dict["author"] = blog_post_obj.author
                temp_dict["body"] = blog_post_obj.body
                temp_dict["cover_image"] = blog_post_obj.get_cover_image()
                blog_post_list.append(temp_dict)

            response["blog_post_list"] = blog_post_list
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("FetchAllBlogPostsAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


CreateBlogPost = CreateBlogPostAPI.as_view()

EditBlogPost = EditBlogPostAPI.as_view()

UploadBlogPostImage = UploadBlogPostImageAPI.as_view()

ModifyBlogPostStatus = ModifyBlogPostStatusAPI.as_view()

AddProductToBlogPost = AddProductToBlogPostAPI.as_view()

RemoveProductFromBlogPost = RemoveProductFromBlogPostAPI.as_view()

FetchBlogPostList = FetchBlogPostListAPI.as_view()

CreateBlogSection = CreateBlogSectionAPI.as_view()

EditBlogSection = EditBlogSectionAPI.as_view()

AddBlogPostToBlogSection = AddBlogPostToBlogSectionAPI.as_view()

RemoveBlogPostFromBlogSection = RemoveBlogPostFromBlogSectionAPI.as_view()

ModifyBlogSectionStatus = ModifyBlogSectionStatusAPI.as_view()

SaveBlogSectionOrderIndex = SaveBlogSectionOrderIndexAPI.as_view()

FetchBlogSectionList = FetchBlogSectionListAPI.as_view()

SearchBlogPostAutoComplete = SearchBlogPostAutoCompleteAPI.as_view()

FetchBlogSectionHomePage = FetchBlogSectionHomePageAPI.as_view()

FetchBlogPostDetails = FetchBlogPostDetailsAPI.as_view()

FetchAllBlogPosts = FetchAllBlogPostsAPI.as_view()