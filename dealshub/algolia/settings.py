from algoliasearch.search_client import SearchClient
from dealshub.algolia.constants import *
import json


client = SearchClient.create(APPLICATION_KEY, ADMIN_KEY)
index = client.init_index(DEALSHUBPRODUCT_ALGOLIA_INDEX)

settings = {
	"replicas":[
		'virtual(DealsHubProductQAPriceDesc)',
		'virtual(DealsHubProductQAPriceAsc)'
	],
	"searchableAttributes":[
		"productName",
		"brand",
		"superCategory",
		"category",
		"subCategory",
		"sellerSKU",
	],
	"attributesForFaceting":[
		"filterOnly(locationGroup)",
		"searchable(brand)",
		"searchable(category)",
		"searchable(subCategory)",
		"searchable(superCategory)",
		"filterOnly(price)",
		"filterOnly(isPublished)",
		"filterOnly(stock)"
	]
}

# replica_index_desc = client.init_index(DEALSHUBPRODUCT_DESC_PRICE_ALGOLIA_INDEX)
# replica_index_desc.set_settings({
#   'customRanking': [
#     'desc(price)'
#   ]
# })


# replica_index_asc = client.init_index(DEALSHUBPRODUCT_ASC_PRICE_ALGOLIA_INDEX)
# replica_index_asc.set_settings({
#   'customRanking': [
#     'asc(price)'
#   ]
# })

index.set_settings(settings) #,{"forwardToReplicas":True})

