from WAMSApp.models import *
from dealshub.models import *
import xlsxwriter
import json
import logging
from django.utils import timezone
from django.core.mail import EmailMessage
from django.core.mail import get_connection, send_mail
from auditlog.models import *

from WAMSApp.utils import *
from WAMSApp.oc_reports import notify_user_for_report
from django.db.models import Count

logger = logging.getLogger(__name__)


def bulk_download_nesto_ecommerce_report(filename, uuid):
    try:
        logger.info('Nesto Ecommerce report start...')
        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        row = [ "No.",
                "Article Number",
                "barcode",
                "Language Key",
                "Product Type",
                "Super Category",
                "Category",
                "Sub Category",
                "Product Name",
                "Product Ecommerce Name",
                "Online",
                "Verified",
                "Vendor Category",
                "Product Long Description",
                "Weight/Volume",
                "Image Front",
                "Image Back",
                "Image Nutrition",
                "Image Product Content",
                "Image Side",
                "Image Supplier",
                "Image Lifestyle",
                "Image Ads",
                "Image Box",
                "Image HighLight",
                "Country Of Origin",
                "brand",
                "Storage Conditions",
                "Preparation and Usage",
                "Allergic Infromation",
                "Nutrient Facts",
                "Ingredients",
                "About Brand",
                "Related Article Nos",
                "UpSell Article Nos",
                "CrossSell Article Nos",
                "Primary keywords",
                "Secondary keywords"
                ]
        
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1})

        cnt=0
            
        colomn = 0
        for k in row:
            worksheet.write(cnt,colomn,k,header_format)
            colomn += 1
        
        nesto_product_objs = NestoProduct.objects.all()

        for nesto_product_obj in nesto_product_objs:
            try:           
                cnt += 1
        
                front_images = ""
                for front_image in nesto_product_obj.front_images.all():
                    front_images += str(front_image.image.url) + ", " 
                back_images = ""
                for back_image in nesto_product_obj.back_images.all():
                    back_images += str(back_image.image.url) + ", " 
                nutrition_images = ""
                for nutrition_image in nesto_product_obj.nutrition_images.all():
                    nutrition_images += str(nutrition_image.image.url) + ", " 
                product_content_images = ""
                for product_content_image in nesto_product_obj.product_content_images.all():
                    product_content_images += str(product_content_image.image.url) + ", " 
                side_images = ""
                for side_image in nesto_product_obj.side_images.all():
                    side_images += str(side_image.image.url) + ", " 
                supplier_images = ""
                for supplier_image in nesto_product_obj.supplier_images.all():
                    supplier_images += str(supplier_image.image.url) + ", " 
                lifestyle_images = ""
                for lifestyle_image in nesto_product_obj.lifestyle_images.all():
                    lifestyle_images += str(lifestyle_image.image.url) + ", " 
                ads_images = ""
                for ads_image in nesto_product_obj.ads_images.all():
                    ads_images += str(ads_image.image.url) + ", " 
                box_images = ""
                for box_image in nesto_product_obj.box_images.all():
                    box_images += str(box_image.image.url) + ", " 
                highlight_images = ""
                for highlight_image in nesto_product_obj.highlight_images.all():
                    highlight_images += str(highlight_image.image.url) + ", " 

                related_article_nos = ""
                for substitute_product in nesto_product_obj.substitute_products.all():
                    related_article_nos += str(substitute_product.barcode) + ", "
                upsell_article_nos = ""
                for upsell_product in nesto_product_obj.upselling_products.all():
                    upsell_article_nos += str(upsell_product.barcode) + ", "
                crosssell_article_nos = ""
                for crosssell_product in nesto_product_obj.cross_selling_products.all():
                    crosssell_article_nos += str(crosssell_product.barcode) + ", "
                
                # nutrition_facts = json.loads(nesto_product_obj.nutrition_facts)
                # nutrition_facts_string = ""
                # for nutrition_fact in nutrition_facts:
                #     for nutrition_fact_key in nutrition_fact.keys():
                #         nutrition_facts_string += str(nutrition_fact_key) + "=" + str(nutrition_fact[nutrition_fact_key]) + ", "

                common_row = ["" for i in range(len(row))]
                common_row[0] = str(cnt)
                common_row[1] = str(nesto_product_obj.article_number)
                common_row[2] = str(nesto_product_obj.barcode)
                common_row[3] = nesto_product_obj.language_key
                common_row[4] = "simple"
                common_row[5] = nesto_product_obj.sub_category.category.super_category.name if nesto_product_obj.sub_category!=None else ""
                common_row[6] = nesto_product_obj.sub_category.category.name if nesto_product_obj.sub_category!=None else ""
                common_row[7] = nesto_product_obj.sub_category.name if nesto_product_obj.sub_category!=None else ""
                common_row[8] = nesto_product_obj.product_name
                common_row[9] = nesto_product_obj.product_name_ecommerce
                common_row[10] = str(nesto_product_obj.is_online)
                common_row[11] = str(nesto_product_obj.is_verified)
                common_row[12] = nesto_product_obj.vendor_category
                common_row[13] = nesto_product_obj.product_description
                common_row[14] = nesto_product_obj.weight_volume
                common_row[15] = front_images[:-2]
                common_row[16] = back_images[:-2]
                common_row[17] = nutrition_images[:-2]
                common_row[18] = product_content_images[:-2]
                common_row[19] = side_images[:-2]
                common_row[20] = supplier_images[:-2]
                common_row[21] = lifestyle_images[:-2]
                common_row[22] = ads_images[:-2]
                common_row[23] = box_images[:-2]
                common_row[24] = highlight_images[:-2]
                common_row[25] = nesto_product_obj.country_of_origin
                common_row[26] = nesto_product_obj.brand.name if nesto_product_obj.brand!=None else ""
                common_row[27] = nesto_product_obj.storage_condition
                common_row[28] = nesto_product_obj.preparation_and_usage
                common_row[29] = nesto_product_obj.allergic_information
                common_row[30] = nesto_product_obj.nutrition_facts
                common_row[31] = nesto_product_obj.ingredients
                common_row[32] = nesto_product_obj.brand.description if nesto_product_obj.brand!=None else ""
                common_row[33] = related_article_nos[:-2]
                common_row[34] = upsell_article_nos[:-2]
                common_row[35] = crosssell_article_nos[:-2]
                common_row[36] = ','.join(json.loads(nesto_product_obj.primary_keywords))
                common_row[37] = ','.join(json.loads(nesto_product_obj.secondary_keywords))

                colnum = 0
                for k in common_row:
                    worksheet.write(cnt, colnum, k)
                    colnum += 1

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("Error bulk_download_nesto_ecommerce_report %s %s", e, str(exc_tb.tb_lineno))
        
        workbook.close()

        oc_report_obj = OCReport.objects.get(uuid=uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

        notify_user_for_report(oc_report_obj)
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error bulk_download_nesto_ecommerce_report %s %s", e, str(exc_tb.tb_lineno))


def bulk_download_nesto_detailed_product_report(filename, uuid,nesto_product_objs=None):
    try:
        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        row = ["Sr. No.",
               "Article ID",
               "Barcode",
               "Product Name",
               "Product Name Ecommerce",
               "UOM",
               "Language Key",
               "Brand",
               "Weight/Volume",
               "Online",
               "Verified",
               "Vendor Category",
               "Country of Origin",
               "Highlights",
               "Storage Condition",
               "Preparation and Usage",
               "Allergic Information",
               "Product Description",
               "SubCategory Code",
               "Product Length",
               "Product Length_metric",
               "Product Width",
               "Product Width Metric",
               "Product Height",
               "Product Height Metric",
               "Nutrition Facts",
               "Ingredients",
               "Return Days",
               "Front Images",
               "Back Images",
               "Side Images",
               "Nutrition Images",
               "Product Content Images",
               "Supplier Images",
               "Lifestyle Images",
               "Ads Images",
               "Box Images",
               "Highlight Images",
               "Primary keywords",
               "Secondary keywords"
        ]

        cnt = 0
        colnum = 0
        for k in row:
            worksheet.write(cnt, colnum, k)
            colnum += 1
            
        pp = NestoProduct.objects.all()
        if nesto_product_objs!=None:
            pp = nesto_product_objs
        for p in pp:
            try:
                cnt += 1
                print("Cnt=", cnt)
                common_row = ["" for i in range(len(row))]
                common_row[0] = str(cnt)
                common_row[1] = str(p.article_number)
                common_row[2] = str(p.barcode)
                common_row[3] = str(p.product_name)
                common_row[4] = str(p.product_name_ecommerce)
                common_row[5] = str(p.uom)
                common_row[6] = str(p.language_key)
                common_row[7] = str(p.brand.name)
                common_row[8] = str(p.weight_volume)
                common_row[9] = str(p.is_online)
                common_row[10] = str(p.is_verified)
                common_row[11] = p.vendor_category
                common_row[12] = str(p.country_of_origin)
                common_row[13] = str(p.highlights)
                common_row[14] = str(p.storage_condition)
                common_row[15] = str(p.preparation_and_usage)
                common_row[16] = str(p.allergic_information)
                common_row[17] = str(p.product_description)
                common_row[18] = "NA" if p.sub_category==None else str(p.sub_category.erp_id)
                dimensions = json.loads(p.dimensions)
                common_row[19] = str(dimensions["product_length"])
                common_row[20] = str(dimensions["product_length_metric"])
                common_row[21] = str(dimensions["product_width"])
                common_row[22] = str(dimensions["product_width_metric"])
                common_row[23] = str(dimensions["product_height"])
                common_row[24] = str(dimensions["product_height_metric"])
                common_row[25] = str(p.nutrition_facts)
                common_row[26] = str(p.ingredients)
                common_row[27] = str(p.return_days)
                common_row[28] = str(p.front_images.count())
                common_row[29] = str(p.back_images.count())
                common_row[30] = str(p.side_images.count())
                common_row[31] = str(p.nutrition_images.count())
                common_row[32] = str(p.product_content_images.count())
                common_row[33] = str(p.supplier_images.count())
                common_row[34] = str(p.lifestyle_images.count())
                common_row[35] = str(p.ads_images.count())
                common_row[36] = str(p.box_images.count())
                common_row[37] = str(p.highlight_images.count())
                common_row[38] = ','.join(json.loads(p.primary_keywords))
                common_row[39] = ','.join(json.loads(p.secondary_keywords))
                colnum = 0
                for k in common_row:
                    worksheet.write(cnt, colnum, k)
                    colnum += 1
            except Exception as e:
                print("Error", str(e))

        workbook.close()

        oc_report_obj = OCReport.objects.get(uuid=uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

        notify_user_for_report(oc_report_obj)
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error bulk_download_nesto_detailed_product_report %s %s", e, str(exc_tb.tb_lineno))


def nesto_products_summary_report(filename, uuid):
    try:
        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        row = ["Products",
           "Front Images",
           "Back Images",
           "Side Images",
           "Nutrition Images",
           "Product Content Images",
           "Supplier Images",
           "Lifestyle Images",
           "Ads Images",
           "Box Images",
           "Highlight Images",
           "Article Number",
           "Product Name",
           "Barcode",
           "UOM",
           "Language Key",
           "Brand",
           "Weight Volume",
           "Country Of Origin",
           "Highlights",
           "Storage Condition",
           "Preparation and Usage",
           "Allergic Information",
           "Product Description",
           "Nutrition Facts",
           "Ingredients",
           "Return Days"]
        
        total_products = NestoProduct.objects.count()
        front_images = NestoProduct.objects.annotate(num_images=Count('front_images')).filter(num_images__gt=0).count()
        back_images = NestoProduct.objects.annotate(num_images=Count('back_images')).filter(num_images__gt=0).count()
        side_images = NestoProduct.objects.annotate(num_images=Count('side_images')).filter(num_images__gt=0).count()
        nutrition_images = NestoProduct.objects.annotate(num_images=Count('nutrition_images')).filter(num_images__gt=0).count()
        product_content_images = NestoProduct.objects.annotate(num_images=Count('product_content_images')).filter(num_images__gt=0).count()
        supplier_images = NestoProduct.objects.annotate(num_images=Count('supplier_images')).filter(num_images__gt=0).count()
        lifestyle_images = NestoProduct.objects.annotate(num_images=Count('lifestyle_images')).filter(num_images__gt=0).count()
        ads_images = NestoProduct.objects.annotate(num_images=Count('ads_images')).filter(num_images__gt=0).count()
        box_images = NestoProduct.objects.annotate(num_images=Count('box_images')).filter(num_images__gt=0).count()
        highlight_images = NestoProduct.objects.annotate(num_images=Count('highlight_images')).filter(num_images__gt=0).count()
        article_number = NestoProduct.objects.exclude(article_number="").count()
        product_name = NestoProduct.objects.exclude(product_name="").count()
        barcode = NestoProduct.objects.exclude(barcode="").count()
        uom = NestoProduct.objects.exclude(uom="").count()
        language_key = NestoProduct.objects.exclude(language_key="").count()
        brand = NestoProduct.objects.exclude(brand=None).count()
        weight_volume = NestoProduct.objects.exclude(weight_volume="").count()
        country_of_origin = NestoProduct.objects.exclude(country_of_origin="").count()
        highlights = NestoProduct.objects.exclude(highlights="").count()
        storage_condition = NestoProduct.objects.exclude(storage_condition="").count()
        preparation_and_usage = NestoProduct.objects.exclude(preparation_and_usage="").count()
        allergic_information = NestoProduct.objects.exclude(allergic_information="").count()
        product_description = NestoProduct.objects.exclude(product_description="").count()
        nutrition_facts = NestoProduct.objects.exclude(nutrition_facts="").count()
        ingredients = NestoProduct.objects.exclude(ingredients="").count()
        return_days = NestoProduct.objects.exclude(return_days="").count()
        rod = [total_products,
           front_images,
           back_images,
           side_images,
           nutrition_images,
           product_content_images,
           supplier_images,
           lifestyle_images,
           ads_images,
           box_images,
           highlight_images,
           article_number,
           product_name,
           barcode,
           uom,
           language_key,
           brand,
           weight_volume,
           country_of_origin,
           highlights,
           storage_condition,
           preparation_and_usage,
           allergic_information,
           product_description,
           nutrition_facts,
           ingredients,
           return_days]
        colnum = 0
        for i in range(len(row)):
            worksheet.write(i, 0, row[i])
            worksheet.write(i, 1, rod[i])
        workbook.close()

        oc_report_obj = OCReport.objects.get(uuid=uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

        notify_user_for_report(oc_report_obj)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error nesto_products_summary_report %s %s", e, str(exc_tb.tb_lineno))

def nesto_image_bucket_report(filename, uuid):

    try:
        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        row = ["Barcode",
               "store_view_code",
               "attribute_set_code",
               "product_type",
               "product_websites",
               "base_image",
               "base_image_label",
               "small_image",
               "small_image_label",
               "thumbnail_image",
               "thumbnail_image_label",
               "swatch_image",
               "swatch_image_label"]

        cnt = 0
        colnum = 0
        for k in row:
            worksheet.write(cnt, colnum, k)
            colnum += 1
        
        pp = NestoProduct.objects.all().annotate(img_cnt=Count('front_images')).exclude(img_cnt=0)
        for p in pp:
            try:
                cnt += 1
                common_row = ["" for i in range(len(row))]
                #sku = "8042-"+(18-len(p.article_number))*"0" +p.article_number
                # if p.uom!="":
                #     sku += "-"+p.uom
                image_obj = p.front_images.all()[0]
                common_row[0] = str(p.barcode)
                common_row[1] = str("")
                common_row[2] = str("Default")
                common_row[3] = str("simple")
                common_row[4] = str("ajman")
                common_row[5] = str(image_obj.image.url)
                common_row[6] = str("Image")
                common_row[7] = str(image_obj.mid_image.url)
                common_row[8] = str("Image")
                common_row[9] = str(image_obj.small_image.url)
                common_row[10] = str("Image")
                common_row[11] = str(image_obj.thumbnail.url)
                common_row[12] = str("Image")

                colnum = 0
                for k in common_row:
                    worksheet.write(cnt, colnum, k)
                    colnum += 1
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("Error nesto_image_bucket_report %s %s", e, str(exc_tb.tb_lineno))

        workbook.close()

        oc_report_obj = OCReport.objects.get(uuid=uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

        notify_user_for_report(oc_report_obj)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error nesto_image_bucket_report %s %s", e, str(exc_tb.tb_lineno))