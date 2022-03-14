import configparser
import glob
import os
import platform
import subprocess

import pmos_tweaks.cpus as cpu_data
import pmos_tweaks.socs as soc_data


class Backend:
    NEED_ROOT = False
    NEED_REBOOT = False
    NOT_IN_DAEMON = False

    def __init__(self, definition):
        self.definition = definition
        self.name = definition['name']
        self.key = definition['key']
        self.type = definition['type']
        self.value = None

    def is_valid(self):
        return True

    def needs_root(self):
        return self.definition['needs-root'] if 'needs-root' in self.definition else self.NEED_ROOT

    def get_value(self):
        raise NotImplemented()

    def set_value(self, value):
        raise NotImplemented()

    def register_callback(self, callback):
        return

    def get_file_contents(self, path):
        if not os.path.isfile(path):
            return None
        try:
            with open(path, 'r') as handle:
                return handle.read().strip()
        except:
            return None

    def get_tweakd_setting(self):
        return None


class GsettingsBackend(Backend):
    NOT_IN_DAEMON = True

    def __init__(self, definition):
        super().__init__(definition)
        self.gtype = definition['gtype'] if 'gtype' in definition else definition['type']
        self.valid = True
        if not isinstance(self.definition['key'], list):
            self.definition['key'] = [self.definition['key']]
        for key in self.definition['key']:
            part = key.split('.')
            self.base_key = '.'.join(part[0:-1])
            self.key = part[-1]

            import gi
            gi.require_version('Gtk', '3.0')
            from gi.repository import Gio

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

    def register_callback(self, callback):
        if self.valid:
            self._settings.connect(f'changed::{self.key}', callback)

    def get_value(self):
        if self.gtype == 'boolean':
            value = self._settings.get_boolean(self.key)
        elif self.gtype == 'string':
            value = self._settings.get_string(self.key)
        elif self.gtype == 'number':
            value = self._settings.get_int(self.key)
        elif self.gtype == 'double':
            value = self._settings.get_double(self.key)
        elif self.gtype == 'flags':
            value = self._settings.get_flags(self.key)
        else:
            raise ValueError("Unknown type for gsettings backend")
        print(self.key, value)
        return value

    def set_value(self, value):
        if self.gtype == 'boolean':
            self._settings.set_boolean(self.key, value)
        elif self.gtype == 'string':
            self._settings.set_string(self.key, value)
        elif self.gtype == 'number':
            self._settings.set_int(self.key, value)
        elif self.gtype == 'double':
            self._settings.set_double(self.key, value)
        elif self.gtype == 'flags':
            self._settings.set_flags(self.key, value)

    def is_valid(self):
        return self.valid


class Gtk3SettingsBackend(Backend):
    def __init__(self, definition):
        super().__init__(definition)

        self.file = os.path.join(os.getenv('XDG_CONFIG_HOME', '~/.config'), 'gtk-3.0/settings.ini')
        self.file = os.path.expanduser(self.file)
        self.default = definition['default'] if 'default' in definition else None

    def get_value(self):
        if os.path.isfile(self.file):
            ini = configparser.ConfigParser()
            ini.read(self.file)
            return ini.get('Settings', self.key)
        else:
            return self.default

    def set_value(self, value):
        ini = configparser.ConfigParser()
        if os.path.isfile(self.file):
            ini.read(self.file)
        if 'Settings' not in ini:
            ini['Settings'] = {}
        ini.set('Settings', self.key, value)
        os.makedirs(os.path.dirname(self.file), exist_ok=True)
        with open(self.file, 'w') as handle:
            ini.write(handle)


class EnvironmentBackend(Backend):
    def get_value(self):
        return os.getenv(self.key, default='')

    def set_value(self, value):
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


class SysfsBackend(Backend):
    NEED_ROOT = True

    def __init__(self, definition):
        super().__init__(definition)

        self.stype = definition['stype']
        self.multiplier = definition['multiplier'] if 'multiplier' in definition else 1
        self.readonly = definition['readonly'] if 'readonly' in definition else False

    def is_valid(self):
        return os.path.isfile(self.definition['key'])

    def get_value(self):
        with open(self.key, 'r') as handle:
            raw = handle.read()
        if self.stype == 'int':
            try:
                self.value = int(raw.rstrip('\0')) / self.multiplier
            except ValueError:
                self.value = 0
        elif self.stype == 'string':
            self.value = raw.rstrip('\0').strip()
        else:
            print(f"Unknown sysfs stype: {self.stype}")
        return self.value

    def set_value(self, value):
        """ Value is not set here, it's done by the background service """
        if self.stype == 'int':
            self.value = value

    def get_tweakd_setting(self):
        if self.value is None:
            return None
        if self.readonly:
            return None
        return 'sysfs', self.key, str(int(self.value * self.multiplier))


class OsksdlBackend(Backend):
    NEED_ROOT = True

    def __init__(self, definition):
        super().__init__(definition)
        self.default = definition['default']

    def get_value(self):
        if not os.path.isfile('/boot/osk.conf'):
            self.value = self.default
            return self.default

        with open('/boot/osk.conf') as handle:
            for line in handle.readlines():
                if line.startswith(f"{self.key} = "):
                    value = line.split(' = ')[1].strip()
                    if self.type == 'boolean':
                        value = value == 'true'
                    self.value = value
                    return value
        self.value = self.default
        return self.default

    def set_value(self, value):
        """ Value is not set here, it's done by the background service """
        if isinstance(value, float):
            value = int(value)
        self.value = value

    def get_tweakd_setting(self):
        if self.value is None:
            return None
        return 'osksdl', self.key, str(self.value)


class HardwareinfoBackend(Backend):
    def get_value(self):
        key = self.key
        GB = 1024 * 1024 * 1024

        if key == 'model':
            if os.path.isdir('/proc/device-tree'):
                return self.get_file_contents('/proc/device-tree/model')
            dmidir = '/sys/devices/virtual/dmi/id'
            if os.path.isdir(dmidir):
                manufacturer = self.get_file_contents(os.path.join(dmidir, 'chassis_vendor')) or ''
                model = self.get_file_contents(os.path.join(dmidir, 'product_name')) or ''
                return '{} {}'.format(manufacturer, model).strip()
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
            if line.startswith('model name') and 'ARMv' not in line:
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
        # Qualcomm / socinfo
        if os.path.isdir('/sys/devices/soc0'):
            machine = self.get_file_contents('/sys/devices/soc0/machine')
            family = self.get_file_contents('/sys/devices/soc0/family')
            soc_id = self.get_file_contents('/sys/devices/soc0/soc_id')
            if soc_id is not None and 'EXYNOS' in soc_id:
                return f"Exynos {soc_id[6:]}"
            elif machine is not None:
                if family is None:
                    return machine
                else:
                    return f"{family} {machine}"

        # Guess based on the device tree
        if os.path.isdir('/proc/device-tree'):
            compatible = self.get_file_contents('/proc/device-tree/compatible')
            part = compatible.rstrip('\0').split('\0')
            manufacturer, part = part[-1].split(',', maxsplit=1)
            return soc_data.get_soc_name(manufacturer, part)
        return "N/A"


class CssBackend(Backend):
    NEED_REBOOT = True

    def __init__(self, definition):
        super().__init__(definition)
        self.selector = definition['selector']
        self.rules = definition['css']
        guard = definition['guard']
        self.guard_start = f'/* TWEAKS-START {guard} */'
        self.guard_end = f'/* TWEAKS-END {guard} */'
        for rule in self.rules:
            if self.rules[rule].startswith('%'):
                self.primary = rule

    def get_value(self):
        filename = os.path.expanduser(self.key)
        if os.path.isfile(filename):
            with open(filename) as handle:
                raw = handle.read()
            if self.guard_start not in raw:
                return None
            else:
                in_block = False
                for line in raw.splitlines():
                    if in_block:
                        if line.strip().startswith(self.primary):
                            key, val = line.strip().split(':', maxsplit=1)
                            value = val.strip()[:-1]
                            if self.definition['css'][key] == '%px':
                                return float(value[:-2])
                            elif value.startswith('url("'):
                                return value[12:-2]
                            else:
                                return value
                    if line.startswith(self.guard_start):
                        in_block = True
                    elif line.startswith(self.guard_end):
                        in_block = False
        else:
            return None

    def set_value(self, value):
        clear = False
        if value is None:
            clear = True
        if value is not None and isinstance(value, str) and value.startswith('/'):
            value = f'url("file://{value}")'
        filename = os.path.expanduser(self.key)
        raw = []
        if os.path.isfile(filename):
            with open(filename) as handle:
                raw = list(handle.readlines())

        result = []
        found = False
        ignore = False
        for line in raw:
            if line.strip() == self.guard_end:
                ignore = False
                if clear:
                    continue

            if clear and line.strip() == self.guard_start:
                ignore = True
                continue

            if not ignore:
                result.append(line)

            if line.strip() == self.guard_start:
                found = True
                ignore = True

                result.append(self.selector + ' {\n')
                for rule in self.rules:
                    val = self.rules[rule]
                    if val == '%':
                        val = value
                    elif val == '%px':
                        val = f'{value}px'
                    result.append('\t' + rule + ': ' + val + ';\n')
                result.append('}\n')

        if not found and not clear:
            if len(result) > 0 and not result[-1].endswith('\n'):
                result.append('\n')
            result.append(self.guard_start + '\n')
            result.append(self.selector + ' {\n')
            for rule in self.rules:
                val = self.rules[rule]
                if val == '%':
                    val = value
                elif val == '%px':
                    val = f'{value}px'
                result.append('\t' + rule + ': ' + val + ';\n')
            result.append('}\n')
            result.append(self.guard_end + '\n')

        with open(filename, 'w') as handle:
            handle.writelines(result)


class SymlinkBackend(Backend):
    def __init__(self, definition):
        super().__init__(definition)
        self.format = None
        self.source_ext = definition['source_ext'] if 'source_ext' in definition else False

    def get_value(self):
        if self.format:
            link = self.key + '.' + self.format
            if os.path.islink(link):
                return os.readlink(link)
            else:
                return None
        else:
            if self.source_ext:
                for link in glob.iglob(self.key + '.*'):
                    if os.path.islink(link):
                        self.format = link.split('.')[-1]
                        return os.readlink(link)
            else:
                return os.readlink(self.key)

    def set_value(self, value):
        if value is None:
            if self.source_ext:
                link = self.key + '.' + self.format
            else:
                link = self.key
            if os.path.islink(link):
                os.unlink(link)
            self.format = None
        else:
            target = os.path.expanduser(value)
            if self.source_ext:
                self.format = target.split('.')[-1]
                link = self.key + '.' + self.format
            else:
                link = self.key
            os.symlink(target, link)


class SoundthemeBackend(SymlinkBackend):
    def __init__(self, definition):
        super().__init__(definition)
        self.source_ext = True
        self.backend = 'symlink'
        themedir = os.path.dirname(os.path.expanduser(self.key))
        themefile = os.path.join(themedir, 'index.theme')
        if os.path.exists(themedir):
            if not os.path.isfile(themefile):
                self.valid = False
            return
        else:
            os.makedirs(themedir)
            lines = []
            lines.append('[Sound Theme]\n')
            lines.append('Name=Custom Profile\n')
            lines.append('Inherits=freedesktop\n')
            lines.append('Directories=.\n')
            with open(themefile, 'w') as handle:
                handle.writelines(lines)


class FileBackend(Backend):
    def __init__(self, definition):
        super().__init__(definition)

        self.default = definition['default'] if 'default' in definition else None
        self.root = definition['needs-root'] if 'needs-root' in definition else False
        self.newline = definition['trailing-newline'] if 'trailing-newline' in definition else True

    def is_valid(self):
        if self.definition is None:
            return os.path.isfile(self.key)
        else:
            return True

    def get_value(self):
        self.value = None
        if os.path.isfile(self.key):
            with open(os.path.expanduser(self.key), 'r') as handle:
                val = handle.read()
                if self.newline:
                    self.value = val.rstrip('\n')
                else:
                    self.value = val
        return self.value

    def set_value(self, value):
        """ Value is not set here if the setting is in a root-only location, the tweakd part will handle it """
        self.value = value

        if not self.root:
            with open(os.path.expanduser(self.key), 'w') as handle:
                val = self.value
                if self.newline:
                    val += '\n'
                handle.write(val)

    def get_tweakd_setting(self):
        if not self.root:
            return None

        if self.value is None:
            return None
        return 'file', self.key, str(self.value)
