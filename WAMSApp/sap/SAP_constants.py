BRAND_COMPANY_DICT = {
    "geepas": "1000",
    "baby plus": "5550",
    "royalford": "3000",
    "krypton": "2100",
    "olsenmark": "1100",
    "ken jardene": "5550",
    "younglife": "5000",
    "para john" : "6000",
    "parry life" : "6000",
    "delcasa": "3050"
}

WIGME_COMPANY_CODE = 1200

######### TESTING URLS ############
PRICE_STOCK_URL = "http://94.56.89.116:8000/sap/bc/srt/rfc/sap/zser_stock_price/150/zser_stock_price/zbin_stock_price"
TRANSFER_HOLDING_URL = "http://94.56.89.116:8000/sap/bc/srt/rfc/sap/zser_holding_so/150/zser_holding_so/zbin_holding_so"
ONLINE_ORDER_URL = "http://94.56.89.116:8000/sap/bc/srt/rfc/sap/zser_online_order/150/zser_online_order/zbin_online_order"
PRODUCT_HOLDING_URL = "http://94.56.89.116:8000/sap/bc/srt/rfc/sap/zser_article_holding_rpt/150/zser_article_holding_rpt/zbin_article_holding_rpt"


CUSTOMER_ID = "40000195"
CUSTOMER_ID_FINAL_BILLING = "50000151"

CUSTOMER_ID_FINAL_BILLING_WIG_COD = "50000151"
CUSTOMER_ID_FINAL_BILLING_WIG_ONLINE = "50000151"
CUSTOMER_ID_FINAL_BILLING_GRAND_GAADI_COD = "50001061"
CUSTOMER_ID_FINAL_BILLING_GRAND_GAADI_ONLINE = "50001062"
CUSTOMER_ID_FINAL_BILLING_SENDEX_COD = "50000151"
CUSTOMER_ID_FINAL_BILLING_SENDEX_ONLINE = "50000151"
CUSTOMER_ID_FINAL_BILLING_STANDARD_COD = "50000151"
CUSTOMER_ID_FINAL_BILLING_STANDARD_ONLINE = "50000151"

# For B2B
CUSTOMER_ID_FINAL_BILLING_WIG_COD_B2B = "50001128"
CUSTOMER_ID_FINAL_BILLING_WIG_ONLINE_B2B = "50001129"
CUSTOMER_ID_FINAL_BILLING_SENDEX_COD_B2B = "50001111"
CUSTOMER_ID_FINAL_BILLING_SENDEX_ONLINE_B2B = "50001112"
CUSTOMER_ID_FINAL_BILLING_GRAND_GAADI_COD_B2B = "50001130"
CUSTOMER_ID_FINAL_BILLING_GRAND_GAADI_ONLINE_B2B = "50001131"

GRN_FOLDER_NAME = "omnicom"

#*********** SAP Credentials ****************#

SAP_USERNAME = "MOBSERVICE"
SAP_PASSWORD = "geepas"     # QA
# SAP_PASSWORD = "~lDT8+QklV=("     # Prod

# old credentials = ("MOBSERVICE", "~lDT8+QklV=(")

#********************************************#

#**************** SAP codes *******************#

SAP_ATTR_CODES = {
    "alternate_uom": "AUOM", 
    "base_uom": "BUOM", 
    "conversion_factor": "CFACT", 
    "gross_weight": "GWEIG", 
    "gross_weight_unit": "GWEIU", 
    "net_weight": "NWEIG", 
    "net_weight_unit": "NWEIU", 
    "length": "LAENG", 
    "width": "BREIT", 
    "height": "HOEHE", 
    "length_measurement_unit": "MEABM", 
    "country_name": "LANDX" 
} 

SAP_CERT_CODES = {
    "certification_type": "CERT_TYPE", 
    "validity_start_date": "VLSTDT", 
    "validity_end_date": "VLENDT"
}

#***********************************************#

######### PRODUCTION URLS ##########
# PRICE_STOCK_URL = "http://wig.westernint.com:8000/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"
# TRANSFER_HOLDING_URL = "http://wig.westernint.com:8000/sap/bc/srt/rfc/sap/zser_holding_so/300/zser_holding_so/zbin_holding_so"
# ONLINE_ORDER_URL = "http://wig.westernint.com:8000/sap/bc/srt/rfc/sap/zser_online_order/300/zser_online_order/zbin_online_order"  

# CUSTOMER_ID = "40000637"

# CUSTOMER_ID_FINAL_BILLING_WIG_COD = "50000391"
# CUSTOMER_ID_FINAL_BILLING_WIG_ONLINE = "50000392"
# CUSTOMER_ID_FINAL_BILLING_POSTAPLUS_COD = "50000666"
# CUSTOMER_ID_FINAL_BILLING_POSTAPLUS_ONLINE = "50000667"
# CUSTOMER_ID_FINAL_BILLING_SENDEX_COD = "50000876"
# CUSTOMER_ID_FINAL_BILLING_SENDEX_ONLINE = "50000877"
# CUSTOMER_ID_FINAL_BILLING_STANDARD_COD = "50000872"
# CUSTOMER_ID_FINAL_BILLING_STANDARD_ONLINE = "50000871"

# For B2B
# CUSTOMER_ID_FINAL_BILLING_WIG_COD_B2B = "50001128"
# CUSTOMER_ID_FINAL_BILLING_WIG_ONLINE_B2B = "50001129"
# CUSTOMER_ID_FINAL_BILLING_SENDEX_COD_B2B = "50001111"
# CUSTOMER_ID_FINAL_BILLING_SENDEX_ONLINE_B2B = "50001112"
# CUSTOMER_ID_FINAL_BILLING_GRAND_GAADI_COD_B2B = "50001130"
# CUSTOMER_ID_FINAL_BILLING_GRAND_GAADI_ONLINE_B2B = "50001131"

# GRN_FOLDER_NAME = "OMNICOM-PRD"

"""

WIG Fleet cash on delivery: 50000391

WIG Fleet Cheque/Onine on delivery: 50000392

 

Postaplus cash on delivery: 50000666

Postaplus Cheque/Onine on delivery: 50000667

 

Sendex cash on delivery: 50000876

Sendex Cheque/Onine on delivery: 50000877



Standard Express Cash On Delivery: 50000872

Standard Express Credit Card Sales: 50000871
"""