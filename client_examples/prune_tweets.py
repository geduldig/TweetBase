from TwitterBase.TweetCouch import TweetCouch


DB_NAME = 'tw_test'
COUCH_URL = 'http://127.0.0.1:5984/'


try:
	storage = TweetCouch(DB_NAME, COUCH_URL)
	storage.compact()

	print('TWEETS: %s' % storage.tweet_count())
	print('USERS: %s' % storage.user_count())
	storage.prune_tweets(storage.tweet_count() - 10)
except Exception as e:
	print('***ERROR: ' + str(e))
