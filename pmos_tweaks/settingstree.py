import os
import glob
import subprocess
from collections import OrderedDict
import configparser
import platform

import pmos_tweaks.cpus as cpu_data

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
        elif self.backend == 'osksdl':
            self.needs_root = True
            self.key = definition['key']
            self.default = definition['default']
        elif self.backend == 'hardwareinfo':
            self.key = definition['key']

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
                try:
                    value = int(raw.rstrip('\0')) / self.multiplier
                except ValueError:
                    value = 0
            self.value = value
        elif self.backend == 'osksdl':
            value = self.osksdl_read(self.key)
        elif self.backend == 'hardwareinfo':
            value = self.hardware_info(self.key)

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
            ini = configparser.ConfigParser()
            if os.path.isfile(self.file):
                ini.read(self.file)
            if 'Settings' not in ini:
                ini['Settings'] = {}
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

        elif self.backend == 'osksdl':
            if isinstance(value, float):
                value = int(value)
            self.value = value

    def create_map_from_data(self):
        if self.data == 'gtk3themes':
            gtk_ver = Gtk.MINOR_VERSION
            if gtk_ver % 2:
                gtk_ver += 1
            gtk_ver = f'3.{gtk_ver}'

            result = []
            theme_dirs = glob.glob('/usr/share/themes/*') + \
                         glob.glob(os.path.expanduser('~/.local/share/themes/*'))
            for dir in theme_dirs:
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
            theme_dirs = glob.glob('/usr/share/icons/*') + \
                         glob.glob(os.path.expanduser('~/.local/share/icons/*'))
            for dir in theme_dirs:
                if os.path.isfile(os.path.join(dir, 'index.theme')):
                    result.append(dir)
            self.map = {}
            for themedir in sorted(result):
                theme = os.path.basename(themedir)
                name = os.path.basename(themedir)
                metafile = os.path.join(themedir, 'index.theme')
                p = configparser.ConfigParser(strict=False)
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

    def osksdl_read(self, key):
        if not os.path.isfile('/boot/osk.conf'):
            return self.default

        with open('/boot/osk.conf') as handle:
            for line in handle.readlines():
                if line.startswith(f"{self.key} = "):
                    return line.split(' = ')[1].strip()
        return self.default

    def get_file_contents(self, path):
        if not os.path.isfile(path):
            return None
        try:
            with open(path, 'r') as handle:
                return handle.read().strip()
        except:
            return None

    def hardware_info(self, key):
        GB = 1024 * 1024 * 1024

        if key == 'model':
            dmidir = '/sys/devices/virtual/dmi/id'
            if os.path.isdir(dmidir):
                manufacturer = self.get_file_contents(os.path.join(dmidir, 'chassis_vendor')) or ''
                model = self.get_file_contents(os.path.join(dmidir, 'product_name')) or ''
                return '{} {}'.format(manufacturer, model).strip()
            if os.path.isdir('/proc/device-tree'):
                return self.get_file_contents('/proc/device-tree/model')
        elif key == 'memory':
            memdir = '/sys/devices/system/memory'
            if os.path.isdir(memdir):
                blocks = 0
                for block in glob.glob(os.path.join(memdir, 'memory*/online')):
                    blocks += 1
                blocksize = self.get_file_contents(os.path.join(memdir, 'block_size_bytes'))
                blocksize_byes = int(blocksize, 16)
                memory_bytes = blocks * blocksize_byes
            else:
                meminfo = dict((i.split()[0].rstrip(':'), int(i.split()[1])) for i in open('/proc/meminfo').readlines())
                mem_kib = meminfo['MemTotal']
                memory_bytes = mem_kib * 1024
            if memory_bytes > GB:
                return "{:.1f} GB".format(memory_bytes / GB)
            else:
                return "{:.0f} MB".format(memory_bytes / GB * 1024)

        elif key == 'cpu':
            return self.hardware_info_cpus()
        elif key == 'chipset':
            return self.hardware_info_chipset()
        elif key == 'disk':
            stats = os.statvfs('/')
            total_bytes = stats.f_frsize * stats.f_blocks
            disk_size = total_bytes / GB
            return str(round(disk_size, 2)) + " GB"
        elif key == 'gpu':
            paths = ['/usr/libexec/gnome-control-center-print-renderer',
                     '/usr/lib/gnome-control-center-print-renderer']
            for path in paths:
                if not os.path.isfile(path):
                    continue
                try:
                    result = subprocess.check_output([path]).decode().strip()
                    return result
                except Exception as e:
                    print(e)
        elif key == 'kernel':
            return platform.release()
        elif key == 'architecture':
            lut = {
                'aarch64': 'ARM64'
            }
            arch = platform.machine()
            if arch in lut:
                return lut[arch]
            else:
                return arch
        elif key == 'distro':
            if os.path.isfile('/etc/os-release'):
                with open('/etc/os-release') as handle:
                    raw = handle.read()
                for line in raw.splitlines():
                    if line.startswith("PRETTY_NAME="):
                        return line.split('=', maxsplit=1)[1].replace('"', '').strip()
        return 'N/A'

    def hardware_info_cpus(self):
        cpus = {}
        raw = self.get_file_contents('/proc/cpuinfo')
        buffer = {}
        arm_names = [
            'CPU implementer',
            'CPU architecture',
            'CPU variant',
            'CPU part',
            'CPU revision',
        ]
        for line in list(raw.splitlines()) + [""]:
            if line.strip() == '':
                if 'CPU implementer' in buffer:
                    implementer = int(buffer['CPU implementer'], 16)
                    part = int(buffer['CPU part'], 16)
                    if implementer in cpu_data.arm_implementer:
                        model = cpu_data.arm_implementer[implementer]
                        if part in cpu_data.arm_part[implementer]:
                            model += ' ' + cpu_data.arm_part[implementer][part]
                        else:
                            model += ' unknown core'
                    else:
                        model = 'unknown cpu'
                    if model in cpus:
                        cpus[model] += 1
                    else:
                        cpus[model] = 1
                buffer = {}
            if line.startswith('model name'):
                _, val = line.split(':')
                name = val.strip()
                if name in cpus:
                    cpus[name] += 1
                else:
                    cpus[name] = 1
            for field in arm_names:
                if line.startswith(field):
                    key, val = line.split(':')
                    buffer[key.strip()] = val.strip()

        result = ''
        for cpu in cpus:
            result += f'{cpus[cpu]}x {cpu}\n'
        return result.strip()

    def hardware_info_chipset(self):
        # Qualcomm / socinfocoo
        if os.path.isdir('/sys/devices/soc0'):
            machine = self.get_file_contents('/sys/devices/soc0/machine')
            family = self.get_file_contents('/sys/devices/soc0/family')
            if machine is not None:
                if family is None:
                    return machine
                else:
                    return f"{family} {machine}"

        # Allwinner
        return "N/A"


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
            if setting.backend == 'osksdl':
                if not result.has_section('osksdl'):
                    result.add_section('osksdl')
                if setting.value is not None:
                    result.set('osksdl', setting.key, str(setting.value))

        result.write(fp)
