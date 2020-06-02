import pandas as pd
from WAMSApp.models import *
from MWS import APIs
import time

access_key = 'AKIAI7PSOABCBAJGX36Q' #replace with your access key
seller_id = 'A3DNFJ8JVFH39T' #replace with your seller id
secret_key = '9un2k+5Q4eCFI4SRDjNyLhjTAHXrsFkZe0mWIRop' #replace with your secret key
marketplace_ae = 'A2VIGQ35RCS4UG'

products_api = APIs.Products(access_key, secret_key, seller_id, region='AE')

filename = "scripts/Nesto_Products_Report.xlsx"

dfs = pd.read_excel(filename, sheet_name=None)["Sheet1"]

rows = len(dfs.iloc[:])
columns = len(dfs.iloc[0][:])
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
dfs = dfs.fillna("")

barcodes_list = []

for i in range(rows):
    
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

product_barcodes_list= sorted(barcodes_list, key=lambda x: x[0])

final_barcodes_list = []

for i in range(len(product_barcodes_list)):
    final_barcodes_list.append((product_barcodes_list[i][0],int(float(product_barcodes_list[i][1]))))

temp = final_barcodes_list[0][0]
flag=0
id_list = []
cnt=0
i=0

while i < len(final_barcodes_list):
    print(i)
    try :
        barcode_type = final_barcodes_list[i][0]
        barcode_string = final_barcodes_list[i][1]
        id_list.append(barcode_string)

        
        print(barcode_string)
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
                    
                    find = dfs[dfs["Barcode"]==id_list[j]].index[0]
                    status = parsed_resposne[j]["status"]["value"]
                    
                    if status == "Success":
                        
                        dfs.loc[find, "Matched/Not Matched"] = "Matched"
                        parsed_products = parsed_resposne[j]["Products"]["Product"]

                        if isinstance(parsed_products,list):
                            
                            dfs.loc[find, "ASIN"] = parsed_products[0]["Identifiers"]["MarketplaceASIN"]["ASIN"]["value"]

                            ItemAttributes = parsed_products[0]["AttributeSets"]["ItemAttributes"]
                            
                            if "Title" in ItemAttributes:
                                dfs.loc[find, "Amazon Title"] = ItemAttributes["Title"]["value"]

                            if "Brand" in ItemAttributes:
                                dfs.loc[find, "Amazon Brand"] = ItemAttributes["Brand"]["value"]

                            if "PackageDimensions" in ItemAttributes:
                                PackageDimensions = ItemAttributes["PackageDimensions"]
                                if "Height" in PackageDimensions:
                                    dfs.loc[find, "Package Height"] = PackageDimensions["Height"]["value"] +" "+ PackageDimensions["Height"]["Units"]["value"]
                                if "Width" in PackageDimensions:
                                    dfs.loc[find, "Package Width"] = PackageDimensions["Width"]["value"]+" "+ PackageDimensions["Width"]["Units"]["value"]
                                if "Length" in PackageDimensions:
                                    dfs.loc[find, "Package Length"] = PackageDimensions["Length"]["value"]+" "+ PackageDimensions["Length"]["Units"]["value"]
                                if "Weight" in PackageDimensions:
                                    dfs.loc[find, "Package Weight"] = PackageDimensions["Weight"]["value"] +" "+PackageDimensions["Weight"]["Units"]["value"]
                        
                            if "ItemDimensions" in ItemAttributes:
                                ItemDimensions = ItemAttributes["ItemDimensions"]
                                if "Height" in ItemDimensions:
                                    dfs.loc[find, "Item Height"] = ItemDimensions["Height"]["value"]+" "+ ItemDimensions["Height"]["Units"]["value"]
                                if "Width" in ItemDimensions:
                                    dfs.loc[find, "Item Width"] = ItemDimensions["Width"]["value"] +" "+ItemDimensions["Width"]["Units"]["value"]
                                if "Length" in ItemDimensions:
                                    dfs.loc[find, "Item Length"] = ItemDimensions["Length"]["value"] +" "+ItemDimensions["Length"]["Units"]["value"]
                                if "Weight" in ItemDimensions:
                                    dfs.loc[find, "Item Weight"] = ItemDimensions["Weight"]["value"] +" "+ItemDimensions["Weight"]["Units"]["value"]
                                     
                            if "PackageQuantity" in ItemAttributes:
                                dfs.loc[find, "Package Quantity"] = ItemAttributes["PackageQuantity"]["value"]
                            
                            if "ProductGroup" in ItemAttributes:
                                dfs.loc[find, "Product Group"] = ItemAttributes["ProductGroup"]["value"]
                            
                            if "ProductTypeName" in ItemAttributes:
                                dfs.loc[find, "Product Type"] = ItemAttributes["ProductTypeName"]["value"]

                            if "ListPrice" in ItemAttributes:
                                ListPrice = ItemAttributes["ListPrice"]
                                dfs.loc[find, "List Price"] = ListPrice["Amount"]["value"]
                                dfs.loc[find, "Currency"] = ListPrice["CurrencyCode"]["value"]
                            
                            if "Size" in ItemAttributes:
                                dfs.loc[find, "Size"] = ItemAttributes["Size"]["value"]
                        
                            if "SmallImage" in ItemAttributes:
                                SmallImage = ItemAttributes["SmallImage"]
                                dfs.loc[find, "Image URL"] = SmallImage["URL"]["value"]
                                dfs.loc[find, "Image Height"] = SmallImage["Height"]["value"]+" "+ SmallImage["Height"]["Units"]["value"]
                                dfs.loc[find, "Image Width"] = SmallImage["Width"]["value"]+" "+ SmallImage["Width"]["Units"]["value"]
                        
                        else:
                            dfs.loc[find, "ASIN"] = parsed_products["Identifiers"]["MarketplaceASIN"]["ASIN"]["value"]

                            ItemAttributes = parsed_products["AttributeSets"]["ItemAttributes"]
                            
                            if "Title" in ItemAttributes:
                                dfs.loc[find, "Amazon Title"] = ItemAttributes["Title"]["value"]

                            if "Brand" in ItemAttributes:
                                dfs.loc[find, "Amazon Brand"] = ItemAttributes["Brand"]["value"]

                            if "PackageDimensions" in ItemAttributes:
                                PackageDimensions = ItemAttributes["PackageDimensions"]
                                if "Height" in PackageDimensions:
                                    dfs.loc[find, "Package Height"] = PackageDimensions["Height"]["value"] +" "+PackageDimensions["Height"]["Units"]["value"]
                                if "Width" in PackageDimensions:
                                    dfs.loc[find, "Package Width"] = PackageDimensions["Width"]["value"]+" "+ PackageDimensions["Width"]["Units"]["value"]
                                if "Length" in PackageDimensions:
                                    dfs.loc[find, "Package Length"] = PackageDimensions["Length"]["value"]+" "+ PackageDimensions["Length"]["Units"]["value"]
                                if "Weight" in PackageDimensions:
                                    dfs.loc[find, "Package Weight"] = PackageDimensions["Weight"]["value"] +" "+PackageDimensions["Weight"]["Units"]["value"]
                        
                            if "ItemDimensions" in ItemAttributes:
                                ItemDimensions = ItemAttributes["ItemDimensions"]
                                if "Height" in ItemDimensions:
                                    dfs.loc[find, "Item Height"] = ItemDimensions["Height"]["value"]+" "+ ItemDimensions["Height"]["Units"]["value"]
                                if "Width" in ItemDimensions:
                                    dfs.loc[find, "Item Width"] = ItemDimensions["Width"]["value"]+" "+ ItemDimensions["Width"]["Units"]["value"]
                                if "Length" in ItemDimensions:
                                    dfs.loc[find, "Item Length"] = ItemDimensions["Length"]["value"] +" "+ItemDimensions["Length"]["Units"]["value"]
                                if "Weight" in ItemDimensions:
                                    dfs.loc[find, "Item Weight"] = ItemDimensions["Weight"]["value"] +" "+ItemDimensions["Weight"]["Units"]["value"]
                                     
                            if "PackageQuantity" in ItemAttributes:
                                dfs.loc[find, "Package Quantity"] = ItemAttributes["PackageQuantity"]["value"]
                            
                            if "ProductGroup" in ItemAttributes:
                                dfs.loc[find, "Product Group"] = ItemAttributes["ProductGroup"]["value"]
                            
                            if "ProductTypeName" in ItemAttributes:
                                dfs.loc[find, "Product Type"] = ItemAttributes["ProductTypeName"]["value"]

                            if "ListPrice" in ItemAttributes:
                                ListPrice = ItemAttributes["ListPrice"]
                                dfs.loc[find, "List Price"] = ListPrice["Amount"]["value"]
                                dfs.loc[find, "Currency"] = ListPrice["CurrencyCode"]["value"]
                            
                            if "Size" in ItemAttributes:
                                dfs.loc[find, "Size"] = ItemAttributes["Size"]["value"]
                        
                            if "SmallImage" in ItemAttributes:
                                SmallImage = ItemAttributes["SmallImage"]
                                dfs.loc[find, "Image URL"] = SmallImage["URL"]["value"]
                                dfs.loc[find, "Image Height"] = SmallImage["Height"]["value"]+" "+ SmallImage["Height"]["Units"]["value"]
                                dfs.loc[find, "Image Width"] = SmallImage["Width"]["value"]+" "+ SmallImage["Width"]["Units"]["value"]
                        
                    else :
                        dfs.loc[find, "Matched/Not Matched"] = "Not Matched"

            else:
                
                find = dfs[dfs["Barcode"]==barcode_string].index[0]
                status = parsed_resposne["status"]["value"]
                
                if status == "Success":
                    
                    dfs.loc[find, "Matched/Not Matched"] = "Matched"
                    parsed_products = parsed_resposne["Products"]["Product"]

                    if isinstance(parsed_products,list):
                        
                        dfs.loc[find, "ASIN"] = parsed_products[0]["Identifiers"]["MarketplaceASIN"]["ASIN"]["value"]

                        ItemAttributes = parsed_products[0]["AttributeSets"]["ItemAttributes"]
                        
                        if "Title" in ItemAttributes:
                            dfs.loc[find, "Amazon Title"] = ItemAttributes["Title"]["value"]

                        if "Brand" in ItemAttributes:
                            dfs.loc[find, "Amazon Brand"] = ItemAttributes["Brand"]["value"]

                        if "PackageDimensions" in ItemAttributes:
                            PackageDimensions = ItemAttributes["PackageDimensions"]
                            if "Height" in PackageDimensions:
                                dfs.loc[find, "Package Height"] = PackageDimensions["Height"]["value"]+" "+ PackageDimensions["Height"]["Units"]["value"]
                            if "Width" in PackageDimensions:
                                dfs.loc[find, "Package Width"] = PackageDimensions["Width"]["value"]+" "+ PackageDimensions["Width"]["Units"]["value"]
                            if "Length" in PackageDimensions:
                                dfs.loc[find, "Package Length"] = PackageDimensions["Length"]["value"]+" "+ PackageDimensions["Length"]["Units"]["value"]
                            if "Weight" in PackageDimensions:
                                dfs.loc[find, "Package Weight"] = PackageDimensions["Weight"]["value"]+" "+ PackageDimensions["Weight"]["Units"]["value"]
                    
                        if "ItemDimensions" in ItemAttributes:
                            ItemDimensions = ItemAttributes["ItemDimensions"]
                            if "Height" in ItemDimensions:
                                dfs.loc[find, "Item Height"] = ItemDimensions["Height"]["value"]+" "+ ItemDimensions["Height"]["Units"]["value"]
                            if "Width" in ItemDimensions:
                                dfs.loc[find, "Item Width"] = ItemDimensions["Width"]["value"] +" "+ItemDimensions["Width"]["Units"]["value"]
                            if "Length" in ItemDimensions:
                                dfs.loc[find, "Item Length"] = ItemDimensions["Length"]["value"]+" "+ ItemDimensions["Length"]["Units"]["value"]
                            if "Weight" in ItemDimensions:
                                dfs.loc[find, "Item Weight"] = ItemDimensions["Weight"]["value"] +" "+ItemDimensions["Weight"]["Units"]["value"]
                                 
                        if "PackageQuantity" in ItemAttributes:
                            dfs.loc[find, "Package Quantity"] = ItemAttributes["PackageQuantity"]["value"]
                        
                        if "ProductGroup" in ItemAttributes:
                            dfs.loc[find, "Product Group"] = ItemAttributes["ProductGroup"]["value"]
                        
                        if "ProductTypeName" in ItemAttributes:
                            dfs.loc[find, "Product Type"] = ItemAttributes["ProductTypeName"]["value"]

                        if "ListPrice" in ItemAttributes:
                            ListPrice = ItemAttributes["ListPrice"]
                            dfs.loc[find, "List Price"] = ListPrice["Amount"]["value"]
                            dfs.loc[find, "Currency"] = ListPrice["CurrencyCode"]["value"]
                        
                        if "Size" in ItemAttributes:
                            dfs.loc[find, "Size"] = ItemAttributes["Size"]["value"]
                    
                        if "SmallImage" in ItemAttributes:
                            SmallImage = ItemAttributes["SmallImage"]
                            dfs.loc[find, "Image URL"] = SmallImage["URL"]["value"]
                            dfs.loc[find, "Image Height"] = SmallImage["Height"]["value"]+" "+ SmallImage["Height"]["Units"]["value"]
                            dfs.loc[find, "Image Width"] = SmallImage["Width"]["value"] +" "+SmallImage["Width"]["Units"]["value"]
                    
                    else:
                        dfs.loc[find, "ASIN"] = parsed_products["Identifiers"]["MarketplaceASIN"]["ASIN"]["value"]

                        ItemAttributes = parsed_products["AttributeSets"]["ItemAttributes"]
                        
                        if "Title" in ItemAttributes:
                            dfs.loc[find, "Amazon Title"] = ItemAttributes["Title"]["value"]

                        if "Brand" in ItemAttributes:
                            dfs.loc[find, "Amazon Brand"] = ItemAttributes["Brand"]["value"]

                        if "PackageDimensions" in ItemAttributes:
                            PackageDimensions = ItemAttributes["PackageDimensions"]
                            if "Height" in PackageDimensions:
                                dfs.loc[find, "Package Height"] = PackageDimensions["Height"]["value"]+" "+ PackageDimensions["Height"]["Units"]["value"]
                            if "Width" in PackageDimensions:
                                dfs.loc[find, "Package Width"] = PackageDimensions["Width"]["value"]+" "+ PackageDimensions["Width"]["Units"]["value"]
                            if "Length" in PackageDimensions:
                                dfs.loc[find, "Package Length"] = PackageDimensions["Length"]["value"]+" "+ PackageDimensions["Length"]["Units"]["value"]
                            if "Weight" in PackageDimensions:
                                dfs.loc[find, "Package Weight"] = PackageDimensions["Weight"]["value"]+" "+ PackageDimensions["Weight"]["Units"]["value"]
                    
                        if "ItemDimensions" in ItemAttributes:
                            ItemDimensions = ItemAttributes["ItemDimensions"]
                            if "Height" in ItemDimensions:
                                dfs.loc[find, "Item Height"] = ItemDimensions["Height"]["value"]+" "+ ItemDimensions["Height"]["Units"]["value"]
                            if "Width" in ItemDimensions:
                                dfs.loc[find, "Item Width"] = ItemDimensions["Width"]["value"]+" "+ ItemDimensions["Width"]["Units"]["value"]
                            if "Length" in ItemDimensions:
                                dfs.loc[find, "Item Length"] = ItemDimensions["Length"]["value"]+" "+ ItemDimensions["Length"]["Units"]["value"]
                            if "Weight" in ItemDimensions:
                                dfs.loc[find, "Item Weight"] = ItemDimensions["Weight"]["value"]+" "+ ItemDimensions["Weight"]["Units"]["value"]
                                 
                        if "PackageQuantity" in ItemAttributes:
                            dfs.loc[find, "Package Quantity"] = ItemAttributes["PackageQuantity"]["value"]
                        
                        if "ProductGroup" in ItemAttributes:
                            dfs.loc[find, "Product Group"] = ItemAttributes["ProductGroup"]["value"]
                        
                        if "ProductTypeName" in ItemAttributes:
                            dfs.loc[find, "Product Type"] = ItemAttributes["ProductTypeName"]["value"]

                        if "ListPrice" in ItemAttributes:
                            ListPrice = ItemAttributes["ListPrice"]
                            dfs.loc[find, "List Price"] = ListPrice["Amount"]["value"]
                            dfs.loc[find, "Currency"] = ListPrice["CurrencyCode"]["value"]
                        
                        if "Size" in ItemAttributes:
                            dfs.loc[find, "Size"] = ItemAttributes["Size"]["value"]
                    
                        if "SmallImage" in ItemAttributes:
                            SmallImage = ItemAttributes["SmallImage"]
                            dfs.loc[find, "Image URL"] = SmallImage["URL"]["value"]
                            dfs.loc[find, "Image Height"] = SmallImage["Height"]["value"]+" "+ SmallImage["Height"]["Units"]["value"]
                            dfs.loc[find, "Image Width"] = SmallImage["Width"]["value"]+" "+ SmallImage["Width"]["Units"]["value"]
                    
                else :
                    dfs.loc[find, "Matched/Not Matched"] = "Not Matched"
                
            id_list = []
            flag = 0
            cnt+=1
            print("Cnt :",cnt)
            time.sleep(2)
            print("Timer passed")

        temp = barcode_type
        i+=1

        if len(id_list)==0:
            flag=0

    except Exception as e:
        print(str(e))
        pass

dfs.to_excel(filename,index=False)