from flask import render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from .utils import role_required
from .__init__ import auth_bp
from app import get_db, User

def init_auth_routes(app, bp):
    @bp.route("/login", methods=["GET","POST"])
    def login():
        if request.method == "POST":
            u = request.form.get("username","").strip()
            p = request.form.get("password","")
            conn = get_db(); cur = conn.cursor()
            cur.execute("SELECT id, username, password_hash, role FROM users WHERE username=%s",(u,))
            row = cur.fetchone()
            if row and check_password_hash(row[2], p):
                login_user(User(row[0], row[1], row[3]))
                flash("Logged in.", "success")
                return redirect(url_for("home"))
            flash("Invalid username or password.", "danger")
        return render_template("auth/login.html")

    @bp.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Logged out.", "info")
        return redirect(url_for("home"))

    @bp.route("/users")
    @role_required("admin")
    def users():
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT id, username, role, created_at FROM users ORDER BY id")
        return render_template("auth/users.html", users=cur.fetchall())

    @bp.route("/users/create", methods=["POST"])
    @role_required("admin")
    def create_user():
        username = request.form["username"].strip()
        password = request.form["password"]
        role = request.form.get("role","user")
        if not username or not password:
            flash("Username and password required.", "danger")
            return redirect(url_for("auth.users"))
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username=%s",(username,))
        if cur.fetchone():
            flash("User already exists.", "info")
        else:
            cur.execute("INSERT INTO users (username, password_hash, role) VALUES (%s,%s,%s)",
                        (username, generate_password_hash(password), role))
            flash("User created.", "success")
        return redirect(url_for("auth.users"))

    @bp.route("/users/<int:uid>/delete", methods=["POST"])
    @role_required("admin")
    def delete_user(uid):
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id=%s",(uid,))
        flash("User deleted.", "info")
        return redirect(url_for("auth.users"))
