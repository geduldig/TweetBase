# EXAMPLE COMMAND LINE ARGS
#-couchurl http://127.0.0.1:5984/ -dbname tw_test -oauth credentials.txt -endpoint statuses/filter -parameters track=zzz


import argparse
import codecs
import shlex
import sys
from .TweetCouch import TweetCouch
from TwitterAPI import *
from .TweetGeocoder import update_geocode, geocoder_stats


# SET UP LOGGING TO FILE AND TO CONSOLE
import logging
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("tzwhere").setLevel(logging.WARNING)
formatter = logging.Formatter('%(levelname)s %(asctime)s %(message)s',
                              '%m/%d/%Y %I:%M:%S %p')
fh = logging.FileHandler('Collector.log')
fh.setFormatter(formatter)
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(fh)
logger.addHandler(ch)


def to_dict(param_list):
	"""Convert a list of key=value to dict[key]=value"""			
	if param_list:
		return {name: value for (name, value) in [param.split('=') for param in param_list]}
	else:
		return None


def prune_database(storage, prune_limit):
	"""Remove oldest CouchDB documents to limit database size."""
	tweet_count = storage.tweet_count()
	if tweet_count > 2*prune_limit:
		prune_count = tweet_count - prune_limit
		logging.info('PRUNING %s tweets...' % prune_count)
		storage.prune_tweets(prune_count)
		storage.compact()
		

def process_tweet(item, args, storage):
	"""Do something with a downloaded tweet."""
	if args.google_geocode:
		try:
			update_geocode(item)
		except Exception as e:
			logging.warning(str(e))
	if args.only_coords and not item['coordinates']:
		return
	sys.stdout.write('%s -- %d\n' % (item['created_at'], item['id']))
	try:
		storage.save_tweet(item, 
		                   save_retweeted_status=args.retweets, 
		                   raw=args.save_raw)
	except Exception as e:
		logging.error(str(e))
		logging.error(item)
	if args.prune:
		prune_database(storage, args.prune)

		
def page_collector(api, args, storage):
	"""Pull tweets from REST pages."""
	total_tweets = 0
	params = to_dict(args.parameters)
	wait = 5 if args.oauth_version == 1 else 2
	wait *= 1.01 # wait a little extra
	iterator = TwitterRestPager(api, args.endpoint, params).get_iterator(wait=wait)
	try:
		for item in iterator:
			if 'text' in item:
				total_tweets += 1
				process_tweet(item, args, storage)
			elif 'message' in item:
				# must terminate
				logging.error(item)
				break
	finally:
		logging.info('Tweet count = %d' % total_tweets)


def stream_collector(api, args, storage):
	"""Pull tweets from stream."""
	total_tweets = 0
	total_skipped = 0
	last_skipped = 0
	params = to_dict(args.parameters)
	while True:
		try:
			iterator = api.request(args.endpoint, params).get_iterator()
			for item in iterator:
				if 'text' in item:
					total_tweets += 1
					process_tweet(item, args, storage)
				elif 'limit' in item:
					last_skipped = item['limit']['track']
					logging.info('SKIPPED %s tweets' % last_skipped)
				elif 'warning' in item:
					logging.warning(item['warning'])
				elif 'disconnect' in item:
					event = item['disconnect']
					if event['code'] in [2,5,6,7]:
						# streaming connection rejected
						raise Exception(event)
					logging.info('RE-CONNECTING: %s' % event)
					break
		except TwitterRequestError as e:
			if e.status_code < 500:
				raise
		except TwitterConnectionError:
			pass
		finally:
			total_skipped += last_skipped
			last_skipped = 0
			logging.info('Tweet total count = %d, Tweets skipped = %d' % (total_tweets,total_skipped))
			logging.info(geocoder_stats())


def run():
	parser = argparse.ArgumentParser(description='Request any Twitter Streaming or REST API endpoint')
	parser.add_argument('-settings', metavar='SETTINGS_FILE', type=str, help='file containing command line settings')
	parser.add_argument('-couchurl', metavar='COUCH_URL', type=str, help='complete url for couchdb', default='http://127.0.0.1:5984')
	parser.add_argument('-dbname', metavar='DB_NAME', type=str, help='database name')
	parser.add_argument('-prune', metavar='PRUNE_COUNT', type=int, help='remove oldest tweets when threshhold reached')
	parser.add_argument('-oauth', metavar='FILE_NAME', type=str, help='file containing OAuth credentials')
	parser.add_argument('-oauth_version', metavar='OAUTH_VERSION', type=int, help='oAuth version (1 or 2)', default=1) 
	parser.add_argument('-endpoint', metavar='ENDPOINT', type=str, help='Twitter endpoint')
	parser.add_argument('-parameters', metavar='NAME_VALUE', type=str, help='Twitter parameter NAME=VALUE', nargs='+')
	parser.add_argument('-pager', action='store_true', help='page from REST API until exhausted')
	parser.add_argument('-google_geocode', action='store_true', help='lookup geocode from Google')
	parser.add_argument('-only_coords', action='store_true', help='throw out tweets that do not have coordinates')
	parser.add_argument('-retweets', action='store_true', help='save retweeted tweets to database')
	parser.add_argument('-save_raw', action='store_true', help='save raw tweets to database')

	args = parser.parse_args()
	if args.settings:
		# optionally (no pun intended), read args from a settings file instead of from command line
		with open(args.settings) as f:
			args = parser.parse_args(shlex.split(f.read()))	
	sys.stdout.write('Database: %s\nTwitter: %s %s\n' % (args.dbname, args.endpoint, args.parameters))

	# twitter authentication
	o = TwitterOAuth.read_file(args.oauth)
	oauth_version = 'oAuth%d' % args.oauth_version
	api = TwitterAPI(o.consumer_key, o.consumer_secret, 
	                 o.access_token_key, o.access_token_secret,
	                 auth_type=oauth_version)
	
	# initialize database repository for tweets
	storage = TweetCouch(args.dbname, args.couchurl)

	try:
		if args.pager:
			page_collector(api, args, storage)
		else:
			stream_collector(api, args, storage)
	except KeyboardInterrupt:
		logging.info('TERMINATED BY USER')
	except Exception as e:
		logging.error('STOPPED: %s' % e)
	

if __name__ == '__main__':
	try:    # python 3
		sys.stdout = codecs.getwriter('utf8')(sys.stdout.buffer)
	except: # python 2
		sys.stdout = codecs.getwriter('utf8')(sys.stdout)
	
	run()
