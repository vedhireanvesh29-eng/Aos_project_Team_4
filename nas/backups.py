from __future__ import annotations

import datetime as dt
import subprocess
import tarfile
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required
from werkzeug.exceptions import Forbidden

from .db import execute, query
from .utils import ensure_directory, role_required


backups_bp = Blueprint("backups", __name__, url_prefix="/backups")


def _backup_root() -> Path:
    root = Path(current_app.config["BACKUP_ROOT"])
    ensure_directory(root)
    return root


def _data_root() -> Path:
    root = Path(current_app.config["DATA_ROOT"])
    ensure_directory(root)
    return root


def _safe_extract(tar: tarfile.TarFile, target_dir: Path) -> None:
    target_dir = target_dir.resolve()
    for member in tar.getmembers():
        member_path = target_dir / member.name
        if target_dir not in member_path.resolve().parents and member_path.resolve() != target_dir:
            raise Forbidden("Invalid archive contents")
    tar.extractall(path=target_dir)


@backups_bp.route("/")
@login_required
@role_required("admin")
def list_backups():
    backups = query("SELECT id, archive_path, created_at FROM backups ORDER BY created_at DESC") or []
    return render_template("backup/backups.html", backups=backups)


def perform_backup() -> Path:
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    archive_name = f"{timestamp}.tar.gz"
    archive_path = _backup_root() / archive_name
    data_root = _data_root()
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(str(data_root), arcname=".")
    rel_path = str(archive_path)
    execute("INSERT INTO backups (archive_path) VALUES (%s)", (rel_path,))
    current_app.logger.info("Backup created at %s", rel_path)
    return archive_path


@backups_bp.route("/create", methods=["POST"])
@login_required
@role_required("admin")
def create_backup():
    archive_path = perform_backup()
    flash("Backup created", "success")
    return redirect(url_for("backups.list_backups"))


@backups_bp.route("/restore", methods=["POST"])
@login_required
@role_required("admin")
def restore_backup():
    archive = request.form.get("archive")
    if not archive:
        flash("Archive not specified", "danger")
        return redirect(url_for("backups.list_backups"))
    backup_root = _backup_root()
    archive_path = (backup_root / Path(archive).name).resolve()
    if backup_root not in archive_path.parents and archive_path != backup_root:
        flash("Invalid archive path", "danger")
        return redirect(url_for("backups.list_backups"))
    if not archive_path.exists():
        flash("Archive not found", "danger")
        return redirect(url_for("backups.list_backups"))
    data_root = _data_root()
    with tarfile.open(archive_path, "r:gz") as tar:
        _safe_extract(tar, data_root)
    flash("Backup restored", "success")
    current_app.logger.info("Restored backup %s", archive_path)
    return redirect(url_for("backups.list_backups"))


@backups_bp.route("/schedule", methods=["POST"])
@login_required
@role_required("admin")
def schedule_backup():
    schedule = request.form.get("schedule", "02:00")
    try:
        hour, minute = schedule.split(":")
        cron_line = f"{int(minute)} {int(hour)} * * * flask --app app run-backup"
    except (ValueError, TypeError):
        flash("Invalid schedule format", "danger")
        return redirect(url_for("backups.list_backups"))
    try:
        existing = subprocess.run(["crontab", "-l"], check=False, capture_output=True, text=True)
        lines = [line for line in existing.stdout.splitlines() if "flask --app app run-backup" not in line]
        lines.append(cron_line)
        subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True, check=True)
        flash("Backup schedule updated", "success")
        current_app.logger.info("Backup schedule set: %s", cron_line)
    except FileNotFoundError:
        flash("crontab command not available", "warning")
    return redirect(url_for("backups.list_backups"))
