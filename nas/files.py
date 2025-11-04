from __future__ import annotations

import shutil
from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.exceptions import Forbidden
from werkzeug.utils import secure_filename

from .db import execute, query
from .utils import ensure_directory, ensure_user_directory, secure_path


files_bp = Blueprint("files", __name__, url_prefix="/files")


def _data_root() -> Path:
    root = Path(current_app.config["DATA_ROOT"])
    ensure_directory(root)
    return root


def _rel_to_root(path: Path) -> str:
    data_root = _data_root()
    return str(path.relative_to(data_root)) if path != data_root else ""


def _resolve_path(subpath: str) -> tuple[Path, str]:
    data_root = _data_root()
    if current_user.role == "admin":
        base = data_root
    else:
        base = ensure_user_directory(current_user.username)
    target = secure_path(base, subpath or ".")
    rel_path = _rel_to_root(target)
    return target, rel_path


def _assert_file_access(rel_path: str):
    if current_user.role == "admin":
        return
    meta = query("SELECT owner_id FROM files WHERE path=%s", (rel_path,), fetchone=True)
    if not meta or meta["owner_id"] != current_user.id:
        current_app.logger.warning("Unauthorized file access attempt by %s", current_user.username)
        raise Forbidden("You do not own this file")


@files_bp.route("/", defaults={"subpath": ""})
@files_bp.route("/<path:subpath>")
@login_required
def index(subpath: str):
    target, rel_path = _resolve_path(subpath)
    if not target.exists():
        flash("Path does not exist", "warning")
        return redirect(url_for("files.index"))
    if not target.is_dir():
        _assert_file_access(rel_path)
        return send_file(target, as_attachment=True)
    entries = []
    for entry in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        entry_rel = _rel_to_root(entry)
        owner = None
        if entry.is_file():
            meta = query(
                "SELECT u.username FROM files f JOIN users u ON f.owner_id = u.id WHERE f.path=%s",
                (entry_rel,),
                fetchone=True,
            )
            owner = meta["username"] if meta else None
        entries.append(
            {
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "path": entry_rel,
                "owner": owner,
            }
        )
    breadcrumbs = [segment for segment in rel_path.split("/") if segment]
    return render_template(
        "files/index.html",
        entries=entries,
        current_path=rel_path,
        breadcrumbs=breadcrumbs,
    )


@files_bp.route("/upload", methods=["POST"])
@login_required
def upload():
    current_path = request.form.get("current_path", "")
    file = request.files.get("file")
    if not file or file.filename == "":
        flash("No file selected", "danger")
        return redirect(url_for("files.index", subpath=current_path))
    filename = secure_filename(file.filename)
    target_dir, _ = _resolve_path(current_path)
    if not target_dir.is_dir():
        flash("Invalid upload directory", "danger")
        return redirect(url_for("files.index"))
    destination = target_dir / filename
    file.save(destination)
    rel_path = _rel_to_root(destination)
    existing = query("SELECT id FROM files WHERE path=%s", (rel_path,), fetchone=True)
    if existing:
        execute("UPDATE files SET owner_id=%s WHERE id=%s", (current_user.id, existing["id"]))
    else:
        execute(
            "INSERT INTO files (path, owner_id) VALUES (%s, %s)",
            (rel_path, current_user.id),
        )
    flash("File uploaded", "success")
    current_app.logger.info("User %s uploaded %s", current_user.username, rel_path)
    return redirect(url_for("files.index", subpath=current_path))


@files_bp.route("/download/<path:subpath>")
@login_required
def download(subpath: str):
    target, rel_path = _resolve_path(subpath)
    if not target.is_file():
        flash("File not found", "danger")
        return redirect(url_for("files.index"))
    _assert_file_access(rel_path)
    return send_file(target, as_attachment=True)


@files_bp.route("/delete", methods=["POST"])
@login_required
def delete():
    path = request.form.get("path", "")
    target, rel_path = _resolve_path(path)
    if not target.exists():
        flash("Path does not exist", "warning")
        return redirect(url_for("files.index"))
    if target == _data_root():
        flash("Cannot delete root directory", "danger")
        return redirect(url_for("files.index"))
    if target.is_file():
        _assert_file_access(rel_path)
        target.unlink()
        execute("DELETE FROM files WHERE path=%s", (rel_path,))
    else:
        shutil.rmtree(target)
        like_pattern = f"{rel_path}/%" if rel_path else "%"
        execute("DELETE FROM files WHERE path LIKE %s", (like_pattern,))
    flash("Deleted", "info")
    current_app.logger.info("User %s deleted %s", current_user.username, rel_path)
    parent = target.parent if target.parent.exists() else _data_root()
    return redirect(url_for("files.index", subpath=_rel_to_root(parent)))


@files_bp.route("/mkdir", methods=["POST"])
@login_required
def mkdir():
    current_path = request.form.get("current_path", "")
    dirname = secure_filename(request.form.get("dirname", "").strip())
    if not dirname:
        flash("Folder name required", "danger")
        return redirect(url_for("files.index", subpath=current_path))
    target_dir, _ = _resolve_path(current_path)
    new_dir = target_dir / dirname
    new_dir.mkdir(exist_ok=True)
    flash("Folder created", "success")
    current_app.logger.info("User %s created folder %s", current_user.username, dirname)
    return redirect(url_for("files.index", subpath=current_path))


@files_bp.route("/rename", methods=["POST"])
@login_required
def rename():
    path = request.form.get("path", "")
    new_name = secure_filename(request.form.get("new_name", "").strip())
    if not new_name:
        flash("New name required", "danger")
        return redirect(url_for("files.index"))
    target, rel_path = _resolve_path(path)
    if target == _data_root():
        flash("Cannot rename root directory", "danger")
        return redirect(url_for("files.index"))
    new_target = target.parent / new_name
    new_rel = _rel_to_root(new_target)
    if target.is_file():
        _assert_file_access(rel_path)
        target.rename(new_target)
        execute("UPDATE files SET path=%s WHERE path=%s", (new_rel, rel_path))
    else:
        target.rename(new_target)
        children = query("SELECT id, path FROM files WHERE path LIKE %s", (f"{rel_path}/%",))
        for child in children or []:
            updated = child["path"].replace(rel_path + "/", new_rel + "/", 1)
            execute("UPDATE files SET path=%s WHERE id=%s", (updated, child["id"]))
    flash("Renamed", "success")
    current_app.logger.info("User %s renamed %s to %s", current_user.username, rel_path, new_rel)
    return redirect(url_for("files.index", subpath=_rel_to_root(new_target.parent)))
