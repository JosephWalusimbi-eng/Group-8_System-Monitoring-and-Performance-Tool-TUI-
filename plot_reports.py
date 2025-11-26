import pandas as pd
import matplotlib.pyplot as plt
import json
import ast

CSV = "metrics_log.csv"

def clean_cpu_percore(value):
    try:
        # Try loading as JSON
        return json.loads(value)
    except:
        try:
            # Try loading as Python list
            return ast.literal_eval(value)
        except:
            return []

df = pd.read_csv(
    CSV,
    on_bad_lines="skip"    # <-- ignore malformed rows
)

# Fix cpu_percore column
if "cpu_percore" in df.columns:
    df["cpu_percore"] = df["cpu_percore"].astype(str).apply(clean_cpu_percore)

df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
df = df.dropna(subset=["ts"])  # drop bad timestamps

def make_plot(column, filename):
    plt.figure(figsize=(10,4))
    plt.plot(df["ts"], df[column], linewidth=1)
    plt.title(column)
    plt.xlabel("Time")
    plt.ylabel(column)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

make_plot("cpu_percent", "cpu_percent.png")
make_plot("mem_percent", "mem_percent.png")
make_plot("disk_percent", "disk_percent.png")

print("Saved cpu_percent.png, mem_percent.png, disk_percent.png")
