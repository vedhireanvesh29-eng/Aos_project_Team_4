from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from flask import Blueprint, flash, redirect, render_template, request, url_for, current_app
from flask_login import UserMixin, current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from .db import execute, query
from .utils import ensure_user_directory, role_required


auth_bp = Blueprint("auth", __name__, url_prefix="")


@auth_bp.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("files.index"))
    return redirect(url_for("auth.login"))


@dataclass
class User(UserMixin):
    id: int
    username: str
    password_hash: str
    role: str

    def get_id(self):
        return str(self.id)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @staticmethod
    def from_row(row: Optional[dict]) -> Optional["User"]:
        if not row:
            return None
        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            role=row["role"],
        )

    @staticmethod
    def get(user_id: int) -> Optional["User"]:
        row = query("SELECT * FROM users WHERE id=%s", (user_id,), fetchone=True)
        return User.from_row(row)

    @staticmethod
    def find_by_username(username: str) -> Optional["User"]:
        row = query("SELECT * FROM users WHERE username=%s", (username,), fetchone=True)
        return User.from_row(row)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.find_by_username(username)
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            current_app.logger.info("User %s logged in", username)
            return redirect(url_for("files.index"))
        flash("Invalid credentials", "danger")
    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    current_app.logger.info("User %s logged out", current_user.username)
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
@role_required("admin")
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "user")
        if not username or not password:
            flash("Username and password are required", "danger")
        elif role not in {"admin", "user"}:
            flash("Invalid role", "danger")
        elif User.find_by_username(username):
            flash("Username already exists", "danger")
        else:
            password_hash = generate_password_hash(password)
            execute(
                "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
                (username, password_hash, role),
            )
            ensure_user_directory(username)
            flash("User registered", "success")
            current_app.logger.info("Admin %s created user %s", current_user.username, username)
            return redirect(url_for("auth.users"))
    return render_template("auth/register.html")


@auth_bp.route("/users", methods=["GET"])
@role_required("admin")
def users():
    users = query("SELECT id, username, role, created_at FROM users ORDER BY created_at DESC")
    return render_template("auth/users.html", users=users)


@auth_bp.route("/users/<int:user_id>/update", methods=["POST"])
@role_required("admin")
def update_user(user_id: int):
    role = request.form.get("role", "user")
    password = request.form.get("password", "")
    if role not in {"admin", "user"}:
        flash("Invalid role", "danger")
        return redirect(url_for("auth.users"))
    if password:
        password_hash = generate_password_hash(password)
        execute(
            "UPDATE users SET role=%s, password_hash=%s WHERE id=%s",
            (role, password_hash, user_id),
        )
    else:
        execute("UPDATE users SET role=%s WHERE id=%s", (role, user_id))
    flash("User updated", "success")
    current_app.logger.info("Admin %s updated user %s", current_user.username, user_id)
    return redirect(url_for("auth.users"))


@auth_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@role_required("admin")
def delete_user(user_id: int):
    user = query("SELECT username FROM users WHERE id=%s", (user_id,), fetchone=True)
    execute("DELETE FROM users WHERE id=%s", (user_id,))
    if user:
        user_dir = Path(current_app.config["DATA_ROOT"]) / user["username"]
        if user_dir.exists():
            shutil.rmtree(user_dir, ignore_errors=True)
    flash("User deleted", "info")
    current_app.logger.info("Admin %s deleted user %s", current_user.username, user["username"] if user else user_id)
    return redirect(url_for("auth.users"))
