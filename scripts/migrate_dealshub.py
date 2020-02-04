from WAMSApp.models import Product
from dealshub.models import *

products = Product.objects.filter(base_product__brand__name__in=["Geepas", "Royalford", "Krypton", "Olsenmark"])
print(products.count())
for p in products:
    d, created = DealsHubProduct.objects.get_or_create(product=p)