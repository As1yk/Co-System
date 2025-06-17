import streamlit as st
import requests 
import json
import time
from config import config

# 使用配置管理
DJANGO_API_BASE_URL = config.get_api_url()

def api_request(method, endpoint, data=None, params=None, headers=None, files=None):
    url = f"{DJANGO_API_BASE_URL}/{endpoint}/"
    
    if 'api_session' not in st.session_state:
        st.session_state.api_session = requests.Session()
    
    try:
        if method.upper() == 'POST':
            if files:
                response = st.session_state.api_session.post(url, data=data, files=files, params=params, headers=headers, timeout=10)
            else:
                response = st.session_state.api_session.post(url, json=data, params=params, headers=headers, timeout=10)
        elif method.upper() == 'GET':
            response = st.session_state.api_session.get(url, params=params, headers=headers, timeout=10)
        else:
            st.error(f"Unsupported method: {method}")
            return None
        
        response.raise_for_status() 
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API 请求失败 ({url}): {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                st.error(f"错误详情: {e.response.json()}")
            except json.JSONDecodeError:
                st.error(f"错误详情 (非JSON): {e.response.text}")
        return None

def display_auth_forms(auth_action):
    """显示登录或注册表单，并处理提交。"""
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if auth_action == '登录':
            # 如果 session_state 中有登录成功并需要显示消息的标志，则只显示消息
            if st.session_state.get('show_login_success_message', False):
                st.success(f"登录成功！欢迎 {st.session_state.get('username', '')}。")
                st.session_state.show_login_success_message = False 
                
                # 在这里添加延迟
                placeholder = st.empty() # 创建一个占位符，用于后续可能的加载指示
                placeholder.info("正在跳转，请稍候...") # 可选的加载提示
                time.sleep(0.7) # 等待 0.7 秒 (约半秒多一点)
                placeholder.empty() # 清除加载提示
                
                # rerun_counter 应该在设置 logged_in = True 时已经增加过了
                # 并且 app.py 中的 st.rerun() 会处理跳转
                # 这里不需要再次 st.rerun()，因为上一次的 st.rerun() 导致了这次的执行
                # 重要的是 app.py 在这次 rerun 后会因为 logged_in=True 而显示主界面
                return 

            st.subheader('用户登录')
            with st.form("login_form"):
                user = st.text_input('用户名', key='login_user_main_form')
                pw = st.text_input('密码', type='password', key='login_pw_main_form')
                submitted = st.form_submit_button('登录')

                if submitted:
                    if not user or not pw:
                        st.error("用户名和密码不能为空。")
                    else:
                        response_data = api_request('POST', 'login', data={'username': user, 'password': pw})
                        if response_data and response_data.get('status') == 'success':
                            st.session_state.logged_in = True
                            st.session_state.username = response_data.get('username', user)
                            st.session_state.is_admin = response_data.get('is_admin', False)
                            st.session_state.logged_in_once = True 
                            st.session_state.show_login_success_message = True # 设置成功消息标志
                            st.session_state.rerun_counter += 1 
                            # 立即重新运行，下一次迭代会进入上面的 if 块显示成功消息
                            st.rerun() # 使用 st.rerun() 强制立即重新运行
                        elif response_data:
                            st.error(response_data.get('message', '登录失败，请检查API响应'))
                        else:
                            st.error('登录请求失败，请检查 Django 服务是否运行。')

        elif auth_action == '注册':
            st.subheader('新用户注册')
            
            # 用户名和密码输入（在表单外部，避免重置）
            new_user = st.text_input('用户名', key='reg_user_outside_form')
            new_pw = st.text_input('密码', type='password', key='reg_pw_outside_form')
            new_pw_conf = st.text_input('确认密码', type='password', key='reg_pw_conf_outside_form')

            st.markdown("---")
            st.subheader("身份照片录入 (必须提供)")
            
            # 照片来源选择（在表单外部）
            photo_source_options = ["上传照片", "现场拍照"]
            photo_source = st.radio(
                "选择照片来源:", 
                photo_source_options, 
                key="reg_photo_source_main",
                index=0, 
                horizontal=True
            )
            
            uploaded_file_data = None
            
            # 动态显示对应的输入组件
            if photo_source == "上传照片":
                st.write("📁 **上传本地照片**")
                uploaded_file = st.file_uploader(
                    "选择一张包含您清晰面部的照片", 
                    type=['jpg', 'jpeg', 'png'], 
                    key="reg_file_uploader_main",
                    help="支持JPG、JPEG、PNG格式，建议照片清晰且光线充足"
                )
                if uploaded_file is not None:
                    st.image(uploaded_file, caption="📁 上传的照片预览", width=200)
                    uploaded_file_data = uploaded_file
                    st.success("✅ 照片上传成功")
                else:
                    st.info("💡 请选择一张照片文件")
            
            elif photo_source == "现场拍照":
                st.write("📷 **现场拍照**")
                st.info("💡 请确保光线充足，正对摄像头，表情自然")
                
                # 检查摄像头权限提示
                st.markdown("""
                📝 **使用提示**：
                - 首次使用需要允许浏览器访问摄像头
                - 确保您的设备有可用的摄像头
                - 点击下方摄像头图标开始拍照
                """)
                
                img_file_buffer = st.camera_input(
                    "📷 点击拍照", 
                    key="reg_camera_input_main",
                    help="正对摄像头，确保光线充足，点击拍照按钮"
                )
                if img_file_buffer is not None:
                    st.image(img_file_buffer, caption="📷 拍摄的照片预览", width=200)
                    uploaded_file_data = img_file_buffer.getvalue()
                    st.success("✅ 照片拍摄成功")
                else:
                    st.info("📷 点击上方摄像头区域进行拍照")

            st.markdown("---")
            
            # 显示当前状态
            if uploaded_file_data is not None:
                st.success(f"✅ 已通过【{photo_source}】方式获取身份照片")
            else:
                st.warning(f"⚠️ 请通过【{photo_source}】方式提供身份照片")
            
            # 注册按钮和处理逻辑
            if st.button('📝 提交注册', key='reg_submit_btn', use_container_width=True, type='primary'):
                # 表单验证
                if not new_user or not new_pw:
                    st.error('❌ 用户名和密码不能为空')
                elif len(new_user.strip()) < 2:
                    st.error('❌ 用户名至少需要2个字符')
                elif len(new_pw) < 6:
                    st.error('❌ 密码至少需要6个字符')
                elif new_pw != new_pw_conf:
                    st.error('❌ 两次密码不一致')
                elif uploaded_file_data is None:
                    st.error(f"❌ 必须提供身份照片才能注册。请通过【{photo_source}】方式提供照片。")
                else:
                    # 准备提交数据
                    form_data = {
                        'username': new_user.strip(), 
                        'password': new_pw
                    }
                    
                    # 处理文件数据
                    photo_filename = "identity_photo.jpg"
                    if photo_source == "上传照片" and hasattr(uploaded_file_data, 'name'):
                        photo_filename = uploaded_file_data.name
                    elif photo_source == "现场拍照":
                        photo_filename = f"camera_photo_{new_user}.jpg"
                    
                    files_payload = {
                        'identity_photo': (photo_filename, uploaded_file_data, 'image/jpeg')
                    }

                    # 提交注册请求
                    with st.spinner('🔄 正在注册，请稍候...'):
                        response_data = api_request('POST', 'register', data=form_data, files=files_payload)
                    
                    if response_data and response_data.get('status') == 'success':
                        st.success(f"🎉 {response_data.get('message', '注册成功！')}")
                        st.balloons()
                        st.info("💡 请切换到【登录】标签页使用新账户登录")
                        
                        # 清空表单数据
                        if 'reg_user_outside_form' in st.session_state:
                            del st.session_state.reg_user_outside_form
                        if 'reg_pw_outside_form' in st.session_state:
                            del st.session_state.reg_pw_outside_form
                        if 'reg_pw_conf_outside_form' in st.session_state:
                            del st.session_state.reg_pw_conf_outside_form
                        
                    elif response_data:
                        st.error(f"❌ {response_data.get('message', '注册失败')}")
                    else:
                        st.error('❌ 注册请求失败，请检查网络连接和Django服务状态')

def handle_logout():
    response_data = api_request('POST', 'logout') 
    if response_data and response_data.get('status') == 'success':
        st.info('已在后端注销。正在清除前端状态...')
    else:
        st.warning('后端注销可能失败或未响应，但仍将清除前端状态。')
    
    st.session_state.logged_in = False
    st.session_state.username = ''
    st.session_state.is_admin = False
    st.session_state.logged_in_once = False
    if 'show_login_success_message' in st.session_state:
        del st.session_state.show_login_success_message # 清除登录成功消息标志
    if 'api_session' in st.session_state: 
        st.session_state.api_session = requests.Session()
    st.session_state.rerun_counter += 1