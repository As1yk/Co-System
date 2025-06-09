# admin_ui.py

import streamlit as st
import sqlite3
import os

DB_PATH = "users.db"

def get_alert_logs(limit: int = 10):
    """
    获取告警日志（普通用户），不含管理员自己。
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"""
      SELECT timestamp, username, action,
             liveness_status, compare_result, score, image_path
      FROM audit_logs
      WHERE image_path IS NOT NULL
        AND username NOT IN (
            SELECT username FROM users WHERE is_admin = 1
        )
      ORDER BY id DESC
      LIMIT {limit};
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def run_admin_panel(username: str):
    st.title("🛠 管理员面板")
    st.write(f"当前管理员：**{username}**")

    st.subheader("⚠️ 验证失败记录")
    alert_rows = get_alert_logs(10)
    if alert_rows:
        for ts, user, action, live_st, cmp_res, score, img_path in alert_rows:
            st.markdown(f"**[{ts}]**  \n"
                        f"- 用户：{user}   \n"
                        f"- 操作：{action}   \n"
                        f"- 活体状态：{live_st}  \n"
                        f"- 比对结果：{cmp_res or ''}  \n"
                        f"- 得分：{score:.2f}")
            if img_path and os.path.isfile(img_path):
                st.image(img_path, width=128)
            else:
                st.write("_无对应图片_")
            st.markdown("---")
    else:
        st.info("暂无带失败人脸图的告警。")

    # 全部审计日志（示例：只展示前 50 条）
    limit = 50
    st.subheader("📜 全部审计日志")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"""
      SELECT timestamp, username, action,
             liveness_status, compare_result, score, image_path
      FROM audit_logs
      WHERE username NOT IN (
          SELECT username FROM users WHERE is_admin = 1
      )
      ORDER BY id DESC
      LIMIT {limit};
    """)
    all_rows = cursor.fetchall()
    conn.close()

    if all_rows:
        st.table([
            {
                "时间":    r[0],
                "用户":    r[1],
                "操作":    r[2],
                "活体状态": r[3],
                "比对结果": r[4] or "",
                "得分":    f"{r[5]:.2f}" if r[5] is not None else "",
            }
            for r in all_rows
        ])
    else:
        st.info("暂无审计日志。")
