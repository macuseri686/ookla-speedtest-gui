import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, GdkPixbuf, Gio

import math
import os
import re
import tempfile
from .speedtest_runner import SpeedtestRunner

# Get the directory of the current file
current_dir = os.path.dirname(os.path.abspath(__file__))
ui_path = os.path.join(current_dir, "ui", "window.ui")

@Gtk.Template.from_file(ui_path)
class SpeedtestWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'SpeedtestWindow'
    
    # Template widgets
    start_button = Gtk.Template.Child()
    cancel_button = Gtk.Template.Child()
    progress_bar = Gtk.Template.Child()
    status_label = Gtk.Template.Child()
    gauge_picture = Gtk.Template.Child()
    speed_value_label = Gtk.Template.Child()
    gauge_phase_label = Gtk.Template.Child()
    gauge_container = Gtk.Template.Child()
    
    download_speed = Gtk.Template.Child()
    upload_speed = Gtk.Template.Child()
    ping_latency = Gtk.Template.Child()
    jitter = Gtk.Template.Child()
    packet_loss = Gtk.Template.Child()
    isp_label = Gtk.Template.Child()
    server_label = Gtk.Template.Child()
    result_url = Gtk.Template.Child()
    
    results_group = Gtk.Template.Child()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.speedtest_runner = SpeedtestRunner()
        self.speedtest_runner.connect("progress", self.on_progress)
        self.speedtest_runner.connect("completed", self.on_completed)
        self.speedtest_runner.connect("error", self.on_error)
        
        self.start_button.connect("clicked", self.on_start_clicked)
        self.cancel_button.connect("clicked", self.on_cancel_clicked)
        
        # Initialize gauge properties
        self.current_speed = 0
        self.max_speed = 100  # Default max speed in Mbps
        self.test_phase = "idle"  # idle, download, upload
        
        # Initially hide the cancel button, gauge, and results
        self.cancel_button.set_visible(False)
        self.results_group.set_visible(False)
        
        # Hide the gauge and related elements initially
        self.gauge_picture.set_visible(False)
        self.speed_value_label.set_visible(False)
        self.gauge_phase_label.set_visible(False)
        
        # Add "Powered by Ookla Speedtest" label
        self.add_powered_by_label()
        
        # Find the initial UI box more precisely based on the UI structure
        self.initial_ui_box = self.find_initial_ui_box()
        
        # Center the initial UI box vertically
        if self.initial_ui_box:
            parent = self.initial_ui_box.get_parent()
            if parent and isinstance(parent, Gtk.Box):
                # Add expand property to center vertically
                self.initial_ui_box.set_vexpand(True)
                self.initial_ui_box.set_valign(Gtk.Align.CENTER)
        
        # Find the Mbps label directly in the UI
        self.mbps_label = self.find_mbps_label()
        
        # Ensure the Mbps label is hidden initially
        if self.mbps_label:
            self.mbps_label.set_visible(False)
        else:
            print("Warning: Mbps label not found!")
            
            # Try to find it in the gauge container
            if hasattr(self, 'gauge_container'):
                def find_in_container(widget):
                    if isinstance(widget, Gtk.Label) and widget.get_text() == "Mbps":
                        return widget
                    
                    if hasattr(widget, 'get_first_child'):
                        child = widget.get_first_child()
                        while child:
                            result = find_in_container(child)
                            if result:
                                return result
                            child = child.get_next_sibling()
                    elif isinstance(widget, Gtk.Box) or isinstance(widget, Gtk.Grid):
                        for child in widget:
                            result = find_in_container(child)
                            if result:
                                return result
                    
                    return None
                
                self.mbps_label = find_in_container(self.gauge_container)
                if self.mbps_label:
                    print(f"Mbps label found in gauge container: {self.mbps_label}")
                    self.mbps_label.set_visible(False)
        
        # Hide the progress bar if it exists
        if hasattr(self, 'progress_bar'):
            self.progress_bar.set_visible(False)
        
    def create_gauge_svg(self, value, max_value, phase):
        # Fixed max value for the gauge
        fixed_max = 500  # Always show 0-500 Mbps range
        
        # Calculate the angle based on the value (0-270 degrees, leaving a 90-degree opening at the bottom)
        percentage = min(value / fixed_max, 1.0)
        max_angle = 270  # Leave a 90-degree opening at the bottom
        start_angle = 270 - (max_angle / 2)  # Start from the left side
        end_angle = start_angle + (max_angle * percentage)  # Fill clockwise
        
        # Define colors based on phase
        if phase == "download":
            gradient_start = "#0066cc"
            gradient_stop = "#00ccff"
        elif phase == "upload":
            gradient_start = "#ff6600"
            gradient_stop = "#ffcc00"
        else:
            gradient_start = "#888888"
            gradient_stop = "#cccccc"
        
        # SVG parameters
        cx, cy = 150, 150  # Center of the circle
        r_outer = 100      # Outer radius
        stroke_width = 20  # Width of the gauge track
        
        # Create tick marks at multiples of 50
        ticks = ""
        tick_values = [0, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500]
        tick_inner_length = 5   # Reduced inner length (how far ticks extend inside)
        tick_outer_length = 15  # Length of ticks extending outside
        tick_width = 2
        
        # Add tick marks and labels
        for value in tick_values:
            tick_percentage = value / fixed_max
            tick_angle = start_angle + (max_angle * tick_percentage)
            tick_rad = math.radians(tick_angle)
            
            # Start point of tick (inside the gauge radius)
            x1 = cx + (r_outer - tick_inner_length) * math.cos(tick_rad)  # Start inside the gauge
            y1 = cy + (r_outer - tick_inner_length) * math.sin(tick_rad)
            
            # End point of tick (extending outward)
            x2 = cx + (r_outer + tick_outer_length) * math.cos(tick_rad)
            y2 = cy + (r_outer + tick_outer_length) * math.sin(tick_rad)
            
            # Add the tick line
            ticks += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#666" stroke-width="{tick_width}" />'
            
            # Calculate label position - fixed distance from end of tick mark
            label_distance = 10  # Distance from end of tick mark to label
            label_x = x2 + label_distance * math.cos(tick_rad)
            label_y = y2 + label_distance * math.sin(tick_rad)
            
            # Determine text anchor based on position around the circle
            # Special case for the middle (250) tick
            if value == 250:
                text_anchor = "middle"
                # Move the label a bit further out for better centering
                label_x = x2 + (label_distance + 5) * math.cos(tick_rad)
                label_y = y2 + (label_distance + 5) * math.sin(tick_rad)
            elif 90 <= tick_angle <= 270:  # Left half
                text_anchor = "end"
            else:  # Right half
                text_anchor = "start"
            
            # Add the label
            ticks += f'<text x="{label_x}" y="{label_y}" text-anchor="{text_anchor}" alignment-baseline="middle" font-size="12" fill="#666" font-family="sans-serif">{value}</text>'
        
        # Create SVG content - note the order: ticks first, then gauge arcs
        svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg width="300" height="300" viewBox="0 0 300 300" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="gauge-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stop-color="{gradient_start}" />
                    <stop offset="100%" stop-color="{gradient_stop}" />
                </linearGradient>
            </defs>
            
            <!-- Tick marks and labels (placed first so they appear behind the gauge) -->
            {ticks}
            
            <!-- Background track (nearly full circle with opening at bottom) -->
            <path d="M {cx + r_outer * math.cos(math.radians(start_angle))} {cy + r_outer * math.sin(math.radians(start_angle))}
                   A {r_outer} {r_outer} 0 1 1 {cx + r_outer * math.cos(math.radians(start_angle + max_angle))} {cy + r_outer * math.sin(math.radians(start_angle + max_angle))}"
                  fill="none" stroke="#e0e0e0" stroke-width="{stroke_width}" stroke-linecap="round" />
            
            <!-- Value arc (follows the same path but only to the current percentage) -->
            <path d="M {cx + r_outer * math.cos(math.radians(start_angle))} {cy + r_outer * math.sin(math.radians(start_angle))}
                   A {r_outer} {r_outer} 0 {1 if end_angle - start_angle > 180 else 0} 1 {cx + r_outer * math.cos(math.radians(end_angle))} {cy + r_outer * math.sin(math.radians(end_angle))}"
                  fill="none" stroke="url(#gauge-gradient)" stroke-width="{stroke_width}" stroke-linecap="round" />
        </svg>'''
        
        # Create a temporary file to store the SVG
        with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as temp:
            temp.write(svg.encode('utf-8'))
            temp_path = temp.name
        
        return temp_path
        
    def update_gauge(self, speed, phase):
        self.current_speed = speed
        self.test_phase = phase
        
        # Create SVG gauge (always using fixed max of 500)
        svg_path = self.create_gauge_svg(speed, 500, phase)
        
        # Load the SVG into the GtkPicture
        file = Gio.File.new_for_path(svg_path)
        self.gauge_picture.set_file(file)
        
        # Update the speed label
        self.speed_value_label.set_text(f"{speed:.1f}")
        
        # Update phase label
        if phase == "download":
            self.gauge_phase_label.set_text("DOWNLOAD")
        elif phase == "upload":
            self.gauge_phase_label.set_text("UPLOAD")
        else:
            self.gauge_phase_label.set_text("READY")
        
        # Clean up the temporary file (schedule for deletion after a delay)
        GLib.timeout_add(1000, lambda path: os.unlink(path) if os.path.exists(path) else None, svg_path)
        
    def show_test_ui(self):
        """Show the UI elements for the test and hide the initial UI"""
        # Find and hide all initial UI elements by their names or types
        for widget_name in ['logo_image', 'title_label', 'description_label', 'initial_content_box']:
            widget = self.find_widget_by_name(widget_name)
            if widget:
                widget.set_visible(False)
        
        # Show test UI elements
        self.gauge_picture.set_visible(True)
        self.speed_value_label.set_visible(True)
        self.gauge_phase_label.set_visible(True)
        
        # Show the Mbps label if we found it
        if hasattr(self, 'mbps_label') and self.mbps_label:
            self.mbps_label.set_visible(True)
    
    def show_initial_ui(self):
        """Show the initial UI elements and hide the test UI"""
        # Find and show all initial UI elements by their names or types
        for widget_name in ['logo_image', 'title_label', 'description_label', 'initial_content_box']:
            widget = self.find_widget_by_name(widget_name)
            if widget:
                widget.set_visible(True)
        
        # Hide test UI elements
        self.gauge_picture.set_visible(False)
        self.speed_value_label.set_visible(False)
        self.gauge_phase_label.set_visible(False)
        
        # Hide the Mbps label if we found it
        if hasattr(self, 'mbps_label') and self.mbps_label:
            self.mbps_label.set_visible(False)
    
    def find_widget_by_name(self, name):
        """Helper method to find widgets by name in the UI hierarchy"""
        # Try direct attribute access first
        if hasattr(self, name):
            return getattr(self, name)
        
        # If not found, search through widget tree
        def search_in_widget(widget, target_name):
            # Check if this widget has the right name
            if hasattr(widget, 'get_name') and widget.get_name() == target_name:
                return widget
            
            # If it's a container, search its children
            if isinstance(widget, Gtk.Box) or isinstance(widget, Gtk.Grid):
                for child in widget:
                    result = search_in_widget(child, target_name)
                    if result:
                        return result
            
            return None
        
        # Start the search from the content area
        content = self.get_content()
        if content:
            return search_in_widget(content, name)
        
        return None
        
    def on_start_clicked(self, button):
        self.start_button.set_visible(False)
        self.cancel_button.set_visible(True)
        self.results_group.set_visible(False)
        
        # Hide initial UI box
        if self.initial_ui_box:
            self.initial_ui_box.set_visible(False)
        else:
            # Fallback: try to find and hide individual elements
            content = self.get_content()
            if content:
                def hide_initial_elements(widget):
                    if isinstance(widget, Gtk.Image) and widget.get_icon_name() == "network-wireless-symbolic":
                        widget.set_visible(False)
                        return True
                    
                    if isinstance(widget, Gtk.Label):
                        text = widget.get_text()
                        if text == "Speedtest" or text == "Test your internet connection speed":
                            widget.set_visible(False)
                            return True
                    
                    if hasattr(widget, 'get_first_child'):
                        child = widget.get_first_child()
                        while child:
                            if hide_initial_elements(child):
                                child = child.get_next_sibling()
                            child = child.get_next_sibling()
                    elif isinstance(widget, Gtk.Box) or isinstance(widget, Gtk.Grid):
                        for child in widget:
                            hide_initial_elements(child)
                    
                    return False
                
                hide_initial_elements(content)
        
        # Show gauge elements
        self.show_gauge_elements()
        
        self.status_label.set_text("Initializing...")
        self.update_gauge(0, "idle")
        
        self.speedtest_runner.start_test()
        
    def on_cancel_clicked(self, button):
        self.speedtest_runner.cancel_test()
        self.cancel_button.set_visible(False)
        self.start_button.set_visible(True)
        self.status_label.set_text("Test cancelled")
        
        # Hide gauge elements
        self.hide_gauge_elements()
        
        # Show initial UI box
        if self.initial_ui_box:
            self.initial_ui_box.set_visible(True)
        else:
            # Fallback: try to find and show individual elements
            content = self.get_content()
            if content:
                def show_initial_elements(widget):
                    if isinstance(widget, Gtk.Image) and widget.get_icon_name() == "network-wireless-symbolic":
                        widget.set_visible(True)
                        return True
                    
                    if isinstance(widget, Gtk.Label):
                        text = widget.get_text()
                        if text == "Speedtest" or text == "Test your internet connection speed":
                            widget.set_visible(True)
                            return True
                    
                    if hasattr(widget, 'get_first_child'):
                        child = widget.get_first_child()
                        while child:
                            if show_initial_elements(child):
                                child = child.get_next_sibling()
                            child = child.get_next_sibling()
                    elif isinstance(widget, Gtk.Box) or isinstance(widget, Gtk.Grid):
                        for child in widget:
                            show_initial_elements(child)
                    
                    return False
                
                show_initial_elements(content)
        
    def on_progress(self, runner, phase, progress, status_text):
        self.status_label.set_text(status_text)
        
        # Update gauge based on phase
        if phase == "download":
            # Extract speed from status text if available
            try:
                speed_text = status_text.split("Download: ")[1].split(" Mbps")[0]
                speed = float(speed_text)
                self.update_gauge(speed, "download")
            except:
                pass
        elif phase == "upload":
            try:
                speed_text = status_text.split("Upload: ")[1].split(" Mbps")[0]
                speed = float(speed_text)
                self.update_gauge(speed, "upload")
            except:
                pass
        elif phase == "download_raw":
            self.update_gauge(progress, "download")
        elif phase == "upload_raw":
            self.update_gauge(progress, "upload")
        
    def on_completed(self, runner, results):
        self.cancel_button.set_visible(False)
        self.start_button.set_visible(True)
        self.status_label.set_text("Test completed")
        
        # Hide gauge elements
        self.hide_gauge_elements()
        
        # Show initial UI box
        if self.initial_ui_box:
            self.initial_ui_box.set_visible(True)
        
        # Update results
        self.download_speed.set_text(f"{results['download']:.2f} Mbps")
        self.upload_speed.set_text(f"{results['upload']:.2f} Mbps")
        self.ping_latency.set_text(f"{results['ping']:.2f} ms")
        self.jitter.set_text(f"{results['jitter']:.2f} ms")
        
        if results['packet_loss'] is not None:
            self.packet_loss.set_text(f"{results['packet_loss']:.1f}%")
        else:
            self.packet_loss.set_text("Not available")
            
        self.isp_label.set_text(results['isp'])
        
        # Display server name and location if available
        server_info = results['server']
        if 'server_location' in results and results['server_location']:
            server_info = f"{server_info} ({results['server_location']})"
        self.server_label.set_text(server_info)
        
        # Find and hide the entire result URL row
        self.hide_result_url_row()
        
        # Make sure the powered by label for results is visible
        if hasattr(self, 'results_powered_by_label'):
            self.results_powered_by_label.set_visible(True)
        
        self.results_group.set_visible(True)
        
    def on_error(self, runner, error_message):
        self.cancel_button.set_visible(False)
        self.start_button.set_visible(True)
        self.status_label.set_text(f"Error: {error_message}")
        
        # Hide gauge elements
        self.hide_gauge_elements()
        
        # Show initial UI box
        if self.initial_ui_box:
            self.initial_ui_box.set_visible(True)

    def hide_gauge_elements(self):
        """Hide all elements related to the gauge display"""
        self.gauge_picture.set_visible(False)
        self.speed_value_label.set_visible(False)
        self.gauge_phase_label.set_visible(False)
        
        # Hide the gauge container if available
        if hasattr(self, 'gauge_container'):
            # Either hide the whole container
            self.gauge_container.set_visible(False)
            
            # Or iterate through all children to find and hide the Mbps label
            def hide_mbps_in_container(widget):
                if isinstance(widget, Gtk.Label) and widget.get_text() == "Mbps":
                    widget.set_visible(False)
                    return True
                
                if hasattr(widget, 'get_first_child'):
                    child = widget.get_first_child()
                    while child:
                        if hide_mbps_in_container(child):
                            return True
                        child = child.get_next_sibling()
                elif isinstance(widget, Gtk.Box) or isinstance(widget, Gtk.Grid):
                    for child in widget:
                        if hide_mbps_in_container(child):
                            return True
                
                return False
            
            hide_mbps_in_container(self.gauge_container)
        
        # Also try the direct approach if we found the label
        if self.mbps_label:
            self.mbps_label.set_visible(False)

    def show_gauge_elements(self):
        """Show all elements related to the gauge display"""
        self.gauge_picture.set_visible(True)
        self.speed_value_label.set_visible(True)
        self.gauge_phase_label.set_visible(True)
        
        # Show the gauge container if available
        if hasattr(self, 'gauge_container'):
            self.gauge_container.set_visible(True)
        
        # Also show the Mbps label if we found it
        if self.mbps_label:
            self.mbps_label.set_visible(True)

    def find_initial_ui_box(self):
        """Find the box containing the initial UI elements (logo, title, description)"""
        content = self.get_content()
        if not content:
            return None
        
        # Find the initial UI box more precisely based on the UI structure
        def find_box(widget):
            # If this is a box with vertical orientation
            if isinstance(widget, Gtk.Box) and widget.get_orientation() == Gtk.Orientation.VERTICAL:
                # Check if it has the expected children (image and labels)
                has_image = False
                has_title_label = False
                has_subtitle_label = False
                
                for child in widget:
                    if isinstance(child, Gtk.Image):
                        has_image = True
                    elif isinstance(child, Gtk.Label):
                        text = child.get_text()
                        if text == "Speedtest":
                            has_title_label = True
                        elif text == "Test your internet connection speed":
                            has_subtitle_label = True
                
                # If we found all expected elements, this is our target
                if has_image and has_title_label and has_subtitle_label:
                    return widget
            
            # If not found at this level, search children
            if hasattr(widget, 'get_first_child'):
                child = widget.get_first_child()
                while child:
                    result = find_box(child)
                    if result:
                        return result
                    child = child.get_next_sibling()
            elif isinstance(widget, Gtk.Box) or isinstance(widget, Gtk.Grid):
                for child in widget:
                    result = find_box(child)
                    if result:
                        return result
            
            return None
        
        return find_box(content)

    def find_mbps_label(self):
        """Find the Mbps label in the UI"""
        content = self.get_content()
        if not content:
            return None
        
        def find_label(widget):
            # Check if this is a label with "Mbps" text
            if isinstance(widget, Gtk.Label) and widget.get_text() == "Mbps":
                return widget
            
            # Search in children
            if hasattr(widget, 'get_first_child'):
                child = widget.get_first_child()
                while child:
                    result = find_label(child)
                    if result:
                        return result
                    child = child.get_next_sibling()
            elif isinstance(widget, Gtk.Box) or isinstance(widget, Gtk.Grid):
                for child in widget:
                    result = find_label(child)
                    if result:
                        return result
            
            return None
        
        # First try to find it in the gauge container
        if hasattr(self, 'gauge_container'):
            label = find_label(self.gauge_container)
            if label:
                return label
        
        # If not found in gauge container, search the entire content
        return find_label(content)

    def hide_result_url_row(self):
        """Find and hide the entire ActionRow containing the result URL"""
        # First try to find the parent of the result_url widget
        parent = self.result_url.get_parent()
        while parent and not isinstance(parent, Gtk.ListBoxRow) and not isinstance(parent, Adw.ActionRow):
            parent = parent.get_parent()
        
        if parent:
            parent.set_visible(False)
        else:
            # Fallback: just hide the URL widget itself
            self.result_url.set_visible(False)
            
            # Also try to find the row by iterating through the results_group
            if hasattr(self.results_group, 'get_first_child'):
                child = self.results_group.get_first_child()
                while child:
                    if isinstance(child, Adw.ActionRow) and child.get_title() == "Result URL":
                        child.set_visible(False)
                        break
                    child = child.get_next_sibling()

    def add_powered_by_label(self):
        """Add 'Powered by Ookla Speedtest' label to both initial screen and results page"""
        # Create the label for the initial screen
        self.powered_by_label = Gtk.Label()
        self.powered_by_label.set_text("Powered by Ookla Speedtest")
        self.powered_by_label.add_css_class("caption")  # Make it smaller
        self.powered_by_label.set_opacity(0.7)  # Make it slightly transparent
        self.powered_by_label.set_margin_top(12)
        self.powered_by_label.set_margin_bottom(12)
        self.powered_by_label.set_halign(Gtk.Align.CENTER)
        
        # Find the container for the initial screen
        content = self.get_content()
        if content:
            # Find the main vertical box that contains everything
            main_box = None
            if hasattr(content, 'get_first_child'):
                child = content.get_first_child()
                while child:
                    if isinstance(child, Gtk.Box) and child.get_orientation() == Gtk.Orientation.VERTICAL:
                        main_box = child
                        break
                    child = child.get_next_sibling()
            
            if main_box:
                # Find the AdwClamp which contains the main content
                clamp = None
                if hasattr(main_box, 'get_first_child'):
                    child = main_box.get_first_child()
                    while child:
                        if isinstance(child, Adw.Clamp):
                            clamp = child
                            break
                        elif isinstance(child, Gtk.ScrolledWindow):
                            # The clamp might be inside a ScrolledWindow
                            if hasattr(child, 'get_child'):
                                if isinstance(child.get_child(), Adw.Clamp):
                                    clamp = child.get_child()
                                    break
                        child = child.get_next_sibling()
                
                if clamp:
                    # Get the main content box inside the clamp
                    content_box = None
                    if hasattr(clamp, 'get_child'):
                        content_box = clamp.get_child()
                    
                    if content_box and isinstance(content_box, Gtk.Box):
                        # Add the powered by label at the end of the content box
                        content_box.append(self.powered_by_label)
        
        # Create a similar label for the results group
        self.results_powered_by_label = Gtk.Label()
        self.results_powered_by_label.set_text("Powered by Ookla Speedtest")
        self.results_powered_by_label.add_css_class("caption")
        self.results_powered_by_label.set_opacity(0.7)
        self.results_powered_by_label.set_halign(Gtk.Align.CENTER)
        self.results_powered_by_label.set_margin_top(12)
        
        # Add the label to the results group
        if hasattr(self.results_group, 'add_suffix_widget'):
            # For newer versions of libadwaita
            self.results_group.add_suffix_widget(self.results_powered_by_label)
        else:
            # For older versions, we need to find the parent of the results group
            parent = self.results_group.get_parent()
            if parent and isinstance(parent, Gtk.Box):
                # Create a container for the powered by label
                label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                label_box.append(self.results_powered_by_label)
                # Insert after the results group
                index = -1
                for i, child in enumerate(parent):
                    if child == self.results_group:
                        index = i
                        break
                if index >= 0:
                    parent.insert_child_after(label_box, self.results_group)