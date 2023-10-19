import configparser
import glob
import os


class Datasource:
    NOT_IN_DAEMON = False

    def get_map(self):
        return {}


class Gtk3ThemesDatasource(Datasource):
    NOT_IN_DAEMON = True

    def get_map(self):
        import gi

        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk
        gtk_ver = Gtk.MINOR_VERSION
        if gtk_ver % 2:
            gtk_ver += 1
        gtk_ver = f'3.{gtk_ver}'

        result = []
        theme_dirs = glob.glob('/usr/share/themes/*') + \
                     glob.glob(os.path.expanduser('~/.local/share/themes/*')) + \
                     glob.glob(os.path.expanduser('~/.themes/*'))
        for dir in theme_dirs:
            if os.path.isfile(os.path.join(dir, 'gtk-3.0/gtk.css')):
                result.append(os.path.basename(dir))
            elif os.path.isdir(os.path.join(dir, f'gtk-{gtk_ver}')):
                result.append(os.path.basename(dir))
        result_map = {'Adwaita': 'Adwaita', 'High Contrast': 'HighContrast'}
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

            result_map[name] = theme
        return result_map


class IconthemesDatasource(Datasource):
    def get_map(self):
        result = []
        theme_dirs = glob.glob('/usr/share/icons/*') + \
                     glob.glob(os.path.expanduser('~/.local/share/icons/*')) + \
                     glob.glob(os.path.expanduser('~/.icons/*'))
        for dir in theme_dirs:
            if os.path.isfile(os.path.join(dir, 'index.theme')):
                result.append(dir)
        result_map = {}
        for themedir in sorted(result):
            theme = os.path.basename(themedir)
            name = os.path.basename(themedir)
            metafile = os.path.join(themedir, 'index.theme')
            p = configparser.ConfigParser(strict=False)
            p.read(metafile)
            if p.has_section('Icon Theme'):
                name = p.get('Icon Theme', 'Name', fallback=name)

            result_map[name] = theme
        return result_map


class SoundthemesDatasource(Datasource):
    def get_map(self):
        # TODO: Reduce code duplication
        result = []
        theme_dirs = glob.glob('/usr/share/sounds/*') + \
                     glob.glob(os.path.expanduser('~/.local/share/sounds/*'))
        for dir in theme_dirs:
            if os.path.isfile(os.path.join(dir, 'index.theme')):
                result.append(dir)
        result_map = {
            'Custom': '__custom'
        }
        for themedir in sorted(result):
            theme = os.path.basename(themedir)
            name = os.path.basename(themedir)
            metafile = os.path.join(themedir, 'index.theme')
            p = configparser.ConfigParser(strict=False)
            p.read(metafile)
            if p.has_section('Sound Theme'):
                name = p.get('Sound Theme', 'Name', fallback=name)
            result_map[name] = theme
        return result_map
