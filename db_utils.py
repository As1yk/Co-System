# db_utils.py

import sqlite3
import hashlib

DB_PATH = "users.db"  # SQLite 数据库文件名

def get_db_connection():
    """
    获取 SQLite 连接，若数据库文件不存在会自动创建。
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

def init_user_table():
    """
    初始化 users 表，若表不存在则创建。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    """
    对明文密码进行 SHA-256 哈希，返回 64 位十六进制哈希串。
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def add_user(username: str, password: str) -> bool:
    """
    向 users 表插入新用户记录（用户名唯一）。返回 True 表示插入成功，False 表示用户名已存在等异常。
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        password_hash = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?);",
            (username, password_hash)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # 用户名冲突（已存在）
        return False
    finally:
        conn.close()

def verify_user(username: str, password: str) -> bool:
    """
    校验用户名和密码是否匹配。匹配返回 True，否则返回 False。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE username = ?;", (username,))
    row = cursor.fetchone()
    conn.close()
    if row:
        stored_hash = row[0]
        return stored_hash == hash_password(password)
    return False
