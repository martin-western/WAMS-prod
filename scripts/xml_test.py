import requests
url="http://94.56.89.114:8001/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"
#headers = {'content-type': 'application/soap+xml'}
#headers = {'content-type': 'text/xml'}
headers = {'content-type':'text/xml','accept':'application/json','cache-control':'no-cache'}

credentials = ("MOBSERVICE", "~lDT8+QklV=(")

body = """<n0:ZAPP_STOCK_PRICE xmlns:n0="urn:sap-com:document:sap:rfc:functions">
 <IM_MATNR>
  <item>
   <MATNR>OME2544</MATNR>
  </item>
 </IM_MATNR>
 <IM_VKORG>
  <item>
   <VKORG>1100</VKORG>
  </item>
 </IM_VKORG>
 <T_DATA>
  <item>
   <MATNR></MATNR>
   <MAKTX></MAKTX>
   <LGORT></LGORT>
   <CHARG></CHARG>
   <SPART></SPART>
   <MEINS></MEINS>
   <ATP_QTY></ATP_QTY>
   <TOT_QTY></TOT_QTY>
   <CURRENCY></CURRENCY>
   <IC_EA></IC_EA>
   <OD_EA></OD_EA>
   <EX_EA></EX_EA>
   <RET_EA></RET_EA>
   <WERKS></WERKS>
  </item>
 </T_DATA>
</n0:ZAPP_STOCK_PRICE>"""

body = """<soapenv:Envelope xmlns:urn="urn:sap-com:document:sap:rfc:functions" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
<soapenv:Header />
<soapenv:Body>
<urn:ZAPP_STOCK_PRICE>

 <IM_MATNR>
  <item>
   <MATNR>OMSB2135</MATNR>
  </item>
 </IM_MATNR>
 <IM_VKORG>
  <item>
   <VKORG>1100</VKORG>
  </item>
 </IM_VKORG>
 <T_DATA>
  <item>
   <MATNR></MATNR>
   <MAKTX></MAKTX>
   <LGORT></LGORT>
   <CHARG></CHARG>
   <SPART></SPART>
   <MEINS></MEINS>
   <ATP_QTY></ATP_QTY>
   <TOT_QTY></TOT_QTY>
   <CURRENCY></CURRENCY>
   <IC_EA></IC_EA>
   <OD_EA></OD_EA>
   <EX_EA></EX_EA>
   <RET_EA></RET_EA>
   <WERKS></WERKS>
  </item>
 </T_DATA>

</urn:ZAPP_STOCK_PRICE>
</soapenv:Body>
</soapenv:Envelope>"""

response = requests.post(url, auth=credentials, data=body, headers=headers)

content = response.content

import xml.dom.minidom
dom = xml.dom.minidom.parseString(content)
pretty_xml_as_string = dom.toprettyxml()
print content