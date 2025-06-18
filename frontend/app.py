import streamlit as st
import requests
from config import Config
import auth_ui
from admin_ui import run_admin_panel
import recognition_ui

config = Config()

# 创建持久的requests session
if 'requests_session' not in st.session_state:
    st.session_state.requests_session = requests.Session()

def check_login_status():
    """检查用户登录状态"""
    try:
        response = st.session_state.requests_session.get(f"{config.DJANGO_API_URL}/current_user_status/")
        if response.status_code == 200:
            data = response.json()
            if data.get('authenticated'):
                st.session_state.authenticated = True
                st.session_state.username = data.get('username', '')
                st.session_state.is_admin = data.get('is_admin', False)
            else:
                st.session_state.authenticated = False
                st.session_state.username = ""
                st.session_state.is_admin = False
    except Exception as e:
        st.error(f"检查登录状态失败: {str(e)}")

def show_auth_interface():
    """显示认证界面（登录/注册）"""
    st.title("👤 人脸识别系统")
    
    tab1, tab2 = st.tabs(["🔐 登录", "📝 注册"])
    
    with tab1:
        # 使用auth_ui模块中的登录功能
        if hasattr(auth_ui, 'show_login_form'):
            auth_ui.show_login_form()
        elif hasattr(auth_ui, 'show_login_interface'):
            auth_ui.show_login_interface()
        else:
            # 如果没有找到对应函数，显示简单的登录表单
            show_simple_login_form()
    
    with tab2:
        # 使用auth_ui模块中的注册功能
        if hasattr(auth_ui, 'show_register_form'):
            auth_ui.show_register_form()
        elif hasattr(auth_ui, 'show_register_interface'):
            auth_ui.show_register_interface()
        else:
            # 如果没有找到对应函数，显示简单的注册表单
            show_simple_register_form()

def show_simple_login_form():
    """简单的登录表单"""
    st.subheader("🔐 用户登录")
    
    with st.form("login_form"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        login_btn = st.form_submit_button("登录", type="primary")
        
        if login_btn:
            if username and password:
                try:
                    response = st.session_state.requests_session.post(
                        f"{config.DJANGO_API_URL}/login/",
                        json={'username': username, 'password': password},
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('status') == 'success':
                            st.session_state.authenticated = True
                            st.session_state.username = result.get('username')
                            st.session_state.is_admin = result.get('is_admin', False)
                            st.success("登录成功！")
                            st.rerun()
                        else:
                            st.error(f"登录失败: {result.get('message')}")
                    else:
                        st.error("服务器连接失败")
                except Exception as e:
                    st.error(f"登录异常: {str(e)}")
            else:
                st.error("请填写用户名和密码")

def show_simple_register_form():
    """简单的注册表单"""
    st.subheader("📝 用户注册")
    
    # 初始化注册步骤状态
    if 'register_step' not in st.session_state:
        st.session_state.register_step = 1
    if 'register_username' not in st.session_state:
        st.session_state.register_username = ""
    if 'register_password' not in st.session_state:
        st.session_state.register_password = ""
    if 'register_photo_method' not in st.session_state:
        st.session_state.register_photo_method = "📁 上传照片文件"
    
    # 步骤1：输入用户信息
    if st.session_state.register_step == 1:
        with st.form("user_info_form"):
            username = st.text_input("用户名", value=st.session_state.register_username)
            password = st.text_input("密码", type="password", value=st.session_state.register_password)
            confirm_password = st.text_input("确认密码", type="password")
            
            next_btn = st.form_submit_button("下一步：选择照片获取方式", type="primary")
            
            if next_btn:
                if not username or not password or not confirm_password:
                    st.error("请填写完整的用户信息")
                elif password != confirm_password:
                    st.error("两次输入的密码不一致")
                else:
                    # 保存用户信息并进入下一步
                    st.session_state.register_username = username
                    st.session_state.register_password = password
                    st.session_state.register_step = 2
                    st.rerun()
    
    # 步骤2：选择照片获取方式并拍照/上传
    elif st.session_state.register_step == 2:
        st.write(f"**用户名**: {st.session_state.register_username}")
        st.write("---")
        
        # 照片获取方式选择
        st.write("**身份照片获取方式：**")
        photo_method = st.radio(
            "选择获取方式：",
            ["📁 上传照片文件", "📷 实时拍照"],
            index=0 if st.session_state.register_photo_method == "📁 上传照片文件" else 1,
            key="photo_method_step2"
        )
        
        # 更新选择的方式
        st.session_state.register_photo_method = photo_method
        
        # 根据选择显示不同的照片获取界面
        photo_file = None
        
        if photo_method == "📁 上传照片文件":
            photo_file = st.file_uploader("上传身份照片", type=['jpg', 'jpeg', 'png'])
            if photo_file:
                st.image(photo_file, caption="上传的照片", width=150)
        else:  # 实时拍照
            st.write("**📷 拍摄身份照片**")
            # 使用列布局来控制拍照界面的大小
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                photo_file = st.camera_input("请拍摄您的身份照片")
                if photo_file:
                    st.image(photo_file, caption="拍摄的照片", width=200)
        
        # 操作按钮
        col_back, col_register = st.columns(2)
        
        with col_back:
            if st.button("⬅️ 返回修改信息"):
                st.session_state.register_step = 1
                st.rerun()
        
        with col_register:
            if st.button("✅ 完成注册", type="primary", disabled=(photo_file is None)):
                if photo_file is None:
                    st.error("请先完成照片获取")
                else:
                    # 执行注册
                    try:
                        data = {
                            'username': st.session_state.register_username,
                            'password': st.session_state.register_password
                        }
                        files = {'identity_photo': photo_file}
                        
                        response = st.session_state.requests_session.post(
                            f"{config.DJANGO_API_URL}/register/",
                            data=data,
                            files=files
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            if result.get('status') == 'success':
                                st.success("✅ 注册成功！请登录")
                                # 重置注册状态
                                st.session_state.register_step = 1
                                st.session_state.register_username = ""
                                st.session_state.register_password = ""
                                st.session_state.register_photo_method = "📁 上传照片文件"
                            else:
                                st.error(f"❌ 注册失败: {result.get('message')}")
                        else:
                            st.error("❌ 服务器连接失败")
                    except Exception as e:
                        st.error(f"❌ 注册异常: {str(e)}")

def main():
    """主应用函数"""
    st.set_page_config(
        page_title="人脸识别系统",
        page_icon="👤",
        layout="wide"
    )
    
    # 初始化会话状态
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = ""
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    if 'admin_menu_selection' not in st.session_state:
        st.session_state.admin_menu_selection = "用户管理"
    
    # 检查登录状态
    check_login_status()
    
    if not st.session_state.authenticated:
        # 未登录，显示登录/注册界面
        show_auth_interface()
    else:
        # 已登录，根据用户类型显示不同界面
        if st.session_state.is_admin:
            show_admin_interface()
        else:
            show_user_interface()

def show_admin_interface():
    """显示管理员界面"""
    st.sidebar.title("🔧 管理员控制台")
    st.sidebar.write(f"欢迎，管理员 **{st.session_state.username}**")
    
    # 管理员菜单选择
    menu_options = ["用户管理", "审计日志"]
    selected_menu = st.sidebar.selectbox(
        "选择管理功能：",
        menu_options,
        index=menu_options.index(st.session_state.admin_menu_selection) if st.session_state.admin_menu_selection in menu_options else 0,
        key="admin_menu_selectbox"
    )
    
    # 更新会话状态中的菜单选择
    if selected_menu != st.session_state.admin_menu_selection:
        st.session_state.admin_menu_selection = selected_menu
    
    # 登出按钮
    if st.sidebar.button("🚪 登出", key="admin_logout_btn"):
        logout_user()
        st.rerun()
    
    # 根据菜单选择显示对应功能
    if st.session_state.admin_menu_selection == "用户管理":
        run_admin_panel(st.session_state.username, "user_management")
    elif st.session_state.admin_menu_selection == "审计日志":
        run_admin_panel(st.session_state.username, "audit_logs")

def show_user_interface():
    """显示普通用户界面"""
    st.sidebar.title("👤 用户控制台")
    st.sidebar.write(f"欢迎，用户 **{st.session_state.username}**")
    
    # 登出按钮
    if st.sidebar.button("🚪 登出", key="user_logout_btn"):
        logout_user()
        st.rerun()
    
    # 直接显示人脸识别功能，移除菜单选择
    try:
        recognition_ui.run_recognition(st.session_state.username)
    except Exception as e:
        st.error(f"❌ 调用人脸识别功能时出错: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

def logout_user():
    """用户登出"""
    try:
        # 调用后端登出API
        response = st.session_state.requests_session.post(f"{config.DJANGO_API_URL}/logout/")
        
        # 清除会话状态
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.session_state.is_admin = False
        st.session_state.admin_menu_selection = "用户管理"
        
        # 重新创建requests session
        st.session_state.requests_session = requests.Session()
        
        # 清除其他可能的会话状态
        for key in list(st.session_state.keys()):
            if key.startswith(('confirm_delete_', 'delete_user_', 'batch_delete_')):
                del st.session_state[key]
        
        st.success("已成功登出")
        
    except Exception as e:
        st.error(f"登出时发生错误: {str(e)}")

if __name__ == "__main__":
    main()