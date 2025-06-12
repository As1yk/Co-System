import streamlit as st
import requests 
import json
import time # 导入 time 模块

# Django 后端 API 地址
DJANGO_API_BASE_URL = "http://127.0.0.1:8000/api" 

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


# 修改 show_auth 以便在主页面布局，并返回用户操作和数据
def display_auth_forms(auth_action):
    """显示登录或注册表单，并处理提交。"""

    # 使用列来限制表单宽度并使其居中
    col1, col2, col3 = st.columns([1, 2, 1]) # 例如，左右各1份，中间2份宽度

    with col2: # 在中间列放置表单
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
            with st.form("registration_form"):
                new_user = st.text_input('用户名', key='reg_user_main_form')
                new_pw = st.text_input('密码', type='password', key='reg_pw_main_form')
                new_pw_conf = st.text_input('确认密码', type='password', key='reg_pw_conf_main_form')

                st.markdown("---")
                st.subheader("身份照片录入 (必须提供)")
                photo_source_options = ("上传照片", "现场拍照")
                photo_source = st.radio("选择照片来源:", photo_source_options, key="reg_photo_source", index=0, horizontal=True)
                
                uploaded_file_data = None # 用于存储上传的文件对象或拍照的字节
                
                if photo_source == "上传照片":
                    uploaded_file = st.file_uploader("选择一张包含您清晰面部的照片", type=['jpg', 'jpeg', 'png'], key="reg_file_uploader")
                    if uploaded_file is not None:
                        st.image(uploaded_file, caption="待上传的照片预览", width=150)
                        uploaded_file_data = uploaded_file # UploadedFile object
                
                elif photo_source == "现场拍照":
                    img_file_buffer = st.camera_input("请正对摄像头，确保光线充足", key="reg_camera_input")
                    if img_file_buffer is not None:
                        st.image(img_file_buffer, caption="拍摄的照片预览", width=150)
                        uploaded_file_data = img_file_buffer.getvalue() # bytes

                st.markdown("---")
                reg_submitted = st.form_submit_button('注册')

                if reg_submitted:
                    if not new_user or not new_pw:
                        st.error('用户名和密码不能为空。')
                    elif new_pw != new_pw_conf:
                        st.error('两次密码不一致。')
                    elif uploaded_file_data is None:
                        st.error("必须提供身份照片才能注册。请上传照片或现场拍照。")
                    else:
                        form_data = {'username': new_user, 'password': new_pw}
                        files_payload = None
                        photo_filename = "identity_photo.jpg"

                        if photo_source == "上传照片" and hasattr(uploaded_file_data, 'name'):
                            photo_filename = uploaded_file_data.name
                        
                        # uploaded_file_data 可能是 UploadedFile 对象或 bytes
                        files_payload = {'identity_photo': (photo_filename, uploaded_file_data, 'image/jpeg')} 

                        response_data = api_request('POST', 'register', data=form_data, files=files_payload)
                        
                        if response_data and response_data.get('status') == 'success':
                            st.success(response_data.get('message', '注册成功，请登录。'))
                        elif response_data:
                            st.error(response_data.get('message', '注册失败'))
                        else:
                            st.error('注册请求失败，请检查 Django 服务。')

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