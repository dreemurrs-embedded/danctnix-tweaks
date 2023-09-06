import os
import subprocess
import tempfile

import gi

from pmos_tweaks.settingstree import SettingsTree

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Pango

gi.require_version('Handy', '1')
from gi.repository import Handy


class TweaksWindow(Handy.ApplicationWindow):
    def __init__(self, application, datadir):
        super().__init__(application=application, title='postmarketOS Tweaks')

        self.titlebar = None
        self.titleleaflet = None
        self.headerbar_side = None
        self.headerbar = None
        self.headergroup = None
        self.leaflet = None
        self.sidebar = None
        self.content = None
        self.listbox = None
        self.stack = None
        self.back = None

        self.sg_sidebar = None
        self.sg_main = None

        self.set_default_size(640, 480)
        self.init_window()

        self.settings = SettingsTree()
        if datadir:
            self.settings.load_dir(os.path.join(datadir, 'postmarketos-tweaks'))
        self.settings.load_dir('/etc/postmarketos-tweaks')
        self.settings.load_dir('settings')
        self.settings.load_dir('../settings')

        self.create_pages()
        self.show_all()

    def init_window(self):
        self.sg_sidebar = Gtk.SizeGroup()
        self.sg_sidebar.set_mode(Gtk.SizeGroupMode.HORIZONTAL)
        self.sg_main = Gtk.SizeGroup()
        self.sg_main.set_mode(Gtk.SizeGroupMode.HORIZONTAL)

        self.headergroup = Handy.HeaderGroup()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(box)

        self.titlebar = Gtk.Box()
        self.titleleaflet = Handy.Leaflet()
        self.titlebar.add(self.titleleaflet)

        self.headerbar_side = Handy.HeaderBar()
        self.headerbar_side.set_show_close_button(True)
        self.titleleaflet.add(self.headerbar_side)
        self.titleleaflet.child_set(self.headerbar_side, name="sidebar")
        leaflet_sep = Gtk.Separator()
        leaflet_sep.get_style_context().add_class('sidebar')
        self.titleleaflet.add(leaflet_sep)

        self.headerbar = Handy.HeaderBar()
        self.titleleaflet.add(self.headerbar)
        self.titleleaflet.child_set(self.headerbar, name="content")
        self.headerbar.set_title("postmarketOS Tweaks")
        self.headerbar.set_show_close_button(True)
        self.headerbar.set_hexpand(True)

        self.headergroup.add_header_bar(self.headerbar_side)
        self.headergroup.add_header_bar(self.headerbar)

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
        leaflet_sep = Gtk.Separator()
        leaflet_sep.get_style_context().add_class('sidebar')
        self.leaflet.add(leaflet_sep)
        self.leaflet.add(self.content)
        self.leaflet.child_set(self.content, name="content")
        self.leaflet.set_visible_child_name("sidebar")

        self.sg_sidebar.add_widget(self.headerbar_side)
        self.sg_sidebar.add_widget(self.sidebar)

        self.sg_main.add_widget(self.headerbar)
        self.sg_main.add_widget(self.content)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.sidebar.pack_start(sw, True, True, 0)
        self.listbox = Gtk.ListBox()
        self.listbox.connect('row-activated', self.on_select_page)
        sw.add(self.listbox)

        self.stack = Gtk.Stack()
        self.content.pack_start(self.stack, True, True, 0)

        box.pack_start(self.titlebar, False, True, 0)
        box.pack_start(self.leaflet, True, True, 0)

        self.actionbar = Gtk.ActionBar()
        self.action_revealer = Gtk.Revealer()
        box.pack_start(self.action_revealer, False, True, 0)
        self.action_revealer.add(self.actionbar)
        label = Gtk.Label(label="You have changed settings that need root"
                          " permissions to save.", xalign=0.0)
        label.set_line_wrap(True)
        self.actionbar.pack_start(label)
        self.action_button = Gtk.Button.new_with_label("Apply")
        self.action_button.get_style_context().add_class('suggested-action')
        self.actionbar.pack_end(self.action_button)
        self.action_button.connect('clicked', self.on_save_settings)

    def create_pages(self):

        # Generate the items in the sidebar
        for page in self.settings.settings:
            label = Gtk.Label(label=page, xalign=0.0)
            label.set_margin_top(8)
            label.set_margin_bottom(8)
            label.set_margin_left(10)
            label.set_margin_right(10)
            label.set_name('row')
            row = Gtk.ListBoxRow()
            row.add(label)
            row.name = page
            row.title = page
            self.listbox.add(row)

        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)

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
                has_settings = False
                for name in self.settings.settings[page]['sections'][section]['settings']:
                    setting = self.settings.settings[page]['sections'][section]['settings'][name]
                    if setting.valid:
                        has_settings = True
                if not has_settings:
                    continue
                label = Gtk.Label(label=section, xalign=0.0)
                label.get_style_context().add_class('heading')
                label.set_margin_bottom(8)
                label.set_margin_top(16)
                box.pack_start(label, False, True, 0)
                frame = Gtk.ListBox()
                frame.set_selection_mode(Gtk.SelectionMode.NONE)
                frame.get_style_context().add_class('content')
                frame.set_margin_bottom(12)
                box.pack_start(frame, False, True, 0)

                for name in self.settings.settings[page]['sections'][section]['settings']:
                    setting = self.settings.settings[page]['sections'][section]['settings'][name]

                    try:
                        # This throws if the backend encounters an error
                        value = setting.get_value()
                    except Exception:
                        error_label = Gtk.Label(label="{name}: exception occurred loading this"
                                                " setting", xalign = 0.0)
                        import traceback
                        tb = traceback.format_exc()
                        copy_details_button = Gtk.Button(label="Copy exception trace")
                        copy_details_button.connect('clicked', lambda self: \
                                Gtk.Clipboard.get_default(self.get_display()).set_text(tb, -1))
                        info_bar = Gtk.InfoBar()
                        info_bar.set_message_type(Gtk.MessageType.ERROR)
                        info_bar.get_content_area().add(error_label)
                        info_bar.add_action_widget(copy_details_button, 0)
                        frame.add(info_bar)
                        continue

                    sbox = Gtk.Box()
                    sbox.set_margin_top(8)
                    sbox.set_margin_bottom(8)
                    sbox.set_margin_left(8)
                    sbox.set_margin_right(8)
                    lbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                    sbox.pack_start(lbox, True, True, 0)
                    frame.add(sbox)
                    wbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                    sbox.pack_end(wbox, False, False, 0)

                    label = Gtk.Label(label=name, xalign=0.0)
                    lbox.pack_start(label, False, True, 0)

                    if setting.help:
                        hlabel = Gtk.Label(label=setting.help, xalign=0.0)
                        hlabel.get_style_context().add_class('subtitle')
                        hlabel.set_line_wrap(True)
                        lbox.pack_start(hlabel, False, True, 0)

                    if setting.type == 'boolean':
                        widget = Gtk.Switch()
                        widget.set_active(value)

                        # Make sure I leak some memory
                        setting.widget = widget
                        widget.setting = setting

                        widget.connect('notify::active', self.on_widget_changed)

                        setting.connect(self.on_setting_change)
                        wbox.pack_start(widget, False, False, 0)
                    elif setting.type == 'info':
                        widget = Gtk.Label(label=value)
                        widget.set_xalign(0.0)
                        widget.get_style_context().add_class('dim-label')
                        widget.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
                        wbox.pack_start(widget, False, False, 0)
                    elif setting.type == 'choice':
                        widget = Gtk.ComboBoxText()
                        setting.widget = widget
                        widget.setting = setting

                        widget.set_entry_text_column(0)
                        i = 0
                        for key in setting.map:
                            widget.append_text(key)
                            if key == value:
                                widget.set_active(i)
                            i += 1
                        widget.connect('changed', self.on_widget_changed)
                        setting.connect(self.on_setting_change)
                        wbox.pack_start(widget, False, False, 0)
                    elif setting.type == 'font':
                        widget = Gtk.FontButton()
                        setting.widget = widget
                        widget.setting = setting
                        widget.set_font(value)
                        widget.connect('font-set', self.on_widget_changed)
                        setting.connect(self.on_setting_change)
                        wbox.pack_start(widget, False, False, 0)
                    elif setting.type == 'file':
                        widget = Gtk.FileChooserButton()
                        setting.widget = widget
                        widget.setting = setting
                        filename_to_display = value or '~'
                        widget.set_filename(filename_to_display)
                        widget.connect('file-set', self.on_widget_changed)
                        setting.connect(self.on_setting_change)
                        enable = Gtk.Switch()
                        if filename_to_display != '~':
                            enable.set_active(True)
                        enable.setting = setting
                        enable.set_margin_bottom(5)
                        enable.connect('notify::active', self.on_widget_changed)
                        widget.null_switch = enable
                        enable.target = widget
                        switchbox = Gtk.Box()
                        switchbox.add(enable)
                        wbox.add(switchbox)
                        wbox.add(widget)
                    elif setting.type == 'color':
                        widget = Gtk.ColorButton()
                        setting.widget = widget
                        widget.setting = setting
                        if value.startswith('#'):
                            color = Gdk.color_parse(value)
                            widget.set_color(color)
                        widget.connect('color-set', self.on_widget_changed)
                        setting.connect(self.on_setting_change)
                        wbox.pack_start(widget, False, False, 0)
                    elif setting.type == 'number':
                        value_to_display = value
                        if 'percentage' in setting.definition and setting.definition['percentage']:
                            w_min = 0
                            w_max = 100
                            w_step = 1
                            val_range = setting.definition['max'] - setting.definition['min']
                            value_to_display = int((value - setting.definition['min']) \
                                                   / val_range * 100)

                        else:
                            w_min = setting.definition['min']
                            w_max = setting.definition['max']
                            w_step = setting.definition['step']
                        widget = Gtk.SpinButton.new_with_range(w_min, w_max, w_step)
                        setting.widget = widget
                        widget.setting = setting
                        if value_to_display is not None:
                            widget.set_value(float(value_to_display))
                        widget.connect('value-changed', self.on_widget_changed)
                        setting.connect(self.on_setting_change)
                        wbox.pack_start(widget, False, False, 0)

        self.leaflet.set_visible_child_name('sidebar')

    def on_setting_change(self, setting, value):
        if setting.type == 'boolean':
            setting.widget.set_active(value)
        elif setting.type == 'choice':
            i = 0
            for key in setting.map:
                if key == value:
                    setting.widget.set_active(i)
                i += 1
        elif setting.type == 'font':
            setting.widget.set_font(value)
        elif setting.type == 'file':
            if value is None:
                value = '~'
            setting.widget.set_filename(value)
        elif setting.type == 'number':
            if 'percentage' in setting.definition and setting.definition['percentage']:
                val_range = setting.definition['max'] - setting.definition['min']
                value = int((value - setting.definition['min']) / val_range * 100)
            setting.widget.set_value(value)

    def on_widget_changed(self, widget, *args):
        setting = widget.setting
        if setting.needs_root:
            self.action_revealer.set_reveal_child(True)
        if setting.type == 'boolean':
            setting.set_value(widget.get_active())
        elif setting.type == 'choice':
            setting.set_value(widget.get_active_text())
        elif setting.type == 'font':
            setting.set_value(widget.get_font())
        elif setting.type == 'file':
            if hasattr(widget, 'null_switch'):
                # Filechooser changed
                setting.set_value(widget.get_filename())
                widget.null_switch.set_active(True)
            else:
                # Null switch changed
                if widget.get_active():
                    return
                else:
                    setting.set_value(None)
                    widget.target.set_filename("~")

        elif setting.type == 'number':
            value = widget.get_value()
            if 'percentage' in setting.definition and setting.definition['percentage']:
                val_range = setting.definition['max'] - setting.definition['min']
                value = (value / 100 * val_range) + setting.definition['min']
            setting.set_value(value)
        elif setting.type == 'color':
            value = widget.get_color().to_string()
            value = '#' + value[1:3] + value[5:7] + value[9:11]
            setting.set_value(value)

    def on_select_page(self, widget, row):
        if self.listbox.get_selection_mode() == Gtk.SelectionMode.NONE:
            self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
            self.listbox.select_row(row)
        self.stack.set_visible_child_name(row.name)
        self.headerbar.set_subtitle(row.title)
        self.leaflet.set_visible_child_name('content')

        # In folded view unselect the row in the listbox
        # so it's possible to go back to the same page
        if self.leaflet.get_folded():
            self.listbox.unselect_row(row)

    def on_back_clicked(self, widget, *args):
        self.leaflet.set_visible_child_name('sidebar')
        self.headerbar.set_subtitle('')

    def on_leaflet_change(self, *args):
        self.titleleaflet.set_visible_child_name(self.leaflet.get_visible_child_name())
        self.back.set_visible(self.leaflet.get_folded())
        if self.leaflet.get_folded():
            self.headerbar_side.set_title("postmarketOS Tweaks")
        else:
            self.headerbar_side.set_title("")

    def on_save_settings(self, *args):
        fd, filename = tempfile.mkstemp()
        with open(filename, 'w') as handle:
            self.settings.save_tweakd_config(handle)

        subprocess.run(['pkexec', 'pk-tweaks-action', filename])

        self.action_revealer.set_reveal_child(False)
