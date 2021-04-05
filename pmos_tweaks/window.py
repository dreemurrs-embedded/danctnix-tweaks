import os

import gi

from pmos_tweaks.settingstree import SettingsTree

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, GObject, Gio, Gdk, GLib

gi.require_version('Handy', '1')
from gi.repository import Handy


class TweaksWindow:
    def __init__(self, application, datadir):
        self.application = application

        Handy.init()

        self.window = None
        self.headerbar = None
        self.leaflet = None
        self.sidebar = None
        self.content = None
        self.listbox = None
        self.stack = None
        self.back = None

        self.create_window()

        self.settings = SettingsTree()
        if datadir:
            self.settings.load_dir(os.path.join(datadir, 'postmarketos-tweaks'))
        self.settings.load_dir('/etc/postmarketos-tweaks')
        self.settings.load_dir('settings')
        self.settings.load_dir('../settings')

        self.create_pages()
        self.window.show_all()
        Gtk.main()

    def create_window(self):
        self.window = Handy.Window()
        self.window.set_title('postmarketOS Tweaks')
        self.window.connect('destroy', self.on_main_window_destroy)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.add(box)

        self.headerbar = Handy.HeaderBar()
        self.headerbar.set_title("postmarketOS Tweaks")
        self.headerbar.set_show_close_button(True)

        self.back = Gtk.Button.new_from_icon_name("go-previous-symbolic", 1)
        self.back.connect("clicked", self.on_back_clicked)
        self.back.set_visible(False)
        self.back.set_no_show_all(True)
        self.headerbar.pack_start(self.back)

        self.leaflet = Handy.Leaflet()
        self.leaflet.set_transition_type(Handy.LeafletTransitionType.SLIDE)
        self.leaflet.connect("notify::folded", self.on_leaflet_change)
        self.leaflet.connect("notify::visible-child", self.on_leaflet_change)
        self.sidebar = Gtk.Box()
        self.sidebar.set_size_request(200, 0)
        self.content = Gtk.Box()
        self.content.props.hexpand = True
        self.leaflet.add(self.sidebar)
        self.leaflet.child_set(self.sidebar, name="sidebar")
        self.leaflet.add(self.content)
        self.leaflet.child_set(self.content, name="content")
        self.leaflet.set_visible_child_name("sidebar")

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.sidebar.pack_start(sw, True, True, 0)
        self.listbox = Gtk.ListBox()
        self.listbox.connect('row-selected', self.on_select_page)
        sw.add(self.listbox)

        self.stack = Gtk.Stack()
        self.content.pack_start(self.stack, True, True, 0)

        box.pack_start(self.headerbar, False, True, 0)
        box.pack_start(self.leaflet, True, True, 0)

    def create_pages(self):

        # Generate the items in the sidebar
        for page in self.settings.settings:
            label = Gtk.Label(label=page, xalign=0.0)
            label.set_margin_top(7)
            label.set_margin_bottom(7)
            label.set_margin_left(10)
            label.set_margin_right(10)
            label.set_name('row')
            row = Gtk.ListBoxRow()
            row.add(label)
            row.name = page
            row.title = page
            self.listbox.add(row)

        for page in self.settings.settings:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            box.set_margin_top(12)
            box.set_margin_bottom(12)
            box.set_margin_left(12)
            box.set_margin_right(12)
            sw = Gtk.ScrolledWindow()
            sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            sw.add(box)
            self.stack.add_named(sw, page)

            for section in self.settings.settings[page]['sections']:
                label = Gtk.Label(label=section, xalign=0.0)
                label.get_style_context().add_class('heading')
                label.set_margin_bottom(4)
                box.pack_start(label, False, True, 0)
                frame = Gtk.Frame()
                frame.get_style_context().add_class('view')
                frame.set_margin_bottom(12)
                box.pack_start(frame, False, True, 0)
                fbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                frame.add(fbox)

                for name in self.settings.settings[page]['sections'][section]['settings']:
                    setting = self.settings.settings[page]['sections'][section]['settings'][name]
                    sbox = Gtk.Box()
                    sbox.set_margin_top(8)
                    sbox.set_margin_bottom(8)
                    sbox.set_margin_left(8)
                    sbox.set_margin_right(8)
                    lbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                    sbox.pack_start(lbox, True, True, 0)
                    fbox.pack_start(sbox, False, True, 0)
                    wbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                    sbox.pack_end(wbox, False, False, 0)

                    label = Gtk.Label(label=name, xalign=0.0)
                    lbox.pack_start(label, False, True, 0)

                    if setting.help:
                        hlabel = Gtk.Label(label=setting.help, xalign=0.0)
                        hlabel.get_style_context().add_class('dim-label')
                        hlabel.set_line_wrap(True)
                        lbox.pack_start(hlabel, False, True, 0)

                    if setting.type == 'boolean':
                        widget = Gtk.Switch()
                        widget.set_active(setting.get_value())

                        # Make sure I leak some memory
                        setting.widget = widget
                        widget.setting = setting

                        widget.connect('notify::active', self.on_widget_changed)

                        setting.connect(self.on_setting_change)
                        wbox.pack_start(widget, False, False, 0)
                    elif setting.type == 'choice':
                        widget = Gtk.ComboBoxText()
                        setting.widget = widget
                        widget.setting = setting

                        widget.set_entry_text_column(0)
                        val = setting.get_value()
                        i = 0
                        for key in setting.map:
                            widget.append_text(key)
                            if key == val:
                                widget.set_active(i)
                            i += 1
                        widget.connect('changed', self.on_widget_changed)
                        setting.connect(self.on_setting_change)
                        wbox.pack_start(widget, False, False, 0)

        widget = self.listbox.get_row_at_index(0)
        self.listbox.select_row(widget)

    def on_setting_change(self, setting, value):
        if setting.type == 'boolean':
            setting.widget.set_active(value)
        elif setting.type == 'choice':
            i = 0
            for key in setting.map:
                setting.widget.append_text(key)
                if key == value:
                    setting.widget.set_active(i)
                i += 1

    def on_widget_changed(self, widget, *args):
        setting = widget.setting
        if setting.type == 'boolean':
            setting.set_value(widget.get_active())
        elif setting.type == 'choice':
            setting.set_value(widget.get_active_text())

    def on_select_page(self, widget, row):
        if row:
            self.stack.set_visible_child_name(row.name)
            self.headerbar.set_subtitle(row.title)
            self.leaflet.set_visible_child_name('content')

    def on_main_window_destroy(self, widget):
        Gtk.main_quit()

    def on_back_clicked(self, widget, *args):
        self.leaflet.set_visible_child_name('sidebar')

    def on_leaflet_change(self, *args):
        folded = self.leaflet.get_folded()
        content = self.leaflet.get_visible_child_name() == "content"
        self.back.set_visible(folded and content)