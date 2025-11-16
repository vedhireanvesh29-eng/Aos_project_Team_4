#!/usr/bin/env python3
"""
Database Migration Script
Adds file_permissions table and updates existing structure
Run this after updating your code to add the new features
"""

import os
import sys
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

load_dotenv()

def get_db_connection():
    """Create database connection"""
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "nas_user"),
            password=os.getenv("DB_PASS", ""),
            database=os.getenv("DB_NAME", "nas_app")
        )
    except Error as e:
        print(f"❌ Error connecting to database: {e}")
        sys.exit(1)

def run_migration():
    """Execute migration steps"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("🚀 Starting database migration...\n")
    
    try:
        # Step 1: Create file_permissions table if it doesn't exist
        print("📝 Creating file_permissions table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `file_permissions` (
              `id` int NOT NULL AUTO_INCREMENT,
              `file_id` int NOT NULL,
              `user_id` int NOT NULL,
              `can_read` tinyint(1) DEFAULT '1',
              `can_write` tinyint(1) DEFAULT '0',
              `granted_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (`id`),
              UNIQUE KEY `unique_file_user` (`file_id`, `user_id`),
              KEY `user_id` (`user_id`),
              CONSTRAINT `file_permissions_ibfk_1` FOREIGN KEY (`file_id`) 
                REFERENCES `files` (`id`) ON DELETE CASCADE,
              CONSTRAINT `file_permissions_ibfk_2` FOREIGN KEY (`user_id`) 
                REFERENCES `users` (`id`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """)
        conn.commit()
        print("✅ file_permissions table created successfully\n")
        
        # Step 2: Check if files table has owner_id column
        print("📝 Checking files table structure...")
        cursor.execute("SHOW COLUMNS FROM files LIKE 'owner_id'")
        if not cursor.fetchone():
            print("⚠️  Warning: files table doesn't have owner_id column")
            print("   Please run the full schema.sql or add it manually:")
            print("   ALTER TABLE files ADD COLUMN owner_id INT NOT NULL AFTER path;")
            print("   ALTER TABLE files ADD CONSTRAINT files_ibfk_1 FOREIGN KEY (owner_id)")
            print("   REFERENCES users(id) ON DELETE CASCADE;\n")
        else:
            print("✅ files table structure is correct\n")
        
        # Step 3: Verify tables exist
        print("📝 Verifying all required tables...")
        required_tables = ['users', 'permissions', 'files', 'file_permissions', 'backups']
        cursor.execute("SHOW TABLES")
        existing_tables = [table[0] for table in cursor.fetchall()]
        
        for table in required_tables:
            if table in existing_tables:
                print(f"   ✅ {table}")
            else:
                print(f"   ❌ {table} - MISSING!")
        
        print("\n📊 Database statistics:")
        for table in existing_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   {table}: {count} rows")
        
        print("\n✨ Migration completed successfully!")
        print("\n⚠️  Next steps:")
        print("   1. If owner_id is missing, you need to run full schema.sql")
        print("   2. Update your code files (files.py, templates, etc.)")
        print("   3. Restart your Flask application")
        print("   4. Test the new file sharing features\n")
        
    except Error as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

def backup_database():
    """Suggest backup before migration"""
    print("⚠️  IMPORTANT: Before running migration, backup your database!")
    print(f"\n   mysqldump -u {os.getenv('DB_USER')} -p {os.getenv('DB_NAME')} > backup_$(date +%Y%m%d_%H%M%S).sql\n")
    
    response = input("Have you backed up your database? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("\n❌ Please backup your database first, then run this script again.")
        sys.exit(0)

if __name__ == "__main__":
    print("=" * 60)
    print("  NAS Web Server - Database Migration Tool")
    print("=" * 60)
    print()
    
    backup_database()
    run_migration()
    
    print("=" * 60)
    print("  Migration Complete!")
    print("=" * 60)
