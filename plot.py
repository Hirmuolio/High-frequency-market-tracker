#!/usr/bin/env python3

import json
from datetime import datetime
from datetime import timedelta
import numpy as np
import matplotlib.pyplot as plt
import gzip
import time



plex = 44992


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
			times.append(datetime.strptime(time, '%Y-%m-%d  %H:%M:%S.%f'))
		
		plt.plot(times, market_cache[str(item_id)]['buy_prices'])
		plt.plot(times, market_cache[str(item_id)]['sell_prices'])
	
		plt.gcf().autofmt_xdate()
		
		plt.xlabel('Time')
		plt.ylabel('Price')
		if str(item_id) in item_cache:
			plt.title(item_cache[str(item_id)]['name'])
		plt.grid(True)
		plt.show()
		
	else:
		print('No data for ', item_id)
	
	
	
	


while True:

	text = input("Give type ID: ")
	
	if text in item_cache:
		print('Plotting: ', item_cache[text]['name'])

	plot_prices(text)