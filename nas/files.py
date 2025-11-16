import os
from pathlib import Path
from flask import render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from nas.__init__ import files_bp
from nas.permissions import perm_required
from app import get_db

DATA_ROOT = Path(os.getenv("DATA_ROOT","/srv/nas_data")).resolve()

def safe_join(rel=""):
    p = (DATA_ROOT / rel).resolve()
    if not str(p).startswith(str(DATA_ROOT)):
        raise ValueError("Invalid path")
    return p

def get_file_metadata(rel_path):
    """Get file metadata from database including owner and permissions"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT f.id, f.owner_id, u.username, f.created_at
            FROM files f
            JOIN users u ON f.owner_id = u.id
            WHERE f.path = %s
        """, (rel_path,))
        row = cur.fetchone()
        if row:
            return {
                'id': row[0],
                'owner_id': row[1],
                'owner_name': row[2],
                'created_at': row[3]
            }
    except Exception as e:
        print(f"Error getting file metadata: {e}")
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass
    return None

def get_file_permissions(file_id, user_id):
    """Check if user has permission to access a file"""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Check if user is file owner
        cur.execute("SELECT owner_id FROM files WHERE id = %s", (file_id,))
        row = cur.fetchone()
        if row and row[0] == user_id:
            return {'can_read': True, 'can_write': True, 'can_delete': True}
        
        # Check shared permissions
        cur.execute("""
            SELECT can_read, can_write
            FROM file_permissions
            WHERE file_id = %s AND user_id = %s
        """, (file_id, user_id))
        row = cur.fetchone()
        if row:
            return {'can_read': row[0], 'can_write': row[1], 'can_delete': False}
    except Exception as e:
        print(f"Error checking file permissions: {e}")
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass
    return {'can_read': False, 'can_write': False, 'can_delete': False}

def is_admin(user):
    """Check if user has admin role"""
    return hasattr(user, 'role') and user.role == 'admin'

@files_bp.route("/")
@login_required
def index():
    rel = request.args.get("p","")
    base = safe_join(rel)
    base.mkdir(parents=True, exist_ok=True)
    items = []
    
    for name in sorted(os.listdir(base)):
        fp = base / name
        rel_path = str((Path(rel)/name) if rel else Path(name))
        
        item_data = {
            "name": name, 
            "is_dir": fp.is_dir(),
            "rel": rel_path,
            "owner": None,
            "can_write": False,
            "can_delete": False
        }
        
        # Get file metadata if it's a file
        if not fp.is_dir():
            metadata = get_file_metadata(rel_path)
            if metadata:
                item_data['owner'] = metadata['owner_name']
                item_data['file_id'] = metadata['id']
                
                # Check permissions
                if is_admin(current_user):
                    item_data['can_write'] = True
                    item_data['can_delete'] = True
                else:
                    perms = get_file_permissions(metadata['id'], current_user.id)
                    item_data['can_write'] = perms['can_write']
                    item_data['can_delete'] = perms['can_delete']
        
        items.append(item_data)
    
    up = str(Path(rel).parent) if rel else ""
    return render_template("files/index.html", rel=rel, items=items, up=up, is_admin=is_admin(current_user))

@files_bp.route("/upload", methods=["POST"])
@perm_required("can_write")
def upload():
    rel = request.form.get("rel","")
    f = request.files.get("file")
    if not f or not f.filename:
        flash("No file selected.", "danger")
        return redirect(url_for("files.index", p=rel))
    
    filename = secure_filename(f.filename)
    dest = safe_join(rel) / filename
    f.save(dest)
    
    # Record in database
    rel_path = str((Path(rel)/filename) if rel else Path(filename))
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO files (path, owner_id) VALUES (%s, %s)
        """, (rel_path, current_user.id))
        flash(f"Uploaded '{filename}' successfully.", "success")
    except Exception as e:
        flash(f"File uploaded but database error: {e}", "danger")
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass
    
    return redirect(url_for("files.index", p=rel))

@files_bp.route("/download")
@login_required
def download():
    rel = request.args.get("rel","")
    filepath = safe_join(rel)
    
    if not filepath.is_file():
        flash("File not found.", "danger")
        return redirect(url_for("files.index"))
    
    # Check permissions
    metadata = get_file_metadata(rel)
    if metadata:
        if not is_admin(current_user):
            perms = get_file_permissions(metadata['id'], current_user.id)
            if not perms['can_read']:
                flash("You don't have permission to download this file.", "danger")
                return redirect(url_for("files.index"))
    
    return send_file(filepath, as_attachment=True)

@files_bp.route("/mkdir", methods=["POST"])
@perm_required("can_write")
def mkdir():
    rel = request.form.get("rel","")
    name = secure_filename(request.form.get("name",""))
    if not name:
        flash("Folder name required.", "danger")
        return redirect(url_for("files.index", p=rel))
    (safe_join(rel) / name).mkdir(parents=True, exist_ok=True)
    flash(f"Folder '{name}' created.", "success")
    return redirect(url_for("files.index", p=rel))

@files_bp.route("/rename", methods=["POST"])
@perm_required("can_edit")
def rename():
    rel = request.form.get("rel","")
    old = request.form.get("old","")
    new = secure_filename(request.form.get("new",""))
    
    old_path = safe_join(rel) / old
    new_path = safe_join(rel) / new
    
    # Check permissions for files
    if old_path.is_file():
        old_rel = str((Path(rel)/old) if rel else Path(old))
        metadata = get_file_metadata(old_rel)
        if metadata and not is_admin(current_user):
            if metadata['owner_id'] != int(current_user.id):
                flash("You can only rename your own files.", "danger")
                return redirect(url_for("files.index", p=rel))
    
    old_path.rename(new_path)
    
    # Update database if it's a file
    if new_path.is_file():
        try:
            conn = get_db()
            cur = conn.cursor()
            old_rel = str((Path(rel)/old) if rel else Path(old))
            new_rel = str((Path(rel)/new) if rel else Path(new))
            cur.execute("UPDATE files SET path = %s WHERE path = %s", (new_rel, old_rel))
        except Exception as e:
            print(f"Error updating file path: {e}")
        finally:
            try:
                cur.close()
                conn.close()
            except:
                pass
    
    flash(f"Renamed '{old}' to '{new}'.", "success")
    return redirect(url_for("files.index", p=rel))

@files_bp.route("/delete", methods=["POST"])
@perm_required("can_edit")
def delete():
    rel = request.form.get("rel","")
    target = request.form.get("target","")
    p = safe_join(rel) / target
    
    # Check permissions for files
    if p.is_file():
        target_rel = str((Path(rel)/target) if rel else Path(target))
        metadata = get_file_metadata(target_rel)
        if metadata:
            if not is_admin(current_user):
                perms = get_file_permissions(metadata['id'], current_user.id)
                if not perms['can_delete']:
                    flash("You don't have permission to delete this file.", "danger")
                    return redirect(url_for("files.index", p=rel))
            
            # Delete from database
            try:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("DELETE FROM files WHERE id = %s", (metadata['id'],))
            except Exception as e:
                flash(f"Database error: {e}", "danger")
                return redirect(url_for("files.index", p=rel))
            finally:
                try:
                    cur.close()
                    conn.close()
                except:
                    pass
    
    # Delete from filesystem
    if p.is_dir():
        try:
            p.rmdir()
        except OSError:
            flash("Folder not empty.", "danger")
            return redirect(url_for("files.index", p=rel))
    else:
        if p.exists():
            p.unlink()
    
    flash(f"Deleted '{target}'.", "info")
    return redirect(url_for("files.index", p=rel))

@files_bp.route("/share/<int:file_id>", methods=["GET", "POST"])
@login_required
def share(file_id):
    """Share a file with other users"""
    # Check if user owns the file or is admin
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT owner_id, path FROM files WHERE id = %s", (file_id,))
        row = cur.fetchone()
        
        if not row:
            flash("File not found.", "danger")
            return redirect(url_for("files.index"))
        
        if row[0] != int(current_user.id) and not is_admin(current_user):
            flash("You can only share your own files.", "danger")
            return redirect(url_for("files.index"))
        
        if request.method == "POST":
            user_id = request.form.get("user_id")
            can_read = request.form.get("can_read") == "on"
            can_write = request.form.get("can_write") == "on"
            
            # Insert or update permission
            cur.execute("""
                INSERT INTO file_permissions (file_id, user_id, can_read, can_write)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE can_read = %s, can_write = %s
            """, (file_id, user_id, can_read, can_write, can_read, can_write))
            
            flash("Permissions updated.", "success")
            return redirect(url_for("files.share", file_id=file_id))
        
        # Get current permissions
        cur.execute("""
            SELECT fp.user_id, u.username, fp.can_read, fp.can_write
            FROM file_permissions fp
            JOIN users u ON fp.user_id = u.id
            WHERE fp.file_id = %s
        """, (file_id,))
        permissions = cur.fetchall()
        
        # Get all users except owner
        cur.execute("""
            SELECT id, username FROM users WHERE id != %s
        """, (row[0],))
        available_users = cur.fetchall()
        
        return render_template("files/share.html", 
                             file_id=file_id, 
                             file_path=row[1],
                             permissions=permissions,
                             available_users=available_users)
    except Exception as e:
        flash(f"Error: {e}", "danger")
        return redirect(url_for("files.index"))
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

@files_bp.route("/share/<int:file_id>/revoke/<int:user_id>", methods=["POST"])
@login_required
def revoke_permission(file_id, user_id):
    """Revoke file access from a user"""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Check ownership
        cur.execute("SELECT owner_id FROM files WHERE id = %s", (file_id,))
        row = cur.fetchone()
        if not row or (row[0] != int(current_user.id) and not is_admin(current_user)):
            flash("Permission denied.", "danger")
            return redirect(url_for("files.index"))
        
        cur.execute("DELETE FROM file_permissions WHERE file_id = %s AND user_id = %s", 
                   (file_id, user_id))
        flash("Permission revoked.", "info")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass
    
    return redirect(url_for("files.share", file_id=file_id))
