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

from django.db.models import Count

logger = logging.getLogger(__name__)


def notify_user_for_report(oc_report_obj):

    if oc_report_obj.created_by.email=="":
        return

    try:
        body = """
            This is to inform you that your requested report has been generated on Omnycomm.
            Report note: """+ str(oc_report_obj.note) +"""
        """
        with get_connection(
            host="smtp.gmail.com",
            port=587, 
            username="nisarg@omnycomm.com", 
            password="verjtzgeqareribg",
            use_tls=True) as connection:
            email = EmailMessage(subject='Omnycomm Report Generated', 
                                 body=body,
                                 from_email='nisarg@omnycomm.com',
                                 to=[oc_report_obj.created_by.email],
                                 connection=connection)
            email.attach_file(oc_report_obj.filename)
            email.send(fail_silently=True)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error notify_user_for_report %s %s", e, str(exc_tb.tb_lineno))

def email_daily_sales_report_to_user(oc_report_obj):

    if oc_report_obj.created_by.email=="":
        return

    try:
        body = """
            This is to inform you that your requested report has been generated on Omnycomm.
            Report note: """+ str(oc_report_obj.note) +"""
        """
        with get_connection(
            host="smtp.gmail.com",
            port=587, 
            username="nisarg@omnycomm.com", 
            password="verjtzgeqareribg",
            use_tls=True) as connection:
            email = EmailMessage(subject='Omnycomm Daily Sales Report Generated', 
                                 body=body,
                                 from_email='nisarg@omnycomm.com',
                                 to=["fathimasamah@westernint.com","shahanas@westernint.com","nawas@westernint.com","wigme@westernint.com","hari.pk@westernint.com","arsal.k@westernint.com","support@westernint.com","support@wigme.com","rikas.k@westernint.com"],
                                 cc=["jay@omnycomm.com", "animesh.kumar@omnycomm.com"],
                                #  to=["hari.pk@westernint.com"],
                                #  cc=["fathimasamah@westernint.com", "shahanas@westernint.com", "wigme@westernint.com"],
                                 connection=connection)
            email.attach_file(oc_report_obj.filename)
            email.send(fail_silently=True)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error email_daily_sales_report_to_user %s %s", e, str(exc_tb.tb_lineno))

def create_mega_bulk_oc_report(filename, uuid, brand_list, product_uuid_list="", organization_obj=None):

    product_objs = Product.objects.filter(base_product__brand__name__in=brand_list, base_product__brand__organization=organization_obj)

    if product_uuid_list!="": 
        product_objs = product_objs.filter(uuid__in=product_uuid_list)

    workbook = xlsxwriter.Workbook('./'+filename)

    worksheet = workbook.add_worksheet()

    row = ["Sr. No.",
           "Product ID*",
           "Product Name*",
           "Brand*",
           "Super Category",
           "Category*",
           "Sub Category*",
           "Seller SKU*",
           "Manufacturer",
           "M. Part Number",
           "Product ID Type*",
           "Description",
           "Feature 1",
           "Feature 2",
           "Feature 3",
           "Feature 4",
           "Feature 5",
           "Color",
           "Color Map",
           "Material Type",
           "Standard Price",
           "MOQ",
           "Barcode",
           "Export Qty Length",
           "Export Qty Length Metric",
           "Export Qty Breadth",
           "Export Qty Breadth Metric",
           "Export Qty Height",
           "Export Qty Height Metric",
           "Export Carton CBM Length",
           "Export Carton CBM Length Metric",
           "Export Carton CBM Breadth",
           "Export Carton CBM Breadth Metric",
           "Export Carton CBM Height",
           "Export Carton CBM Height Metric",
           "Product Dimension Length",
           "Product Dimension Length Metric",
           "Product Dimension Breadth",
           "Product Dimension Breadth Metric",
           "Product Dimension Height",
           "Product Dimension Height Metric",
           "GiftBox Length",
           "GiftBox Length Metric",
           "GiftBox Breadth",
           "GiftBox Breadth Metric",
           "GiftBox Height",
           "GiftBox Height Metric",
           "Main Image",
           "Sub Image 1",
           "Sub Image 2",
           "Sub Image 3",
           "Sub Image 4",
           "Sub Image 5",
           "Sub Image 6",
           "Sub Image 7",
           "Sub Image 8",
           "Sub Image 9",
           "Sub Image 10",
           "White Background Image 1",
           "White Background Image 2",
           "White Background Image 3",
           "White Background Image 4",
           "White Background Image 5",
           "White Background Image 6",
           "White Background Image 7",
           "White Background Image 8",
           "White Background Image 9",
           "White Background Image 10",
           "PFL Image 1",
           "PFL Image 2",
           "PFL Image 3",
           "PFL Image 4",
           "PFL Image 5",
           "PFL Image 6",
           "PFL Image 7",
           "PFL Image 8",
           "PFL Image 9",
           "PFL Image 10",
           "Lifestyle Image 1",
           "Lifestyle Image 2",
           "Lifestyle Image 3",
           "Lifestyle Image 4",
           "Lifestyle Image 5",
           "Lifestyle Image 6",
           "Lifestyle Image 7",
           "Lifestyle Image 8",
           "Lifestyle Image 9",
           "Lifestyle Image 10",
           "Certificate Image 1",
           "Certificate Image 2",
           "Certificate Image 3",
           "Certificate Image 4",
           "Certificate Image 5",
           "Certificate Image 6",
           "Certificate Image 7",
           "Certificate Image 8",
           "Certificate Image 9",
           "Certificate Image 10",
           "Giftbox Image 1",
           "Giftbox Image 2",
           "Giftbox Image 3",
           "Giftbox Image 4",
           "Giftbox Image 5",
           "Giftbox Image 6",
           "Giftbox Image 7",
           "Giftbox Image 8",
           "Giftbox Image 9",
           "Giftbox Image 10",
           "Diecut Image 1",
           "Diecut Image 2",
           "Diecut Image 3",
           "Diecut Image 4",
           "Diecut Image 5",
           "Diecut Image 6",
           "Diecut Image 7",
           "Diecut Image 8",
           "Diecut Image 9",
           "Diecut Image 10",
           "A+ Content Image 1",
           "A+ Content Image 2",
           "A+ Content Image 3",
           "A+ Content Image 4",
           "A+ Content Image 5",
           "A+ Content Image 6",
           "A+ Content Image 7",
           "A+ Content Image 8",
           "A+ Content Image 9",
           "A+ Content Image 10",
           "Ads Image 1",
           "Ads Image 2",
           "Ads Image 3",
           "Ads Image 4",
           "Ads Image 5",
           "Ads Image 6",
           "Ads Image 7",
           "Ads Image 8",
           "Ads Image 9",
           "Ads Image 10",
           "Unedited Image 1",
           "Unedited Image 2",
           "Unedited Image 3",
           "Unedited Image 4",
           "Unedited Image 5",
           "Unedited Image 6",
           "Unedited Image 7",
           "Unedited Image 8",
           "Unedited Image 9",
           "Unedited Image 10",
           "Transparent Image 1",
           "Transparent Image 2",
           "Transparent Image 3",
           "Transparent Image 4",
           "Transparent Image 5",
           "Transparent Image 6",
           "Transparent Image 7",
           "Transparent Image 8",
           "Transparent Image 9",
           "Transparent Image 10",
           "Is Amazon UK Channel",
           "Product Name",
           "Amazon UK Product Description*",
           "Attribute 1",
           "Attribute 2",
           "Attribute 3",
           "Attribute 4",
           "Attribute 5",
           "Category*",
           "SubCategory",
           "Parentage",
           "Parent SKU",
           "Relationship Type",
           "Variation Theme",
           "Feed Product Type",
           "Update Delete",
           "Recommended Browse Nodes",
           "Search Terms",
           "Enclosure Material",
           "Cover Material Type",
           "Special Feature 1",
           "Special Feature 2",
           "Special Feature 3",
           "Special Feature 4",
           "Special Feature 5",
           "Sale Price",
           "Sale From",
           "Sale End",
           "Wattage",
           "Wattage Metric",
           "Item Count",
           "Item Count Metric",
           "Item Condition Note",
           "MOQ",
           "No. Of. Items",
           "Condition Type",
           "Package Length",
           "Package Length Metric",
           "Package Width",
           "Package Width Metric",
           "Package Height",
           "Package Height Metric",
           "Package Weight",
           "Package Weight Metric",
           "Package Quantity",
           "Shipping Weight",
           "Shipping Weight Metric",
           "Item Display Weight",
           "Item Display Weight Metric",
           "Item Display Volume",
           "Item Display Volume Metric",
           "Item Display Length",
           "Item Display Length Metric",
           "Item Display Width",
           "Item Display Width Metric",
           "Item Display Height",
           "Item Display Height Metric",
           "Item Weight",
           "Item Weight Metric",
           "Item Length",
           "Item Length Metric",
           "Item Width",
           "Item Width Metric",
           "Item Height",
           "Item Height Metric",
           "Is Amazon UK Verified",
           "Is Amazon UAE Channel",
           "Product Name",
           "Amazon UAE Product Description*",
           "Attribute 1",
           "Attribute 2",
           "Attribute 3",
           "Attribute 4",
           "Attribute 5",
           "Category*",
           "SubCategory",
           "Feed Product Type",
           "Recommended Browse Nodes",
           "Update Delete",
           "Is Amazon UAE Verified",
           "Is Ebay Product",
           "Product Name",
           "Ebay Product Description*",
           "Attribute 1",
           "Attribute 2",
           "Attribute 3",
           "Attribute 4",
           "Attribute 5",
           "Category*",
           "SubCategory",
           "Is Ebay Verified",
           "Is Noon Product",
           "Product Name",
           "Noon Product Description*",
           "Product Type",
           "Product SubType",
           "Partner SKU",
           "Category*",
           "SubCategory",
           "Model Number",
           "Model Name",
           "Attribute 1",
           "Attribute 2",
           "Attribute 3",
           "Attribute 4",
           "Attribute 5",
           "MSRP AE",
           "MSRP AE Unit",
           "Is Noon Verified"]

    cnt = 0
        
    colnum = 0
    for k in row:
        worksheet.write(cnt, colnum, k)
        colnum += 1
    cnt = 1
    for product in product_objs:
        common_row = ["" for i in range(266)]
        try:
            common_row[0] = str(cnt)
            common_row[1] = product.product_id
            common_row[2] = product.product_name
            common_row[3] = str(product.base_product.brand)
            common_row[4] = str(product.base_product.category.super_category)
            common_row[5] = str(product.base_product.category)
            common_row[6] = str(product.base_product.sub_category)
            common_row[7] = str(product.base_product.seller_sku)
            common_row[8] = str(product.base_product.manufacturer)
            common_row[9] = str(product.base_product.manufacturer_part_number)
            common_row[10] = str(product.product_id_type)
            common_row[11] = str(product.get_non_html_description())
            product_features = json.loads(product.pfl_product_features)[:5]
            for i in range(len(product_features)):
                common_row[12+i] = product_features[i]
            common_row[17] = str(product.color)
            common_row[18] = str(product.color_map)
            common_row[19] = str(product.material_type)
            common_row[20] = "" if product.standard_price==None else str(product.standard_price)
            common_row[21] = "" if product.quantity==None else str(product.quantity)
            common_row[22] = "" if product.barcode_string==None else str(product.barcode_string)
            dimensions = json.loads(product.base_product.dimensions)
            common_row[23] = str(dimensions.get("export_carton_quantity_l", ""))
            common_row[24] = str(dimensions.get("export_carton_quantity_l_metric", ""))
            common_row[25] = str(dimensions.get("export_carton_quantity_b",""))
            common_row[26] = str(dimensions.get("export_carton_quantity_b_metric", ""))
            common_row[27] = str(dimensions.get("export_carton_quantity_h", ""))
            common_row[28] = str(dimensions.get("export_carton_quantity_h_metric", ""))
            common_row[29] = str(dimensions.get("export_carton_crm_l", ""))
            common_row[30] = str(dimensions.get("export_carton_crm_l_metric", ""))
            common_row[31] = str(dimensions.get("export_carton_crm_b", ""))
            common_row[32] = str(dimensions.get("export_carton_crm_b_metric", ""))
            common_row[33] = str(dimensions.get("export_carton_crm_h", ""))
            common_row[34] = str(dimensions.get("export_carton_crm_h_metric", ""))
            common_row[35] = str(dimensions.get("product_dimension_l", ""))
            common_row[36] = str(dimensions.get("product_dimension_l_metric", ""))
            common_row[37] = str(dimensions.get("product_dimension_b", ""))
            common_row[38] = str(dimensions.get("product_dimension_b_metric", ""))
            common_row[39] = str(dimensions.get("product_dimension_h", ""))
            common_row[40] = str(dimensions.get("product_dimension_h_metric", ""))
            common_row[41] = str(dimensions.get("giftbox_l", ""))
            common_row[42] = str(dimensions.get("giftbox_l_metric", ""))
            common_row[43] = str(dimensions.get("giftbox_b", ""))
            common_row[44] = str(dimensions.get("giftbox_b_metric", ""))
            common_row[45] = str(dimensions.get("giftbox_h", ""))
            common_row[46] = str(dimensions.get("giftbox_h_metric", ""))
            try:
                main_images = MainImages.objects.get(product=product, is_sourced=True)
                main_image = main_images.main_images.all()[0]
                common_row[47] = main_image.image.image.url
            except Exception as e:
                pass
            try:
                sub_images = SubImages.objects.get(product=product, is_sourced=True)
                sub_images = sub_images.sub_images.all()[:10]
                iterr = 0
                for sub_image in sub_images:
                    common_row[48+iterr] = sub_image.image.image.url
                    iterr += 1
            except Exception as e:
                pass
            try:
                iterr = 0
                for image in product.white_background_images.all()[:10]:
                    common_row[58+iterr] = image.image.url
                    iterr += 1
            except Exception as e:
                pass
            try:            
                iterr = 0
                for image in product.pfl_images.all()[:10]:
                    common_row[68+iterr] = image.image.url
                    iterr += 1
            except Exception as e:
                pass
            try:
                iterr = 0
                for image in product.lifestyle_images.all()[:10]:
                    common_row[78+iterr] = image.image.url
                    iterr += 1
            except Exception as e:
                pass
            try:
                iterr = 0
                for image in product.certificate_images.all()[:10]:
                    common_row[88+iterr] = image.image.url
                    iterr += 1
            except Exception as e:
                pass
            try:
                iterr = 0
                for image in product.giftbox_images.all()[:10]:
                    common_row[98+iterr] = image.image.url
                    iterr += 1
            except Exception as e:
                pass
            try:
                iterr = 0
                for image in product.diecut_images.all()[:10]:
                    common_row[108+iterr] = image.image.url
                    iterr += 1
            except Exception as e:
                pass
            try:
                iterr = 0
                for image in product.aplus_content_images.all()[:10]:
                    common_row[118+iterr] = image.image.url
                    iterr += 1
            except Exception as e:
                pass
            try:
                iterr = 0
                for image in product.ads_images.all()[:10]:
                    common_row[128+iterr] = image.image.url
                    iterr += 1
            except Exception as e:
                pass
            try:
                iterr = 0
                for image in product.base_product.unedited_images.all()[:10]:
                    common_row[138+iterr] = image.image.url
                    iterr += 1
            except Exception as e:
                pass
            try:
                iterr = 0
                for image in product.transparent_images.all()[:10]:
                    common_row[148+iterr] = image.image.url
                    iterr += 1
            except Exception as e:
                pass
            ############################################ Amazon UK
            amazon_uk_product_json = json.loads(product.channel_product.amazon_uk_product_json)
            common_row[158] = str(product.channel_product.is_amazon_uk_product_created)
            common_row[159] = str(amazon_uk_product_json.get("product_name", ""))
            common_row[160] = str(amazon_uk_product_json.get("product_description", ""))
            attributes = amazon_uk_product_json.get("product_attribute_list", [])[:5]
            for i in range(len(attributes)):
                common_row[161+i] = str(attributes[i])
            common_row[166] = str(amazon_uk_product_json.get("category", ""))
            common_row[167] = str(amazon_uk_product_json.get("sub_category", ""))
            common_row[168] = str(amazon_uk_product_json.get("parentage", ""))
            common_row[169] = str(amazon_uk_product_json.get("parent_sku", ""))
            common_row[170] = str(amazon_uk_product_json.get("relationship_type", ""))
            common_row[171] = str(amazon_uk_product_json.get("variation_theme", ""))
            common_row[172] = str(amazon_uk_product_json.get("feed_product_type", ""))
            common_row[173] = str(amazon_uk_product_json.get("update_delete", ""))
            common_row[174] = str(amazon_uk_product_json.get("recommended_browse_nodes", ""))
            common_row[175] = str(amazon_uk_product_json.get("search_terms", ""))
            common_row[176] = str(amazon_uk_product_json.get("enclosure_material", ""))
            common_row[177] = str(amazon_uk_product_json.get("cover_material_type", ""))
            special_features = amazon_uk_product_json.get("special_features", [])[:5]
            for i in range(len(special_features)):
                common_row[178+i] = str(special_features[i])        
            common_row[183] = str(amazon_uk_product_json.get("sale_price", ""))
            common_row[184] = str(amazon_uk_product_json.get("sale_from", ""))
            common_row[185] = str(amazon_uk_product_json.get("sale_end", ""))
            common_row[186] = str(amazon_uk_product_json.get("wattage", ""))
            common_row[187] = str(amazon_uk_product_json.get("wattage_metric", ""))
            common_row[188] = str(amazon_uk_product_json.get("item_count", ""))
            common_row[189] = str(amazon_uk_product_json.get("item_count_metric", ""))
            common_row[190] = str(amazon_uk_product_json.get("item_condition_note", ""))
            common_row[191] = str(amazon_uk_product_json.get("max_order_quantity", ""))
            common_row[192] = str(amazon_uk_product_json.get("number_of_items", ""))
            common_row[193] = str(amazon_uk_product_json.get("condition_type", ""))
            dimensions = amazon_uk_product_json.get("dimensions", {})
            common_row[194] = dimensions.get("package_length", "")
            common_row[195] = dimensions.get("package_length_metric", "")
            common_row[196] = dimensions.get("package_width", "")
            common_row[197] = dimensions.get("package_width_metric", "")
            common_row[198] = dimensions.get("package_height", "")
            common_row[199] = dimensions.get("package_height_metric", "")
            common_row[200] = dimensions.get("package_weight", "")
            common_row[201] = dimensions.get("package_weight_metric", "")
            #common_row[146] = dimensions["package_quantity"]
            common_row[203] = dimensions.get("shipping_weight", "")
            common_row[204] = dimensions.get("shipping_weight_metric", "")
            common_row[205] = dimensions.get("item_display_weight", "")
            common_row[206] = dimensions.get("item_display_weight_metric", "")
            common_row[207] = dimensions.get("item_display_volume", "")
            common_row[208] = dimensions.get("item_display_volume_metric", "")
            common_row[209] = dimensions.get("item_display_length", "")
            common_row[210] = dimensions.get("item_display_length_metric", "")
            common_row[211] = dimensions.get("item_display_width", "")
            common_row[212] = dimensions.get("item_display_width_metric", "")
            common_row[213] = dimensions.get("item_display_height", "")
            common_row[214] = dimensions.get("item_display_height_metric", "")
            common_row[215] = dimensions.get("item_weight", "")
            common_row[216] = dimensions.get("item_weight_metric", "")
            common_row[217] = dimensions.get("item_length", "")
            common_row[218] = dimensions.get("item_length_metric", "")
            common_row[219] = dimensions.get("item_width", "")
            common_row[220] = dimensions.get("item_width_metric", "")
            common_row[221] = dimensions.get("item_height", "")
            common_row[222] = dimensions.get("item_height_metric", "")
            #common_row[167] = amazon_verified
            amazon_uae_product_json = json.loads(product.channel_product.amazon_uae_product_json)
            common_row[224] = str(product.channel_product.is_amazon_uae_product_created)
            common_row[225] = amazon_uae_product_json.get("product_name", "")
            common_row[226] = amazon_uae_product_json.get("product_description", "")
            attributes = amazon_uae_product_json.get("product_attribute_list", [])[:5]
            for i in range(len(attributes)):
                common_row[227+i] = attributes[i]
            common_row[232] = amazon_uae_product_json.get("category", "")
            common_row[233] = amazon_uae_product_json.get("sub_category", "")
            common_row[234] = amazon_uae_product_json.get("feed_product_type", "")
            common_row[235] = amazon_uae_product_json.get("recommended_browse_nodes", "")
            common_row[236] = amazon_uae_product_json.get("update_delete", "")
            #common_row[181] = amazon_verified
            ebay_product_json = json.loads(product.channel_product.ebay_product_json)
            common_row[238] = str(product.channel_product.is_ebay_product_created)
            common_row[239] = ebay_product_json.get("product_name", "")
            common_row[240] = ebay_product_json.get("product_description", "")
            attributes = ebay_product_json.get("product_attribute_list", [])[:5]
            for i in range(len(attributes)):
                common_row[241+i] = attributes[i]
            common_row[246] = ebay_product_json.get("category", "")
            common_row[247] = ebay_product_json.get("sub_category", "")
            #common_row[192] = ebay_verified
            noon_product_json = json.loads(product.channel_product.noon_product_json)
            common_row[249] = str(product.channel_product.is_noon_product_created)
            common_row[250] = noon_product_json.get("product_name", "")
            common_row[251] = noon_product_json.get("product_description", "")
            #common_row[196] = noon_product_json["product_type"]
            #common_row[197] = noon_product_json["product_subtype"]
            common_row[254] = noon_product_json.get("partner_sku", "")
            common_row[255] = noon_product_json.get("category", "")
            #common_row[200] = noon_product_json["subtitle"]
            common_row[257] = noon_product_json.get("model_number", "")
            common_row[258] = noon_product_json.get("model_name", "")
            attributes = noon_product_json.get("product_attribute_list", [])[:5]
            for i in range(len(attributes)):
                common_row[259+i] = attributes[i]
            common_row[264] = noon_product_json.get("msrp_ae", "")
            common_row[265] = noon_product_json.get("msrp_ae_unit", "")
            #common_row[210] = noon_verified

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error create_mega_bulk_oc_report %s %s", e, str(exc_tb.tb_lineno))
        
        colnum = 0
        for k in common_row:
            worksheet.write(cnt, colnum, k)
            colnum += 1
        cnt += 1

    workbook.close()

    oc_report_obj = OCReport.objects.get(uuid=uuid)
    oc_report_obj.is_processed = True
    oc_report_obj.completion_date = timezone.now()
    oc_report_obj.save()

    notify_user_for_report(oc_report_obj)


def create_flyer_report(filename, uuid, brand_list, organization_obj):

    workbook = xlsxwriter.Workbook('./'+filename)
    worksheet = workbook.add_worksheet()

    row = ["Sr. No.",
           "Flyer Name",
           "Brand",
           "Mode",
           "Date Created",
           "User"]

    cnt = 0
        
    colnum = 0
    for k in row:
        worksheet.write(cnt, colnum, k)
        colnum += 1

    flyer_objs = Flyer.objects.all()

    if len(brand_list)!=0:
        flyer_objs = flyer_objs.filter(brand__name__in=brand_list, brand__organization=organization_obj)

    for flyer_obj in flyer_objs:
        try:
            cnt += 1
            common_row = ["" for i in range(15)]
            common_row[0] = str(cnt)
            common_row[1] = str(flyer_obj.name)
            common_row[2] = str(flyer_obj.brand)
            common_row[3] = str(flyer_obj.mode)
            try:
                common_row[4] = str(flyer_obj.created_date.strftime("%d %b, %Y"))
            except Exception as e:
                common_row[4] = "NA"
            try:
                common_row[5] = str(flyer_obj.user)
            except Exception as e:
                common_row[5] = "NA"

            colnum = 0
            for k in common_row:
                worksheet.write(cnt, colnum, k)
                colnum += 1

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error create_flyer_report %s %s", e, str(exc_tb.tb_lineno))

    workbook.close()

    oc_report_obj = OCReport.objects.get(uuid=uuid)
    oc_report_obj.is_processed = True
    oc_report_obj.completion_date = timezone.now()
    oc_report_obj.save()

    notify_user_for_report(oc_report_obj)


def create_image_report(filename, uuid, brand_list, organization_obj):

    workbook = xlsxwriter.Workbook('./'+filename)
    worksheet = workbook.add_worksheet()

    row = ["Sr. No.",
           "Product ID",
           "Seller SKU",
           "Product Name",
           "Main Images",
           "Sub Images",
           "PFL Images",
           "White Background Images",
           "Lifestyle Images",
           "Certificate Images",
           "Giftbox Images",
           "Diecut Images",
           "A+ Content Images",
           "Ads Images",
           "Unedited Images"]

    cnt = 0
        
    colnum = 0
    for k in row:
        worksheet.write(cnt, colnum, k)
        colnum += 1

    product_objs = Product.objects.none()

    if len(brand_list)!=0:
        product_objs = product_objs.filter(base_product__brand__name__in=brand_list, base_product__brand__organization=organization_obj)

    for product_obj in product_objs:
        try:
            cnt += 1
            common_row = ["" for i in range(15)]
            common_row[0] = str(cnt)
            common_row[1] = str(product_obj.product_id)
            common_row[2] = str(product_obj.base_product.seller_sku)
            common_row[3] = str(product_obj.product_name)
            try:
                common_row[4] = str(MainImages.objects.get(product=product_obj, is_sourced=True).main_images.count())
            except Exception as e:
                common_row[4] = "0"
            
            try:
                common_row[5] = str(SubImages.objects.get(product=product_obj, is_sourced=True).sub_images.count())
            except Exception as e:
                common_row[5] = "0"

            common_row[6] = str(product_obj.pfl_images.count())
            common_row[7] = str(product_obj.white_background_images.count())
            common_row[8] = str(product_obj.lifestyle_images.count())
            common_row[9] = str(product_obj.certificate_images.count())
            common_row[10] = str(product_obj.giftbox_images.count())
            common_row[11] = str(product_obj.diecut_images.count())
            common_row[12] = str(product_obj.aplus_content_images.count())
            common_row[13] = str(product_obj.ads_images.count())
            common_row[14] = str(product_obj.base_product.unedited_images.count())
            colnum = 0
            for k in common_row:
                worksheet.write(cnt, colnum, k)
                colnum += 1

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error create_image_report %s %s", e, str(exc_tb.tb_lineno))

    workbook.close()

    oc_report_obj = OCReport.objects.get(uuid=uuid)
    oc_report_obj.is_processed = True
    oc_report_obj.completion_date = timezone.now()
    oc_report_obj.save()

    notify_user_for_report(oc_report_obj)


def create_wigme_report(filename, uuid, brand_list, custom_permission_obj,location_group_obj):

    workbook = xlsxwriter.Workbook('./'+filename)
    worksheet = workbook.add_worksheet()

    row = ["Sr. No.",
           "Product ID",
           "Seller SKU",
           "Product Name",
           "Super Category",
           "Category",
           "Sub Category",
           "Active",
           "Was Price",
           "Now Price",
           "Stock"]

    cnt = 0
        
    colnum = 0
    for k in row:
        worksheet.write(cnt, colnum, k)
        colnum += 1

    location_group_objs = custom_permission_obj.location_groups.all()
    if location_group_obj!=None:
        location_group_objs = location_group_objs.filter(uuid=location_group_obj.uuid)

    dh_product_objs = DealsHubProduct.objects.filter(product__base_product__brand__name__in=brand_list, location_group__in=location_group_objs)
    cnt = 1
    for dh_product_obj in dh_product_objs:
        try:
            product_obj = dh_product_obj.product
            common_row = ["" for i in range(11)]
            common_row[0] = str(cnt)
            common_row[1] = str(product_obj.product_id)
            common_row[2] = str(product_obj.base_product.seller_sku)
            common_row[3] = str(product_obj.product_name)
            common_row[4] = dh_product_obj.get_super_category()
            common_row[5] = dh_product_obj.get_category()
            common_row[6] = dh_product_obj.get_sub_category()
            common_row[7] = str(dh_product_obj.is_published)
            common_row[8] = str(dh_product_obj.was_price)
            common_row[9] = str(dh_product_obj.now_price)
            common_row[10] = str(dh_product_obj.stock)
            
            colnum = 0
            for k in common_row:
                worksheet.write(cnt, colnum, k)
                colnum += 1
            cnt += 1

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error create_wigme_report %s %s", e, str(exc_tb.tb_lineno))

    workbook.close()

    oc_report_obj = OCReport.objects.get(uuid=uuid)
    oc_report_obj.is_processed = True
    oc_report_obj.completion_date = timezone.now()
    oc_report_obj.save()

    notify_user_for_report(oc_report_obj)


def create_search_keyword_report(filename, uuid, custom_permission_obj,location_group_obj):

    workbook = xlsxwriter.Workbook('./'+filename)
    worksheet = workbook.add_worksheet()

    row = ["Sr. No.",
           "Timestamp",
           "Keyword",
           "LocationGroup"]

    cnt = 0
        
    colnum = 0
    for k in row:
        worksheet.write(cnt, colnum, k)
        colnum += 1
    cnt = 1
    location_group_objs = custom_permission_obj.location_groups.all()
    if location_group_obj!=None:
        location_group_objs = location_group_objs.filter(uuid=location_group_obj.uuid)

    search_keyword_objs = SearchKeyword.objects.filter(location_group__in=location_group_objs).order_by('-pk')[:5000]

    for search_keyword_obj in search_keyword_objs:
        try:

            common_row = ["" for i in range(4)]
            common_row[0] = str(cnt)
            common_row[1] = str(search_keyword_obj.created_date)
            common_row[2] = str(search_keyword_obj.word)
            common_row[3] = str(search_keyword_obj.location_group)
            
            colnum = 0
            for k in common_row:
                worksheet.write(cnt, colnum, k)
                colnum += 1
            cnt += 1

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error create_search_keyword_report %s %s", e, str(exc_tb.tb_lineno))

    workbook.close()

    oc_report_obj = OCReport.objects.get(uuid=uuid)
    oc_report_obj.is_processed = True
    oc_report_obj.completion_date = timezone.now()
    oc_report_obj.save()

    notify_user_for_report(oc_report_obj)


def create_sales_report(filename, uuid, from_date, to_date, brand_list, custom_permission_obj,location_group_obj):

    workbook = xlsxwriter.Workbook('./'+filename)
    worksheet = workbook.add_worksheet()

    row = ["Sr. No.",
           "Seller SKU",
           "Product ID",
           "Product Name",
           "Brand",
           "Location",
           "Units Sold",
           "Revenue"]

    cnt = 0
    colnum = 0
    for k in row:
        worksheet.write(cnt, colnum, k)
        colnum += 1
    cnt = 1
    location_group_objs = custom_permission_obj.location_groups.all()
    if location_group_obj!=None:
        location_group_objs = location_group_objs.filter(uuid=location_group_obj.uuid)
    
    unit_order_objs = UnitOrder.objects.filter(order__location_group__in=location_group_objs)
    if from_date!="":
        from_date = from_date[:10]+"T00:00:00+04:00"
        unit_order_objs = unit_order_objs.filter(order__order_placed_date__gte=from_date)

    if to_date!="":
        to_date = to_date[:10]+"T23:59:59+04:00"
        unit_order_objs = unit_order_objs.filter(order__order_placed_date__lte=to_date)

    dh_product_objs = DealsHubProduct.objects.filter(pk__in=unit_order_objs.values_list('product__pk', flat=True).distinct(), product__base_product__brand__name__in=brand_list, location_group__in=location_group_objs)

    for dh_product_obj in dh_product_objs:
        try:
            unit_order_objs = UnitOrder.objects.filter(product=dh_product_obj)

            if from_date!="":
                from_date = from_date[:10]+"T00:00:00+04:00"
                unit_order_objs = unit_order_objs.filter(order__order_placed_date__gte=from_date)

            if to_date!="":
                to_date = to_date[:10]+"T23:59:59+04:00"
                unit_order_objs = unit_order_objs.filter(order__order_placed_date__lte=to_date)

            total_count = 0
            revenue = 0
            for unit_order_obj in unit_order_objs:
                total_count += unit_order_obj.quantity
                revenue += unit_order_obj.get_subtotal()

            common_row = ["" for i in range(8)]
            common_row[0] = str(cnt)
            common_row[1] = str(dh_product_obj.get_seller_sku())
            common_row[2] = str(dh_product_obj.get_product_id())
            common_row[3] = str(dh_product_obj.get_name())
            common_row[4] = str(dh_product_obj.get_brand())
            common_row[5] = str(dh_product_obj.location_group)
            common_row[6] = str(total_count)
            common_row[7] = str(revenue)
            
            colnum = 0
            for k in common_row:
                worksheet.write(cnt, colnum, k)
                colnum += 1
            cnt += 1
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error create_sales_report %s %s", e, str(exc_tb.tb_lineno))

    workbook.close()

    oc_report_obj = OCReport.objects.get(uuid=uuid)
    oc_report_obj.is_processed = True
    oc_report_obj.completion_date = timezone.now()
    oc_report_obj.save()

    notify_user_for_report(oc_report_obj)


def create_order_report(filename, uuid, from_date, to_date, brand_list, custom_permission_obj,location_group_obj):

    try:
        logger.info("create_order_report started!")
        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        row = ["Sr. No.",
               "Datetime",
               "Order ID",
               "Order Item ID",
               "Channel",
               "Product Name",
               "Product ID",
               "Seller SKU",
               "Currency",
               "Strike Price",
               "Selling Price",
               "Delivery (inc. VAT)",
               "Delivery VAT",
               "Delivery (excl. VAT)",
               "COD (inc. VAT)",
               "COD VAT",
               "COD (excl. VAT)",
               "Subtotal (inc. VAT)",
               "Subtotal VAT",
               "Subtotal (excl. VAT)", 
               "Quantity",
               "Customer Name",
               "Customer Email ID",
               "Customer Phone Number",
               "Billing Address",
               "Shipping Address",
               "Payment Status",
               "Shipping Method",
               "Order Tracking Status",
               "Order Tracking Status Time"]

        cnt = 0
            
        colnum = 0
        for k in row:
            worksheet.write(cnt, colnum, k)
            colnum += 1
        cnt = 1
        location_group_objs = custom_permission_obj.location_groups.all()
        if location_group_obj!=None:
            location_group_objs = location_group_objs.filter(uuid=location_group_obj.uuid)
        unit_order_objs = UnitOrder.objects.filter(order__location_group__in=location_group_objs).order_by('-pk')
        if from_date!="":
            from_date = from_date[:10]+"T00:00:00+04:00"
            unit_order_objs = unit_order_objs.filter(order__order_placed_date__gte=from_date)
        if to_date!="":
            to_date = to_date[:10]+"T23:59:59+04:00"
            unit_order_objs = unit_order_objs.filter(order__order_placed_date__lte=to_date)
        order_objs = Order.objects.filter(unitorder__in=unit_order_objs).distinct().order_by("-order_placed_date")

        unit_order_list = []
        for order_obj in order_objs:
            try:
                address_obj = order_obj.shipping_address

                shipping_address = address_obj.get_shipping_address()
                customer_name = address_obj.first_name

                delivery_fee_with_vat = order_obj.get_delivery_fee()
                delivery_fee_vat = order_obj.get_delivery_fee_vat()
                delivery_fee_without_vat = order_obj.get_delivery_fee_without_vat()

                cod_fee_with_vat = order_obj.get_cod_charge()
                cod_fee_vat = order_obj.get_cod_charge_vat()
                cod_fee_without_vat = order_obj.get_cod_charge_without_vat()

                for unit_order_obj in unit_order_objs.filter(order=order_obj):

                    subtotal_with_vat = unit_order_obj.get_subtotal()
                    subtotal_vat = unit_order_obj.get_total_vat()
                    subtotal_without_vat = unit_order_obj.get_subtotal_without_vat()

                    tracking_status_time = str(timezone.localtime(UnitOrderStatus.objects.filter(unit_order=unit_order_obj).last().date_created).strftime("%d %b, %Y %I:%M %p"))

                    

                    dealshub_product_obj = unit_order_obj.product

                    common_row = ["" for i in range(len(row))]
                    common_row[0] = str(cnt)
                    common_row[1] = str(timezone.localtime(order_obj.order_placed_date).strftime("%d %b, %Y %I:%M %p"))
                    common_row[2] = order_obj.bundleid
                    common_row[3] = unit_order_obj.orderid
                    common_row[4] = dealshub_product_obj.location_group.name
                    common_row[5] = dealshub_product_obj.get_name()
                    common_row[6] = dealshub_product_obj.get_product_id()
                    common_row[7] = dealshub_product_obj.get_seller_sku()
                    common_row[8] = dealshub_product_obj.get_currency()
                    common_row[9] = str(dealshub_product_obj.was_price)
                    common_row[10] = str(unit_order_obj.price)

                    common_row[11] = str(delivery_fee_with_vat)
                    common_row[12] = str(delivery_fee_vat)
                    common_row[13] = str(delivery_fee_without_vat)
                    common_row[14] = str(cod_fee_with_vat)
                    common_row[15] = str(cod_fee_vat)
                    common_row[16] = str(cod_fee_without_vat)
                    common_row[17] = str(subtotal_with_vat)
                    common_row[18] = str(subtotal_vat)
                    common_row[19] = str(subtotal_without_vat)

                    common_row[20] = str(unit_order_obj.quantity)
                    common_row[21] = customer_name
                    common_row[22] = order_obj.owner.email
                    common_row[23] = str(order_obj.owner.contact_number)
                    common_row[24] = shipping_address
                    common_row[25] = shipping_address
                    common_row[26] = order_obj.payment_status
                    common_row[27] = unit_order_obj.shipping_method
                    common_row[28] = unit_order_obj.current_status_admin
                    common_row[29] = tracking_status_time
                    
                    colnum = 0
                    for k in common_row:
                        worksheet.write(cnt, colnum, k)
                        colnum += 1
                    cnt += 1

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("create_order_report: %s at %s", e, str(exc_tb.tb_lineno))

        workbook.close()

        oc_report_obj = OCReport.objects.get(uuid=uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

        notify_user_for_report(oc_report_obj)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("create_order_report: %s at %s", e, str(exc_tb.tb_lineno))


def create_daily_sales_report(filename, uuid, from_date, to_date, brand_list, custom_permission_obj,location_group_obj):

    try:
        logger.info("create_daily_sales_report started!")
        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        row = ["Sr. No.",
               "Datetime",
               "Order ID",
               "Channel",
               "Seller SKU & Quantity",
               "Currency",
               "Order Amount",
               "Total Quantity",
               "Customer Name",
               "Customer Email ID",
               "Customer Phone Number",
               "Shipping Address",
               "Payment Status",
               "Shipping Method",
               "Order Tracking Status",
               "Order Tracking Status Time",
               "Sales Person",
               "Order Type",
               "SAP Status",
               "Medium",
               "Order Note"]
               
        cnt = 0
            
        colnum = 0
        for k in row:
            worksheet.write(cnt, colnum, k)
            colnum += 1
        cnt = 1
        location_group_objs = custom_permission_obj.location_groups.all()
        if location_group_obj!=None:
            location_group_objs = location_group_objs.filter(uuid=location_group_obj.uuid)
        unit_order_objs = UnitOrder.objects.filter(order__location_group__in=location_group_objs).order_by('-pk')
        if from_date!="":
            from_date = from_date[:10]+"T00:00:00+04:00"
            unit_order_objs = unit_order_objs.filter(order__order_placed_date__gte=from_date)
        if to_date!="":
            to_date = to_date[:10]+"T23:59:59+04:00"
            unit_order_objs = unit_order_objs.filter(order__order_placed_date__lte=to_date)
        order_objs = Order.objects.filter(unitorder__in=unit_order_objs).distinct().order_by("-order_placed_date")

        for order_obj in order_objs:
            common_row = ["" for i in range(len(row))]
            try:
                unit_order_obj = UnitOrder.objects.filter(order=order_obj).filter(product__product__base_product__brand__name__in=brand_list)[0]           
                tracking_status_time = str(timezone.localtime(UnitOrderStatus.objects.filter(unit_order=unit_order_obj).last().date_created).strftime("%d %b, %Y %I:%M %p"))

                common_row[0] = str(cnt)
                common_row[1] = str(timezone.localtime(order_obj.order_placed_date).strftime("%d %b, %Y %I:%M %p"))
                common_row[2] = order_obj.bundleid
                common_row[3] = unit_order_obj.product.location_group.name
                common_row[4] = get_sellersku_and_quantity(order_obj)
                common_row[5] = unit_order_obj.product.get_currency()
                common_row[6] = order_obj.get_total_amount()
                common_row[7] = order_obj.get_total_quantity()
                common_row[8] = order_obj.get_customer_full_name()
                common_row[9] = order_obj.owner.email
                common_row[10] = str(order_obj.owner.contact_number)
                common_row[11] = str(order_obj.shipping_address.get_shipping_address())
                common_row[12] = order_obj.payment_mode
                common_row[13] = unit_order_obj.shipping_method
                common_row[14] = unit_order_obj.current_status_admin
                common_row[15] = tracking_status_time
                common_row[16] = "-"
                if order_obj.is_order_offline and order_obj.offline_sales_person!=None:
                    common_row[16] = order_obj.offline_sales_person.username
                common_row[17] = "offline" if order_obj.is_order_offline else "online"
                common_row[18] = order_obj.sap_status
                common_row[19] = order_obj.reference_medium
                common_row[20] = order_obj.additional_note
                cnt += 1
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("create_daily_sales_report: %s at %s", e, str(exc_tb.tb_lineno))
                
            colnum = 0
            for k in common_row:
                worksheet.write(cnt, colnum, k)
                colnum += 1

        workbook.close()

        oc_report_obj = OCReport.objects.get(uuid=uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()
        email_daily_sales_report_to_user(oc_report_obj)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("create_daily_sales_report: %s at %s", e, str(exc_tb.tb_lineno))


def create_verified_products_report(filename, uuid, from_date, to_date, brand_list, custom_permission_obj):

    workbook = xlsxwriter.Workbook('./'+filename)
    worksheet = workbook.add_worksheet()

    row = ["Sr. No.",
           "Seller SKU",
           "Product ID",
           "Product Name",
           "Brand",
           "Date Verified",
           "User"]

    cnt = 0
    colnum = 0
    for k in row:
        worksheet.write(cnt, colnum, k)
        colnum += 1

    product_objs = Product.objects.filter(verified=True, base_product__brand__name__in=brand_list, base_product__brand__organization=custom_permission_obj.organization)

    for product_obj in product_objs:
        try:
            log_entry_obj = LogEntry.objects.filter(changes__icontains='"verified": ["False", "True"]', object_pk=product_obj.pk).first()
            date_verified = "NA"
            user = "NA"
            if log_entry_obj!=None:
                user = str(log_entry_obj.actor)
                date_verified = str(timezone.localtime(log_entry_obj.timestamp).strftime("%d-%m-%Y %H:%M"))

            if from_date!="":
                from_date = from_date[:10]
                if log_entry_obj.timestamp.replace(tzinfo=None)<from_date:
                    continue

            if to_date!="":
                to_date = to_date[:10]
                if log_entry_obj.timestamp.replace(tzinfo=None)>to_date:
                    continue

            cnt += 1
            common_row = ["" for i in range(7)]
            common_row[0] = str(cnt)
            common_row[1] = str(product_obj.base_product.seller_sku)
            common_row[2] = str(product_obj.product_id)
            common_row[3] = str(product_obj.product_name)
            common_row[4] = str(product_obj.base_product.brand.name)
            common_row[5] = str(date_verified)
            common_row[6] = str(user)

            colnum = 0
            for k in common_row:
                worksheet.write(cnt, colnum, k)
                colnum += 1
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error create_verified_products_report %s %s", e, str(exc_tb.tb_lineno))

    workbook.close()

    oc_report_obj = OCReport.objects.get(uuid=uuid)
    oc_report_obj.is_processed = True
    oc_report_obj.completion_date = timezone.now()
    oc_report_obj.save()

    notify_user_for_report(oc_report_obj)


def create_wishlist_report(filename, uuid, brand_list, custom_permission_obj, location_group_obj):

    try:
        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        row = ["Sr. No.",
               "Customer Name",
               "Contact Number",
               "Location",
               "Wishlist"]

        cnt = 0
        colnum = 0
        for k in row:
            worksheet.write(cnt, colnum, k)
            colnum += 1
        cnt = 1
        location_group_objs = custom_permission_obj.location_groups.all()
        if location_group_obj!=None:
            location_group_objs = location_group_objs.filter(uuid=location_group_obj.uuid)

        dealshub_user_objs = DealsHubUser.objects.filter(pk__in=UnitWishList.objects.filter(product__product__base_product__brand__name__in=brand_list, wish_list__location_group__in=location_group_objs).values_list('wish_list__owner__pk', flat=True).distinct())

        for dealshub_user_obj in dealshub_user_objs:
            try:
                for location_group_obj in location_group_objs:
                    if UnitWishList.objects.filter(wish_list__owner=dealshub_user_obj, wish_list__location_group=location_group_obj).exists()==False:
                        continue

                    customer_name = (dealshub_user_obj.first_name + " " + dealshub_user_obj.last_name).strip()
                    contact_number = dealshub_user_obj.contact_number
                    product_list = []
                    for unit_wish_list_obj in UnitWishList.objects.filter(wish_list__owner=dealshub_user_obj, wish_list__location_group=location_group_obj):
                        product_list.append(unit_wish_list_obj.product.get_seller_sku()+" - "+unit_wish_list_obj.product.get_product_id())

                    common_row = ["" for i in range(5)]
                    common_row[0] = str(cnt)
                    common_row[1] = str(customer_name)
                    common_row[2] = str(contact_number)
                    common_row[3] = str(location_group_obj.name)
                    common_row[4] = str(",".join(product_list))
                
                colnum = 0
                for k in common_row:
                    worksheet.write(cnt, colnum, k)
                    colnum += 1
                cnt += 1
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("Error create_wishlist_report %s %s", e, str(exc_tb.tb_lineno))

        workbook.close()

        oc_report_obj = OCReport.objects.get(uuid=uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

        notify_user_for_report(oc_report_obj)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error create_wishlist_report %s %s", e, str(exc_tb.tb_lineno))


def create_abandoned_cart_report(filename, uuid, brand_list, custom_permission_obj, location_group_obj):

    try:
        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        row = ["Sr. No.",
               "Customer Name",
               "Contact Number",
               "Location",
               "Cart"]

        cnt = 0
        colnum = 0
        for k in row:
            worksheet.write(cnt, colnum, k)
            colnum += 1
        cnt = 1
        location_group_objs = custom_permission_obj.location_groups.all()
        if location_group_obj!=None:
            location_group_objs = location_group_objs.filter(uuid=location_group_obj.uuid)

        dealshub_user_objs = DealsHubUser.objects.filter(pk__in=UnitCart.objects.filter(product__product__base_product__brand__name__in=brand_list, cart__location_group__in=location_group_objs).values_list('cart__owner__pk', flat=True).distinct())

        for dealshub_user_obj in dealshub_user_objs:
            try:
                for location_group_obj in location_group_objs:
                    if FastCart.objects.filter(owner=dealshub_user_obj, location_group=location_group_obj).exclude(product=None).exists()==False and UnitCart.objects.filter(cart__owner=dealshub_user_obj, cart__location_group=location_group_obj).exists()==False:
                        continue
                    
                    customer_name = (dealshub_user_obj.first_name).strip()
                    contact_number = dealshub_user_obj.contact_number
                    product_list = []
                    for unit_cart_obj in UnitCart.objects.filter(cart__owner=dealshub_user_obj, cart__location_group=location_group_obj):
                        product_list.append(unit_cart_obj.product.get_seller_sku()+" - "+unit_cart_obj.product.get_product_id())

                    if FastCart.objects.filter(owner=dealshub_user_obj, location_group=location_group_obj).exclude(product=None).exists():
                        fast_cart_obj = FastCart.objects.get(owner=dealshub_user_obj, location_group=location_group_obj)
                        product_list.append(fast_cart_obj.product.get_seller_sku()+" - "+fast_cart_obj.product.get_product_id())

                    common_row = ["" for i in range(5)]
                    common_row[0] = str(cnt)
                    common_row[1] = str(customer_name)
                    common_row[2] = str(contact_number)
                    common_row[3] = str(location_group_obj.name)
                    common_row[4] = str(",".join(product_list))
                
                colnum = 0
                for k in common_row:
                    worksheet.write(cnt, colnum, k)
                    colnum += 1
                cnt += 1
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("Error create_abandoned_cart_report %s %s", e, str(exc_tb.tb_lineno))

        workbook.close()

        oc_report_obj = OCReport.objects.get(uuid=uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

        notify_user_for_report(oc_report_obj)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error create_abandoned_cart_report %s %s", e, str(exc_tb.tb_lineno))


def create_sap_billing_report(filename, uuid, from_date, to_date, custom_permission_obj, location_group_obj):
    try:
        logger.info('Sap billing report start..')
        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        row = ["Sr. No.",
               "Datetime",
               "Order ID",
               "Order Item ID",
               "Product Name",
               "Product ID",
               "Seller SKU",
               "Customer Name",
               "Customer Email ID",
               "Customer Phone Number",
               "sap Status",
               "grn filename",
               "intercompany order SO",
               "intercompany order DO",
               "final bill SO",
               "final bill DO",
               "final bill DO",
               "final bill INV"]

        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1})

        cnt = 0

        colnum = 0
        for k in row:
            worksheet.write(cnt,colnum,k,header_format)
            colnum += 1
        cnt = 1
        location_group_objs = custom_permission_obj.location_groups.all()
        if location_group_obj!=None:
            location_group_objs = location_group_objs.filter(uuid=location_group_obj.uuid)
        unit_order_objs = UnitOrder.objects.filter(order__location_group__in=location_group_objs).order_by('-pk')
        if from_date!="":
            from_date = from_date[:10]+"T00:00:00+04:00"
            unit_order_objs = unit_order_objs.filter(order__order_placed_date__gte=from_date)
        if to_date!="":
            to_date = to_date[:10]+"T23:59:59+04:00"
            unit_order_objs = unit_order_objs.filter(order__order_placed_date__lte=to_date)
        order_objs = Order.objects.filter(unitorder__in=unit_order_objs).distinct().order_by("-order_placed_date")

        for order_obj in order_objs:
            try:
                address_obj = order_obj.shipping_address
                customer_name = address_obj.first_name
                
                for unit_order_obj in unit_order_objs.filter(order=order_obj):

                    dealshub_product_obj = unit_order_obj.product
                    common_row = ["" for i in range(len(row))]
                    common_row[0] = str(cnt)
                    common_row[1] = str(timezone.localtime(order_obj.order_placed_date).strftime("%d %b, %Y %I:%M %p"))
                    common_row[2] = order_obj.bundleid
                    common_row[3] = unit_order_obj.orderid
                    common_row[4] = dealshub_product_obj.get_name()
                    common_row[5] = dealshub_product_obj.get_product_id()
                    common_row[6] = dealshub_product_obj.get_seller_sku()
                    common_row[7] = customer_name
                    common_row[8] = order_obj.owner.email
                    common_row[9] = str(order_obj.owner.contact_number)
                    common_row[10] = unit_order_obj.sap_status
                    common_row[11] = unit_order_obj.grn_filename
                    intercompany_doc_list = unit_order_obj.sap_intercompany_info["doc_list"]
                    common_row[12] = str(intercompany_doc_list[1].id) + " " + intercompany_doc_list[1].message
                    common_row[13] = str(intercompany_doc_list[2].id) + " " + intercompany_doc_list[2].message
                    final_billing_doc_list = order_obj.sap_final_billing_info["doc_list"]
                    common_row[14] = str(final_billing_doc_list[1].id) + " " + final_billing_doc_list[1].message
                    common_row[15] = str(final_billing_doc_list[2].id) + " " + final_billing_doc_list[2].message
                    common_row[16] = str(final_billing_doc_list[3].id) + " " + final_billing_doc_list[3].message
                    common_row[17] = str(final_billing_doc_list[4].id) + " " + final_billing_doc_list[4].message

                    colnum = 0
                    for k in common_row:
                        worksheet.write(cnt, colnum, k)
                        colnum += 1
                    cnt += 1

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("Error create_sap_billing_report %s %s", e, str(exc_tb.tb_lineno))
        
        workbook.close()
        
        oc_report_obj = OCReport.objects.get(uuid=uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

        notify_user_for_report(oc_report_obj)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error create_sap_billing_report %s %s", e, str(exc_tb.tb_lineno))


def create_sendex_courier_report(filename, uuid, from_date, to_date, custom_permission_obj, location_group_obj):
    try:
        logger.info('Sendex Courier report start...')
        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        row = ["Sr. No.",
               "OrderNo",
               "Customer Name",
               "Mobile",
               "DeliveryLocation",
               "DeliveryAddress",
               "DescriptionOfGoods",
               "Pieces",
               "Weight",
               "DeliveryType",
               "Amount"]

        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1})

        cnt = 0

        colomn = 0
        for k in row:
            worksheet.write(cnt,colomn,k,header_format)
            colomn += 1
        cnt = 1
        location_group_objs = custom_permission_obj.location_groups.all()
        if location_group_obj!=None:
            location_group_objs = location_group_objs.filter(uuid=location_group_obj.uuid)
        unit_order_objs = UnitOrder.objects.filter(shipping_method="sendex", order__location_group__in=location_group_objs).order_by('-pk')
        if from_date!="":
            from_date = from_date[:10]+"T00:00:00+04:00"
            unit_order_objs = unit_order_objs.filter(order__order_placed_date__gte=from_date)
        if to_date!="":
            to_date = to_date[:10]+"T23:59:59+04:00"
            unit_order_objs = unit_order_objs.filter(order__order_placed_date__lte=to_date)
        order_objs = Order.objects.filter(unitorder__in=unit_order_objs).distinct().order_by("-order_placed_date")

        for order_obj in order_objs:
            try:
                address_obj = order_obj.shipping_address              

                description_product_list = []
                order_total_items = 0
                order_total_weight = 0
                for unit_order_obj in unit_order_objs.filter(order=order_obj):
                    dealshub_product_obj = unit_order_obj.product
                    dealshub_product_qty = "(" + str(unit_order_obj.quantity) + ")"
                    description_product_list.append(dealshub_product_obj.get_seller_sku() + dealshub_product_qty)
                    order_total_items += unit_order_obj.quantity
                    order_total_weight += unit_order_obj.quantity * dealshub_product_obj.get_weight()
                
                customer_name = address_obj.first_name + " " + address_obj.last_name
                description_products = ", ".join(description_product_list)

                address_lines = json.loads(address_obj.address_lines)
                address_lines_list = [customer_name, address_lines[0], address_lines[1], address_lines[2], address_lines[3]]
                address_lines_list = list(filter(None, address_lines_list))
                address_lines_combined = "\n".join(address_lines_list)

                common_row = ["" for i in range(len(row))]
                common_row[0] = str(cnt)
                common_row[1] = order_obj.bundleid
                common_row[2] = customer_name
                common_row[3] = str(address_obj.contact_number)
                common_row[4] = address_obj.emirates
                common_row[5] = address_lines_combined
                common_row[6] = description_products
                common_row[7] = str(order_total_items)
                common_row[8] = str(order_total_weight)
                common_row[9] = order_obj.payment_mode
                common_row[10] = str(order_obj.to_pay) if order_obj.payment_mode=="COD" else "0" 

                colnum = 0
                for k in common_row:
                    worksheet.write(cnt, colnum, k)
                    colnum += 1
                cnt += 1
                
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("Error create_sendex_courier_report %s %s", e, str(exc_tb.tb_lineno))

        workbook.close()
        
        oc_report_obj = OCReport.objects.get(uuid=uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

        notify_user_for_report(oc_report_obj)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error create_sendex_courier_report %s %s", e, str(exc_tb.tb_lineno))


def create_standard_courier_report(filename, uuid, from_date, to_date, custom_permission_obj, location_group_obj):
    try:
        logger.info('Standard Courier report start...')
        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        row = ["Sr. No.",
               "Reference No",
               "Delivery Type",
               "Sender Name",
               "Sender Destination",
               "Consignee Name",
               "Consignee Address",
               "Destination Code",
               "Consignee Address Type",
               "Consignee Mobile No",
               "Courier Fees Responsible",
               "COD Amount",
               "Package Type",
               "Item category",
               "Item Description",
               "Item Quantity",
               "Item Weight in KG"]

        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1})

        cnt = 0

        colomn = 0
        for k in row:
            worksheet.write(cnt,colomn,k,header_format)
            colomn += 1
        
        location_group_objs = custom_permission_obj.location_groups.all()
        if location_group_obj!=None:
            location_group_objs = location_group_objs.filter(uuid=location_group_obj.uuid)
        unit_order_objs = UnitOrder.objects.filter(shipping_method="standard", order__location_group__in=location_group_objs).order_by('-pk')
        if from_date!="":
            from_date = from_date[:10]+"T00:00:00+04:00"
            unit_order_objs = unit_order_objs.filter(order__order_placed_date__gte=from_date)
        if to_date!="":
            to_date = to_date[:10]+"T23:59:59+04:00"
            unit_order_objs = unit_order_objs.filter(order__order_placed_date__lte=to_date)
        order_objs = Order.objects.filter(unitorder__in=unit_order_objs).distinct().order_by("-order_placed_date")

        for order_obj in order_objs:
            try:
                address_obj = order_obj.shipping_address              

                description_product_list = []
                order_total_items = 0
                order_total_weight = 0
                for unit_order_obj in unit_order_objs.filter(order=order_obj):
                    dealshub_product_obj = unit_order_obj.product
                    product_quantity = unit_order_obj.quantity
                    dealshub_product_qty = "(" + str(unit_order_obj.quantity) + ")"
                    dealshub_product_seller_sku = dealshub_product_obj.get_seller_sku() + dealshub_product_qty
                    description_product_list.append(dealshub_product_seller_sku)
                    order_total_items += product_quantity
                    order_total_weight += product_quantity * dealshub_product_obj.get_weight()
                
                customer_name = address_obj.first_name + " " + address_obj.last_name
                description_products = ", ".join(description_product_list)

                address_lines = json.loads(address_obj.address_lines)
                address_lines_list = [customer_name, address_lines[0], address_lines[1], address_lines[2], address_lines[3]]
                address_lines_list = list(filter(None, address_lines_list))
                address_lines_combined = "\n".join(address_lines_list)
                check_alain_location = ("alain" in address_lines_combined) or ("Alain" in address_lines_combined)

                cnt += 1

                common_row = ["" for i in range(len(row))]
                common_row[0] = str(cnt)
                common_row[1] = order_obj.bundleid
                common_row[2] = "Standard Delivery"
                common_row[3] = "WIGME"
                common_row[4] = "DXB"
                common_row[5] = customer_name
                common_row[6] = address_lines_combined
                common_row[7] = "ALN" if check_alain_location else "AUH"
                common_row[8] = "Home"
                common_row[9] = str(address_obj.contact_number)
                common_row[10] = "PPD"
                common_row[11] = str(order_obj.to_pay) if order_obj.payment_mode=="COD" else "0" 
                common_row[12] = "Box"
                common_row[13] = "Electronics"
                common_row[14] = description_products
                common_row[15] = str(order_total_items)
                common_row[16] = str(order_total_weight)

                colnum = 0
                for k in common_row:
                    worksheet.write(cnt, colnum, k)
                    colnum += 1
                
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("Error create_standard_courier_report %s %s", e, str(exc_tb.tb_lineno))

        workbook.close()
        
        oc_report_obj = OCReport.objects.get(uuid=uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

        notify_user_for_report(oc_report_obj)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error create_standard_courier_report %s %s", e, str(exc_tb.tb_lineno))


def create_postaplus_courier_report(filename, uuid, from_date, to_date, custom_permission_obj, location_group_obj):
    try:
        logger.info('Postaplus Courier report start...')
        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        row = ["No.",
               "Shipment Type",
               "CustomerAc#",
               "CneeName100",
               "CompanyName100",
               "Address250",
               "AddressIdendityNumber",
               "Cnee Country Code",
               "Cnee Province Code",
               "Cnee City Name",
               "Cnee City Code",
               "CneeArea",
               "Cnee AreaCode",
               "AutodialerMobile1",
               "Email1",
               "ServiceID",
               "DescriptionOfGoods100",
               "Pcs",
               "Wt",
               "CODAmount",
               "CODCurrency",
               "CostOfGoodsAmount",
               "Currency",
               "OriginOfCountry",
               "Ref2100",
               "Note4250",
               "Ref1100"]

        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1})

        cnt = 0

        colomn = 0
        for k in row:
            worksheet.write(cnt,colomn,k,header_format)
            colomn += 1
        
        location_group_objs = custom_permission_obj.location_groups.all()
        if location_group_obj!=None:
            location_group_objs = location_group_objs.filter(uuid=location_group_obj.uuid)
        unit_order_objs = UnitOrder.objects.filter(order__location_group__in=location_group_objs).order_by('-pk')
        if from_date!="":
            from_date = from_date[:10]+"T00:00:00+04:00"
            unit_order_objs = unit_order_objs.filter(order__order_placed_date__gte=from_date)
        if to_date!="":
            to_date = to_date[:10]+"T23:59:59+04:00"
            unit_order_objs = unit_order_objs.filter(order__order_placed_date__lte=to_date)
        order_objs = Order.objects.filter(unitorder__in=unit_order_objs).distinct().order_by("-order_placed_date")

        for order_obj in order_objs:
            try:
                address_obj = order_obj.shipping_address              

                description_product_list = []
                order_total_items = 0
                order_total_weight = 0
                for unit_order_obj in unit_order_objs.filter(order=order_obj):
                    dealshub_product_obj = unit_order_obj.product

                    description_product_list.append(dealshub_product_obj.get_seller_sku())
                    order_total_items += unit_order_obj.quantity
                    order_total_weight += unit_order_obj.quantity * dealshub_product_obj.get_weight()
                
                customer_name = address_obj.first_name + " " + address_obj.last_name
                description_products = ", ".join(description_product_list)

                address_lines = json.loads(address_obj.address_lines)
                address_lines_list = [customer_name, address_lines[0], address_lines[1], address_lines[2], address_lines[3]]
                address_lines_list = list(filter(None, address_lines_list))
                address_lines_combined = "\n".join(address_lines_list)

                cnt += 1

                common_row = ["" for i in range(len(row))]
                common_row[0] = str(cnt)
                common_row[1] = ""
                common_row[2] = ""
                common_row[3] = customer_name
                common_row[4] = ""
                common_row[5] = address_lines_combined
                common_row[6] = ""
                common_row[7] = ""
                common_row[8] = ""
                common_row[9] = address_obj.emirates
                common_row[10] = ""
                common_row[11] = ""
                common_row[12] = ""
                common_row[13] = str(address_obj.contact_number)
                common_row[14] = ""
                common_row[15] = ""
                common_row[16] = description_products
                common_row[17] = str(order_total_items)
                common_row[18] = str(order_total_weight)
                common_row[19] = str(order_obj.to_pay)
                common_row[20] = order_obj.get_currency()
                common_row[21] = ""
                common_row[22] = ""
                common_row[23] = ""
                common_row[24] = order_obj.bundleid
                common_row[25] = ""
                common_row[26] = ""

                colnum = 0
                for k in common_row:
                    worksheet.write(cnt, colnum, k)
                    colnum += 1
                
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("Error create_postaplus_courier_report %s %s", e, str(exc_tb.tb_lineno))

        workbook.close()
        
        oc_report_obj = OCReport.objects.get(uuid=uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

        notify_user_for_report(oc_report_obj)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error create_postaplus_courier_report %s %s", e, str(exc_tb.tb_lineno))


def create_sales_executive_value_report(filename, uuid, from_date, to_date, custom_permission_obj, location_group_obj):
    
    try:
        logger.info('Sales Executive Value report start...')
        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        row = ["No.",
               "sales person",
               "location group",
               "currency",
               "No of orders",
               "Total value of orders"]

        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1})

        cnt = 0

        colomn = 0
        for k in row:
            worksheet.write(cnt,colomn,k,header_format)
            colomn += 1
        
        location_group_objs = custom_permission_obj.location_groups.all()
        if location_group_obj!=None:
            location_group_objs = location_group_objs.filter(uuid=location_group_obj.uuid)

        for location_group_obj in location_group_objs:
            custom_permission_objs = location_group_obj.custompermission_set.all()
            for custom_permission_obj in custom_permission_objs:
                try:
                    oc_user_obj = custom_permission_obj.user
                    order_objs = Order.objects.filter(location_group=location_group_obj, offline_sales_person=oc_user_obj, is_order_offline=True)
                    if from_date!="" and from_date!=None:
                        from_date = from_date[:10]+"T00:00:00+04:00"
                        order_objs = order_objs.filter(order_placed_date__gte=from_date)
                    if to_date!="" and to_date!=None:
                        to_date = to_date[:10]+"T23:59:59+04:00"
                        order_objs = order_objs.filter(order_placed_date__lte=to_date)
                    
                    orders_count = order_objs.count()
                    orders_total_value = order_objs.aggregate(Sum('to_pay')).to_pay_sum

                    cnt += 1

                    common_row = ["" for i in range(len(row))]
                    common_row[0] = str(cnt)
                    common_row[1] = oc_user_obj.username
                    common_row[2] = location_group_obj.name
                    common_row[3] = str(location_group_obj.loaction.currency)
                    common_row[4] = str(orders_count)
                    common_row[5] = str(orders_total_value)
                    
                    colnum = 0
                    for k in common_row:
                        worksheet.write(cnt, colnum, k)
                        colnum += 1
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("Error create_sales_executive_value_report %s %s", e, str(exc_tb.tb_lineno))

        workbook.close()

        oc_report_obj = OCReport.objects.get(uuid=uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

        notify_user_for_report(oc_report_obj)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error create_sales_executive_value_report %s %s", e, str(exc_tb.tb_lineno))
        

def bulk_download_product_seo_details_report(filename, uuid, location_group_obj):
    try:
        logger.info('Product seo details download report start...')
        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        row = ["No.",
               "Product uuid",
               "Product Name",
               "seller sku",
               "page description",
               "seo title",
               "seo keywords",
               "seo description",
               "search keywords"]
        
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1})
        
        worksheet.write(0,0,"Type",header_format)
        worksheet.write(0,1,"product")

        cnt=1

        colomn = 0
        for k in row:
            worksheet.write(cnt,colomn,k,header_format)
            colomn += 1
        
        dh_product_objs = DealsHubProduct.objects.filter(location_group=location_group_obj, is_published=True, product__base_product__brand__in=location_group_obj.website_group.brands.all())

        for dh_product_obj in dh_product_objs:
            try:
                cnt += 1

                common_row = ["" for i in range(len(row))]
                common_row[0] = str(cnt-1)
                common_row[1] = str(dh_product_obj.uuid)
                common_row[2] = dh_product_obj.get_name()
                common_row[3] = dh_product_obj.get_seller_sku()
                common_row[4] = dh_product_obj.page_description
                common_row[5] = dh_product_obj.seo_title
                common_row[6] = dh_product_obj.seo_keywords
                common_row[7] = dh_product_obj.seo_description
                common_row[8] = dh_product_obj.search_keywords

                colnum = 0
                for k in common_row:
                    worksheet.write(cnt, colnum, k)
                    colnum += 1    

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("Error bulk_download_product_seo_details_report %s %s", e, str(exc_tb.tb_lineno))        

        workbook.close()

        oc_report_obj = OCReport.objects.get(uuid=uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

        notify_user_for_report(oc_report_obj)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error bulk_download_product_seo_details_report %s %s", e, str(exc_tb.tb_lineno))


def bulk_download_categories_seo_details_report(filename, uuid, location_group_obj, category_type):
    try:
        logger.info('seo categories download report start...')
        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        row = ["No.",
               str(category_type + "Category uuid"),
               str(category_type + "Category Name"),
               "page description",
               "seo title",
               "seo keywords",
               "seo description",
               "short description",
               "long description"]
        
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1})
        
        worksheet.write(0,0,"Type",header_format)
        worksheet.write(0,1,category_type+"category")

        cnt=1
        
        colomn = 0
        for k in row:
            worksheet.write(cnt,colomn,k,header_format)
            colomn += 1
        
        generic_category_objs = None
        if category_type=="sub":
            generic_category_objs = SEOSubCategory.objects.filter(location_group=location_group_obj)
        elif category_type=="":
            generic_category_objs = SEOCategory.objects.filter(location_group=location_group_obj)
        elif category_type=="super":
            generic_category_objs = SEOSuperCategory.objects.filter(location_group=location_group_obj)
        cnt += 1
        if generic_category_objs is not None:
            for generic_category_obj in generic_category_objs:
                try:
                   
                    generic_category_name = ""
                    if category_type=="sub":
                        generic_category_name = generic_category_obj.sub_category.get_name()
                    elif category_type=="":
                        generic_category_name = generic_category_obj.category.get_name()
                    elif category_type=="super":
                        generic_category_name = generic_category_obj.super_category.get_name()

                    common_row = ["" for i in range(len(row))]
                    common_row[0] = str(cnt-1)
                    common_row[1] = str(generic_category_obj.uuid)
                    common_row[2] = generic_category_name
                    common_row[3] = generic_category_obj.page_description
                    common_row[4] = generic_category_obj.seo_title
                    common_row[5] = generic_category_obj.seo_keywords
                    common_row[6] = generic_category_obj.seo_description
                    common_row[7] = generic_category_obj.short_description
                    common_row[8] = generic_category_obj.long_description

                    colnum = 0
                    for k in common_row:
                        worksheet.write(cnt, colnum, k)
                        colnum += 1
                    cnt += 1
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("Error bulk_download_categories_seo_details_report %s %s", e, str(exc_tb.tb_lineno))
        
        workbook.close()

        oc_report_obj = OCReport.objects.get(uuid=uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

        notify_user_for_report(oc_report_obj)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error bulk_download_categories_seo_details_report %s %s", e, str(exc_tb.tb_lineno))


def bulk_download_brand_categories_seo_details_report(filename, uuid, location_group_obj, category_type):
    try:
        logger.info('Categories+brand seo details download report start...')
        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        row = ["No.",
               "Brand "+category_type+"Category uuid",
               "Brand Name",
               category_type+"Category Name",
               "page description",
               "seo title",
               "seo keywords",
               "seo description",
               "short description",
               "long description"]
        
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1})
        
        worksheet.write(0,0,"Type",header_format)
        worksheet.write(0,1,"brand"+category_type+"category")
  
        cnt=1
        
        colomn = 0
        for k in row:
            worksheet.write(cnt,colomn,k,header_format)
            colomn += 1
        cnt += 1
        generic_category_brand_objs = None
        if category_type=="sub":
            generic_category_brand_objs = BrandSubCategory.objects.filter(location_group=location_group_obj, brand__organization__name="WIG")
        elif category_type=="":
            generic_category_brand_objs = BrandCategory.objects.filter(location_group=location_group_obj, brand__organization__name="WIG")
        elif category_type=="super":
            generic_category_brand_objs = BrandSuperCategory.objects.filter(location_group=location_group_obj, brand__organization__name="WIG")
        
        if generic_category_brand_objs is not None:
            for generic_category_brand_obj in generic_category_brand_objs:
                try:

                    generic_category_name =""
                    if category_type=="sub":
                        generic_category_name = generic_category_brand_obj.sub_category.get_name()
                    elif category_type=="":
                        generic_category_name = generic_category_brand_obj.category.get_name()
                    elif category_type=="super":
                        generic_category_name = generic_category_brand_obj.super_category.get_name()

                    common_row = ["" for i in range(len(row))]
                    common_row[0] = str(cnt-1)
                    common_row[1] = str(generic_category_brand_obj.uuid)
                    common_row[2] = generic_category_brand_obj.brand.get_name()
                    common_row[3] = generic_category_name
                    common_row[4] = generic_category_brand_obj.page_description
                    common_row[5] = generic_category_brand_obj.seo_title
                    common_row[6] = generic_category_brand_obj.seo_keywords
                    common_row[7] = generic_category_brand_obj.seo_description
                    common_row[8] = generic_category_brand_obj.short_description
                    common_row[9] = generic_category_brand_obj.long_description
                    
                    colnum = 0
                    for k in common_row:
                        worksheet.write(cnt, colnum, k)
                        colnum += 1
                    cnt += 1
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("Error bulk_download_brand_categories_seo_details_report %s %s", e, str(exc_tb.tb_lineno))
        workbook.close()

        oc_report_obj = OCReport.objects.get(uuid=uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

        notify_user_for_report(oc_report_obj)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error bulk_download_brand_categories_seo_details_report %s %s", e, str(exc_tb.tb_lineno))


def bulk_download_brand_seo_details_report(filename, uuid, location_group_obj):
    try:
        logger.info('Brand seo details download report start...')
        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        row = ["No.",
               "SEO Brand uuid",
               "Brand Name",
               "page description",
               "seo title",
               "seo keywords",
               "seo description",
               "short description",
               "long description"]
        
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1})
        
        worksheet.write(0,0,"Type",header_format)
        worksheet.write(0,1,"brand")

        cnt=1
        
        colomn = 0
        for k in row:
            worksheet.write(cnt,colomn,k,header_format)
            colomn += 1
        cnt += 1
        seo_brand_objs = SEOBrand.objects.filter(location_group=location_group_obj, brand__organization__name="WIG")

        for seo_brand_obj in seo_brand_objs:
            try:

                common_row = ["" for i in range(len(row))]
                common_row[0] = str(cnt-1)
                common_row[1] = str(seo_brand_obj.uuid)
                common_row[2] = seo_brand_obj.brand.get_name()
                common_row[3] = seo_brand_obj.page_description
                common_row[4] = seo_brand_obj.seo_title
                common_row[5] = seo_brand_obj.seo_keywords
                common_row[6] = seo_brand_obj.seo_description
                common_row[7] = seo_brand_obj.short_description
                common_row[8] = seo_brand_obj.long_description

                colnum = 0
                for k in common_row:
                    worksheet.write(cnt, colnum, k)
                    colnum += 1
                cnt += 1
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("Error bulk_download_brand_seo_details_report %s %s", e, str(exc_tb.tb_lineno))
        
        workbook.close()

        oc_report_obj = OCReport.objects.get(uuid=uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

        notify_user_for_report(oc_report_obj)
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error bulk_download_brand_seo_details_report %s %s", e, str(exc_tb.tb_lineno))


def bulk_upload_product_seo_details_report(dfs, seo_type, location_group_obj):

    try:
        logger.info('Product seo details upload report start...')
        rows = len(dfs.iloc[:])

        for i in range(2,rows):
            try:
                product_uuid = str(dfs.iloc[i][1]).strip()
                product_name = str(dfs.iloc[i][2]).strip()
                product_seller_sku = str(dfs.iloc[i][3]).strip()
                page_description = str(dfs.iloc[i][4]).strip()
                seo_title = str(dfs.iloc[i][5]).strip()
                seo_keywords = str(dfs.iloc[i][6]).strip()
                seo_description = str(dfs.iloc[i][7]).strip()
                search_keywords = str(dfs.iloc[i][8]).strip()

                dh_product_obj = DealsHubProduct.objects.get(uuid=product_uuid)

                dh_product_obj.page_description = page_description
                dh_product_obj.seo_title = seo_title
                dh_product_obj.seo_keywords = seo_keywords
                dh_product_obj.seo_description = seo_description
                dh_product_obj.search_keywords = search_keywords
                dh_product_obj.save()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("Error bulk_upload_product_seo_details_report %s %s", e, str(exc_tb.tb_lineno))

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error bulk_upload_product_seo_details_report %s %s", e, str(exc_tb.tb_lineno))

        
def bulk_upload_categories_seo_details_report(dfs, seo_type, location_group_obj):
    
    try:
        logger.info('Categories seo details upload report start...')
        rows = len(dfs.iloc[:])

        for i in range(2,rows):
            try:
                generic_category_uuid = str(dfs.iloc[i][1]).strip()
                generic_category_name = str(dfs.iloc[i][2]).strip()
                page_description = str(dfs.iloc[i][3]).strip()
                seo_title = str(dfs.iloc[i][4]).strip()
                seo_keywords = str(dfs.iloc[i][5]).strip()
                seo_description = str(dfs.iloc[i][6]).strip()
                short_description = str(dfs.iloc[i][7]).strip()
                long_description = str(dfs.iloc[i][8]).strip()
                
                generic_category_obj = None
                if seo_type=="subcategory":
                    generic_category_obj = SEOSubCategory.objects.get(uuid=generic_category_uuid, location_group=location_group_obj)
                elif seo_type=="category":
                    generic_category_obj = SEOCategory.objects.get(uuid=generic_category_uuid, location_group=location_group_obj)
                elif seo_type=="supercategory":
                    generic_category_obj = SEOSuperCategory.objects.get(uuid=generic_category_uuid, location_group=location_group_obj)

                if generic_category_obj!=None:
                    generic_category_obj.page_description = page_description
                    generic_category_obj.seo_title = seo_title
                    generic_category_obj.seo_keywords = seo_keywords
                    generic_category_obj.seo_description = seo_description
                    generic_category_obj.short_description = short_description
                    generic_category_obj.long_description = long_description
                    generic_category_obj.save()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("Error bulk_upload_categories_seo_details_report %s %s", e, str(exc_tb.tb_lineno))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error bulk_upload_categories_seo_details_report %s %s", e, str(exc_tb.tb_lineno))

        
def bulk_upload_brand_categories_seo_details_report(dfs, seo_type, location_group_obj):

    try:
        logger.info('Brand + Categories seo details upload report start...')
        rows = len(dfs.iloc[:])

        for i in range(2,rows):
            try:
                generic_brand_category_uuid = str(dfs.iloc[i][1]).strip()
                generic_category_name = str(dfs.iloc[i][2]).strip()
                brand_name = str(dfs.iloc[i][3]).strip()
                page_description = str(dfs.iloc[i][4]).strip()
                seo_title = str(dfs.iloc[i][5]).strip()
                seo_keywords = str(dfs.iloc[i][6]).strip()
                seo_description = str(dfs.iloc[i][7]).strip()
                short_description = str(dfs.iloc[i][8]).strip()
                long_description = str(dfs.iloc[i][9]).strip()
                
                generic_brand_category_obj = None
                if seo_type=="subcategory":
                    generic_brand_category_obj = BrandSubCategory.objects.get(uuid=generic_brand_category_uuid, location_group=location_group_obj, brand__organization__name="WIG")
                elif seo_type=="category":
                    generic_brand_category_obj = BrandCategory.objects.get(uuid=generic_brand_category_uuid, location_group=location_group_obj, brand__organization__name="WIG")
                elif seo_type=="supercategory":
                    generic_brand_category_obj = BrandSuperCategory.objects.get(uuid=generic_brand_category_uuid, location_group=location_group_obj, brand__organization__name="WIG")

                if generic_brand_category_obj!=None:
                    generic_brand_category_obj.page_description = page_description
                    generic_brand_category_obj.seo_title = seo_title
                    generic_brand_category_obj.seo_keywords = seo_keywords
                    generic_brand_category_obj.seo_description = seo_description
                    generic_brand_category_obj.short_description = short_description
                    generic_brand_category_obj.long_description = long_description
                    generic_brand_category_obj.save()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("Error bulk_upload_brand_categories_seo_details_report %s %s", e, str(exc_tb.tb_lineno))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error bulk_upload_brand_categories_seo_details_report %s %s", e, str(exc_tb.tb_lineno))


def bulk_upload_brand_seo_details_report(dfs, seo_type, location_group_obj):

    try:
        logger.info('Brand seo details upload report start...')
        rows = len(dfs.iloc[:])

        for i in range(2,rows):
            try:
                brand_uuid = str(dfs.iloc[i][1]).strip()
                brand_name = str(dfs.iloc[i][2]).strip()
                page_description = str(dfs.iloc[i][3]).strip()
                seo_title = str(dfs.iloc[i][4]).strip()
                seo_keywords = str(dfs.iloc[i][5]).strip()
                seo_description = str(dfs.iloc[i][6]).strip()
                short_description = str(dfs.iloc[i][7]).strip()
                long_description = str(dfs.iloc[i][8]).strip()

                brand_obj = SEOBrand.objects.get(uuid=brand_uuid, location_group=location_group_obj, brand__organization__name="WIG")

                brand_obj.page_description = page_description
                brand_obj.seo_title = seo_title
                brand_obj.seo_keywords = seo_keywords
                brand_obj.seo_description = seo_description
                brand_obj.short_description = short_description
                brand_obj.long_description = long_description
                brand_obj.save()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("Error bulk_upload_brand_seo_details_report %s %s", e, str(exc_tb.tb_lineno))
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error bulk_upload_brand_seo_details_report %s %s", e, str(exc_tb.tb_lineno))


def create_bulk_image_report(filename, uuid, brand_list, organization_obj=None):
    
    try:
        logger.info("Bulk image report started...")
        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        product_objs = Product.objects.filter(base_product__brand__name__in=brand_list, base_product__brand__organization=organization_obj)

        row = ["No.",
           "Main Image",
           "Sub Image 1",
           "Sub Image 2",
           "Sub Image 3",
           "Sub Image 4",
           "Sub Image 5",
           "Sub Image 6",
           "Sub Image 7",
           "Sub Image 8",
           "Sub Image 9",
           "Sub Image 10",
           "White Background Image 1",
           "White Background Image 2",
           "White Background Image 3",
           "White Background Image 4",
           "White Background Image 5",
           "White Background Image 6",
           "White Background Image 7",
           "White Background Image 8",
           "White Background Image 9",
           "White Background Image 10",
           "PFL Image 1",
           "PFL Image 2",
           "PFL Image 3",
           "PFL Image 4",
           "PFL Image 5",
           "PFL Image 6",
           "PFL Image 7",
           "PFL Image 8",
           "PFL Image 9",
           "PFL Image 10",
           "Lifestyle Image 1",
           "Lifestyle Image 2",
           "Lifestyle Image 3",
           "Lifestyle Image 4",
           "Lifestyle Image 5",
           "Lifestyle Image 6",
           "Lifestyle Image 7",
           "Lifestyle Image 8",
           "Lifestyle Image 9",
           "Lifestyle Image 10",
           "Certificate Image 1",
           "Certificate Image 2",
           "Certificate Image 3",
           "Certificate Image 4",
           "Certificate Image 5",
           "Certificate Image 6",
           "Certificate Image 7",
           "Certificate Image 8",
           "Certificate Image 9",
           "Certificate Image 10",
           "Giftbox Image 1",
           "Giftbox Image 2",
           "Giftbox Image 3",
           "Giftbox Image 4",
           "Giftbox Image 5",
           "Giftbox Image 6",
           "Giftbox Image 7",
           "Giftbox Image 8",
           "Giftbox Image 9",
           "Giftbox Image 10",
           "Diecut Image 1",
           "Diecut Image 2",
           "Diecut Image 3",
           "Diecut Image 4",
           "Diecut Image 5",
           "Diecut Image 6",
           "Diecut Image 7",
           "Diecut Image 8",
           "Diecut Image 9",
           "Diecut Image 10",
           "A+ Content Image 1",
           "A+ Content Image 2",
           "A+ Content Image 3",
           "A+ Content Image 4",
           "A+ Content Image 5",
           "A+ Content Image 6",
           "A+ Content Image 7",
           "A+ Content Image 8",
           "A+ Content Image 9",
           "A+ Content Image 10",
           "Ads Image 1",
           "Ads Image 2",
           "Ads Image 3",
           "Ads Image 4",
           "Ads Image 5",
           "Ads Image 6",
           "Ads Image 7",
           "Ads Image 8",
           "Ads Image 9",
           "Ads Image 10",
           "Unedited Image 1",
           "Unedited Image 2",
           "Unedited Image 3",
           "Unedited Image 4",
           "Unedited Image 5",
           "Unedited Image 6",
           "Unedited Image 7",
           "Unedited Image 8",
           "Unedited Image 9",
           "Unedited Image 10",
           "Transparent Image 1",
           "Transparent Image 2",
           "Transparent Image 3",
           "Transparent Image 4",
           "Transparent Image 5",
           "Transparent Image 6",
           "Transparent Image 7",
           "Transparent Image 8",
           "Transparent Image 9",
           "Transparent Image 10"]
        
        cnt = 0
        
        colnum = 0
        for k in row:
            worksheet.write(cnt, colnum, k)
            colnum += 1
        cnt += 1
        for product in product_objs:
            try:
                common_row = ["" for i in range(len(row))]
                common_row[0] = str(cnt)
                
                try:
                    main_images = MainImages.objects.get(product=product, is_sourced=True)
                    main_image = main_images.main_images.all()[0]
                    common_row[1] = main_image.image.image.url
                except Exception as e:
                    pass
                try:
                    sub_images = SubImages.objects.get(product=product, is_sourced=True)
                    sub_images = sub_images.sub_images.all()[:10]
                    iterr = 0
                    for sub_image in sub_images:
                        common_row[2+iterr] = sub_image.image.image.url
                        iterr += 1
                except Exception as e:
                    pass
                try:
                    iterr = 0
                    for image in product.white_background_images.all()[:10]:
                        common_row[12+iterr] = image.image.url
                        iterr += 1
                except Exception as e:
                    pass
                try:
                    iterr = 0
                    for image in product.white_background_images.all()[:10]:
                        common_row[22+iterr] = image.image.url
                        iterr += 1
                except Exception as e:
                    pass
                try:            
                    iterr = 0
                    for image in product.pfl_images.all()[:10]:
                        common_row[32+iterr] = image.image.url
                        iterr += 1
                except Exception as e:
                    pass
                try:
                    iterr = 0
                    for image in product.lifestyle_images.all()[:10]:
                        common_row[42+iterr] = image.image.url
                        iterr += 1
                except Exception as e:
                    pass
                try:
                    iterr = 0
                    for image in product.certificate_images.all()[:10]:
                        common_row[52+iterr] = image.image.url
                        iterr += 1
                except Exception as e:
                    pass
                try:
                    iterr = 0
                    for image in product.giftbox_images.all()[:10]:
                        common_row[62+iterr] = image.image.url
                        iterr += 1
                except Exception as e:
                    pass
                try:
                    iterr = 0
                    for image in product.diecut_images.all()[:10]:
                        common_row[72+iterr] = image.image.url
                        iterr += 1
                except Exception as e:
                    pass
                try:
                    iterr = 0
                    for image in product.aplus_content_images.all()[:10]:
                        common_row[82+iterr] = image.image.url
                        iterr += 1
                except Exception as e:
                    pass
                try:
                    iterr = 0
                    for image in product.ads_images.all()[:10]:
                        common_row[92+iterr] = image.image.url
                        iterr += 1
                except Exception as e:
                    pass
                try:
                    iterr = 0
                    for image in product.base_product.unedited_images.all()[:10]:
                        common_row[102+iterr] = image.image.url
                        iterr += 1
                except Exception as e:
                    pass
                try:
                    iterr = 0
                    for image in product.transparent_images.all()[:10]:
                        common_row[112+iterr] = image.image.url
                        iterr += 1
                except Exception as e:
                    pass
                
                colnum = 0
                for k in common_row:
                    worksheet.write(cnt, colnum, k)
                    colnum += 1
                cnt += 1
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("Error create_bulk_image_report %s %s", e, str(exc_tb.tb_lineno))

        workbook.close()

        oc_report_obj = OCReport.objects.get(uuid=uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

        notify_user_for_report(oc_report_obj)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error create_bulk_image_report %s %s", e, str(exc_tb.tb_lineno))


def create_stock_report(filename, uuid, brand_list, location_group_obj):
    try:
        logger.info('Stock Report download report start...')
        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        row = ["No.",
               "Product id",
               "Seller SKU",
               "Product Name",
               "Stocks",
               "Price"]
        
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
        cnt += 1
        dh_product_objs = DealsHubProduct.objects.filter(product__base_product__brand__name__in=brand_list, location_group=location_group_obj)

        for dh_product_obj in dh_product_objs:
            try:

                common_row = ["" for i in range(len(row))]
                common_row[0] = str(cnt)
                common_row[1] = dh_product_obj.get_product_id()
                common_row[2] = dh_product_obj.get_seller_sku()
                common_row[3] = dh_product_obj.get_name()
                common_row[4] = str(dh_product_obj.stock)
                common_row[5] = str(dh_product_obj.now_price)

                colnum = 0
                for k in common_row:
                    worksheet.write(cnt, colnum, k)
                    colnum += 1
                cnt += 1
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("Error create_stock_report %s %s", e, str(exc_tb.tb_lineno))
        
        workbook.close()

        oc_report_obj = OCReport.objects.get(uuid=uuid)
        oc_report_obj.is_processed = True
        oc_report_obj.completion_date = timezone.now()
        oc_report_obj.save()

        notify_user_for_report(oc_report_obj)
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error create_stock_report %s %s", e, str(exc_tb.tb_lineno))


def create_newsletter_subscribers_report(filename, uuid, location_group_obj):

    try:
        workbook = xlsxwriter.Workbook('./'+filename)
        worksheet = workbook.add_worksheet()

        row = ["Sr. No.",
               "Subscribers"]

        cnt = 0
        colnum = 0
        for k in row:
            worksheet.write(cnt, colnum, k)
            colnum += 1

        location_group_obj = LocationGroup.objects.get(uuid=location_group_obj.uuid)
        blog_emails = json.loads(location_group_obj.blog_emails)
        cnt += 1
        for blog_email in blog_emails:
            try:
                common_row = ["" for i in range(len(row))]
                common_row[0] = str(cnt)
                common_row[1] = str(blog_email)
                
                colnum = 0

                for k in common_row:
                    worksheet.write(cnt, colnum, k)
                    colnum += 1
                
                cnt += 1
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("Error create_newsletter_subscribers_report %s %s", e, str(exc_tb.tb_lineno))

        workbook.close()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Error create_newsletter_subscribers_report %s %s", e, str(exc_tb.tb_lineno))

    oc_report_obj = OCReport.objects.get(uuid=uuid)
    oc_report_obj.is_processed = True
    oc_report_obj.completion_date = timezone.now()
    oc_report_obj.save()