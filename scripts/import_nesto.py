import json
import pandas as pd
import os
import sys
from io import BytesIO as StringIO
from WAMSApp.models import *
from PIL import Image as IMage
from django.core.files.uploadedfile import InMemoryUploadedFile
import glob

filename = "./scripts/Nesto.xlsx"
dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]

rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

print dfs.iloc[0]

BASE_PATH = "/home/ubuntu/thumbs/"
CURR_PATH = os.getcwd()

organization_obj, created = Organization.objects.get_or_create(name="Nesto")

not_inserted = []
nesto_images_error = []
article_id_error = []

cnt = 0
#rows = 23
os.chdir(BASE_PATH)
for i in range(rows):
    try:
        cnt += 1
        print cnt
        article_id = str(dfs.iloc[i][0])
        product_name = str(dfs.iloc[i][1].encode('ascii', errors='ignore'))
        brand = str(dfs.iloc[i][2])
        measure = str(dfs.iloc[i][3])
        unit = str(dfs.iloc[i][4])
        barcode = str(dfs.iloc[i][5])

        if brand.lower() in ["", "none", "null"]:
            brand = "Nesto"

        if Product.objects.filter(product_id=article_id).exists():
            not_inserted.append({"article_id": str(article_id), "i":str(i)})
            continue

        brand_obj = None
        if Brand.objects.filter(name=brand.lower()).exists():
            brand_obj = Brand.objects.get(name=brand.lower())
        else:
            brand_obj = Brand.objects.create(name=brand.lower(),
                                             organization=organization_obj)

        product_obj = Product.objects.create(product_name_sap=product_name,
                                             product_name_amazon_uk=product_name,
                                             product_id=article_id,
                                             brand=brand_obj,
                                             barcode_string=barcode)


        if unit in ["Bag", "Box", "Dzn", "Mah", "Pieces", "packet", "pieces"]:
            # unit is of type unit count
            if unit=="pieces":
                unit = "Pieces"
            try:
                product_obj.item_count = float(measure)
                product_obj.item_count_metric = unit
                product_obj.save()
            except Exception as e:
                print("Error with units, article_id: ", article_id)
                article_id_error.append({"product_pk": product_obj.pk})
        elif unit in ["Cl", "Gal", "Litre", "Oz", "ml"]:
            # unit is of type Volume
            if unit=="Cl":
                unit = "cl"
            elif unit=="Litre":
                unit = "litres"
            elif unit=="Oz":
                unit = "OZ"
            try:
                product_obj.item_display_volume = float(measure)
                product_obj.item_display_volume_metric = unit
            except Exception as e:
                print("Error with units, article_id: ", article_id)
                article_id_error.append({"product_pk": product_obj.pk})
        elif unit in ["Cm", "Ft", "Mt", "Sq ft", "Inches", "mm"]:
            # unit is of type Length
            if unit=="Cm":
                unit = "CM"
            elif unit=="Ft":
                unit = "FT"
            elif unit=="Mt":
                unit = "M"
            elif unit=="Inches":
                unit = "IN"
            elif unit=="mm":
                unit = "MM"

            try:
                product_obj.item_length = float(measure)
                product_obj.item_length_metric = unit
            except Exception as e:
                print("Error with units, article_id: ", article_id)
                article_id_error.append({"product_pk": product_obj.pk})
        elif unit in ["Kg", "Mg", "gm", "lbs"]:
            # unit is of type Weight
            if unit=="Kg":
                unit = "KG"
            elif unit=="lbs":
                unit = "LB"
            elif unit=="Mg":
                unit = "MG"
            elif unit=="gm":
                unit = "GR"
            try:
                product_obj.item_weight = float(measure)
                product_obj.item_weight_metric = unit
            except Exception as e:
                print("Error with units, article_id: ", article_id)
                article_id_error.append({"product_pk": product_obj.pk})


        try:
            filepath = None
            try:
                filepath = str(dfs.iloc[i][6])
                if os.path.exists(filepath) == False:
                    pattern = "".join(filepath.split(".")[0:-1])+"*"
                    if len(glob.glob(pattern))>0:
                        filepath = glob.glob(pattern)[0]
                    else:
                        pattern = pattern[:len(pattern)/2]+"*"
                        if len(glob.glob(pattern))>0:
                            filepath = glob.glob(pattern)[0]
                        else:
                            nesto_images_error.append({"article_id": str(article_id), "i":str(i), "file":str(dfs.iloc[i][6])})
            except Exception as e:
                nesto_images_error.append({"article_id": str(article_id), "i":str(i), "file":str(dfs.iloc[i][6])})
                print("Error images", str(e))


            if os.path.exists(filepath) == True:
                thumb = IMage.open(filepath)
                im_type = thumb.format
                thumb_io = StringIO.StringIO()
                thumb.save(thumb_io, format=im_type)

                thumb_file = InMemoryUploadedFile(thumb_io, None, filepath, 'image/'+im_type, thumb_io.len, None)

                image_obj = Image.objects.create(image=thumb_file)
                image_bucket_obj = ImageBucket.objects.create(image=image_obj, is_main_image=True)
                product_obj.main_images.add(image_bucket_obj)
                product_obj.save()

        except Exception as e:
            nesto_images_error.append({"article_id": str(article_id), "i":str(i), "file":str(dfs.iloc[i][6])})
            print("Error images", str(e))

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error: %s at %s", e, str(exc_tb.tb_lineno))


os.chdir(CURR_PATH)

f = open("not_inserted.txt", "w")
f.write(json.dumps(not_inserted))
f.close()


f = open("nesto_images_error.txt", "w")
f.write(json.dumps(nesto_images_error))
f.close()


f = open("article_id_error.txt", "w")
f.write(json.dumps(article_id_error))
f.close()

from WAMSApp.models import *
import json
seller_id = 'A3DNFJ8JVFH39T' #replace with your seller id

def generate_xml_for_post_product_data(product_pk_list,seller_id):
    cnt=0
    try:
         # Check if Cached
        xml_string = """<?xml version="1.0"?>
                        <AmazonEnvelope xsi:noNamespaceSchemaLocation="amzn-envelope.xsd"
                            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                            <Header>
                                <DocumentVersion>1.01</DocumentVersion>
                                <MerchantIdentifier>"""+seller_id+"""</MerchantIdentifier>
                            </Header>
                            <MessageType>Product</MessageType>
                            <PurgeAndReplace>false</PurgeAndReplace>"""
        
        for product_pk in product_pk_list:

            try:
                product_obj = Product.objects.get(pk=int(product_pk))
                message_id = str(product_pk)
                seller_sku = product_obj.base_product.seller_sku
                product_id_type = product_obj.product_id_type.name
                product_id = product_obj.barcode_string

                xml_string += """<Message>
                                    <MessageID>"""+ message_id +"""</MessageID>
                                    <OperationType>Update</OperationType> 
                                    <Product>
                                        <SKU>"""+ seller_sku +"""</SKU>
                                        <StandardProductID>
                                            <Type>"""+product_id_type+"""</Type>
                                            <Value>"""+product_id +"""</Value>
                                        </StandardProductID>
                                        <Condition>
                                            <ConditionType>New</ConditionType>
                                        </Condition>
                                    </Product>
                                </Message> """
                cnt+=1
                print("Cnt :",cnt)
            except Exception as e:
                print("Hii",str(e))
                pass

        xml_string += """</AmazonEnvelope>"""
        # xml_string = xml_string.encode('utf-8')
        # print(xml_string)
        return xml_string

    except Exception as e:
        print(str(e))
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("Generating XML UAE: %s at %s", e, str(exc_tb.tb_lineno))
        return ""

product_objs_list = Product.objects.filter(base_product__brand__organization__name="Nesto").exclude(barcode_string="")

product_pk_list = list(product_objs_list.values_list('pk',flat=True))

xml = generate_xml_for_post_product_data(product_pk_list,seller_id)

f = open("feed.txt","w")
f.write(xml)
f.close()

import json
import xlsxwriter
from WAMSApp.models import *

workbook = xlsxwriter.Workbook('./files/csv/all_nesto_products.xlsx')
worksheet = workbook.add_worksheet()
rownum =0

worksheet.write(rownum, 0,"Seller SKU")
worksheet.write(rownum, 1,"Product Name")
worksheet.write(rownum, 2,"Product ID")
worksheet.write(rownum, 3,"Product ID Type")
worksheet.write(rownum, 4,"Barcode")
worksheet.write(rownum, 5,"Brand")
worksheet.write(rownum, 6,"Category")

product_objs_list = Product.objects.filter(base_product__brand__organization__name="Nesto")

cnt =0

for prod in product_objs_list:
    
    try:

        seller_sku = prod.base_product.seller_sku
        product_name = prod.product_name
        product_id = prod.product_id
        barcode_string = prod.barcode_string


        if prod.base_product.brand!=None:
            brand = prod.base_product.brand.name
        else:
            brand = ""

        if prod.base_product.category!=None:
            category = prod.base_product.category.name
        else:
            category = ""
        
        if prod.product_id_type!=None:
            product_id_type = prod.product_id_type.name
        else:
            product_id_type = ""

        rownum+=1
        worksheet.write(rownum, 0,seller_sku)
        worksheet.write(rownum, 1,product_name)
        worksheet.write(rownum, 2,product_id)
        worksheet.write(rownum, 3,product_id_type)
        worksheet.write(rownum, 4,barcode_string)
        worksheet.write(rownum, 5,brand)
        worksheet.write(rownum, 6,category)

        cnt+=1
        print("Cnt: ",cnt)

    except Exception as e:
        print(str(e))
        pass

workbook.close()


import pandas as pd
from WAMSApp.models import *

filename = "scripts/all_nesto_products.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]
dfs.loc[:, 'OmnyComm Error'] = ""
dfs.loc[:, 'OmnyComm Error Mesage'] = ""
rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

dfs = dfs.fillna("")

for i in range(rows): #len(rows):
    print(i)
    try:

        seller_sku = str(dfs.iloc[i,0])
        product_name = str(dfs.iloc[i,1])
        product_id = str(dfs.iloc[i,2])
        product_id_type = str(dfs.iloc[i,3])
        barcode_string = str(dfs.iloc[i,4])
        brand = str(dfs.iloc[i,5])
        category = str(dfs.iloc[i,6])

        if "UNDEFINED" in seller_sku:
            dfs.iloc[i,7] = "OC_01"
            dfs.iloc[i,8] = "Invalid Seller SKU"

        elif product_id_type == "":
            dfs.iloc[i,7] = "OC_02"
            dfs.iloc[i,8] = "Invalid Product ID"

        elif brand == "":
            dfs.iloc[i,7] = "OC_03"
            dfs.iloc[i,8] = "Brand not Assigned"

        elif category == "":
            dfs.iloc[i,7] = "OC_04"
            dfs.iloc[i,8] = "Category not Assigned"

    except Exception as e:
        print(str(e))
        pass

dfs.to_excel(filename,index=False)

# dfs.loc[dfs[dfs["Seller SKU"]=="UNDEFINED_11975"].index, "OmnyComm Error"]

from MWS import APIs

access_key = 'AKIAI7PSOABCBAJGX36Q' #replace with your access key
seller_id = 'A3DNFJ8JVFH39T' #replace with your seller id
secret_key = '9un2k+5Q4eCFI4SRDjNyLhjTAHXrsFkZe0mWIRop' #replace with your secret key
marketplace_ae = 'A2VIGQ35RCS4UG'

feeds_api = APIs.Feeds(access_key, secret_key, seller_id, region='AE')
response_feed_submission_result = feeds_api.get_feed_submission_result(50582018380)

feed_submission_result = response_feed_submission_result.parsed

errors = []

result = feed_submission_result["ProcessingReport"]["Result"]

if isinstance(result,list):
    for i in range(len(result)):
        temp_dict = {}
        temp_dict["product_pk"] = result[i]["MessageID"]["value"]
        temp_dict["error_type"] = result[i]["ResultCode"]["value"]
        temp_dict["error_code"] = result[i]["ResultMessageCode"]["value"]
        temp_dict["error_message"] = result[i]["ResultDescription"]["value"]
        temp_dict["seller_sku"] = result[i]["AdditionalInfo"]["SKU"]["value"]
        errors.append(temp_dict)
else:
    temp_dict = {}
    temp_dict["product_pk"] = result["MessageID"]["value"]
    temp_dict["error_type"] = result["ResultCode"]["value"]
    temp_dict["error_code"] = result["ResultMessageCode"]["value"]
    temp_dict["error_message"] = result["ResultDescription"]["value"]
    temp_dict["seller_sku"] = result[i]["AdditionalInfo"]["SKU"]["value"]
    errors.append(temp_dict)

filename = "scripts/all_nesto_products.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]

dfs.loc[:, 'Amazon Error'] = ""
dfs.loc[:, 'Amazon Error Mesage'] = ""
dfs.loc[:, 'Amazon Error 2'] = ""
dfs.loc[:, 'Amazon Error Mesabarcodes_listge 2'] = ""
dfs.loc[:, 'Amazon Error 3'] = ""
dfs.loc[:, 'Amazon Error Mesage 3'] = ""

dfs = dfs.fillna("")

cnt=0
for i in range(len(errors)):
    # print(errors[i][seller_sku])
    cnt+=1
    print("Cnt :",cnt)
    find = dfs[dfs["Seller SKU"]==errors[i]["seller_sku"]].index[0]
    if dfs.loc[find, "Amazon Error"] == "":
        dfs.loc[find, "Amazon Error"] = errors[i]["error_code"]
        dfs.loc[find, "Amazon Error Mesage"] = errors[i]["error_message"]
    elif dfs.loc[find, "Amazon Error 2"] == "":
        dfs.loc[find, "Amazon Error 2"] = errors[i]["error_code"]
        dfs.loc[find, "Amazon Error Mesage 2"] = errors[i]["error_message"]
    else:
        dfs.loc[find, "Amazon Error 3"] = errors[i]["error_code"]
        dfs.loc[find, "Amazon Error Mesage 3"] = errors[i]["error_message"]

dfs.to_excel(filename,index=False)

import pandas as pd
from WAMSApp.models import *

filename = "scripts/Nesto_Products_Report.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]

rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

dfs = dfs.fillna("")

barcodes_list = []

for i in range(rows):
    print(i)
    
    try:
        product_id_type = str(dfs.iloc[i,3])
        barcode_string = str(dfs.iloc[i,4])
        amazon_error1 = dfs.iloc[i,9]
        amazon_error2 = dfs.iloc[i,11]
        
        if barcode_string != "" and amazon_error1 != 8105:
            
            if amazon_error1 != 8560 and amazon_error1 != 8058:
                barcodes_list.append((product_id_type,barcode_string))
            elif amazon_error2 != "":
                barcodes_list.append((product_id_type,barcode_string))
            

    except Exception as e:
        print(str(e))
        pass

dfs.loc[:, 'Matched/Not Matched'] = ""
dfs.loc[:, 'Amazon Title'] = ""
dfs.loc[:, 'ASIN'] = ""
dfs.loc[:, 'Amazon Brand'] = ""
dfs.loc[:, 'Item Height'] = ""
dfs.loc[:, 'Item Length'] = ""
dfs.loc[:, 'Item Width'] = ""
dfs.loc[:, 'Item Weight'] = ""
dfs.loc[:, 'Package Height'] = ""
dfs.loc[:, 'Package Length'] = ""
dfs.loc[:, 'Package Width'] = ""
dfs.loc[:, 'Package Weight'] = ""
dfs.loc[:, 'Package Quantity'] = ""
dfs.loc[:, 'Product Group'] = ""
dfs.loc[:, 'Product Type'] = ""
dfs.loc[:, 'Image URL'] = ""
dfs.loc[:, 'Image Height'] = ""
dfs.loc[:, 'Image Width'] = ""
dfs.loc[:, 'List Price'] = ""
dfs.loc[:, 'Currency'] = ""
dfs.loc[:, 'Size'] = ""

product_barcodes_list = []

for i in range(len(final_barcodes_list)):
    product_barcodes_list.append((final_barcodes_list[i][0],int(float(final_barcodes_list[i][1]))))


temp = final_barcodes_list[0][0]
flag=0
id_list = []
pk_list = []
cnt=0
i=0

while i < len(final_barcodes_list):
    
    barcode_type = final_barcodes_list[i][0]
    barcode_string = final_barcodes_list[i][1]
    id_list.append(barcode_string)
    
    if temp != barcode_type:
        flag=1
        i-=1
        id_list.pop()
    
    if flag != 1:
        if i%5 == 4:
            flag=1
    
    if i == len(final_barcodes_list) - 1:
        flag=1
    
    if flag==1 and len(id_list) !=0:
        
        respose = products_api.get_matching_product_for_id(marketplace_id=marketplace_ae, type_=temp, ids = id_list)
        parsed_resposne = respose.parsed

        if isinstance(parsed_resposne,list):

            for j in range(len(parsed_resposne)):
                
                find = dfs[dfs["Barcode"]==barcode_string].index[0]
                status = parsed_resposne[j]["status"]["value"]
                
                if status == "Success":
                    
                    dfs.loc[find, "Matched/Not Matched"] = "Matched"
                    parsed_products = parsed_resposne[j]["Products"]["Product"]

                    if isinstance(parsed_products,list):
                        
                        dfs.loc[find, "ASIN"] = parsed_products[0]["Identifiers"]["MarketplaceASIN"]["ASIN"]["value"]

                        ItemAttributes = parsed_products[0]["AttributeSets"]["ItemAttributes"]
                        
                        dfs.loc[find, "Amazon Title"] = ItemAttributes["Title"]["value"]
                        dfs.loc[find, "Amazon Brand"] = ItemAttributes["Brand"]["value"]

                        PackageDimensions = ItemAttributes["PackageDimensions"]
                        dfs.loc[find, "Package Height"] = PackageDimensions["Height"]["value"] + PackageDimensions["Height"]["Units"]["value"]
                        dfs.loc[find, "Package Width"] = PackageDimensions["Width"]["value"] + PackageDimensions["Width"]["Units"]["value"]
                        dfs.loc[find, "Package Length"] = PackageDimensions["Length"]["value"] + PackageDimensions["Length"]["Units"]["value"]
                        dfs.loc[find, "Package Weight"] = PackageDimensions["Weight"]["value"] + PackageDimensions["Weight"]["Units"]["value"]
                    
                        ItemDimensions = ItemAttributes["PackageDimensions"]
                        dfs.loc[find, "Item Height"] = ItemDimensions["Height"]["value"] + ItemDimensions["Height"]["Units"]["value"]
                        dfs.loc[find, "Item Width"] = ItemDimensions["Width"]["value"] + ItemDimensions["Width"]["Units"]["value"]
                        dfs.loc[find, "Item Length"] = ItemDimensions["Length"]["value"] + ItemDimensions["Length"]["Units"]["value"]
                        dfs.loc[find, "Item Weight"] = ItemDimensions["Weight"]["value"] + ItemDimensions["Weight"]["Units"]["value"]
                    
                        dfs.loc[find, "Package Quantity"] = ItemAttributes["PackageQuantity"]["value"]
                        
                        dfs.loc[find, "Product Group"] = ItemAttributes["ProductGroup"]["value"]
                        dfs.loc[find, "Product Type"] = ItemAttributes["ProductTypeName"]["value"]

                        ListPrice = ItemAttributes["ListPrice"]
                        dfs.loc[find, "List Price"] = ListPrice["Amount"]["value"]
                        dfs.loc[find, "Currency"] = ListPrice["CurrencyCode"]["value"]
                        
                        dfs.loc[find, "Size"] = ItemAttributes["Size"]["value"]
                    
                        SmallImage = ItemAttributes["SmallImage"]
                        dfs.loc[find, "Image URL"] = SmallImage["URL"]["value"]
                        dfs.loc[find, "Image Height"] = SmallImage["Height"]["value"] + SmallImage["Height"]["Units"]["value"]
                        dfs.loc[find, "Image Width"] = SmallImage["Width"]["value"] + SmallImage["Width"]["Units"]["value"]
                    
                    else:
                        temp_dict["matched_ASIN"] = products.parsed[j]["Products"]["Product"]["Identifiers"]["MarketplaceASIN"]["ASIN"]["value"]
                        temp_dict["matched_product_feed_submission_id"] = products.parsed[j]["Products"]["Product"]["AttributeSets"]["ItemAttributes"]["Title"]["value"]
                else :
                    dfs.loc[find, "Matched/Not Matched"] = "Not Matched"

        else:
            temp_dict = {}
            temp_dict["status"] = products.parsed["status"]["value"]
            temp_dict["matched_ASIN"] = ""
            if temp_dict["status"] == "Success":
                parsed_products = products.parsed["Products"]["Product"]
                if isinstance(parsed_products,list):
                    temp_dict["matched_ASIN"] = parsed_products[0]["Identifiers"]["MarketplaceASIN"]["ASIN"]["value"]
                    temp_dict["matched_product_feed_submission_id"] = parsed_products[0]["AttributeSets"]["ItemAttributes"]["Title"]["value"]
                else:
                    temp_dict["matched_ASIN"] = products.parsed["Products"]["Product"]["Identifiers"]["MarketplaceASIN"]["ASIN"]["value"]
                    temp_dict["matched_product_feed_submission_id"] = products.parsed["Products"]["Product"]["AttributeSets"]["ItemAttributes"]["Title"]["value"]
            else :
                temp_dict["status"] = "New Product"

            matched_products_list.append(temp_dict)
            
        id_list = []
        flag = 0
        cnt+=1

        time.sleep(1)

    temp = barcode_type
    i+=1

    if len(id_list)==0:
        flag=0

import pandas as pd

filename = "scripts/Nesto_Products_Report.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]

rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

dfs = dfs.fillna("")

barcodes_list = {}
seller_sku_list = []
cnt=0
for i in range(rows):
    try:
        
        barcode_string = str(dfs.iloc[i,4])
        seller_sku = str(dfs.iloc[i,0])
        if barcode_string != "":
            if barcode_string in barcodes_list:
                if "UNDEFINED" in seller_sku:
                    seller_sku_list.append(seller_sku)
                elif "UNDEFINED" in barcodes_list[barcode_string]:
                    seller_sku_list.append(barcodes_list[barcode_string])
                cnt+=1
            else:
                if "UNDEFINED" in seller_sku:
                    barcodes_list[barcode_string] = seller_sku
                else:
                    barcodes_list[barcode_string] = "1"

    except Exception as e:
        print(str(e))
        pass

print(cnt)

cnt = 0
for seller_sku in seller_sku_list :
    cnt+=1
    find = dfs[dfs["Seller SKU"]==seller_sku].index
    dfs = dfs.drop(find)
    print(cnt)


import pandas as pd
import re 

filename = "scripts/Nesto_Products_Report.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Final Report"]

rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

dfs = dfs.fillna("")


Product_Name = dfs["Product Name"]
dfs.loc[:, 'OmnyComm Size'] = ""

for i in range(len(Product_Name)):
    try:
        name = Product_Name[i]
        name = name.lower()
        print(name)
        metric = ""
        flag=0
        if "ml" in name :
            metric = "ml"
        elif "lt" in name :
            metric = "lt"
        elif "gm" in name :
            metric = "gm"
        elif "gal" in name :
            metric = "gal"
        elif "kg" in name :
            metric = "kg"
        elif "lb" in name :
            metric = "lb"
        elif "cm" in name :
            metric = "cm"
        elif "mm" in name :
            metric = "mm"
        elif "inch" in name :
            metric = "inch"
        elif "ft" in name :
            metric = "ft"
        elif "oz" in name :
            metric = "oz"
        elif "lb" in name :
            metric = "lb"
        elif "xxl" in name :
            flag=1
            metric = "xxl"
        elif "xl" in name :
            flag=1
            metric = "xl"
        elif "mah" in name :
            metric = "mah"
        elif "watt" in name :
            metric = "watt"
        elif "a5" in name :
            metric = "a5"
            flag=1
        elif "a4" in name :
            metric = "a4"
            flag=1
        elif "a3" in name :
            metric = "a3"
            flag=1
        elif "a2" in name :
            metric = "a2"
            flag=1
        elif "a1" in name :
            metric = "a1"
            flag=1
        elif "sq" in name:
            metric = "sq"
        elif "pkt" in name:
            metric = "pkt"
        
        if flag==1:
            x=metric
            dfs.loc[i, "OmnyComm Size"] = x 
        elif metric != "":
            # name = jergens foot cream 100ml @20% off
            # name = J&J Baby Oil 500Ml+200Ml Free
            x = name.split(metric)[:-1]
            # x = ['jergens foot cream 100']
            # x = ['J&J Baby Oil 500' , '+200']
            x = x[0] 
            # x[0] = 'jergens foot cream 100'
            # x[0] = 'J&J Baby Oil 500'
            y = x.split(" ")[-1]
            if y== "":
                y = x.split(" ")[-2]
            # x = ['jeergens', 'foot', 'cream', '100']
            if metric =="sq":
                metric = "sqft"
            if y!= "" and y[0].isdigit():
                dfs.loc[i, "OmnyComm Size"] = y + " " + metric
            print(y + " " + metric)
    except Exception as e:
        pass
    print(i)

dfs.to_excel(filename,index=False)


print(cnt_ml_lt_gal)
print(cnt_gm_kg_oz_lb)
print(cnt_cm_mm_inch_ft)
print(cnt_xl_xxl)
print(cnt_mah_watt)
print(cnt_a4_a5_a3_a2_a1)
print(cnt_sqf)
print(cnt_pkt)
print("Total Left : " , len(Product_Name) - 
    cnt_mah_watt - cnt_xl_xxl - 
    cnt_ml_lt_gal - cnt_gm_kg_oz_lb - 
    cnt_cm_mm_inch_ft - cnt_a4_a5_a3_a2_a1 - 
    cnt_sqf - cnt_pkt)


dfs.loc[:, 'Documents Required'] = "" 
cnt=0
for i in range(rows):
    print(i)
    
    try:
        amazon_error1 = dfs.iloc[i,10]
        amazon_error2 = dfs.iloc[i,12]
        print(amazon_error1,amazon_error2)
        if(amazon_error1==6024 or amazon_error1==6039 or amazon_error1==8026):
            cnt+=1
            dfs.loc[i, "Documents Required"] = "True"
        elif(amazon_error2==6024 or amazon_error2==6039 or amazon_error2==8026):
            cnt+=1
            dfs.loc[i, "Documents Required"] = "True"
        else:
            dfs.loc[i, "Documents Required"] = "False"

    except Exception as e:
        print(str(e))
        pass


import pandas as pd
from WAMSApp.models import *

filename = "scripts/delcasa_products.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["delcasa total"]
rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

dfs = dfs.fillna("")

brand , created = Brand.objects.get_or_create(name="Delcasa")

cnt=0

for i in range(rows):

    try:
        seller_sku = str(dfs.iloc[i,0])
        product_name = str(dfs.iloc[i,1])
        barcode_string = str(dfs.iloc[i,3])
        product_id = str(dfs.iloc[i,3])
        category = str(dfs.iloc[i,4])

        product_id_type = ProductIDType.objects.get(name="EAN")

        category , created = Category.objects.get_or_create(name=category)

        base_product,created = BaseProduct.objects.get_or_create(seller_sku=seller_sku)

        base_product.base_product_name=product_name 
        base_product.category=category
        base_product.brand = brand

        base_product.save()
        
        product = Product.objects.create(base_product=base_product,
                                        product_name = product_name,
                                        product_id = product_id,
                                        barcode_string = barcode_string,
                                        product_id_type=product_id_type) 

        cnt +=1
        print("Cnt :",cnt)

    except Exception as e:
        print(str(e))
        pass

filename = "scripts/Royalford_Check.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]
dfs.loc[:, 'Present'] = ""
rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

dfs = dfs.fillna("")


cnt=0
for i in range(rows): #len(rows):
    print(i)
    try:

        seller_sku = str(dfs.iloc[i,2])

        try:
            p = BaseProduct.objects.get(seller_sku=seller_sku)
            dfs.loc[i, "Present"] = "True"
            cnt+=1

        except Exception as e:
            dfs.loc[i, "Present"] = "False"


    except Exception as e:
        print(str(e))
        pass

print("Cnt :",cnt)
dfs.to_excel(filename,index=False)


from WAMSApp.models import *

base_product_objs = BaseProduct.objects.filter(brand__organization__name="Nesto")
base_product_objs = base_product_objs.filter(seller_sku__icontains="UNDEFINED")

cnt=0
cnt1=0
cnt2=0
cnt3=0
cnt4=0
i=0
for base_product in base_product_objs:
    try:
        i+=1
        print(i)
        product_objs = Product.objects.filter(base_product=base_product)
        product_obj = product_objs[0]
        product_id = product_obj.product_id
        barcode_string = product_obj.barcode_string
        matched_product_objs = Product.objects.filter(barcode_string=barcode_string).exclude(base_product__seller_sku__icontains="UNDEFINED")
        if len(matched_product_objs)>1:
            matched_product_obj = matched_product_objs[0]
            matched_product_objs = Product.objects.filter(barcode_string=barcode_string,base_product__seller_sku__icontains="UNDEFINED")
            for product in matched_product_objs:
                if product.product_name.lower() in matched_product_obj.product_name:
                    cnt1+=1
                    product.delete()
                    product.base_product.delete()
            cnt+=1
        matched_product_objs = Product.objects.filter(base_product__seller_sku=product_id)
        if len(matched_product_objs)>=1:
            matched_product_obj = matched_product_objs[0]
            for product in product_objs:
                if product.product_name.lower() in matched_product_obj.product_name:
                    cnt3+=1
                    product.delete()
                    product.base_product.delete()
            cnt4+=1
        elif product_id != "":
            try :
                cnt2+=1
                base_product.seller_sku = product_id
                base_product.save()
            except Exception as e:
                pass
    except Exception as e:
        print(str(e))
        pass

cnt1=0
cnt2=0
i=0
from WAMSApp.models import *

base_product_objs = BaseProduct.objects.filter(brand__organization__name="Nesto")

for base_product in base_product_objs:
    i+=1
    print(i)
    try:
        if "UNDEFINED" in base_product.seller_sku:
            product_objs = Product.objects.filter(base_product=base_product)
            product_obj = product_objs[0]
            product_id = product_obj.product_id
            if len(BaseProduct.objects.filter(seller_sku=product_id)) >0:
                flag=1
                for product in product_objs:
                    if len(Product.objects.filter(barcode_string=product.barcode_string)) >1:
                        product.delete()
                    else:
                        flag=0
                if flag==1:
                    base_product.delete()
                cnt1+=1
            else:
                base_product.seller_sku = product_id
                base_product.save()
                cnt2+=1
    except Exception as e:
        print(str(e))
        pass

import pandas as pd
from WAMSApp.models import *
from dealshub.models import *

filename = "scripts/Nesto_Prices.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]
dfs.loc[:, 'Updated/Not Found'] = ""
rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

dfs = dfs.fillna("")
cnt=0

for i in range(rows):
    print(i)
    try:
        product_name = str(dfs.iloc[i,0])
        brand = str(dfs.iloc[i,1])
        seller_sku = str(dfs.iloc[i,4])
        price = float(dfs.iloc[i,5])

        base_product = BaseProduct.objects.get(seller_sku=seller_sku)
        dealshub_product = DealsHubProduct.objects.get(product__base_product=base_product)

        dealshub_product.was_price = price
        dealshub_product.now_price = price
        dealshub_product.save()

        dfs.loc[i, 'Updated/Not Found'] = "Updated"
        cnt+=1
    except Exception as e:
        print(str(e))
        dfs.loc[i, 'Updated/Not Found'] = "Not Found"
        pass

print("Cnt : ",cnt)


import pandas as pd
from WAMSApp.models import *
from dealshub.models import *

filename = "scripts/New_Listings.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Royal ford"]
dfs.loc[:, 'New/Existing'] = ""
rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

dfs = dfs.fillna("")
cnt=0

brand = Brand.objects.get(name="RoyalFord")
product_id_type = ProductIDType.objects.get(name="EAN")

for i in range(rows):
    print(i)
    try:
        category = str(dfs.iloc[i,0])
        sub_category = str(dfs.iloc[i,1])
        seller_sku = str(dfs.iloc[i,2])
        product_name = str(dfs.iloc[i,3])
        barcode = str(dfs.iloc[i,4])
        product_id = str(dfs.iloc[i,4])

        try:
            base_product = BaseProduct.objects.get(seller_sku=seller_sku)
            dfs.loc[i, 'New/Existing'] = "Existing"

        except Exception as e:
            
            if(len(barcode)==13):
                
                pid_type = product_id_type
            
                category, created = Category.objects.get_or_create(name=category)
                sub_category, created = SubCategory.objects.get_or_create(name=sub_category,category=category)

                base_product = BaseProduct.objects.create(seller_sku=seller_sku,
                                                            category=category,
                                                            sub_category=sub_category,
                                                            brand=brand,
                                                            base_product_name=product_name)

                product = Product.objects.create(base_product=base_product,
                                                product_name=product_name,
                                                product_id_type=pid_type,
                                                product_id = product_id,
                                                barcode_string=barcode)

                dfs.loc[i, 'New/Existing'] = "New"
                cnt+=1
    
    except Exception as e:
        print(str(e))
        # dfs.loc[i, 'Updated/Not Found'] = "Not Found"
        pass

print("Cnt : ",cnt)


from WAMSApp.models import *
oc = OmnyCommUser.objects.get(username="arsal")
cp, created = CustomPermission.objects.get_or_create(user=oc)
brand_obj = Brand.objects.get(name="Delcasa")
cp.brands.add(brand_obj)
cp.save()





import pandas as pd
from WAMSApp.models import *

filename = "scripts/BabyPlus_Products.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]
rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

dfs = dfs.fillna("")
cnt=0

brand_obj = Brand.objects.get(name="Baby Plus")
product_id_type = ProductIDType.objects.get(name="EAN")
i=22
while i < rows:
    print(i)
    try:
        category = str(dfs.iloc[i,0])
        seller_sku = str(dfs.iloc[i,1])
        product_name = str(dfs.iloc[i,2])
        barcode = str(dfs.iloc[i,3])
        product_id = str(dfs.iloc[i,3])
        status = str(dfs.iloc[i,4])
        
        if status== "Not Created":
            try:
                print(seller_sku)

                category , c = Category.objects.get_or_create(name=category)
                sub_category , c = SubCategory.objects.get_or_create(name=category.name)

                base_product = BaseProduct.objects.create(base_product_name=product_name,
                                                          seller_sku=seller_sku,
                                                          brand=brand_obj,
                                                          category=category,
                                                          sub_category=sub_category)
                
                product = Product.objects.create(base_product=base_product,
                                                product_name=product_name,
                                                product_id_type=product_id_type,
                                                product_id = product_id,
                                                barcode_string=barcode)
                cnt+=1

            except Exception as e:
               print(str(e))

        else:
            break
    
    except Exception as e:
        print(str(e))
        # dfs.loc[i, 'Updated/Not Found'] = "Not Found"
        pass
    i+= 1

print("Cnt : ",cnt)

dfs.to_excel(filename,index=False)


from WAMSApp.models import *
import json
cs = ChannelProduct.objects.all()
cnt=0
for c in cs:
    uk = json.loads(c.amazon_uk_product_json)
    uae = json.loads(c.amazon_uae_product_json)
    n = json.loads(c.noon_product_json)
    e = json.loads(c.ebay_product_json)
    uk["status"] = "Inactive"
    uae["status"] = "Inactive"
    n["status"] = "Inactive"
    e["status"] = "Inactive"
    c.amazon_uk_product_json = json.dumps(uk)
    c.amazon_uae_product_json = json.dumps(uae)
    c.noon_product_json = json.dumps(n)
    c.ebay_product_json = json.dumps(e)
    c.save()
    cnt+=1
    print("Cnt : ",cnt)




from WAMSApp.models import *

noon_product_json_template = {
    "product_name" : "",
    "noon_sku" : "",
    "parent_sku" : "",
    "parent_barcode" : "",
    "category" : "",
    "subtitle" : "",
    "sub_category" : "",
    "model_number" : "",
    "model_name" : "",
    "msrp_ae" : "",
    "msrp_ae_unit" : "",
    "product_description" : "",
    "product_attribute_list" : [],
    "created_date" : "",
    "status" : "Inactive",
    "http_link": "",
    "price":"",
    "sale_price":"",
    "sale_start":"",
    "sale_end":"",
    "quantity":"",
    "warranty":""
}
amazon_uk_product_json_template = {
    "product_name" : "",
    "product_description" : "",
    "product_attribute_list" : [],
    "category" : "",
    "sub_category" : "",
    "created_date" : "",
    "parentage" : "",
    "parent_sku" : "",
    "relationship_type" : "",
    "variation_theme" : "",
    "feed_product_type" : "",
    "ASIN" : "",
    "update_delete" : "",
    "recommended_browse_nodes" : "",
    "search_terms" : "",
    "enclosure_material" : "",
    "cover_material_type" : "",
    "special_features" : [],
    "sale_price" : "",
    "sale_from" : "",
    "sale_end" :  "",
    "wattage" : "",
    "wattage_metric" : "",
    "item_count" : "",
    "item_count_metric" : "",
    "item_condition_note" : "",
    "max_order_quantity" : "",
    "number_of_items" : "",
    "condition_type" : "",
    "dimensions": {
        "package_length":"",
        "package_length_metric":"",
        "package_width":"",
        "package_width_metric":"",
        "package_height":"",
        "package_height_metric":"",
        "package_weight":"",
        "package_weight_metric":"",
        "package_quantity":"",
        "shipping_weight":"",
        "shipping_weight_metric":"",
        "item_display_weight":"",
        "item_display_weight_metric":"",
        "item_display_volume":"",
        "item_display_volume_metric":"",
        "item_display_length":"",
        "item_display_length_metric":"",
        "item_weight":"",
        "item_weight_metric":"",
        "item_length":"",
        "item_length_metric":"",
        "item_width":"",
        "item_width_metric":"",
        "item_height":"",
        "item_height_metric":"",
        "item_display_width":"",
        "item_display_width_metric":"",
        "item_display_height":"",
        "item_display_height_metric":""
    },
    "status" : "Inactive",
    "http_link": "",
    "price":"",
    "quantity":""
}
amazon_uae_product_json_template = {
    "product_name" : "",
    "product_description" : "",
    "product_attribute_list" : [],
    "category" : "",
    "sub_category" : "",
    "created_date" : "",
    "feed_product_type" : "",
    "ASIN" : "",
    "recommended_browse_nodes" : "",
    "update_delete" : "",
    "status" : "Inactive",
    "http_link": "",
    "price":"",
    "quantity":""
}
ebay_product_json_template = {
    "category" : "",
    "sub_category" : "",
    "product_name" : "",
    "product_description" : "",
    "product_attribute_list" : [],
    "created_date" : "",
    "status" : "Inactive",
    "http_link": "",
    "price":"",
    "quantity":""
}


ch_objs = ChannelProduct.objects.all()
i=0
for ch_obj in ch_objs:
    i+=1
    print(i)
    json_attr = json.loads(ch_obj.noon_product_json)
    for key in noon_product_json_template:
        if key not in json_attr:
            json_attr[key] = noon_product_json_template[key]
    ch_obj.noon_product_json = json.dumps(json_attr)
    json_attr = json.loads(ch_obj.amazon_uk_product_json)
    for key in amazon_uk_product_json_template:
        if key not in json_attr:
            json_attr[key] = amazon_uk_product_json_template[key]
    ch_obj.amazon_uk_product_json = json.dumps(json_attr)
    json_attr = json.loads(ch_obj.amazon_uae_product_json)
    for key in amazon_uae_product_json_template:
        if key not in json_attr:
            json_attr[key] = amazon_uae_product_json_template[key]
    ch_obj.amazon_uae_product_json = json.dumps(json_attr)
    json_attr = json.loads(ch_obj.ebay_product_json)
    for key in ebay_product_json_template:
        if key not in json_attr:
            json_attr[key] = ebay_product_json_template[key]
    ch_obj.ebay_product_json = json.dumps(json_attr)
    ch_obj.save()    


import pandas as pd
from WAMSApp.models import *
from dealshub.models import *

filename = "scripts/Babyplus_Price_List.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]
dfs.loc[:, 'Updated/Not Found'] = ""
rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

dfs = dfs.fillna("")
cnt=0

for i in range(rows):
    print(i)
    try:
        seller_sku = str(dfs.iloc[i,0])
        seller_sku1 = str(dfs.iloc[i,1])
        seller_sku2 = str(dfs.iloc[i,2])
        was_price = float(dfs.iloc[i,3])
        now_price = float(dfs.iloc[i,4])

        try:
            base_product = BaseProduct.objects.get(seller_sku=seller_sku)
        except Exception as e:
            try:
                base_product = BaseProduct.objects.get(seller_sku=seller_sku1)
            except Exception as e1:
                base_product = BaseProduct.objects.get(seller_sku=seller_sku2)


        product = Product.objects.filter(base_product=base_product)[0]
        dealshub_product ,c  = DealsHubProduct.objects.get_or_create(product=product)

        dealshub_product.was_price = was_price
        dealshub_product.now_price = now_price
        dealshub_product.save()

        dfs.loc[i, 'Updated/Not Found'] = "Updated"
        cnt+=1
    except Exception as e:
        print(str(e))
        dfs.loc[i, 'Updated/Not Found'] = "Not Found"
        pass

print("Cnt : ",cnt)

dfs.to_excel(filename,index=False)


import pandas as pd
from WAMSApp.models import *
from dealshub.models import *

filenames = ["scripts/Olsenamark_Stock_List.xlsx", "scripts/Geepas_Stock_List.xlsx",
 "scripts/Royalford_Stock_List.xlsx", "scripts/Krypton_Stock_List.xlsx"]

for filename in filenames :
    dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]
    dfs.loc[:, 'Updated/Not Found'] = ""
    rows = len(dfs.iloc[:])
    columns = len(dfs.iloc[0][:])
    dfs = dfs.fillna("")
    cnt=0
    for i in range(rows):
        # print(i)
        try:
            seller_sku = str(dfs.iloc[i,0])
            was_price = float(dfs.iloc[i,1])
            now_price = float(dfs.iloc[i,2])
            stock = float(dfs.iloc[i,4])
            base_product = BaseProduct.objects.get(seller_sku=seller_sku)
            product = Product.objects.filter(base_product=base_product)[0]
            dealshub_product = DealsHubProduct.objects.get(product=product)
            dealshub_product.was_price = was_price
            dealshub_product.now_price = now_price
            dealshub_product.stock = stock
            dealshub_product.save()
            dfs.loc[i, 'Updated/Not Found'] = "Updated"
            cnt+=1
        except Exception as e:
            # print(str(e))
            dfs.loc[i, 'Updated/Not Found'] = "Not Found"
            pass
    print()
    print(filename, "Cnt : ",cnt)
    print()
    dfs.to_excel(filename,index=False)

import pandas as pd
from WAMSApp.models import *
from dealshub.models import *

filename = "scripts/Babyplus_Stock_List.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]
dfs.loc[:, 'Updated/Not Found'] = ""
rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

dfs = dfs.fillna("")
cnt=0

for i in range(rows):
    print(i)
    try:
        seller_sku = str(dfs.iloc[i,0])
        seller_sku1 = str(dfs.iloc[i,1])
        seller_sku2 = str(dfs.iloc[i,2])
        was_price = float(dfs.iloc[i,3])
        now_price = float(dfs.iloc[i,4])
        stock = float(dfs.iloc[i,5])

        try:
            base_product = BaseProduct.objects.get(seller_sku=seller_sku)
        except Exception as e:
            try:
                base_product = BaseProduct.objects.get(seller_sku=seller_sku1)
            except Exception as e1:
                base_product = BaseProduct.objects.get(seller_sku=seller_sku2)


        product = Product.objects.filter(base_product=base_product)[0]
        dealshub_product = DealsHubProduct.objects.get(product=product)

        dealshub_product.stock = stock
        dealshub_product.save()

        dfs.loc[i, 'Updated/Not Found'] = "Updated"
        cnt+=1
    except Exception as e:
        print(str(e))
        dfs.loc[i, 'Updated/Not Found'] = "Not Found"
        pass

print("Cnt : ",cnt)

dfs.to_excel(filename,index=False)



import pandas as pd
from WAMSApp.models import *
from dealshub.models import *
import urllib
from PIL import Image as IMAGE
import requests
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile

filename = "scripts/Parajohn_products.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]
rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

dfs = dfs.fillna("")
cnt=0

brand_obj, c = Brand.objects.get_or_create(name="Parajohn")

for i in range(rows):
    print(i)
    try:
        product_name = str(dfs.iloc[i][1])
        seller_sku = str(dfs.iloc[i][3])
        super_category = str(dfs.iloc[i][7])
        category = str(dfs.iloc[i][8])
        sub_category = str(dfs.iloc[i][9])
        product_description = str(dfs.iloc[i][10])
        material = str(dfs.iloc[i][12])
        main_image_url = str(dfs.iloc[i][24])
        sub_image_urls = []
        sub_image_url1 = str(dfs.iloc[i][25])
        if sub_image_url1 != "":
            if "https" not in sub_image_url1 and "Https" not in sub_image_url1:
                sub_image_url1 = "https:/"+sub_image_url1
            sub_image_urls.append(sub_image_url1)
        sub_image_url2 = str(dfs.iloc[i][26])
        if sub_image_url2 != "":
            if "https" not in sub_image_url2 and "Https" not in sub_image_url2:
                sub_image_url2 = "https:/"+sub_image_url2
            sub_image_urls.append(sub_image_url2)
        sub_image_url3 = str(dfs.iloc[i][27])
        if sub_image_url3 != "":
            if "https" not in sub_image_url3 and "Https" not in sub_image_url3:
                sub_image_url3 = "https:/"+sub_image_url3
            sub_image_urls.append(sub_image_url3)
        sub_image_url4 = str(dfs.iloc[i][28])
        if sub_image_url4 != "":
            if "https" not in sub_image_url4 and "Https" not in sub_image_url4:
                sub_image_url4 = "https:/"+sub_image_url4
            sub_image_urls.append(sub_image_url4)
        sub_image_url5 = str(dfs.iloc[i][29])
        if sub_image_url5 != "":
            if "https" not in sub_image_url5 and "Https" not in sub_image_url5:
                sub_image_url5 = "https:/"+sub_image_url5
            sub_image_urls.append(sub_image_url5)
        sub_image_url6 = str(dfs.iloc[i][30])
        if sub_image_url6 != "":
            if "https" not in sub_image_url6 and "Https" not in sub_image_url6:
                sub_image_url6 = "https:/"+sub_image_url6
            sub_image_urls.append(sub_image_url6)
        sub_image_url7 = str(dfs.iloc[i][31])
        if sub_image_url7 != "":
            if "https" not in sub_image_url7 and "Https" not in sub_image_url7:
                sub_image_url7 = "https:/"+sub_image_url7
            sub_image_urls.append(sub_image_url7)
        sub_image_url8 = str(dfs.iloc[i][32])
        if sub_image_url8 != "":
            if "https" not in sub_image_url8 and "Https" not in sub_image_url8:
                sub_image_url8 = "https:/"+sub_image_url8
            sub_image_urls.append(sub_image_url8)
        sub_image_url9 = str(dfs.iloc[i][33])
        if sub_image_url9 != "":
            if "https" not in sub_image_url9 and "Https" not in sub_image_url9:
                sub_image_url9 = "https:/"+sub_image_url9
            sub_image_urls.append(sub_image_url9)
        print(sub_image_urls)
        base_product , created = BaseProduct.objects.get_or_create(seller_sku=seller_sku)
        if Product.objects.filter(base_product=base_product).exists():
            product_obj = Product.objects.filter(base_product=base_product)[0]
        else:
            product_obj = Product.objects.create(base_product=base_product)
        sub_images_objs = []
        sub_images_obj,c = SubImages.objects.get_or_create(product = product_obj,is_sourced=True)
        sub_images_obj.sub_images.clear()
        sub_images_objs.append(sub_images_obj)
        chan = Channel.objects.get(name="Amazon UK")
        sub_images_obj,c = SubImages.objects.get_or_create(product = product_obj,channel=chan)
        sub_images_obj.sub_images.clear()
        sub_images_objs.append(sub_images_obj)
        chan = Channel.objects.get(name="Amazon UAE")
        sub_images_obj,c = SubImages.objects.get_or_create(product = product_obj,channel=chan)
        sub_images_obj.sub_images.clear()
        sub_images_objs.append(sub_images_obj)
        chan = Channel.objects.get(name="Noon")
        sub_images_obj,c = SubImages.objects.get_or_create(product = product_obj,channel=chan)
        sub_images_obj.sub_images.clear()
        sub_images_objs.append(sub_images_obj)
        chan = Channel.objects.get(name="Ebay")
        sub_images_obj,c = SubImages.objects.get_or_create(product = product_obj,channel=chan)
        sub_images_obj.sub_images.clear()
        sub_images_objs.append(sub_images_obj)
        for sub_image_url in sub_image_urls:
            size = 512, 512 
            response = requests.get(sub_image_url, timeout=10)
            thumb = IMAGE.open(BytesIO(response.content))
            thumb.thumbnail(size)
            infile = str(sub_image_url.split("/")[-1]) 
            im_type = thumb.format 
            thumb_io = BytesIO()
            thumb.save(thumb_io, format=im_type)
            thumb_file = InMemoryUploadedFile(thumb_io, None, infile, 'image/'+im_type, thumb_io.getbuffer().nbytes, None)
            image_obj = Image.objects.create(image=thumb_file)
            image_bucket_obj = ImageBucket.objects.create(image=image_obj)
            for sub_images_obj in sub_images_objs:
                sub_images_obj.sub_images.add(image_bucket_obj)
                sub_images_obj.save()
    except Exception as e:
        print(str(e))
        pass

filename = "Downloads/Wigme_Geepas_Data_Aswin.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]
rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

dfs = dfs.fillna("")
cnt=0


import pandas as pd
from WAMSApp.models import *
from dealshub.models import *

filename = "scripts/Babyplus_Price_Stock_List.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]
dfs.loc[:, 'Updated/Not Found'] = ""
rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])
dfs = dfs.fillna("")
cnt=0
for i in range(rows):
    print(i)
    try:
        seller_sku = str(dfs.iloc[i,0])
        was_price = float(dfs.iloc[i,2])
        now_price = float(dfs.iloc[i,1])
        stock = float(dfs.iloc[i,3])
        base_product = BaseProduct.objects.get(seller_sku=seller_sku)
        product = Product.objects.filter(base_product=base_product)[0]
        dealshub_product = DealsHubProduct.objects.get(product=product)
        dealshub_product.was_price = was_price
        dealshub_product.now_price = now_price
        dealshub_product.stock = stock
        dealshub_product.save()
        dfs.loc[i, 'Updated/Not Found'] = "Updated"
        cnt+=1
    except Exception as e:
        print(str(e))
        dfs.loc[i, 'Updated/Not Found'] = "Not Found"
        pass


print(filename, "Cnt : ",cnt)

dfs.to_excel(filename,index=False)

brand = Brand.objects.get(name="Geepas")

for x in ba:
    if "G" == x.seller_sku[0]:
        print(x.seller_sku)
        x.brand = brand
        x.save() 

ms = MainImages.objects.all()
i=0
for m in ms:
    print(i)
    i+=1
    if m.main_images.all().count()==1:
        img = m.main_images.all()[0]
        img.is_main_image=True
        img.save()

p = Product.objects.annotate(text_len=Length('product_id')).exclude(
    text_len=13)
i=0
for x in p:
    print(i)
    i+=1
    x.save()

brands = ["Geepas","Royalford","Delcasa"]

p = Product.objects.filter(base_product__brand__name__in=brands).filter(product_id_type__name="EAN")
i=0
for x in p:
    print(i)
    i+=1
    if x.barcode_string == "":
        x.barcode=None
        x.barcode_string=x.product_id
        x.save()

import pandas as pd
from WAMSApp.models import *
from dealshub.models import *
import xlsxwriter
import json
filename = "scripts/All_Listings_Report.xlsx"
dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]
dfs = dfs.fillna("")
rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])
cnt=0
for i in range(rows):
    print(i)
    all_products = Product.objects.filter(base_product__seller_sku=str(dfs.iloc[i][0]))
    for product_obj in all_products:
        channel_product = product_obj.channel_product
        amazon_uae_product_json = channel_product.amazon_uae_product_json
        amazon_uae_product_json = json.loads(amazon_uae_product_json)
        if dfs.iloc[i][4] != "":
            amazon_uae_product_json['price'] = float(dfs.iloc[i][4])
            amazon_uae_product_json['was_price'] = float(dfs.iloc[i][4])
            amazon_uae_product_json['now_price'] = float(dfs.iloc[i][4])
        if dfs.iloc[i][5] != "":
            amazon_uae_product_json['stock'] = int(dfs.iloc[i][5])
            amazon_uae_product_json['quantity'] = int(dfs.iloc[i][5])
        # if str(dfs.iloc[i][6]) == "Active":
        #     amazon_uae_product_json['status'] = "Active"
        # elif str(dfs.iloc[i][6]) == "Inactive":
        #     amazon_uae_product_json['status'] = "Listed"
        #     cnt+=1
        #     print("Cnt : ",cnt)
        amazon_uae_product_json = json.dumps(amazon_uae_product_json)
        channel_product.amazon_uae_product_json = amazon_uae_product_json
        channel_product.save()


from WAMSApp.models import *
import math
c = ChannelProduct.objects.all()
i=0
cnt =0
for x in c:
    try:
        if i%50==0:
            print(i)
        i+=1
        uk = json.loads(x.noon_product_json)
        if type(uk["price"]) != int and uk["quantity"] != ""  and uk["quantity"] !="nan":
            uk["stock"] = int(float(str(uk["quantity"]).strip()))
        elif type(uk["quantity"]) == str:
            uk["quantity"] = 0
        if type(uk["price"]) != float and uk["price"] != ""  and uk["price"] !="nan":
            uk["was_price"] = float(str(uk["price"]).strip())
            uk["now_price"] = float(str(uk["price"]).strip())
        elif type(uk["price"]) == str:
            uk["was_price"] = 0.0
            uk["now_price"] = 0.0
        x.noon_product_json = json.dumps(uk)        
        if uk["status"] =="Listed":
            cnt+=1
            print("Cnt : " , cnt)
        uk = json.loads(x.amazon_uk_product_json)
        if type(uk["price"]) != int and uk["quantity"] != ""  and uk["quantity"] !="nan":
            uk["stock"] = int(float(str(uk["quantity"]).strip()))
        elif type(uk["quantity"]) == str:
            uk["quantity"] = 0
        if type(uk["price"]) != float and uk["price"] != ""  and uk["price"] !="nan":
            uk["was_price"] = float(str(uk["price"]).strip())
            uk["now_price"] = float(str(uk["price"]).strip())
        elif type(uk["price"]) == str:
            uk["was_price"] = 0.0
            uk["now_price"] = 0.0
        x.amazon_uk_product_json = json.dumps(uk)
        uk = json.loads(x.amazon_uae_product_json)
        if type(uk["price"]) != int and uk["quantity"] != ""  and uk["quantity"] !="nan":
            uk["stock"] = int(float(str(uk["quantity"]).strip()))
        elif type(uk["quantity"]) == str:
            uk["quantity"] = 0
        if type(uk["price"]) != float and uk["price"] != ""  and uk["price"] !="nan":
            uk["was_price"] = float(str(uk["price"]).strip())
            uk["now_price"] = float(str(uk["price"]).strip())
        elif type(uk["price"]) == str:
            uk["was_price"] = 0.0
            uk["now_price"] = 0.0
        x.amazon_uae_product_json = json.dumps(uk)
        uk = json.loads(x.ebay_product_json)
        if type(uk["price"]) != int and uk["quantity"] != ""  and uk["quantity"] !="nan":
            uk["stock"] = int(float(str(uk["quantity"]).strip()))
        elif type(uk["quantity"]) == str:
            uk["quantity"] = 0
        if type(uk["price"]) != float and uk["price"] != ""  and uk["price"] !="nan":
            uk["was_price"] = float(str(uk["price"]).strip())
            uk["now_price"] = float(str(uk["price"]).strip())
        elif type(uk["price"]) == str:
            uk["was_price"] = 0.0
            uk["now_price"] = 0.0
        x.ebay_product_json = json.dumps(uk)
        x.save()
    except Exception as e:
        import sys
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(str(e) , str(exc_tb.tb_lineno))
        print(x.pk , "   " , type(uk["quantity"]) , "  " , uk["quantity"])




from WAMSApp.models import *
p = Product.objects.get(base_product__seller_sku="RF7604")
c = p.channel_product
x = json.loads(c.noon_product_json)
print(x["was_price"])
print(x["now_price"])
print(x["stock"])

from WAMSApp.models import *
import math
c = ChannelProduct.objects.all()
i=0
cnt =0
for x in c:
    if i%50==0:
        print(i)
    i+=1
    uk = json.loads(x.noon_product_json)      
    if uk["status"] =="Active":
        cnt+=1
        print("Cnt : " , cnt)


from WAMSApp.models import *
import json
cnt=0
for channel_product in ChannelProduct.objects.all():
    cnt+=1
    print("Cnt : ",cnt)
    noon_product_json = json.loads(channel_product.noon_product_json)
    parent_sku = noon_product_json.get("parent_sku","") 
    if("partner_sku" not in noon_product_json):
        noon_product_json["partner_sku"] = ""
    if(parent_sku != ""):
        noon_product_json["partner_sku"] = parent_sku
    parent_barcode = noon_product_json.get("parent_barcode","") 
    if("partner_barcode" not in noon_product_json):
        noon_product_json["partner_barcode"] = ""
    if(parent_barcode != ""):
        noon_product_json["partner_barcode"] = parent_barcode
    noon_product_json["sale_price"] = noon_product_json["now_price"]
    channel_product.noon_product_json = json.dumps(noon_product_json)
    channel_product.save()


import pandas as pd
from WAMSApp.models import *

filename = "../../../../Downloads/Price_Upload.xlsx"
dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]

dfs = dfs.fillna("")
rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])

print(dfs.iloc[2][2])

from dealshub.models import *
import json, math
# cc = ChannelProduct.objects.filter(amazon_uae_product_json__contains="NaN")
cc = ChannelProduct.objects.exclude(amazon_uae_product_json__icontains="sale_price",noon_product_json__icontains="sale_price")
i=0
for c in cc:
    print(i)
    i = i+1
    t = json.loads(c.amazon_uae_product_json)
    t["was_price"] = t["now_price"]
    c.amazon_uae_product_json = json.dumps(t)
    t = json.loads(c.noon_product_json)
    t["was_price"] = t["now_price"]
    c.noon_product_json = json.dumps(t)
    c.save()
    if type(json.loads(c.amazon_uae_product_json)["was_price"])!=str and math.isnan(json.loads(c.amazon_uae_product_json)["was_price"]):
        print("YES1", c)
        t = json.loads(c.amazon_uae_product_json)
        t["was_price"] = 0.0
        c.amazon_uae_product_json = json.dumps(t)
        c.save()
    if type(json.loads(c.amazon_uae_product_json)["now_price"])!=str and math.isnan(json.loads(c.amazon_uae_product_json)["now_price"]):
        print("YES2", c)
    if type(json.loads(c.amazon_uae_product_json)["stock"])!=str and math.isnan(json.loads(c.amazon_uae_product_json)["stock"]):
        print("YES3", c)
    if type(json.loads(c.amazon_uae_product_json)["quantity"])!=str and math.isnan(json.loads(c.amazon_uae_product_json)["quantity"]):
        print("YES4", c)
    if type(json.loads(c.amazon_uae_product_json)["sale_price"])!=str and math.isnan(json.loads(c.amazon_uae_product_json)["sale_price"]):
        print("YES5", c)
        t = json.loads(c.amazon_uae_product_json)
        t["sale_price"] = 0.0
        c.amazon_uae_product_json = json.dumps(t)
        c.save()

from dealshub.models import *
import json, math
cnt=0
cc = ChannelProduct.objects.exclude(amazon_uae_product_json__contains="sale_price")
for c in cc:
    t = json.loads(c.amazon_uae_product_json)
    t["sale_price"] = t["now_price"]
    c.amazon_uae_product_json = json.dumps(t)
    c.save()
    cnt+=1
    print(cnt)


from WAMSApp.models import *
pp = Product.objects.all()
cnt=0
for p in pp:
    try:
        product_name = p.product_name  
        brand = p.base_product.brand.name 
        seller_sku = p.base_product.seller_sku 
        product_id = p.product_id 
        final_product_name = product_name
        product_name_list = product_name.split(" ")
        for e in product_name_list:
            if seller_sku.lower() in e.lower():
                final_product_name = final_product_name.replace(e,"")
            if brand.lower() in e.lower():
                final_product_name = final_product_name.replace(e,"")
            if str(product_id) != "" and str(product_id) in e:
                final_product_name = final_product_name.replace(e,"")
        final_product_name = final_product_name.strip()
        final_product_name = final_product_name.replace("  "," ")
        p.product_name = final_product_name
        p.save()
        # print(product_name)
        # print(final_product_name)
        # print()
        # print()
        cnt+=1
        print(cnt)
    except Exception as e:
        pass

from WAMSApp.models import *
pp = Product.objects.filter(product_name__icontains="-")
cnt=0
for p in pp:
    try:
        product_name = p.product_name  
        brand = p.base_product.brand.name 
        seller_sku = p.base_product.seller_sku 
        product_id = p.product_id 
        final_product_name = product_name
        product_name_list = product_name.split(" ")
        e= product_name_list[0]
        if e.lower() == "-":
            final_product_name = final_product_name.replace(e,"")
            cnt+=1
            print(cnt)
        final_product_name = final_product_name.strip()
        final_product_name = final_product_name.replace("  "," ")
        p.product_name = final_product_name
        # print(product_name)
        # print(final_product_name)
        # print()
        # print()
        p.save()
    except Exception as e:
        pass

import json
import pandas as pd
import os
import sys
from io import BytesIO as StringIO
from WAMSApp.models import *
from PIL import Image as IMage
from django.core.files.uploadedfile import InMemoryUploadedFile
import glob

filename = "scripts/Delete_Products.xlsx"
dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]
dfs = dfs.fillna("")
rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])
cnt=0

for i in range(rows):
    seller_sku = str(dfs.iloc[i][6])
    try :
        product_id = str(int(dfs.iloc[i][1]))
    except Exception as e:
        product_id = ""
    product_name = str(dfs.iloc[i][2])
    all_products = Product.objects.filter(base_product__seller_sku=seller_sku)
    for product_obj in all_products:
        # cnt+=1
        # print("Cnt : ",cnt)
        if product_obj.product_id == product_id and product_obj.product_name==product_name:
            product_obj.channel_product.delete()
            product_obj.delete()
            cnt+=1
            print("Cnt : ",cnt)
        else:
            print(product_obj.product_id , "    " , product_id)
    if Product.objects.filter(base_product__seller_sku=seller_sku).all().count()==0:
        base_product_obj = BaseProduct.objects.get(seller_sku=seller_sku)
        base_product_obj.delete()

from dealshub.models import *
super_category_obj , created = SuperCategory.objects.get_or_create(name="GENERAL")
category_obj ,created = Category.objects.get_or_create(name="GENERAL",super_category=super_category_obj)
sub_category_obj , created= SubCategory.objects.get_or_create(name="GENERAL",category=category_obj)
BaseProduct.objects.filter(super_category=None).update(super_category=super_category_obj)
BaseProduct.objects.filter(category=None).update(category=category_obj)
BaseProduct.objects.filter(sub_category=None).update(sub_category=sub_category_obj)

from dealshub.models import *
pp = Product.objects.exclude(base_product=None)
i=0
for p in pp:
    try :
        print(i)
        i+=1
        category = p.base_product.category.name
        sub_category = p.base_product.sub_category.name
        t = json.loads(p.channel_product.amazon_uae_product_json)
        t["category"] = category
        t["sub_category"] = sub_category
        p.channel_product.amazon_uae_product_json = json.dumps(t)
        p.channel_product.save()
    except Exception as e:
        pass

from dealshub.models import *
import pandas as pd
filename = "scripts/Category_List.xlsx"
dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]
dfs = dfs.fillna("")
rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])
cnt=0
for i in range(rows):
    print(i)
    super_category = str(dfs.iloc[i][0])
    category = str(dfs.iloc[i][1])
    sub_category = str(dfs.iloc[i][2])
    print(super_category+"  "+category+"  "+sub_category)
    sap_super_category , created = SapSuperCategory.objects.get_or_create(super_category=super_category) 
    sap_category , created = SapCategory.objects.get_or_create(super_category=sap_super_category,category=category) 
    sap_sub_category , created = SapSubCategory.objects.get_or_create(category=sap_category,sub_category=sub_category) 
    category_mapping , created = CategoryMapping.objects.get_or_create(sap_sub_category=sap_sub_category) 