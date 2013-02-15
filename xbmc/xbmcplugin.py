import os, sys
import urllib, re
from urlparse import urlparse
from ast import literal_eval

import jumpy, xbmcinit, xbmc

# some plugins seem to expect these to be preloaded
# sys is already preloaded by jumpy
import __builtin__
__builtin__.os = os
__builtin__.xbmc = xbmc

# xbmc/SortFileItem.h
SORT_METHOD_NONE = 0
SORT_METHOD_LABEL = 1
SORT_METHOD_LABEL_IGNORE_THE = 2
SORT_METHOD_DATE = 3
SORT_METHOD_SIZE = 4
SORT_METHOD_FILE = 5
SORT_METHOD_DRIVE_TYPE = 6
SORT_METHOD_TRACKNUM = 7
SORT_METHOD_DURATION = 8
SORT_METHOD_TITLE = 9
SORT_METHOD_TITLE_IGNORE_THE = 10
SORT_METHOD_ARTIST = 11
SORT_METHOD_ARTIST_IGNORE_THE = 12
SORT_METHOD_ALBUM = 13
SORT_METHOD_ALBUM_IGNORE_THE = 14
SORT_METHOD_GENRE = 15
SORT_METHOD_COUNTRY = 16
SORT_METHOD_YEAR = 17
SORT_METHOD_VIDEO_RATING = 18
SORT_METHOD_DATEADDED = 19
SORT_METHOD_PROGRAM_COUNT = 20
SORT_METHOD_PLAYLIST_ORDER = 21
SORT_METHOD_EPISODE = 22
SORT_METHOD_VIDEO_TITLE = 23
SORT_METHOD_VIDEO_SORT_TITLE = 24
SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE = 25
SORT_METHOD_PRODUCTIONCODE = 26
SORT_METHOD_SONG_RATING = 27
SORT_METHOD_MPAA_RATING = 28
SORT_METHOD_VIDEO_RUNTIME = 29
SORT_METHOD_STUDIO = 30
SORT_METHOD_STUDIO_IGNORE_THE = 31
SORT_METHOD_FULLPATH = 32
SORT_METHOD_LABEL_IGNORE_FOLDERS = 33
SORT_METHOD_LASTPLAYED = 34
SORT_METHOD_PLAYCOUNT = 35
SORT_METHOD_LISTENERS = 36
SORT_METHOD_UNSORTED = 37
SORT_METHOD_BITRATE = 38
SORT_METHOD_MAX = 39

SORT_ORDER_NONE = 0
SORT_ORDER_ASC = 1
SORT_ORDER_DESC = 2

SORT_NORMALLY = 0
SORT_ON_TOP = 1
SORT_ON_BOTTOM = 2

argv0 = sys.argv[0]

# restructure args to xbmc command format, i.e.
#   'plugin://plugin.video.foo/ [window_id query_string]'
if len(sys.argv) > 1:
	argv = sys.argv[1].split('?')
	sys.argv = []
	sys.argv.append(argv[0])
	sys.argv.append('0')
	sys.argv.append("" if len(argv) == 1 else "?" + argv[1])

librtmp_checked = False
librtmp = False

# added functions

def using_librtmp():
	global librtmp_checked, librtmp
	if not librtmp_checked:
		librtmp = pms.getVar('using_librtmp') == 'true'
		librtmp_checked = True
	return librtmp

def getMediaType(listitem):
	itemtype = listitem.getProperty('type').strip().upper()
	if itemtype == "VIDEO":
		return PMS_VIDEO
	elif itemtype == "AUDIO":
		return PMS_AUDIO
	else:
		return PMS_UNRESOLVED

def fullPath(base, path):
#	print 'fullPath %s' % [base, path]
	if path == None:
		return None
	if urlparse(path).scheme == "" and not os.path.isabs(path):
		url = urlparse(base)
		path = '%s://%s/%s' % (url.scheme, url.netloc, path) if url.scheme != ""  \
			else os.path.join(os.path.dirname(base), path)
	return xbmc.translatePath(path, False)

# see xbmc/guilib/GUITextLayout.cpp::ParseText
def striptags(label):
	if label is not None:
		return label.replace('[COLOR ', '[').replace('[COLOR=', '[').replace('[/COLOR]', '') \
			.replace('[B]', '').replace('[/B]', '') \
			.replace('[I]', '').replace('[/I]', '')
	return label

def rtmpsplit(url, listitem):
	sargs = []
	args = []
	tups = re.findall(r' ([-\w]+)=(".*?"|\S+)', ' -r=' + url)
	# see xbmc/cores/dvdplayer/DVDInputStreams/DVDInputStreamRTMP.cpp:120
	for key,tag in [
			( "SWFPlayer", "swfUrl"),
			( "PageURL",   "pageUrl"),
			( "PlayPath",  "playpath"),
			( "TcUrl",     "tcUrl"),
			( "IsLive",    "live")
		]:
			try:
				tups.append((tag, listitem.getProperty(key)))
			except KeyError:
				pass
	swfVfy = True if url.lower().replace('=1', '=true').find(" swfvfy=true") > -1 else False
	opts = {
		'swfurl'    : '-W' if swfVfy else '-s',
		'playpath'  : '-y',
		'app'       : '-a',
		'pageurl'   : '-p',
		'tcurl'     : '-t',
		'subscribe' : '-d',
		'live'      : '-v',
		'playlist'  : '-Y',
		'socks'     : '-S',
		'flashver'  : '-f',
		'conn'      : '-C',
		'jtv'       : '-j',
		'token'     : '-T',
		'swfage'    : '-X',
		'start'     : '-A',
		'stop'      : '-B',
		'buffer'    : '-b',
		'timeout'   : '-m',
		'auth'      : '-u'
	}
	for key,val in tups:
		if val is None:
			continue
#		# convert some '\hh' hex escapes
#		val = val.replace('\\5c','\\').replace('\\20',' ') \
#			.replace('\\22','\\"' if sys.platform.startswith('win32') else '"')
		# convert all '\hh' hex escapes
		val = literal_eval("'%s'" % val.replace('\\','\\x'))
		if sys.platform.startswith('win32'):
			val = val.replace('"', '\\"')
		if key.lower() in opts:
			key = opts[key.lower()]
		if val == '1' or val.lower() == 'true':
			if key.lower() != 'swfvfy':
				sargs.append(key)
		else:
			args.append((key, val))
	cmd = "rtmpdump " + ' '.join('%s "%s"' % arg for arg in args) + ' ' + ' '.join(sargs)
	print "test cmd: %s\n" %  cmd
	return (args, sargs)

def librtmpify(url, listitem):
	newurl = [url]
	# see xbmc/cores/dvdplayer/DVDInputStreams/DVDInputStreamRTMP.cpp:120
	for key,tag in [
			( "SWFPlayer", "swfUrl"),
			( "PageURL",   "pageUrl"),
			( "PlayPath",  "playpath"),
			( "TcUrl",     "tcUrl"),
			( "IsLive",    "live")
		]:
			try:
				val = listitem.getProperty(key)
				if val:
					newurl.append('%s=%s' % (tag, val))
			except KeyError:
				pass
	newurl = ' '.join(newurl)
	print 'test cmd: ffmpeg -y -i "%s" -target ntsc-dvd - \n' %  newurl
	return newurl

# native xbmc functions

def addDirectoryItem(handle, url, listitem, isFolder=False, totalItems=None):
	"""Callback function to pass directory contents back to XBMC."""
	itemtype = PMS_FOLDER
	script = argv0
	if not isFolder:
		if url.startswith('plugin://'):
			id = urlparse(url).netloc
			script = os.path.join(_info[id]['path'], _info[id]['_script'])
			itemtype = PMS_UNRESOLVED
		else:
			listitem.setProperty('path', url)
			setResolvedUrl(handle, True, listitem, 0)
			return True
	label = striptags(listitem.getLabel())
	if label and url:
		pms.addItem(itemtype, label,
			[script, url] if itemtype < 0 else url,
			fullPath(url, listitem.getProperty('thumbnailImage')))
	return True

def addDirectoryItems(handle, items, totalItems=None):
	"""Callback function to pass directory contents back to XBMC as a list."""
	for (url, listitem, isFolder) in items:
		addDirectoryItem(handle, url, listitem, isFolder)
	return True

def setResolvedUrl(handle, succeeded, listitem, stack=-1):
	"""Callback function to tell XBMC that the file plugin has been resolved to a url"""
	url = listitem.getProperty('path')
	if not succeeded or url is None:
		return
	media = getMediaType(listitem)
	if '|' in url:
		url,headers = url.split('|')

	if url.startswith('rtmp'):
		if using_librtmp():
			url = librtmpify(url, listitem)
		else:
			args, sargs = rtmpsplit(url, listitem)
			url = "rtmpdump://rtmp2pms?" + urllib.urlencode(args) + (('&' + '&'.join(sargs)) if len(sargs) else '')

	elif url.startswith('plugin://'):
		dir = os.path.dirname(xbmc.translatePath(url.split('?')[0]))
		id = xbmcinit.read_addon(dir, full=False)
		info = _info[id]
		pms.addPath(info['_pythonpath'])
		url = [os.path.join(info['path'], info['_script']), url]
		media = PMS_UNRESOLVED

	# see xbmc/filesystem/StackDirectory.cpp
	elif url.startswith('stack://'):
		ct = 0
		for url in url[8:].split(' , '):
			listitem.setProperty('path', url.replace(',,', ','))
			setResolvedUrl(handle, succeeded, listitem, ct)
			ct += 1
		return

	name = striptags(listitem.getLabel())
	if name == "" or name == None: name = striptags(listitem.getProperty('title'))
	if name == "" or name == None: name = pms.getFolderName()
	if name == "" or name == None: name = "Item"
	name = name + "" if stack < 1 else " %d" % stack

	pms.addItem(media, name, url, fullPath(url, listitem.getProperty('thumbnailImage')))
	print "*** setResolvedUrl ***"
	print "raw : %s" % listitem.getProperty('path')
	print "name: %s" % name
	print "type: %d" % media
	print "url :",url

def endOfDirectory(handle, succeeded=None, updateListing=None, cacheToDisc=None):
	"""Callback function to tell XBMC that the end of the directory listing in a virtualPythonFolder is reached."""
	print "*** endOfDirectory ***"

def addSortMethod(handle, sortMethod, label2Mask=None):
	"""Adds a sorting method for the media list."""
	pass

# some plugins e.g Nickolodeon call getSetting(handle, id) instead of getSetting(id)
def getSetting(id, id2=None):
	"""Returns the value of a setting as a string."""
	try:
		return _settings[_mainid][id if id2 == None else id2]
	except KeyError:
		return ''

def setSetting(handle, id, value):
	"""Sets a plugin setting for the current running plugin."""
	_settings[_mainid][id] = value

def setContent(handle, content):
	"""Sets the plugins content."""
	pass

def setPluginCategory(handle, category):
	"""Sets the plugins name for skins to display."""
	pass

def setPluginFanart(handle, image, color1=None, color2=None, color3=None):
	"""Sets the plugins fanart and color for skins to display."""
	pass

def setProperty(handle, key, value):
	"""Sets a container property for this plugin."""
	pass

# protocols:
#	ftp
#	ftps
#	dav
#	davs
#	http
#	https
#	rtp
#	udp
#	rtmp
#	rtsp

#	filereader
#	shout
#	mms
#	musicdb
#	videodb
#	zip
#	file
#	playlistmusic
#	playlistvideo
#	special
#	upnp
#	plugin
#	musicsearch
#	lastfm
#	rss
#	smb
#	daap
#	hdhomerun
#	sling
#	rtv
#	htsp
#	vtp
#	myth
#	sap
#	sources
#	stack
#	tuxbox
#	multipath
#	rar
#	script
#	addons

