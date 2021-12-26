from dealshub.models import *
from dealshub.constants import *
from rest_framework.views import APIView
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view

from django.db.models import Q
from django.core.paginator import Paginator
from django.core.files.storage import default_storage
from django.core.mail import get_connection, send_mail, EmailMessage

import logging
import json
import pandas as pd
import threading
import datetime
import xlsxwriter

logger = logging.getLogger(__name__)

class UnPublishedWIGmeProductReportAPI(APIView):

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):

        response = {}
        response['status'] = 500
        
        try:
            data = request.data
            logger.info("UnPublishedWIGmeProductReportAPI: %s", str(data))

            if not isinstance(data, dict):
                data = json.loads(data)

            location_group_objs = LocationGroup.objects.filter(name__in=["WIGMe - UAE", "WIGme - KWT"])

            filename = "files/reports/"+str(datetime.datetime.now().strftime("%d%m%Y%H%M"))+"_unpublished-products-report.xlsx"

            workbook = xlsxwriter.Workbook(filename)
            worksheet = workbook.add_worksheet()

            row = ["Sr. No.",
                   "Seller SKU",
                   "Product ID",
                   "Website"]

            cnt = 0
                
            colnum = 0
            for k in row:
                worksheet.write(cnt, colnum, k)
                colnum += 1


            total_brand_objs = Brand.objects.none()
            for location_group_obj in location_group_objs:
                total_brand_objs |= location_group_obj.website_group.brands.all()
            total_brand_objs = total_brand_objs.distinct()

            dealshub_product_objs = DealsHubProduct.objects.filter(location_group__in=location_group_objs, product__base_product__brand__in=total_brand_objs, product__no_of_images_for_filter=0, is_published=False)
            for dealshub_product_obj in dealshub_product_objs:
                try:
                    cnt += 1
                    common_row = ["" for i in range(len(row))]
                    common_row[0] = str(cnt)
                    common_row[1] = str(dealshub_product_obj.get_seller_sku())
                    common_row[2] = str(dealshub_product_obj.get_product_id())
                    common_row[3] = str(dealshub_product_obj.location_group.name)

                    colnum = 0
                    for k in common_row:
                        worksheet.write(cnt, colnum, k)
                        colnum += 1
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("UnPublishedWIGmeProductReportAPI: %s at %s", e, str(exc_tb.tb_lineno))        

            workbook.close()

            try:
                with get_connection(
                    host="smtp.gmail.com",
                    port=587, 
                    username=NISARG_EMAIL,
                    password=NISARG_EMAIL_PASSWORD,
                    use_tls=True) as connection:
                    email = EmailMessage(subject='UnPublished Products Report Generated', 
                                         body='This is to inform you that your requested report has been generated on Omnycomm',
                                         from_email=NISARG_EMAIL,
                                         to=["hari.pk@westernint.com","faris.p@westernint.com","wigme.dm@westernint.com","rashid.c@westernint.com","support@westernint.com","marheamwk@gmail.com"],
                                         connection=connection)
                    email.attach_file(filename)
                    email.send(fail_silently=True)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("Error UnPublishedWIGmeProductReportAPI %s %s", e, str(exc_tb.tb_lineno))

            response['status'] = 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("UnPublishedWIGmeProductReportAPI: %s at %s", e, str(exc_tb.tb_lineno))

        return Response(data=response)


UnPublishedWIGmeProductReport = UnPublishedWIGmeProductReportAPI.as_view()
