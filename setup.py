from distutils.core import setup
from TweetBase import __version__
import io

def read(*filenames, **kwargs):
    encoding = kwargs.get('encoding', 'utf-8')
    sep = kwargs.get('sep', '\n')
    buf = []
    for filename in filenames:
        with io.open(filename, encoding=encoding) as f:
            buf.append(f.read())
    return sep.join(buf)
    
setup(
    name='TweetBase',
    version=__version__,
    author='Jonas Geduldig',
    author_email='boxnumber03@gmail.com',
    packages=['TweetBase'],
    url='https://github.com/geduldig/TweetBase',
    download_url = 'https://github.com/geduldig/TweetBase/tarball/master',
    license='MIT',
    keywords='twitter,couchdb',
    description='Write tweets to database',
    long_description=read('README.txt'),
    install_requires = ['TwitterAPI', 'TwitterGeoPics', 'couchdb']
)
