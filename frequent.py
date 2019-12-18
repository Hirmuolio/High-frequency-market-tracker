#!/usr/bin/env python3

import json
from datetime import datetime
from datetime import timedelta
#import numpy as np
import gzip
import time

import esi_calling


esi_calling.set_user_agent('Hirmuolio/high-frequency-market-tracker')

def import_orders(region_id):
	#'10000044' Solitude
	#10000002 = Jita
	all_orders = []
	
	response_array = esi_calling.call_esi(scope = '/v1/markets/{par}/orders/', url_parameters=[region_id], job = 'get market orders')[0]
	
	expires = datetime.utcnow()
	
	for response in response_array:
		all_orders.extend(response.json())
	print('Got {:,d} orders.'.format(len(all_orders)))
	expires = max( expires, datetime.strptime(response_array[-1].headers['expires'], '%a, %d %b %Y %H:%M:%S GMT') )
	
	with open('expires.txt', "w") as text_file:
		print(str(expires), file=text_file)
	
	return [all_orders, expires]
	

def percentage_change(value1, value2):
	try:
		change = abs(value1- value2)/value1
		return change
	except:
		#Value 2 is zero (divide by zero)
		#We don't really care. Lets return 100
		return 100
	
try:
	with gzip.GzipFile('market_cache.gz', 'r') as fin:
		market_cache = json.loads(fin.read().decode('utf-8'))
except:
	print('no market cache found')
	market_cache = {}


#Main loop

while True:
	print('\n')
	print(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), '- Importing market...')
	esi_response = import_orders( 10000002 )
	
	
	#Process market orders
	print(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), '- Processing market orders...')
	
	current_prices = {}
	
	#Merge all prices to a json
	for market_order in esi_response[0]:
		#if market_order['location_id'] == 60003760: #Only take orders from Jita 4-4
		#type id = market_order['type_id']
		if not str(market_order['type_id']) in current_prices:
			current_prices[str(market_order['type_id'])] = { 'buy_prices':[], 'sell_prices':[], 'type_id':market_order['type_id']}
		
		if market_order['is_buy_order'] == True:
			current_prices[str(market_order['type_id'])]['buy_prices'].append( market_order['price'] )
		else:
			current_prices[str(market_order['type_id'])]['sell_prices'].append( market_order['price'] )
				
	#Find the current dominating prices and add them to the cache
	time_now = datetime.utcnow()
	
	for item_id in current_prices:
		item_id = str(item_id)
		
		
		if not item_id in market_cache:
			#New item. Add entry for it in cache.
			market_cache[ item_id ] = {'times':[], 'buy_prices':[], 'sell_prices':[]}
		
		
		if len(current_prices[item_id]['buy_prices']) != 0:
			current_buy = max(current_prices[item_id]['buy_prices'])
		else:
			current_buy = 0

		
		if len(current_prices[item_id]['sell_prices']) != 0:
			current_sell = min(current_prices[item_id]['sell_prices'])
		else:
			current_sell = 0
			
			
		
		sell_is_duplicate = False
		buy_is_duplicate = False
		
		if len( market_cache[ item_id ]['buy_prices'] ) > 1:
			diff_1 = percentage_change(market_cache[ item_id ]['buy_prices'][-1], current_buy)
			diff_2 = percentage_change(market_cache[ item_id ]['buy_prices'][-2], current_buy)
			
			if diff_1 < 0.03 and diff_2 < 0.03:
				buy_is_duplicate = True
				
		if len( market_cache[ item_id ]['sell_prices']) > 1:
			diff_1 = percentage_change(market_cache[ item_id ]['sell_prices'][-1], current_sell)
			diff_2 = percentage_change(market_cache[ item_id ]['sell_prices'][-2], current_sell)
			
			if diff_1 < 0.03 and diff_2 < 0.03:
				sell_is_duplicate = True
				
				
				
		if sell_is_duplicate and buy_is_duplicate:
			market_cache[ item_id ]['times'][-1] = str(time_now)
			market_cache[ item_id ]['sell_prices'][-1] = current_sell
			market_cache[ item_id ]['buy_prices'][-1] = current_buy
		else:
			market_cache[ item_id ]['times'].append( str(time_now) )
			market_cache[ item_id ]['sell_prices'].append( current_sell )
			market_cache[ item_id ]['buy_prices'].append( current_buy )
	
	try:
		with gzip.GzipFile('market_cache.gz', 'w') as outfile:
			outfile.write(json.dumps(market_cache).encode('utf-8')) 
	except:
		print(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), '- Failed to save cache. Cache will be saved after next import (do not keep the cache opened in other programs to avoid this)')
	
	
	current_prices = {}
	
	time_to_refetch = (esi_response[1] - datetime.utcnow()).total_seconds()
	
	esi_response = []
	
	print(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), '- Fetching new orders in',round(time_to_refetch)+1 ,'seconds')
	time.sleep( round(time_to_refetch)+1 )
