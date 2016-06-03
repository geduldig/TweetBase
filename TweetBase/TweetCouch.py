import couchdb
from couchdb.design import ViewDefinition


class TweetCouch(object):
	def __init__(self, dbname, url=None):
		try:
			self.server = couchdb.Server(url=url)
			self.db = self.server.create(dbname)
			self._create_views()
		except couchdb.http.PreconditionFailed:
			self.db = self.server[dbname]

	def _create_views(self):
		# twitter/count_type
		count_type_map = 'function(doc) { emit([doc.type, doc.id], 1); }'
		count_type_reduce = 'function(keys, values) { return sum(values); }'
		view = ViewDefinition('twitter', 'count_type', count_type_map, reduce_fun=count_type_reduce)
		view.sync(self.db)
		
		# The unique key for each tweet is doc.id.  The key (a 64-bit long) is represented as a string because 
		# the largest JavaScript long is 2^53.
		# A problem arises because keys are sorted as strings and a doc.id may have fewer digits but a larger
		# leading digit.  So, it is sorted in the wrong order.
		# The solutions is to zero-pad the doc.id to fill 19 digits.  (The max 64-bit long - 2^63 - has 19 digits.)
		# That is why we emit the doc.id key as ("0000000000000000000"+doc.id).slice(-19).

		# twitter/get_tweets
		get_tweets = 'function(doc) { if (doc.type == "TWITTER_STATUS") emit(("0000000000000000000"+doc.id).slice(-19), doc); }'
		view = ViewDefinition('twitter', 'get_tweets', get_tweets)
		view.sync(self.db)

		# twitter/get_tweets_by_date (sort by date and tweet id)
		get_tweets_by_date = 'function(doc) { if (doc.type == "TWITTER_STATUS") emit((new Date(doc.created_at).getTime())+"-"+("0000000000000000000"+doc.id).slice(-19), doc); }'
		view = ViewDefinition('twitter', 'get_tweets_by_date', get_tweets_by_date)
		view.sync(self.db)

		# twitter/get_users
		get_users = 'function(doc) { if (doc.type == "TWITTER_USER") emit(doc.id, doc); }'
		view = ViewDefinition('twitter', 'get_users', get_users)
		view.sync(self.db)

	def tweet_count(self):
		for row in self.db.view('twitter/count_type', group=True, group_level=1,
		                        startkey=['TWITTER_STATUS'], endkey=['TWITTER_STATUS',{}]):
        		return row['value']
		return -1

	def user_count(self):
		for row in self.db.view('twitter/count_type', group=True, group_level=1,
		                        startkey=['TWITTER_USER'], endkey=['TWITTER_USER',{}]):
        		return row['value']
		return -1

	def prune_tweets(self, count):
		for row in self.db.view('twitter/get_tweets', limit=count, descending=False):
			self.db.delete(self.db[row.id])

	def compact(self):
		self.db.compact()
		self.db.cleanup()

	def delete(self):
		self.server.delete(self.db.name)

	def _new_tweet_doc(self, tw, id_time):
		return {
			'_id':                     tw['id_str'],
			'type':                    'TWITTER_STATUS',
			'coordinates':             tw['coordinates']['coordinates'] if tw['coordinates'] else None,
			'created_at':              tw['created_at'],
			'entities':                tw['entities'],
			'favorite_count':          tw['favorite_count'],
			'id':                      tw['id_str'],
			'in_reply_to_screen_name': tw['in_reply_to_screen_name'],
			'in_reply_to_status_id':   tw['in_reply_to_status_id'],
			'in_reply_to_user_id':     tw['in_reply_to_user_id'],
			'lang':                    tw['lang'],
			'place':                   tw['place'],
			'retweet_count':           tw['retweet_count'],
			'retweeted_status_id':     tw['retweeted_status']['id_str'] if 'retweeted_status' in tw else None, # PARENT
			'retweeted_by_list':       [], # extra field containing id's of CHILD tweets
			'source':                  tw['source'],
			'text':                    tw['text'],
			'truncated':               tw['truncated'],
			'user_id':                 tw['user']['id_str']
		}

	def _new_user_doc(self, user):
		return {
			'_id':                     user['id_str'],
			'type':                    'TWITTER_USER',
			'created_at':              user['created_at'],
			'description':             user['description'],
			'entities':                user['entities'] if 'entities' in user else None,
			'favourites_count':        user['favourites_count'],
			'followers_count':         user['followers_count'],
			'friends_count':           user['friends_count'],
			'geo_enabled':             user['geo_enabled'],
			'id':                      user['id_str'],
			'lang':                    user['lang'],
			'location':                user['location'],
			'name':                    user['name'],
			'profile_image_url':       user['profile_image_url'],
			'screen_name':             user['screen_name'],
			'statuses_count':          user['statuses_count'],
			'url':                     user['url'],
			'utc_offset':              user['utc_offset'],
			'verified':                user['verified']
		}

	# def save_tweet(self, tw, retweeted_by_id=None, save_retweeted_status=True, id_time=False):
	# 	doc = self.db.get(tw['id_str'])
	# 	if not doc:
	# 		if save_retweeted_status and 'retweeted_status' in tw:
	# 			self.save_tweet(tw['retweeted_status'], tw['id_str'])
	# 			# NEED TO UPDATE retweet_count OF tw['retweeted_status'] ???
	# 		self.save_user(tw['user'])
	# 		doc = self._new_tweet_doc(tw, id_time)
	# 	if retweeted_by_id:
	# 		doc['retweeted_by_list'].append(retweeted_by_id)
	# 	self.db.save(doc)
		
	def save_tweet(self, tw, retweeted_by_id=None, save_retweeted_status=True, raw=False):
		if raw:
			tw['_id'] = tw['id_str']
			tw['type'] = 'TWITTER_STATUS'
			self.db.save(tw)
		else:
			# SAVE TWEET W/O USER FIELD, AND SAVE USER AS A SEPARATE RECORD
			if save_retweeted_status and 'retweeted_status' in tw:
				self.save_tweet(tw['retweeted_status'], tw['id_str'])
			self.save_user(tw['user'])
			doc = self._new_tweet_doc(tw)
			if retweeted_by_id:
				doc['retweeted_by_list'].append(retweeted_by_id)
			self.db.save(doc)

	def save_user(self, user):
		if not self.db.get(user['id_str']):
			doc = self._new_user_doc(user)
			self.db.save(doc)
