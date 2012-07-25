#    This file is part of Radio-Browser-Plugin for Rhythmbox.
#
#    Copyright (C) 2009 <segler_alex@web.de>
#
#    Radio-Browser-Plugin is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Radio-Browser-Plugin is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Radio-Browser-Plugin.  If not, see <http://www.gnu.org/licenses/>.

import os
import urllib2
import httplib
from urlparse import urlparse
import datetime
import locale
import xml.sax.handler

from radio_station import RadioStation

class FeedAction:
	def __init__(self,feed,name,func):
		self.feed = feed
		self.name = name
		self.func = func

	def call(self,source):
		self.func(source)

class FeedStationAction:
	def __init__(self,feed,name,func):
		self.feed = feed
		self.name = name
		self.func = func

	def call(self,source,station):
		self.func(source,station)

class Feed:
	def __init__(self):
		self.loaded = False
		self.AutoDownload = True
		self.UpdateChecking = True
		self.FileSize = 0
		self.remote_mod = datetime.datetime.now()

	def getSource(self):
		return self.uri

	def getDescription(self):
		return ""

	def getHomepage(self):
		return ""

	def setAutoDownload(self,autodownload):
		self.AutoDownload = autodownload

	def setUpdateChecking(self,updatechecking):
		self.UpdateChecking = updatechecking

	def copy_callback(self,current,total):
		self.status_change_handler(self.uri,current,total)

	def download(self):
		print "downloading "+self.uri
		try:
			os.remove(self.filename)
		except:
			pass

		try:
			remotefile = urllib2.urlopen(self.uri)
			chunksize = 100
			data = ""
			current = 0

			while True:
				chunk = remotefile.read(chunksize)
				current += chunksize
				self.copy_callback(current,self.FileSize)
				if chunk == "":
					break
				if chunk == None:
					break
				data += chunk

			localfile = open(self.filename,"w")
			localfile.write(data)
			localfile.close()
		except Exception, e:
			print "download failed exception"
			print e
			return False
		return True

	def getRemoteFileInfo(self):
		try:
			urlparts = urlparse(self.uri)
			conn = httplib.HTTPConnection(urlparts.netloc)
			conn.request("HEAD", urlparts.path)
			res = conn.getresponse()
			for key,value in res.getheaders():
				if key == "last-modified":
					print key+":"+value
					oldlocale = locale.setlocale(locale.LC_ALL)
					locale.setlocale(locale.LC_ALL,"C")
					self.remote_mod = datetime.datetime.strptime(value,'%a, %d %b %Y %H:%M:%S %Z')
					locale.setlocale(locale.LC_ALL,oldlocale)
				if key == "content-length":
					print key+":"+value
					self.FileSize = int(value)
		except Exception, e:
			print "could not check remote file for modification time:"+self.uri
			print e
			return

	# only download if necessary
	def update(self):
		download = False
		local_mod = datetime.datetime.min

		try:
			local_mod = datetime.datetime.fromtimestamp(os.path.getmtime(self.filename))
		except:
			print "could not load local file:"+self.filename
			download = True

		self.getRemoteFileInfo()
		
		if self.remote_mod > local_mod:
			print "Local file older than 1 day: remote("+str(self.remote_mod)+") local("+str(local_mod)+")"
			# change date is different -> download
			download = True

		if download:
			self.download()

	def load(self):
		print "loading "+self.filename
		try:
			xml.sax.parse(self.filename,self.handler)
		except:
			print "parse failed of "+self.filename

	def genres(self):
		if not os.path.isfile(self.filename) and not self.AutoDownload:
			return []

		if not self.loaded:
			if self.UpdateChecking:
				self.update()
			if not os.path.isfile(self.filename):
				download()
			self.load()
			self.loaded = True

		list = []
		for station in self.handler.entries:
			if station.genre is not None:
				for genre in station.genre.split(","):
					tmp = genre.strip().lower()
					if tmp not in list:
						list.append(tmp)
		return list

	def entries(self):
		if not os.path.isfile(self.filename) and not self.AutoDownload:
			return []

		if not self.loaded:
			if self.UpdateChecking:
				self.update()
			if not os.path.isfile(self.filename):
				download()
			self.load()
			self.loaded = True

		return self.handler.entries

	def force_redownload(self):
		self.handler.entries = []
		self.loaded = False
		try:
			os.remove(self.filename)
		except:
			pass
		pass

	def get_feed_actions(self):
		actions = []
		return actions

	def get_station_actions(self):
		actions = []
		return actions

	#def search(self,term,queue):
	#	print "not implemented in this feed"
	#	return None

	def downloadFile(self,url):
		try:
			remotefile = urllib2.urlopen(url)
			chunksize = 100
			data = ""
			current = 0

			while True:
				chunk = remotefile.read(chunksize)
				current += chunksize
				if chunk == "":
					break
				if chunk == None:
					break
				data += chunk

			remotefile.close()
			return data
		except Exception, e:
			print "download failed exception"
			print e

		return None
