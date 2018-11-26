#!/usr/bin/env python3

import json
from datetime import datetime
from datetime import timedelta
#import numpy as np
import gzip
import time

import esi_calling


esi_calling.set_user_agent('Hirmuolio/high-frequency-market-tracker')

		
def import_market():
	region_id = '10000002'
	
	response_array = esi_calling.call_esi(scope = '/v1/markets/{par}/orders/', url_parameter=region_id, job = 'get market orders')
	
	if type(response_array) != type([]):
		#For some reason it is not a list. Make it into a list
		response_array = [response_array]
	
	#Process the responses:
	#Merge all the orders form different responses
	#Save the time until next requests should be sent
	orders = []
	time_now = datetime.utcnow()
	expires = time_now
	
	for response in response_array:
		try:
			orders.extend(response.json())
		except:
			print('This should not be here ', response)
			print('Got ', len(response_array), ' responses')
		
		expires = max( expires, datetime.strptime(response.headers['expires'], '%a, %d %b %Y %H:%M:%S GMT') )
	
	print(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), '- Got', len(orders), 'orders. Expires at', expires)
	
	with open('expires.txt', "w") as text_file:
		print(str(expires), file=text_file)
	
	return [orders, expires]
	


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
	esi_response = import_market()
	
	
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
		#current_prices[item]
		if not item_id in market_cache:
			market_cache[ str(current_prices[item_id]['type_id']) ] = {'type_id':current_prices[item_id]['type_id'], 'buy_times':[], 'buy_prices':[], 'sell_times':[], 'sell_prices':[]}
		
		if len(current_prices[item_id]['buy_prices']) != 0:
			if not str(time_now) in market_cache[ item_id ]['buy_times']:
				market_cache[ item_id ]['buy_times'].append( str(time_now) )
				market_cache[ item_id ]['buy_prices'].append( max(current_prices[item_id]['buy_prices']) )
		if len(current_prices[item_id]['sell_prices']) != 0:
			if not str(time_now) in market_cache[ item_id ]['sell_times']:
				market_cache[ item_id ]['sell_times'].append( str(time_now) )
				market_cache[ item_id ]['sell_prices'].append( min(current_prices[item_id]['sell_prices']) )
	
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
