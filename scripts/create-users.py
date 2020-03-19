user_list = [
    {"username": "priyanka", "password": "e0764523"},
    {"username": "ramees", "password": "0953b472"},
    {"username": "naveed", "password": "1e211e79"},
    {"username": "fanseem", "password": "e81546c7"},
    {"username": "oman", "password": "2814351f"},
    {"username": "jeddah", "password": "80d358f8"},
    {"username": "riyadh", "password": "8aa66bf9"},
    {"username": "dammam", "password": "1fcc8598"},
    {"username": "qatar", "password": "c3d384ba"},
    {"username": "rasheed", "password": "9c7426c7"},
    {"username": "dhipu", "password": "b1e7a2ae"},
    {"username": "mathew", "password": "86b046e0"},
    {"username": "shuhaib", "password": "12e0998b"},
    {"username": "radeef", "password": "ce1ac61e"},
    {"username": "shihab", "password": "fe53a7f4"},
    {"username": "sterin", "password": "c35965c8"},
    {"username": "geepas", "password": "bb4ad07a"},
    {"username": "olsenmak", "password": "aba6c329"},
    {"username": "krypton", "password": "bc315de4"},
    {"username": "royalford", "password": "9e0dda7e"},
    {"username": "parajohn", "password": "a5dbd91b"},
    {"username": "mansoor", "password": "830d4ce6"},
    {"username": "mohammad", "password": "3afc3bdd"},
    {"username": "muhammad_opr", "password": "cd30907a"},
    {"username": "ajnas", "password": "4125d5a8"},
    {"username": "azar", "password": "35ec14d0"},
    {"username": "rafeeq", "password": "7be357a5"},
    {"username": "rinas", "password": "ca18d908"},
    {"username": "sajid", "password": "9e364d6a"},
    {"username": "shyam", "password": "9faa44e0"},
    {"username": "nawas", "password": "1f8587a8"},
    {"username": "shihabudeen", "password": "be9349fa"},
    {"username": "nikhil", "password": "1f1d5186"},
    {"username": "ranjith", "password": "fe6aca1f"},
    {"username": "radheef", "password": "156a3955"},
    {"username": "vaisakh", "password": "109565f9"},
    {"username": "subair", "password": "bba25895"},
    {"username": "arsal", "password": "5a917320"},
    {"username": "umesh", "password": "5e3a10ef"},
    {"username": "ijilal", "password": "6ecf5c9a"},
    {"username": "hari", "password": "a763542q"}
]

from WAMSApp.models import *
from django.contrib.auth.models import User

for user in user_list:
    user_obj = None
    if OmnyCommUser.objects.filter(username=user["username"]).exists():
        user_obj = OmnyCommUser.objects.get(username=user["username"])
    else:
        user_obj = OmnyCommUser.objects.create(username=user["username"], first_name=user["username"].title())
        django_user = User.objects.get(username=user["username"])
        CustomPermission.objects.create(user=django_user)
    user_obj.set_password(user["password"])
    user_obj.save()