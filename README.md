# Group 8 System Monitor (TUI + CSV logging)

# System Monitor (Python)

A lightweight cross-platform system performance monitor using:

- psutil (metrics)
- curses (TUI)
- CSV logging
- Configurable alert thresholds

## PROJECT STRUCTURE
system-monitor/
│
├─ venv                   # virtual environment
├─ metrics_collector.py   # Logs metrics to CSV
├─ tui_monitor.py         # TUI dashboard script first version
├─ plot_reports.py        # Generates PNG performance graphs
├─ tui_monitors.py        # Final script for color coded TUI dashbaord
├─ config.json            # Thresholds + settings
├─ requirements.txt
└─ README.md


## How to Use
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

### Start the Logger
python metrics_collector.py

### Open another terminal in the venv and Start the first version of the Dashboard that we created
python tui_monitor.py

### Open another terminal in the venv and Start the Final Dashboard that we created
python tui_monitors.py

## Open another terminal in the venv Generate Report Graphs
python plot_reports.py


This will produce:
- cpu_plot.png
- memory_plot.png
- disk_plot.png


## Requirements
- Python 3.8+
- pip install -r requirements.txt

## Run
1. Start collector (logs to CSV):
   python metrics_collector.py

2. Start TUI dashboard:
   python tui_monitor.py

## Config
Edit `config.json` to change thresholds and intervals.

## Notes
On Windows install `windows-curses`.
Linux and MacOS have native support for curses 
