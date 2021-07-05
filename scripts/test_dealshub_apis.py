import requests
import json

DEALSHUB_TEST_LINK = "http://127.0.0.1/"


#------------------------------------------------------------------------------
print("Testing Login")
url = DEALSHUB_TEST_LINK + "token-auth/"
data = {
    "username": "priyanka",
    "password": "p7165wig"
}
r = requests.post(url=url, data=data, timeout=10)
print(r.content)
token = json.loads(r.content)["token"]
print("\n\n\n")



#------------------------------------------------------------------------------
print("Testing Fetch Banner Types")
url = DEALSHUB_TEST_LINK + "dealshub/fetch-banner-types/"
headers = {
    "Authorization": "JWT "+token
}
data = {
    "organizationName": "geepas"
}
r = requests.post(headers=headers, url=url, data=data, timeout=10)
print(r.content)
status = json.loads(r.content)["status"]
banner_type = json.loads(r.content)["bannerTypes"][0]["type"]
if status==200:
    print("OK\n\n\n")
else:
    print("Fail\n\n\n")



#------------------------------------------------------------------------------
"""
print("Testing Create Banner")
url = DEALSHUB_TEST_LINK + "dealshub/create-banner/"
headers = {
    "Authorization": "JWT "+token
}
data = {
    "organizationName": "geepas",
    "bannerType": banner_type
}
r = requests.post(headers=headers, url=url, data=data)
print(r.content)
status = json.loads(r.content)["status"]
if status==200:
    print("OK\n\n\n")
else:
    print("Fail\n\n\n")
"""


#------------------------------------------------------------------------------
print("Testing Fetch Banner")
url = DEALSHUB_TEST_LINK + "dealshub/fetch-banner/"
headers = {
    "Authorization": "JWT "+token
}
data = {
    "uuid": "e4136d7f-2b79-4732-bffb-3c3fba936e37"
}
r = requests.post(headers=headers, url=url, data=data, timeout=10)
print(r.content)
status = json.loads(r.content)["status"]
if status==200:
    print("OK\n\n\n")
else:
    print("Fail\n\n\n")



#------------------------------------------------------------------------------
print("Testing Fetch Dealshub Admin Sections")
url = DEALSHUB_TEST_LINK + "dealshub/fetch-dealshub-admin-sections/"
headers = {
    "Authorization": "JWT "+token
}
data = {
    "organizationName": "geepas"
}
r = requests.post(headers=headers, url=url, data=data, timeout=10)
print(r.content)
status = json.loads(r.content)["status"]
if status==200:
    print("OK\n\n\n")
else:
    print("Fail\n\n\n")



#------------------------------------------------------------------------------
print("Testing Save Dealshub Admin Sections")
url = DEALSHUB_TEST_LINK + "dealshub/save-dealshub-admin-sections-order/"
headers = {
    "Authorization": "JWT "+token
}
obj1 = [{"type": "ProductListing","uuid": "12121"}, {"type": "Banner","uuid": "e4136d7f-2b79-4732-bffb-3c3fba936e37"}]
obj1 = json.dumps(obj1)
data = {
    "dealshubAdminSections": obj1
}
r = requests.post(headers=headers, url=url, data=data, timeout=10)
print(r.content)
status = json.loads(r.content)["status"]
if status==200:
    print("OK\n\n\n")
else:
    print("Fail\n\n\n")




#------------------------------------------------------------------------------
print("Testing Fetch Dealshub Admin Sections")
url = DEALSHUB_TEST_LINK + "dealshub/fetch-dealshub-admin-sections/"
headers = {
    "Authorization": "JWT "+token
}
data = {
    "organizationName": "geepas"
}
r = requests.post(headers=headers, url=url, data=data, timeout=10)
print(r.content)
status = json.loads(r.content)["status"]
if status==200:
    print("OK\n\n\n")
else:
    print("Fail\n\n\n")