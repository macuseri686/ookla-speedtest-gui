#!/usr/bin/env python3

import sys
import gi
import os
from gi.repository import Gio

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

# Load resources
resource_path = os.path.join(os.path.dirname(__file__), "speedtest_gui", "resources.gresource")
resource = Gio.Resource.load(resource_path)
Gio.resources_register(resource)

from speedtest_gui.application import SpeedtestApplication

if __name__ == "__main__":
    app = SpeedtestApplication()
    exit_status = app.run(sys.argv)
    sys.exit(exit_status) 