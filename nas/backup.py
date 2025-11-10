import os, tarfile, time, shutil
from pathlib import Path
from flask import render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required
from nas.__init__ import backup_bp
from nas.roles import role_required  # Added import

DATA_ROOT = Path(os.getenv("DATA_ROOT","/srv/nas_data"))
BACKUP_ROOT = Path(os.getenv("BACKUP_ROOT","/srv/nas_backups"))

@backup_bp.route("/")
@role_required("admin")
def index():
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    archives = sorted([f for f in BACKUP_ROOT.glob("*.tar.gz")],
                      key=lambda p: p.stat().st_mtime, reverse=True)
    return render_template("backup/index.html", archives=[a.name for a in archives])

@backup_bp.route("/create", methods=["POST"])
@role_required("admin")
def create():
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    out = BACKUP_ROOT / f"nas_backup_{ts}.tar.gz"
    with tarfile.open(out, "w:gz") as tar:
        tar.add(DATA_ROOT, arcname="nas_data")
    flash(f"Backup created: {out.name}", "success")
    return redirect(url_for("backup.index"))

@backup_bp.route("/download")
@role_required("admin")
def download():
    name = request.args.get("name","")
    p = (BACKUP_ROOT / name).resolve()
    if not p.is_file() or not str(p).startswith(str(BACKUP_ROOT.resolve())):
        flash("Invalid archive.", "danger")
        return redirect(url_for("backup.index"))
    return send_file(p, as_attachment=True)

@backup_bp.route("/restore", methods=["POST"])
@role_required("admin")
def restore():
    name = request.form.get("name","")
    p = (BACKUP_ROOT / name).resolve()
    if not p.is_file() or not str(p).startswith(str(BACKUP_ROOT.resolve())):
        flash("Invalid archive.", "danger")
        return redirect(url_for("backup.index"))
    tmp = BACKUP_ROOT / "_restore_tmp"
    if tmp.exists(): shutil.rmtree(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    with tarfile.open(p, "r:gz") as tar:
        tar.extractall(tmp)
    src = tmp / "nas_data"
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        dest_dir = (DATA_ROOT / rel)
        dest_dir.mkdir(parents=True, exist_ok=True)
        for f in files:
            shutil.copy2(os.path.join(root,f), dest_dir / f)
    shutil.rmtree(tmp)
    flash("Restore completed.", "success")
    return redirect(url_for("backup.index"))
