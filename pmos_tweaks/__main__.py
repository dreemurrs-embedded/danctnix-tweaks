import argparse
import os
import gi

from pmos_tweaks.window import TweaksWindow

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio

gi.require_version('Handy', '1')
from gi.repository import Handy


class TweaksApplication(Gtk.Application):
    def __init__(self, application_id, flags, args):
        Gtk.Application.__init__(self, application_id=application_id, flags=flags)
        self.connect("activate", self.new_window)
        self.args = args

    def new_window(self, *args):
        TweaksWindow(self, self.args)


def main(version):
    Handy.init()

    parser = argparse.ArgumentParser(description="postmarketOS Tweaks tool")
    parser.add_argument('config', help='TOTP url to register', default='/etc/pmos-tweaks/tweaks.conf')
    args = parser.parse_args()

    app = TweaksApplication("org.postmarketos.Tweaks", Gio.ApplicationFlags.FLAGS_NONE, args=args)
    app.run()


if __name__ == '__main__':
    main('')
