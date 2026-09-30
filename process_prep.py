import psutil

explorer_pid = None
for p in psutil.process_iter(['pid', 'name']):
    try:
        if p.name().lower() == "explorer.exe":
            explorer_pid = p.pid
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        continue