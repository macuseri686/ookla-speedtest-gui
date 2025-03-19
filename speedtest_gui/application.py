import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib

from .window import SpeedtestWindow

class SpeedtestApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.github.speedtest_gui",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        
        self.create_action("quit", self.quit_app, ["<primary>q"])
        self.create_action("about", self.on_about_action)
        
    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = SpeedtestWindow(application=self)
        win.present()
        
    def on_about_action(self, widget, _):
        about = Adw.AboutWindow(
            transient_for=self.props.active_window,
            application_name="Speedtest GUI",
            application_icon="network-wireless",
            developer_name="Caleb Banzhaf",
            version="0.1.0",
            developers=["Caleb Banzhaf"],
            copyright="© 2025 Caleb Banzhaf",
            license_type=Gtk.License.GPL_3_0,
            website="https://github.com/yourusername/speedtest-gui",
            issue_url="https://github.com/yourusername/speedtest-gui/issues"
        )
        about.present()
        
    def quit_app(self, action, param):
        self.quit()
        
    def create_action(self, name, callback, shortcuts=None):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts) 