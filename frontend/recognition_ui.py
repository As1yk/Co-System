import os
import streamlit as st
import cv2
import requests
import time
import io

DJANGO_API_BASE_URL = os.environ.get('DJANGO_API_URL', "http://127.0.0.1:8000/api")

def get_api_session():
    """获取API会话"""
    if 'api_session' not in st.session_state:
        st.session_state.api_session = requests.Session()
    return st.session_state.api_session

def api_request(endpoint, method='GET', data=None, files=None):
    """统一的API请求"""
    session = get_api_session()
    url = f"{DJANGO_API_BASE_URL}/{endpoint}/"
    
    try:
        if method.upper() == 'POST':
            if files:
                response = session.post(url, data=data, files=files, timeout=30)
            else:
                response = session.post(url, json=data, headers={'Content-Type': 'application/json'}, timeout=30)
        else:
            response = session.get(url, timeout=30)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API请求失败: {str(e)}")
        return None

def check_backend_connectivity():
    """检查后端连接"""
    try:
        response = get_api_session().get(f"{DJANGO_API_BASE_URL}/current_user_status/", timeout=5)
        return response.status_code in [200, 401]
    except:
        return False

def run_recognition(username: str):
    """主要的识别界面函数"""
    st.title('🎯 用户身份验证')
    st.write("**基于AI的人脸识别系统**")
    
    if not check_backend_connectivity():
        st.error("🔴 后端服务不可达")
        st.markdown(f"""
        ### 🔧 故障排查步骤：
        1. **检查后端服务**: 确认Django服务运行在 `{DJANGO_API_BASE_URL.replace('/api', '')}`
        2. **检查网络**: 确认前后端设备网络互通
        3. **检查配置**: 验证API地址配置正确
        4. **检查防火墙**: 确认端口8000已开放
        """)
        return

    st.info(f"👤 当前用户：**{username}**")
    
    # 身份验证界面
    verify_user_identity(username)

def verify_user_identity(username: str):
    """用户身份验证"""
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col2:
        st.header("🔒 身份验证")
        st.write("将进行 **10** 次活体检测投票，阈值：0.50")
        
        if 'run_live' not in st.session_state:
            st.session_state.run_live = False
        
        run_live = st.checkbox("开启实时验证", value=st.session_state.run_live)
        st.session_state.run_live = run_live
        
        if not run_live:
            st.info("请勾选'开启实时验证'以开始身份验证")
            return
        
        # 创建识别会话
        st.info("🔄 正在创建识别会话...")
        session_response = api_request('recognition/start', 'POST', {
            'username': username,
            'num_votes': 10,
            'live_threshold': 0.5
        })
        
        if not session_response or session_response.get('status') != 'success':
            st.error("❌ 创建识别会话失败")
            st.session_state.run_live = False
            return
        
        session_id = session_response['session_id']
        st.success(f"✅ 识别会话已创建")
        st.session_state.current_session_id = session_id
        
        # 视频处理
        process_video_frames(session_id, username)

def process_video_frames(session_id, username):
    """处理视频帧"""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        st.error("❌ 无法打开摄像头")
        st.session_state.run_live = False
        return
    
    frame_ph = st.empty()
    status_ph = st.empty()
    progress = st.progress(0.0)
    
    frame_count = 0
    
    try:
        while st.session_state.run_live:
            ret, frame = cap.read()
            if not ret:
                status_ph.warning("⚠️ 无法读取摄像头帧")
                time.sleep(0.1)
                continue
            
            frame_count += 1
            display_frame = cv2.flip(frame, 1)
            frame_ph.image(display_frame, channels="BGR", caption=f"第 {frame_count} 帧")
            
            # 每8帧处理一次
            if frame_count % 8 == 0:
                status_ph.info("🔍 正在处理帧...")
                
                # 编码并发送帧
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                frame_bytes = io.BytesIO(buffer.tobytes())
                frame_bytes.name = 'frame.jpg'
                
                frame_response = api_request('recognition/process_frame', 'POST',
                    {'session_id': session_id}, {'frame': frame_bytes})
                
                if frame_response and frame_response.get('status') == 'success':
                    result = frame_response['result']
                    session_status = frame_response['session_status']
                    
                    if result['success']:
                        votes_info = f"{result['votes_passed']}/{result['total_votes']}"
                        liveness_info = f"活体分数: {result['liveness_score']:.3f}"
                        vote_result = "✅" if result['vote_result'] == 'passed' else "❌"
                        status_ph.success(f"{vote_result} 投票 {votes_info} - {liveness_info}")
                        
                        progress.progress(result['total_votes'] / 10)
                        
                        if session_status in ['liveness_passed', 'liveness_failed']:
                            break
                    else:
                        status_ph.warning(f"⚠️ {result['message']}")
                else:
                    st.error("❌ 后端处理失败")
                    break
            
            time.sleep(0.05)
            
            if not st.session_state.run_live:
                break
    
    finally:
        cap.release()
        progress.empty()
    
    # 完成识别
    if st.session_state.run_live:
        finalize_recognition(session_id, username, status_ph)

def finalize_recognition(session_id, username, status_ph):
    """完成识别流程"""
    status_ph.info("🔄 正在完成识别流程...")
    
    final_response = api_request('recognition/finalize', 'POST', {
        'session_id': session_id,
        'username': username
    })
    
    if final_response and final_response.get('status') == 'success':
        final_result = final_response['final_result']
        
        if final_result['success']:
            score_info = f"匹配分数: {final_result.get('score', 'N/A')}"
            st.success(f"✅ 身份验证成功！{score_info}")
        else:
            st.error(f"❌ 身份验证失败: {final_result['message']}")
    else:
        st.error("❌ 完成识别流程失败")
    
    st.session_state.run_live = False

def run_recognition_with_callback(username: str):
    """带回调的人脸识别验证，用于关键操作"""
    st.title('🎯 用户身份验证')
    st.write("**基于AI的人脸识别系统**")
    
    if not check_backend_connectivity():
        st.error("🔴 后端服务不可达")
        st.markdown(f"""
        ### 🔧 故障排查步骤：
        1. **检查后端服务**: 确认Django服务运行在 `{DJANGO_API_BASE_URL.replace('/api', '')}`
        2. **检查网络**: 确认前后端设备网络互通
        3. **检查配置**: 验证API地址配置正确
        4. **检查防火墙**: 确认端口8000已开放
        """)
        return False

    st.info(f"👤 当前用户：**{username}**")
    
    # 身份验证界面
    return verify_user_identity_with_callback(username)

def verify_user_identity_with_callback(username: str):
    """用户身份验证 - 带返回值"""
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col2:
        st.header("🔒 身份验证")
        st.write("将进行 **10** 次活体检测投票，阈值：0.50")
        
        if 'run_live' not in st.session_state:
            st.session_state.run_live = False
        
        run_live = st.checkbox("开启实时验证", value=st.session_state.run_live)
        st.session_state.run_live = run_live
        
        if not run_live:
            st.info("请勾选'开启实时验证'以开始身份验证")
            return None
        
        # 创建识别会话
        st.info("🔄 正在创建识别会话...")
        session_response = api_request('recognition/start', 'POST', {
            'username': username,
            'num_votes': 10,
            'live_threshold': 0.5
        })
        
        if not session_response or session_response.get('status') != 'success':
            st.error("❌ 创建识别会话失败")
            st.session_state.run_live = False
            return False
        
        session_id = session_response['session_id']
        st.success(f"✅ 识别会话已创建")
        st.session_state.current_session_id = session_id
        
        # 视频处理
        return process_video_frames_with_callback(session_id, username)

def process_video_frames_with_callback(session_id, username):
    """处理视频帧 - 带返回值"""
    import cv2
    import time
    import io
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        st.error("❌ 无法打开摄像头")
        st.session_state.run_live = False
        return False
    
    frame_ph = st.empty()
    status_ph = st.empty()
    progress = st.progress(0.0)
    
    frame_count = 0
    verification_completed = False
    
    try:
        while st.session_state.run_live and not verification_completed:
            ret, frame = cap.read()
            if not ret:
                status_ph.warning("⚠️ 无法读取摄像头帧")
                time.sleep(0.1)
                continue
            
            frame_count += 1
            display_frame = cv2.flip(frame, 1)
            frame_ph.image(display_frame, channels="BGR", caption=f"第 {frame_count} 帧")
            
            # 每8帧处理一次
            if frame_count % 8 == 0:
                status_ph.info("🔍 正在处理帧...")
                
                # 编码并发送帧
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                frame_bytes = io.BytesIO(buffer.tobytes())
                frame_bytes.name = 'frame.jpg'
                
                frame_response = api_request('recognition/process_frame', 'POST',
                    {'session_id': session_id}, {'frame': frame_bytes})
                
                if frame_response and frame_response.get('status') == 'success':
                    result = frame_response['result']
                    session_status = frame_response['session_status']
                    
                    if result['success']:
                        votes_info = f"{result['votes_passed']}/{result['total_votes']}"
                        liveness_info = f"活体分数: {result['liveness_score']:.3f}"
                        vote_result = "✅" if result['vote_result'] == 'passed' else "❌"
                        status_ph.success(f"{vote_result} 投票 {votes_info} - {liveness_info}")
                        
                        progress.progress(result['total_votes'] / 10)
                        
                        if session_status in ['liveness_passed', 'liveness_failed']:
                            verification_completed = True
                            break
                    else:
                        status_ph.warning(f"⚠️ {result['message']}")
                else:
                    st.error("❌ 后端处理失败")
                    break
            
            time.sleep(0.05)
            
            if not st.session_state.run_live:
                break
    
    finally:
        cap.release()
        progress.empty()
    
    # 完成识别
    if verification_completed:
        return finalize_recognition_with_callback(session_id, username, status_ph)
    else:
        return False

def finalize_recognition_with_callback(session_id, username, status_ph):
    """完成识别流程 - 带返回值"""
    status_ph.info("🔄 正在完成识别流程...")
    
    final_response = api_request('recognition/finalize', 'POST', {
        'session_id': session_id,
        'username': username
    })
    
    if final_response and final_response.get('status') == 'success':
        final_result = final_response['final_result']
        
        if final_result['success']:
            score_info = f"匹配分数: {final_result.get('score', 'N/A')}"
            st.success(f"✅ 身份验证成功！{score_info}")
            st.session_state.run_live = False
            return True
        else:
            st.error(f"❌ 身份验证失败: {final_result['message']}")
            st.session_state.run_live = False
            return False
    else:
        st.error("❌ 完成识别流程失败")
        st.session_state.run_live = False
        return False

# 向后兼容
def verify_user_identity_api(*args, **kwargs):
    return verify_user_identity(*args, **kwargs)

def run_admin(username: str):
    st.warning("此功能已迁移到admin_ui模块，请使用管理员面板。")