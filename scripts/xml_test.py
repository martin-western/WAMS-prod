import requests
url="http://ECCPRD01:8001/sap/bc/srt/rfc/sap/zser_stock_price/300/zser_stock_price/zbin_stock_price"
#headers = {'content-type': 'application/soap+xml'}
headers = {'content-type': 'text/xml'}
body = """<n0:ZAPP_STOCK_PRICE xmlns:n0="urn:sap-com:document:sap:rfc:functions">
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
   <MATNR>Str 5</MATNR>
   <MAKTX>Str 6</MAKTX>
   <LGORT>Str</LGORT>
   <CHARG>Str 8</CHARG>
   <SPART>St</SPART>
   <MEINS>Str</MEINS>
   <ATP_QTY>123456789012.345</ATP_QTY>
   <TOT_QTY>123456789012.345</TOT_QTY>
   <CURRENCY>Str 1</CURRENCY>
   <IC_EA>Str 12</IC_EA>
   <OD_EA>Str 13</OD_EA>
   <EX_EA>Str 14</EX_EA>
   <RET_EA>Str 15</RET_EA>
   <WERKS>Str</WERKS>
  </item>
  <item>
   <MATNR>Str 17</MATNR>
   <MAKTX>Str 18</MAKTX>
   <LGORT>Str</LGORT>
   <CHARG>Str 20</CHARG>
   <SPART>St</SPART>
   <MEINS>Str</MEINS>
   <ATP_QTY>123456789012.345</ATP_QTY>
   <TOT_QTY>123456789012.345</TOT_QTY>
   <CURRENCY>Str 2</CURRENCY>
   <IC_EA>Str 24</IC_EA>
   <OD_EA>Str 25</OD_EA>
   <EX_EA>Str 26</EX_EA>
   <RET_EA>Str 27</RET_EA>
   <WERKS>Str</WERKS>
  </item>
 </T_DATA>
</n0:ZAPP_STOCK_PRICE>"""

response = requests.post(url,data=body,headers=headers)
print response.content