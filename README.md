# NAS Web Server

A Flask-based web interface for managing a Linux NAS server. It provides file management, user administration, system monitoring, and backup scheduling for data stored under `/srv/nas_data` with archives stored in `/srv/nas_backups`.

## Features

- User authentication with admin and standard user roles.
- Admin user management (create, update role/password, delete).
- File browser with upload, download, rename, delete, and folder creation.
- Ownership enforcement so users only access their own files.
- System dashboard showing CPU and disk usage plus recent syslog entries.
- Backup creation, restoration, and cron scheduling for automated backups.
- CLI helpers to initialize admin accounts and run backups manually.

## Requirements

- Python 3.10+
- MySQL or MariaDB server
- Access to `/srv/nas_data` and `/srv/nas_backups` on the host machine

## Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/<your-username>/nas-web.git
   cd nas-web
   ```

2. **Create virtual environment & install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Create database and user**
   ```bash
   mysql -u root -p -e "
   CREATE DATABASE nas_app;
   CREATE USER 'nas_user'@'localhost' IDENTIFIED BY 'StrongLocalPass!123';
   GRANT ALL PRIVILEGES ON nas_app.* TO 'nas_user'@'localhost';
   FLUSH PRIVILEGES;"
   ```

4. **Load schema**
   ```bash
   mysql -u nas_user -p nas_app < db/schema.sql
   ```

5. **Prepare environment variables**
   ```bash
   cp .env.example .env
   # edit .env to provide real credentials and secret key
   ```

6. **Create data directories**
   ```bash
   sudo mkdir -p /srv/nas_data /srv/nas_backups
   sudo chown -R $USER:$USER /srv/nas_data /srv/nas_backups
   ```

7. **Run the application**
   ```bash
   flask --app app run --host 0.0.0.0 --port 5000
   ```

## CLI Utilities

- Create or update an admin user:
  ```bash
  flask --app app create-admin <username> <password>
  ```

- Run an immediate backup:
  ```bash
  flask --app app run-backup
  ```

- Schedule a daily backup at a given time (HH:MM):
  ```bash
  flask --app app schedule-backup 02:00
  ```

## Development Notes

- Do not commit `.env` or generated backup archives (`*.tar.gz`).
- Maximum upload size defaults to 50 MB. Adjust `MAX_CONTENT_LENGTH_MB` in `.env` if needed.
- The application writes tarball archives into `/srv/nas_backups` and records metadata in the `backups` table.
- Ensure the system user running the app has permission to read `/var/log/syslog` for monitoring.

## License

MIT
