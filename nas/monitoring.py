from __future__ import annotations

from pathlib import Path
from typing import List

import psutil
from flask import Blueprint, current_app, render_template
from flask_login import login_required

from .utils import ensure_directory, role_required


monitor_bp = Blueprint("monitor", __name__, url_prefix="/monitor")


@monitor_bp.route("/")
@login_required
@role_required("admin")
def dashboard():
    data_root = Path(current_app.config["DATA_ROOT"])
    backup_root = Path(current_app.config["BACKUP_ROOT"])
    ensure_directory(data_root)
    ensure_directory(backup_root)
    disk_usage = psutil.disk_usage(str(data_root)) if data_root.exists() else None
    cpu = psutil.cpu_percent(interval=None)
    log_path = Path("/var/log/syslog")
    log_lines: List[str] = []
    if log_path.exists():
        try:
            with log_path.open("r", errors="ignore") as fh:
                log_lines = fh.readlines()[-100:]
        except PermissionError:
            log_lines = ["Permission denied reading syslog"]
    return render_template(
        "monitor/dashboard.html",
        cpu=cpu,
        disk_usage=disk_usage,
        data_root=str(data_root),
        backup_root=str(backup_root),
        log_lines=log_lines,
    )
