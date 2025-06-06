# app.py

import streamlit as st
from auth_ui import show_auth
from recognition_ui import run_recognition

def main():
    # 1. 先展示侧边栏的“登录 / 注册 / 注销”，并返回当前登录状态
    logged_in, username = show_auth()

    # 2. 如果未登录，则直接在主区域提示并停止执行
    if not logged_in:
        st.title("请先注册或登录，才能使用人脸识别功能")
        return

    # 3. 已登录 → 进入人脸识别界面
    run_recognition(username)

if __name__ == "__main__":
    main()
