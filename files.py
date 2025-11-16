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
    """Safely join paths to prevent directory traversal"""
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
            return {'can_read': True, 'can_write': True, 'can_delete': True, 'is_owner': True}
        
        # Check shared permissions
        cur.execute("""
            SELECT can_read, can_write
            FROM file_permissions
            WHERE file_id = %s AND user_id = %s
        """, (file_id, user_id))
        row = cur.fetchone()
        if row:
            return {
                'can_read': bool(row[0]), 
                'can_write': bool(row[1]), 
                'can_delete': False,
                'is_owner': False
            }
    except Exception as e:
        print(f"Error checking file permissions: {e}")
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass
    return {'can_read': False, 'can_write': False, 'can_delete': False, 'is_owner': False}

def is_admin(user):
    """Check if user has admin role"""
    return hasattr(user, 'role') and user.role == 'admin'

def get_user_accessible_files(user_id, is_admin_user):
    """Get all files that a user can access (own or shared)"""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        if is_admin_user:
            # Admin can see all files
            cur.execute("""
                SELECT f.id, f.path, f.owner_id, u.username, f.created_at
                FROM files f
                JOIN users u ON f.owner_id = u.id
                ORDER BY f.created_at DESC
            """)
        else:
            # Regular users see their own files + shared files
            cur.execute("""
                SELECT DISTINCT f.id, f.path, f.owner_id, u.username, f.created_at,
                       CASE WHEN f.owner_id = %s THEN 1 ELSE 0 END as is_owner,
                       COALESCE(fp.can_read, 0) as can_read,
                       COALESCE(fp.can_write, 0) as can_write
                FROM files f
                JOIN users u ON f.owner_id = u.id
                LEFT JOIN file_permissions fp ON f.id = fp.file_id AND fp.user_id = %s
                WHERE f.owner_id = %s OR fp.user_id = %s
                ORDER BY f.created_at DESC
            """, (user_id, user_id, user_id, user_id))
        
        files_list = []
        for row in cur.fetchall():
            if is_admin_user:
                files_list.append({
                    'id': row[0],
                    'path': row[1],
                    'owner_id': row[2],
                    'owner_name': row[3],
                    'created_at': row[4],
                    'can_read': True,
                    'can_write': True,
                    'can_delete': True,
                    'is_owner': False
                })
            else:
                is_owner = bool(row[5])
                files_list.append({
                    'id': row[0],
                    'path': row[1],
                    'owner_id': row[2],
                    'owner_name': row[3],
                    'created_at': row[4],
                    'can_read': is_owner or bool(row[6]),
                    'can_write': is_owner or bool(row[7]),
                    'can_delete': is_owner,
                    'is_owner': is_owner
                })
        
        return files_list
    except Exception as e:
        print(f"Error getting accessible files: {e}")
        return []
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

@files_bp.route("/")
@login_required
def index():
    """File manager main page - shows only files user has access to"""
    rel = request.args.get("p","")
    base = safe_join(rel)
    base.mkdir(parents=True, exist_ok=True)
    
    # Get all accessible files from database
    accessible_files = get_user_accessible_files(
        int(current_user.id), 
        is_admin(current_user)
    )
    
    # Create a map of file paths to permissions
    file_perms_map = {f['path']: f for f in accessible_files}
    
    items = []
    
    for name in sorted(os.listdir(base)):
        fp = base / name
        rel_path = str((Path(rel)/name) if rel else Path(name))
        
        # Always show directories
        if fp.is_dir():
            items.append({
                "name": name, 
                "is_dir": True,
                "rel": rel_path,
                "owner": None,
                "can_write": True,  # Can navigate into directories
                "can_delete": False,
                "is_owner": False
            })
        else:
            # Only show files the user has access to
            if rel_path in file_perms_map:
                file_info = file_perms_map[rel_path]
                items.append({
                    "name": name,
                    "is_dir": False,
                    "rel": rel_path,
                    "file_id": file_info['id'],
                    "owner": file_info['owner_name'],
                    "can_read": file_info['can_read'],
                    "can_write": file_info['can_write'],
                    "can_delete": file_info['can_delete'],
                    "is_owner": file_info['is_owner']
                })
    
    up = str(Path(rel).parent) if rel else ""
    return render_template("files/index.html", 
                         rel=rel, 
                         items=items, 
                         up=up, 
                         is_admin=is_admin(current_user))

@files_bp.route("/my-files")
@login_required
def my_files():
    """View all files accessible to the current user (own + shared)"""
    accessible_files = get_user_accessible_files(
        int(current_user.id), 
        is_admin(current_user)
    )
    
    return render_template("files/my_files.html", 
                         files=accessible_files,
                         is_admin=is_admin(current_user))

@files_bp.route("/upload", methods=["POST"])
@perm_required("can_write")
def upload():
    """Upload a file and record it in the database"""
    rel = request.form.get("rel","")
    f = request.files.get("file")
    if not f or not f.filename:
        flash("No file selected.", "danger")
        return redirect(url_for("files.index", p=rel))
    
    filename = secure_filename(f.filename)
    dest = safe_join(rel) / filename
    
    # Check if file already exists
    if dest.exists():
        flash(f"File '{filename}' already exists. Please rename or delete the existing file first.", "danger")
        return redirect(url_for("files.index", p=rel))
    
    f.save(dest)
    
    # Record in database
    rel_path = str((Path(rel)/filename) if rel else Path(filename))
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO files (path, owner_id) VALUES (%s, %s)
        """, (rel_path, current_user.id))
        conn.commit()
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
    """Download a file (requires read permission)"""
    rel = request.args.get("rel","")
    filepath = safe_join(rel)
    
    if not filepath.is_file():
        flash("File not found.", "danger")
        return redirect(url_for("files.index"))
    
    # Check permissions
    metadata = get_file_metadata(rel)
    if metadata:
        if not is_admin(current_user):
            perms = get_file_permissions(metadata['id'], int(current_user.id))
            if not perms['can_read']:
                flash("You don't have permission to download this file.", "danger")
                return redirect(url_for("files.index"))
    else:
        flash("File not found in database.", "danger")
        return redirect(url_for("files.index"))
    
    return send_file(filepath, as_attachment=True)

@files_bp.route("/mkdir", methods=["POST"])
@perm_required("can_write")
def mkdir():
    """Create a new directory"""
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
    """Rename a file or folder (requires ownership)"""
    rel = request.form.get("rel","")
    old = request.form.get("old","")
    new = secure_filename(request.form.get("new",""))
    
    if not new:
        flash("New name is required.", "danger")
        return redirect(url_for("files.index", p=rel))
    
    old_path = safe_join(rel) / old
    new_path = safe_join(rel) / new
    
    if not old_path.exists():
        flash(f"'{old}' does not exist.", "danger")
        return redirect(url_for("files.index", p=rel))
    
    if new_path.exists():
        flash(f"'{new}' already exists.", "danger")
        return redirect(url_for("files.index", p=rel))
    
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
            conn.commit()
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
    """Delete a file or folder (requires ownership or admin)"""
    rel = request.form.get("rel","")
    target = request.form.get("target","")
    p = safe_join(rel) / target
    
    if not p.exists():
        flash(f"'{target}' does not exist.", "danger")
        return redirect(url_for("files.index", p=rel))
    
    # Check permissions for files
    if p.is_file():
        target_rel = str((Path(rel)/target) if rel else Path(target))
        metadata = get_file_metadata(target_rel)
        if metadata:
            if not is_admin(current_user):
                perms = get_file_permissions(metadata['id'], int(current_user.id))
                if not perms['can_delete']:
                    flash("You don't have permission to delete this file.", "danger")
                    return redirect(url_for("files.index", p=rel))
            
            # Delete from database (this will cascade to file_permissions)
            try:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("DELETE FROM files WHERE id = %s", (metadata['id'],))
                conn.commit()
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
            flash("Folder not empty. Please delete all contents first.", "danger")
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
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT owner_id, path FROM files WHERE id = %s", (file_id,))
        row = cur.fetchone()
        
        if not row:
            flash("File not found.", "danger")
            return redirect(url_for("files.index"))
        
        # Only owner or admin can share
        if row[0] != int(current_user.id) and not is_admin(current_user):
            flash("You can only share your own files.", "danger")
            return redirect(url_for("files.index"))
        
        if request.method == "POST":
            user_id = request.form.get("user_id")
            can_read = request.form.get("can_read") == "on"
            can_write = request.form.get("can_write") == "on"
            
            if not user_id:
                flash("Please select a user.", "danger")
                return redirect(url_for("files.share", file_id=file_id))
            
            # Prevent sharing with self
            if int(user_id) == int(current_user.id):
                flash("You cannot share a file with yourself.", "info")
                return redirect(url_for("files.share", file_id=file_id))
            
            # Insert or update permission
            cur.execute("""
                INSERT INTO file_permissions (file_id, user_id, can_read, can_write)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE can_read = %s, can_write = %s
            """, (file_id, user_id, can_read, can_write, can_read, can_write))
            conn.commit()
            
            flash("Permissions updated successfully.", "success")
            return redirect(url_for("files.share", file_id=file_id))
        
        # Get current permissions
        cur.execute("""
            SELECT fp.user_id, u.username, fp.can_read, fp.can_write, fp.granted_at
            FROM file_permissions fp
            JOIN users u ON fp.user_id = u.id
            WHERE fp.file_id = %s
            ORDER BY u.username
        """, (file_id,))
        permissions = cur.fetchall()
        
        # Get all users except owner
        cur.execute("""
            SELECT id, username FROM users 
            WHERE id != %s
            ORDER BY username
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
        conn.commit()
        flash("Permission revoked successfully.", "info")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass
    
    return redirect(url_for("files.share", file_id=file_id))
