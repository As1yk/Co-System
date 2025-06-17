import os
import streamlit as st
import cv2
import numpy as np
import requests
from datetime import datetime
import time
import base64

# Django API 配置 - 支持环境变量配置
DJANGO_API_BASE_URL = os.environ.get('DJANGO_API_URL', "http://127.0.0.1:8000/api")

def get_api_session():
    """获取API会话"""
    if 'api_session' not in st.session_state:
        st.session_state.api_session = requests.Session()
    return st.session_state.api_session

def check_backend_connectivity():
    """检查后端连接状态"""
    try:
        session = get_api_session()
        response = session.get(f"{DJANGO_API_BASE_URL}/current_user_status/", timeout=5)
        return response.status_code in [200, 401]  # 401也表示后端正常，只是未认证
    except Exception as e:
        return False


def api_request(method, endpoint, data=None, files=None):
    """API请求辅助函数 - 增强跨网络支持"""
    session = get_api_session()
    url = f"{DJANGO_API_BASE_URL}/{endpoint}/"
    
    # 添加更详细的网络错误处理
    try:
        if method.upper() == 'POST':
            if files:
                response = session.post(url, data=data, files=files, timeout=30)
            else:
                headers = {'Content-Type': 'application/json'}
                response = session.post(url, json=data, headers=headers, timeout=30)
        else:
            response = session.get(url, params=data, timeout=30)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error(f"🔌 无法连接到后端服务器: {DJANGO_API_BASE_URL}")
        st.error("请检查：1) 后端是否启动  2) 网络连接  3) API地址配置")
        return None
    except requests.exceptions.Timeout:
        st.error("⏱️ 请求超时，后端响应过慢")
        return None
    except requests.exceptions.HTTPError as e:
        try:
            error_detail = e.response.json()
            st.error(f"API HTTP错误 ({e.response.status_code}): {error_detail}")
        except:
            st.error(f"API HTTP错误 ({e.response.status_code}): {e.response.text[:200]}")
        return None
    except Exception as e:
        st.error(f"API请求失败: {e}")
        return None

def verify_user_identity_api(username: str, num_votes: int = 10, live_threshold: float = 0.6):
    """完全基于API的用户身份验证"""
    
    col_ui_1, col_ui_2, col_ui_3 = st.columns([1, 3, 1])

    with col_ui_2:
        st.header("🔒 身份验证")
        
        # 动态检测系统状态
        system_status = check_system_status()
        
        # 系统状态检查
        with st.expander("🔍 系统状态检查", expanded=False):
            if system_status['simulation_mode']:
                st.markdown("""
                ### ⚠️ 当前系统状态：模拟模式
                
                **原因分析**：
                - 后端Django服务可能有导入错误
                - AI模型依赖未正确安装
                - API函数缺失或命名不匹配
                
                **解决方案**：
                
                1. **检查后端启动错误**：
                ```bash
                # 查看后端控制台错误信息
                cd backend
                python manage.py runserver 0.0.0.0:8000
                ```
                
                2. **安装缺失依赖**：
                ```bash
                cd backend
                pip install -r requirements.txt
                ```
                
                3. **检查API模块**：
                ```bash
                # 确认API模块完整性
                python -c "from api.utils_recognition import *"
                ```
                
                4. **重启服务**：
                重启后端服务器以加载最新代码
                """)
            else:
                st.markdown("""
                ### ✅ 当前系统状态：AI模式
                
                - 后端服务正常运行
                - AI模型已正确加载
                - 所有依赖完整安装
                """)
        
        st.write(f"将进行 **{num_votes}** 次活体检测投票，阈值：{live_threshold:.2f}")

        if 'run_live' not in st.session_state:
            st.session_state.run_live = False
        
        # 根据系统状态显示不同的警告
        if system_status['simulation_mode']:
            st.warning("⚠️ 当前运行在模拟模式下，识别结果为随机生成")
            st.info("💡 要使用真实AI识别，请先解决后端导入错误")
        else:
            st.success("✅ 系统运行在AI模式下，将使用真实的人脸识别")
        
        run_live_checkbox = st.checkbox("开启实时验证", key="run_live_cb", value=st.session_state.run_live,
                                        on_change=lambda: setattr(st.session_state, 'run_live', st.session_state.run_live_cb))

        if not st.session_state.run_live:
            st.info("请勾选'开启实时验证'以开始身份验证")
            return None

        # 1. 创建识别会话
        st.info("🔄 正在创建识别会话...")
        session_response = api_request('POST', 'recognition/start', {
            'num_votes': num_votes,
            'live_threshold': live_threshold,
            'username': username  # 添加用户名参数
        })
        
        if not session_response or session_response.get('status') != 'success':
            st.error("❌ 创建识别会话失败")
            if session_response:
                error_msg = session_response.get('message', '未知错误')
                st.error(f"错误详情: {error_msg}")
                
                # 检查是否是模拟模式相关错误
                if 'simulation' in error_msg.lower() or '模拟' in error_msg:
                    st.warning("🔧 检测到后端运行在模拟模式，请检查AI模型加载状态")
            st.session_state.run_live = False
            return False
        
        session_id = session_response['session_id']
        
        # 检查是否为模拟模式
        is_simulation = session_response.get('simulation_mode', False)
        if is_simulation:
            st.warning("🎭 当前会话运行在模拟模式")
        else:
            st.success(f"✅ 识别会话已创建: {session_id}")
        
        # 存储session_id到streamlit session
        st.session_state.current_session_id = session_id

        # 2. 开始视频捕获和处理
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            st.error("❌ 无法打开摄像头")
            st.session_state.run_live = False
            return False

        frame_ph = st.empty()
        status_ph = st.empty()
        progress = st.progress(0.0)

        frame_count = 0
        process_interval = 8  # 增加间隔，减少请求频率

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

                # 每隔几帧发送到后端处理
                if frame_count % process_interval == 0:
                    status_ph.info("🔍 正在发送帧到后端处理...")
                    
                    # 编码帧为JPEG
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    
                    # 创建文件对象
                    import io
                    frame_bytes = io.BytesIO(buffer.tobytes())
                    frame_bytes.name = 'frame.jpg'
                    
                    # 发送帧到后端 - 使用存储的session_id
                    files = {'frame': frame_bytes}
                    data = {'session_id': st.session_state.current_session_id}
                    
                    frame_response = api_request('POST', 'recognition/process_frame', 
                                               data=data, files=files)
                    
                    if frame_response and frame_response.get('status') == 'success':
                        result = frame_response['result']
                        session_status = frame_response['session_status']
                        
                        if result['success']:
                            votes_info = f"{result['votes_passed']}/{result['total_votes']}"
                            liveness_info = f"活体分数: {result['liveness_score']:.3f}"
                            vote_result = "✅" if result['vote_result'] == 'passed' else "❌"
                            status_ph.success(f"{vote_result} 投票 {votes_info} - {liveness_info}")
                            
                            # 更新进度
                            progress.progress(result['total_votes'] / num_votes)
                            
                            # 检查是否完成
                            if session_status in ['liveness_passed', 'liveness_failed']:
                                break
                        else:
                            status_ph.warning(f"⚠️ {result['message']}")
                    else:
                        st.error("❌ 后端处理失败")
                        if frame_response:
                            st.error(f"错误详情: {frame_response}")
                        break
                
                # 短暂延迟
                time.sleep(0.05)

                # 检查用户是否取消
                if not st.session_state.run_live:
                    break

        finally:
            cap.release()
            progress.empty()

        # 3. 完成识别流程
        if st.session_state.run_live:
            status_ph.info("🔄 正在完成识别流程...")
            
            # 使用存储的session_id
            final_response = api_request('POST', 'recognition/finalize', {
                'session_id': st.session_state.current_session_id,
                'username': username
            })
            
            if final_response and final_response.get('status') == 'success':
                final_result = final_response['final_result']
                
                if final_result['success']:
                    score_info = f"匹配分数: {final_result.get('score', 'N/A')}"
                    simulation_info = ""
                    
                    # 检查是否为模拟结果
                    if final_result.get('simulation_mode', False):
                        simulation_info = " (模拟结果)"
                        st.warning("🎭 这是模拟识别结果，不代表真实的人脸匹配")
                    
                    st.success(f"✅ 身份验证成功！{score_info}{simulation_info}")
                    if not final_result.get('simulation_mode', False):
                        st.balloons()
                    st.session_state.run_live = False
                    return True
                else:
                    error_msg = final_result['message']
                    simulation_info = ""
                    
                    # 处理模拟模式错误信息
                    if '模拟' in error_msg:
                        simulation_info = "\n\n💡 **这是模拟结果**：当前系统运行在测试模式下"
                        error_msg = error_msg.replace('（模拟）', '').replace('(模拟)', '')
                    
                    st.error(f"❌ 身份验证失败: {error_msg}{simulation_info}")
                    st.session_state.run_live = False
                    return False
            else:
                st.error("❌ 完成识别流程失败")
                if final_response:
                    st.error(f"错误详情: {final_response}")
                st.session_state.run_live = False
                return False
        else:
            st.warning("⚠️ 验证已取消")
            return None

def check_system_status():
    """检查系统运行状态"""
    try:
        # 尝试获取系统状态
        response = api_request('GET', 'system_status')
        if response and response.get('status') == 'success':
            return response.get('system_info', {'simulation_mode': True})
        else:
            return {'simulation_mode': True, 'error': 'API不可达'}
    except:
        return {'simulation_mode': True, 'error': '连接失败'}

def run_recognition(username: str):
    """主要的识别界面函数 - 供app.py调用"""
    st.title('🎯 用户身份验证')
    
    # 检查系统状态并显示
    system_status = check_system_status()
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write("**基于AI的人脸识别系统**")
    with col2:
        if system_status['simulation_mode']:
            st.markdown("🎭 **模拟模式**")
        else:
            st.markdown("🤖 **AI模式**")
    
    if system_status['simulation_mode']:
        st.warning("💡 当前系统运行在模拟模式下 - 后端可能有导入错误")
        st.markdown("""
        **常见问题**：
        - Django启动时出现ImportError
        - API函数名称不匹配
        - 依赖包未正确安装
        
        **解决步骤**：请检查后端控制台的错误信息
        """)
    else:
        st.success("✅ 系统正常运行在AI模式下")

    # 连接状态检查
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

    with st.expander("📖 使用说明", expanded=False):
        st.markdown("""
        ### 前后端分离架构特点：
        1. **前端职责：** 仅负责UI展示和用户交互
        2. **后端职责：** 处理所有AI模型和业务逻辑
        3. **通信方式：** 通过RESTful API进行数据交换
        
        ### 验证流程：
        1. 前端创建识别会话
        2. 前端采集视频帧并发送给后端
        3. 后端执行活体检测和人脸识别
        4. 前端展示处理结果
        """)

    st.info(f"👤 当前用户：**{username}**")

    # 调用基于API的验证函数
    result = verify_user_identity_api(username, num_votes=10, live_threshold=0.5)
    
    if result is None:
        pass  # 用户未开启或取消
    elif result is False:
        st.error('❌ 身份验证失败')
        st.markdown("""
        ### 可能的原因：
        - **模拟模式**: 当前使用随机结果模拟识别过程
        - **模型未加载**: 后端AI模型可能未正确加载
        - **依赖缺失**: TensorFlow或DeepFace未安装
        - **网络问题**: 前后端通信异常
        
        ### 解决建议：
        1. 检查后端控制台是否有模型加载错误
        2. 确认所有AI依赖包已正确安装
        3. 重启后端服务再次尝试
        """)
    else:
        st.success('✅ 恭喜！身份验证成功！')
        if result != "simulation":
            st.info("🎭 注意：这是模拟识别结果，用于演示系统功能")

# 兼容性函数 - 如果有其他地方调用旧函数
def run_admin(username: str):
    """管理员功能 - 重定向到admin_ui"""
    st.warning("此功能已迁移到admin_ui模块，请使用管理员面板。")
    
# 确保所有必要的函数都存在
def verify_user_identity(*args, **kwargs):
    """向后兼容的函数"""
    return verify_user_identity_api(*args, **kwargs)