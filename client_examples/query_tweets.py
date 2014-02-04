from TweetBase.TweetCouch import TweetCouch
import couchdb.design


# Let's say you create a database called "tw_test" and fill it with tweets containing "pizza" with this command:
# python -m TweetBase.TweetBase -couchurl http://127.0.0.1:5984 -dbname tw_test -endpoint statuses/filter -parameters track=pizza


# You can iterate the tweets stored in the database using the "get_tweets" view.
tc = TweetCouch('tw_test', 'http://127.0.0.1:5984')
for row in tc.db.view('twitter/get_tweets'):
	print row
