from __future__ import annotations

import functools
import subprocess
from pathlib import Path
from typing import Callable

from flask import current_app, redirect, url_for
from flask_login import current_user
from werkzeug.exceptions import Forbidden

from .db import execute


ALLOWED_ROLES = {"admin", "user"}


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def ensure_user_directory(username: str) -> Path:
    base = Path(current_app.config["DATA_ROOT"])
    ensure_directory(base)
    user_dir = base / username
    ensure_directory(user_dir)
    return user_dir


def secure_path(base: Path, target: str) -> Path:
    base = base.resolve()
    candidate = (base / target).resolve()
    if base not in candidate.parents and candidate != base:
        raise Forbidden("Invalid path")
    return candidate


def role_required(*roles: str):
    roles = set(roles)

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if roles and current_user.role not in roles:
                current_app.logger.warning(
                    "Access denied for user %s on %s", current_user.username, func.__name__
                )
                raise Forbidden("You do not have access to this resource")
            return func(*args, **kwargs)

        return wrapper

    return decorator


def register_cli_commands(app):
    import click
    from werkzeug.security import generate_password_hash
    from .db import query

    @app.cli.command("create-admin")
    @click.argument("username")
    @click.argument("password")
    def create_admin(username: str, password: str):
        """Create or update an admin user with the given credentials."""
        if not username or not password:
            raise click.BadParameter("Username and password are required")
        existing = query("SELECT id FROM users WHERE username=%s", (username,), fetchone=True)
        password_hash = generate_password_hash(password)
        if existing:
            execute(
                "UPDATE users SET password_hash=%s, role='admin' WHERE id=%s",
                (password_hash, existing["id"]),
            )
            click.echo("Updated existing admin user")
        else:
            execute(
                "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, 'admin')",
                (username, password_hash),
            )
            click.echo("Created new admin user")
        ensure_user_directory(username)

    @app.cli.command("run-backup")
    def run_backup():
        """Create a backup archive immediately."""
        from .backups import perform_backup

        path = perform_backup()
        click.echo(f"Backup written to {path}")

    @app.cli.command("schedule-backup")
    @click.argument("schedule")
    def schedule_backup(schedule: str):
        """Set the cron schedule for daily backups. Format: 'HH:MM'."""
        hour, minute = schedule.split(":")
        cron_line = f"{int(minute)} {int(hour)} * * * flask --app app run-backup"
        try:
            existing = subprocess.run(
                ["crontab", "-l"],
                check=False,
                capture_output=True,
                text=True,
            )
            lines = [line for line in existing.stdout.splitlines() if "flask --app app run-backup" not in line]
            lines.append(cron_line)
            subprocess.run(
                ["crontab", "-"],
                input="\n".join(lines) + "\n",
                text=True,
                check=True,
            )
            click.echo("Cron schedule updated")
        except FileNotFoundError:
            click.echo("crontab command not available", err=True)


__all__ = [
    "ensure_user_directory",
    "secure_path",
    "role_required",
    "register_cli_commands",
]
