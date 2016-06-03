import pytz
from datetime import datetime
from TwitterGeoPics.Geocoder import Geocoder
from tzwhere import tzwhere


GEO = Geocoder()
TZ = tzwhere.tzwhere()


def compare_timezone(latitude, longitude, utc_offset):
	"""The trick: Does longitude fall within timezone?"""
	try:
		tz_name =  TZ.tzNameAt(latitude, longitude)
		if not tz_name:
			return False
		military = datetime.now(pytz.timezone(tz_name)).strftime('%z')
		hours = int(military[:(len(military)-2)])
		minutes = int(military[-2:])
		seconds = (abs(hours)*60 + minutes)*60
	except Exception as e:
		# logging.error('COMPARE TIME ZONE ERROR: %s' % e)
		return False
	test = abs(seconds - abs(utc_offset)) <= 3600 
	#strict_test = abs(hours/abs(hours)*seconds - utc_offset) <= 3600
	return test


def update_geocode(status):
	"""Get geocode from tweet's 'coordinates' field (unlikely) or from tweet's location and Google."""
	if 'geocoder' in status:
		return

	if GEO.quota_exceeded:
		elapsed = datetime.now() - GEO.quota_exceeded_at
		if elapsed.days > 0:
			GEO.quota_exceeded = False
			GEO.quota_exceeded_at = None

	coords = status['coordinates']['coordinates'] if status['coordinates'] else None
	loc = status['user']['location'] if status['user']['location'] else None
	utc = status['user']['utc_offset'] if status['user']['utc_offset'] else None
	place = status['place']

	if coords:
		status['geocoder'] = 'coordinates'
	elif place:
		bounding_box = place['bounding_box']['coordinates'][0];
		coords = [
			(bounding_box[0][0] + bounding_box[1][0]) / 2.,
			(bounding_box[1][1] + bounding_box[2][1]) / 2.
		]
		status['geocoder'] = 'place'
	elif not coords and loc and utc and not GEO.quota_exceeded:
		try:
			geocode = GEO.geocode_tweet(status)
			if geocode[0]:
				location, latitude, longitude = geocode
				if compare_timezone(latitude, longitude, utc):
					# status['user']['location'] = '* ' + location
					status['coordinates'] = {'coordinates':[longitude, latitude]}
					status['geocoder'] = 'utc'
				else:
					status['geocoder'] = 'none'
			else:
				status['geocoder'] = 'none'
		except Exception as e:
			if hasattr(e, 'status') and e.status == 'ZERO_RESULTS':
				status['geocoder'] = 'none'
			elif GEO.quota_exceeded:
				# logging.error('GEOCODER QUOTA EXCEEDED: %s' % GEO.count_request)
				raise Exception('GEOCODER QUOTA EXCEEDED: %s' % GEO.count_request)
	else:
		status['geocoder'] = 'none'

	if 'geocoder' in status:
		print('==== GEOCODER: %s' % status['geocoder'])


def geocoder_stats():
	return GEO.print_stats()
