from algoliasearch.search_client import SearchClient
from dealshub.algolia.constants import *
import json


client = SearchClient.create(APPLICATION_KEY, ADMIN_KEY)
index = client.init_index('DealsHubProduct')

settings = {
	"replicas":[
		'virtual(DealsHubProductPriceDesc)',
		'virtual(DealsHubProductPriceAsc)'
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

index.set_settings(settings,{"forwardToReplicas":True})

replica_index_desc = client.init_index('DealsHubProductPriceDesc')
replica_index_desc.set_settings({
  'customRanking': [
    'desc(price)'
  ]
})


replica_index_asc = client.init_index('DealsHubProductPriceAsc')
replica_index_asc.set_settings({
  'customRanking': [
    'asc(price)'
  ]
})