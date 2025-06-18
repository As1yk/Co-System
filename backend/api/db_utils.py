# db_utils.py

import sqlite3
import hashlib
from django.conf import settings
import os

# 使用Django配置的数据库路径
DB_PATH = settings.DATABASES['default']['NAME']

def get_db_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_user_table():
    """
    初始化 users 表，如果不存在就创建；
    如果已存在但缺少 is_admin 列，则通过 ALTER TABLE 添加该列并设默认 0。
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. 如果表不存在，创建时就包含 is_admin 列
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_admin INTEGER NOT NULL DEFAULT 0
    );
    """)

    # 2. 检查 users 表中是否已有 is_admin 列
    cursor.execute("PRAGMA table_info(users);")
    columns = [row[1] for row in cursor.fetchall()]  # row[1] 是列名
    if "is_admin" not in columns:
        # 如果缺少 is_admin，则添加它
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0;")

    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def add_user(username: str, password: str, is_admin: bool=False) -> bool:
    """
    向 users 表插入新用户，is_admin 默认 False。
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        password_hash = hash_password(password)
        admin_flag = 1 if is_admin else 0
        cursor.execute(
            "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?);",
            (username, password_hash, admin_flag)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username: str, password: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE username = ?;", (username,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0] == hash_password(password)
    return False

def is_admin_user(username: str) -> bool:
    """
    查询指定用户名是否为管理员。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_admin FROM users WHERE username = ?;", (username,))
    row = cursor.fetchone()
    conn.close()
    return bool(row and row[0] == 1)

def delete_user_from_db(username):
    """从数据库删除用户"""
    try:
        conn = sqlite3.connect(os.path.join(BASE_DIR, 'users.db'))
        cursor = conn.cursor()
        
        # 检查用户是否存在
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        
        if not user:
            return False
        
        # 删除用户记录
        cursor.execute('DELETE FROM users WHERE username = ?', (username,))
        
        # 删除用户的人脸图片文件
        user_face_path = os.path.join(BASE_DIR, 'faces_database', f'{username}.jpg')
        if os.path.exists(user_face_path):
            os.remove(user_face_path)
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"删除用户失败: {e}")
        return False
