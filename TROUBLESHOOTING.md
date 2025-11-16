# NAS Web Server - Troubleshooting Guide

## 🔍 Common Issues and Solutions

### 1. "Permission denied" Errors

#### Symptom
User gets "You do not have permission for this action" message

#### Possible Causes & Solutions

**A. Missing Global Permissions**
```sql
-- Check user's global permissions
SELECT u.username, p.* 
FROM users u
LEFT JOIN permissions p ON u.id = p.user_id
WHERE u.username = 'YOUR_USERNAME';

-- If no record found, add permissions
INSERT INTO permissions (user_id, can_read, can_write, can_edit)
VALUES (USER_ID, 1, 1, 1);
```

**B. Missing File Permission**
```sql
-- Check file-level permissions
SELECT f.path, u.username, fp.can_read, fp.can_write
FROM files f
JOIN users u ON f.owner_id = u.id
LEFT JOIN file_permissions fp ON f.id = fp.file_id
WHERE fp.user_id = YOUR_USER_ID;
```

**C. Not Logged In**
- Solution: Login at `/auth/login`
- Check: Look for user icon in header

---

### 2. Files Not Showing in File Manager

#### Symptom
Directory appears empty even though files exist in filesystem

#### Diagnosis Steps

**Step 1: Check if file exists in database**
```sql
SELECT * FROM files WHERE path LIKE '%filename%';
```

**Step 2: Check file ownership**
```sql
SELECT f.path, u.username as owner
FROM files f
JOIN users u ON f.owner_id = u.id
WHERE f.path = 'path/to/file.txt';
```

**Step 3: Check if you have access**
```sql
-- For regular users
SELECT f.*, fp.can_read, fp.can_write
FROM files f
LEFT JOIN file_permissions fp ON f.id = fp.file_id
WHERE (f.owner_id = YOUR_USER_ID OR fp.user_id = YOUR_USER_ID)
AND f.path = 'path/to/file.txt';
```

#### Solutions

**A. File Not in Database**
```python
# Fix: Re-upload the file OR manually add to database
INSERT INTO files (path, owner_id)
VALUES ('path/to/file.txt', OWNER_USER_ID);
```

**B. No Permission to View**
- Ask file owner to share it with you
- Or ask admin for access

**C. Orphaned Files** (filesystem but not in DB)
```bash
# List files in filesystem
ls -la /srv/nas_data/

# Compare with database
mysql -u nas_user -p nas_app -e "SELECT path FROM files;"

# To import orphaned files (as admin)
# You'll need to manually INSERT each file
```

---

### 3. Upload Fails

#### Symptom
File upload returns error or appears to succeed but file doesn't appear

#### Common Causes

**A. No Write Permission**
```sql
SELECT * FROM permissions WHERE user_id = YOUR_USER_ID;
-- Ensure can_write = 1
```

**B. File Already Exists**
- Error: "File 'filename.txt' already exists"
- Solution: Rename file or delete existing one

**C. Filesystem Permission Issue**
```bash
# Check directory permissions
ls -ld /srv/nas_data
# Should show: drwxr-xr-x

# Fix permissions
sudo chown -R $USER:$USER /srv/nas_data
chmod 755 /srv/nas_data
```

**D. Disk Full**
```bash
# Check disk space
df -h /srv/nas_data

# If full, delete old files or expand disk
```

**E. File Too Large**
```python
# Check Flask config (in app.py)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB default

# To increase limit:
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
```

---

### 4. Cannot Delete File

#### Symptom
"You don't have permission to delete this file"

#### Diagnosis

**Check Ownership**
```sql
SELECT f.path, f.owner_id, u.username as owner
FROM files f
JOIN users u ON f.owner_id = u.id
WHERE f.path = 'path/to/file.txt';
```

#### Solutions

**A. You're Not the Owner**
- Only file owners can delete files
- Exception: Admins can delete any file
- Solution: Ask owner to delete OR ask admin for help

**B. You Need to be Admin**
```sql
-- Check if you're admin
SELECT role FROM users WHERE id = YOUR_USER_ID;

-- If not, ask admin to grant you admin role:
UPDATE users SET role='admin' WHERE id = YOUR_USER_ID;
```

---

### 5. Sharing Not Working

#### Symptom
Shared file doesn't appear for other user

#### Diagnosis Steps

**Step 1: Verify share was created**
```sql
SELECT * FROM file_permissions 
WHERE file_id = FILE_ID AND user_id = SHARED_USER_ID;
```

**Step 2: Check permissions are correct**
```sql
SELECT 
    f.path,
    u1.username as owner,
    u2.username as shared_with,
    fp.can_read,
    fp.can_write
FROM file_permissions fp
JOIN files f ON fp.file_id = f.id
JOIN users u1 ON f.owner_id = u1.id
JOIN users u2 ON fp.user_id = u2.id
WHERE f.id = FILE_ID;
```

#### Solutions

**A. Share Not Created**
- Re-share the file
- Check for errors in flash messages

**B. Can't See Shared File**
- User needs to go to "My Files"
- Click "Shared with Me" filter
- File should appear there

**C. Wrong User Selected**
- Delete the permission:
```sql
DELETE FROM file_permissions 
WHERE file_id = FILE_ID AND user_id = WRONG_USER_ID;
```
- Re-share with correct user

---

### 6. Backup Issues

#### Symptom: Backup Creation Fails

**A. Disk Space Full**
```bash
df -h /srv/nas_backups
# If at 100%, delete old backups or expand disk
```

**B. Permission Denied**
```bash
# Check directory permissions
ls -ld /srv/nas_backups

# Fix permissions
sudo chown -R $USER:$USER /srv/nas_backups
chmod 755 /srv/nas_backups
```

**C. Not Admin**
- Only admins can create backups
- Check: `SELECT role FROM users WHERE id = YOUR_USER_ID;`

#### Symptom: Cannot Download Backup

**A. File Not Found**
```bash
# Check if backup file exists
ls -lh /srv/nas_backups/*.tar.gz
```

**B. Database/Filesystem Mismatch**
```sql
-- Check database records
SELECT * FROM backups;

-- Compare with filesystem
-- If mismatch, clean up:
DELETE FROM backups WHERE archive_path = 'missing_file.tar.gz';
```

#### Symptom: Restore Fails

**A. Corrupted Archive**
```bash
# Test archive integrity
tar -tzf /srv/nas_backups/backup_file.tar.gz

# If corrupted, use a different backup
```

**B. Insufficient Space**
```bash
# Check available space
df -h /srv/nas_data

# Archive will extract to same size as original
```

---

### 7. Login Issues

#### Symptom: Cannot Login

**A. Wrong Credentials**
- Verify username and password
- Check caps lock is off
- Try different browser

**B. User Doesn't Exist**
```sql
SELECT username FROM users;
-- If your username not in list, ask admin to create account
```

**C. Password Hash Mismatch**
```sql
-- Check password hash
SELECT username, password_hash FROM users WHERE username = 'YOUR_USERNAME';

-- To reset password (as admin):
UPDATE users 
SET password_hash = 'NEW_HASH'  -- Use generate_password_hash('new_password')
WHERE username = 'USERNAME';
```

#### Symptom: Session Expires Immediately

**A. SECRET_KEY Not Set**
```bash
# Check .env file
cat .env | grep SECRET_KEY

# Should have:
SECRET_KEY=your-secret-key-here

# If missing, add it and restart app
```

**B. Cookie Issues**
- Clear browser cookies
- Try incognito/private mode
- Check browser console for errors

---

### 8. Database Connection Errors

#### Symptom
"MySQL Connection Failed" or similar errors

#### Solutions

**A. MySQL Not Running**
```bash
# Check MySQL status
sudo systemctl status mysql

# Start if stopped
sudo systemctl start mysql
```

**B. Wrong Credentials in .env**
```bash
# Check .env file
cat .env

# Verify:
DB_HOST=localhost
DB_USER=nas_user
DB_PASS=your_password
DB_NAME=nas_app

# Test connection manually:
mysql -h localhost -u nas_user -p nas_app
```

**C. Database Doesn't Exist**
```bash
# List databases
mysql -u root -p -e "SHOW DATABASES;"

# Create if missing:
mysql -u root -p -e "CREATE DATABASE nas_app;"
```

**D. User Doesn't Have Permissions**
```sql
-- As MySQL root user:
GRANT ALL PRIVILEGES ON nas_app.* TO 'nas_user'@'localhost';
FLUSH PRIVILEGES;
```

---

### 9. "My Files" Page Empty

#### Symptom
"My Files" page shows "No Files Found" even though you have files

#### Diagnosis

**Check if you own any files**
```sql
SELECT * FROM files WHERE owner_id = YOUR_USER_ID;
```

**Check if any files are shared with you**
```sql
SELECT f.*, fp.can_read, fp.can_write
FROM files f
JOIN file_permissions fp ON f.id = fp.file_id
WHERE fp.user_id = YOUR_USER_ID;
```

#### Solutions

**A. No Files Uploaded**
- Go to "File Manager" and upload some files

**B. Files Not in Database**
- Files exist in filesystem but not recorded
- Re-upload them OR manually insert records

**C. Wrong User ID**
- Logout and login again
- Check: `SELECT id, username FROM users WHERE username = 'YOUR_USERNAME';`

---

### 10. Performance Issues

#### Symptom: Slow Page Loads

**A. Too Many Files**
```sql
-- Check number of files
SELECT COUNT(*) FROM files;

-- If > 10,000 files, consider:
-- 1. Pagination
-- 2. Archiving old files
-- 3. Database indexing
```

**B. Large Database**
```bash
# Check database size
mysql -u nas_user -p nas_app -e "
SELECT 
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS Size_MB
FROM information_schema.TABLES
WHERE table_schema = 'nas_app';
"
```

**C. Too Many Permissions**
```sql
-- Check permissions count
SELECT COUNT(*) FROM file_permissions;

-- If very high, clean up unused permissions
DELETE fp FROM file_permissions fp
LEFT JOIN files f ON fp.file_id = f.id
WHERE f.id IS NULL;  -- Removes orphaned permissions
```

---

### 11. UI Issues

#### Symptom: Styles Not Loading

**A. CSS Not Applied**
- Hard refresh: Ctrl+F5 (Ctrl+Shift+R on Mac)
- Clear browser cache
- Check browser console for 404 errors

**B. Icons Not Showing**
- Font Awesome CDN might be down
- Check internet connection
- Try different browser

#### Symptom: Buttons Not Working

**A. JavaScript Errors**
- Open browser developer console (F12)
- Check for errors in Console tab
- Common issues:
  - Confirm dialogs being blocked
  - Form validation errors

---

## 🔧 Diagnostic Commands

### Quick System Check
```bash
# Run all these commands to get system status

# 1. Check if Flask app is running
ps aux | grep python

# 2. Check MySQL
sudo systemctl status mysql

# 3. Check disk space
df -h

# 4. Check file permissions
ls -la /srv/nas_data
ls -la /srv/nas_backups

# 5. Check database connectivity
mysql -u nas_user -p nas_app -e "SELECT 1;"

# 6. Check for Python errors
# (if running as service)
sudo journalctl -u nas-server -n 50
```

### Database Health Check
```sql
-- Run in MySQL

-- 1. Count records in each table
SELECT 'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'files', COUNT(*) FROM files
UNION ALL
SELECT 'permissions', COUNT(*) FROM permissions
UNION ALL
SELECT 'file_permissions', COUNT(*) FROM file_permissions
UNION ALL
SELECT 'backups', COUNT(*) FROM backups;

-- 2. Check for orphaned records
SELECT 'Orphaned file_permissions' as issue, COUNT(*) as count
FROM file_permissions fp
LEFT JOIN files f ON fp.file_id = f.id
WHERE f.id IS NULL
UNION ALL
SELECT 'Orphaned files', COUNT(*)
FROM files f
LEFT JOIN users u ON f.owner_id = u.id
WHERE u.id IS NULL;

-- 3. Check for users without permissions
SELECT u.id, u.username
FROM users u
LEFT JOIN permissions p ON u.id = p.user_id
WHERE p.user_id IS NULL AND u.role != 'admin';
```

---

## 🆘 Emergency Recovery

### If Everything Is Broken

**Step 1: Backup Current State**
```bash
# Backup database
mysqldump -u nas_user -p nas_app > emergency_backup_$(date +%Y%m%d_%H%M%S).sql

# Backup files
cp -r /srv/nas_data /srv/nas_data_emergency_$(date +%Y%m%d_%H%M%S)
```

**Step 2: Reset Database**
```bash
# Drop and recreate database
mysql -u root -p -e "DROP DATABASE nas_app;"
mysql -u root -p -e "CREATE DATABASE nas_app;"

# Reimport schema
mysql -u nas_user -p nas_app < schema.sql

# Restore from backup (if have one)
mysql -u nas_user -p nas_app < emergency_backup_XXXXXX.sql
```

**Step 3: Reset File Permissions**
```bash
# Fix all file permissions
sudo chown -R $USER:$USER /srv/nas_data /srv/nas_backups
chmod -R 755 /srv/nas_data /srv/nas_backups
```

**Step 4: Restart Application**
```bash
# If using systemd
sudo systemctl restart nas-server

# If running directly
pkill -f "python app.py"
python app.py
```

---

## 📝 Logging and Debugging

### Enable Debug Mode
```python
# In app.py, change:
app.run(host="0.0.0.0", port=5000, debug=True)

# This will show detailed error messages in browser
# WARNING: Only use in development!
```

### Check Application Logs
```bash
# If running directly, errors appear in terminal

# If using systemd:
sudo journalctl -u nas-server -f  # Follow logs in real-time
sudo journalctl -u nas-server -n 100  # Last 100 lines
```

### MySQL Query Logging
```sql
-- Enable general log
SET GLOBAL general_log = 'ON';
SET GLOBAL general_log_file = '/var/log/mysql/general.log';

-- View recent queries
SHOW VARIABLES LIKE 'general_log%';

-- Disable when done (performance impact)
SET GLOBAL general_log = 'OFF';
```

---

## 📞 Getting More Help

### Information to Collect Before Asking for Help

1. **Error Message** - Exact text of error
2. **Steps to Reproduce** - What you did before error
3. **User Role** - Admin or regular user?
4. **Browser** - Chrome, Firefox, Safari?
5. **System Info**:
   ```bash
   python --version
   mysql --version
   cat /etc/os-release
   ```
6. **Relevant Logs**:
   ```bash
   # Last 20 lines of application log
   sudo journalctl -u nas-server -n 20
   ```

### Useful SQL Queries for Support

```sql
-- User information
SELECT id, username, role, created_at FROM users;

-- File ownership summary
SELECT u.username, COUNT(f.id) as file_count
FROM users u
LEFT JOIN files f ON u.id = f.owner_id
GROUP BY u.id;

-- Permission summary
SELECT u.username, p.*
FROM users u
LEFT JOIN permissions p ON u.id = p.user_id;

-- Sharing statistics
SELECT f.path, COUNT(fp.user_id) as shared_with_count
FROM files f
LEFT JOIN file_permissions fp ON f.id = fp.file_id
GROUP BY f.id
HAVING shared_with_count > 0;
```

---

## ✅ Prevention Best Practices

1. **Regular Backups**
   - Create daily backups
   - Download backups to external storage
   - Test restore process monthly

2. **Monitor Disk Space**
   ```bash
   # Add to crontab for daily check
   0 9 * * * df -h | mail -s "Disk Space Report" admin@example.com
   ```

3. **Regular Database Maintenance**
   ```sql
   -- Run weekly
   OPTIMIZE TABLE files;
   OPTIMIZE TABLE file_permissions;
   ```

4. **Update Regularly**
   ```bash
   # Update Python packages
   pip install --upgrade -r requirements.txt
   
   # Update system packages
   sudo apt update && sudo apt upgrade
   ```

5. **Monitor Logs**
   ```bash
   # Check for errors daily
   sudo journalctl -u nas-server --since "24 hours ago" | grep -i error
   ```

---

With this troubleshooting guide, you should be able to solve 95% of common issues!
