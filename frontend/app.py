import streamlit as st
from auth_ui import display_auth_forms, handle_logout
from recognition_ui import run_recognition 
from admin_ui import run_admin_panel 
import requests
import sys
import os
from config import config

# 检查Django后端连接
def check_backend_connection():
    """检查Django后端是否可用"""
    try:
        response = requests.get(f"{config.get_api_url()}/current_user_status/", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def show_backend_error():
    """显示后端连接错误信息"""
    st.error("🚫 无法连接到Django后端服务")
    st.markdown(f"""
    ### 解决方案：
    1. **启动Django后端：**
       - 运行 `python manage.py runserver`
    
    2. **确认后端地址：**
       - Django应运行在: {config.BACKEND_HOST}:{config.BACKEND_PORT}
       - API地址应为: {config.get_api_url()}
    
    3. **检查依赖安装：**
       - 运行 `pip install -r requirements.txt`
    """)
    
    if st.button("重新检查连接"):
        st.rerun()

# ----------- 应用入口 -----------

def main():
    # 页面配置
    st.set_page_config(
        page_title="人脸识别系统 - 前端",
        page_icon="🔒",
        layout="wide"
    )
    
    # 检查后端连接状态
    if not check_backend_connection():
        st.title("人脸识别系统")
        show_backend_error()
        return
    
    # 初始化 session_state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ''
        st.session_state.is_admin = False
        st.session_state.api_session = requests.Session() 
    if 'rerun_counter' not in st.session_state:
        st.session_state.rerun_counter = 0

    # 根据登录状态决定显示哪个主界面
    if st.session_state.logged_in:
        st.sidebar.title(f"欢迎, {st.session_state.username}")
        if st.sidebar.button("注销", key="logout_button_main"):
            handle_logout() 
            st.rerun()

        st.sidebar.markdown("---")

        if st.session_state.is_admin:
            st.sidebar.title("管理员菜单")
            admin_menu_options = ["用户管理", "审计日志"]
            admin_choice = st.sidebar.radio("选择操作", admin_menu_options, key="admin_main_menu")
            
            if admin_choice == "用户管理":
                run_admin_panel(st.session_state.username, "user_management")
            elif admin_choice == "审计日志":
                run_admin_panel(st.session_state.username, "audit")
            else:
                run_admin_panel(st.session_state.username, "audit")
        else:
            run_recognition(st.session_state.username)
    else:
        st.title("人脸识别系统")
        
        tab1, tab2 = st.tabs(["登录", "注册"])

        with tab1:
            display_auth_forms("登录")
        
        with tab2:
            display_auth_forms("注册")


if __name__ == '__main__':
    main()