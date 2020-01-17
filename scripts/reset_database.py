from django.contrib.auth.models import User

# Create superuser
admin = User.objects.create(username="admin", password="adminadmin", is_staff=True, is_superuser=True)

# Create Channels
c1 = Channel.objects.create(name="Amazon UK")
c2 = Channel.objects.create(name="Amazon UAE")
c3 = Channel.objects.create(name="Ebay")
c4 = Channel.objects.create(name="Noon")

# Create Brands
b1 = Brand.objects.create(name="Geepas")
b2 = Brand.objects.create(name="Royalford")


# Create Content Manager
cm = ContentManager.objects.create(username="priyanka", password="p7165wig")
# Give All permission

user = User.objects.get(username="priyanka")

cp = CustomPermission.objects.create(user=user)
cp.brands.add(*[b1, b2])
cp.channels.add(*[c1, c2, c3, c4])
cp.save()