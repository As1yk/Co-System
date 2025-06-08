import streamlit as st
from auth_ui import show_auth
from recognition_ui import run_recognition, run_admin

# ----------- 应用入口 -----------

def main():
    logged_in, username, is_admin = show_auth()
    if not logged_in:
        st.title('请登录以继续')
        return
    # 登录后
    if is_admin:
        run_admin(username)
    else:
        run_recognition(username)

if __name__ == '__main__':
    main()