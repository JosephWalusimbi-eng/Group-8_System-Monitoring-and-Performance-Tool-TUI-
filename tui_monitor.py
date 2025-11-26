import curses, time, json, psutil
from datetime import datetime

CONFIG_PATH = "config.json"

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def format_bytes(n):
    for unit in ["B","KB","MB","GB","TB"]:
        if n < 1024:
            return f"{n:3.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"

def draw_bar(win, y, x, width, percent, color):
    fill = int((percent/100)*width)
    win.addstr(y, x, "[" + "#"*fill + " "*(width-fill) + "]", curses.color_pair(color))

def check_alerts(cfg, cpu, mem, disk, net_bps):
    th = cfg["thresholds"]
    alerts = []
    if cpu >= th["cpu_percent"]: alerts.append(f"CPU {cpu}%")
    if mem >= th["memory_percent"]: alerts.append(f"MEM {mem}%")
    if disk >= th["disk_percent"]: alerts.append(f"DISK {disk}%")
    if net_bps >= th["net_bytes_per_sec"]: alerts.append(f"NET {net_bps:.0f} B/s")
    return alerts

def main(stdscr):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_RED, -1)

    cfg = load_config()
    refresh = cfg["tui"]["refresh_interval"]

    prev_net = psutil.net_io_counters()
    prev_t = time.time()

    while True:
        stdscr.erase()

        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        net = psutil.net_io_counters()

        now = time.time()
        dt = now - prev_t
        net_bps = ((net.bytes_sent-prev_net.bytes_sent)+(net.bytes_recv-prev_net.bytes_recv))/dt
        prev_net, prev_t = net, now

        # header
        stdscr.addstr(0, 2, f"System Monitor — {datetime.utcnow().isoformat()}Z")

        # CPU
        color = 2 if cpu < 50 else (3 if cpu < 80 else 4)
        stdscr.addstr(2, 2, f"CPU: {cpu:.1f}%")
        draw_bar(stdscr, 3, 2, 40, cpu, color)

        # Memory
        m = mem.percent
        color = 2 if m < 50 else (3 if m < 80 else 4)
        stdscr.addstr(5, 2, f"Memory: {m:.1f}% ({format_bytes(mem.used)} / {format_bytes(mem.total)})")
        draw_bar(stdscr, 6, 2, 40, m, color)

        # Disk
        d = disk.percent
        color = 2 if d < 70 else (3 if d < 90 else 4)
        stdscr.addstr(8, 2, f"Disk: {d:.1f}% ({format_bytes(disk.used)} / {format_bytes(disk.total)})")
        draw_bar(stdscr, 9, 2, 40, d, color)

        # Network
        stdscr.addstr(11, 2, f"Network: {format_bytes(net_bps)}/s")

        # Alerts
        alerts = check_alerts(cfg, cpu, m, d, net_bps)
        stdscr.addstr(13, 2, "Alerts:")
        if alerts:
            for i, a in enumerate(alerts):
                stdscr.addstr(14+i, 4, f"- {a}", curses.color_pair(4))
        else:
            stdscr.addstr(14, 4, "No alerts", curses.color_pair(2))

        # Quit
        stdscr.addstr(20, 2, "Press 'q' to quit.")

        stdscr.refresh()
        stdscr.nodelay(True)
        key = stdscr.getch()
        if key == ord("q"):
            break

        time.sleep(refresh)

if __name__ == "__main__":
    curses.wrapper(main)
