import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash
from flask_login import LoginManager, UserMixin

load_dotenv()

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST","localhost"),
        user=os.getenv("DB_USER","nas_user"),
        password=os.getenv("DB_PASS",""),
        database=os.getenv("DB_NAME","nas_app"),
        autocommit=True,
    )

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY","dev-secret-change-me")

# ---- Login manager ----
login_manager = LoginManager(app)
login_manager.login_view = "auth.login"

class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = str(id)
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT id, username, role FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
        if row: return User(row[0], row[1], row[2])
    except Exception:
        pass
    finally:
        try: cur.close(); conn.close()
        except Exception: pass
    return None

@app.route("/")
def home():
    info = {"connected": False, "tables": [], "error": None}
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SHOW TABLES;")
        info["tables"] = [r[0] for r in cur.fetchall()]
        info["connected"] = True
    except Error as e:
        info["error"] = str(e)
    finally:
        try: cur.close(); conn.close()
        except Exception: pass
    return render_template("home.html", info=info)

@app.route("/init_admin", methods=["POST"])
def init_admin():
    username, password = "admin", "admin123"
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username=%s",(username,))
        if cur.fetchone():
            flash("Admin user already exists.", "info")
        else:
            cur.execute(
              "INSERT INTO users (username, password_hash, role) VALUES (%s,%s,'admin')",
              (username, generate_password_hash(password))
            )
            flash("Admin user created: admin / admin123 (please change later).", "success")
    except Error as e:
        flash(f"MySQL error: {e}", "danger")
    finally:
        try: cur.close(); conn.close()
        except Exception: pass
    return redirect(url_for("home"))

# Blueprints
from nas.__init__ import auth_bp, files_bp, monitor_bp, backup_bp
from nas.auth import init_auth_routes
import nas.files as _files
import nas.monitor as _monitor
import nas.backup as _backup

init_auth_routes(app, auth_bp)
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(files_bp, url_prefix="/files")
app.register_blueprint(monitor_bp, url_prefix="/monitor")
app.register_blueprint(backup_bp, url_prefix="/backup")

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static','favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
