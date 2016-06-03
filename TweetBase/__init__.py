__title__ = 'TweetBase'
__version__ = '0.2.9'
__author__ = 'Jonas Geduldig'
__license__ = 'MIT'
__copyright__ = 'Copyright 2014 Jonas Geduldig'


try:
	from .TweetCouch import TweetCouch
except:
	pass


__all__ = [
	'TweetCouch'
]
