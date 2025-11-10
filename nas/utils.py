from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user
from app import get_db

# ---------------------------------------------------------------------
# Role-based access control decorator
# ---------------------------------------------------------------------
def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in.", "info")
                return redirect(url_for("auth.login"))
            if roles and getattr(current_user, "role", None) not in roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("home"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# ---------------------------------------------------------------------
# Permission-based access control helpers (using `permissions` table)
# ---------------------------------------------------------------------
def get_permissions(user_id):
    """Return dict with can_read, can_write, can_edit, is_admin for a user_id."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT can_read, can_write, can_edit, is_admin
            FROM permissions
            WHERE user_id = %s
        """, (user_id,))
        row = cur.fetchone()
        if not row:
            # default to read-only if missing
            return {"can_read": 1, "can_write": 0, "can_edit": 0, "is_admin": 0}
        return {
            "can_read": row[0],
            "can_write": row[1],
            "can_edit": row[2],
            "is_admin": row[3],
        }
    except Exception as e:
        # fail closed (no permissions) on error
        print("Error loading permissions:", e)
        return {"can_read": 0, "can_write": 0, "can_edit": 0, "is_admin": 0}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass

def perm_required(flag):
    """Decorator to enforce a specific permission flag, e.g., 'can_write' or 'can_edit'."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in first.", "info")
                return redirect(url_for("auth.login"))
            perms = get_permissions(current_user.id)
            if not perms.get(flag, 0):
                flash("You do not have permission for this action.", "danger")
                return redirect(url_for("home"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator
