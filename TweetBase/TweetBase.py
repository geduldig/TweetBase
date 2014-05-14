import argparse
import codecs
import shlex
import sys
from .TweetCouch import TweetCouch
from TwitterAPI.TwitterOAuth import TwitterOAuth
from TwitterAPI.TwitterAPI import TwitterAPI
from TwitterGeoPics.Geocoder import Geocoder


# EXAMPLE SETTINGS
#-couchurl http://127.0.0.1:5984/ -dbname tw_test -oauth credentials.txt -endpoint statuses/filter -parameters track=zzz


GEO = Geocoder()


def to_dict(param_list):
	"""Convert a list of key=value to dict[key]=value"""			
	if param_list:
		return {name: value for (name, value) in [param.split('=') for param in param_list]}
	else:
		return None
		

def update_geocode(status, log):
	"""Get geocode from tweet's 'coordinates' field (unlikely) or from tweet's location and Google."""
	if status['coordinates']:
		log.write('COORDINATES: %s\n' % status['coordinates']['coordinates'])
	if status['place']:
		log.write('PLACE: %s\n' % status['place']['full_name'])
	if status['user']['location']:
		log.write('LOCATION: %s\n' % status['user']['location'])

	if not GEO.quota_exceeded:
		try:
			geocode = GEO.geocode_tweet(status)
			if geocode[0]:
				log.write('GEOCODER: %s %s,%s\n' % geocode)
				location, latitude, longitude = geocode
				status['user']['location'] = location
				status['coordinates'] = {'coordinates':[longitude, latitude]}
		except Exception as e:
			if GEO.quota_exceeded:
				log.write('GEOCODER QUOTA EXCEEDED: %s\n' % GEO.count_request)


def run(log):
	parser = argparse.ArgumentParser(description='Request any Twitter Streaming or REST API endpoint')
	parser.add_argument('-settings', metavar='SETTINGS_FILE', type=str, help='file containing command line settings')
	parser.add_argument('-couchurl', metavar='COUCH_URL', type=str, help='complete url for couchdb')
	parser.add_argument('-dbname', metavar='DB_NAME', type=str, help='database name')
	parser.add_argument('-oauth', metavar='FILE_NAME', type=str, help='file containing OAuth credentials')
	parser.add_argument('-endpoint', metavar='ENDPOINT', type=str, help='Twitter endpoint')
	parser.add_argument('-parameters', metavar='NAME_VALUE', type=str, help='Twitter parameter NAME=VALUE', nargs='+')
	parser.add_argument('-prune', metavar='PRUNE_COUNT', type=int, help='remove oldest tweets when threshhold reached')
	parser.add_argument('-no_retweets', action='store_true', help='do not save retweeted tweets to database')

	args = parser.parse_args()
	if (args.settings):
		# read args from a settings file
		with open(args.settings) as f:
			args = parser.parse_args(shlex.split(f.read()))	
			log.write('DB: %s, %s %s\n' % (args.dbname, args.endpoint, args.parameters))

	params = to_dict(args.parameters)
	o = TwitterOAuth.read_file(args.oauth)
	api = TwitterAPI(o.consumer_key, o.consumer_secret, o.access_token_key, o.access_token_secret)

	storage = TweetCouch(args.dbname, args.couchurl)

	while True:
		try:
			for item in api.request(args.endpoint, params):
				if 'message' in item:
					log.write('ERROR %s: %s\n' % (item['code'], item['message']))
				elif 'text' in item:
					log.write('\n%s -- %s\n' % (item['user']['screen_name'], item['text']))
					update_geocode(item, log)
					storage.save_tweet(item, save_retweeted_status=not args.no_retweets)
					tweet_count = storage.tweet_count()
					if args.prune and tweet_count > 2*args.prune:
						prune_count = tweet_count - args.prune
						log.write('*** PRUNING %s tweets...\n' % prune_count)
						storage.prune_tweets(prune_count)
						storage.compact()
				elif 'limit' in item:
					log.write('*** SKIPPED %s tweets' % item['limit'])
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
