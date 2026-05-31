# cloud_config.py
# Detects if running on cloud (SQLite) or local (MySQL)

import os

def is_cloud():
    return os.path.exists("opsassist.db") and not os.getenv("DB_HOST")

def get_db_connection():
    if is_cloud():
        import sqlite3
        from database.init_sqlite import init_db, DB_PATH
        init_db()
        return sqlite3.connect(DB_PATH, check_same_thread=False)
    else:
        from app.audit_logger import get_connection
        return get_connection()
