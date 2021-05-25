from WAMSApp.models import *
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import datetime
import sys
import json

# sorted(list(set(split(" "))),key=len,reverse=True)[:30] to fetch 30 distinct words with sorted reverse so that the, a ,is, from, words could easily eliminated from string

@receiver(post_save, sender=SuperCategory, dispatch_uid="create_seo_supercategory")
def create_seo_supercategory(sender, instance, **kwargs):
    website_group_obj = WebsiteGroup.objects.get(name="shopnesto")
    location_group_objs = LocationGroup.objects.filter(website_group=website_group_obj)
    super_category_obj = instance
    for location_group_obj in location_group_objs:
        if SEOSuperCategory.objects.filter(super_category=super_category_obj,location_group=location_group_obj).exists() == False:
            SEOSuperCategory.objects.create(
                super_category=super_category_obj,
                location_group=location_group_obj,
                seo_title=str(super_category_obj.name) + "_" + str(location_group_obj.name),
                seo_keywords=json.dumps(sorted(list(set(super_category_obj.description.split(" "))),key=len,reverse=True)[:30]),
                seo_description="",
                short_description="", 
                long_description="",
            )


@receiver(post_save, sender=Category, dispatch_uid="create_seo_category")
def create_seo_category(sender, instance, **kwargs):
    website_group_obj = WebsiteGroup.objects.get(name="shopnesto")
    location_group_objs = LocationGroup.objects.filter(website_group=website_group_obj)
    category_obj = instance
    for location_group_obj in location_group_objs:   
        if SEOCategory.objects.filter(category=category_obj,location_group=location_group_obj).exists() == False:
            SEOCategory.objects.create(
                category=category_obj,
                location_group=location_group_obj,
                seo_title=str(category_obj.name) + "_" + str(location_group_obj.name),
                seo_keywords=json.dumps(sorted(list(set(category_obj.description.split(" "))),key=len,reverse=True)[:30]),
                seo_description="",
                short_description="", 
                long_description="",     
            )


@receiver(post_save, sender=SubCategory, dispatch_uid="create_seo_subcategory")
def create_seo_subcategory(sender, instance, **kwargs):
    website_group_obj = WebsiteGroup.objects.get(name="shopnesto")
    location_group_objs = LocationGroup.objects.filter(website_group=website_group_obj)
    sub_category_obj = instance
    for location_group_obj in location_group_objs:
        if SEOSubCategory.objects.filter(sub_category=sub_category_obj,location_group=location_group_obj).exists() == False:
            SEOSubCategory.objects.create(
                sub_category=sub_category_obj,
                location_group=location_group_obj,
                seo_title=str(sub_category_obj.name) + "_" + str(location_group_obj.name),
                seo_keywords=json.dumps(sorted(list(set(sub_category_obj.description.split(" "))),key=len,reverse=True)[:30]),
                seo_description="",
                short_description="", 
                long_description="",  
            )


@receiver(post_save, sender=Brand, dispatch_uid="create_seobrand")
def create_seobrand(sender, instance, **kwargs):
    website_group_obj = WebsiteGroup.objects.get(name="shopnesto")
    location_group_objs = LocationGroup.objects.filter(website_group=website_group_obj)
    brand_obj = instance
    for location_group_obj in location_group_objs:
        if SEOBrand.objects.filter(brand=brand_obj,location_group=location_group_obj).exists() == False:
            SEOBrand.objects.create(
                brand=brand_obj,
                location_group=location_group_obj,
                seo_title=str(brand_obj.name) + "_" + str(location_group_obj.name),
                seo_keywords=json.dumps(sorted(list(set(brand_obj.description.split(" "))),key=len,reverse=True)[:30]),
                seo_description="",
                short_description="", 
                long_description="", 
            )


@receiver(post_save, sender=Brand, dispatch_uid="create_brand_supercategory_brand_instance")
def create_brand_supercategory_brand_instance(sender, instance, **kwargs):
    website_group_obj = WebsiteGroup.objects.get(name="shopnesto")
    location_group_objs = LocationGroup.objects.filter(website_group=website_group_obj)
    brand_obj = instance
    super_category_objs = website_group_obj.super_categories.all()
    for location_group_obj in location_group_objs:    
        for super_category_obj in super_category_objs:
            if BrandSuperCategory.objects.filter(super_category=super_category_obj,brand=brand_obj,location_group=location_group_obj).exists() == False:
                BrandSuperCategory.objects.create(
                    super_category=super_category_obj,
                    brand=brand_obj,
                    location_group=location_group_obj,
                    seo_title=str(brand_obj.name) + "_" + str(super_category_obj.name) + "_" + str(location_group_obj.name),
                    seo_keywords=json.dumps(sorted(list(set(super_category_obj.description.split(" ") + brand_obj.description.split(" "))),key=len,reverse=True)[:30]),
                    seo_description="",
                    short_description="", 
                    long_description="", 
                )


@receiver(post_save, sender=SuperCategory, dispatch_uid="create_brand_supercategory_supercategory_instance")
def create_brand_supercategory_supercategory_instance(sender, instance, **kwargs):
    website_group_obj = WebsiteGroup.objects.get(name="shopnesto")
    location_group_objs = LocationGroup.objects.filter(website_group=website_group_obj)
    brand_objs = website_group_obj.brands.all()
    super_category_obj = instance
    for location_group_obj in location_group_objs:    
        for brand_obj in brand_objs:
            if BrandSuperCategory.objects.filter(super_category=super_category_obj,brand=brand_obj,location_group=location_group_obj).exists() == False:
                BrandSuperCategory.objects.create(
                    super_category=super_category_obj,
                    brand=brand_obj,
                    location_group=location_group_obj,
                    seo_title=str(brand_obj.name) + "_" + str(super_category_obj.name) + "_" + str(location_group_obj.name),
                    seo_keywords=json.dumps(sorted(list(set(super_category_obj.description.split(" ") + brand_obj.description.split(" "))),key=len,reverse=True)[:30]),
                    seo_description="",
                    short_description="", 
                    long_description="", 
                )


@receiver(post_save, sender=Brand, dispatch_uid="create_brand_category_brand_instance")
def create_brand_category_brand_instance(sender, instance, **kwargs):
    website_group_obj = WebsiteGroup.objects.get(name="shopnesto")
    location_group_objs = LocationGroup.objects.filter(website_group=website_group_obj)
    brand_obj = instance
    category_objs = website_group_obj.categories.all()
    for location_group_obj in location_group_objs:    
        for category_obj in category_objs:
            if BrandCategory.objects.filter(category=category_obj,brand=brand_obj,location_group=location_group_obj).exists() == False:
                BrandCategory.objects.create(
                    category=category_obj,
                    brand=brand_obj,
                    location_group=location_group_obj,
                    seo_title=str(brand_obj.name) + "_" + str(category_obj.name) + "_" + str(location_group_obj.name),
                    seo_keywords=json.dumps(sorted(list(set(category_obj.description.split(" ") + brand_obj.description.split(" "))),key=len,reverse=True)[:30]),
                    seo_description="",
                    short_description="", 
                    long_description="", 
                )


@receiver(post_save, sender=Category, dispatch_uid="create_brand_category_category_instance")
def create_brand_category_category_instance(sender, instance, **kwargs):
    website_group_obj = WebsiteGroup.objects.get(name="shopnesto")
    location_group_objs = LocationGroup.objects.filter(website_group=website_group_obj)
    brand_objs = website_group_obj.brands.all()
    category_obj = instance
    for location_group_obj in location_group_objs:    
        for brand_obj in brand_objs:
            if BrandCategory.objects.filter(category=category_obj,brand=brand_obj,location_group=location_group_obj).exists() == False:
                BrandCategory.objects.create(
                    category=category_obj,
                    brand=brand_obj,
                    location_group=location_group_obj,
                    seo_title=str(brand_obj.name) + "_" + str(category_obj.name) + "_" + str(location_group_obj.name),
                    seo_keywords=json.dumps(sorted(list(set(category_obj.description.split(" ") + brand_obj.description.split(" "))),key=len,reverse=True)[:30]),
                    seo_description="",
                    short_description="", 
                    long_description="", 
                )


@receiver(post_save, sender=Brand, dispatch_uid="create_brand_subcategory_brand_instance")
def create_brand_subcategory_brand_instance(sender, instance, **kwargs):
    website_group_obj = WebsiteGroup.objects.get(name="shopnesto")
    location_group_objs = LocationGroup.objects.filter(website_group=website_group_obj)
    brand_obj = instance
    category_objs = website_group_obj.categories.all()
    sub_category_objs = SubCategory.objects.filter(category__in=category_objs)
    for location_group_obj in location_group_objs:    
        for sub_category_obj in sub_category_objs:
            if BrandSubCategory.objects.filter(sub_category=sub_category_obj,brand=brand_obj,location_group=location_group_obj).exists() == False:
                BrandSubCategory.objects.create(
                    sub_category=sub_category_obj,
                    brand=brand_obj,
                    location_group=location_group_obj,
                    seo_title=str(brand_obj.name) + "_" + str(sub_category_obj.name) + "_" + str(location_group_obj.name),
                    seo_keywords=json.dumps(sorted(list(set(sub_category_obj.description.split(" ") + brand_obj.description.split(" "))),key=len,reverse=True)[:30]),
                    seo_description="",
                    short_description="", 
                    long_description="", 
                )


@receiver(post_save, sender=SubCategory, dispatch_uid="create_brand_subcategory_subcategory_instance")
def create_brand_subcategory_subcategory_instance(sender, instance, **kwargs):
    website_group_obj = WebsiteGroup.objects.get(name="shopnesto")
    location_group_objs = LocationGroup.objects.filter(website_group=website_group_obj)
    brand_objs = website_group_obj.brands.all()
    sub_category_obj = instance
    for location_group_obj in location_group_objs:    
        for brand_obj in brand_objs:
            if BrandSubCategory.objects.filter(sub_category=sub_category_obj,brand=brand_obj,location_group=location_group_obj).exists() == False:
                BrandSubCategory.objects.create(
                    sub_category=sub_category_obj,
                    brand=brand_obj,
                    location_group=location_group_obj,
                    seo_title=str(brand_obj.name) + "_" + str(sub_category_obj.name) + "_" + str(location_group_obj.name),
                    seo_keywords=json.dumps(sorted(list(set(sub_category_obj.description.split(" ") + brand_obj.description.split(" "))),key=len,reverse=True)[:30]),
                    seo_description="",
                    short_description="", 
                    long_description=""
                )
