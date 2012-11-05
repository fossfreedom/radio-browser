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

from threading import Thread
import threading
from gi.repository import GObject
import subprocess
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Gdk
import os
from datetime import datetime

import xml.sax.saxutils

from radio_station import RadioStation

GLib.threads_init()


class RecordProcess(threading.Thread,Gtk.VBox):
    def __init__(self,station,outputpath,play_cb,shell):
        # init base classes
        threading.Thread.__init__(self)
        Gtk.VBox.__init__(self)

        # make shortcuts
        title = station.server_name
        uri = station.getRealURL()
        self.relay_port = ""
        self.server_name = ""
        self.bitrate = ""
        self.song_info = ""
        self.stream_name = ""
        self.filesize = ""
        self.song_start = datetime.now()
        self.play_cb = play_cb
        self.outputpath = outputpath
        self.shell = shell

        # prepare streamripper
        commandline = ["streamripper",uri,"-d",outputpath,"-r","-o","larger"]
        print "streamripper commandline"
        print commandline
        self.process = subprocess.Popen(commandline,stdout=subprocess.PIPE)

        # infobox
        left = Gtk.Table(12,2)
        left.set_col_spacing(0,10)
        self.info_box = left

        right = Gtk.VBox()
        play_button = Gtk.Button(stock=Gtk.STOCK_MEDIA_PLAY,label="")
        right.pack_start(play_button, False, False, 0) #dm
        stop_button = Gtk.Button(stock=Gtk.STOCK_STOP,label="")
        right.pack_start(stop_button, False, False, 0) #dm

        box = Gtk.HBox()
        box.pack_start(left, False, False, 0) #dm
        box.pack_start(right,False, False, 0) #dm was just Falses
        decorated_box = Gtk.Frame()
        decorated_box.set_label("Ripping stream")
        decorated_box.add(box)

        play_button.connect("clicked",self.record_play_button_handler,uri)
        stop_button.connect("clicked",self.record_stop_button_handler)
        
        # song list
        self.songlist = Gtk.TreeView()
        self.songlist.connect('row-activated', self.open_file)
        self.songlist_store = Gtk.TreeStore(int,str,str)
        self.songlist_store.set_sort_column_id(0,Gtk.SortType.DESCENDING)
        self.songlist.set_model(self.songlist_store)

        column_time_cell = Gtk.CellRendererText()
        column_time_cell.set_property('xalign', 0.0)
        column_time = Gtk.TreeViewColumn(_("Time"),column_time_cell)
        column_time.set_cell_data_func(column_time_cell,self.display_cb)
        self.songlist.append_column(column_time)

        column_title = Gtk.TreeViewColumn(_("Title"),Gtk.CellRendererText(),text=1)
        self.songlist.append_column(column_title)

        column_size_cell = Gtk.CellRendererText()
        column_size_cell.set_property('xalign', 1.0)
        column_size = Gtk.TreeViewColumn(_("Filesize"),column_size_cell,text=2)
        column_size.set_alignment(1.0)
        self.songlist.append_column(column_size)

        tree_view_container = Gtk.ScrolledWindow()
        tree_view_container.set_shadow_type(Gtk.ShadowType.IN)
        tree_view_container.add(self.songlist)
        tree_view_container.set_property("hscrollbar-policy", Gtk.PolicyType.AUTOMATIC)

        self.pack_start(decorated_box,False,False,0) #dm was just false
        self.pack_start(tree_view_container,True,True,0) #dm
        self.show_all()

    def open_file(self, treeview, path, column):
        model = treeview.get_model()
        iter = model.get_iter(path)
        filename = os.path.join(os.path.join(self.outputpath, self.stream_name),model.get_value(iter, 1))
        #self.shell.add_to_queue("file:/"+filename)
        #self.shell.load_uri("file:/"+filename,True)
        t = threading.Thread(target = self.play,args = (filename,))
        t.setDaemon(True)
        t.start()
        return

    def display_cb(self,column,cell,model,iter, another):
        seconds = model.get_value(iter,0)
        cell.set_property("text",datetime.fromtimestamp(seconds).strftime("%x %X"))

    def play(self,filename):
        print filename
        subprocess.call(["rhythmbox",filename])

    def refillList(self):
        self.songlist.set_model(None)
        self.songlist_store.clear()

        path = os.path.join(self.outputpath,self.stream_name)
        if os.path.isdir(path):
            for filename in os.listdir(path):
                filepath = os.path.join(path,filename)
                if os.path.isfile(filepath):
                    self.songlist_store.append(None,(int(os.path.getmtime(filepath)),filename,str(os.path.getsize(filepath)/1024)+" kB"))

        self.songlist.set_model(self.songlist_store)

    def set_info_box(self):
        self.added_lines = 0
        def add_label(title,value):
            if not value == "":
                label = Gtk.Label()
                if value.startswith("http://"):
                    label.set_markup("<a href='"+xml.sax.saxutils.escape(value)+"'>"+value+"</a>")
                else:
                    label.set_markup(xml.sax.saxutils.escape(value))
                label.set_selectable(True)
                label.set_alignment(0, 0)

                title_label = Gtk.Label()
                title_label.set_alignment(1, 0)
                title_label.set_markup("<b>"+xml.sax.saxutils.escape(title)+"</b>")

                self.info_box.attach(title_label,0,1,self.added_lines,self.added_lines+1)
                self.info_box.attach(label,1,2,self.added_lines,self.added_lines+1)
                self.added_lines += 1

        for widget in self.info_box.get_children():
            self.info_box.remove(widget)

        add_label(_("Server"),self.server_name)
        add_label(_("Stream"),self.stream_name)
        add_label(_("Current song"),self.song_info)
        playing_time = datetime.now()-self.song_start
        add_label(_("Playing time"),"{0:02d}:{1:02d}".format(playing_time.seconds/60,playing_time.seconds%60))
        add_label(_("Filesize"),self.filesize)
        add_label(_("Bitrate"),self.bitrate)
        add_label(_("Relay port"),str(self.relay_port))

        self.info_box.show_all()

        return False

    def run(self):
        pout = self.process.stdout
        while self.process.poll()==None:
            line = ""
            
            while True:
                try:
                    char = pout.read(1)
                except:
                    print "exception"
                    break

                if char == None or char == "":
                    break

                if char == "\n":
                    break
                if char == "\r":
                    break
                line = line+char

            #print "STREAMRIPPER:"+line
            if line.startswith("relay port"):
                self.relay_port = line.split(":")[1].strip()
            if line.startswith("stream"):
                self.stream_name = line.split(":")[1].strip()
                # refillList depends on stream_name
                self.refillList()
            if line.startswith("server name"):
                self.server_name = line.split(":")[1].strip()
            if line.startswith("declared bitrate"):
                self.bitrate = line.split(":")[1].strip()
            if line.startswith("[ripping") or line.startswith("[skipping"):
                song = line[17:len(line)-10]
                # add old song to list, after recording title changed to new song
                if self.song_info != song:
                    #if self.song_info != "":
                    #   self.songlist_store.append((str(self.song_start.strftime("%x %X")),self.song_info,self.filesize))
                    self.song_info = song
                    self.song_start = datetime.now()
                    self.refillList()
                self.filesize = line[len(line)-8:len(line)-1].strip()

            GObject.idle_add(self.set_info_box)

        print "thread closed"
        
        Gdk.threads_enter()
        self.get_parent().set_current_page(0)
        self.get_parent().remove(self)
        Gdk.threads_leave()

    def stop(self):
        if self.process.poll() is None:
            self.process.terminate()

    def record_play_button_handler(self,button,uri):
        station = RadioStation()
        station.server_name = self.stream_name
        station.listen_url = "http://127.0.0.1:"+self.relay_port
        station.type = "local"
        self.play_cb(station)

    def record_stop_button_handler(self,button):
        self.process.terminate()
