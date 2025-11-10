import os
from pathlib import Path
from flask import render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required
from werkzeug.utils import secure_filename
from nas.__init__ import files_bp
from nas.permissions import perm_required  # Added import

DATA_ROOT = Path(os.getenv("DATA_ROOT","/srv/nas_data")).resolve()

def safe_join(rel=""):
    p = (DATA_ROOT / rel).resolve()
    if not str(p).startswith(str(DATA_ROOT)):
        raise ValueError("Invalid path")
    return p

@files_bp.route("/")
@login_required
def index():
    rel = request.args.get("p","")
    base = safe_join(rel)
    base.mkdir(parents=True, exist_ok=True)
    items = []
    for name in sorted(os.listdir(base)):
        fp = base / name
        items.append({"name": name, "is_dir": fp.is_dir(),
                      "rel": str((Path(rel)/name) if rel else Path(name))})
    up = str(Path(rel).parent) if rel else ""
    return render_template("files/index.html", rel=rel, items=items, up=up)

@files_bp.route("/upload", methods=["POST"])
@perm_required("can_write")
def upload():
    rel = request.form.get("rel","")
    f = request.files.get("file")
    if not f or not f.filename:
        flash("No file selected.", "danger")
        return redirect(url_for("files.index", p=rel))
    dest = safe_join(rel) / secure_filename(f.filename)
    f.save(dest)
    flash("Uploaded.", "success")
    return redirect(url_for("files.index", p=rel))

@files_bp.route("/mkdir", methods=["POST"])
@perm_required("can_write")
def mkdir():
    rel = request.form.get("rel","")
    name = secure_filename(request.form.get("name",""))
    if not name:
        flash("Folder name required.", "danger")
        return redirect(url_for("files.index", p=rel))
    (safe_join(rel) / name).mkdir(parents=True, exist_ok=True)
    flash("Folder created.", "success")
    return redirect(url_for("files.index", p=rel))

@files_bp.route("/rename", methods=["POST"])
@perm_required("can_edit")
def rename():
    rel = request.form.get("rel","")
    old = request.form.get("old","")
    new = secure_filename(request.form.get("new",""))
    (safe_join(rel) / old).rename(safe_join(rel) / new)
    flash("Renamed.", "success")
    return redirect(url_for("files.index", p=rel))

@files_bp.route("/delete", methods=["POST"])
@perm_required("can_edit")
def delete():
    rel = request.form.get("rel","")
    target = request.form.get("target","")
    p = safe_join(rel) / target
    if p.is_dir():
        try:
            p.rmdir()
        except OSError:
            flash("Folder not empty.", "danger")
            return redirect(url_for("files.index", p=rel))
    else:
        if p.exists():
            p.unlink()
    flash("Deleted.", "info")
    return redirect(url_for("files.index", p=rel))
