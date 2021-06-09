OMNYCOMM_IP = "http://qa.omnycomm.com:8028"
NETWORK_URL = "https://api-gateway.sandbox.ngenius-payments.com"
#NETWORK_URL = "https://api-gateway.ngenius-payments.com"
SPOTII_AUTH_IP = "https://auth.sandbox.spotii.me"
SPOTII_IP = "https://api.sandbox.spotii.me"
WIGME_IP = "https://qa.wigme.com"
TAP_IP = "https://api.tap.company/v2"


#******************************* SENDEX Courier Integration *****************************#

SENDEX_ADD_CONSIGNMENT_URL = "https://portal.sendex.me/webservice/CustomerBooking"
SENDEX_TRACK_CONSIGNMENT_STATUS_URL = "https://portal.sendex.me/webservice/GetTracking"
SENDEX_API_KEY = "818f251c7eb1c890478f1aca6c171189"

#Mapping from sendex status codes to the current_status_admin codes we maintain ******
SENDEX_CODE_TO_STATUS = {
    "TR" : "dispatched",
    "DD" : "delivered",
    "IN" : "dispatched",
    "RTO" : "returned",
    "RSH" : "returned",
    "SCD" : "dispatched",
    "NR" : "dispatched",
    "CSD" : "dispatched",
    "MSO" : "dispatched",
    "IDN" : "dispatched",       
    "UND" : "dispatched",
    "RTO" : "returned",
    "WLO" : "dispatched",
    "VOM" : "dispatched",
    "CST" : "dispatched",
    "POD" : "delivered",
    "NTN" : "dispatched",       
    "LOC" : "dispatched",
    "OFD" : "dispatched",
    "WNO" : "dispatched",
    "LC" : "dispatched",
    "SRH" : "dispatched",
    "MOS" : "dispatched",
    "SHE" : "dispatched",
    "CNR" : "dispatched",
    "OCL" : "returned",
    "CC" : "dispatched",
    "TD" : "dispatched",
    "CN" : "dispatched",
    "SD" : "dispatched",
    "RF" : "dispatched",
    "7" : "dispatched",
    "WA" : "dispatched" 
}

SENDEX_PHRASE_TO_STATUS = {
    "in transit" : "dispatched",
    "delivered" : "delivered",
    "inscan" : "dispatched",
    "return delivery" : "returned",
    "return to hub" : "returned",
    "scheduled" : "dispatched",
    "no response" : "dispatched",
    "pkg with customer service" : "dispatched",
    "mobile switched off" : "dispatched",
    "id not available" : "dispatched",       
    "undelivered" : "dispatched",
    "return to origin" : "returned",
    "wrong location" : "dispatched",
    "voice mail" : "dispatched",
    "cust req nxt day" : "dispatched",
    "proof of delivery" : "delivered",
    "incomplete tel no" : "dispatched",       
    "location taken" : "dispatched",
    "out for delivery" : "dispatched",
    "wrong number" : "dispatched",
    "location changed" : "dispatched",
    "shipper requested to hold" : "dispatched",
    "mobile out of service" : "dispatched",
    "delivery scheduled on next day" : "dispatched",
    "cod not ready" : "dispatched",
    "order cancelled" : "returned",
    "consignee out of country" : "dispatched",
    "tommorrow delivery" : "dispatched",
    "consignee not available" : "dispatched",
    "scheduled for delivery" : "dispatched",
    "consginee refused" : "dispatched",
    "dispatched" : "dispatched",
    "wrong address" : "dispatched", 
    "request submitted" : "dispatched"      # doubtful
}

#********************************************************************************************
