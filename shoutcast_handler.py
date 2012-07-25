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

class ShoutcastRadioStation(RadioStation):
	def updateRealURL(self):
		self.listen_urls = []
		try:
			# download from "http://www.shoutcast.com"+self.tunein+"?id="+shoutcast_id
			url = "http://www.shoutcast.com"+self.tunein+"?id="+self.listen_id
			remote = urllib2.urlopen(url)
			data = remote.read()
			remote.close()

			lines = data.splitlines()
			for line in lines:
				if line.startswith("File"):
					self.listen_urls.append(line.split("=")[1])
					print "new link:"+line.split("=")[1]
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

class ShoutcastHandler(xml.sax.handler.ContentHandler):
	def __init__(self):
		self.genres = []
		self.entries = []
 
	def startElement(self, name, attributes):
		if name == "genre":
			self.genres.append(attributes.get("name"))
		if name == "tunein":
			self.tunein = attributes.get("base")
		if name == "station":
			self.entry = ShoutcastRadioStation()
			self.entry.tunein = self.tunein
			self.entry.type = "Shoutcast"
			self.entry.server_name = attributes.get("name")
			self.entry.genre = attributes.get("genre").lower()
			self.entry.genre = ",".join(self.entry.genre.split(" "))
			self.entry.current_song = attributes.get("ct")
			self.entry.bitrate = attributes.get("br")
			self.entry.listen_id = attributes.get("id")
			self.entry.listeners = attributes.get("lc")
			self.entry.server_type = attributes.get("mt")
			try:
				self.entry.homepage = "http://shoutcast.com/directory/search_results.jsp?searchCrit=simple&s="+urllib.quote_plus(self.entry.server_name.replace("- [SHOUTcast.com]","").strip())
			except:
				self.entry.homepage = ""
			self.entries.append(self.entry)

class FeedShoutcast(Feed):
	def __init__(self,cache_dir,status_change_handler):
		Feed.__init__(self)
		print "init shoutcast feed"
		self.handler = ShoutcastHandler()
		self.cache_dir = cache_dir
		self.filename = os.path.join(self.cache_dir, "shoutcast-genre.xml")
		self.uri = "http://www.shoutcast.com/sbin/newxml.phtml"
		self.status_change_handler = status_change_handler

	def name(self):
		return "Shoutcast"

	def getHomepage(self):
		return "http://shoutcast.com/"

	def genres(self):
		if not self.loaded:
			if not os.path.isfile(self.filename):
				self.download()
			self.load()
			self.loaded = True

		return self.handler.genres

	def entries(self):
		entry_list = []
		genres = self.genres()
		for genre in genres:
			entry = FeedSubShoutcast(self.cache_dir,self.status_change_handler,genre)
			entry_list.append(entry)

		return entry_list

	def search(self,term):
		searchUrl = "http://www.shoutcast.com/sbin/newxml.phtml?%s" % urllib.urlencode({"search":term})
		data = self.downloadFile(searchUrl)
		handler = ShoutcastHandler()
		if data != None:
			xml.sax.parseString(data,handler)
			return handler.entries

		return None

class FeedSubShoutcast(Feed):
	def __init__(self,cache_dir,status_change_handler,genre):
		Feed.__init__(self)
		self.handler = ShoutcastHandler()
		self.cache_dir = cache_dir
		self.filename = os.path.join(self.cache_dir, "shoutcast-"+genre+".xml")
		self.uri = "http://www.shoutcast.com/sbin/newxml.phtml?%s" % urllib.urlencode({"genre":genre})
		self.status_change_handler = status_change_handler
		self.genre = genre
		self.setAutoDownload(False)
		self.setUpdateChecking(False)

	def name(self):
		return "Shoutcast Genre "+self.genre

	def getHomepage(self):
		return "http://shoutcast.com/"
