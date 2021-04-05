import os
import glob
from collections import OrderedDict
import configparser

import yaml

from gi.repository import Gio


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

        self.map = definition['map'] if 'map' in definition else None

        if self.backend == 'gsettings':
            key = self.definition['key']
            part = key.split('.')
            self.base_key = '.'.join(part[0:-1])
            self.key = part[-1]
            self._settings = Gio.Settings.new(self.base_key)
            self._settings.connect(f'changed::{self.key}', self._callback)

            self.gtype = definition['gtype'] if 'gtype' in definition else definition['type']
        elif self.backend == 'gtk3settings':
            self.key = definition['key']
            self.file = os.path.join(os.getenv('XDG_CONFIG_HOME', '~/.config'), 'gtk-3.0/settings.ini')
            self.file = os.path.expanduser(self.file)
            self.default = definition['default'] if 'default' in definition else None

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
        elif self.backend == 'gtk3settings':
            if os.path.isfile(self.file):
                ini = configparser.SafeConfigParser()
                ini.read(self.file)
                value = ini.get('Settings', self.key)
            else:
                value = self.default

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
        elif self.backend == 'gtk3settings':
            ini = configparser.SafeConfigParser()
            if os.path.isfile(self.file):
                ini.read(self.file)
            ini.set('Settings', self.key, value)
            os.makedirs(os.path.dirname(self.file), exist_ok=True)
            with open(self.file, 'w') as handle:
                ini.write(handle)

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
                            self.settings[page['name']]['sections'][section['name']]['settings'][
                                setting['name']] = Setting(setting)

        self.settings = self._sort_weight(self.settings)
        for page in self.settings:
            self.settings[page]['sections'] = self._sort_weight(self.settings[page]['sections'])
            for section in self.settings[page]['sections']:
                self.settings[page]['sections'][section]['settings'] = self._sort_weight(
                    self.settings[page]['sections'][section]['settings'])
