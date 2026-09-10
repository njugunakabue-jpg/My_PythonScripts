import os
import shutil
import psutil
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

# -----------------------------
# Core Optimization Functions
# -----------------------------

def clear_temp():
    temp_dirs = []
    user_temp = os.getenv("TEMP")
    windows_dir = os.getenv("WINDIR")
    if user_temp:
        temp_dirs.append(Path(user_temp))
    if windows_dir:
        temp_dirs.append(Path(windows_dir) / "Temp")

    deleted = 0
    skipped = 0
    for d in temp_dirs:
        if d.exists():
            try:
                items = d.iterdir()
            except OSError:
                skipped += 1
                continue
            for item in items:
                try:
                    if item.is_file():
                        item.unlink()
                        deleted += 1
                    else:
                        shutil.rmtree(item)
                        deleted += 1
                except Exception:
                    skipped += 1
    messagebox.showinfo(
        "Temp Cleanup",
        f"Cleared {deleted} temp items.\nSkipped {skipped} item(s) due to permissions or use.",
    )

def list_startup_programs():
    startup_path = Path(os.getenv("APPDATA")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    items = [item.name for item in startup_path.iterdir()]
    messagebox.showinfo("Startup Programs", "\n".join(items) if items else "No startup programs found.")

def kill_heavy_processes(threshold=80):
    killed = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
        try:
            if proc.info['cpu_percent'] > threshold:
                psutil.Process(proc.info['pid']).terminate()
                killed.append(proc.info['name'])
        except Exception:
            pass
    messagebox.showinfo("Heavy Processes", f"Killed:\n" + "\n".join(killed) if killed else "No heavy processes.")

def get_top_memory_consumers(limit=3):
    consumers = []
    for proc in psutil.process_iter(['name', 'memory_info']):
        try:
            memory_mb = proc.info['memory_info'].rss / (1024 * 1024)
            consumers.append((memory_mb, proc.info['name'] or "Unknown"))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    consumers.sort(reverse=True)
    return consumers[:limit]

def update_stats():
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    cpu_label.config(text=f"CPU Usage: {cpu}%")
    ram_label.config(text=f"RAM Usage: {ram}%")
    top_consumers = get_top_memory_consumers()
    consumer_lines = [
        f"{index}. {name} ({memory_mb:.1f} MB)"
        for index, (memory_mb, name) in enumerate(top_consumers, start=1)
    ]
    memory_consumers_label.config(
        text="Top RAM Consumers:\n" + "\n".join(consumer_lines)
    )
    root.after(1500, update_stats)

# -----------------------------
# GUI Setup
# -----------------------------

root = tk.Tk()
root.title("PC Optimizer")
root.geometry("500x420")
root.resizable(False, False)

title = ttk.Label(root, text="PC Optimizer", font=("Segoe UI", 18, "bold"))
title.pack(pady=10)

cpu_label = ttk.Label(root, text="CPU Usage: --%", font=("Segoe UI", 12))
cpu_label.pack()

ram_label = ttk.Label(root, text="RAM Usage: --%", font=("Segoe UI", 12))
ram_label.pack()

memory_consumers_label = ttk.Label(
    root,
    text="Top RAM Consumers:\n--",
    font=("Segoe UI", 10),
    justify="left",
)
memory_consumers_label.pack(pady=(6, 0))

ttk.Separator(root, orient="horizontal").pack(fill="x", pady=10)

btn_frame = ttk.Frame(root)
btn_frame.pack(pady=10)

ttk.Button(btn_frame, text="Clear Temp Files", width=25, command=clear_temp).grid(row=0, column=0, pady=5)
ttk.Button(btn_frame, text="Show Startup Programs", width=25, command=list_startup_programs).grid(row=1, column=0, pady=5)
ttk.Button(btn_frame, text="Kill Heavy Processes", width=25, command=kill_heavy_processes).grid(row=2, column=0, pady=5)

update_stats()
root.mainloop()
