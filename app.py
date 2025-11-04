import os
import secrets
from flask import Flask, abort, request, session
from flask_login import LoginManager
from dotenv import load_dotenv

from nas.config import Config
from nas.db import init_app as init_db
from nas.auth import auth_bp, User
from nas.files import files_bp
from nas.monitoring import monitor_bp
from nas.backups import backups_bp
from nas.utils import register_cli_commands


load_dotenv()

app = Flask(__name__)
config = Config()
app.config.update(dict(config))
app.secret_key = app.config["SECRET_KEY"]
app.config["MAX_CONTENT_LENGTH"] = app.config.get("MAX_CONTENT_LENGTH_MB", 50) * 1024 * 1024

login_manager = LoginManager(app)
login_manager.login_view = "auth.login"


@login_manager.user_loader
def load_user(user_id: str):
    return User.get(int(user_id))


def generate_csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_hex(16)
        session["_csrf_token"] = token
    return token


@app.before_request
def csrf_protect():
    if request.method in {"POST", "PUT", "DELETE"}:
        token = session.get("_csrf_token")
        form_token = request.form.get("csrf_token")
        if not token or token != form_token:
            abort(400)


app.jinja_env.globals["csrf_token"] = generate_csrf_token


init_db(app)
app.register_blueprint(auth_bp)
app.register_blueprint(files_bp)
app.register_blueprint(monitor_bp)
app.register_blueprint(backups_bp)
register_cli_commands(app)


@app.context_processor
def inject_globals():
    return {"DATA_ROOT": app.config["DATA_ROOT"], "BACKUP_ROOT": app.config["BACKUP_ROOT"]}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
