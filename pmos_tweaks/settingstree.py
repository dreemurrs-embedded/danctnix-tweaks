import os
import glob
from collections import OrderedDict
import configparser

import yaml

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gio, Gtk


# Needed for qt5 theming, disabled because qt5 theming is a mess
# from PyQt5 import QtWidgets


class Setting:
    def __init__(self, definition):
        self.name = definition['name']
        self.weight = 50
        if 'weight' in definition:
            self.weight = definition['weight']
        self.type = definition['type']
        self.backend = definition['backend'] if 'backend' in definition else 'gsettings'
        self.help = definition['help'] if 'help' in definition else None

        self.definition = definition
        self.callback = None
        self.widget = None
        self.valid = True
        self.needs_root = False
        self.value = None

        self.map = definition['map'] if 'map' in definition else None
        self.data = definition['data'] if 'data' in definition else None

        if self.data:
            self.create_map_from_data()

        if self.backend == 'gsettings':
            self.gtype = definition['gtype'] if 'gtype' in definition else definition['type']

            if not isinstance(self.definition['key'], list):
                self.definition['key'] = [self.definition['key']]
            for key in self.definition['key']:
                part = key.split('.')
                self.base_key = '.'.join(part[0:-1])
                self.key = part[-1]

                source = Gio.SettingsSchemaSource.get_default()
                if source.lookup(self.base_key, True) is None:
                    continue
                self._settings = Gio.Settings.new(self.base_key)

                if self.key not in self._settings.keys():
                    continue
                break
            else:
                print(f"None of the keys for {self.name} exist")
                for key in self.definition['key']:
                    print(f" - {key}")
                self.valid = False
                return

            self._settings.connect(f'changed::{self.key}', self._callback)

        elif self.backend == 'gtk3settings':
            self.key = definition['key']
            self.file = os.path.join(os.getenv('XDG_CONFIG_HOME', '~/.config'), 'gtk-3.0/settings.ini')
            self.file = os.path.expanduser(self.file)
            self.default = definition['default'] if 'default' in definition else None
        elif self.backend == 'environment':
            self.key = definition['key']
        elif self.backend == 'sysfs':
            if not os.path.isfile(definition['key']):
                self.valid = False
                return

            self.needs_root = True
            self.key = definition['key']
            self.stype = definition['stype']
            self.multiplier = definition['multiplier'] if 'multiplier' in definition else 1

    def connect(self, callback):
        self.callback = callback

    def _callback(self, *args):
        if self.callback is not None:
            self.callback(self, self.get_value())

    def get_value(self):
        if self.backend == 'gsettings':
            if self.gtype == 'boolean':
                value = self._settings.get_boolean(self.key)
            elif self.gtype == 'string':
                print(self.key)
                value = self._settings.get_string(self.key)
            elif self.gtype == 'number':
                value = self._settings.get_int(self.key)
            elif self.gtype == 'double':
                value = self._settings.get_double(self.key)
        elif self.backend == 'gtk3settings':
            if os.path.isfile(self.file):
                ini = configparser.ConfigParser()
                ini.read(self.file)
                value = ini.get('Settings', self.key)
            else:
                value = self.default
        elif self.backend == 'environment':
            value = os.getenv(self.key, default='')
        elif self.backend == 'sysfs':
            with open(self.key, 'r') as handle:
                raw = handle.read()
            if self.stype == 'int':
                value = int(raw) / self.multiplier
            self.value = value

        if self.map:
            for key in self.map:
                if self.map[key] == value:
                    value = key
        return value

    def set_value(self, value):
        if self.map:
            value = self.map[value]

        if self.backend == 'gsettings':
            if self.gtype == 'boolean':
                self._settings.set_boolean(self.key, value)
            elif self.gtype == 'string':
                self._settings.set_string(self.key, value)
            elif self.gtype == 'number':
                self._settings.set_int(self.key, value)
            elif self.gtype == 'double':
                self._settings.set_double(self.key, value)

        elif self.backend == 'gtk3settings':
            ini = configparser.SafeConfigParser()
            if os.path.isfile(self.file):
                ini.read(self.file)
            ini.set('Settings', self.key, value)
            os.makedirs(os.path.dirname(self.file), exist_ok=True)
            with open(self.file, 'w') as handle:
                ini.write(handle)

        elif self.backend == 'environment':
            file = os.path.expanduser('~/.pam_environment')
            lines = []
            if os.path.isfile(file):
                with open(file) as handle:
                    lines = list(handle.readlines())

            for i, line in enumerate(lines):
                if line.startswith(f'export {self.key}='):
                    lines[i] = f'export {self.key}={value}\n'
                    break
            else:
                lines.append(f'export {self.key}={value}\n')

            with open(file, 'w') as handle:
                handle.writelines(lines)

        elif self.backend == 'sysfs':
            if self.stype == 'int':
                self.value = value

    def create_map_from_data(self):
        if self.data == 'gtk3themes':
            result = []
            gtk_ver = Gtk.MINOR_VERSION
            if gtk_ver % 2:
                gtk_ver += 1
            gtk_ver = f'3.{gtk_ver}'

            for dir in glob.glob('/usr/share/themes/*'):
                if os.path.isfile(os.path.join(dir, 'gtk-3.0/gtk.css')):
                    result.append(os.path.basename(dir))
                elif os.path.isdir(os.path.join(dir, f'gtk-{gtk_ver}')):
                    result.append(os.path.basename(dir))
            self.map = {}
            for theme in sorted(result):
                name = theme
                metafile = os.path.join('/usr/share/themes', theme, 'index.theme')
                if os.path.isfile(metafile):
                    p = configparser.ConfigParser(strict=False)
                    p.read(metafile)
                    if p.has_section('X-GNOME-Metatheme'):
                        name = p.get('X-GNOME-Metatheme', 'name', fallback=name)
                    if p.has_section('Desktop Entry'):
                        name = p.get('Desktop Entry', 'Name', fallback=name)

                self.map[name] = theme
        elif self.data == 'iconthemes':
            result = []
            for dir in glob.glob(os.path.expanduser('~/.local/share/icons/*')):
                if os.path.isfile(os.path.join(dir, 'index.theme')):
                    result.append(dir)

            for dir in glob.glob('/usr/share/icons/*'):
                if os.path.isfile(os.path.join(dir, 'index.theme')):
                    result.append(dir)

            self.map = {}
            for themedir in sorted(result):
                theme = os.path.basename(themedir)
                name = os.path.basename(themedir)
                metafile = os.path.join(themedir, 'index.theme')
                p = configparser.SafeConfigParser()
                p.read(metafile)
                if p.has_section('Icon Theme'):
                    name = p.get('Icon Theme', 'Name', fallback=name)

                self.map[name] = theme
        elif self.data == 'qt5platformthemes':
            result = QtWidgets.QStyleFactory.keys()
            self.map = {}
            for theme in result:
                self.map[theme] = theme

    def __getitem__(self, item):
        return getattr(self, item)


class SettingsTree:
    def __init__(self):
        self.settings = OrderedDict()

    def _sort_weight(self, unsorted):
        test = sorted(unsorted.items(), key=lambda t: t[1]['weight'])
        return OrderedDict({k: v for k, v in test})

    def load_dir(self, path):
        print(f"Scanning {path}")
        for file in glob.glob(os.path.join(path, '*.yml')):
            print(f"  Loading {file}")
            with open(file) as handle:
                raw = handle.read()

            data = yaml.load(raw, Loader=yaml.SafeLoader)

            for page in data:
                if page['name'] not in self.settings:
                    weight = 50
                    if 'weight' in page:
                        weight = page['weight']

                    self.settings[page['name']] = {
                        'name': page['name'],
                        'weight': weight,
                        'sections': OrderedDict()
                    }

                for section in page['sections']:
                    weight = 50
                    if 'weight' in section:
                        weight = section['weight']

                    if section['name'] not in self.settings[page['name']]['sections']:
                        self.settings[page['name']]['sections'][section['name']] = {
                            'name': section['name'],
                            'weight': weight,
                            'settings': OrderedDict()
                        }

                    for setting in section['settings']:

                        if setting['name'] not in self.settings[page['name']]['sections'][section['name']]['settings']:
                            setting_obj = Setting(setting)
                            if not setting_obj.valid:
                                continue
                            self.settings[page['name']]['sections'][section['name']]['settings'][
                                setting['name']] = setting_obj

        self.settings = self._sort_weight(self.settings)
        for page in self.settings:
            self.settings[page]['sections'] = self._sort_weight(self.settings[page]['sections'])
            for section in self.settings[page]['sections']:
                self.settings[page]['sections'][section]['settings'] = self._sort_weight(
                    self.settings[page]['sections'][section]['settings'])

    def save_tweakd_config(self, fp):
        needs_saving = []
        for page in self.settings:
            for section in self.settings[page]['sections']:
                for setting in self.settings[page]['sections'][section]['settings']:
                    s = self.settings[page]['sections'][section]['settings'][setting]
                    if s.needs_root:
                        needs_saving.append(s)

        result = configparser.ConfigParser()
        for setting in needs_saving:
            if setting.backend == 'sysfs':
                if not result.has_section('sysfs'):
                    result.add_section('sysfs')
                result.set('sysfs', setting.key, str(int(setting.value * setting.multiplier)))

        result.write(fp)
