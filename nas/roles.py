from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

def role_required(*roles):
    """Restrict a route to specific roles (e.g., admin)."""
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
