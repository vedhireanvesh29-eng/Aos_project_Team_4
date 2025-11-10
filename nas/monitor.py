import os, psutil, shutil
from pathlib import Path
from flask import render_template
from flask_login import login_required
from .__init__ import monitor_bp

DATA_ROOT = Path(os.getenv("DATA_ROOT","/srv/nas_data"))

@monitor_bp.route("/")
@login_required
def index():
    cpu = psutil.cpu_percent(interval=0.2)
    mem = psutil.virtual_memory()
    disk_total, disk_used, disk_free = shutil.disk_usage(str(DATA_ROOT))
    try:
        load1, load5, load15 = os.getloadavg()
    except OSError:
        load1 = load5 = load15 = 0.0
    procs = []
    for p in psutil.process_iter(attrs=["pid","name","cpu_percent"]):
        procs.append(p.info)
    procs = sorted(procs, key=lambda x: x.get("cpu_percent",0), reverse=True)[:5]
    stats = {
        "cpu": cpu,
        "mem": {"total": mem.total, "used": mem.used, "percent": mem.percent},
        "disk": {"total": disk_total, "used": disk_used, "free": disk_free},
        "load": {"1m": load1, "5m": load5, "15m": load15},
        "procs": procs
    }
    return render_template("monitor/index.html", stats=stats, data_root=str(DATA_ROOT))
