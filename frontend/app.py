import streamlit as st
import requests
from config import Config
import auth_ui
from admin_ui import run_admin_panel
import recognition_ui

config = Config()

def get_session():
    """获取或创建请求会话"""
    if 'requests_session' not in st.session_state:
        st.session_state.requests_session = requests.Session()
    return st.session_state.requests_session

def api_request(endpoint, method='GET', data=None, files=None):
    """统一的API请求函数"""
    session = get_session()
    url = f"{config.DJANGO_API_URL}/{endpoint}/"
    
    try:
        if method.upper() == 'POST':
            if files:
                response = session.post(url, data=data, files=files)
            else:
                response = session.post(url, json=data, headers={'Content-Type': 'application/json'})
        else:
            response = session.get(url)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API请求失败: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"请求异常: {str(e)}")
        return None

def check_login_status():
    """检查用户登录状态"""
    try:
        data = api_request('current_user_status')
        if data and data.get('authenticated'):
            st.session_state.authenticated = True
            st.session_state.username = data.get('username', '')
            st.session_state.is_admin = data.get('is_admin', False)
        else:
            st.session_state.authenticated = False
            st.session_state.username = ""
            st.session_state.is_admin = False
    except Exception:
        st.session_state.authenticated = False

def show_auth_interface():
    """显示认证界面（登录/注册）"""
    st.title("👤 人脸识别系统")
    
    tab1, tab2 = st.tabs(["🔐 登录", "📝 注册"])
    
    with tab1:
        show_login_form()
    
    with tab2:
        show_register_form()

def show_login_form():
    """登录表单"""
    st.subheader("🔐 用户登录")
    
    with st.form("login_form"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        login_btn = st.form_submit_button("登录", type="primary")
        
        if login_btn and username and password:
            result = api_request('login', 'POST', {'username': username, 'password': password})
            if result and result.get('status') == 'success':
                st.session_state.authenticated = True
                st.session_state.username = result.get('username')
                st.session_state.is_admin = result.get('is_admin', False)
                st.success("登录成功！")
                st.rerun()
            else:
                st.error(result.get('message', '登录失败') if result else '服务器连接失败')

def show_register_form():
    """注册表单"""
    st.subheader("📝 用户注册")
    
    # 初始化状态
    if 'register_step' not in st.session_state:
        st.session_state.register_step = 1
    
    if st.session_state.register_step == 1:
        show_register_step1()
    else:
        show_register_step2()

def show_register_step1():
    """注册步骤1：用户信息"""
    with st.form("user_info_form"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        confirm_password = st.text_input("确认密码", type="password")
        next_btn = st.form_submit_button("下一步：选择照片获取方式", type="primary")
        
        if next_btn:
            if not all([username, password, confirm_password]):
                st.error("请填写完整的用户信息")
            elif password != confirm_password:
                st.error("两次输入的密码不一致")
            else:
                st.session_state.register_username = username
                st.session_state.register_password = password
                st.session_state.register_step = 2
                st.rerun()

def show_register_step2():
    """注册步骤2：照片获取"""
    st.write(f"**用户名**: {st.session_state.register_username}")
    st.write("---")
    
    photo_method = st.radio("选择获取方式：", ["📁 上传照片文件", "📷 实时拍照"])
    
    photo_file = None
    if photo_method == "📁 上传照片文件":
        photo_file = st.file_uploader("上传身份照片", type=['jpg', 'jpeg', 'png'])
        if photo_file:
            st.image(photo_file, caption="上传的照片", width=150)
    else:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            photo_file = st.camera_input("请拍摄您的身份照片")
            if photo_file:
                st.image(photo_file, caption="拍摄的照片", width=200)
    
    col_back, col_register = st.columns(2)
    
    with col_back:
        if st.button("⬅️ 返回修改信息"):
            st.session_state.register_step = 1
            st.rerun()
    
    with col_register:
        if st.button("✅ 完成注册", type="primary", disabled=(photo_file is None)):
            if photo_file:
                result = api_request('register', 'POST', 
                    {'username': st.session_state.register_username, 'password': st.session_state.register_password},
                    {'identity_photo': photo_file}
                )
                
                if result and result.get('status') == 'success':
                    st.success("✅ 注册成功！请登录")
                    # 重置状态
                    st.session_state.register_step = 1
                    for key in ['register_username', 'register_password']:
                        if key in st.session_state:
                            del st.session_state[key]
                else:
                    st.error(result.get('message', '注册失败') if result else '服务器连接失败')

def logout_user():
    """用户登出"""
    api_request('logout', 'POST')
    
    # 清除状态
    for key in ['authenticated', 'username', 'is_admin', 'requests_session']:
        if key in st.session_state:
            del st.session_state[key]
    
    st.success("已成功登出")

def show_admin_interface():
    """显示管理员界面"""
    st.sidebar.title("🔧 管理员控制台")
    st.sidebar.write(f"欢迎，管理员 **{st.session_state.username}**")
    
    menu_options = ["用户管理", "审计日志"]
    selected_menu = st.sidebar.selectbox("选择管理功能：", menu_options)
    
    if st.sidebar.button("🚪 登出"):
        logout_user()
        st.rerun()
    
    # 显示对应功能
    if selected_menu == "用户管理":
        run_admin_panel(st.session_state.username, "user_management")
    else:
        run_admin_panel(st.session_state.username, "audit_logs")

def show_user_interface():
    """显示普通用户界面"""
    st.sidebar.title("👤 用户控制台")
    st.sidebar.write(f"欢迎，用户 **{st.session_state.username}**")
    
    if st.sidebar.button("🚪 登出"):
        logout_user()
        st.rerun()
    
    # 新增：操作类型选择
    st.sidebar.markdown("---")
    
    if st.sidebar.button("🟢 非关键操作", key="do_normal_op"):
        # 设置非关键操作状态
        st.session_state.operation_mode = "normal"
        st.rerun()
    
    if st.sidebar.button("🔴 关键操作", key="do_critical_op"):
        # 设置关键操作状态
        st.session_state.operation_mode = "critical"
        st.rerun()
    
    # 根据操作模式显示不同界面
    if st.session_state.get('operation_mode') == "normal":
        # 非关键操作界面 - 只显示成功文字
        st.title("🟢 非关键操作")
        st.success("✅ 非关键操作已成功执行！")
        
        if st.button("返回主界面"):
            st.session_state.operation_mode = None
            st.rerun()
            
    elif st.session_state.get('operation_mode') == "critical":
        # 关键操作界面 - 使用人脸识别验证
        try:
            # 检查是否验证成功
            if st.session_state.get('critical_verification_success'):
                st.title("🔴 关键操作")
                st.success("✅ 关键操作已成功执行！")
                
                if st.button("返回主界面"):
                    st.session_state.operation_mode = None
                    st.session_state.critical_verification_success = False
                    st.rerun()
            else:
                # 进行人脸识别验证
                result = recognition_ui.run_recognition_with_callback(st.session_state.username)
                if result is True:
                    st.session_state.critical_verification_success = True
                    st.rerun()
                    
        except Exception as e:
            st.error(f"❌ 人脸识别功能错误: {str(e)}")
        
    else:
        # 主界面 - 空白界面
        st.title("👤 用户控制台")
        st.write("请在左侧选择要执行的操作类型")

def main():
    """主应用函数"""
    st.set_page_config(
        page_title="人脸识别系统",
        page_icon="👤",
        layout="wide"
    )
    
    # 初始化状态
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'rerun_counter' not in st.session_state:
        st.session_state.rerun_counter = 0
    
    check_login_status()
    
    if not st.session_state.authenticated:
        show_auth_interface()
    elif st.session_state.is_admin:
        show_admin_interface()
    else:
        show_user_interface()

if __name__ == "__main__":
    main()