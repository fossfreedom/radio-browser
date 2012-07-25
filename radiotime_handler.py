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
import urllib
import urllib2
import xml.sax.handler

from radio_station import RadioStation
from feed import Feed

class RadioTimeRadioStation(RadioStation):
	def updateRealURL(self):
		self.listen_urls = []
		try:
			url = "http://opml.radiotime.com/Tune.ashx?id="+self.listen_id
			print "tunein:"+url
			remote = urllib2.urlopen(url)
			data = remote.read()
			remote.close()

			lines = data.splitlines()
			for line in lines:
				if not line.startswith("#"):
					self.listen_urls.append(line)
					print "new link:"+line
			self.askUserAboutUrls()

		except:
			return

	def getRealURL(self):
		if self.listen_url == "":
			self.updateRealURL()
		if self.listen_url == "":
			return None
		else:
			return self.listen_url

class RadioTimeHandler(xml.sax.handler.ContentHandler):
	def __init__(self):
		self.genres = {}
		self.entries = []
 
	def startElement(self, name, attributes):
		if name == "outline":
			if attributes.get("type") == "audio":
				self.entry = RadioTimeRadioStation()
				self.entry.type = "RadioTime"
				self.entry.server_name = attributes.get("text")
				self.entry.bitrate = attributes.get("bitrate")
				self.entry.reliability = attributes.get("reliability")
				self.entry.listen_id = attributes.get("guide_id")
				self.entry.genre = ""
				self.entry.genre_id = attributes.get("genre_id")
				self.entry.icon_src = attributes.get("image")
				self.entry.server_type = attributes.get("formats")
				self.entry.homepage = ""
				self.entries.append(self.entry)
			if attributes.get("type") == "link":
				try:
					self.entry = FeedRadioTime(self.cache_dir,self.status_change_handler)
					self.entry.uri = attributes.get("URL")
					self.entry._name = attributes.get("text")
					self.entry.filename = os.path.join(self.cache_dir,"radiotime-%s.xml" % attributes.get("guide_id"))
					self.entry.setAutoDownload(False)
					self.entries.append(self.entry)
				except:
					pass
			if attributes.get("type") == "text":
				self.genres[attributes.get("guide_id")] = attributes.get("text")

RadioTimeGenreList = None

class FeedRadioTime(Feed):
	def __init__(self,cache_dir,status_change_handler):
		Feed.__init__(self)
		self.handler = RadioTimeHandler()
		self.handler.cache_dir = cache_dir
		self.handler.status_change_handler = status_change_handler
		self.cache_dir = cache_dir
		self.status_change_handler = status_change_handler
		self.filename = os.path.join(self.cache_dir, "radiotime.xml")
		self.uri = "http://opml.radiotime.com/Browse.ashx?%s" % urllib.urlencode({"id":"r0","formats":"ogg,mp3,aac,wma"})
		self._name = "RadioTime"
		self.setUpdateChecking(False)

	def loadGenreList(self):
		global RadioTimeGenreList
		print "load genre list"

		url = "http://opml.radiotime.com/Describe.ashx?c=genres"
		handler = RadioTimeHandler()
		RadioTimeGenreList = {}

		try:
			remote = urllib2.urlopen(url)
			xmlData = remote.read()
			remote.close()
		except Exception, e:
			print "could not load genre list"
			print str(e)
			return

		try:
			xml.sax.parseString(xmlData,handler)
			RadioTimeGenreList = handler.genres
		except:
			print "parse failed of "+xmlData

	def entries(self):
		items = Feed.entries(self)
		if RadioTimeGenreList == None:
			self.loadGenreList()

		for item in items:
			if isinstance(item,RadioTimeRadioStation):
				#print "search for '"+item.genre_id+"'"
				if item.genre_id in RadioTimeGenreList:
					#print "found it!"
					item.genre = RadioTimeGenreList[item.genre_id]

		return items

	def name(self):
		return self._name

	def getHomepage(self):
		return "http://radiotime.com/"

	def search(self,term):
		searchUrl = "http://opml.radiotime.com/Search.ashx?%s" % urllib.urlencode({"query":term,"formats":"ogg,mp3,aac,wma"})
		print("url:"+searchUrl)
		data = self.downloadFile(searchUrl)
		handler = RadioTimeHandler()
		if data != None:
			xml.sax.parseString(data,handler)
			return handler.entries

		return None

class FeedRadioTimeLocal(FeedRadioTime):
	def __init__(self,cache_dir,status_change_handler):
		FeedRadioTime.__init__(self,cache_dir,status_change_handler)
		self.uri = "http://opml.radiotime.com/Browse.ashx?%s" % urllib.urlencode({"c":"local","formats":"ogg,mp3,aac,wma"})
		self._name = "RadioTime Local"
		self.filename = os.path.join(self.cache_dir, "radiotime-local.xml")
