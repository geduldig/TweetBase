var tweetbase = (function ($, options) {

	options = options || {};

	var my = {};
	my.server = options.server || '127.0.0.1';
	my.database = options.database || 'tw_test';
	my.live = options.live || true;
	my.max_old_tweets = options.max_old_tweets || 10;
	my.update_interval = options.update_interval || 3000;
	my.display_interval = options.display_interval || 300;
	my.updateCallback = options.updateCallback || function(item) { console.log(item) };
 
	COUCH_VIEW_PATH = 'http://' + my.server + ':5984/' + my.database + '/_design/twitter/_view/';
	DB_GETTWEETS = COUCH_VIEW_PATH + 'get_tweets';
	DB_GETUSERS = COUCH_VIEW_PATH + 'get_users';
	DB_GETCOUNT = COUCH_VIEW_PATH + 'count_type?group=true&group_level=1&startkey=["TWITTER_STATUS"]&endkey=["TWITTER_STATUS",{}]';

	last_id = null;

	my.startFeed = function() {
		my.getCount(function(count) { 
			var nskip = Math.max(0, count - my.max_old_tweets);
			my.getTweets({ skip:nskip });
		});
	};

	my.getCount = function(callback) {
		queryDatabase(DB_GETCOUNT, null, function(data) {
			if (data.rows != null && data.rows.length == 1) {
				count = data.rows[0].value;
				callback(count);
			}
		});
	};

	my.getTweets = function(params) {
		queryDatabase(DB_GETTWEETS, params, function(data) {
			if (data.rows != null && data.rows.length > 0) {
				last_id = data.rows[data.rows.length-1].key;
				displayTweets(data.rows, my.updateCallback);
			}
			setTimeout(function() { my.getTweets({ startkey:'"'+incrID(last_id)+'"' }); }, my.update_interval);
		});
	};
 
	my.getTweetByID = function(id, callback) {
		queryDatabase(DB_GETTWEETS, {key:id}, function(data) {
			if (data.rows != null && data.rows.length > 0) 
				callback(data.rows[0].value);
		});
	};

	my.getUser = function(status, callback) {
		queryDatabase(DB_GETUSERS, { key:'"'+status.user_id+'"' }, function(data) {
			if (data.rows != null && data.rows.length == 1) {
				user = data.rows[0].value;
				callback(status, user);
			}
		});
	};

	function queryDatabase(view, params, callback) {
		$.ajax({
			url: view,
			data: params,
			dataType: 'jsonp',
			success: callback,
			error: function(status) {
				error(JSON.stringify(status));
			}
		});
	};

	function displayTweets(rows, callback) {
		if (rows.length > 0) {
			var tw = rows.pop().value;
			setTimeout(function() {
				my.getUser(tw, function(status, user) {
					callback({'status':status, 'user':user});
				});
				displayTweets(rows, callback);
			}, my.display_interval);
		}
	}

	function incrID(id) {
		// INCREMENT STRING REPRESENTATION OF 64-BIT INTEGER
		var digits = id.toString().split('');
		var i = digits.length - 1;
		while (digits[i] == 9 && i > 0) {      
			digits[i] = 0;
			i--;
		}
		digits[i] = 1 + parseInt(digits[i]);
		return digits.join('');
	}
	
	function error(msg) {
		alert('tweetbase error: ' + msg);
	}

	return my;
});
