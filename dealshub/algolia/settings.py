from algolia.constant import *
from algoliasearch.search_client import SearchClient
from algolia.constants import *
import json


client = SearchClient.create(APPLICATION_KEY, ADMIN_KEY)
index = client.init_index('DealsHubProduct')

settings = {
	"replicas":[
		virtual(DealsHubProductPriceDesc),
		virtual(DealsHubProductPriceAsc)
	]
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
		"filterOnly(brand)",
		"filterOnly(category)",
		"filterOnly(subCategory)",
		"filterOnly(superCategory)",
		"filterOnly(price)",
		"filterOnly(isPublished)",
		"filterOnly(stock)"
	]
	"forwardToReplicas":True
}

index.set_settings(settings)

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