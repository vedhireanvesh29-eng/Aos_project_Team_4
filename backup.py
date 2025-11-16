import os, tarfile, time, shutil
from pathlib import Path
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required
from nas.__init__ import backup_bp
from nas.roles import role_required
from app import get_db

DATA_ROOT = Path(os.getenv("DATA_ROOT","/srv/nas_data"))
BACKUP_ROOT = Path(os.getenv("BACKUP_ROOT","/srv/nas_backups"))

def create_backup_entry(archive_name):
    """Record backup in database"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO backups (archive_path) VALUES (%s)",
            (archive_name,)
        )
        conn.commit()
    except Exception as e:
        print(f"Error recording backup: {e}")
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

def get_backups_from_db():
    """Get all backups from database"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, archive_path, created_at 
            FROM backups 
            ORDER BY created_at DESC
        """)
        return cur.fetchall()
    except Exception as e:
        print(f"Error getting backups: {e}")
        return []
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

def delete_backup_from_db(backup_id):
    """Delete backup record from database"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM backups WHERE id = %s", (backup_id,))
        conn.commit()
    except Exception as e:
        print(f"Error deleting backup record: {e}")
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

def perform_backup():
    """Create a backup archive"""
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    archive_name = f"nas_backup_{ts}.tar.gz"
    out = BACKUP_ROOT / archive_name
    
    try:
        with tarfile.open(out, "w:gz") as tar:
            tar.add(DATA_ROOT, arcname="nas_data")
        
        # Record in database
        create_backup_entry(archive_name)
        return archive_name
    except Exception as e:
        if out.exists():
            out.unlink()
        raise e

@backup_bp.route("/")
@role_required("admin")
def index():
    """Backup management page"""
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    
    # Get backups from database
    db_backups = get_backups_from_db()
    
    # Get actual files from filesystem
    actual_files = {f.name: f for f in BACKUP_ROOT.glob("*.tar.gz")}
    
    # Combine database info with file stats
    backups = []
    for backup_id, archive_name, created_at in db_backups:
        if archive_name in actual_files:
            file_path = actual_files[archive_name]
            size_mb = file_path.stat().st_size / (1024 * 1024)
            backups.append({
                'id': backup_id,
                'name': archive_name,
                'created_at': created_at,
                'size_mb': round(size_mb, 2)
            })
    
    # Also show orphaned files (files not in database)
    db_names = {name for _, name, _ in db_backups}
    for filename, filepath in actual_files.items():
        if filename not in db_names:
            size_mb = filepath.stat().st_size / (1024 * 1024)
            backups.append({
                'id': None,
                'name': filename,
                'created_at': datetime.fromtimestamp(filepath.stat().st_mtime),
                'size_mb': round(size_mb, 2)
            })
    
    # Sort by creation time (newest first)
    backups.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render_template("backup/index.html", backups=backups)

@backup_bp.route("/create", methods=["POST"])
@role_required("admin")
def create():
    """Create a new backup"""
    try:
        archive_name = perform_backup()
        flash(f"Backup created successfully: {archive_name}", "success")
    except Exception as e:
        flash(f"Backup failed: {str(e)}", "danger")
    
    return redirect(url_for("backup.index"))

@backup_bp.route("/auto-create", methods=["POST"])
@role_required("admin")
def auto_create():
    """Create automatic daily backups"""
    try:
        # Check if a backup was created today
        today = datetime.now().strftime("%Y%m%d")
        backups = get_backups_from_db()
        
        today_backup_exists = any(
            backup[1].startswith(f"nas_backup_{today}") 
            for backup in backups
        )
        
        if today_backup_exists:
            flash("A backup for today already exists.", "info")
        else:
            archive_name = perform_backup()
            flash(f"Daily backup created: {archive_name}", "success")
    except Exception as e:
        flash(f"Auto backup failed: {str(e)}", "danger")
    
    return redirect(url_for("backup.index"))

@backup_bp.route("/download/<int:backup_id>")
@role_required("admin")
def download(backup_id):
    """Download a backup archive"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT archive_path FROM backups WHERE id = %s", (backup_id,))
        row = cur.fetchone()
        
        if not row:
            flash("Backup not found in database.", "danger")
            return redirect(url_for("backup.index"))
        
        archive_name = row[0]
        p = (BACKUP_ROOT / archive_name).resolve()
        
        if not p.is_file() or not str(p).startswith(str(BACKUP_ROOT.resolve())):
            flash("Invalid backup file.", "danger")
            return redirect(url_for("backup.index"))
        
        return send_file(p, as_attachment=True)
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for("backup.index"))
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

@backup_bp.route("/restore/<int:backup_id>", methods=["POST"])
@role_required("admin")
def restore(backup_id):
    """Restore from a backup"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT archive_path FROM backups WHERE id = %s", (backup_id,))
        row = cur.fetchone()
        
        if not row:
            flash("Backup not found.", "danger")
            return redirect(url_for("backup.index"))
        
        archive_name = row[0]
        p = (BACKUP_ROOT / archive_name).resolve()
        
        if not p.is_file() or not str(p).startswith(str(BACKUP_ROOT.resolve())):
            flash("Invalid backup file.", "danger")
            return redirect(url_for("backup.index"))
        
        # Create a safety backup before restore
        safety_backup_name = f"pre_restore_backup_{time.strftime('%Y%m%d_%H%M%S')}.tar.gz"
        safety_backup = BACKUP_ROOT / safety_backup_name
        with tarfile.open(safety_backup, "w:gz") as tar:
            tar.add(DATA_ROOT, arcname="nas_data")
        create_backup_entry(safety_backup_name)
        
        # Restore from backup
        tmp = BACKUP_ROOT / "_restore_tmp"
        if tmp.exists(): 
            shutil.rmtree(tmp)
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
        flash(f"Restore completed from {archive_name}. A safety backup was created before restore.", "success")
    except Exception as e:
        flash(f"Restore failed: {str(e)}", "danger")
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass
    
    return redirect(url_for("backup.index"))

@backup_bp.route("/delete/<int:backup_id>", methods=["POST"])
@role_required("admin")
def delete(backup_id):
    """Delete a backup"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT archive_path FROM backups WHERE id = %s", (backup_id,))
        row = cur.fetchone()
        
        if not row:
            flash("Backup not found.", "danger")
            return redirect(url_for("backup.index"))
        
        archive_name = row[0]
        p = (BACKUP_ROOT / archive_name).resolve()
        
        # Delete file if it exists
        if p.is_file() and str(p).startswith(str(BACKUP_ROOT.resolve())):
            p.unlink()
        
        # Delete from database
        delete_backup_from_db(backup_id)
        
        flash(f"Backup '{archive_name}' deleted.", "info")
    except Exception as e:
        flash(f"Error deleting backup: {str(e)}", "danger")
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass
    
    return redirect(url_for("backup.index"))
