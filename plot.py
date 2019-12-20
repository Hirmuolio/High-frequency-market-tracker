#!/usr/bin/env python3

import json
from datetime import datetime
from datetime import timedelta
import numpy as np
import matplotlib.pyplot as plt
import gzip
import time

import esi_calling


try:
	with gzip.GzipFile('market_cache.gz', 'r') as fin:
		market_cache = json.loads(fin.read().decode('utf-8'))
except:
	print('no market cache found')
	market_cache = {}

try:
	with gzip.GzipFile('item_cache.gz', 'r') as fin:
		item_cache = json.loads(fin.read().decode('utf-8'))
except:
	print('no item_cache found')
	item_cache = {}

def plot_prices(item_id):
	#market_cache[str(item_id)]['buy_prices']
	
	if str(item_id) in market_cache:
		times = []
	
		for time in market_cache[str(item_id)]['times']:
			times.append(datetime.strptime(time, '%Y-%m-%d  %H:%M:%S'))
		
		plt.plot(times, market_cache[str(item_id)]['buy_prices'], 'r-', label='Buy prices')
		plt.plot(times, market_cache[str(item_id)]['sell_prices'], 'b-', label='Sell prices')
	
		plt.gcf().autofmt_xdate()
		
		plt.title(item_cache[str(item_id)]['name'])
		plt.xlabel('Time')
		plt.ylabel('Price')
		
		plt.legend(loc='best')
		
		
		plt.grid(True)
		plt.show()
		
	else:
		print('No data for "'+ item_id+ '"')


while True:

	text = input("Give type ID: ")
	
	if not text in item_cache:
		print( 'Fetching info on ID "'+ text+'"')
		response = esi_calling.call_esi(scope = '/v3/universe/types/{par}/', url_parameters=[text], job = 'get item info')[0][0]
		if response.status_code != 200:
			print( 'No item with ID "'+ text+'"')
			continue
		else:
			item_cache[text] = response.json()			
			with gzip.GzipFile('item_cache.gz', 'w') as outfile:
				outfile.write(json.dumps(item_cache).encode('utf-8'))
	plot_prices(text)