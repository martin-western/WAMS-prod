from WAMSApp.models import *

import json
import pdfkit
import inflect
import sys

import logging
import os

logger = logging.getLogger(__name__)

def generate_pi(factory_code, invoice_details, product_list):
    try:
        logger.info("Why not!!")
        logger.info("ENV %s", str(os.getenv("DISPLAY")))
        factory_obj = Factory.objects.get(factory_code=factory_code)

        factory_name = factory_obj.name
        factory_address = factory_obj.address
        factory_number = ""
        try:
            factory_number = json.loads(factory_obj.phone_numbers)[0]
        except Exception as e:
            pass

        point_of_contact = factory_obj.contact_person_name
        contact_number = factory_obj.contact_person_mobile_no
        loading_port = factory_obj.loading_port
        discharge_port = invoice_details["discharge_port"]
        vessel_details = invoice_details["vessel_details"]
        vessel_final_destination = invoice_details["vessel_final_destination"]

        payment_terms = invoice_details["payment_terms"]
        inco_terms = invoice_details["inco_terms"]
        delivery_terms = invoice_details["delivery_terms"]
        shipment_lot_no = invoice_details["shipment_lot_no"]

        invoice_number = invoice_details["invoice_number"]
        invoice_date = invoice_details["invoice_date"]

        bank_name = factory_obj.bank_details.name
        account_number = factory_obj.bank_details.account_number
        ifsc_code = factory_obj.bank_details.ifsc_code
        swift_code = factory_obj.bank_details.swift_code
        branch_code = factory_obj.bank_details.branch_code
        bank_address = factory_obj.bank_details.address

        important_notes = invoice_details["important_notes"]

        brand_logo_url = Brand.objects.get(name="geepas").logo.image.url


        product_html_string = ""

        cnt = 0
        total_qty = 0
        total_price = 0
        for product in product_list:
            cnt += 1
            product_obj = Product.objects.get(uuid=product["uuid"])
            sourcing_product_obj = SourcingProduct.objects.get(product=product_obj)


            image_url = Config.objects.all()[0].product_404_image.image.url
            try:
                image_url = MainImages.objects.get(product=product_obj).main_images.all()[0].image.image.url
            except Exception as e:
                pass

            total_product_price = float(sourcing_product_obj.price)*int(product["quantity"])
            logger.info("Total Price: %s %s", str(total_product_price), str(type(total_product_price)))

            product_html_string += """

                <div class="product-table-body">
                    <div class="product-table-head-serial-container  center-element">
                      <p class="product-table-head-text">
                        """+str(cnt)+"""
                      </p>
                    </div>
                    <div class="product-table-products-container">
                      <div class="img-container">
                        <img src=" """+str(image_url)+""" " />
                      </div>
                      <div class="label-container">
                        <p>
                          Product Name:
                        </p>
                        <p>
                          Item Number:
                        </p>
                        <p>
                          Brand Name:
                        </p>
                      </div>
                      <div class="value-container">
                        <p class="list-value">
                          """+str(product_obj.product_name)+"""
                        </p>
                        <p class="list-value">
                          """+str(product_obj.base_product.seller_sku)+"""
                        </p>
                        <p class="list-value">
                          """+str(product_obj.base_product.brand)+"""
                        </p>
                      </div>
                    </div>
                    <div class="product-table-head-quantity-container center-element">
                      <p class="product-table-head-text">
                        """+str(product["quantity"])+"""
                      </p>
                    </div>
                    <div class="product-table-head-unit-container center-element">
                      <p class="product-table-head-text">
                        Sets
                      </p>
                    </div>
                    <div class="product-table-head-price-container center-element">
                      <p class="product-table-head-text">
                        """+str(sourcing_product_obj.price)+"""
                      </p>
                    </div>
                    <div class="product-table-head-amount-container center-element">
                      <p class="product-table-head-text">
                        """+str(total_product_price)+"""
                      </p>
                    </div>
                  </div>
            """

            total_qty += int(product["quantity"])
            total_price += round(sourcing_product_obj.price*int(product["quantity"]), 2)

        p = inflect.engine()
        total_in_words = p.number_to_words(total_price)

        product_total_html_string = """
              <div class="product-table-footer">
                <div class="label-container">
                  <p>
                    Amount Chargeable:
                  </p>
                  <p>
                    Total Quantity:
                  </p>
                  <p>
                    Total Price:
                  </p>

                </div>
                <div class="value-container">
                  <p class="list-value">
                    """+total_in_words.title()+""" Dirhams Only
                  </p>
                  <p class="list-value">
                    """+str(total_qty)+"""
                  </p>
                  <p class="list-value">
                    AED """+str(total_price)+"""
                  </p>
                </div>
              </div>"""


        html_string = """
            <!DOCTYPE html>
                <html lang="en">

                  <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <meta http-equiv="X-UA-Compatible" content="ie=edge">
                    <title>Pi page</title>
                    <link rel="stylesheet" href="https://use.fontawesome.com/releases/v5.6.3/css/all.css"
                      integrity="sha384-UHRtZLI+pbxtHCWp1t77Bi1L4ZtiqrqD80Kn4Z8NTSRyMA2Fd33n5dQ8lWUE00s/" crossorigin="anonymous">
                    <link href="https://fonts.googleapis.com/css2?family=Roboto:ital,wght@0,400;0,500;0,700;0,900;1,400;1,500;1,700;1,900&display=swap"
                      rel="stylesheet">

                    <style type="text/css">
                      /*body:before {
                        white-space: pre;
                        font-family: monospace;
                        content: "Errno::ENOENT: No such file or directory @ rb_sysopen - main.scss"; 
                      }*/

                      html {
                        -webkit-box-sizing: border-box;
                        -moz-box-sizing: border-box;
                        box-sizing: border-box;
                      }
                      *, *:before, *:after {
                        -webkit-box-sizing: inherit;
                        -moz-box-sizing: inherit;
                        box-sizing: inherit;
                      }



                      body {
                          margin: 0px;
                          font-family: 'Roboto', sans-serif;
                      }
                      p {
                          margin: 0px;
                      }
                      .center-element {
                          display: -webkit-box;;
                          /*justify-content: center;*/
                          /*align-items: center;*/
                      }
                      .pi-page-container {
                          min-height: 100vh;
                          /* background-color: grey; */
                          padding: 0px 28px;
                          max-width: 1280px; 
                          margin: 0 auto;
                      }

                      nav {
                          display: -webkit-box;
                          /*justify-content: space-between;*/
                          /*align-items: center;*/
                          position: relative;
                          text-align: center;
                          padding: 10px;
                          margin-bottom: 30px;
                      }

                      nav .nav-title-container {
                          width: 100%;
                          
                      }

                      .nav-title-container p {
                          font-weight: 700;
                          margin: 0px;
                          font-size: 1.6em;
                      }
                      nav .logo {
                          position: absolute;
                          top: 5px;
                      }
                      .logo img {
                          width:150px;
                          height: auto;
                      }


                      .details-cards-container {
                          display: -webkit-box;
                          /*justify-content: space-between;*/
                      }


                      .card-title {
                          font-weight: 500;
                          font-size: 1.1em;
                      }
                      .details-cards-left-container {
                          width: 49%;
                          padding:10px;
                          background-color: white;
                          min-height: 500px;
                      }
                      .details-cards-right-container {
                          width: 49%;
                          padding:10px;
                          background-color: white;
                          min-height: 500px;
                      }

                      .details-card {
                          border: 1px solid black;
                          border-radius: 5px;
                          margin-bottom: 20px;

                      }
                      .details-card-nav {
                          padding: 10px;
                          text-align: left;
                          border-bottom: 1px solid black;
                      }

                      .details-card-list-container {
                          /* list-style-type: square; */
                          padding: 10px;
                          margin: 0px;
                      }
                      .details-card-list {
                          display: -webkit-box;
                          margin-bottom: 5px;
                      }
                      .list-title {
                          width: 30%;
                      }
                      .list-value {
                          width: 90%;
                          font-weight: 500;
                          font-size: 1em;
                      }
                      .important-notes-container {
                      padding: 10px;
                      }

                      .product-table-container {
                          
                      }
                      .product-table {
                          border: 1px solid black;
                          border-radius: 5px;
                          margin-bottom: 20px;
                      }
                      .product-table-head {
                          border-bottom: 1px solid black;
                          display: -webkit-box;
                          
                      }
                      .product-table-head-text {
                          font-weight: 500;
                          font-size: 1em;
                      }

                      .product-table-head-serial-container {
                          width: 5%;
                          border-right: 1px solid black !important;
                          padding: 5px 5px;
                      }
                      .product-table-head-products-container {
                          width: 50%;
                          border-right: 1px solid black !important;
                          padding: 10px 10px;

                      }
                      .product-table-head-quantity-container {
                          width: 10%;
                          border-right: 1px solid black !important;
                          padding: 10px 10px;

                      }
                      .product-table-head-unit-container {
                          width: 10%;
                          border-right: 1px solid black !important;
                          padding: 10px 10px;

                      }
                      .product-table-head-price-container {
                          width: 10%;
                          border-right: 1px solid black !important;
                          padding: 10px 10px;

                      }
                      .product-table-head-amount-container {
                          width: 10%;
                          padding: 10px 10px;
                      }
                      .product-table-body{
                          display: -webkit-box;
                      }
                      .product-table-footer{
                          padding: 10px;
                          border-top: 1px solid black;
                          display: -webkit-box;
                      }
                      .product-table-footer .label-container {
                          width: 15%;
                      }
                      .product-table-footer .value-container {
                          width: 95%;
                      }
                      .product-table-products-container {
                          width: 50%;
                          border-right: 1px solid black !important;
                          padding: 10px 10px;
                          display: -webkit-box;
                          align-items: center;
                      }

                      .product-table-products-container .img-container  {
                          width: 30%;
                      }
                      .product-table-products-container .label-container  {
                          width: 30%;
                      }
                      .product-table-products-container .label-container p {
                          margin-bottom: 5px;
                      }
                      .product-table-products-container .value-container  {
                          width: 40%;
                      }
                      .product-table-products-container .value-container .list-value {
                          margin-bottom: 5px;
                      }
                      .product-table-products-container .img-container img {
                          width: 100px;
                          height: auto;
                      }


                      .signature-container {
                          border: 1px solid black;
                          border-radius: 5px;
                          margin-bottom: 20px;
                          display: -webkit-box;
                      }
                      .signature-left-container{
                          width: 50%;
                          border-right: 1px solid black;
                          min-height: 200px;
                      }
                      .signature-left-container .signature-title {
                          font-weight: 500;
                          font-size: 1em;
                      }


                      .signature-right-container {
                          width: 50%;
                          min-height: 150px;

                      }
                      .signature-right-container .signature-title {
                          font-weight: 500;
                          font-size: 1em;
                      }
                      .signature-title-container{
                          border-bottom: 1px solid black;
                          padding: 10px;
                      }



                      .product-specification-nav {
                          display: -webkit-box;
                          background-color: #FFC403;
                          border-radius: 5px;
                          margin-bottom: 20px;
                      }
                      .product-details{
                          padding: 20px 20px;
                          width: 55%;
                      }
                      .specification{
                          padding: 20px 0px;

                          width: 20%;
                      }
                      .other-details {
                          padding: 20px 0px;

                          width: 25%;
                      }

                      .product-specification-content{
                          border: 1px solid black;
                          border-radius: 5px;
                          padding: 20px 0px;
                          display: -webkit-box;
                          align-items: center;
                          margin-bottom: 20px;
                      }

                      .product-image-container {
                          padding-left: 20px;
                          width: 10%;
                      }
                      .product-image-container img {
                          width: 100px;
                          height: auto;
                      }
                      .product-specification-container-1 {
                          width: 45%;
                          padding-left: 20px;
                      }
                      .product-specification-container-2 {
                          width: 20%;
                          
                      }
                      .product-specification-container-3 {
                          width: 25%;
                          
                      }

                      .product-content-box-1 {
                          display: -webkit-box;
                          width: 100%;
                          margin-bottom: 5px;
                      }
                      .product-content-box-1 .left-box {
                      width: 30%;
                      }
                      .product-content-box-1 .right-box {
                          width: 70%;
                      }
                      .right-box-text {
                          font-weight: 500;
                          font-size: 1em;
                      }


                      .product-content-box-2 {
                          display: -webkit-box;
                          width: 100%;
                          margin-bottom: 5px;

                      }
                      .product-content-box-2 .left-box {
                      width: 50%;
                      }
                      .product-content-box-2 .right-box {
                          width: 50%;
                      }

                      .product-content-box-3 {
                          display: -webkit-box;
                          width: 100%;
                          margin-bottom: 5px;

                      }
                      .product-content-box-2 .left-box {
                      width: 50%;
                      }
                      .product-content-box-2 .right-box {
                          width: 50%;
                      }



                      .instructions-container {
                          border: 1px solid black;
                          border-radius: 5px;
                          margin-bottom: 20px;
                      }
                      .important-notes-lists {
                          margin: 0px;
                      }

                      .important-notes-lists li{
                          margin-bottom: 5px;
                      }
                    </style>

                  </head>

                  <body>
                    <div class="pi-page-container">
                      <nav>
                        <div class="logo">
                          <img src=" """ +brand_logo_url+ """ " />
                        </div>
                        <div class="nav-title-container">
                          <p>ORDER CONFIRMATION SHEET</p>
                        </div>
                      </nav>
                      <div class="details-cards-container">
                        <div class="details-cards-left-container">
                          <div class="details-card">
                            <div class="details-card-nav">
                              <p class="card-title">"""+factory_name+"""</p>
                            </div>
                            <div class="details-card-body">
                              <ul class="details-card-list-container">
                                <li class="details-card-list">
                                  <p class="list-title">Address:</p>
                                  <p class="list-value">"""+factory_address+"""</p>
                                </li>
                                <li class="details-card-list">
                                  <p class="list-title">Factory Number:</p>
                                  <p class="list-value">"""+factory_number+"""</p>
                                </li>
                                <li class="details-card-list">
                                  <p class="list-title">Point of Contact:</p>
                                  <p class="list-value">"""+point_of_contact+"""</p>
                                </li>
                                <li class="details-card-list">
                                  <p class="list-title">Contact’s number:</p>
                                  <p class="list-value">"""+contact_number+"""</p>
                                </li>
                                <li class="details-card-list">
                                  <p class="list-title">Port of Loading:</p>
                                  <p class="list-value">"""+loading_port+"""</p>
                                </li>
                                <li class="details-card-list">
                                  <p class="list-title">Port of Discharge:</p>
                                  <p class="list-value">"""+discharge_port+"""</p>
                                </li>
                                <li class="details-card-list">
                                  <p class="list-title">Vessel Details:</p>
                                  <p class="list-value">"""+vessel_details+"""</p>
                                </li>
                                <li class="details-card-list">
                                  <p class="list-title">Vessel Final Destination:</p>
                                  <p class="list-value">"""+vessel_final_destination+"""</p>
                                </li>
                              </ul>
                            </div>
                          </div>
                          <div class="details-card">
                            <div class="details-card-nav">
                              <p class="card-title">Shipment Details</p>
                            </div>
                            <div class="details-card-body">
                              <ul class="details-card-list-container">
                                <li class="details-card-list">
                                  <p class="list-title">Payment Terms:</p>
                                  <p class="list-value">"""+payment_terms+"""</p>
                                </li>
                                <li class="details-card-list">
                                  <p class="list-title">Inco Terms:</p>
                                  <p class="list-value">"""+inco_terms+"""</p>
                                </li>
                                <li class="details-card-list">
                                  <p class="list-title">Delivery Terms:</p>
                                  <p class="list-value">"""+delivery_terms+"""</p>
                                </li>
                                <li class="details-card-list">
                                  <p class="list-title">Shipment Lot No:</p>
                                  <p class="list-value">"""+shipment_lot_no+"""</p>
                                </li>
                              </ul>
                            </div>
                          </div>
                        </div>
                        <div class="details-cards-right-container">
                          <div class="details-card">
                            <div class="details-card-nav">
                              <p class="card-title">Invoice Details</p>
                            </div>
                            <div class="details-card-body">
                              <ul class="details-card-list-container">
                                <li class="details-card-list">
                                  <p class="list-title">Invoice Number:</p>
                                  <p class="list-value">"""+invoice_number+"""</p>
                                </li>
                                <li class="details-card-list">
                                  <p class="list-title">Invoice Date:</p>
                                  <p class="list-value">"""+invoice_date+"""</p>
                                </li>
                              </ul>
                            </div>
                          </div>
                          <div class="details-card">
                            <div class="details-card-nav">
                              <p class="card-title">Bank Details</p>
                            </div>
                            <div class="details-card-body">
                              <ul class="details-card-list-container">
                                <li class="details-card-list">
                                  <p class="list-title">Bank Name:</p>
                                  <p class="list-value">"""+bank_name+"""</p>
                                </li>
                                <li class="details-card-list">
                                  <p class="list-title">A/c Number:</p>
                                  <p class="list-value">"""+account_number+"""</p>
                                </li>
                                <li class="details-card-list">
                                  <p class="list-title">IFSC Code:</p>
                                  <p class="list-value">"""+ifsc_code+"""</p>
                                </li>
                                <li class="details-card-list">
                                  <p class="list-title">SWIFT Code:</p>
                                  <p class="list-value">"""+swift_code+"""</p>
                                </li>
                                <li class="details-card-list">
                                  <p class="list-title">Branch Code:</p>
                                  <p class="list-value">"""+branch_code+"""</p>
                                </li>
                                <li class="details-card-list">
                                  <p class="list-title">Address:</p>
                                  <p class="list-value">"""+bank_address+"""</p>
                                </li>
                              </ul>
                            </div>
                          </div>
                          <div class="details-card">
                            <div class="details-card-nav">
                              <p class="card-title">Important Notes</p>
                            </div>
                            <div class="details-card-body important-notes-container">
                              """+important_notes+"""
                            </div>
                          </div>
                        </div>
                      </div>
                      <div class="product-table-container">



                        <div class="product-table">

                          <div class="product-table-head">
                            <div class="product-table-head-serial-container center-element">
                              <p class="product-table-head-text">
                                Sr.No.
                              </p>
                            </div>
                            <div class="product-table-head-products-container">
                              <p class="product-table-head-text">
                                Products
                              </p>
                            </div>
                            <div class="product-table-head-quantity-container center-element">
                              <p class="product-table-head-text">
                                Quantity
                              </p>
                            </div>
                            <div class="product-table-head-unit-container center-element">
                              <p class="product-table-head-text">
                                Unit
                              </p>
                            </div>
                            <div class="product-table-head-price-container center-element">
                              <p class="product-table-head-text">
                                Price (AED)
                              </p>
                            </div>
                            <div class="product-table-head-amount-container center-element">
                              <p class="product-table-head-text">
                                Amount
                              </p>
                            </div>
                          </div>

                          """+product_html_string+"""
                          """+product_total_html_string+"""
                        </div>
                      </div>
                      <div class="signature-container">
                        <div class="signature-left-container">
                          <div class="signature-title-container">
                            <p class="signature-title">Signature</p>
                          </div>
                          <div class="signature-content">

                          </div>
                        </div>
                        <div class="signature-right-container">
                          <div class="signature-title-container">
                            <p class="signature-title">Consignee Signature</p>
                          </div>
                        </div>
                      </div>

                      <div class="product-specification-container">

                        <div class="instructions-container">
                          <div class="details-card-nav">
                            <p class="card-title">Important Notes</p>
                          </div>
                          <div class="details-card-body important-notes-container">
                            <p class="card-title">Packaging Standard:</p>
                            <br>
                            <ul class="important-notes-lists">
                              <li>
                                Export carton must be 5 layer carton with minimum board GSM of 1300 as standard (3 layer will not be
                                accepted). Kraft Liner preferred.
                              </li>
                              <li>
                                Carton must be free of any humidity and should hold all products inside
                                it without damage.
                              </li>
                              <li>
                                Condition 3
                              </li>
                              <li>
                                Condition 4
                              </li>
                            </ul>

                          </div>
                        </div>
                      </div>
                    </div>

                  </body>

                </html>"""

        filepath = "files/invoices/"+str(invoice_number)+".pdf"
        pdfkit.from_string(html_string, filepath)
        return filepath
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("generate_pi: %s at %s", e, str(exc_tb.tb_lineno))
    