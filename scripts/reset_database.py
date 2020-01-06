from django.contrib.auth.models import User

admin = User.objects.create(username="admin2", password="adminadmin", is_staff=True, is_superuser=True)