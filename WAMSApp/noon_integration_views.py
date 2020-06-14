import json
import csv
import requests

partner_id = "11109"
country_code = "ae"
partner_warehouse_code = "12345"

headers = {
			"x-partner": "11109", 
			"x-api-token": "AIzaSyCxOIBdBpXFeo_4YctGCimGaVkusHDu4ZQ",
			"content-type" : "application/json"
		}

# with open('/tmp/noon_price_update.tsv', 'wt') as out_file:
#     tsv_writer = csv.writer(out_file, delimiter='\t')
#     tsv_writer.writerow(['country_code', 'id_partner','partner_sku','price','sale_end','sale_price','sale_start'])
#     tsv_writer.writerow([country_code, partner_id , "TEST_1",str(float(25)),"","",""])
#     tsv_writer.writerow([country_code, partner_id , "TEST_2",str(float(24)),"","",""])
#     tsv_writer.writerow([country_code, partner_id , "TEST_3",str(float(23)),"","",""])

# urls = requests.post('https://integration.noon.partners/public/signed-url/noon_price_update.tsv',
# 						 headers=headers).json()

# response = requests.put(urls['upload_url'], data=open('/tmp/noon_price_update.tsv','rb')).raise_for_status()

# payload = {
# 			"filename": "noon_price_update.tsv", 
# 			"import_type": "integration_psku_update", 
# 			"url": urls['download_url'],
# 			"partner_import_ref": ""
# 		}

with open('/tmp/noon_stock_update.tsv', 'wt') as out_file:
    tsv_writer = csv.writer(out_file, delimiter='\t')
    tsv_writer.writerow(['id_partner','partner_sku','partner_warehouse_code','stock_gross','stock_updated_at'])
    tsv_writer.writerow([partner_id , "TEST_1",partner_warehouse_code,str(int(130)),""])
    tsv_writer.writerow([partner_id , "TEST_2",partner_warehouse_code,str(int(500)),""])
    tsv_writer.writerow([partner_id , "TEST_3",partner_warehouse_code,str(int(150)),""])
   

urls = requests.post('https://integration.noon.partners/public/signed-url/noon_stock_update.tsv',
						 headers=headers).json()

response = requests.put(urls['upload_url'], data=open('/tmp/noon_stock_update.tsv','rb')).raise_for_status()

payload = {
			"filename": "noon_stock_update.tsv", 
			"import_type": "integration_partner_warehouse_stock", 
			"url": urls['download_url'],
			"partner_import_ref": ""
		}

response = requests.post('https://integration.noon.partners/public/webhook/v2/partner-import', 
				data=json.dumps(payload),
				headers=headers)