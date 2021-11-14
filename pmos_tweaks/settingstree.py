import os
import glob
from collections import OrderedDict
import configparser

import pmos_tweaks.backend as backends
import pmos_tweaks.datasource as datasources

import yaml


# Needed for qt5 theming, disabled because qt5 theming is a mess
# from PyQt5 import QtWidgets


class Setting:
    def __init__(self, definition, daemon=False):
        self.daemon = daemon
        self.name = definition['name']
        self.weight = 50
        if 'weight' in definition:
            self.weight = definition['weight']
        self.type = definition['type']
        self.key = definition['key'] if 'key' in definition else ''
        self.backend_name = definition['backend'] if 'backend' in definition else 'gsettings'

        classname = self.backend_name.title() + "Backend"
        if not hasattr(backends, classname):
            raise ValueError(f"Unknown backend {self.backend_name}, missing class {classname}")
        class_ref = getattr(backends, classname)
        if daemon and class_ref.NOT_IN_DAEMON:
            self.valid = False
            return
        self.backend = getattr(backends, classname)(definition)

        self.help = definition['help'] if 'help' in definition else None

        self.definition = definition
        self.callback = None
        self.widget = None
        self.valid = self.backend.is_valid()
        self.needs_root = self.backend.NEED_ROOT
        self.value = None

        self.map = definition['map'] if 'map' in definition else None
        self.data = definition['data'] if 'data' in definition else None

        if self.data:
            self.create_map_from_data()

        self.backend.register_callback(self._callback)

    def connect(self, callback):
        self.callback = callback

    def _callback(self, *args):
        if self.callback is not None:
            self.callback(self, self.get_value())

    def get_value(self):
        try:
            value = self.backend.get_value()
            if self.map:
                for key in self.map:
                    if self.map[key] == value:
                        value = key
            return value
        except Exception as e:
            print(f"Exception while loading {self.name}/{self.type} backend {self.backend_name}")
            raise e

    def set_value(self, value):
        if self.map:
            value = self.map[value]

        self.backend.set_value(value)

    def create_map_from_data(self):
        classname = self.data.title() + 'Datasource'
        if not hasattr(datasources, classname):
            raise ValueError(f"Unknown data source: {self.data}, missing class pmos_tweaks.datasource.{classname}")
        class_ref = getattr(datasources, classname)

        if self.daemon and class_ref.NOT_IN_DAEMON:
            return

        instance = getattr(datasources, classname)()
        self.map = instance.get_map()

    def __getitem__(self, item):
        return getattr(self, item)


class SettingsTree:
    def __init__(self, daemon=False):
        self.daemon = daemon
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
            store = setting.backend.get_tweakd_setting()
            if store is None:
                continue
            ini_section, ini_key, ini_value = store
            if not result.has_section(ini_section):
                result.add_section(ini_section)
            result.set(ini_section, ini_key, ini_value)
        result.write(fp)
