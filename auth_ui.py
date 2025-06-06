# auth_ui.py

import streamlit as st
from db_utils import init_user_table, add_user, verify_user

def show_auth():
    """
    在侧边栏展示“登录 / 注册 / 注销”窗口，并在 session_state 中维护登录状态。
    返回值： (logged_in: bool, username: str)
    """
    # 首次运行时，保证用户表已建
    init_user_table()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""

    st.sidebar.title("账号管理")

    # 根据是否已登录，显示不同的选项
    options = ["登录", "注册"]
    if st.session_state.logged_in:
        options.append("注销")

    menu = st.sidebar.selectbox("请选择操作", options)

    # —— 登录分支 ——
    if menu == "登录":
        st.sidebar.subheader("用户登录")
        input_user = st.sidebar.text_input("用户名", key="login_user")
        input_pw = st.sidebar.text_input("密码", type="password", key="login_pw")
        if st.sidebar.button("登录"):
            if verify_user(input_user, input_pw):
                st.session_state.logged_in = True
                st.session_state.username = input_user
                st.sidebar.success(f"登录成功，欢迎 {input_user}！")
            else:
                st.sidebar.error("用户名或密码错误，请重试。")

    # —— 注册分支 ——
    elif menu == "注册":
        st.sidebar.subheader("新用户注册")
        new_user = st.sidebar.text_input("用户名", key="reg_user")
        new_pw = st.sidebar.text_input("密码", type="password", key="reg_pw")
        new_pw_confirm = st.sidebar.text_input("确认密码", type="password", key="reg_pw_confirm")
        if st.sidebar.button("注册"):
            if not new_user or not new_pw:
                st.sidebar.error("用户名和密码不能为空。")
            elif new_pw != new_pw_confirm:
                st.sidebar.error("两次输入的密码不一致。")
            else:
                success = add_user(new_user, new_pw)
                if success:
                    st.sidebar.success("注册成功，请前往登录。")
                else:
                    st.sidebar.error("用户名已存在，请选择其他用户名。")

    # —— 注销分支 ——
    elif menu == "注销":
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.sidebar.info("您已注销。")

    return st.session_state.logged_in, st.session_state.username
