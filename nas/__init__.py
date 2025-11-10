from flask import Blueprint
auth_bp    = Blueprint("auth",    __name__, template_folder="../templates/auth")
files_bp   = Blueprint("files",   __name__, template_folder="../templates/files")
monitor_bp = Blueprint("monitor", __name__, template_folder="../templates/monitor")
backup_bp  = Blueprint("backup",  __name__, template_folder="../templates/backup")
