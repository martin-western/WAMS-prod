import requests


def add_product_in_dealshub(uuid):

    r = requests.post(
        "http://127.0.0.1:8000/api/dealshub/v1.0/product/add-product", data={"uuid": str(uuid)})
    return


def delete_product_in_dealshub(uuid):
    r = requests.post(
        "http://127.0.0.1:8000/api/dealshub/v1.0/product/delete-product", data={"uuid": str(uuid)})
    return True
