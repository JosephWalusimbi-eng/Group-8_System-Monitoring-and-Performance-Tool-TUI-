import curses, time, json, psutil, os
from datetime import datetime

CONFIG_PATH = "config.json"


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def format_bytes(n):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def percent_color(val, threshold):
    if val < 0.75 * threshold:
        return 2  # green
    if val < threshold:
        return 3  # yellow
    return 4      # red


def rate_color(value):
    if value < 1024 * 100:  # <100KB/s
        return 2
    if value < 1024 * 1024:  # <1MB/s
        return 3
    return 4


def draw_bar(win, y, x, width, percent, color):
    percent = max(0, min(percent, 100))
    inner = width - 2
    filled = int(inner * (percent / 100))
    bar = "[" + "#" * filled + " " * (inner - filled) + "]"
    try:
        win.addstr(y, x, bar[:width], curses.color_pair(color))
    except curses.error:
        pass


def compute_disk_io(prev, prev_t):
    now = time.time()
    cur = psutil.disk_io_counters()
    dt = max(1e-6, now - prev_t)
    read_bps = (cur.read_bytes - prev.read_bytes) / dt
    write_bps = (cur.write_bytes - prev.write_bytes) / dt
    return cur, now, read_bps, write_bps


def compute_net_io(prev, prev_t):
    now = time.time()
    cur = psutil.net_io_counters()
    dt = max(1e-6, now - prev_t)
    up = (cur.bytes_sent - prev.bytes_sent) / dt
    down = (cur.bytes_recv - prev.bytes_recv) / dt
    return cur, now, up, down


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
    th = cfg["thresholds"]

    prev_disk = psutil.disk_io_counters()
    prev_net = psutil.net_io_counters()
    prev_t = time.time()
    last_alerts = set()

    stdscr.nodelay(True)

    while True:
        stdscr.erase()
        maxy, maxx = stdscr.getmaxyx()

        timestamp = datetime.utcnow().isoformat() + "Z"
        stdscr.addstr(0, 2, f"System Monitor — {timestamp}    (q to quit)", curses.color_pair(1))

        # Collect metrics
        cpu = psutil.cpu_percent()
        cpu_per_core = psutil.cpu_percent(percpu=True)
        mem = psutil.virtual_memory()
        disk_usage = psutil.disk_usage("C:/")
        prev_disk, prev_t, disk_read, disk_write = compute_disk_io(prev_disk, prev_t)
        prev_net, prev_t, net_up, net_down = compute_net_io(prev_net, prev_t)

        row = 2
        col_mid = maxx // 2

        # ───────────────────────────── CPU Section ─────────────────────────────
        stdscr.addstr(row, 2, "+---------------- CPU ----------------+", curses.color_pair(1)); row += 1
        stdscr.addstr(row, 4, f"Total: {cpu:.1f}%", curses.color_pair(percent_color(cpu, th['cpu_percent']))); row += 1
        draw_bar(stdscr, row, 4, col_mid - 8, cpu, percent_color(cpu, th['cpu_percent'])); row += 2

        stdscr.addstr(row, 4, "Per-Core:", curses.color_pair(1)); row += 1
        for i, pct in enumerate(cpu_per_core):
            stdscr.addstr(row, 6, f"Core {i}: {pct:4.1f}%", curses.color_pair(percent_color(pct, th['cpu_percent'])))
            draw_bar(stdscr, row, 20, col_mid - 24, pct, percent_color(pct, th['cpu_percent']))
            row += 1

        # Reset row for right column
        row = 2
        col = col_mid + 2

        # ───────────────────────────── Memory Section ─────────────────────────────
        stdscr.addstr(row, col, "+----------------------------- Memory -----------------------------+", curses.color_pair(1)); row += 1
        stdscr.addstr(row, col + 2, f"Usage: {mem.percent:.1f}%"); row += 1
        draw_bar(stdscr, row, col + 2, maxx - col - 4, mem.percent, percent_color(mem.percent, th['memory_percent'])); row += 2
        stdscr.addstr(row, col + 2, f"{format_bytes(mem.used)} / {format_bytes(mem.total)}"); row += 2

        # ───────────────────────────── Disk Section ─────────────────────────────
        stdscr.addstr(row, col, "+-------------------------- Disk ---------------------------+", curses.color_pair(1)); row += 1
        stdscr.addstr(row, col + 2, f"Usage: {disk_usage.percent:.1f}%"); row += 1
        draw_bar(stdscr, row, col + 2, maxx - col - 4, disk_usage.percent, percent_color(disk_usage.percent, th['disk_percent'])); row += 2
        stdscr.addstr(row, col + 2, f"Read:  {format_bytes(disk_read)}/s", curses.color_pair(rate_color(disk_read))); row += 1
        stdscr.addstr(row, col + 2, f"Write: {format_bytes(disk_write)}/s", curses.color_pair(rate_color(disk_write))); row += 2

        # ───────────────────────────── Network Section ─────────────────────────────
        stdscr.addstr(row, col, "+-------------------------------- Network ---------------------------+", curses.color_pair(1)); row += 1
        stdscr.addstr(row, col + 2, f"Upload:   {format_bytes(net_up)}/s", curses.color_pair(rate_color(net_up))); row += 1
        stdscr.addstr(row, col + 2, f"Download: {format_bytes(net_down)}/s", curses.color_pair(rate_color(net_down))); row += 2

        # ───────────────────────────── Alerts Footer ─────────────────────────────
        alerts = []
        if cpu >= th["cpu_percent"]:
            alerts.append(f"High CPU: {cpu:.1f}%")
        if mem.percent >= th["memory_percent"]:
            alerts.append(f"High Memory: {mem.percent:.1f}%")
        if disk_usage.percent >= th["disk_percent"]:
            alerts.append(f"High Disk: {disk_usage.percent:.1f}%")
        if net_up >= th["net_bytes_per_sec"] or net_down >= th["net_bytes_per_sec"]:
            alerts.append("High Network I/O")

        # --- Logging system for warnings (only logs new alerts) ---
        alert_log_path = cfg.get("alert_log_path", "alerts.log")
        current_alert_set = set(alerts)
        new_alerts = [a for a in current_alert_set if a not in last_alerts]

        if new_alerts:
            ts = datetime.utcnow().isoformat() + "Z"
            try:
                with open(alert_log_path, "a") as f:
                    for a in new_alerts:
                        f.write(f"{ts} - {a}\n")
            except:
                pass

        last_alerts = current_alert_set

        # --- Footer Drawing ---
        alerts_y = maxy - 4
        stdscr.addstr(alerts_y, 2, "-" * (maxx - 4), curses.color_pair(1))
        stdscr.addstr(alerts_y + 1, 2, "Alerts:", curses.color_pair(1))

        # Determine blink support and blinking state
        blink_supported = curses.tigetnum("blink") != -1 if hasattr(curses, "tigetnum") else False
        blink_state = int(time.time() * 2) % 2  # toggle ~2x per sec

        if alerts:
            for i, a in enumerate(alerts[:2]):
                if blink_supported:
                    # Real blinking (if terminal supports it)
                    attr = curses.color_pair(4) | curses.A_BLINK
                    stdscr.addstr(alerts_y + 2 + i, 4, a, attr)
                else:
                    # Simulated blinking (Windows CMD fallback)
                    if blink_state == 0:
                        stdscr.addstr(alerts_y + 2 + i, 4, a, curses.color_pair(4))
                    else:
                        stdscr.addstr(alerts_y + 2 + i, 4, " " * len(a))
        else:
            stdscr.addstr(alerts_y + 2, 4, "No alerts", curses.color_pair(2))

        stdscr.refresh()

        key = stdscr.getch()
        if key == ord("q"):
            break

        time.sleep(refresh)


if __name__ == "__main__":
    curses.wrapper(main)
