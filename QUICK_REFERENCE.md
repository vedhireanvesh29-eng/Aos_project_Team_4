# NAS Web Server - Quick Reference Guide

## 🚀 Quick Start

### For New Users
1. Get login credentials from admin
2. Login at http://localhost:5000/auth/login
3. Go to "File Manager" to upload files
4. Go to "My Files" to see your files and shared files

### For Admins
1. Login with admin credentials
2. Create users in "Users" section
3. Monitor system in "Monitor" section
4. Manage backups in "Backup" section

---

## 👤 User Operations

### Upload a File
```
1. Click "File Manager" in navigation
2. Use "Upload File" card
3. Click "Choose File"
4. Select file
5. Click "Upload"
```

### Share a File
```
1. Go to "File Manager" or "My Files"
2. Find your file
3. Click "Share" button
4. Select user from dropdown
5. Check "Can Read" and/or "Can Write"
6. Click "Grant Access"
```

### View Shared Files
```
1. Click "My Files" in navigation
2. Click "Shared with Me" filter button
3. See all files others shared with you
```

### Download a File
```
1. Find file in "File Manager" or "My Files"
2. Click "Download" button
3. File downloads to your browser
```

### Revoke Access
```
1. Go to file sharing page
2. Find user in permissions list
3. Click "Revoke" button
4. Confirm action
```

---

## 👨‍💼 Admin Operations

### Create a User
```
1. Click "Users" in navigation
2. Scroll to "Create User" form
3. Enter username
4. Enter password
5. Select role (admin/user)
6. Click "Create"
```

### Set User Permissions
```sql
-- Give full permissions to user
INSERT INTO permissions (user_id, can_read, can_write, can_edit)
VALUES (USER_ID, 1, 1, 1)
ON DUPLICATE KEY UPDATE 
  can_read=1, can_write=1, can_edit=1;
```

### Create Manual Backup
```
1. Click "Backup" in navigation
2. Click "Create Backup Now"
3. Wait for completion
4. Backup appears in list
```

### Create Daily Backup
```
1. Click "Backup" in navigation
2. Click "Create Daily Backup"
3. System creates one backup per day
4. Safe to click multiple times (won't duplicate)
```

### Restore from Backup
```
1. Click "Backup" in navigation
2. Find backup in list
3. Click "Restore" button
4. Confirm warning (safety backup created automatically)
5. Wait for completion
```

### Delete a Backup
```
1. Click "Backup" in navigation
2. Find backup in list
3. Click "Delete" button
4. Confirm deletion
```

### Access All Files
```
1. Click "My Files" in navigation
2. You see ALL files in system
3. Can download/share/delete any file
```

### Delete Any File
```
1. Find file in "File Manager" or "My Files"
2. Click "Delete" button
3. Confirm deletion
4. File removed for all users
```

---

## 🔍 Filter Files in "My Files"

| Filter Button | Shows |
|--------------|-------|
| All Files | All files you can access |
| My Files | Only files you own |
| Shared with Me | Files others shared with you |
| Read Access | Files you can read |
| Write Access | Files you can modify |

---

## 🎨 Permission Badges

| Badge | Meaning |
|-------|---------|
| 🟢 Owner | You own this file |
| 🔵 Read | You can download this file |
| 🟡 Write | You can modify this file |

---

## 🛠️ Common SQL Queries

### Check User Permissions
```sql
SELECT u.username, p.* 
FROM permissions p
JOIN users u ON p.user_id = u.id;
```

### See File Ownership
```sql
SELECT f.path, u.username as owner, f.created_at
FROM files f
JOIN users u ON f.owner_id = u.id
ORDER BY f.created_at DESC;
```

### View File Sharing
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
JOIN users u2 ON fp.user_id = u2.id;
```

### List All Backups
```sql
SELECT * FROM backups ORDER BY created_at DESC;
```

### Grant Admin Rights
```sql
UPDATE users SET role='admin' WHERE username='USERNAME';
INSERT INTO permissions (user_id, can_read, can_write, can_edit, is_admin)
VALUES (USER_ID, 1, 1, 1, 1)
ON DUPLICATE KEY UPDATE is_admin=1;
```

---

## 📁 Directory Structure

```
/srv/nas_data/          # User files
/srv/nas_backups/       # Backup archives
Aos_project_Team_4/     # Application code
  ├── app.py            # Main application
  ├── nas/              # Module directory
  │   ├── files.py      # File management
  │   ├── backup.py     # Backup system
  │   ├── auth.py       # Authentication
  │   └── monitor.py    # System monitoring
  └── templates/        # HTML templates
      ├── files/
      ├── backup/
      └── auth/
```

---

## ⚡ Keyboard Shortcuts

When browsing file manager:
- **Ctrl+F** - Focus search (browser default)
- **Alt+U** - Focus upload file input
- **Escape** - Cancel any form

---

## 🔐 Security Tips

### For Users
- ✅ Use strong, unique passwords
- ✅ Only share files when necessary
- ✅ Revoke access when no longer needed
- ✅ Log out after use on shared computers
- ❌ Don't share your login credentials

### For Admins
- ✅ Change default admin password immediately
- ✅ Create backups before major changes
- ✅ Regularly audit user permissions
- ✅ Monitor disk usage
- ✅ Keep software updated
- ❌ Don't give admin role to untrusted users
- ❌ Don't delete all backups

---

## 🆘 Quick Troubleshooting

### "Permission denied" error
→ Check your global permissions in database
→ Ask admin to grant you permissions

### Can't see uploaded file
→ Refresh page
→ Check "My Files" section
→ Verify file was uploaded successfully

### File already exists
→ Rename your file before uploading
→ Or delete the existing file first (if you own it)

### Backup failed
→ Check disk space: `df -h /srv/nas_backups`
→ Check permissions: `ls -la /srv/nas_backups`
→ Contact admin

### Can't delete file
→ You must own the file to delete it
→ Or be an admin
→ Check who owns the file in "My Files"

---

## 📞 Getting Help

1. **Check error message** - Often tells you exactly what's wrong
2. **Check permissions** - Most issues are permission-related
3. **Check logs** - Look for error details
4. **Ask admin** - For user permission issues
5. **Check documentation** - Read IMPLEMENTATION_GUIDE.md

---

## 🎯 Pro Tips

### For Efficient File Management
- Use descriptive filenames
- Organize files in folders
- Regularly clean up old files
- Use "My Files" filters to find files quickly

### For Effective Sharing
- Share with specific users, not groups
- Use read-only access when appropriate
- Document why you shared each file
- Revoke access promptly when done

### For Reliable Backups
- Create daily backups
- Download important backups externally
- Test restore process occasionally
- Keep at least 3 recent backups
- Delete very old backups to save space

---

## 📊 Status Indicators

### In File Manager
- 🟢 **Green Badge (Owner)** - You own this file
- 🔵 **Blue Badge (User)** - File owned by this user
- 🟣 **Purple Share Button** - You can share this file
- 🔴 **Red Delete Button** - You can delete this file
- 🔵 **Blue Download Button** - You can download this file

### In Backup Manager
- 🟢 **Success** - Operation completed
- 🔴 **Danger** - Critical action (delete, restore)
- 🟡 **Warning** - Caution required
- 🔵 **Info** - Information message

---

## 🎓 Learning Path

### Beginner
1. Login to system
2. Upload a test file
3. Download your file
4. View "My Files"

### Intermediate
5. Share a file with another user
6. Create a folder structure
7. Rename files/folders
8. Revoke file access

### Advanced
9. Use filters in "My Files"
10. Request admin to change permissions
11. Understand permission hierarchy

### Admin Level
12. Create user accounts
13. Manage user permissions
14. Create and restore backups
15. Monitor system resources
16. Audit file sharing

---

## 📈 Best Practices Summary

| Category | Do ✅ | Don't ❌ |
|----------|------|---------|
| **Passwords** | Use strong, unique passwords | Share your password |
| **Files** | Organize in folders | Upload sensitive data without encryption |
| **Sharing** | Share only when needed | Give write access unnecessarily |
| **Permissions** | Review regularly | Leave old permissions active |
| **Backups** | Create daily backups | Delete all backups |
| **Security** | Log out after use | Leave computer unlocked |

---

## 🔄 Workflow Examples

### Scenario 1: Collaborating on a Document
```
1. User A uploads document
2. User A shares with User B (read+write)
3. User B downloads, edits locally
4. User B uploads new version
5. User B shares back with User A
6. User A downloads updated version
```

### Scenario 2: Distributing Read-Only Files
```
1. Admin uploads company policy document
2. Admin shares with all users (read only)
3. Users can download but not modify
4. Admin can update and reshare
```

### Scenario 3: Regular Backup Routine
```
1. Monday: Create backup before weekly changes
2. Daily: Auto-backup runs automatically
3. Friday: Download weekly backup to external drive
4. Monthly: Delete backups older than 3 months
```

---

This quick reference should be printed and kept handy for all users!
