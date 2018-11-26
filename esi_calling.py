#Esi calling 1.2


import json
import time
import base64
import random
import sys
import grequests
import webbrowser

from datetime import datetime
from datetime import timedelta




scopes = ''
user_agent = 'ESI calling script by Hirmuolio'
config = {}


def load_config(loaded_config):
	global config
	try:
		client_id = loaded_config['client_id']
		client_secret = loaded_config['client_secret']
		config = loaded_config
	except KeyError:
		#Config found but no wanted content
		print('  no client ID or secret found. \nRegister at https://developers.eveonline.com/applications to get them')
		
		client_id = input("Give your client ID: ")
		client_secret = input("Give your client secret: ")
		config = {"client_id":client_id, "client_secret":client_secret, 'authorizations':{}}
	return config

def set_user_agent(new_user_agent):
	global user_agent
	user_agent = new_user_agent
	

def error_handling(esi_response, number_of_attempts, job = '', authorized = False, strict = False):
	#Call this function to check the response for errors
	#Struct = True will onnly accept 200, 204 and 304
	#Returns False if everything is OK
	#Return True if something is wrong
	
	
	if esi_response.status_code in [200, 204, 304]:
			#[200, 204, 304] = All OK
			return False
	
	if esi_response.status_code in [404,  400]:
			#[404,  400] = not found or user error. Still OK unless strict
			if strict == False:
				return False
	
	
	#Some arbitrary maximum try ammount
	if number_of_attempts == 20:
		print('  There has been 20 failed attemts to call ESI. Something may be wrong.')
		input('  Press enter to continue trying...')
		number_of_attempts = 1
	
	if job != '':
		job_description = 'Failed to ' + job #+ '. Payload: ' + payload
	
	print(' ', datetime.utcnow().strftime('%H:%M:%S'), job_description+'. Error',esi_response.status_code, end="")
	
	#Some errors have no description so try to print it
	try:
		print(' -', esi_response.json()['error'])
	except:
		#No error description from ESI
		print('')
	
	
	if esi_response.status_code in [404,  400]:
		#[404,  400] = not found or user error. Not ok for strict
		print('  Fatal user error. Try to be better next time')
		return True
	elif esi_response.status_code == 420:
		#error limit reached. Wait until reset and try again.
		time.sleep(esi_response.headers['x-esi-error-limit-reset']+1)
	elif esi_response.status_code in [401, 403]:
		if authorized == True:
			input(' Press enter to continue trying (won\'t work. Just close the script and redo login or client ID/secret)...')
			return True
		else:
			#This was never meant to work. Everything is OK
			return False
	else:
		#500 = internal server error (downtime?)
		#502 = bad gateway
		#503 = service unavailable
		#Other errors
		#Lets just wait a sec and try again and hope for best
		time_to_wait = (2 ** number_of_attempts) + (random.randint(0, 1000) / 1000)
		print('  Retrying in', time_to_wait, 'second...')
		time.sleep(time_to_wait)
		return True


def logging_in(scopes):
	global config
	
	number_of_attempts = 1
	client_id = config['client_id']
	client_secret = config['client_secret']
	
	login_url = 'https://login.eveonline.com/oauth/authorize?response_type=code&redirect_uri=http://localhost/oauth-callback&client_id='+client_id+'&scope='+scopes

	webbrowser.open(login_url, new=0, autoraise=True)

	authentication_code = input("Give your authentication code: ")
	
	combo = base64.b64encode(bytes( client_id+':'+client_secret, 'utf-8')).decode("utf-8")
	authentication_url = "https://login.eveonline.com/oauth/token"
	
	esi_response = grequests.post(authentication_url, headers =  {"Authorization":"Basic "+combo, "User-Agent":user_agent}, data = {"grant_type": "authorization_code", "code": authentication_code} ).send().response
	
	if error_handling(esi_response, number_of_attempts, job = 'log in', strict = True) == False:
		tokens = {}
		
		tokens['refresh_token'] = esi_response.json()['refresh_token']
		tokens['access_token'] = esi_response.json()['access_token']
		tokens['expiry_time'] = str( datetime.utcnow() + timedelta(0,esi_response.json()['expires_in']) )
		
		token_info = get_token_info(tokens)
		
		tokens['character_name'] = token_info['character_name']
		tokens['character_id'] = token_info['character_id']
		tokens['scopes'] = token_info['scopes']
		
		config['authorizations'][tokens['character_id']] = tokens
		
	else:
		print('  Failed to log in.')
	
	return config
	
def check_tokens(authorizer_id):
	#Check if access token still good
	#If access token too old or doesn't exist generate new access token
	
	#refresh_token = tokens['refresh_token']
	#access_token = tokens['access_token'] (optional)
	#expiry_time = tokens['expiry_time'] (optional. Should exist with access token)
	global config
	
	try:
		tokens = config['authorizations'][str(authorizer_id)]
	except:
		print('  Error: This character has no authorization. Something is very broken.')
	
	number_of_attempts = 1
	
	
	#Check if token is valid
	#Needs to be done like this since the expiry time may or may not exist
	if 'expiry_time' in tokens:
		if datetime.utcnow() < datetime.strptime(tokens['expiry_time'], '%Y-%m-%d %H:%M:%S.%f'):
			return
	
	client_id = config['client_id']
	client_secret = config['client_secret']
	
	#No "expiry time" or the token has expired already
	#No valid access token. Make new.
	refresh_url = 'https://login.eveonline.com/oauth/token'
	combo = base64.b64encode(bytes( client_id+':'+client_secret, 'utf-8')).decode("utf-8")
	
	trying = True
	while trying == True:
		esi_response = grequests.post(refresh_url, headers =  {"Authorization":"Basic "+combo, "User-Agent":user_agent}, data = {"grant_type": "refresh_token", "refresh_token": tokens['refresh_token']} ).send().response
		
		trying = error_handling(esi_response, number_of_attempts, job = 'refresh tokens', strict = True)
		number_of_attempts = number_of_attempts + 1
	
	config['authorizations'][str(authorizer_id)]['refresh_token']	= esi_response.json()['refresh_token']
	config['authorizations'][str(authorizer_id)]['access_token'] = esi_response.json()['access_token']
	config['authorizations'][str(authorizer_id)]['expiry_time'] = str( datetime.utcnow() + timedelta(0,esi_response.json()['expires_in']) )
		

def get_token_info(tokens):
	#Uses the access token to get various info
	#character ID
	#character name
	#expiration time (not sure on format)
	#scopes
	#token type (char/corp)
	
	url = 'https://login.eveonline.com/oauth/verify'
	
	trying = True
	number_of_attempts = 1
	
	while trying == True:
		esi_response = grequests.get(url, headers =  {"Authorization":"Bearer "+tokens['access_token'], "User-Agent":user_agent}).send().response
		
		trying = error_handling(esi_response, number_of_attempts, job = 'get token info')
		number_of_attempts = number_of_attempts + 1

	token_info = {}
	token_info['character_name'] = esi_response.json()['CharacterName']
	token_info['character_id'] = esi_response.json()['CharacterID']	
	token_info['expiration'] = esi_response.json()['ExpiresOn']	
	token_info['scopes'] = esi_response.json()['Scopes']	
	token_info['token_type'] = esi_response.json()['TokenType']	
	
	return token_info

	


def call_esi(scope, url_parameter = '', etag = None, authorizer_id = None, datasource = 'tranquility', calltype='get', job = ''):
	#scope = url part. Mark the spot of parameter with {par}
	#url_parameter = parameter that goes into the url
	#etag = TODO
	#authorizer_id = ID of the char whose authorization will be used
	
	#datasource. Default TQ
	#calltype = get, post or delete. Default get
	#job = string telling what is being done. Is displayed on error message.
	
	number_of_attempts = 0
	
	#Build the url to call to
	#Also replace // with / to make things easier
	url = 'https://' + ('esi.evetech.net'+scope+'/?datasource='+datasource).replace('{par}', str(url_parameter)).replace('//', '/')

	
	#print(url)
	
	#un-authorized / authorized
	if authorizer_id == None:
		headers = {"User-Agent":user_agent}
		authorized = False
	else:
		check_tokens(authorizer_id)
		tokens = config['authorizations'][str(authorizer_id)]
		headers =  {"Authorization":"Bearer "+tokens['access_token'], "User-Agent":user_agent}
		authorized = True
	
	trying = True
	
	#Uncomment this to see what is sent to CCP
	#url = 'https://esi.tech.ccp.is/v1/universe/regions/'
	#print('  url = ', url,'\nHeaders = ', headers)
	
	while trying == True:
		#Make the call based on calltype
		if calltype == 'get':
			esi_response = grequests.get(url, headers = headers).send().response
		elif calltype == 'post':
			esi_response = grequests.post(url, headers = headers).send().response
		elif calltype == 'delete':
			esi_response = grequests.delete(url, headers = headers).send().response
		
		
		trying = error_handling(esi_response, number_of_attempts, job, authorized)
		number_of_attempts = number_of_attempts + 1
	
	#Multipaged  calls
	#Returns array of all the responses
	#You need to remember to expect the responses in array for potentially paginated calls
	if 'X-Pages' in esi_response.headers:
		number_of_attempts = 0
		all_responses = []
		all_responses.append(esi_response)
		
		total_pages = int(esi_response.headers['X-Pages'])
		expires = esi_response.headers['expires']
		if total_pages > 1:
			print('  multipage response. Fetching ', total_pages, 'pages...')
		else:
			print('  multipaged but no extra pages')
		
		pages_left = total_pages - 1
		
		#print('Importing ', total_pages-pages_left, '/', total_pages, end='')

		reqs = []
		for page in range(2, total_pages + 1):

			req = grequests.get(url, headers = headers, params={'page': page})
			reqs.append(req)
			pages_left = pages_left - 1
			#print('\rImporting ', total_pages-pages_left, '/', total_pages, end='')
		
		rest_of_responses = grequests.map(reqs, size=10)
		
		#Check for errors. Keep doing this until no errors.
		#These should be all valid calls so error 5XX should be the only ones happening (hopefully)
		
		check_errors = True
		error_check_rounds = 0
		
		number_of_responses = len(rest_of_responses)
		print('  Checking for errors...')
		
		while check_errors:
			check_errors = False
			sleep_time = 0
			refetch_pages = []
			for index  in range(number_of_responses):
				try:
					if not rest_of_responses[index].status_code in [200, 204, 304, 404, 400]:
						check_errors = True
						refetch_pages.append(index+2)
						print('  Error -', rest_of_responses[index].status_code, '. Refetching page', index+2, '...')
						if rest_of_responses[index].status_code == 420:
							#error limit reached. Wait until reset and try again.
							#Not sure how well this error limiter works
							sleep_time = rest_of_responses[index].headers['x-esi-error-limit-reset']+1
				except:
					#The call failed completely
					check_errors = True
					print('  Error - failed call. Refetching page', index+2, '...')
					check_errors = True
					refetch_pages.append(index+2)
					
				
			if check_errors == True:
				if len(refetch_pages) > 10:
					print('Lots of errors. This may take a while')
				print('  Refetching ', len(refetch_pages), ' pages...')
				
				if sleep_time != 0:
					print('Error limited. Waiting', sleep_time, 'seconds')
					time.sleep(sleep_time)
				elif error_check_rounds > 1:
					sleep_time = (2 ** number_of_attempts) + (random.randint(0, 1000) / 1000)
					print('Waiting', sleep_time, 'seconds')
					time.sleep(sleep_time)
					
				
				for page in refetch_pages:
					esi_response = grequests.get(url, headers = headers, params={'page': page}).send().response
					rest_of_responses[page-2] = esi_response
				error_check_rounds = error_check_rounds + 1
					
		
		
		all_responses.extend(rest_of_responses)
		
		return all_responses

		
		
	return esi_response
	
	
	
	
	
