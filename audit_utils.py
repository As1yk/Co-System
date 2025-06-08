import sqlite3
from datetime import datetime

DB_PATH = "users.db"

def get_db_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_audit_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        username TEXT,
        action TEXT NOT NULL,
        liveness_status TEXT,
        compare_result TEXT,
        score REAL
    );
    """)
    conn.commit()
    conn.close()


def add_audit_log(username: str,
                  action: str,
                  liveness_status: str = None,
                  compare_result: str = None,
                  score: float = None):
    """
       插入一条审计日志，timestamp 直接格式化为 'YYYY-MM-DD HH:MM:SS'。
       """
    # 1. 获取当前本地时间并格式化
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 2. 插入数据库
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO audit_logs
    (timestamp, username, action, liveness_status, compare_result, score)
    VALUES (?, ?, ?, ?, ?, ?);
    """, (ts, username, action, liveness_status, compare_result, score))
    conn.commit()
    conn.close()