# Speedtest GUI

A GTK4/libadwaita application for testing internet connection speed using the Ookla Speedtest CLI.

![Screenshot from 2025-03-19 12-45-44](https://github.com/user-attachments/assets/24371fbf-196a-483a-bee7-31f74e0031e4)
![Screenshot from 2025-03-19 12-47-25](https://github.com/user-attachments/assets/afe76255-ca4f-4b29-8930-bf4e4f0a2c1a)
![Screenshot from 2025-03-19 12-47-52](https://github.com/user-attachments/assets/51d03ee8-239f-43ca-aff8-859c0bd54ef0)

## Features

- Clean, modern interface built with GTK4 and libadwaita
- Real-time download and upload speed visualization
- Detailed test results including:
  - Download speed
  - Upload speed
  - Ping latency
  - Jitter
  - Packet loss
  - ISP information
  - Server information

## Requirements

- Python 3.6+
- GTK 4.0+
- libadwaita 1.0+
- Ookla Speedtest CLI

## Installation

### 1. Install GTK4 and libadwaita

#### Ubuntu/Debian:
```
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 libadwaita-1-dev
```

#### Fedora:
```
sudo dnf install python3-gobject gtk4 libadwaita-devel
```

#### Arch Linux:
```
sudo pacman -S python-gobject gtk4 libadwaita
```

### 2. Install Ookla Speedtest CLI

Download the official Speedtest CLI from [Ookla's website](https://www.speedtest.net/apps/cli).

Extract the downloaded package and place the `speedtest` binary in the `ookla-speedtest-gui` directory within the application folder, or ensure it's available in your system PATH.

### 3. Clone the repository

```
git clone https://github.com/macuseri686/ookla-speedtest-gui.git
cd ookla-speedtest-gui
```

### 4. Run the application

```
python3 -m speedtest_gui
```

## Usage

1. Launch the application
2. Click the "Start Test" button to begin the speed test
3. View real-time progress with the gauge visualization
4. When the test completes, detailed results will be displayed
5. Click "Start Test" again to run another test

## Development

### Project Structure

- `speedtest_gui/` - Main package directory
  - `__init__.py` - Package initialization
  - `main.py` - Application entry point
  - `window.py` - Main application window
  - `speedtest_runner.py` - Backend for running speedtest CLI
  - `ui/` - UI definition files
    - `window.ui` - Main window UI definition

### Building from Source

```
# Install development dependencies
pip install meson ninja

# Configure build
meson setup builddir

# Build
meson compile -C builddir

# Install
meson install -C builddir
```

## Troubleshooting

### Speedtest CLI not found

Ensure the Ookla Speedtest CLI binary is:
1. Placed in the `ookla-speedtest-gui` directory within the application folder, or
2. Available in your system PATH

### Permission Issues

If you encounter permission issues with the Speedtest CLI:

```
chmod +x ookla-speedtest/speedtest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Powered by [Ookla Speedtest](https://www.speedtest.net/)
- Built with [GTK](https://www.gtk.org/) and [libadwaita](https://gnome.pages.gitlab.gnome.org/libadwaita/)
