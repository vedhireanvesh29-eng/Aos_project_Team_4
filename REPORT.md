# Objective
Build a Linux web server for NAS management: file ops, user/role management, monitoring, backup/restore.

# Environment Setup

- **OS:** Ubuntu 22.04
- **Packages installed (with versions):**
  - python3 (3.10+)
  - mysql-server / mariadb-server
  - build-essential (for mysqlclient headers if required)
- **Project cloned path:** `/home/<user>/projects/nas-web`
- **Virtualenv activation command:** `source .venv/bin/activate`
- **pip install -r requirements.txt output (summary):** Install Flask, Flask-Login, mysql-connector-python, python-dotenv, psutil.
- **MySQL setup commands (exact commands run):**
  ```bash
  mysql -u root -p -e "
  CREATE DATABASE nas_app;
  CREATE USER 'nas_user'@'localhost' IDENTIFIED BY 'StrongLocalPass!123';
  GRANT ALL PRIVILEGES ON nas_app.* TO 'nas_user'@'localhost';
  FLUSH PRIVILEGES;"
  ```
- **Created folders /srv/nas_data, /srv/nas_backups + permissions:**
  ```bash
  sudo mkdir -p /srv/nas_data /srv/nas_backups
  sudo chown -R $USER:$USER /srv/nas_data /srv/nas_backups
  ```

# Database Initialization

- **schema.sql snippet or link:** See [`db/schema.sql`](db/schema.sql) for table definitions.
- **Commands used to load schema:** `mysql -u nas_user -p nas_app < db/schema.sql`
- **Verification:** Run `SHOW TABLES;` in MySQL client (capture screenshot during deployment).

# Application Configuration

- **.env content (without secrets) and meaning of each key:**
  - `DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME`: database connection details.
  - `DATA_ROOT`, `BACKUP_ROOT`: absolute paths for storage and archives.
  - `SECRET_KEY`: Flask session/CSRF key (generate random 32 bytes).
  - `MAX_CONTENT_LENGTH_MB`: upload limit in megabytes.
- **Why secrets are not committed:** `.env` ignored via `.gitignore`; share `.env.example` only.

# Application Structure

```
nas-web/
├── app.py
├── nas/
│   ├── __init__.py
│   ├── auth.py
│   ├── backups.py
│   ├── config.py
│   ├── db.py
│   ├── files.py
│   ├── monitoring.py
│   └── utils.py
├── templates/
│   ├── layout.html
│   ├── auth/
│   │   ├── login.html
│   │   ├── register.html
│   │   └── users.html
│   ├── files/index.html
│   ├── monitor/dashboard.html
│   └── backup/backups.html
├── static/css/app.css
├── db/schema.sql
├── requirements.txt
├── README.md
└── REPORT.md
```

- **Module overview:**
  - `app.py`: Flask app bootstrap, CSRF, blueprint registration.
  - `nas/config.py`: environment configuration loader.
  - `nas/db.py`: MySQL helper functions.
  - `nas/auth.py`: user model and authentication routes.
  - `nas/files.py`: file management routes and ownership enforcement.
  - `nas/monitoring.py`: monitoring dashboard route.
  - `nas/backups.py`: backup/restore logic and scheduling helpers.
  - `nas/utils.py`: role decorators, CLI commands, helper utilities.

# Security & Access Control

- **Password hashing approach:** `werkzeug.security.generate_password_hash` and `check_password_hash` for credentials.
- **Role-based decorators:** `nas.utils.role_required` ensures admin-only endpoints.
- **Path traversal prevention strategy:** `nas.utils.secure_path` resolves paths and ensures they remain within configured roots.
- **Upload limits and filename sanitization:** Flask `MAX_CONTENT_LENGTH` plus `werkzeug.utils.secure_filename` and 50 MB default cap.

# Features & Screens

Capture screenshots after deployment:
- **Auth:** login page, admin user list/CRUD.
- **Files:** listing with upload/rename/delete UI.
- **Monitoring:** CPU, disk usage, syslog view.
- **Backups:** list, create, restore, schedule forms.

# Backup Scheduling

- **Exact crontab line inserted:** `0 2 * * * flask --app app run-backup`
- **Where backups are stored and naming convention:** `/srv/nas_backups/YYYYmmdd_HHMM.tar.gz`
- **Restore test:** Select archive from backups UI, confirm files reappear under `/srv/nas_data`.

# Testing & Validation

- **Test matrix:** Validate admin vs. user permissions for file management, monitoring, and backups.
- **Negative tests:** Oversized upload (>50 MB) blocked by Flask; path traversal attempts rejected with 403.
- **Logs excerpt:** Use `flask run` console output or configured logging to demonstrate key events.

# Port Forwarding (If Required)

- Document router model, rules (e.g., forward 5000/80/443) and mention HTTPS/Let’s Encrypt considerations if exposed externally.

# How to Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # edit secrets
flask --app app run --host 0.0.0.0 --port 5000
```

- Expected output: Flask dev server startup logs and URL `http://127.0.0.1:5000`.

# Git & Deployment

- **Initial commit message:** `feat: initial NAS web server scaffold (auth, files, monitoring, backups)`
- **Branch/PR example:** `feat/file-quota`
- **Commands used to push to GitHub:** documented in README under setup section.

# Lessons Learned

- **What worked:** Modular blueprints simplify maintenance; CLI aids admin tasks.
- **What didn’t / trade-offs:** Lighter UI without JS; backup restore trusts tar integrity.
- **Future improvements:** HTTPS termination, Docker packaging, LDAP/SSO integration, audit logs, storage quotas.

# Appendix

- **Command history:** Keep sanitized shell history during deployment.
- **Versions:**
  - `python --version`
  - `mysql --version`
  - `pip freeze | head -n 20`
