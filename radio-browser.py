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
from gi.repository import Peas
from gi.repository import Gtk
from gi.repository import GdkPixbuf
from gi.repository import Gio
#need package gir1.2-gconf-2.0 to be installed
from gi.repository import PeasGtk
from gi.repository import Gio

#import gconf
import os
import rb
from gettext import *

from radio_browser_source import RadioBrowserSource

DIALOG_FILE = 'radio-browser.ui'
DIALOG = 'config_dialog'


class ConfigDialog(GObject.Object, PeasGtk.Configurable):
    __type_name__ = 'RadioBrowserConfigDialog'
    object = GObject.property(type=GObject.Object)

    download_trys = GObject.Property(type=int)
    recently_played_purge_days = GObject.Property(type=int)
    outputpath = GObject.Property(type=str)

    def __init__(self):
        GObject.Object.__init__(self)
        self.settings = Gio.Settings("org.gnome.rhythmbox.plugins.radio-browser")
        self.settings.bind("download-trys",self,"download_trys",Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("recently-played-purge-days",self,"recently_played_purge_days",Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("outputpath",self,"outputpath",Gio.SettingsBindFlags.DEFAULT)
        
        if self.outputpath == "":
            _outputpath = os.path.expanduser("~")
            # try to read xdg music dir
            try:
                f = open(_outputpath + "/.config/user-dirs.dirs", "r")
            except IOError:
                print("xdg user dir file not found")
            else:
                for line in f:
                    if line.startswith("XDG_MUSIC_DIR"):
                        _outputpath = os.path.expandvars(line.split("=")[1].strip().strip('"'))
                        print(_outputpath)
                f.close()
            self.outputpath=_outputpath

    def do_create_configure_widget(self):
        # next define the GUI
        builder = Gtk.Builder()
        file = rb.find_plugin_file(self, DIALOG_FILE)
        builder.add_from_file(file)

        # ... and fill in values found and connect the methods


        self.spin_download_trys = builder.get_object('spin_download_trys')
        self.spin_download_trys.set_adjustment(Gtk.Adjustment(value=1, lower=1, upper=10, step_incr=1))
        self.spin_download_trys.set_value(float(self.download_trys))
        self.spin_download_trys.connect("changed", self.on_spin_download_trys_change_value)
        self.spin_removaltime = builder.get_object('spin_removaltime')
        self.spin_removaltime.set_adjustment(Gtk.Adjustment(value=1, lower=1, upper=7, step_incr=1))
        self.spin_removaltime.connect("changed", self.on_spin_removaltime_change_value)
        self.spin_removaltime.set_value(float(self.recently_played_purge_days))
        self.entry_outputpath = builder.get_object('entry_outputpath')
        self.entry_outputpath.connect("changed", self.on_entry_outputpath_changed)
        self.entry_outputpath.set_text(self.outputpath)
        self.file_browser_button = builder.get_object('file_browser_button')
        self.file_browser_button.connect("clicked", self.on_file_browser_button_clicked)

        return builder.get_object(DIALOG)

    def on_file_browser_button_clicked(self, button):
        print("file browser button")
        filew = Gtk.FileChooserDialog("File selection", action=Gtk.FileChooserAction.SELECT_FOLDER,
                                      buttons=(Gtk.STOCK_CANCEL,
                                               Gtk.ResponseType.REJECT,
                                               Gtk.STOCK_OK,
                                               Gtk.ResponseType.OK))
        filew.set_filename(self.outputpath)
        if filew.run() == Gtk.ResponseType.OK:
            self.entry_outputpath.set_text(filew.get_filename())
        filew.destroy()

    """ immediately change gconf values in config dialog after user changed download trys """
    def on_spin_download_trys_change_value(self,spin):
        self.download_trys = self.spin_download_trys.get_value_as_int()

    """ immediately change gconf values in config dialog after user changed removal days """
    def on_spin_removaltime_change_value(self,spin):
        self.recently_played_purge_days = self.spin_removaltime.get_value_as_int()

    """ immediately change gconf values in config dialog after user changed recorded music output directory """

    def on_entry_outputpath_changed(self, entry):
        print("on outputpath change")
        self.outputpath = self.entry_outputpath.get_text()


class RadioBrowserEntryType(RB.RhythmDBEntryType):
    def __init__(self):
        RB.RhythmDBEntryType.__init__(self, name='RadioBrowserEntryType')


class RadioBrowserPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'RadioBrowserPlugin'
    object = GObject.Property(type=GObject.GObject)

    download_trys = GObject.Property(type=int)
    recently_played_purge_days = GObject.Property(type=int)
    outputpath = GObject.Property(type=str)

    def __init__(self):
        super(RadioBrowserPlugin, self).__init__()

        self.settings = Gio.Settings("org.gnome.rhythmbox.plugins.radio-browser")
        self.settings.bind("download-trys",self,"download_trys",Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("recently-played-purge-days",self,"recently_played_purge_days",Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("outputpath",self,"outputpath",Gio.SettingsBindFlags.DEFAULT)

    def action_update_list(self):
        try:
            self.shell.get_property("selected-source").update_button_clicked()
        except:
            # 0.13.3
            self.shell.get_property("selected-page").update_button_clicked()

    def action_remove_images(self):
        try:
            self.shell.get_property("selected-source").clear_iconcache_button_clicked()
        except:
            # 0.13.3
            self.shell.get_property("selected-page").clear_iconcache_button_clicked()

    """ on plugin activation """

    def do_activate(self):

        # Get the translation file
        install('radio-browser')

        self.shell = self.object
        # register this source in rhythmbox
        db = self.shell.props.db
        try:
            entry_type = RadioBrowserEntryType()
            db.register_entry_type(entry_type)
        except NotImplementedError:
            entry_type = db.entry_register_type("RadioBrowserEntryType")

        entry_type.category = RB.RhythmDBEntryCategory.STREAM

        # load plugin icon
        try:
            theme = Gtk.IconTheme.get_default()
            rb.append_plugin_source_path(theme, "/icons")
        except:
            rb.append_plugin_source_path(self, "/icons")
            
        what, width, height = Gtk.icon_size_lookup(Gtk.IconSize.LARGE_TOOLBAR)
        #pxbf = GdkPixbuf.Pixbuf.new_from_file_at_size(rb.find_plugin_file(self, "radio-browser.png"), width, height)

        group = RB.DisplayPageGroup.get_by_id("library")

        iconfile = Gio.File.new_for_path(
            rb.find_plugin_file(self, 'radio-browser.png'))

        self.source = GObject.new(RadioBrowserSource,
                                  shell=self.shell,
                                  name=_("Radio browser"),
                                  entry_type=entry_type,
                                  plugin=self,
                                  icon=Gio.FileIcon.new(iconfile))

        self.shell.register_entry_type_for_source(self.source, entry_type)
        self.shell.append_display_page(self.source, group)

        #       GObject.type_register(RadioBrowserSource)



        #self.actiongroup = Gtk.ActionGroup('RadioBrowserActionGroup')

        # add "update-all" action to the toolbar
        #action = Gtk.Action('UpdateList', None, _("Update radio station list"), Gtk.STOCK_GO_DOWN)
        #action.connect('activate', lambda a: action_update_list())
        #self.actiongroup.add_action(action)

        #action = Gtk.Action('ClearIconCache', None, _("Clear icon cache"), Gtk.STOCK_CLEAR)
        #action.connect('activate', lambda a: action_remove_images())
        #self.actiongroup.add_action(action)

        #uim = self.shell.props.ui_manager
        #uim.insert_action_group (self.actiongroup)
        #uim.ensure_update()

    """ build plugin configuration dialog """

    def create_configure_dialog(self, dialog=None):
        if not dialog:
            dialog = ConfigDialog(self)
            dialog.connect("response", self.dialog_response)

        dialog.present()
        return dialog

    def dialog_response(self, dialog, response):
        dialog.hide()

    """ on plugin deactivation """

    def do_deactivate(self):
        #uim = self.shell.props.ui_manager
        #uim.remove_action_group(self.actiongroup)
        #self.actiongroup = None
        self.source.delete_thyself()
        self.source = None
