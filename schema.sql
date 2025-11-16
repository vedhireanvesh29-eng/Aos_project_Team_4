-- Enhanced NAS Database Schema with File Ownership & Permissions

-- Users table
DROP TABLE IF EXISTS `file_permissions`;
DROP TABLE IF EXISTS `permissions`;
DROP TABLE IF EXISTS `backups`;
DROP TABLE IF EXISTS `files`;
DROP TABLE IF EXISTS `users`;

CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(64) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` enum('admin','user') NOT NULL DEFAULT 'user',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Global permissions table (for system-wide permissions)
CREATE TABLE `permissions` (
  `user_id` int NOT NULL,
  `can_read` tinyint(1) DEFAULT '1',
  `can_write` tinyint(1) DEFAULT '0',
  `can_edit` tinyint(1) DEFAULT '0',
  `is_admin` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`user_id`),
  CONSTRAINT `permissions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Files table with ownership tracking
CREATE TABLE `files` (
  `id` int NOT NULL AUTO_INCREMENT,
  `path` text NOT NULL,
  `owner_id` int NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `owner_id` (`owner_id`),
  CONSTRAINT `files_ibfk_1` FOREIGN KEY (`owner_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- File-level permissions (user can share files with specific users)
CREATE TABLE `file_permissions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `file_id` int NOT NULL,
  `user_id` int NOT NULL,
  `can_read` tinyint(1) DEFAULT '1',
  `can_write` tinyint(1) DEFAULT '0',
  `granted_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_file_user` (`file_id`, `user_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `file_permissions_ibfk_1` FOREIGN KEY (`file_id`) REFERENCES `files` (`id`) ON DELETE CASCADE,
  CONSTRAINT `file_permissions_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Backups table
CREATE TABLE `backups` (
  `id` int NOT NULL AUTO_INCREMENT,
  `archive_path` text NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Insert default admin user (password: admin123)
-- NOTE: Change this password immediately after first login!
INSERT INTO users (username, password_hash, role) VALUES 
('admin', 'scrypt:32768:8:1$lEaXqGp3j8KNZn3l$290a1c5c71e7e34fcceea7f7d7a8e7b6d9a4b4f6c1e1a0e1d9f1b6e7a2b1c0d8e5f6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9', 'admin');

-- Grant admin full permissions
INSERT INTO permissions (user_id, can_read, can_write, can_edit, is_admin) VALUES 
(1, 1, 1, 1, 1);
