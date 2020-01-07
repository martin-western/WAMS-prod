from django.contrib.auth.models import User

admin = User.objects.create(username="admin", password="adminadmin", is_staff=True, is_superuser=True)