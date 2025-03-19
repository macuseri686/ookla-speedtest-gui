import gi
gi.require_version('GLib', '2.0')
from gi.repository import GObject, GLib

import subprocess
import json
import re
import threading
import time
import shlex
import sys
import os

class SpeedtestRunner(GObject.Object):
    __gsignals__ = {
        'progress': (GObject.SignalFlags.RUN_FIRST, None, (str, float, str)),
        'completed': (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        'error': (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.process = None
        self.thread = None
        
    def start_test(self):
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_test)
        self.thread.daemon = True
        self.thread.start()
        
    def cancel_test(self):
        if not self.running:
            return
            
        if self.process:
            try:
                self.process.terminate()
            except:
                pass
                
        self.running = False
        
    def _run_test(self):
        try:
            # Emit progress for initialization
            GLib.idle_add(self.emit, "progress", "init", 0.1, "Finding optimal server...")
            
            print("DEBUG: Starting speedtest process")
            
            # Path to the Ookla speedtest CLI - updated path
            speedtest_path = "./ookla-speedtest-gui/speedtest"
            
            # Check if the file exists at the specified path
            if not os.path.isfile(speedtest_path):
                # Try alternative paths
                alternative_paths = [
                    "ookla-speedtest/speedtest",  # No leading ./
                    "/home/macuseri686/ookla-speedtest-gui/speedtest",  # Full path
                    "speedtest"  # Just the command name, rely on PATH
                ]
                
                for path in alternative_paths:
                    if os.path.isfile(path):
                        speedtest_path = path
                        print(f"DEBUG: Found speedtest at {speedtest_path}")
                        break
                    elif path == "speedtest":
                        # Try to find it in PATH
                        try:
                            which_result = subprocess.run(["which", "speedtest"], 
                                                         capture_output=True, text=True)
                            if which_result.returncode == 0:
                                speedtest_path = which_result.stdout.strip()
                                print(f"DEBUG: Found speedtest in PATH at {speedtest_path}")
                                break
                        except:
                            pass
            
            print(f"DEBUG: Using speedtest path: {speedtest_path}")
            
            # Run the speedtest command with progress output
            cmd = [speedtest_path, "--format=json", "--progress=yes"]
            print(f"DEBUG: Running command: {' '.join(cmd)}")
            
            # First check if speedtest CLI is available
            try:
                print("DEBUG: Checking speedtest CLI availability")
                version_check = subprocess.run(
                    [speedtest_path, "--version"], 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                print(f"DEBUG: Version check result: {version_check.returncode}")
                print(f"DEBUG: Version check stdout: {version_check.stdout}")
                print(f"DEBUG: Version check stderr: {version_check.stderr}")
                
                if version_check.returncode != 0:
                    error_msg = f"Speedtest CLI not working properly: {version_check.stderr}"
                    print(f"ERROR: {error_msg}")
                    GLib.idle_add(self.emit, "error", error_msg)
                    self.running = False
                    return
            except Exception as e:
                error_msg = f"Failed to run speedtest command: {str(e)}"
                print(f"ERROR: {error_msg}")
                GLib.idle_add(self.emit, "error", error_msg)
                self.running = False
                return
            
            # Now run the actual test
            print("DEBUG: Starting actual speedtest")
            self.process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )
            
            # Start a thread to read stderr and print it
            def read_stderr():
                for line in self.process.stderr:
                    print(f"DEBUG STDERR: {line.strip()}")
            
            stderr_thread = threading.Thread(target=read_stderr)
            stderr_thread.daemon = True
            stderr_thread.start()
            
            # Variables to store server info
            server_name = "Unknown"
            server_location = "Unknown"
            
            # Process output in real-time
            output = ""
            for line in self.process.stdout:
                if not self.running:
                    break
                
                line = line.strip()
                print(f"DEBUG STDOUT: {line}")
                
                # Try to parse progress information
                try:
                    data = json.loads(line)
                    
                    # Check if this is a progress update
                    if "type" in data:
                        # Extract server info from testStart event
                        if data["type"] == "testStart" and "server" in data:
                            server_name = data["server"].get("name", "Unknown")
                            server_location = data["server"].get("location", "Unknown")
                            country = data["server"].get("country", "")
                            
                            # Combine location and country if both are available
                            if server_location and country and server_location != country:
                                server_location = f"{server_location}, {country}"
                            elif not server_location and country:
                                server_location = country
                            
                            # Update status with server info
                            status_message = f"Testing with {server_name} ({server_location})"
                            GLib.idle_add(self.emit, "progress", "server_info", 0, status_message)
                        
                        if data["type"] == "download":
                            # Convert bandwidth from bytes/s to Mbps (bytes/s * 8 / 1,000,000)
                            bandwidth_mbps = data["download"]["bandwidth"] * 8 / 1_000_000
                            progress = data["download"].get("progress", 0)
                            
                            # Create a status message with the current speed and server info
                            status_message = f"Running download test"
                            if server_name != "Unknown" and server_location != "Unknown":
                                status_message += f" - {server_name} ({server_location})"
                            
                            # Emit both the progress percentage and the raw speed value
                            GLib.idle_add(self.emit, "progress", "download", progress, status_message)
                            GLib.idle_add(self.emit, "progress", "download_raw", bandwidth_mbps, status_message)
                            
                        elif data["type"] == "upload":
                            # Convert bandwidth from bytes/s to Mbps (bytes/s * 8 / 1,000,000)
                            bandwidth_mbps = data["upload"]["bandwidth"] * 8 / 1_000_000
                            progress = data["upload"].get("progress", 0)
                            
                            # Create a status message with the current speed and server info
                            status_message = f"Running upload test"
                            if server_name != "Unknown" and server_location != "Unknown":
                                status_message += f" - {server_name} ({server_location})"
                            
                            # Emit both the progress percentage and the raw speed value
                            GLib.idle_add(self.emit, "progress", "upload", progress, status_message)
                            GLib.idle_add(self.emit, "progress", "upload_raw", bandwidth_mbps, status_message)
                            
                        elif data["type"] == "ping":
                            # Update status for ping test
                            progress = data["ping"].get("progress", 0)
                            latency = data["ping"].get("latency", 0)
                            status_message = f"Testing ping: {latency:.2f} ms"
                            if server_name != "Unknown" and server_location != "Unknown":
                                status_message += f" - {server_name} ({server_location})"
                            GLib.idle_add(self.emit, "progress", "ping", progress, status_message)
                            
                        # Check if this is the final result
                        elif data["type"] == "result":
                            output = line
                    
                except json.JSONDecodeError:
                    # Not valid JSON or not a progress update
                    pass
            
            # Parse the JSON result
            if output:
                print("DEBUG: Processing JSON result")
                try:
                    result = json.loads(output)
                    print(f"DEBUG: Parsed JSON successfully")
                    
                    # Extract server location from result if not already set
                    if "server" in result and server_location == "Unknown":
                        server_location = result["server"].get("location", "Unknown")
                        country = result["server"].get("country", "")
                        if server_location and country and server_location != country:
                            server_location = f"{server_location}, {country}"
                        elif not server_location and country:
                            server_location = country
                    
                    # Convert to our format
                    parsed_result = {
                        'download': result.get('download', {}).get('bandwidth', 0) * 8 / 1_000_000,  # Convert to Mbps
                        'upload': result.get('upload', {}).get('bandwidth', 0) * 8 / 1_000_000,      # Convert to Mbps
                        'ping': result.get('ping', {}).get('latency', 0),
                        'jitter': result.get('ping', {}).get('jitter', 0),
                        'packet_loss': result.get('packetLoss', 0),
                        'isp': result.get('isp', 'Unknown'),
                        'server': f"{result.get('server', {}).get('name', 'Unknown')} ({result.get('server', {}).get('id', 'Unknown')})",
                        'server_location': server_location,
                        'result_url': result.get('result', {}).get('url')
                    }
                    
                    print(f"DEBUG: Emitting completed signal with results: {parsed_result}")
                    GLib.idle_add(self.emit, "completed", parsed_result)
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON: {e}")
                    print(f"Output: {output}")
                    GLib.idle_add(self.emit, "error", f"Failed to parse speedtest results: {str(e)}")
            
            # Get the return code
            print("DEBUG: Waiting for process to complete")
            self.process.wait()
            
            if not self.running:
                print("DEBUG: Process was cancelled")
                return
                
            print(f"DEBUG: Process completed with return code: {self.process.returncode}")
            if self.process.returncode != 0 and not output:
                stderr_output = self.process.stderr.read()
                error_msg = f"Speedtest failed with code {self.process.returncode}: {stderr_output.strip()}"
                print(f"ERROR: {error_msg}")
                GLib.idle_add(self.emit, "error", error_msg)
                
        except Exception as e:
            if self.running:
                error_msg = f"Unexpected error: {str(e)}"
                print(f"ERROR: {error_msg}")
                import traceback
                traceback.print_exc()
                GLib.idle_add(self.emit, "error", error_msg)
                
        finally:
            print("DEBUG: Test finished, cleaning up")
            self.running = False
            self.process = None 