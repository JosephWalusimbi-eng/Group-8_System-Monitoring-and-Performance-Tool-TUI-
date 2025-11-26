import time, csv, json, os
from datetime import datetime
import psutil

CONFIG_PATH = "config.json"

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def human_ts():
    return datetime.utcnow().isoformat() + "Z"

def sample(prev_net):
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_percore = psutil.cpu_percent(interval=None, percpu=True)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    disk_io = psutil.disk_io_counters()
    net = psutil.net_io_counters()

    net_bps = 0.0
    if prev_net is not None:
        prev_sent, prev_recv, prev_t = prev_net
        dt = time.time() - prev_t if time.time() - prev_t > 0 else 1.0
        net_bps = ((net.bytes_sent - prev_sent) + (net.bytes_recv - prev_recv)) / dt

    return {
        "ts": human_ts(),
        "cpu_percent": cpu_percent,
        "cpu_percore": cpu_percore,
        "mem_total": mem.total,
        "mem_used": mem.used,
        "mem_available": mem.available,
        "mem_percent": mem.percent,
        "disk_total": disk.total,
        "disk_used": disk.used,
        "disk_percent": disk.percent,
        "disk_read_count": disk_io.read_count,
        "disk_write_count": disk_io.write_count,
        "disk_read_bytes": disk_io.read_bytes,
        "disk_write_bytes": disk_io.write_bytes,
        "net_bytes_sent": net.bytes_sent,
        "net_bytes_recv": net.bytes_recv,
        "net_bytes_per_sec": net_bps
    }

def check_alerts(cfg, row):
    alerts = []
    th = cfg["thresholds"]
    if row["cpu_percent"] >= th.get("cpu_percent", 100):
        alerts.append(f"High CPU {row['cpu_percent']}%")
    if row["mem_percent"] >= th.get("memory_percent", 100):
        alerts.append(f"High Memory {row['mem_percent']}%")
    if row["disk_percent"] >= th.get("disk_percent", 100):
        alerts.append(f"High Disk usage {row['disk_percent']}%")
    if th.get("net_bytes_per_sec") and row["net_bytes_per_sec"] >= th["net_bytes_per_sec"]:
        alerts.append(f"High Network throughput {row['net_bytes_per_sec']:.0f} B/s")
    return alerts

def ensure_headers(path, headers):
    if not os.path.exists(path):
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()

def main():
    cfg = load_config()
    csv_path = cfg["csv_log_path"]
    alert_path = cfg["alert_log_path"]
    interval = cfg["log_interval_seconds"]

    headers = [
        "ts","cpu_percent","cpu_percore","mem_total","mem_used",
        "mem_available","mem_percent","disk_total","disk_used",
        "disk_percent","disk_read_count","disk_write_count",
        "disk_read_bytes","disk_write_bytes","net_bytes_sent",
        "net_bytes_recv","net_bytes_per_sec"
    ]

    ensure_headers(csv_path, headers)

    net0 = psutil.net_io_counters()
    prev_net = (net0.bytes_sent, net0.bytes_recv, time.time())

    print(f"Starting metrics logger (interval={interval}s) writing to {csv_path}")
    try:
        while True:
            row = sample(prev_net)

            with open(csv_path, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                row["cpu_percore"] = json.dumps(row["cpu_percore"])
                writer.writerow(row)

            alerts = check_alerts(cfg, row)
            if alerts:
                with open(alert_path, "a") as af:
                    for a in alerts:
                        af.write(f"{row['ts']} - {a}\n")
                        print(f"ALERT: {a}")

            net_c = psutil.net_io_counters()
            prev_net = (net_c.bytes_sent, net_c.bytes_recv, time.time())
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Stopping metrics logger.")

if __name__ == "__main__":
    main()
