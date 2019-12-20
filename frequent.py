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
	

def prices_are_about_same( price1, price2, price3 ):
	if price1 == price2 == price3:
		return True
	elif price1 == 0 or price2 == 0 or price3 == 0:
		return False
	
	treshold = 0.01
	diff1 = abs( 1 - price1/price2) < treshold
	diff2 = abs( 1 - price2/price3) < treshold
	
	if diff1 and diff2:
		return True
	return False
	
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

	# Check if server is on
	esi_calling.check_server_status()
	
	esi_response = import_orders( 10000002 )
	
	
	#Process market orders
	print(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), '- Processing market orders...')
	
	current_prices = {}
	
	#Merge all prices to a json
	for market_order in esi_response[0]:
		#type id = market_order['type_id']
		if not str(market_order['type_id']) in current_prices:
			current_prices[str(market_order['type_id'])] = { 'buy_prices':[0], 'sell_prices':[]}
		
		
		if market_order['is_buy_order'] == True:
			current_prices[str(market_order['type_id'])]['buy_prices'].append( market_order['price'] )
		else:
			current_prices[str(market_order['type_id'])]['sell_prices'].append( market_order['price'] )
				
	#Find the current dominating prices and add them to the cache
	time_now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
	
	for item_id in current_prices:
		item_id = str(item_id)
		
		
		if not item_id in market_cache:
			#New item. Add entry for it in cache.
			market_cache[ item_id ] = {'times':[], 'buy_prices':[], 'sell_prices':[]}
		
		current_buy = max( current_prices[item_id]['buy_prices'] )
		
		if len( current_prices[item_id]['sell_prices'] ) != 0:
			current_sell = min( current_prices[item_id]['sell_prices'] )
		else:
			current_sell = 0
		
		
		duplicate = False
		if len( market_cache[ item_id ]['buy_prices'] ) > 1:
			previous_buy = market_cache[ item_id ]['buy_prices'][-1]
			previous_buy_2 = market_cache[ item_id ]['buy_prices'][-2]
			
			previous_sell = market_cache[ item_id ]['sell_prices'][-1]
			previous_sell_2 = market_cache[ item_id ]['sell_prices'][-2]
			
			duplicate_buy = prices_are_about_same( current_buy, previous_buy, previous_buy_2 )
			duplicate_sell = prices_are_about_same( current_sell, previous_sell, previous_sell_2 )
			
			if duplicate_buy and duplicate_sell:
				duplicate = True
		
		if duplicate:
			market_cache[ item_id ]['times'][-1] = time_now
			market_cache[ item_id ]['sell_prices'][-1] = current_sell
			market_cache[ item_id ]['buy_prices'][-1] = current_buy
		else:
			market_cache[ item_id ]['times'].append( time_now )
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
	
	print(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), '- Fetching new orders in',round(time_to_refetch)+4 ,'seconds')
	time.sleep( round(time_to_refetch)+4 )
