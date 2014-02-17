TweetBase
=========
[![Downloads](https://pypip.in/d/TweetBase/badge.png)](https://crate.io/packages/TweetBase)
[![Downloads](https://pypip.in/v/TweetBase/badge.png)](https://crate.io/packages/TweetBase) 

Download tweets into a CouchDB database

Features
--------

* Flexible: works with any Twitter endpoint (REST API or Streaming API).
* Geocode lookup for the Twitter user location using Google's Map geocode service.
* Uses CouchDB for storage.

Installation
------------

* Install Python packages TweetBase and dependencies:

		pip install TweetBase

* Install [CouchDB](http://couchdb.apache.org)

Usage
-----

The first time the script is executed the database is created.  For example, to store tweets in a database called "tw_test" and to stream tweets that contain "pizza", run this command:

	python -m TweetBase.TweetBase 
		-couchurl http://127.0.0.1:5984
		-dbname tw_test 
		-endpoint statuses/filter 
		-parameters track=pizza
		
The TweetBase script downloads tweets and stores them into the specified database.  Tweet meta data is stored separately from the user meta data.  This is done so user data is only stored once in the database.  The two types of records are differentiated by the "type" field, which is either TWITTER\_STATUS or TWITTER\_USER.  

The same time that a new database is created, some views are also created.  These views are:

* get\_tweets
* get\_users
* count\_type

In the client_examples folder you will find a Python example and a JavaScript example that uses these views to retrieve data.

Dependencies
------------
* TwitterAPI
* TwitterGeoPics
* couchdb
