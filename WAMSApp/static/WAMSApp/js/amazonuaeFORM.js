
    $('.tabs').tabs();
    $('.chips').chips();
    $('select').formSelect();
    $('.modal').modal();
    $('body').css('background-color', '#ebebeb');
    $('.sidenav').sidenav({ edge: 'left' });

    $('document').ready(function(){
        console.log("chala");
        $('.dropdown-trigger').dropdown();
    });


    $("#open-it-btn").click(function () {
        if ($(this).attr("visible") == "no") {
            $(this).attr("visible", "yes");
            $("#collapse-div").attr("class", "col s4 center");
            $("#sidebar2").show(600);
            console.log($(this));
            // $(".main-div").css('margin-right' , '0px');
        }
        else {
            $(this).attr("visible", "no");
            $("#sidebar2").hide();
            $("#collapse-div").attr("class", "col s8 center");
            $(".main-div").css('margin-right' , '70px');
        }
    })

    $('.button-collapse').sidenav({
      menuWidth: 300, // Default is 240
      edge: 'right', // Choose the horizontal origin
      closeOnClick: true,
      isFixed: true,
      // Closes side-nav on <a> clicks, useful for Angular/Meteor
    }
    );



    var global_verification_status = false;
    var global_delete_image_pk = null;

    //Page reload prevent logic
    let savecounter = false;
    $('#save-btn').click(() => {
        savecounter = false;
    })

    $('input').click(function () {
        savecounter = true;
    })

    function preventDefault() {
        if (savecounter) {
            alert('Please save the details before refreshing!');
        }
        else {
            window.close();
        }
    }

    $('#close-btn').click(function () {
        preventDefault();
    })

    $("#download-product-btn").click(function () {

        var export_format = $("#export-format").val();

        $.ajax({
            url: "/download-product/",
            type: "POST",
            headers: {
                'X-CSRFToken': getCsrfToken()
            },
            data: {
                product_pk: window.location.pathname.split("/")[3],
                export_format: export_format
            },
            success: function (response) {
                console.log("Success!", response);
                $("#download-export-list-modal").modal("close");
                var file_path = response["file_path"]
                window.open(file_path);
            },
            error: function (xhr, textstatus, errorthrown) {
                console.log("Please report this error: " + errorthrown + xhr.status + xhr.responseText);
            }
        });

    });

    window.addEventListener('beforeunload', function (e) {
        if (savecounter) {
            e.preventDefault();
            e.returnValue = '';
        }
        else
            window.close();
    });

    $("#pending-icon").click(function () {
        if (global_verification_status) {
            call_verify_api(0);
        }
    });

    $("#verified-icon").click(function () {
        if (!global_verification_status) {
            call_verify_api(1);
        }
    });

    function fetch_details_amazon_uae()     
      {
        $.ajax({
          url: "/fetch-channel-product-amazon-uae/",
          type: "POST",
          headers: {
            'X-CSRFToken': getCsrfToken()
          },
          data: {
            product_pk: window.location.pathname.split("/")[3]
          },
          success: function (response) {
            console.log("Success!", response);
            if(response["status"]==200)
            {
              global_details_amazon_uae = response["amazon_uae_product_json"];
              // render_amazon_uk();
            }
            else
            {
              M.toast({ html: "Internal Server" });
            }
          },
          error: function (xhr, textstatus, errorthrown) {
            console.log("Please report this error: " + errorthrown + xhr.status + xhr.responseText);
          }
        });
      }
    fetch_details_amazon_uae();

    function call_verify_api(verify) {
        var fd = new FormData()
        fd.append("product_pk", window.location.pathname.split("/")[3]);
        fd.append("verify", verify);

        $.ajax({
            url: "/verify-product/",
            type: "POST",
            headers: {
                'X-CSRFToken': getCsrfToken()
            },
            processData: false,
            contentType: false,
            data: fd,
            success: function (response) {
                console.log("Success!", response);
                if (response["status"] == 200) {
                    if (verify == 1) {
                        set_verify(true);
                        global_verification_status = true;
                        M.toast({ html: "Product status changed to verified" });
                    }
                    else {
                        set_verify(false);
                        global_verification_status = false;
                        M.toast({ html: "Product status changed to pending" });
                    }
                }
                else if (response["status"] == 403) {
                    M.toast({ html: "You do not have access to update the status!" });
                }
                else {
                    M.toast({ html: "Error updating the status!" });
                }
            },
            error: function (xhr, textstatus, errorthrown) {
                console.log("Please report this error: " + errorthrown + xhr.status + xhr.responseText);
            }
        });
    }

    $(document).ready(function () {
        $('.tabs').tabs();
    });

    $('#barcode-string').characterCounter();

    $("#download-image-btn").click(function () {

        $("#download-image-btn").attr("disabled", "disabled");
        var high_def_url = $($(".preview-img")[0]).attr("high_def_url");
        var image_links = [];
        image_links.push({
            "key": "high_def_url",
            "url": high_def_url
        })

        $.ajax({
            url: "/download-images-s3/",
            type: "POST",
            headers: {
                'X-CSRFToken': getCsrfToken()
            },
            data: {
                links: JSON.stringify(image_links)
            },
            success: function (response) {
                console.log("Success! ", response);
                $("#download-image-btn").removeAttr("disabled");
                if (response["status"] == 200) {
                    var local_link = response["local_links"][0]["url"];

                    var a = document.createElement('a');
                    a.href = local_link;
                    var filename = high_def_url.split("/")[high_def_url.split("/").length - 1];
                    a.download = filename;
                    a.click();
                }
            },
            error: function (xhr, textstatus, errorthrown) {
                console.log("Please report this error: " + errorthrown + xhr.status + xhr.responseText);
                $("#download-image-btn").removeAttr("disabled");
            }
        });
    });

    var pfl_feature_cnt = 2;

    $("#add-feature-btn").click(function () {
        var html_string = `<div class="feature-div">
                         <div class="input-field col s9">
                           <input class="feature-text" id="pfl-feature-`+ pfl_feature_cnt + `" type="text" >
                           <label for="pfl-feature-`+ pfl_feature_cnt + `">Feature</label>
                         </div>

                        <div class="input-field col s1">
                          <a href="#!" class="delete-feature-btn btn-floating red" style="transform: scale(0.7);box-shadow: none;"><i class="material-icons">remove</i></a>
                        </div>
                      </div>`;
        $("#feature-summary-editor-div").append(html_string);
        pfl_feature_cnt++;
    });


    $(document).on('click', ".delete-feature-btn", function () {
        $(this).parent().parent().remove();
    });

    // $('.pflspecific').hide(); 

    $("#heading-title").html("PRODUCT FORM");

    window.editor = []

    DecoupledEditor
        .create(document.querySelector('.document-editor__editable'), {
            cloudServices: {
            }
        })
        .then(editor => {
            const toolbarContainer = document.querySelector('.document-editor__toolbar');

            toolbarContainer.appendChild(editor.ui.view.toolbar.element);
            //editor.isReadOnly = !response['edit_access'];
            window.editor.push(editor);
        })
        .catch(err => {
            console.error(err);
        });

    DecoupledEditor
        .create(document.querySelector('.clone2_editable'), {
            cloudServices: {
            }
        })
        .then(editor => {
            const toolbarContainer = document.querySelector('.clone2_toolbar');

            toolbarContainer.appendChild(editor.ui.view.toolbar.element);
            //editor.isReadOnly = !response['edit_access'];
            window.editor.push(editor);
        })
        .catch(err => {
            console.error(err);
        });

    DecoupledEditor
        .create(document.querySelector('.clone3_editable'), {
            cloudServices: {
            }
        })
        .then(editor => {
            const toolbarContainer = document.querySelector('.clone3_toolbar');

            toolbarContainer.appendChild(editor.ui.view.toolbar.element);
            //editor.isReadOnly = !response['edit_access'];
            window.editor.push(editor);
        })
        .catch(err => {
            console.error(err);
        });




    DecoupledEditor
        .create(document.querySelector('.clone4_editable'), {
            cloudServices: {
            }
        })
        .then(editor => {
            const toolbarContainer = document.querySelector('.clone4_toolbar');

            toolbarContainer.appendChild(editor.ui.view.toolbar.element);
            //editor.isReadOnly = !response['edit_access'];
            window.editor.push(editor);
        })
        .catch(err => {
            console.error(err);
        });



    function getCsrfToken() {
        var CSRF_TOKEN = $('input[name="csrfmiddlewaretoken"]').val();
        return CSRF_TOKEN;
    }

    var global_images = {};
    var global_image_key = "all_images";

    function fetch_constant_values() {
        $.ajax({
            url: "/fetch-constant-values/",
            type: "POST",
            headers: {
                'X-CSRFToken': getCsrfToken()
            },
            data: {},
            success: function (response) {
                console.log("Success!", response);
                if (response["status"] == 200) {
                    var autocomplete_data = {}
                    var material_list = response["material_list"];
                    for (var i = 0; i < material_list.length; i++) {
                        autocomplete_data[material_list[i]["name"]] = null;
                    }
                    $('#material-type').autocomplete({
                        data: autocomplete_data
                    });

                    autocomplete_data = {};
                    var ebay_category_list = response["ebay_category_list"];
                    for (var i = 0; i < ebay_category_list.length; i++) {
                        autocomplete_data[ebay_category_list[i]["name"] + "|" + ebay_category_list[i]["category_id"]] = null;
                    }
                    $('#category').autocomplete({
                        data: autocomplete_data,
                        onAutocomplete: function (val) {
                            var category_id = val.split("|")
                            category_id = category_id[category_id.length - 1];
                            $("#category").val(category_id);
                        }
                    });


                    autocomplete_data = {};
                    var brand_list = response["brand_list"];
                    for (var i = 0; i < brand_list.length; i++) {
                        autocomplete_data[brand_list[i]["name"]] = null;
                    }
                    $('#brand-name').autocomplete({
                        data: autocomplete_data
                    });


                    var product_id_type_list = response["product_id_type_list"];
                    var html_string = `<option value="" selected>Product ID Type</option>`;
                    for (var i = 0; i < product_id_type_list.length; i++) {
                        html_string += `<option value="` + product_id_type_list[i]["name"] + `">` + product_id_type_list[i]["name"] + `</option>`
                    }




                    $("#product-id-type").html(html_string);
                    $('select').formSelect();
                }
                else {
                    //M.toast({html:"Duplicate product detected!"});
                }
                //$("#save-btn").removeAttr("disabled");
            },
            error: function (xhr, textstatus, errorthrown) {
                console.log("Please report this error: " + errorthrown + xhr.status + xhr.responseText);
            }
        });
    }

    fetch_constant_values();


    function fetch_product_images_details() {
        $.ajax({
            url: "/fetch-product-details/",
            type: "POST",
            headers: {
                'X-CSRFToken': getCsrfToken()
            },
            data: {
                pk: window.location.pathname.split("/")[3]
            },
            success: function (response) {
                console.log("Success!", response);

                if (response["status"] == 200) {
                    $('.material-placeholder').remove();
                    $('.main-image').append(`<img class = "preview-img materialboxed" src='` + response["repr_image_url"] + `' high_def_url="` + response["repr_high_def_url"] + `">`)
                    $('.materialboxed').materialbox();

                    global_images = response["images"];

                    $("#all-images-option").html("All Images (" + global_images["all_images"].length + ")");
                    $("#main-images-option").html("Main Images (" + global_images["main_images"].length + ")");
                    $("#sub-images-option").html("Sub Images (" + global_images["sub_images"].length + ")");
                    $("#pfl-images-option").html("PFL Images (" + global_images["pfl_images"].length + ")");
                    $("#pfl-generated-images-option").html("PFL Generated Images (" + global_images["pfl_generated_images"].length + ")");
                    $("#white-background-images-option").html("White Background Images (" + global_images["white_background_images"].length + ")");
                    $("#lifestyle-images-option").html("Lifestyle Images (" + global_images["lifestyle_images"].length + ")");
                    $("#certificate-images-option").html("Certificate Images (" + global_images["certificate_images"].length + ")");
                    $("#giftbox-images-option").html("Giftbox Images (" + global_images["giftbox_images"].length + ")");
                    $("#diecut-images-option").html("Diecut Images (" + global_images["diecut_images"].length + ")");
                    $("#aplus-content-images-option").html("A+ Content Images (" + global_images["aplus_content_images"].length + ")");
                    $("#ads-images-option").html("Ads Images (" + global_images["ads_images"].length + ")");
                    $("#unedited-images-option").html("Unedited Images (" + global_images["unedited_images"].length + ")");

                    update_grid_images(global_image_key);

                    $('#brand-image-img').attr("src", response["brand_logo"]);
                    if (global_images["main_images"].length > 0) {
                        $('#pfl-product-image-preview-img').attr("src", global_images["main_images"][0]["main-url"]);
                    }
                    $('#barcode-image-preview-img').attr("src", response["barcode_image_url"]);

                    M.updateTextFields();
                    $('select').formSelect();
                }
                else {
                    M.toast({ html: "Error fetching images information" });
                }
            },
            error: function (xhr, textstatus, errorthrown) {
                console.log("Please report this error: " + errorthrown + xhr.status + xhr.responseText);
            }
        });
    }


    $("#upload-image-btn").click(function () {

        $("#upload-image-btn").attr("disabled", "disabled");
        $("#upload-preloader").show();

        product_pk = window.location.pathname.split("/")[3];

        var fd = new FormData();

        fd.append("product_pk", product_pk);
        var product_image_input = document.getElementById("product-image-input");

        fd.append('image_count', product_image_input.files.length);
        for (var i = 0; i < product_image_input.files.length; i++) {
            fd.append('image_' + i, product_image_input.files[i]);
        }


        fd.append('image_category', global_image_key);

        $.ajax({
            url: "/upload-product-image/",
            type: "POST",
            headers: {
                'X-CSRFToken': getCsrfToken()
            },
            processData: false,
            contentType: false,
            data: fd,
            success: function (response) {
                console.log("Success!", response);
                $("#upload-preloader").hide();
                $("#upload-image-btn").removeAttr("disabled");

                if (response["status"] == 200) {
                    $("#upload-image-modal").modal("close");
                    M.toast({ html: "Successfully uploaded images!" });
                    fetch_product_images_details();
                }
                else if (response["status"] == 403) {
                    M.toast({ html: "You do not have permission to upload images!" });
                }
                else {
                    M.toast({ html: "Error uploading images!" });
                }
            },
            error: function (xhr, textstatus, errorthrown) {
                console.log("Please report this error: " + errorthrown + xhr.status + xhr.responseText);
                $("#upload-preloader").hide();
            }
        });
    })

    function set_verify(verified) {
        if (verified == true) {
            $("#pending-icon").css("background-color", "#f7f7f7");
            $("#pending-icon").css("color", "gray");
            $("#verified-icon").css("background-color", "#009051");
            $("#verified-icon").css("color", "white");
        }
        else {
            $("#verified-icon").css("background-color", "#f7f7f7");
            $("#verified-icon").css("color", "gray");
            $("#pending-icon").css("background-color", "orange");
            $("#pending-icon").css("color", "white");
        }
    }

    function fetch_product_details() {
        $.ajax({
            url: "/fetch-product-details/",
            type: "POST",
            headers: {
                'X-CSRFToken': getCsrfToken()
            },
            data: {
                pk: window.location.pathname.split("/")[3]
            },
            success: function (response) {
                console.log("Success!", response);

                global_verification_status = response["verified"];

                if (response["verified"] == true) {
                    set_verify(true);
                }
                else {
                    set_verify(false);
                }

                $("#pfl-product-name").val(response["pfl_product_name"])
                var pfl_product_features = response["pfl_product_features"]
                $('.material-placeholder').remove();
                $('.main-image').append(`<img class = "preview-img materialboxed" src='` + response["repr_image_url"] + `' high_def_url="` + response["repr_high_def_url"] + `">`)
                $('.materialboxed').materialbox();

                for (var i = 0; i < pfl_product_features.length; i++) {
                    $("#pfl-feature-" + (i + 1)).val(pfl_product_features[i]);
                    if ((i + 1) != pfl_product_features.length) {
                        $("#add-feature-btn").click();
                    }
                }

                $("#product-name-amazon-uk").val(response["product_name_amazon_uk"]);
                $("#product-name-amazon-uae").val(response["product_name_amazon_uae"]);
                $("#product-name-sap").val(response["product_name_sap"]);
                $("#product-name-ebay").val(response["product_name_ebay"]);
                $("#product-name-noon").val(response["product_name_noon"]);
                $("#category").val(response["category"]);
                $("#subtitle").val(response["subtitle"]);
                $("#brand-name").val(response["brand"]);
                $("#manufacturer").val(response["manufacturer"]);
                $("#product-id").val(response["product_id"]);
                $("#product-id-type").val(response["product_id_type"]);
                $("#seller-sku").val(response["seller_sku"]);
                $("#manufacturer-part-number").val(response["manufacturer_part_number"]);
                $("#barcode-string").val(response["barcode_string"]);
                $("#noon-product-type").val(response["noon_product_type"]);
                $("#noon-product-subtype").val(response["noon_product_subtype"]);
                $("#noon-model-name").val(response["noon_model_name"]);
                $("#noon-model-number").val(response["noon_model_number"]);

                $("#condition-type").val(response["condition_type"]);
                $("#feed-product-type").val(response["feed_product_type"]);
                $("#update-delete").val(response["update_delete"]);
                $("#recommended-browse-nodes").val(response["recommended_browse_nodes"]);


                window.editor[0].setData(response["product_description_amazon_uk"]);
                window.editor[1].setData(response["product_description_amazon_uae"]);
                window.editor[2].setData(response["product_description_ebay"]);
                window.editor[3].setData(response["product_description_noon"]);


                var product_attribute_list_amazon_uk = response["product_attribute_list_amazon_uk"];
                if (product_attribute_list_amazon_uk.length > 0) {
                    $("#product-attribute-amazon-uk-1").val(product_attribute_list_amazon_uk[0]);
                }
                for (var i = 1; i < product_attribute_list_amazon_uk.length; i++) {
                    $("#add-product-attribute-amazon-uk-btn").click();
                    $("#product-attribute-amazon-uk-" + (i + 1)).val(product_attribute_list_amazon_uk[i]);
                }

                var product_attribute_list_amazon_uae = response["product_attribute_list_amazon_uae"];
                if (product_attribute_list_amazon_uae.length > 0) {
                    $("#product-attribute-amazon-uae-1").val(product_attribute_list_amazon_uae[0]);
                }
                for (var i = 1; i < product_attribute_list_amazon_uae.length; i++) {
                    $("#add-product-attribute-amazon-uae-btn").click();
                    $("#product-attribute-amazon-uae-" + (i + 1)).val(product_attribute_list_amazon_uae[i]);
                }

                var product_attribute_list_ebay = response["product_attribute_list_ebay"];
                if (product_attribute_list_ebay.length > 0) {
                    $("#product-attribute-ebay-1").val(product_attribute_list_ebay[0]);
                }
                for (var i = 1; i < product_attribute_list_ebay.length; i++) {
                    $("#add-product-attribute-ebay-btn").click();
                    $("#product-attribute-ebay-" + (i + 1)).val(product_attribute_list_ebay[i]);
                }

                var product_attribute_list_noon = response["product_attribute_list_noon"];
                if (product_attribute_list_noon.length > 0) {
                    $("#product-attribute-noon-1").val(product_attribute_list_noon[0]);
                }
                for (var i = 1; i < product_attribute_list_noon.length; i++) {
                    $("#add-product-attribute-noon-btn").click();
                    $("#product-attribute-noon-" + (i + 1)).val(product_attribute_list_noon[i]);
                }

                $("#search-terms").val(response["search_terms"]);
                $("#color-map").val(response["color_map"]);
                $("#color").val(response["color"]);
                $("#enclosure-material").val(response["enclosure_material"]);
                $("#cover-material-type").val(response["cover_material_type"]);

                var special_features = response["special_features"];
                if (special_features.length > 0) {
                    $("#special-feature-1").val(special_features[0]);
                }
                for (var i = 1; i < special_features.length; i++) {
                    $("#add-special-feature-btn").click();
                    $("#special-feature-" + (i + 1)).val(special_features[i]);
                }

                $("#special-feature").val(response["special_features"]);
                $("#package-length").val(response["package_length"]);
                $("#package-length-metric").val(response["package_length_metric"]);
                $("#package-width").val(response["package_width"]);
                $("#package-width-metric").val(response["package_width_metric"]);
                $("#package-height").val(response["package_height"]);
                $("#package-height-metric").val(response["package_height_metric"]);
                $("#package-weight").val(response["package_weight"]);
                $("#package-weight-metric").val(response["package_weight_metric"]);
                $("#shipping-weight").val(response["shipping_weight"]);
                $("#shipping-weight-metric").val(response["shipping_weight_metric"]);
                $("#item-display-weight").val(response["item_display_weight"]);
                $("#item-display-weight-metric").val(response["item_display_weight_metric"]);
                $("#item-display-volume").val(response["item_display_volume"]);
                $("#item-display-volume-metric").val(response["item_display_volume_metric"]);
                $("#item-display-length").val(response["item_display_length"]);
                $("#item-display-length-metric").val(response["item_display_length_metric"]);
                $("#item-weight").val(response["item_weight"]);
                $("#item-weight-metric").val(response["item_weight_metric"]);
                $("#item-length").val(response["item_length"]);
                $("#item-length-metric").val(response["item_length_metric"]);
                $("#item-width").val(response["item_width"]);
                $("#item-width-metric").val(response["item_width_metric"]);
                $("#item-height").val(response["item_height"]);
                $("#item-height-metric").val(response["item_height_metric"]);
                $("#item-display-width").val(response["item_display_width"]);
                $("#item-display-width-metric").val(response["item_display_width_metric"]);
                $("#item-display-height").val(response["item_display_height"]);
                $("#item-display-height-metric").val(response["item_display_height_metric"]);
                $("#item-count").val(response["item_count"]);
                $("#item-count-metric").val(response["item_count_metric"]);
                $("#item-condition-note").val(response["item_condition_note"]);
                $("#max-order-quantity").val(response["max_order_quantity"]);
                $("#number-of-items").val(response["number_of_items"]);
                $("#wattage").val(response["wattage"]);
                $("#wattage-metric").val(response["wattage_metric"]);
                $("#material-type").val(response["material_type"]);
                $("#parentage").val(response["parentage"]);
                $("#parent-sku").val(response["parent_sku"]);
                $("#relationship-type").val(response["relationship_type"]);
                $("#variation-theme").val(response["variation_theme"]);
                $("#standard-price").val(response["standard_price"]);
                $("#quantity").val(response["quantity"]);
                $("#sale-price").val(response["sale_price"]);
                $("#sale-from").val(response["sale_from"]);
                $("#sale-end").val(response["sale_end"]);

                $("#noon-msrp-ae").val(response["noon_msrp_ae"]);
                $("#noon-msrp-ae-unit").val(response["noon_msrp_ae_unit"]);

                $("#factory-notes").val(response["factory_notes"]);


                global_images = response["images"];

                $("#all-images-option").html("All Images (" + global_images["all_images"].length + ")");
                $("#main-images-option").html("Main Images (" + global_images["main_images"].length + ")");
                $("#sub-images-option").html("Sub Images (" + global_images["sub_images"].length + ")");
                $("#pfl-images-option").html("PFL Images (" + global_images["pfl_images"].length + ")");
                $("#pfl-generated-images-option").html("PFL Generated Images (" + global_images["pfl_generated_images"].length + ")");
                $("#white-background-images-option").html("White Background Images (" + global_images["white_background_images"].length + ")");
                $("#lifestyle-images-option").html("Lifestyle Images (" + global_images["lifestyle_images"].length + ")");
                $("#certificate-images-option").html("Certificate Images (" + global_images["certificate_images"].length + ")");
                $("#giftbox-images-option").html("Giftbox Images (" + global_images["giftbox_images"].length + ")");
                $("#diecut-images-option").html("Diecut Images (" + global_images["diecut_images"].length + ")");
                $("#aplus-content-images-option").html("A+ Content Images (" + global_images["aplus_content_images"].length + ")");
                $("#ads-images-option").html("Ads Images (" + global_images["ads_images"].length + ")");
                $("#unedited-images-option").html("Unedited Images (" + global_images["unedited_images"].length + ")");

                update_grid_images(global_image_key);

                $('#brand-image-img').attr("src", response["brand_logo"]);
                if (global_images["main_images"].length > 0) {
                    $('#pfl-product-image-preview-img').attr("src", global_images["main_images"][0]["main-url"]);
                }
                $('#barcode-image-preview-img').attr("src", response["barcode_image_url"]);

                $("#pfl-editor-link").attr("href", "/pfl/" + response["pfl_pk"]);

                M.updateTextFields();
                $('select').formSelect();
            },
            error: function (xhr, textstatus, errorthrown) {
                console.log("Please report this error: " + errorthrown + xhr.status + xhr.responseText);
            }
        });
    }

    fetch_product_details();

    var product_attribute_amazon_uk_cnt = 1;
    $("#add-product-attribute-amazon-uk-btn").click(function () {
        product_attribute_amazon_uk_cnt++;

        var html_string = `<div>
                         <div class="input-field col s9">
                           <input id="product-attribute-amazon-uk-`+ product_attribute_amazon_uk_cnt + `" type="text" >
                           <label for="product-attribute-amazon-uk-`+ product_attribute_amazon_uk_cnt + `">Product Attribute</label>
                         </div>
                         <div class="input-field col s1">
                           <a href="#!" class="remove-product-attribute-amazon-uk-btn btn-floating red" style="background-color: red !important; transform: scale(0.7);box-shadow: none;"><i class="material-icons">delete</i></a>
                         </div>
                       </div>`
        $("#product-attributes-amazon-uk-div").append(html_string);
    });

    $(document).on("click", ".remove-product-attribute-amazon-uk-btn", function () {
        $(this).parent().parent().remove();
    });


    var product_attribute_amazon_uae_cnt = 1;
    $("#add-product-attribute-amazon-uae-btn").click(function () {
        product_attribute_amazon_uae_cnt++;

        var html_string = `<div>
                         <div class="input-field col s9">
                           <input id="product-attribute-amazon-uae-`+ product_attribute_amazon_uae_cnt + `" type="text" >
                           <label for="product-attribute-amazon-uae-`+ product_attribute_amazon_uae_cnt + `">Product Attribute</label>
                         </div>
                         <div class="input-field col s1">
                           <a href="#!" class="remove-product-attribute-amazon-uae-btn btn-floating red" style="background-color: red !important; transform: scale(0.7);box-shadow: none;"><i class="material-icons">delete</i></a>
                         </div>
                      </div>`
        $("#product-attributes-amazon-uae-div").append(html_string);
    });

    $(document).on("click", ".remove-product-attribute-amazon-uae-btn", function () {
        $(this).parent().parent().remove();
    });


    var product_attribute_ebay_cnt = 1;
    $("#add-product-attribute-ebay-btn").click(function () {
        product_attribute_ebay_cnt++;

        var html_string = `<div>
                         <div class="input-field col s9">
                           <input id="product-attribute-ebay-`+ product_attribute_ebay_cnt + `" type="text" >
                           <label for="product-attribute-ebay-`+ product_attribute_ebay_cnt + `">Product Attribute</label>
                         </div>
                         <div class="input-field col s1">
                           <a href="#!" class="remove-product-attribute-ebay-btn btn-floating red" style="background-color: red !important; transform: scale(0.7);box-shadow: none;"><i class="material-icons">delete</i></a>
                         </div>
                       </div>`
        $("#product-attributes-ebay-div").append(html_string);
    });

    $(document).on("click", ".remove-product-attribute-ebay-btn", function () {
        $(this).parent().parent().remove();
    });




    var product_attribute_noon_cnt = 1;
    $("#add-product-attribute-noon-btn").click(function () {
        product_attribute_noon_cnt++;

        var html_string = `<div>
                         <div class="input-field col s9">
                           <input id="product-attribute-noon-`+ product_attribute_noon_cnt + `" type="text" >
                           <label for="product-attribute-noon-`+ product_attribute_noon_cnt + `">Product Attribute</label>
                         </div>
                         <div class="input-field col s1">
                           <a href="#!" class="remove-product-attribute-noon-btn btn-floating red" style="background-color: red !important; transform: scale(0.7);box-shadow: none;"><i class="material-icons">delete</i></a>
                         </div>
                       </div>`
        $("#product-attributes-noon-div").append(html_string);
    });

    $(document).on("click", ".remove-product-attribute-noon-btn", function () {
        $(this).parent().parent().remove();
    });




    var special_feature_cnt = 1;
    $("#add-special-feature-btn").click(function () {
        special_feature_cnt++;

        var html_string = `<div>
                           <div class="input-field col s9">
                             <input id="special-feature-`+ special_feature_cnt + `" type="text" >
                             <label for="special-feature-`+ special_feature_cnt + `">Special Feature</label>
                           </div>

                           <div class="input-field col s1">
                             <a href="#!" class="remove-special-feature-btn btn-floating blue" style = "background-color: red !important; transform: scale(0.7);box-shadow: none;"><i class="material-icons">delete</i></a>
                           </div>
                        </div>`
        $("#special-features-div").append(html_string);
    });

    $(document).on("click", ".remove-special-feature-btn", function () {
        $(this).parent().parent().remove();
    });


    function update_grid_images_main_images(key) {
        var html_string = "";
        for (var i = 0; i < global_images[key].length; i++) {
            var checked = "";
            if (global_images[key][i]["is_main_image"] == true) {
                checked = "checked";
            }

            if (i % 3 == 0) {
                html_string += "<div class='flex-container-space-btw' style='margin-top:0em;margin-bottom:0em;padding-top:0em !important;padding-bottom:0em !important;width:25.5vw !important;'>";
            }

            html_string += `<div style=";position:relative;">
                        <a href="#delete-image-modal" id="delimg-`+ global_images[key][i]["pk"] + `" class="delete-image-modal-btn modal-trigger right" style="position:absolute;top:4px;right:2px;z-index:100;background-color: transparent;display: block;cursor: pointer;" title="Delete Image">
                          <i class="material-icons redd" title="Delete Image" style="
                            background-color: transparent;
                            padding: 4px;
                            color: gray;
                            border-radius: 2px;
                            margin-left: 4px;
                            font-size: 10px;
                            margin-right: 4px;
                            display: block;
                            margin-bottom: 5px;">
                            close
                          </i>
                        </a>
                        <img class="miniimage" src="`+ global_images[key][i]["thumbnail-url"] + `" midimage_url="` + global_images[key][i]["midimage-url"] + `" high_def_url="` + global_images[key][i]["main-url"] + `"  style="width: 100%;object-fit:contain;">
                        <label style="margin-left:0px !important;">
                          <input value="`+ global_images[key][i]["pk"] + `" name="group1" type="radio" ` + checked + ` />
                          <span class = "checkbox"></span>
                        </label>
                      </div>`;

            if (i % 3 == 2 || i == global_images[key].length - 1) {
                html_string += "</div>";
            }
        }

        $("#graphics-section").html(html_string);
    }


    $(document).on('click', '.miniimage', function () {
        let url = $(this).attr('midimage_url');
        let high_def_url = $(this).attr('high_def_url');
        $('.material-placeholder').remove();
        $('.main-image').append(`<img class = "preview-img materialboxed" src = '` + url + `' high_def_url="` + high_def_url + `">`)
        $('.materialboxed').materialbox();
    });

    $(document).on("click", ".delete-image-modal-btn", function () {
        global_delete_image_pk = this.id.split("-")[1];
    })

    $("#delete-image-btn").click(function () {
        delete_image();
    })

    function delete_image() {
        var image_type = "";
        if (global_image_key == "sub_images" || global_image_key == "main_images") {
            image_type = "main_sub";
        }
        else {
            image_type = "other";
        }

        var fd = new FormData();
        fd.append("image_pk", global_delete_image_pk);
        fd.append("image_type", image_type);

        $.ajax({
            url: "/delete-image/",
            type: "POST",
            headers: {
                'X-CSRFToken': getCsrfToken()
            },
            processData: false,
            contentType: false,
            data: fd,
            success: function (response) {
                console.log("Success!", response);
                if (response["status"] == 200) {
                    M.toast({ html: "Image successfully deleted!" });
                    $("#delete-image-modal").modal("close");
                    fetch_product_images_details();
                }
                else if (response["status"] == 403) {
                    M.toast({ html: "You do not have permission to delete images!" });
                }
                else {
                    M.toast({ html: "Error deleting image!" });
                }
            },
            error: function (xhr, textstatus, errorthrown) {
                console.log("Please report this error: " + errorthrown + xhr.status + xhr.responseText);
            }
        });
    }

    $("#main-image-select-save-btn").click(function () {

        if (global_image_key != "main_images") {
            return;
        }

        var fd = new FormData();

        var checked_pk = $("input[name=group1]:checked").val();
        fd.append("checked_pk", checked_pk);
        fd.append("product_pk", window.location.pathname.split("/")[3]);

        $.ajax({
            url: "/update-main-image/",
            type: "POST",
            headers: {
                'X-CSRFToken': getCsrfToken()
            },
            processData: false,
            contentType: false,
            data: fd,
            success: function (response) {
                console.log("Success!", response);
                if (response["status"] == 200) {
                    M.toast({ html: "Main image updated successfully!" });
                }
                else if (response["status"] == 403) {
                    M.toast({ html: "You do not have permission to update main image!" });
                }
                else {
                    M.toast({ html: "Error updating main image!" });
                }
            },
            error: function (xhr, textstatus, errorthrown) {
                console.log("Please report this error: " + errorthrown + xhr.status + xhr.responseText);
            }
        });
    });


    function update_grid_images_sub_images(key) {
        var html_string = "";
        for (var i = 0; i < global_images[key].length; i++) {
            var checked = "";
            if (global_images[key][i]["is_sub_image"] == true) {
                checked = "checked";
            }

            if (i % 3 == 0) {
                html_string += "<div class='flex-container-space-btw' style='margin-top:0em;margin-bottom:0em;padding-top:0em !important;padding-bottom:0em !important;width:25.5vw !important;'>";
            }

            var sub_image_index = global_images[key][i]["sub_image_index"];
            if (sub_image_index == 0)
                sub_image_index = "-"

            html_string += `<div class="" style="position:relative;">
                        <a href="#delete-image-modal" id="delimg-`+ global_images[key][i]["pk"] + `" class="delete-image-modal-btn modal-trigger right" style="position:absolute;top:4px;right:4px;z-index:100;background-color: transparent;display: block;cursor: pointer;" title="Delete Image">
                          <i class="material-icons redd" title="Delete Image" style="
                            background-color: transparent;
                            padding: 4px;
                            color: gray;
                            border-radius: 2px;
                            margin-left: 4px;
                            font-size: 10px;
                            margin-right: 4px;
                            display: block;
                            margin-bottom: 5px;">
                            close
                          </i>
                        </a>
                        <img class="miniimage" src="`+ global_images[key][i]["thumbnail-url"] + `" midimage_url="` + global_images[key][i]["midimage-url"] + `" high_def_url="` + global_images[key][i]["main-url"] + `" style="width: 100%;object-fit:contain;">
                        <input value="`+ sub_image_index + `" id="subcheck_` + global_images[key][i]["pk"] + `" type="text">
                      </div>`;

            if (i % 3 == 2 || i == global_images[key].length - 1) {
                html_string += "</div>";
            }
        }
        $("#graphics-section").html(html_string);
    }

    function save_subimages_index() {
        if (global_image_key != "sub_images") {
            return;
        }
        var fd = new FormData();

        var sub_image = [];
        var key = "sub_images";

        // Check for condition
        var unique_sub_index = [];
        for (var i = 0; i < global_images[key].length; i++) {
            var sub_image_index = $("#subcheck_" + global_images[key][i]["pk"]).val().trim();
            if (sub_image_index != "-" && sub_image_index != "") {
                sub_image_index = parseInt(sub_image_index);
                if (sub_image_index >= 1 && sub_image_index <= 8) {
                    console.log("Key: ", sub_image_index);
                    if (unique_sub_index.includes(sub_image_index)) {
                        M.toast({ html: "Sub Image indices must be unique" })
                        return;
                    }

                    unique_sub_index.push(sub_image_index);
                }
                else {
                    M.toast({ html: "Sub Image indices must be between 1 to 8" })
                    return;
                }
            }
        }


        for (var i = 0; i < global_images[key].length; i++) {
            var temp_dict = {};
            temp_dict["pk"] = global_images[key][i]["pk"];
            var sub_image_index = $("#subcheck_" + global_images[key][i]["pk"]).val();
            if (sub_image_index == "" || sub_image_index == "-")
                sub_image_index = "0"
            temp_dict["sub_image_index"] = sub_image_index;
            sub_image.push(temp_dict);
        }

        fd.append("sub_images", JSON.stringify(sub_image));
        fd.append("product_pk", window.location.pathname.split("/")[3]);

        $.ajax({
            url: "/update-sub-images/",
            type: "POST",
            headers: {
                'X-CSRFToken': getCsrfToken()
            },
            processData: false,
            contentType: false,
            data: fd,
            success: function (response) {
                console.log("Success!", response);
                if (response["status"] == 200) {
                    M.toast({ html: "Sub images updated successfully!" });
                }
                else if (response["status"] == 403) {
                    M.toast({ html: "You do not have permission to update sub images!" });
                }
                else {
                    M.toast({ html: "Error updating sub images!" });
                }
            },
            error: function (xhr, textstatus, errorthrown) {
                console.log("Please report this error: " + errorthrown + xhr.status + xhr.responseText);
            }
        });
    }


    function update_grid_images(key) {
        if (key == "all_images") {
            $("#import-btn").attr("class", "disabled");
        }
        else {
            $("#import-btn").attr("class", "modal-trigger");
        }

        if (key == "main_images") {
            update_grid_images_main_images(key);
            return;
        }


        if (key == "sub_images") {
            update_grid_images_sub_images(key);
            return;
        }


        var html_string = "";
        for (var i = 0; i < global_images[key].length; i++) {
            html_string += `<div class="col s4" style="padding:1em;">
                        <div style="position:relative;">
                          <a href="#delete-image-modal" id="delimg-`+ global_images[key][i]["pk"] + `" class="delete-image-modal-btn modal-trigger right" style="position:absolute;top:4px;right:2px;z-index:100;background-color: transparent;display: block;cursor: pointer;" title="Delete Image">
                            <i class="material-icons redd" title="Delete Image" style="
                              background-color: transparent;
                              padding: 4px;
                              color: gray;
                              border-radius: 2px;
                              margin-left: 4px;
                              font-size: 10px;
                              margin-right: 4px;
                              display: block;
                              margin-bottom: 5px;">
                              close
                            </i> 
                          </a> 
                          <img class="miniimage" src="`+ global_images[key][i]["thumbnail-url"] + `" midimage_url="` + global_images[key][i]["midimage-url"] + `" high_def_url="` + global_images[key][i]["main-url"] + `" style="width: 100%;object-fit:contain;">
                        </div>
                      </div>`;  
        }

        $("#graphics-section").html(html_string);
    }



    $("#images-category").change(function () {
        if ($("#images-category").val() == "All Images") {
            update_grid_images("all_images");
            global_image_key = "all_images";
        }
        else if ($("#images-category").val() == "Main Images") {
            update_grid_images("main_images");
            global_image_key = "main_images";
        }
        else if ($("#images-category").val() == "Sub Images") {
            update_grid_images("sub_images");
            global_image_key = "sub_images";
        }
        else if ($("#images-category").val() == "PFL Images") {
            update_grid_images("pfl_images");
            global_image_key = "pfl_images";
        }
        else if ($("#images-category").val() == "PFL Generated Images") {
            update_grid_images("pfl_generated_images");
            global_image_key = "pfl_generated_images";
        }
        else if ($("#images-category").val() == "White Background Images") {
            update_grid_images("white_background_images");
            global_image_key = "white_background_images";
        }
        else if ($("#images-category").val() == "Lifestyle Images") {
            update_grid_images("lifestyle_images");
            global_image_key = "lifestyle_images";
        }
        else if ($("#images-category").val() == "Certificate Images") {
            update_grid_images("certificate_images");
            global_image_key = "certificate_images";
        }
        else if ($("#images-category").val() == "Giftbox Images") {
            update_grid_images("giftbox_images");
            global_image_key = "giftbox_images";
        }
        else if ($("#images-category").val() == "Diecut Images") {
            update_grid_images("diecut_images");
            global_image_key = "diecut_images";
        }
        else if ($("#images-category").val() == "A+ Content Images") {
            update_grid_images("aplus_content_images");
            global_image_key = "aplus_content_images";
        }
        else if ($("#images-category").val() == "Ads Images") {
            update_grid_images("ads_images");
            global_image_key = "ads_images";
        }
        else if ($("#images-category").val() == "Unedited Images") {
            update_grid_images("unedited_images");
            global_image_key = "unedited_images";
        }
    });


    function save_pfl_image_to_bucket() {
        var pfl_product_name = $("#pfl-product-name").val();

        var seller_sku = $("#seller-sku").val();

        var image_links = [];

        //Set the images
        if (global_images["main_images"].length > 0) {
            $("#pfl-product-image-preview-img").attr("src", global_images["main_images"][0]["main-url"]);
        }

        //$("#brand-image-img").attr("src", "");
        //$("#barcode-image-preview-img").attr("src", "");


        if ($("#pfl-product-image-preview-img").attr("src") != "") {
            image_links.push({
                "key": "product_image",
                "url": $("#pfl-product-image-preview-img").attr("src")
            });
        }

        if ($("#brand-image-img").attr("src") != "") {
            image_links.push({
                "key": "brand_image",
                "url": $("#brand-image-img").attr("src")
            });
        }

        if ($("#barcode-image-preview-img").attr("src") != "") {
            image_links.push({
                "key": "barcode_image",
                "url": $("#barcode-image-preview-img").attr("src")
            });
        }


        $("#seller-sku-preview").html(seller_sku);

        var html_string = `<br><br>`;
        var feature_text = $(".feature-text");
        for (var i = 0; i < feature_text.length; i++) {
            html_string += `<span style="font-family: 'AvenirNextRegular'"><span style="color:#521893;">&bullet;&nbsp;&nbsp;</span> ` + feature_text[i].value + `</span><br>`
        }
        $("#features-preview-div").html(html_string);

        $("#product-name-preview").text(pfl_product_name);


        $.ajax({
            url: "/download-images-s3/",
            type: "POST",
            headers: {
                'X-CSRFToken': getCsrfToken()
            },
            data: {
                links: JSON.stringify(image_links)
            },
            success: function (response) {
                console.log("Success! ", response);
                if (response["status"] == 200) {
                    var local_links = response["local_links"];

                    for (var i = 0; i < response["local_links"].length; i++) {
                        if (local_links[i]["key"] == "product_image") {
                            $("#pfl-product-image-preview-img").attr("src", local_links[i]["url"]);
                            $("#pfl-product-image-preview-img").show();
                        }
                        else if (local_links[i]["key"] == "brand_image") {
                            $("#brand-image-img").attr("src", local_links[i]["url"]);
                            $("#brand-image-img").show();
                        }
                        else if (local_links[i]["key"] == "barcode_image") {
                            $("#barcode-image-preview-img").attr("src", local_links[i]["url"]);
                            $("#barcode-image-preview-img").show();
                        }
                    }

                    $('#pfl-div').css("display", "block");

                    html2canvas($("#pfl-div"), {
                        logging: true,
                        dpi: 600,
                        scale: 3,
                        onrendered: function (canvas) {

                            $("#pfl-div").hide();
                            var image_data = canvas.toDataURL();

                            var fd = new FormData();
                            fd.append('image_data', image_data);
                            fd.append('product_pk', window.location.pathname.split("/")[3]);

                            $.ajax({
                                url: "/save-pfl-in-bucket/",
                                type: "POST",
                                headers: {
                                    'X-CSRFToken': getCsrfToken()
                                },
                                processData: false,
                                contentType: false,
                                data: fd,
                                success: function (response) {
                                    console.log("Success!", response);
                                    if (response["status"] == 200) {
                                        global_images["pfl_generated_images"] = [{
                                            "main-url": response["main-url"],
                                            "midimage-url": response["midimage-url"],
                                            "thumbnail-url": response["thumbnail-url"]
                                        }];
                                        if (global_image_key != "sub_images") {
                                            update_grid_images(global_image_key);
                                        }

                                        if (global_image_key == "pfl_generated_images") {
                                            $($(".miniimage")[0]).click();
                                        }
                                    }
                                },
                                error: function (xhr, textstatus, errorthrown) {
                                    console.log("Please report this error: " + errorthrown + xhr.status + xhr.responseText);
                                }
                            });
                        }
                    });
                }
            },
            error: function (xhr, textstatus, errorthrown) {
                console.log("Please report this error: " + errorthrown + xhr.status + xhr.responseText);
            }
        });
    }

    function save_product() {
        save_pfl_image_to_bucket();

        $("#save-btn").attr("disabled", "disabled");

        var product_pk = window.location.pathname.split("/")[3];

        var pfl_product_name = $("#pfl-product-name").val();
        var pfl_product_features = [];
        for (var i = 0; i < $(".feature-text").length; i++) {
            pfl_product_features.push($(".feature-text")[i].value);
        }

        var product_name_amazon_uk = $("#product-name-amazon-uk").val();
        var product_name_amazon_uae = $("#product-name-amazon-uae").val();
        var product_name_ebay = $("#product-name-ebay").val();
        var product_name_sap = $("#product-name-sap").val();
        var product_name_noon = $("#product-name-noon").val();

        var category = $("#category").val();
        var subtitle = $("#subtitle").val();
        var brand = $("#brand-name").val();
        var manufacturer = $("#manufacturer").val();
        var product_id = $("#product-id").val();
        var product_id_type = $("#product-id-type").val();
        var seller_sku = $("#seller-sku").val();
        var manufacturer_part_number = $("#manufacturer-part-number").val();
        var barcode_string = $("#barcode-string").val();
        var noon_product_type = $("#noon-product-type").val();
        var noon_product_subtype = $("#noon-product-subtype").val();
        var noon_model_number = $("#noon-model-number").val();
        var noon_model_name = $("#noon-model-name").val();
        var condition_type = $("#condition-type").val();
        var feed_product_type = $("#feed-product-type").val();
        var update_delete = $("#update-delete").val();
        var recommended_browse_nodes = $("#recommended-browse-nodes").val();
        var product_description_amazon_uk = window.editor[0].getData();
        var product_description_amazon_uae = window.editor[1].getData();
        var product_description_ebay = window.editor[2].getData();
        var product_description_noon = window.editor[3].getData();


        var product_attribute_data_amazon_uk = [];
        for (var i = 1; i <= product_attribute_amazon_uk_cnt; i++) {
            if ($("#product-attribute-amazon-uk-" + i).val() != "") {
                product_attribute_data_amazon_uk.push($("#product-attribute-amazon-uk-" + i).val());
            }
        }
        product_attribute_data_amazon_uk = JSON.stringify(product_attribute_data_amazon_uk);


        var product_attribute_data_amazon_uae = [];
        for (var i = 1; i <= product_attribute_amazon_uae_cnt; i++) {
            if ($("#product-attribute-amazon-uae-" + i).val() != "") {
                product_attribute_data_amazon_uae.push($("#product-attribute-amazon-uae-" + i).val());
            }
        }
        product_attribute_data_amazon_uae = JSON.stringify(product_attribute_data_amazon_uae);


        var product_attribute_data_ebay = [];
        for (var i = 1; i <= product_attribute_ebay_cnt; i++) {
            if ($("#product-attribute-ebay-" + i).val() != "") {
                product_attribute_data_ebay.push($("#product-attribute-ebay-" + i).val());
            }
        }
        product_attribute_data_ebay = JSON.stringify(product_attribute_data_ebay);



        var product_attribute_data_noon = [];
        for (var i = 1; i <= product_attribute_noon_cnt; i++) {
            if ($("#product-attribute-noon-" + i).val() != "") {
                product_attribute_data_noon.push($("#product-attribute-noon-" + i).val());
            }
        }
        product_attribute_data_noon = JSON.stringify(product_attribute_data_noon);


        var search_terms = $("#search-terms").val();
        var color_map = $("#color-map").val();
        var color = $("#color").val();
        var enclosure_material = $("#enclosure-material").val();
        var cover_material_type = $("#cover-material-type").val();


        var special_feature_data = [];
        for (var i = 1; i <= special_feature_cnt; i++) {
            if ($("#special-feature-" + i).val() != "") {
                special_feature_data.push($("#special-feature-" + i).val());
            }
        }

        var special_feature_data = JSON.stringify(special_feature_data);
        var package_length = $("#package-length").val();
        var package_length_metric = $("#package-length-metric").val();
        var package_width = $("#package-width").val();
        var package_width_metric = $("#package-width-metric").val();
        var package_height = $("#package-height").val();
        var package_height_metric = $("#package-height-metric").val();
        var package_weight = $("#package-weight").val();
        var package_weight_metric = $("#package-weight-metric").val();
        var shipping_weight = $("#shipping-weight").val();
        var shipping_weight_metric = $("#shipping-weight-metric").val();
        var item_display_weight = $("#item-display-weight").val();
        var item_display_weight_metric = $("#item-display-weight-metric").val();
        var item_display_volume = $("#item-display-volume").val();
        var item_display_volume_metric = $("#item-display-volume-metric").val();
        var item_display_length = $("#item-display-length").val();
        var item_display_length_metric = $("#item-display-length-metric").val();
        var item_weight = $("#item-weight").val();
        var item_weight_metric = $("#item-weight-metric").val();
        var item_length = $("#item-length").val();
        var item_length_metric = $("#item-length-metric").val();
        var item_width = $("#item-width").val();
        var item_width_metric = $("#item-width-metric").val();
        var item_height = $("#item-height").val();
        var item_height_metric = $("#item-height-metric").val();
        var item_display_width = $("#item-display-width").val();
        var item_display_width_metric = $("#item-display-width-metric").val();
        var item_display_height = $("#item-display-height").val();
        var item_display_height_metric = $("#item-display-height-metric").val();
        var item_count = $("#item-count").val();
        var item_count_metric = $("#item-count-metric").val();

        var item_condition_note = $("#item-condition-note").val();
        var max_order_quantity = $("#max-order-quantity").val();
        var number_of_items = $("#number-of-items").val();
        var wattage = $("#wattage").val();
        var wattage_metric = $("#wattage-metric").val();
        var material_type = $("#material-type").val();
        var parentage = $("#parentage").val();
        var parent_sku = $("#parent-sku").val();
        var relationship_type = $("#relationship-type").val();
        var variation_theme = $("#variation-theme").val();
        var standard_price = $("#standard-price").val();
        var quantity = $("#quantity").val();
        var sale_price = $("#sale-price").val();
        var sale_from = $("#sale-from").val();
        var sale_end = $("#sale-end").val();
        var noon_msrp_ae = $("#noon-msrp-ae").val();
        var noon_msrp_ae_unit = $("#noon-msrp-ae-unit").val();
        var product_pk = window.location.pathname.split("/")[3];

        var factory_notes = $("#factory-notes").val();

        var fd = new FormData();

        fd.append('pfl_product_name', pfl_product_name)
        fd.append('pfl_product_features', JSON.stringify(pfl_product_features));
        fd.append('product_pk', product_pk)
        fd.append('product_name_sap', product_name_sap);
        fd.append('product_name_amazon_uk', product_name_amazon_uk);
        fd.append('product_name_amazon_uae', product_name_amazon_uae);
        fd.append('product_name_ebay', product_name_ebay);
        fd.append('product_name_noon', product_name_noon);
        fd.append('category', category);
        fd.append('subtitle', subtitle);
        fd.append('brand', brand);
        fd.append('manufacturer', manufacturer);
        fd.append('product_id', product_id);
        fd.append('product_id_type', product_id_type);
        fd.append('seller_sku', seller_sku);
        fd.append('manufacturer_part_number', manufacturer_part_number);
        fd.append('barcode_string', barcode_string);
        fd.append('noon_product_type', noon_product_type);
        fd.append('noon_product_subtype', noon_product_subtype);
        fd.append('noon_model_name', noon_model_name);
        fd.append('noon_model_number', noon_model_number);
        fd.append('condition_type', condition_type);
        fd.append('feed_product_type', feed_product_type);
        fd.append('update_delete', update_delete);
        fd.append('recommended_browse_nodes', recommended_browse_nodes);
        fd.append('product_description_amazon_uk', product_description_amazon_uk);
        fd.append('product_description_amazon_uae', product_description_amazon_uae);
        fd.append('product_description_ebay', product_description_ebay);
        fd.append('product_description_noon', product_description_noon);

        fd.append('product_attribute_list_amazon_uk', product_attribute_data_amazon_uk);
        fd.append('product_attribute_list_amazon_uae', product_attribute_data_amazon_uae);
        fd.append('product_attribute_list_ebay', product_attribute_data_ebay);
        fd.append('product_attribute_list_noon', product_attribute_data_noon);
        fd.append('search_terms', search_terms);
        fd.append('color_map', color_map);
        fd.append('color', color);
        fd.append('enclosure_material', enclosure_material);
        fd.append('cover_material_type', cover_material_type);
        fd.append('special_features', special_feature_data);
        fd.append('package_length', package_length);
        fd.append('package_length_metric', package_length_metric);
        fd.append('package_width', package_width);
        fd.append('package_width_metric', package_width_metric);
        fd.append('package_height', package_height);
        fd.append('package_height_metric', package_height_metric);
        fd.append('package_weight', package_weight);
        fd.append('package_weight_metric', package_weight_metric);
        fd.append('shipping_weight', shipping_weight);
        fd.append('shipping_weight_metric', shipping_weight_metric);
        fd.append('item_display_weight', item_display_weight);
        fd.append('item_display_weight_metric', item_display_weight_metric);
        fd.append('item_display_volume', item_display_volume);
        fd.append('item_display_volume_metric', item_display_volume_metric);
        fd.append('item_display_length', item_display_length);
        fd.append('item_display_length_metric', item_display_length_metric);
        fd.append('item_weight', item_weight);
        fd.append('item_weight_metric', item_weight_metric);
        fd.append('item_length', item_length);
        fd.append('item_length_metric', item_length_metric);
        fd.append('item_width', item_width);
        fd.append('item_width_metric', item_width_metric);
        fd.append('item_height', item_height);
        fd.append('item_height_metric', item_height_metric);
        fd.append('item_display_width', item_display_width);
        fd.append('item_display_width_metric', item_display_width_metric);
        fd.append('item_display_height', item_display_height);
        fd.append('item_display_height_metric', item_display_height_metric);
        fd.append('item_count', item_count);
        fd.append('item_count_metric', item_count_metric);

        fd.append('item_condition_note', item_condition_note);
        fd.append('max_order_quantity', max_order_quantity);
        fd.append('number_of_items', number_of_items);
        fd.append('wattage', wattage);
        fd.append('wattage_metric', wattage_metric);
        fd.append('material_type', material_type);
        fd.append('parentage', parentage);
        fd.append('parent_sku', parent_sku);
        fd.append('relationship_type', relationship_type);
        fd.append('variation_theme', variation_theme);
        fd.append('standard_price', standard_price);
        fd.append('quantity', quantity);
        fd.append('sale_price', sale_price);
        fd.append('sale_from', sale_from);
        fd.append('sale_end', sale_end);
        fd.append('noon_msrp_ae', noon_msrp_ae);
        fd.append('noon_msrp_ae_unit', noon_msrp_ae_unit);
        fd.append('factory_notes', factory_notes);

        $.ajax({
            url: "/save-product/",
            type: "POST",
            headers: {
                'X-CSRFToken': getCsrfToken()
            },
            processData: false,
            contentType: false,
            data: fd,
            success: function (response) {

                console.log("Success!", response);
                if (response["status"] == 200) {
                    M.toast({ html: "Product saved successfully!" });
                }
                else if (response["status"] == 409) {
                    M.toast({ html: "Product ID or Seller SKU is duplicated!" });
                }
                else if (response["status"] == 403) {
                    M.toast({ html: "You do not have permission for saving product!" });
                }
                else {
                    M.toast({ html: "Error saving product!" });
                }
                $("#save-btn").removeAttr("disabled");
            },
            error: function (xhr, textstatus, errorthrown) {
                console.log("Please report this error: " + errorthrown + xhr.status + xhr.responseText);
            }
        });

        save_subimages_index();
    }


    $("#save-btn").click(function () {
        if ($("#product-name-sap").val() == "" || $("#product-id").val() == "" || $("#seller-sku").val() == "" || $("#brand-name").val() == "" || $("#product-name-sap").val() == "") {

        }

        if ($("#brand-name").val().trim() == "") {
            M.toast({ html: "Brand name cannot be empty!" });
            return;
        }

        if ($("#product-id").val().trim() == "") {
            M.toast({ html: "Product ID cannot be empty!" });
            return;
        }

        if ($("#seller-sku").val().trim() == "") {
            M.toast({ html: "Seller SKU cannot be empty!" });
            return;
        }

        save_product();
    });

    $("#information-tab").click(function () {
        setTimeout(function () {
            $('.tabs').tabs('updateTabIndicator');
        }, 100);
    });


    $(window).keydown(function (event) {
        console.log(event.which, event.keyCode, event.ctrlKey);
        if (event.which == 83 && event.ctrlKey) {
            event.preventDefault();
            save_product();
            return false;
        }
    });

   $('#collapse-div').bind('resize', function(){
   console.log('resized');
   return false;
});