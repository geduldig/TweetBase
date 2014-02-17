import argparse
import codecs
import os
import sys
from .TweetCouch import TweetCouch
from TwitterAPI.TwitterOAuth import TwitterOAuth
from TwitterAPI.TwitterAPI import TwitterAPI
from TwitterGeoPics.Geocoder import Geocoder


GEO = Geocoder()


def to_dict(param_list):
	"""Convert a list of key=value to dict[key]=value"""			
	if param_list:
		return {name: value for (name, value) in [param.split('=') for param in param_list]}
	else:
		return None
		

def update_geocode(status, log):
	"""Get geocode from tweet's 'coordinates' field (unlikely) or from tweet's location and Google."""
	if not GEO.quota_exceeded:
		try:
			geocode = GEO.geocode_tweet(status)
			if geocode[0]:
				log.write('GEOCODER: %s %s,%s\n' % geocode)
				location, latitude, longitude = geocode
				status['user']['location'] = location
				status['coordinates'] = {'coordinates':[longitude, latitude]}
			else:
				log.write('LOCATION: %s\n' % status['user']['location'])
		except Exception as e:
			if GEO.quota_exceeded:
				log.write('GEOCODER QUOTA EXCEEDED: %s\n' % GEO.count_request)


def run(log):
	parser = argparse.ArgumentParser(description='Request any Twitter Streaming or REST API endpoint')
	parser.add_argument('-couchurl', metavar='COUCH_URL', type=str, help='complete url for couchdb')
	parser.add_argument('-dbname', metavar='DB_NAME', type=str, help='database name')
	parser.add_argument('-oauth', metavar='FILE_NAME', type=str, help='file containing OAuth credentials')
	parser.add_argument('-endpoint', metavar='ENDPOINT', type=str, help='Twitter endpoint', required=True)
	parser.add_argument('-parameters', metavar='NAME_VALUE', type=str, help='parameter NAME=VALUE', nargs='+')

	args = parser.parse_args()
	params = to_dict(args.parameters)

	o = TwitterOAuth.read_file(args.oauth)
	api = TwitterAPI(o.consumer_key, o.consumer_secret, o.access_token_key, o.access_token_secret)

	storage = TweetCouch(args.dbname, args.couchurl)
	storage.compact()

	while True:
		try:
			for item in api.request(args.endpoint, params):
				if 'message' in item:
					log.write('ERROR %s: %s\n' % (item['code'], item['message']))
				elif 'text' in item:
					if item['lang'] == 'en':
						log.write('\n%s -- %s\n' % (item['user']['screen_name'], item['text']))
						if item['coordinates']:
							log.write('COORDINATES: %s\n' % item['coordinates']['coordinates'])
						elif item['user']['location']:
							update_geocode(item, log)
						storage.save_tweet(item)
			if args.endpoint == 'statuses/user_timeline':
				log.write('*** Got one page of user timeline\n')
				break
						
		except KeyboardInterrupt:
			log.write('\nTerminated by user\n')
			break
		
		except Exception as e:
			log.write('*** STOPPED %s\n' % str(e))


if __name__ == '__main__':
	try:    # python 3
		sys.stdout = codecs.getwriter('utf8')(sys.stdout.buffer)
	except: # python 2
		sys.stdout = codecs.getwriter('utf8')(sys.stdout)
	
	try:
		run(sys.stdout)
	except Exception as e:
		print(str(e))