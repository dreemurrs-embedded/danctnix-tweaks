import gi

from danctnix_tweaks.window import TweaksWindow

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib

gi.require_version('Handy', '1')
from gi.repository import Handy


Handy.init()


class TweaksApplication(Gtk.Application):
    def __init__(self, application_id, flags, datadir):
        self.datadir = datadir
        self.window = None
        Gtk.Application.__init__(self, application_id=application_id, flags=flags)
        GLib.set_prgname(application_id)

    def do_activate(self, *args):
        if not self.window:
            self.window = TweaksWindow(self, self.datadir)
        self.window.present()

    def do_startup(self):
        Gtk.Application.do_startup(self)

        Handy.StyleManager.get_default().set_color_scheme(
            Handy.ColorScheme.PREFER_LIGHT)


def main(version, datadir=None):
    app = TweaksApplication("org.danctnix.Tweaks", Gio.ApplicationFlags.FLAGS_NONE, datadir)
    app.run()


if __name__ == '__main__':
    main('')
