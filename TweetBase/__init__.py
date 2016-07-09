__title__ = 'TweetBase'
__version__ = '0.2.12'
__author__ = 'geduldig'
__license__ = 'MIT'
__copyright__ = 'Copyright 2014 geduldig'


try:
	from .TweetCouch import TweetCouch
except:
	pass


__all__ = [
	'TweetCouch'
]
