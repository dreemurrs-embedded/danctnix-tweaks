import argparse
import os
import gi

from danctnix_tweaks.window import TweaksWindow

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib

gi.require_version('Handy', '1')
from gi.repository import Handy


class TweaksApplication(Gtk.Application):
    def __init__(self, application_id, flags, datadir):
        self.datadir = datadir
        Gtk.Application.__init__(self, application_id=application_id, flags=flags)
        GLib.set_prgname(application_id)
        self.connect("activate", self.new_window)

    def new_window(self, *args):
        TweaksWindow(self, self.datadir)


def main(version, datadir=None):
    Handy.init()
    app = TweaksApplication("org.danctnix.Tweaks", Gio.ApplicationFlags.FLAGS_NONE, datadir)
    app.run()


if __name__ == '__main__':
    main('')
