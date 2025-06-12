import streamlit as st
from auth_ui import display_auth_forms, handle_logout # 导入新的函数
from recognition_ui import run_recognition 
from admin_ui import run_admin_panel 
import requests

# ----------- 应用入口 -----------

def main():
    # 初始化 session_state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ''
        st.session_state.is_admin = False
        st.session_state.api_session = requests.Session() 
    if 'rerun_counter' not in st.session_state:
        st.session_state.rerun_counter = 0
    # 'auth_action' 和 'show_login_success_message' 会在 auth_ui.py 中按需设置或检查
    # 我们不再需要 auth_action 来控制 tab 的选择，因为 tabs 是固定顺序的
    # if 'auth_action' not in st.session_state: 
    #     st.session_state.auth_action = '登录'


    # 根据登录状态决定显示哪个主界面
    if st.session_state.logged_in:
        # 如果是从登录成功消息跳转过来的，show_login_success_message 应该已经是 False
        # 所以这里直接显示用户界面
        st.sidebar.title(f"欢迎, {st.session_state.username}")
        if st.sidebar.button("注销", key="logout_button_main"):
            handle_logout() 
            # handle_logout() 内部会增加 rerun_counter, 导致 rerun
            # 在 rerun 后，logged_in 会是 False，将显示下面的 else 分支
            st.rerun() # 确保在 handle_logout 后立即重新运行以反映状态
            # return # st.rerun() 会停止当前脚本执行，所以 return 不是必须的，但无害

        st.sidebar.markdown("---")

        if st.session_state.is_admin:
            st.sidebar.title("管理员菜单")
            admin_menu_options = ["用户管理", "审计日志"] # 简化示例
            admin_choice = st.sidebar.radio("选择操作", admin_menu_options, key="admin_main_menu")
            
            if admin_choice == "用户管理":
                run_admin_panel(st.session_state.username) 
            elif admin_choice == "审计日志":
                st.subheader("审计日志 (功能待实现)")
            else:
                run_admin_panel(st.session_state.username)
        else: # 普通用户
            # 普通用户登录后直接显示识别界面
            # 移除 "用户操作" 标题: st.sidebar.title("用户操作")
            run_recognition(st.session_state.username)
    else:
        # 用户未登录，显示全屏认证页面
        st.title("人脸识别系统")
        
        # st.tabs 默认会显示第一个 tab。
        # 如果需要确保注销后总是回到“登录”tab，并且 st.tabs 记住了之前的状态，
        # 我们可能需要更复杂的逻辑来重置 tabs 的状态，但这通常不直接支持。
        # 简单的 rerun 应该会让 tabs 重新初始化到其默认状态（第一个 tab）。
        tab1, tab2 = st.tabs(["登录", "注册"])

        with tab1:
            display_auth_forms("登录")
        
        with tab2:
            display_auth_forms("注册")


if __name__ == '__main__':
    # Streamlit 页面配置 (可以放在这里或 main() 的开头)
    st.set_page_config(layout="wide") # 使用宽布局可能会更好看
    main()