#    This file is part of Radio-Browser-Plugin for Rhythmbox.
#    Copyright (C) 2012 <foss.freedom@gmail.com>
#    This is a derivative of software originally created by <segler_alex@web.de> 2009
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
import urllib.request, urllib.parse, urllib.error
from gi.repository import Gtk
import xml.sax.handler

from radio_station import RadioStation
from feed import Feed
from feed import FeedAction
from feed import FeedStationAction

class BoardHandler(xml.sax.handler.ContentHandler):
    def __init__(self):
        self.entries = []
        self.languages = []
        self.countries = []

    def startElement(self, name, attributes):
        if name == "station":
            self.entry = RadioStation()
            self.entry.type = "Board"
            self.entry.id = attributes.get("id")
            self.entry.server_name = attributes.get("name")
            self.entry.genre = attributes.get("tags")
            if (self.entry.genre == None):
                self.entry.genre = ""
            self.entry.genre = ",".join(self.entry.genre.split(" "))
            self.entry.listen_url = attributes.get("url")
            self.entry.language = attributes.get("language")
            self.entry.country = attributes.get("country")
            self.entry.votes = attributes.get("votes")
            self.entry.negativevotes = attributes.get("negativevotes")
            self.entry.homepage = attributes.get("homepage")
            self.entry.icon_src = attributes.get("favicon")
            try:
                self.entry.clickcount = attributes.get("clickcount")
            except:
                self.entry.clickcount = 0
            self.entries.append(self.entry)

            if self.entry.country.title() not in self.countries:
                self.countries.append(self.entry.country.title())
            if self.entry.language.title() not in self.languages:
                self.languages.append(self.entry.language.title())

class PostStationDialog(Gtk.Dialog):
    def __init__(self):
        super(PostStationDialog,self).__init__()

        title_label = Gtk.Label()
        title_label.set_markup("<span font='20.0'>"+_("Post new station")+"</span>")
        self.get_content_area().pack_start(title_label)
        self.add_button(Gtk.STOCK_CANCEL,Gtk.RESPONSE_CANCEL)
        self.add_button(Gtk.STOCK_OK,Gtk.RESPONSE_OK)

        table = Gtk.Table(3,8)

        table.attach(Gtk.Label(_("Examples")),2,3,0,1)

        table.attach(Gtk.Label(_("Name")),0,1,1,2)
        self.StationName = Gtk.Entry()
        table.attach(self.StationName,1,2,1,2)
        table.attach(Gtk.Label(_("My Station")),2,3,1,2)

        table.attach(Gtk.Label(_("URL")),0,1,2,3)
        self.StationUrl = Gtk.Entry()
        table.attach(self.StationUrl,1,2,2,3)
        table.attach(Gtk.Label(_("http://listen.to.my/station.pls")),2,3,2,3)

        table.attach(Gtk.Label(_("Homepage URL")),0,1,3,4)
        self.StationHomepage = Gtk.Entry()
        table.attach(self.StationHomepage,1,2,3,4)
        table.attach(Gtk.Label(_("http://very.cool.site")),2,3,3,4)

        table.attach(Gtk.Label(_("Favicon URL")),0,1,4,5)
        self.StationFavicon = Gtk.Entry()
        table.attach(self.StationFavicon,1,2,4,5)
        table.attach(Gtk.Label(_("http://very.cool.site/favicon.ico")),2,3,4,5)

        table.attach(Gtk.Label(_("Country")),0,1,5,6)
        self.StationCountry = Gtk.ComboBoxEntry()
        table.attach(self.StationCountry,1,2,5,6)
        table.attach(Gtk.Label(_("Utopia")),2,3,5,6)

        table.attach(Gtk.Label(_("Language")),0,1,6,7)
        self.StationLanguage = Gtk.ComboBoxEntry()
        table.attach(self.StationLanguage,1,2,6,7)
        table.attach(Gtk.Label(_("Esperanto")),2,3,6,7)

        table.attach(Gtk.Label(_("Tags")),0,1,7,8)
        self.StationTags = Gtk.Entry()
        table.attach(self.StationTags,1,2,7,8)
        table.attach(Gtk.Label(_("Classical Jazz Talk")),2,3,7,8)

        self.get_content_area().pack_start(table,False)

        self.set_title(_("Post new station"))
        self.set_resizable(False)
        self.set_position(Gtk.WIN_POS_CENTER)
        self.show_all()

class FeedBoard(Feed):
    def __init__(self,cache_dir,status_change_handler):
        Feed.__init__(self)
        print("init board feed")
        self.handler = BoardHandler()
        self.cache_dir = cache_dir
        self.filename = os.path.join(self.cache_dir, "board.xml")
        self.uri = "http://www.radio-browser.info/xml.php"
        self.status_change_handler = status_change_handler

    def name(self):
        return "Board"

    def getDescription(self):
        return _("Community radio station board. Click the homepage and help!")

    def getHomepage(self):
        return "http://www.radio-browser.info"

    def search(self, term):
        foundEntries = []

        for entry in self.entries():
            if entry.server_name.lower().find(term.lower()) >= 0:
                foundEntries.append(entry)

        return foundEntries

    """ vote for station on board """
    def vote_station(self,source,station):
        message = Gtk.MessageDialog(message_format=_("Vote for station"),buttons=Gtk.BUTTONS_YES_NO,type=Gtk.MESSAGE_QUESTION)
        message.format_secondary_text(_("Do you really want to vote for this station? It means, that you like it, and you want more people to know, that this is a good station."))
        response = message.run()
        if response == Gtk.RESPONSE_YES:
            params = urllib.parse.urlencode({'action': 'vote','id': station.id})
            f = urllib.request.urlopen("http://www.radio-browser.info/?%s" % params)
            f.read()
            source.refill_list()
        message.destroy()

    """ mark station as bad on board """
    def bad_station(self,source,station):
        message = Gtk.MessageDialog(message_format=_("Mark station as broken"),buttons=Gtk.BUTTONS_YES_NO,type=Gtk.MESSAGE_WARNING)
        message.format_secondary_text(_("Do you really want to mark this radio station as broken? It will eventually get deleted if enough people do that! More information on that on the feeds homepage: http://www.radio-browser.info/"))
        response = message.run()
        if response == Gtk.RESPONSE_YES:
            params = urllib.parse.urlencode({'action': 'negativevote','id': station.id})
            f = urllib.request.urlopen("http://www.radio-browser.info/?%s" % params)
            f.read()
            source.refill_list()
        message.destroy()

    """ post new station to board """
    def post_new_station(self,source):
        dialog = PostStationDialog()

        LanguageList = Gtk.ListStore(str)
        for language in self.handler.languages:
            LanguageList.append([language])
        LanguageList.set_sort_column_id(0,Gtk.SortType.ASCENDING)
        dialog.StationLanguage.set_model(LanguageList)
        dialog.StationLanguage.set_text_column(0)

        CountryList = Gtk.ListStore(str)
        for country in self.handler.countries:
            CountryList.append([country])
        CountryList.set_sort_column_id(0,Gtk.SortType.ASCENDING)
        dialog.StationCountry.set_model(CountryList)
        dialog.StationCountry.set_text_column(0)

        while True:
            def show_message(message):
                info_dialog = Gtk.MessageDialog(parent=dialog,buttons=Gtk.BUTTONS_OK,message_format=message)
                info_dialog.run()
                info_dialog.destroy()

            response = dialog.run()
            if response == Gtk.RESPONSE_CANCEL:
                break
            if response == Gtk.RESPONSE_OK:
                Name = dialog.StationName.get_text().strip()
                URL = dialog.StationUrl.get_text().strip()
                Homepage = dialog.StationHomepage.get_text().strip()
                Favicon = dialog.StationFavicon.get_text().strip()
                Tags = dialog.StationTags.get_text().strip()
                Country = dialog.StationCountry.get_child().get_text().strip()
                Language = dialog.StationLanguage.get_child().get_text().strip()

                if Name == "" or URL == "":
                    show_message(_("Name and URL are necessary"))
                    continue

                if not (URL.lower().startswith("http://") or URL.lower().startswith("mms://")):
                    show_message(_("URL needs to start with http:// or mms://"))
                    continue

                if Homepage != "":
                    if not Homepage.lower().startswith("http://"):
                        show_message(_("Homepage URL needs to start with http://"))
                        continue

                if Favicon != "":
                    if not Favicon.lower().startswith("http://"):
                        show_message(_("Favicon URL needs to start with http://"))
                        continue
                
                params = urllib.parse.urlencode({'action': 'add','name': Name, 'url': URL, 'homepage': Homepage,'favicon': Favicon, 'tags': Tags,'language': Language, 'country':Country})
                f = urllib.request.urlopen("http://www.radio-browser.info/?%s" % params)
                f.read()

                show_message(_("Station successfully posted"))
                source.refill_list()
                break

        dialog.destroy()

    def get_feed_actions(self):
        actions = []
        actions.append(FeedAction(self,_("Post new station"),self.post_new_station))
        return actions

    def get_station_actions(self):
        actions = []
        actions.append(FeedStationAction(self,_("Vote for station"),self.vote_station))
        actions.append(FeedStationAction(self,_("Station is broken"),self.bad_station))
        return actions
