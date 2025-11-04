import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


def _get_env(name: str, default=None):
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass
class Config:
    db_host: str = _get_env("DB_HOST", "localhost")
    db_user: str = _get_env("DB_USER", "nas_user")
    db_pass: str = _get_env("DB_PASS", "")
    db_name: str = _get_env("DB_NAME", "nas_app")
    data_root: str = _get_env("DATA_ROOT", "/srv/nas_data")
    backup_root: str = _get_env("BACKUP_ROOT", "/srv/nas_backups")
    secret_key: str = _get_env("SECRET_KEY", "change-me")
    max_content_length_mb: int = int(_get_env("MAX_CONTENT_LENGTH_MB", "50"))

    def __iter__(self):
        return iter({
            "DB_HOST": self.db_host,
            "DB_USER": self.db_user,
            "DB_PASS": self.db_pass,
            "DB_NAME": self.db_name,
            "DATA_ROOT": self.data_root,
            "BACKUP_ROOT": self.backup_root,
            "SECRET_KEY": self.secret_key,
            "MAX_CONTENT_LENGTH_MB": self.max_content_length_mb,
        }.items())

    def __getitem__(self, item):
        return dict(self)[item]
