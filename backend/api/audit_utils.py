# audit_utils.py

import sqlite3
from datetime import datetime
from django.conf import settings
from .db_utils import is_admin_user

# 使用Django配置的数据库路径
DB_PATH = settings.DATABASES['default']['NAME']

def get_db_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_audit_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    # 创建时包含 image_path 列
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        username TEXT NOT NULL,
        action TEXT NOT NULL,
        liveness_status TEXT,
        compare_result TEXT,
        score REAL,
        image_path TEXT
    );
    """)
    # 如果旧表缺少 image_path，则添加
    cursor.execute("PRAGMA table_info(audit_logs);")
    cols = [r[1] for r in cursor.fetchall()]
    if "image_path" not in cols:
        cursor.execute("ALTER TABLE audit_logs ADD COLUMN image_path TEXT;")
    conn.commit()
    conn.close()

def add_audit_log(username: str,
                  action: str,
                  liveness_status: str = None,
                  compare_result: str = None,
                  score: float = None,
                  image_path: str = None):
    """
    插入一条审计日志，记录可选的 image_path。
    """
    # 如果是管理员账号，不记录
    if is_admin_user(username):
        return

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO audit_logs
    (timestamp, username, action, liveness_status, compare_result, score, image_path)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (ts, username, action, liveness_status, compare_result, score, image_path))
    conn.commit()
    conn.close()


