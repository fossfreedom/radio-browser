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

from gi.repository import RB
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository.GdkPixbuf import Pixbuf
from gi.repository import GLib
import rb
import http.client
import os
import subprocess
from threading import Thread
import threading
import hashlib
import urllib.request, urllib.parse, urllib.error
import webbrowser
import queue
import pickle
import datetime
import math
import urllib.request, urllib.error, urllib.parse

import xml.sax.saxutils
from radio_station import RadioStation
from record_process import RecordProcess

from feed import Feed
from icecast_handler import FeedIcecast
from shoutcast_handler import FeedShoutcast
from shoutcast_handler import ShoutcastRadioStation
from board_handler import FeedBoard
from board_handler import BoardHandler
from radiotime_handler import FeedRadioTime
from radiotime_handler import FeedRadioTimeLocal

#TODO: should not be defined here, but I don't know where to get it from. HELP: much apreciated
RB_METADATA_FIELD_TITLE = 0
RB_METADATA_FIELD_GENRE = 4
RB_METADATA_FIELD_BITRATE = 20
BOARD_ROOT = "http://www.radio-browser.info/"
RECENTLY_USED_FILENAME = "recently2.bin"
BOOKMARKS_FILENAME = "bookmarks.bin"

GLib.threads_init()


class RadioBrowserSource(RB.StreamingSource):
    def __init__(self):
        self.hasActivated = False
        RB.StreamingSource.__init__(self, name="RadioBrowserPlugin")

    def do_get_status(self, *args):
        '''
        Method called by Rhythmbox to figure out what to show on this source
        statusbar.
        '''

        if self.updating:
            return (self.load_status, '', 1)
        else:
            return ('', '', 1)

    def do_set_property(self, property, value):
        if property.name == 'plugin':
            self.plugin = value

    """ return list of actions that should be displayed in toolbar """

    def do_get_ui_actions(self):
        print("do_get_ui_actions")
        return self.do_impl_get_ui_actions()

    def do_impl_get_ui_actions(self):
        print("do_impl_get_ui_actions")
        return ["UpdateList", "ClearIconCache"]

    def do_impl_get_status(self):
        print("do_impl_get_status")
        if self.updating:
            progress = -1.0
            if self.load_total_size > 0:
                progress = min(float(self.load_current_size) / self.load_total_size, 1.0)
            return (self.load_status, None, progress)
        else:
            return (_("Nothing to do"), None, 2.0)

    def update_download_status(self, filename, current, total):
        #print "update_download_status"
        self.load_current_size = current
        self.load_total_size = total
        self.load_status = _("Loading %(url)s") % {'url': filename}
        Gdk.threads_enter()
        self.notify_status_changed()
        Gdk.threads_leave()

    def do_selected(self):
        print("do_selected")
        self.do_impl_activate()

    """ on source actiavation, e.g. double click on source or playing something in this source """

    def do_impl_activate(self):
        print("do_impl_activate")
        # first time of activation -> add graphical stuff
        if not self.hasActivated:
            self.plugin = self.props.plugin
            self.shell = self.props.shell
            self.db = self.shell.props.db;
            self.entry_type = self.props.entry_type
            self.hasActivated = True

            # add listener for stream infos
            sp = self.shell.props.shell_player
            sp.props.player.connect("info", self.info_available)

            # create cache dir
            self.cache_dir = RB.find_user_cache_file("radio-browser")

            if os.path.exists(self.cache_dir) is False:
                os.makedirs(self.cache_dir, 0o700)
            self.icon_cache_dir = os.path.join(self.cache_dir, "icons")
            if os.path.exists(self.icon_cache_dir) is False:
                os.makedirs(self.icon_cache_dir, 0o700)
            self.updating = False
            self.load_current_size = 0
            self.load_total_size = 0
            self.load_status = ""

            # create the model for the view

            ui = Gtk.Builder()
            ui.add_from_file(rb.find_plugin_file(self.plugin,
                                                 'radio_station.ui'))

            self.filter_entry = ui.get_object('filter_entry')
            self.filter_entry_bitrate = ui.get_object('filter_entry_bitrate')
            self.filter_entry_genre = ui.get_object('filter_entry_genre')

            self.tree_store = Gtk.TreeStore(str, object)

            self.sorted_list_store = Gtk.TreeModelSort(model=self.tree_store)  #Gtk.TreeModelSort(self.tree_store)
            self.filtered_list_store = self.sorted_list_store.filter_new()
            self.filtered_list_store.set_visible_func(self.list_store_visible_func)
            self.filtered_icon_view_store = None

            #self.tree_view = Gtk.TreeView(self.sorted_list_store)
            self.tree_view = ui.get_object('tree_view')
            self.tree_view.set_model(self.sorted_list_store)
            # create the view
            column_title = Gtk.TreeViewColumn()  #"Title",Gtk.CellRendererText(),text=0)
            column_title.set_title(_("Title"))
            renderer = Gtk.CellRendererPixbuf()
            column_title.pack_start(renderer, expand=False)
            column_title.set_cell_data_func(renderer, self.model_data_func, "image")
            renderer = Gtk.CellRendererText()
            column_title.pack_start(renderer, expand=True)
            column_title.add_attribute(renderer, 'text', 0)
            column_title.set_resizable(True)
            column_title.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            column_title.set_fixed_width(100)
            column_title.set_expand(True)
            self.tree_view.append_column(column_title)

            self.info_box_tree = ui.get_object('info_box_tree')
            # - selection change
            self.tree_view.connect("cursor-changed", self.treeview_cursor_changed_handler, self.info_box_tree)

            # create icon view
            self.icon_view = ui.get_object('icon_view')
            self.icon_view.set_text_column(0)
            self.icon_view.set_pixbuf_column(2)
            self.tree_view_container = ui.get_object('tree_view_container')
            self.icon_view_container = ui.get_object('icon_view_container')
            self.view = ui.get_object('view')
            filterbox = ui.get_object('filterbox')
            self.start_box = ui.get_object('start_box')

            # prepare search tab
            print("prepare search tab")
            self.info_box_search = ui.get_object('info_box_search')
            self.search_box = ui.get_object('search_box')
            self.search_entry = ui.get_object('search_entry')

            def searchButtonClick(widget):
                self.doSearch(self.search_entry.get_text())

            searchbutton = ui.get_object('searchbutton')
            searchbutton.connect("clicked", searchButtonClick)

            search_input_box = ui.get_object('search_input_box')
            self.result_box = ui.get_object('result_box')
            self.result_box.connect("cursor-changed", self.treeview_cursor_changed_handler, self.info_box_search)

            self.result_box_container = ui.get_object('result_box_container')
            self.result_box.append_column(Gtk.TreeViewColumn(_("Title"), Gtk.CellRendererText(), text=0))

            stations_box = ui.get_object('stations_box')
            self.notebook = ui.get_object('notebook')
            ui.connect_signals(self)

            self.pack_start(self.notebook, True, True, 0)
            self.notebook.show_all()
            self.icon_view_container.hide()

            # initialize lists for recording streams and icon cache
            self.recording_streams = {}
            self.icon_cache = {}

            # start icon downloader thread
            # use queue for communication with thread
            # enqueued addresses will get downloaded
            self.icon_download_queue = queue.Queue()
            self.icon_download_thread = threading.Thread(target=self.icon_download_worker)
            self.icon_download_thread.setDaemon(True)
            self.icon_download_thread.start()

            # first time filling of the model
            self.main_list_filled = False

            # enable images on buttons
            settings = Gtk.Settings.get_default()
            settings.set_property("gtk_button_images", True)
            #Gtk.Settings.gtk_button_images(True)

            self.event_page_switch(_, _, 0)

        # rhythmbox 0.13.3 does not have the following method
        try:
            rb.BrowserSource.do_impl_activate(self)
        except:
            print("ignored error")

    def searchEngines(self):
        print("searchEngines")
        yield FeedIcecast(self.cache_dir,self.update_download_status)
        yield FeedBoard(self.cache_dir, self.update_download_status)
        #yield FeedShoutcast(self.cache_dir,self.update_download_status)
        #yield FeedRadioTime(self.cache_dir,self.update_download_status)

    def doSearch(self, term):
        print("doSearch")
        search_model = Gtk.ListStore(str)
        search_model.append((_("Searching for : '%s'") % term,))

        # unset model
        self.result_box.set_model(search_model)
        # start thread
        search_thread = threading.Thread(target=self.doSearchThread, args=(term,))
        search_thread.start()

    def doSearchThread(self, term):
        print("doSearchThread")
        results = {}
        self.station_actions = {}

        # check each engine for search method
        for feed in self.searchEngines():
            try:
                feed.search
            except:
                print("no search support in : " + feed.name())
                continue

            # call search method
            try:
                self.station_actions[feed.name()] = feed.get_station_actions()
                result = feed.search(term)
                results[feed.name()] = result
            except Exception as e:
                print("error with source:" + feed.name())
                print("error:" + str(e))

        Gdk.threads_enter()
        # create new model
        new_model = Gtk.TreeStore(str, object)
        # add entries to model
        for name in list(results.keys()):
            result = results[name]
            source_parent = new_model.append(None, (name + " (" + str(len(result)) + ")", None))
            for entry in result:
                new_model.append(source_parent, (entry.server_name, entry))

        # set model of result_box
        new_model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.result_box.set_model(new_model)
        Gdk.threads_leave()

    def download_click_statistic(self):
        print("download_click_statistic")
        # download statistics
        statisticsStr = ""
        try:
            remotefile = urllib.request.urlopen("http://www.radio-browser.info/topclick.php?limit=10")
            statisticsStr = remotefile.read()

        except Exception as e:
            print("download failed exception")
            print(e)
            return

        # parse statistics
        self.statistics_handler = BoardHandler()
        xml.sax.parseString(statisticsStr, self.statistics_handler)

        # fill statistics box
        self.refill_statistics(thread=True)

    def shortStr(self, longstring, maxlen):
        if len(longstring) > maxlen:
            short_value = longstring[0:maxlen - 3] + "..."
        else:
            short_value = longstring
        return short_value

    def refill_statistics(self, thread=False):
        print("refill_statistics")
        # check if already downloaded
        try:
            self.statistics_handler
        except:
            transmit_thread = threading.Thread(target=self.download_click_statistic)
            transmit_thread.start()
            return

        def button_click(widget, name, station):
            self.play_uri(station)

        def button_add_click(widget, name, station):
            data = self.load_from_file(os.path.join(self.cache_dir, BOOKMARKS_FILENAME))
            if data is None:
                data = {}
            if station.server_name not in data:
                data[station.server_name] = station
            self.save_to_file(os.path.join(self.cache_dir, BOOKMARKS_FILENAME), data)

            self.refill_favourites()

        if thread:
            Gdk.threads_enter()
        for entry in self.statistics_handler.entries:
            button = Gtk.Button(self.shortStr(entry.server_name, 30) + " (" + entry.clickcount + ")")
            button.connect("clicked", button_click, entry.server_name, entry)

            button_add = Gtk.Button()
            img = Gtk.Image()
            img.set_from_stock(Gtk.STOCK_GO_FORWARD, Gtk.IconSize.BUTTON)
            button_add.set_image(img)
            button_add.connect("clicked", button_add_click, entry.server_name, entry)
            line = Gtk.HBox()
            line.pack_start(button, True, True, 0)  #dm
            line.pack_start(button_add, False, False, 0)

            self.statistics_box.pack_start(line, False, False, 0)
            line.show_all()

        self.statistics_box_parent.show_all()
        if thread:
            Gdk.threads_leave()

    def refill_favourites(self):
        print("refill favourites")

        (hasfound, width, height) = Gtk.icon_size_lookup(Gtk.IconSize.BUTTON)
        # remove all old information in infobox
        for widget in self.start_box.get_children():
            self.start_box.remove(widget)

        def button_click(widget, name, station):
            self.play_uri(station)

        def button_record_click(widget, name, station):
            self.record_uri(station)

        def button_add_click(widget, name, station):
            data = self.load_from_file(os.path.join(self.cache_dir, BOOKMARKS_FILENAME))
            if data is None:
                data = {}
            if station.server_name not in data:
                data[station.server_name] = station
            self.save_to_file(os.path.join(self.cache_dir, BOOKMARKS_FILENAME), data)

            self.refill_favourites()

        def button_delete_click(widget, name, station):
            data = self.load_from_file(os.path.join(self.cache_dir, BOOKMARKS_FILENAME))
            if data is None:
                data = {}
            if station.server_name in data:
                del data[station.server_name]
            self.save_to_file(os.path.join(self.cache_dir, BOOKMARKS_FILENAME), data)

            self.refill_favourites()

        left_box = Gtk.VBox()
        left_box.show()

        # add click statistics list
        self.statistics_box = Gtk.VBox()
        scrolled_box = Gtk.ScrolledWindow()
        scrolled_box.add_with_viewport(self.statistics_box)
        scrolled_box.set_property("hscrollbar-policy", Gtk.PolicyType.AUTOMATIC)
        decorated_box = Gtk.Frame()
        decorated_box.set_label("Click statistics (Last 30 days)")
        decorated_box.add(scrolled_box)
        self.statistics_box_parent = decorated_box
        left_box.pack_start(decorated_box, True, True, 0)  #dm

        self.refill_statistics()

        # add recently played list
        recently_box = Gtk.VBox()
        scrolled_box = Gtk.ScrolledWindow()
        scrolled_box.add_with_viewport(recently_box)
        scrolled_box.set_property("hscrollbar-policy", Gtk.PolicyType.AUTOMATIC)
        decorated_box = Gtk.Frame()
        decorated_box.set_label("Recently played")
        decorated_box.add(scrolled_box)
        left_box.pack_start(decorated_box, True, True, 0)  #dm

        self.start_box.pack1(left_box)

        data = self.load_from_file(os.path.join(self.cache_dir, RECENTLY_USED_FILENAME))
        if data is None:
            data = {}
        dataNew = {}
        sortedkeys = sorted(data.keys())
        for name in sortedkeys:
            station = data[name]
            if datetime.datetime.now() - station.PlayTime <= datetime.timedelta(
                    days=float(self.plugin.recently_played_purge_days)):
                if len(name) > 53:
                    short_value = name[0:50] + "..."
                else:
                    short_value = name
                button = Gtk.Button(short_value)
                button.connect("clicked", button_click, name, station)

                button_add = Gtk.Button()
                img = Gtk.Image()
                img.set_from_stock(Gtk.STOCK_GO_FORWARD, Gtk.IconSize.BUTTON)
                button_add.set_image(img)
                button_add.connect("clicked", button_add_click, name, station)
                line = Gtk.HBox()
                line.pack_start(button, True, True, 0)  #dm
                line.pack_start(button_add, False, False, 0)  #expand

                recently_box.pack_start(line, False, False, 0)  #expand
                dataNew[name] = station

                try:
                    if station.icon_src != "":
                        hash_src = hashlib.md5(station.icon_src.encode('utf-8')).hexdigest()
                        filepath = os.path.join(self.icon_cache_dir, hash_src)
                        if os.path.exists(filepath):
                            buffer = Pixbuf.new_from_file_at_size(filepath, width, height)
                            img = Gtk.Image()
                            img.set_from_pixbuf(buffer)
                            img.show()
                            button.set_image(img)
                except:
                    print("could not set image for station:" + str(station.server_name))

        if len(sortedkeys) > 0:
            decorated_box.show_all()
        self.save_to_file(os.path.join(self.cache_dir, RECENTLY_USED_FILENAME), dataNew)

        # add bookmarks
        favourites_box = Gtk.VBox()
        scrolled_box = Gtk.ScrolledWindow()
        scrolled_box.add_with_viewport(favourites_box)
        scrolled_box.set_property("hscrollbar-policy", Gtk.PolicyType.AUTOMATIC)
        decorated_box = Gtk.Frame()
        decorated_box.set_label("Favourites")
        decorated_box.add(scrolled_box)
        self.start_box.pack2(decorated_box)

        data = self.load_from_file(os.path.join(self.cache_dir, BOOKMARKS_FILENAME))
        if data is None:
            data = {}
        sortedkeys = sorted(data.keys())
        for name in sortedkeys:
            line = Gtk.HBox()
            station = data[name]
            if len(name) > 53:
                short_value = name[0:50] + "..."
            else:
                short_value = name

            button = Gtk.Button(short_value)
            button.connect("clicked", button_click, name, station)
            button_delete = Gtk.Button()
            img = Gtk.Image()
            img.set_from_stock(Gtk.STOCK_DELETE, Gtk.IconSize.BUTTON)
            button_delete.set_image(img)
            button_delete.connect("clicked", button_delete_click, name, station)

            button_record = Gtk.Button()
            img = Gtk.Image()
            img.set_from_stock(Gtk.STOCK_MEDIA_RECORD, Gtk.IconSize.BUTTON)
            button_record.set_image(img)
            button_record.connect("clicked", button_record_click, name, station)

            line.pack_start(button, True, True, 0)  #dm
            line.pack_start(button_record, False, False, 0)  #dm expand
            line.pack_start(button_delete, False, False, 0)  #dm expand
            favourites_box.pack_start(line, False, False, 0)  #dm expand

            try:
                if station.icon_src != "":
                    hash_src = hashlib.md5(station.icon_src.encode('utf-8')).hexdigest()
                    filepath = os.path.join(self.icon_cache_dir, hash_src)
                    if os.path.exists(filepath):
                        buffer = Pixbuf.new_from_file_at_size(filepath, width, height)
                        img = Gtk.Image()
                        img.set_from_pixbuf(buffer)
                        img.show()
                        button.set_image(img)
            except:
                print("could not set image for station:" + str(station.server_name))

        if (len(sortedkeys) > 0):
            decorated_box.show_all()

    """ handler for page switches in the main notebook """

    def event_page_switch(self, notebook, page, page_num):
        print("event_page_switch")
        if page_num == 0:
            # update favourites each time user selects it
            self.refill_favourites()
        if page_num == 1:
            pass
        if page_num == 2:
            if not self.main_list_filled:
                # fill the list only the first time, the user selects the main tab
                self.main_list_filled = True
                self.refill_list()

    """ listener on double click in search view """

    def on_item_activated_icon_view(self, widget, item):
        print("on_item_activated_icon_view")
        model = widget.get_model()
        station = model[item][1]

        self.play_uri(station)

    """ listener on selection change in search view """

    def on_selection_changed_icon_view(self, widget):
        print("on_selection_changed_icon_view")
        #model = widget.get_model()
        #items = widget.get_selected_items()
        model = self.icon_view.get_model()
        items = self.icon_view.get_selected_items()

        if len(items) == 1:
            print("time to update with the info box")
            obj = model[items[0]][1]
            self.update_info_box(obj, self.info_box_tree)  #dm2

    """ listener for selection changes """

    def treeview_cursor_changed_handler(self, treeview, info_box):
        # get selected item
        print("treeview_cursor_changed_handler")
        selection = treeview.get_selection()
        model, iter = selection.get_selected()

        # if some item is selected
        if not iter == None:
            obj = model.get_value(iter, 1)
            self.update_info_box(obj, info_box)

    def update_info_box(self, obj, info_box):
        print("update_info_box")
        # remove all old information in infobox
        for widget in info_box.get_children():
            info_box.remove(widget)

        # create new infobox
        info_container = Gtk.Table(12, 2)
        info_container.set_col_spacing(0, 10)
        self.info_box_added_rows = 0

        # convenience method for adding new labels to infobox
        def add_label(title, value, shorten=True):
            if value == None:
                return
            if not value == "":
                if shorten:
                    if len(value) > 53:
                        short_value = value[0:50] + "..."
                    else:
                        short_value = value
                else:
                    short_value = value

                label = Gtk.Label()
                label.set_line_wrap(True)
                if value.startswith("http://") or value.startswith("mms:") or value.startswith("mailto:"):
                    label.set_markup("<a href='" + xml.sax.saxutils.escape(value) + "'>" + xml.sax.saxutils.escape(
                        short_value) + "</a>")
                else:
                    label.set_markup(xml.sax.saxutils.escape(short_value))
                label.set_selectable(True)
                label.set_alignment(0, 0)

                title_label = Gtk.Label(title)
                title_label.set_alignment(1, 0)
                title_label.set_markup("<b>" + xml.sax.saxutils.escape(title) + "</b>")
                info_container.attach(title_label, 0, 1, self.info_box_added_rows, self.info_box_added_rows + 1)
                info_container.attach(label, 1, 2, self.info_box_added_rows, self.info_box_added_rows + 1)
                self.info_box_added_rows = self.info_box_added_rows + 1

        if isinstance(obj, Feed):
            feed = obj
            add_label(_("Entry type"), _("Feed"))

            add_label(_("Description"), feed.getDescription(), False)
            add_label(_("Feed homepage"), feed.getHomepage())
            add_label(_("Feed source"), feed.getSource())

            try:
                t = os.path.getmtime(feed.filename)
                timestr = datetime.datetime.fromtimestamp(t).strftime("%x %X")
            except:
                timestr = _("No local copy")
            add_label(_("Last update"), timestr)

        if isinstance(obj, RadioStation):
            station = obj
            add_label(_("Source feed"), station.type)
            add_label(_("Name"), station.server_name)
            add_label(_("Tags"), station.genre)
            add_label(_("Bitrate"), station.bitrate)
            add_label(_("Server type"), station.server_type)
            add_label(_("Homepage"), station.homepage)
            add_label(_("Current song (on last refresh)"), station.current_song)
            add_label(_("Current listeners"), station.listeners)
            add_label(_("Language"), station.language)
            add_label(_("Country"), station.country)
            add_label(_("Votes"), station.votes)
            add_label(_("Negative votes"), station.negativevotes)
            add_label(_("Stream URL"), station.listen_url)
            try:
                PlayTime = station.PlayTime.strftime("%x %X")
                add_label(_("Added to recently played at"), PlayTime)
            except:
                pass

        button_box = Gtk.VBox()

        def button_play_handler(widget, station):
            self.play_uri(station)

        def button_bookmark_handler(widget, station):
            data = self.load_from_file(os.path.join(self.cache_dir, BOOKMARKS_FILENAME))
            if data is None:
                data = {}
            if station.server_name not in data:
                self.tree_store.append(self.bookmarks_iter, (station.server_name, station))
                data[station.server_name] = station
                widget.set_label(_("Unbookmark"))
            else:
                iter = self.tree_store.iter_children(self.bookmarks_iter)
                while True:
                    title = self.tree_store.get_value(iter, 0)

                    if title == station.server_name:
                        self.tree_store.remove(iter)
                        break

                    iter = self.tree_store.iter_next(iter)
                    if iter == None:
                        break
                del data[station.server_name]
                widget.set_label(_("Bookmark"))
            self.save_to_file(os.path.join(self.cache_dir, BOOKMARKS_FILENAME), data)

        def button_record_handler(widget, station):
            self.record_uri(station)

        def button_download_handler(widget, feed):
            transmit_thread = threading.Thread(target=self.download_feed, args=(feed,))
            transmit_thread.setDaemon(True)
            transmit_thread.start()

        def button_action_handler(widget, action):
            action.call(self)

        def button_station_action_handler(widget, action, station):
            action.call(self, station)

        if isinstance(obj, Feed):
            feed = obj
            if os.path.isfile(feed.filename):
                button = Gtk.Button(_("Redownload"))
                button.connect("clicked", button_download_handler, feed)
            else:
                button = Gtk.Button(_("Download"))
                button.connect("clicked", button_download_handler, feed)
            button_box.pack_start(button, False, False, 0)

            for action in feed.get_feed_actions():
                button = Gtk.Button(action.name)
                button.connect("clicked", button_action_handler, action)
                button_box.pack_start(button, False, False, 0)

        if isinstance(obj, RadioStation):
            button = Gtk.Button(_("Play"))
            button.connect("clicked", button_play_handler, obj)
            button_box.pack_start(button, False, False, 0)

            # check for streamripper, before displaying record button
            try:
                process = subprocess.Popen("streamripper", stdout=subprocess.PIPE)
                process.communicate()
                process.wait()
            except(OSError):
                print("streamripper not found")
            else:
                button = Gtk.Button(_("Record"))
                button.connect("clicked", button_record_handler, obj)
                button_box.pack_start(button, False, False, 0)

            data = self.load_from_file(os.path.join(self.cache_dir, BOOKMARKS_FILENAME))
            if data is None:
                data = {}
            if station.server_name not in data:
                button = Gtk.Button(_("Bookmark"))
            else:
                button = Gtk.Button(_("Unbookmark"))
            button.connect("clicked", button_bookmark_handler, obj)
            button_box.pack_start(button, False, False, 0)

            if station.type in list(self.station_actions.keys()):
                actions = self.station_actions[station.type]
                for action in actions:
                    button = Gtk.Button(action.name)
                    button.connect("clicked", button_station_action_handler, action, obj)
                    button_box.pack_start(button, False, False, 0)

        sub_info_box = Gtk.HBox()
        sub_info_box.pack_start(info_container, True, True, 0)  #dm
        sub_info_box.pack_start(button_box, False, False, 0)

        decorated_info_box = Gtk.Frame()
        decorated_info_box.set_label("Info box")
        decorated_info_box.add(sub_info_box)

        info_box.pack_start(decorated_info_box, True, True, 0)  #dm
        print(decorated_info_box)
        info_box.show_all()
        print("finished info box routine")

    """ icon download worker thread function """

    def icon_download_worker(self):
        print("icon_download_worker")
        while True:
            filepath, src = self.icon_download_queue.get()

            if os.path.exists(filepath) is False:
                if src.lower().startswith("http://"):
                    try:
                        urllib.request.urlretrieve(src, filepath)
                    except:
                        pass

            self.icon_download_queue.task_done()

    """ tries to load icon from disk and if found it saves it in cache returns it """

    def get_icon_pixbuf(self, filepath, return_value_not_found=None):
        if os.path.exists(filepath):
            icon = None

            if filepath in self.icon_cache:
                return self.icon_cache[filepath]
            else:
                try:
                    what, width, height = Gtk.icon_size_lookup(Gtk.IconSize.BUTTON)
                    icon = Pixbuf.new_from_file_at_size(filepath, width, height)
                except:
                    icon = return_value_not_found
                self.icon_cache[filepath] = icon

            return icon
        return return_value_not_found

    """ data display function for tree view """

    def model_data_func(self, column, cell, model, iter, infostr):
        obj = model.get_value(iter, 1)
        self.clef_icon = self.get_icon_pixbuf(rb.find_plugin_file(self.plugin, "note.png"))

        if infostr == "image":
            icon = None
            if isinstance(obj, RadioStation):
                station = obj
                # default icon
                icon = self.clef_icon

                # icons for special feeds
                if station.type == "Shoutcast":
                    icon = self.get_icon_pixbuf(rb.find_plugin_file(self.plugin, "shoutcast-logo.png"))
                if station.type == "Icecast":
                    icon = self.get_icon_pixbuf(rb.find_plugin_file(self.plugin, "xiph-logo.png"))
                if station.type == "Board":
                    icon = self.get_icon_pixbuf(rb.find_plugin_file(self.plugin, "local-logo.png"))

                # most special icons, if the station has one for itsself
                if station.icon_src != "":
                    hash_src = hashlib.md5(station.icon_src.encode('utf-8')).hexdigest()
                    filepath = os.path.join(self.icon_cache_dir, hash_src)
                    if os.path.exists(filepath):
                        icon = self.get_icon_pixbuf(filepath, icon)
                    else:
                        # load icon
                        self.icon_download_queue.put([filepath, station.icon_src])

            if icon is None:
                cell.set_property("stock-id", Gtk.STOCK_DIRECTORY)
            else:
                cell.set_property("pixbuf", icon)

    """ transmits station information to board """

    def transmit_station(self, station):
        print("transmit_station")
        params = urllib.parse.urlencode(
            {'action': 'clicked', 'name': station.server_name, 'url': station.getRealURL(), 'source': station.type})
        f = urllib.request.urlopen(BOARD_ROOT + "?%s" % params)
        f.read()
        print("Transmit station '" + str(station.server_name) + "' OK")

    """ transmits title information to board """
    """def transmit_title(self,title):
        params = urllib.urlencode({'action':'streaming','name': self.station.server_name,'url': self.station.getRealURL(),'source':self.station.type,'title':title})
        f = urllib.urlopen(BOARD_ROOT+"?%s" % params)
        f.read()
        print "Transmit title '"+str(title)+"' OK"
    """
    """ stream information listener """

    def info_available(self, player, uri, field, value):
        print("info_available")
        if field == RB_METADATA_FIELD_TITLE:
            self.title = value
            self.set_streaming_title(self.title)
            #transmit_thread = threading.Thread(target = self.transmit_title,args = (value,))
            #transmit_thread.setDaemon(True)
            #transmit_thread.start()
            #print "setting title to:"+value

        elif field == RB_METADATA_FIELD_GENRE:
            self.genre = value
            ## causes warning: RhythmDB-WARNING **: trying to sync properties of non-editable file
            #self.shell.props.db.set(self.entry, rhythmdb.PROP_GENRE, value)
            #self.shell.props.db.commit()
            #print "setting genre to:"+value

        elif field == RB_METADATA_FIELD_BITRATE:
            ## causes warning: RhythmDB-WARNING **: trying to sync properties of non-editable file
            #self.shell.props.db.set(self.entry, rhythmdb.PROP_BITRATE, value/1000)
            #self.shell.props.db.commit()
            #print "setting bitrate to:"+str(value/1000)
            pass

        else:
            print("Server sent unknown info '" + str(field) + "':'" + str(value) + "'")

        #   def playing_changed (self, sp, playing):
        #       print "playing changed"

        #   def playing_entry_changed (self, sp, entry):
        #       print "playing entry changed"

        #   def playing_song_property_changed (self, sp, uri, property, old, new):
        #       print "property changed "+str(new)

    def record_uri(self, station):
        print("record_uri")
        play_thread = threading.Thread(target=self.play_uri_, args=(station, True))
        play_thread.setDaemon(True)
        play_thread.start()

    """ listener for filter entry change """

    def filter_entry_changed(self, Gtk_entry):
        print("filter_entry_changed")
        if self.filter_entry.get_text() == "" and self.filter_entry_genre.get_text() == "":
            print("entry and genre are empty")
            self.tree_view_container.show()
            self.icon_view_container.hide()
        else:
            print("entry or genre has a value")
            self.tree_view_container.hide()
            self.icon_view_container.show()

        self.icon_view.set_model(None)
        if not self.filtered_icon_view_store == None:
            self.filtered_icon_view_store.refilter()
            self.icon_view.set_model(self.filtered_icon_view_store)

        self.notify_status_changed()

    """ callback for item filtering """

    def list_store_visible_func(self, model, iter, destroy):
        #print "list_store_visible_func"
        # returns true if the row should be visible
        if len(model) == 0:
            return True
        obj = model.get_value(iter, 1)
        if isinstance(obj, RadioStation):
            station = obj
            try:
                bitrate = int(station.bitrate)
                min_bitrate = int(float(self.filter_entry_bitrate.get_value()))
                if bitrate < min_bitrate:
                    return False
            except:
                pass

            filter_string = self.filter_entry.get_text().lower()
            if filter_string != "":
                if station.server_name.lower().find(filter_string) < 0:
                    return False

            filter_string = self.filter_entry_genre.get_text().lower()
            if filter_string != "":
                genre = station.genre
                if genre is None:
                    genre = ""
                if genre.lower().find(filter_string) < 0:
                    return False

            return True
        else:
            return True

    """ handler for update toolbar button """

    def update_button_clicked(self, widget):
        print("update_button_clicked")
        if not self.updating:
            # delete cache files
            files = os.listdir(self.cache_dir)
            for filename in files:
                if filename.endswith("xml"):
                    filepath = os.path.join(self.cache_dir, filename)
                    os.unlink(filepath)
            # start filling again
            self.refill_list()

    def clear_iconcache_button_clicked(self, widget):
        print("clear_iconcache_button_clicked")
        if not self.updating:
            # delete cache files
            files = os.listdir(self.icon_cache_dir)
            for filename in files:
                filepath = os.path.join(self.icon_cache_dir, filename)
                os.unlink(filepath)
            # delete internal cache
            self.icon_cache = {}
            # start filling again
            self.refill_list()
        pass

    """ starts playback of the station """

    def play_uri(self, station):
        print("play_uri")
        station.updateRealURL()
        play_thread = threading.Thread(target=self.play_uri_, args=(station,))
        play_thread.setDaemon(True)
        play_thread.start()

    def play_uri_(self, station, record=False):
        print("play_uri_")
        # do not play while downloading
        if self.updating:
            return

        # try downloading station information
        tryno = 0
        self.updating = True
        while True:
            tryno += 1

            Gdk.threads_enter()
            self.load_status = _("downloading station information") + " '" + station.server_name + "', " + _(
                "Try") + ":" + str(tryno) + "/" + str(math.floor(float(self.plugin.download_trys)))
            self.load_total_size = 0
            self.notify_status_changed()
            Gdk.threads_leave()

            if station.getRealURL() is not None:
                break
            if tryno >= float(self.plugin.download_trys):
                Gdk.threads_enter()
                self.load_status = ""
                self.updating = False
                self.notify_status_changed()
                message = Gtk.MessageDialog(message_format=_("Could not download station information"),
                                            buttons=Gtk.ButtonsType.OK, type=Gtk.MessageType.ERROR)
                message.format_secondary_text(_(
                    "Could not download station information from shoutcast directory server. Please try again later."))
                response = message.run()
                message.destroy()
                Gdk.threads_leave()
                return

        if not station.listen_url.startswith("http://127.0.0.1"):
            # add to recently played
            data = self.load_from_file(os.path.join(self.cache_dir, RECENTLY_USED_FILENAME))
            if data is None:
                data = {}
            if station.server_name not in data:
                try:
                    self.tree_store.append(self.recently_iter, (station.server_name, station))
                except:
                    pass
                data[station.server_name] = station
                data[station.server_name].PlayTime = datetime.datetime.now()
            else:
                data[station.server_name].PlayTime = datetime.datetime.now()

            self.save_to_file(os.path.join(self.cache_dir, RECENTLY_USED_FILENAME), data)

        Gdk.threads_enter()
        self.load_status = ""
        self.updating = False
        self.notify_status_changed()

        if record:
            def short_name(name):
                maxlen = 30
                if len(name) > maxlen:
                    return name[0:maxlen - 3] + "..."
                else:
                    return name

            uri = station.getRealURL()

            # do not record the same stream twice
            if uri in self.recording_streams:
                if self.recording_streams[uri].process.poll() is None:
                    return
            self.recording_streams[uri] = RecordProcess(station, self.plugin.outputpath, self.play_uri, self.shell)
            self.notebook.append_page(self.recording_streams[uri], Gtk.Label(short_name(station.server_name)))
            self.recording_streams[uri].start()
            self.notebook.set_current_page(self.notebook.page_num(self.recording_streams[uri]))
        else:
            # get player
            player = self.shell.props.shell_player
            player.stop()

            # create new entry to play
            entry = self.db.entry_lookup_by_location(station.getRealURL())
            if entry == None:
                #self.shell.props.db.entry_delete(self.entry)
                entry = RB.RhythmDBEntry.new(self.db, self.entry_type, station.getRealURL())
                #               self.entry = self.shell.props.db.entry_new(self.entry_type, station.getRealURL())
                print(station.getRealURL())
                print(station.getId())
                #               server = station.server_name
                #               self.db.entry_set(entry,RB.RhythmDBPropType.TITLE, server)
                self.db.entry_set(entry, RB.RhythmDBPropType.TITLE, station.getId())
                self.db.commit()

            #shell.load_uri(uri,False)

            # start playback
            player.play_entry(entry, self)

        Gdk.threads_leave()

        # transmit station click to station board (statistic) """
        transmit_thread = threading.Thread(target=self.transmit_station, args=(station,))
        transmit_thread.setDaemon(True)
        transmit_thread.start()

    """ handler for double clicks in tree view """

    def row_activated_handler(self, treeview, path, column):
        print("row_activated_handler (treeview double click)")
        model = treeview.get_model()
        myiter = model.get_iter(path)

        obj = model.get_value(myiter, 1)
        if obj == None:
            return

        if isinstance(obj, RadioStation):
            station = obj
            if station is not None:
                self.play_uri(station)

        if isinstance(obj, Feed):
            feed = obj
            transmit_thread = threading.Thread(target=self.download_feed, args=(feed,))
            transmit_thread.setDaemon(True)
            transmit_thread.start()

    def download_feed(self, feed):
        print("download_feed")
        tryno = 0
        self.updating = True
        while True:
            tryno += 1

            Gdk.threads_enter()
            self.load_status = _("Downloading feed %(name)s from %(url)s. %(try)d/%(trys)d") % {'name': feed.name(),
                                                                                                'url': feed.uri,
                                                                                                'try': tryno, 'trys': (
                                                                        math.floor(float(self.plugin.download_trys)))}
            self.load_total_size = 0
            self.notify_status_changed()
            Gdk.threads_leave()

            if feed.download():
                break

            if tryno >= float(self.plugin.download_trys):
                Gdk.threads_enter()
                self.load_status = ""
                self.updating = False
                self.notify_status_changed()
                message = Gtk.MessageDialog(message_format=_("Feed download failed"), buttons=Gtk.ButtonsType.OK,
                                            type=Gtk.MessageType.ERROR)
                message.format_secondary_text(_("Could not download feed. Please try again later."))
                response = message.run()
                message.destroy()
                Gdk.threads_leave()
                return

        self.refill_list()

    def do_impl_delete_thyself(self):
        print("do_impl_delete_thyself")
        if self.hasActivated:
            # kill all running records
            for uri in list(self.recording_streams.keys()):
                self.recording_streams[uri].stop()
            self.shell = False

    def engines(self):
        print("engines")
        yield FeedIcecast(self.cache_dir,self.update_download_status)
        yield FeedBoard(self.cache_dir, self.update_download_status)
        #yield FeedShoutcast(self.cache_dir,self.update_download_status)
        #yield FeedRadioTime(self.cache_dir,self.update_download_status)
        #yield FeedRadioTimeLocal(self.cache_dir,self.update_download_status)

    def get_stock_icon(self, name):
        #print "get_stock_icon"
        theme = Gtk.icon_theme_get_default()
        return theme.load_icon(name, 48, 0)

    def load_icon_file(self, filepath, value_not_found):
        #print "load_icon_file"
        icon = value_not_found
        try:
            icon = Pixbuf.new_from_file_at_size(filepath, 72, 72)
        except:
            icon = value_not_found
        return icon

    def get_station_icon(self, station, default_icon):
        #print "get_station_icon"
        # default icon
        icon = default_icon

        # most special icons, if the station has one for itself
        if station.icon_src != "":
            if station.icon_src is not None:
                hash_src = hashlib.md5(station.icon_src.encode('utf-8')).hexdigest()
                filepath = os.path.join(self.icon_cache_dir, hash_src)
                if os.path.exists(filepath):
                    icon = self.load_icon_file(filepath, icon)
                else:
                    # load icon
                    self.icon_download_queue.put([filepath, station.icon_src])
        return icon

    def insert_feed(self, feed, parent):
        # preload most used icons
        note_icon = self.load_icon_file(rb.find_plugin_file(self.plugin, "note.png"), None)
        shoutcast_icon = self.load_icon_file(rb.find_plugin_file(self.plugin, "shoutcast-logo.png"), None)
        xiph_icon = self.load_icon_file(rb.find_plugin_file(self.plugin, "xiph-logo.png"), None)
        local_icon = self.load_icon_file(rb.find_plugin_file(self.plugin, "local-logo.png"), None)

        Gdk.threads_enter()
        self.load_status = _("Loading feed %(name)s") % {'name': feed.name(), }
        self.load_total_size = 0
        self.notify_status_changed()
        Gdk.threads_leave()

        # create main feed root item
        current_iter = self.tree_store.append(parent, (feed.name(), feed))

        # initialize dicts for iters
        genres = {}
        countries = {}
        subcountries = {}
        streamtypes = {}
        bitrates = {}

        # load entries
        entries = feed.entries()

        Gdk.threads_enter()
        self.load_status = _("Integrating feed %(name)s (%(itemcount)d items) into tree...") % {'name': feed.name(),
                                                                                                'itemcount': len(
                                                                                                    entries)}
        self.notify_status_changed()
        Gdk.threads_leave()

        def short_name(name):
            maxlen = 50
            if len(name) > maxlen:
                return name[0:maxlen - 3] + "..."
            else:
                return name

        self.load_total_size = len(entries)
        self.load_current_size = 0

        stations_count = 0

        print ("###################")
        print (len(entries))
        for obj in entries:
            if isinstance(obj, Feed):
                sub_feed = obj
                # add sub feed to treeview
                stations_count += self.insert_feed(sub_feed, current_iter)

            elif isinstance(obj, RadioStation):
                stations_count += 1
                station = obj
                # add subitems for sorting, if there are stations
                if self.load_current_size == 0:
                    genre_iter = self.tree_store.append(current_iter, (_("By Genres"), None))
                    country_iter = self.tree_store.append(current_iter, (_("By Country"), None))
                    streamtype_iter = self.tree_store.append(current_iter, (_("By Streamtype"), None))
                    bitrate_iter = self.tree_store.append(current_iter, (_("By Bitrate"), None))

                # display status info in statusbar
                self.load_current_size += 1
                Gdk.threads_enter()
                if self.load_current_size % 50 == 0:
                    self.notify_status_changed()
                Gdk.threads_leave()

                # default icon
                icon = note_icon
                # icons for special feeds
                if station.type == "Shoutcast":
                    icon = shoutcast_icon
                if station.type == "Icecast":
                    icon = xiph_icon
                if station.type == "Board":
                    icon = local_icon

                # add new station to liststore of search-view too
                self.icon_view_store.append(
                    (short_name(station.server_name), station, self.get_station_icon(station, icon)))

                # add station to treeview, by streamtype
                if station.server_type not in streamtypes:
                    streamtypes[station.server_type] = self.tree_store.append(streamtype_iter,
                                                                              (station.server_type, None))
                self.tree_store.append(streamtypes[station.server_type], (station.server_name, station))

                # add station to treeview, by bitrate
                br = station.bitrate
                try:
                    br_int = int(br)
                    br = str((((br_int - 1) / 32) + 1) * 32)
                    if br_int > 512:
                        br = _("Invalid")
                except:
                    pass
                if br not in bitrates:
                    bitrates[br] = self.tree_store.append(bitrate_iter, (br, None))
                self.tree_store.append(bitrates[br], (station.server_name, station))

                # add station to treeview, by genre
                if station.genre is not None:
                    for genre in station.genre.split(","):
                        genre = genre.strip().lower()
                        if genre not in genres:
                            genres[genre] = self.tree_store.append(genre_iter, (genre, None))
                        self.genre_list[genre] = 1
                        self.tree_store.append(genres[genre], (station.server_name, station))

                # add station to treeview, by country
                country_arr = station.country.split("/")
                if country_arr[0] not in countries:
                    countries[country_arr[0]] = self.tree_store.append(country_iter, (country_arr[0], None))
                if len(country_arr) == 2:
                    if station.country not in subcountries:
                        subcountries[station.country] = self.tree_store.append(countries[country_arr[0]],
                                                                               (country_arr[1], None))
                    self.tree_store.append(subcountries[station.country], (station.server_name, station))
                else:
                    self.tree_store.append(countries[country_arr[0]], (station.server_name, station))

            else:
                print("ERROR: unknown class type in feed")

        self.tree_store.set_value(current_iter, 0, feed.name() + " (" + str(stations_count) + ")")
        return stations_count

    def refill_list_worker(self):
        print("refill list worker")

        Gdk.threads_enter()  #dm
        self.station_actions = {}
        tree = self.tree_view.set_model(None)
        self.icon_view.set_model(None)
        #self.filter_entry_genre.set_model()
        Gdk.threads_leave()  #dm

        self.updating = True
        # deactivate sorting
        self.icon_view_store = Gtk.ListStore(str, object, GdkPixbuf.Pixbuf)
        self.sorted_list_store.reset_default_sort_func()

        # delete old entries
        self.tree_store.clear()
        self.icon_view_store.clear()

        # add recently played list
        self.recently_iter = self.tree_store.append(None, (_("Recently played"), None))
        data = self.load_from_file(os.path.join(self.cache_dir, RECENTLY_USED_FILENAME))
        if data is None:
            data = {}
        dataNew = {}
        for name, station in list(data.items()):
            if datetime.datetime.now() - station.PlayTime <= datetime.timedelta(
                    days=float(self.plugin.recently_played_purge_days)):
                self.tree_store.append(self.recently_iter, (name, station))
                dataNew[name] = station
        self.save_to_file(os.path.join(self.cache_dir, RECENTLY_USED_FILENAME), dataNew)

        # add bookmarks
        self.bookmarks_iter = self.tree_store.append(None, (_("Bookmarks"), None))
        data = self.load_from_file(os.path.join(self.cache_dir, BOOKMARKS_FILENAME))
        if data is None:
            data = {}
        for name, station in list(data.items()):
            self.tree_store.append(self.bookmarks_iter, (name, station))

        # initialize genre dict for genre filter combobox
        self.genre_list = {}

        for feed in self.engines():
            try:
                self.station_actions[feed.name()] = feed.get_station_actions()
                self.insert_feed(feed, None)
            except Exception as e:
                print("error with source:" + feed.name())
                print("error:" + str(e))

        self.genre_liststore = Gtk.ListStore(GObject.TYPE_STRING)
        self.genre_liststore.append(("",))
        for key in list(self.genre_list.keys()):
            self.genre_liststore.append((key,))
        self.genre_liststore.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        completion = Gtk.EntryCompletion()
        completion.set_text_column(0)
        completion.set_model(self.genre_liststore)
        self.filter_entry_genre.set_completion(completion)

        # activate sorting
        self.sorted_list_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.icon_view_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        # connect model to view
        print("connect filter to view")
        self.filtered_icon_view_store = self.icon_view_store.filter_new()
        self.filtered_icon_view_store.set_visible_func(self.list_store_visible_func)
        Gdk.threads_enter()  #dm
        self.tree_view.set_model(self.sorted_list_store)
        self.icon_view.set_model(self.filtered_icon_view_store)
        print("filter set model to tree and icon views")

        #Gdk.threads_enter()
        self.updating = False
        self.notify_status_changed()
        Gdk.threads_leave()

        print("refill list worker")

    def refill_list(self):
        print("refill list")
        self.list_download_thread = threading.Thread(target=self.refill_list_worker)
        self.list_download_thread.setDaemon(True)
        self.list_download_thread.start()

    def load_from_file(self, filename):
        print("load_from_file")
        if not os.path.isfile(filename):
            return None

        try:
            f = open(filename, "rb")
            p = pickle.Unpickler(f)
            data = p.load()
            f.close()
            return data
        except:
            print("load file did not work:" + filename)
            return None

    def save_to_file(self, filename, obj):
        print("save_to_file")
        f = open(filename, "wb")
        p = pickle.Pickler(f)
        p.dump(obj)
        f.close()


GObject.type_register(RadioBrowserSource)

