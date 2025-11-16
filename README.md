# NAS Web Server - Advanced Operating Systems Project

A full-featured Network Attached Storage (NAS) web interface built with Flask, featuring file management, user permissions, system monitoring, and backup capabilities.

##  Features

### Implemented Features

- **File Management**
  - Upload, download, delete files
  - Create, rename, delete folders
  - File ownership tracking
  - Granular file-level permissions
  - Share files with specific users (read/write access)

- **User Management**
  - Create, modify, delete user accounts
  - Role-based access control (Admin/User)
  - Global permissions (can_read, can_write, can_edit)
  - Per-file permission sharing

- **System Monitoring**
  - Real-time CPU usage
  - Memory usage statistics
  - Disk space monitoring
  - Top processes display
  - System load averages

- **Backup & Restore**
  - Create full system backups (.tar.gz)
  - Download backup archives
  - Restore from backups
  - Admin-only access

- **Security**
  - Password hashing (Werkzeug)
  - Session management (Flask-Login)
  - Role-based route protection
  - Permission-based file access
  - Admin can manage all files and users

###  Modern UI

- Beautiful gradient design
- Responsive layout (mobile-friendly)
- Icon-based navigation (Font Awesome)
- Smooth animations and transitions
- Card-based interface
- Color-coded flash messages

##  Requirements

- Python 3.8+
- MySQL 8.0+
- Linux server (Ubuntu 20.04+ recommended)

##  Installation

### 1. Clone the Repository

```bash
git clone <https://github.com/vedhireanvesh29-eng/Aos_project_Team_4>
cd Aos_project_Team_4
```

### 2. Install Python Dependencies

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 3. Setup MySQL Database

```bash
# Login to MySQL
sudo mysql -u root -p

# Create database and user
CREATE DATABASE nas_app;
CREATE USER 'nas_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON nas_app.* TO 'nas_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# Import schema
mysql -u nas_user -p nas_app < schema.sql
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Database Configuration
DB_HOST=localhost
DB_USER=nas_user
DB_PASS=your_secure_password
DB_NAME=nas_app

# Flask Configuration
SECRET_KEY=your-very-secret-key-change-this

# Storage Paths
DATA_ROOT=/srv/nas_data
BACKUP_ROOT=/srv/nas_backups
```

### 5. Create Storage Directories

```bash
sudo mkdir -p /srv/nas_data
sudo mkdir -p /srv/nas_backups
sudo chown -R $USER:$USER /srv/nas_data /srv/nas_backups
chmod 755 /srv/nas_data /srv/nas_backups
```

### 6. Run the Application

```bash
python app.py
```

The server will start on `http://0.0.0.0:5000`

##  Default Admin Credentials

On first run, visit the dashboard and click "Create Admin User":
- **Username:** admin
- **Password:** admin123

⚠️*IMPORTANT:** Change this password immediately after first login!

##  User Permissions System

### Two-Level Permission System

1. **Global Permissions** (System-wide)
   - `can_read`: Can browse and download files
   - `can_write`: Can upload files
   - `can_edit`: Can rename/delete files
   - `is_admin`: Full system access

2. **File-Level Permissions** (Per-file sharing)
   - File owners can share their files with specific users
   - Grant read or write access individually
   - Admins have access to all files

### Permission Hierarchy

```
Admin Role
  └─ Full access to everything
     ├─ Manage all users
     ├─ Access all files
     ├─ Share any file
     ├─ Create backups
     └─ System monitoring

User Role + File Ownership
  └─ Owner of uploaded files
     ├─ Full control over own files
     ├─ Share with specific users
     └─ Grant read/write permissions

User Role + Shared Access
  └─ Access to shared files only
     ├─ Read (if granted)
     └─ Write (if granted)
```

##  Project Structure

```
Aos_project_Team_4/
├── app.py                 # Main Flask application
├── nas/
│   ├── __init__.py       # Blueprint initialization
│   ├── auth.py           # Authentication routes
│   ├── files.py          # File management (ENHANCED)
│   ├── monitor.py        # System monitoring
│   ├── backup.py         # Backup/restore
│   ├── permissions.py    # Permission helpers
│   ├── roles.py          # Role-based decorators
│   └── utils.py          # Utility functions
├── templates/
│   ├── base.html         # Base template (ENHANCED UI)
│   ├── home.html         # Dashboard (ENHANCED)
│   ├── auth/
│   │   ├── login.html
│   │   └── users.html
│   ├── files/
│   │   ├── index.html    # File manager (ENHANCED)
│   │   └── share.html    # File sharing (NEW)
│   ├── monitor/
│   │   └── index.html
│   └── backup/
│       └── index.html
├── static/
│   └── favicon.ico
├── schema.sql            # Database schema (UPDATED)
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

##  Key Updates Made

### 1. Enhanced File Management (`nas/files.py`)
- Added file ownership tracking
- Implemented per-file permission system
- Created file sharing functionality
- Admin can access/manage all files

### 2. Updated Database Schema (`schema.sql`)
- Added `file_permissions` table
- Enhanced `files` table with ownership
- Proper foreign key relationships

### 3. Modern UI (`templates/base.html`)
- Beautiful gradient backgrounds
- Responsive card-based layout
- Icon integration (Font Awesome)
- Smooth animations

### 4. File Sharing Interface (`templates/files/share.html`)
- Grant read/write access to users
- Revoke permissions
- Visual permission badges

### 5. Enhanced Dashboard (`templates/home.html`)
- Quick stats cards
- System status indicators
- Quick action buttons

##  Port Forwarding (For Remote Access)

To access your NAS from outside your local network:

1. **Find Your Router's IP:**
   ```bash
   ip route | grep default
   ```

2. **Configure Port Forwarding in Router:**
   - External Port: 8080 (or your choice)
   - Internal Port: 5000
   - Internal IP: Your server's local IP
   - Protocol: TCP

3. **Update Firewall:**
   ```bash
   sudo ufw allow 5000/tcp
   sudo ufw enable
   ```

4. **Access Remotely:**
   ```
   http://your-public-ip:8080
   ```

⚠️ **Security Note:** Use HTTPS in production! Consider using Nginx with SSL certificates.

##  Security Best Practices

1. **Change Default Credentials**
   - Change admin password immediately
   - Use strong, unique passwords

2. **Use HTTPS**
   - Set up SSL/TLS certificates
   - Use Let's Encrypt for free certificates

3. **Firewall Configuration**
   ```bash
   sudo ufw allow 22/tcp    # SSH
   sudo ufw allow 80/tcp    # HTTP
   sudo ufw allow 443/tcp   # HTTPS
   sudo ufw enable
   ```

4. **Regular Backups**
   - Schedule automatic backups
   - Store backups in separate location

5. **Keep Software Updated**
   ```bash
   pip install --upgrade -r requirements.txt
   sudo apt update && sudo apt upgrade
   ```

##  Troubleshooting

### Database Connection Error
```bash
# Check MySQL status
sudo systemctl status mysql

# Verify credentials
mysql -u nas_user -p nas_app
```

### Permission Denied Errors
```bash
# Fix storage directory permissions
sudo chown -R $USER:$USER /srv/nas_data /srv/nas_backups
chmod -R 755 /srv/nas_data /srv/nas_backups
```

### Port Already in Use
```bash
# Find process using port 5000
sudo lsof -i :5000

# Kill the process (use the PID from above)
kill -9 <PID>
```

## 📝 Usage Guide

### For Admins

1. **Manage Users:** Navigate to Users section
2. **Create User:** Provide username, password, and role
3. **Set Global Permissions:** Edit permissions table directly in MySQL
4. **Access All Files:** Browse and manage any user's files
5. **Create Backups:** Use Backup section for system backups

### For Regular Users

1. **Upload Files:** Go to Files section, use upload form
2. **Share Files:** Click "Share" button on your files
3. **Grant Access:** Select user and choose read/write permissions
4. **Download Files:** Click download on any accessible file
5. **Manage Your Files:** Rename, delete, or organize your uploads


Built by Team 4 for AOS Project 2
