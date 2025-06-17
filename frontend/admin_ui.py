# admin_ui.py

import streamlit as st
import requests
import os
import json
from config import config

# 使用配置管理
DJANGO_API_BASE_URL = config.get_api_url()
DJANGO_MEDIA_URL = f"{config.BACKEND_HOST}:{config.BACKEND_PORT}/media/"

def get_api_session():
    if 'api_session' not in st.session_state:
        st.session_state.api_session = requests.Session()
    return st.session_state.api_session

def get_logs_from_api(endpoint: str, params: dict = None):
    api_session = get_api_session()
    url = f"{DJANGO_API_BASE_URL}/{endpoint}/"
    try:
        response = api_session.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get('status') == 'success':
            # 处理不同的响应格式
            if 'logs' in data:
                return data.get('logs', [])
            elif 'users' in data:
                return data.get('users', [])
            else:
                return data
        else:
            st.error(f"API 获取数据失败: {data.get('message', '未知错误')}")
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"请求 API ({url}) 失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                st.error(f"错误详情: {e.response.json()}")
            except json.JSONDecodeError:
                 st.error(f"错误详情 (非JSON): {e.response.text[:200]}...")
        return []
    except json.JSONDecodeError:
        st.error(f"无法解析来自 {url} 的 API 响应。")
        return []


def run_user_management(username: str):
    """用户管理功能"""
    st.subheader("👥 用户管理")
    st.write(f"管理员：**{username}**")
    
    # 获取用户列表
    users_response = get_logs_from_api("users", params={'limit': 100})
    
    if users_response:
        st.write("### 系统用户列表")
        user_table_data = []
        for user in users_response:
            user_table_data.append({
                "用户名": user.get('username', ''),
                "邮箱": user.get('email', ''),
                "是否管理员": "是" if user.get('is_admin', False) else "否",
                "注册时间": user.get('date_joined', ''),
                "最后登录": user.get('last_login', '未登录'),
                "状态": "活跃" if user.get('is_active', True) else "禁用"
            })
        
        st.table(user_table_data)
    else:
        st.info("无法获取用户列表或列表为空")
    
    # 用户操作区域
    st.write("### 用户操作")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**创建管理员用户**")
        with st.form("create_admin_form"):
            new_admin_username = st.text_input("管理员用户名")
            new_admin_password = st.text_input("密码", type="password")
            create_admin_submitted = st.form_submit_button("创建管理员")
            
            if create_admin_submitted and new_admin_username and new_admin_password:
                # 调用API创建管理员
                response = api_request('POST', 'create_admin', {
                    'username': new_admin_username,
                    'password': new_admin_password
                })
                if response and response.get('status') == 'success':
                    st.success(response.get('message', '管理员创建成功'))
                    st.rerun()
                else:
                    error_msg = response.get('message', '管理员创建失败') if response else '请求失败'
                    st.error(error_msg)
    
    with col2:
        st.write("**用户状态管理**")
        with st.form("user_status_form"):
            target_username = st.text_input("目标用户名")
            action = st.selectbox("操作", ["启用用户", "禁用用户", "重置密码"])
            status_submitted = st.form_submit_button("执行操作")
            
            if status_submitted and target_username:
                st.info(f"功能开发中：{action} - {target_username}")

def run_audit_logs(username: str):
    """审计日志功能"""
    st.subheader("📋 审计日志")
    st.write(f"管理员：**{username}**")
    
    # 验证失败记录
    st.write("### ⚠️ 验证失败记录")
    alert_rows = get_logs_from_api("alert_logs", params={'limit': 10})
    
    if alert_rows:
        for log_entry in alert_rows:
            ts = log_entry.get('timestamp')
            user = log_entry.get('username')
            action = log_entry.get('action')
            live_st = log_entry.get('liveness_status')
            cmp_res = log_entry.get('compare_result')
            score = log_entry.get('score')
            img_path_relative = log_entry.get('image_path')

            st.markdown(f"**[{ts}]**  \n"
                        f"- 用户：{user}   \n"
                        f"- 操作：{action}   \n"
                        f"- 活体状态：{live_st}  \n"
                        f"- 比对结果：{cmp_res or ''}  \n"
                        f"- 得分：{score:.2f}" if score is not None else "- 得分：N/A")
            
            if img_path_relative:
                img_filename = os.path.basename(img_path_relative)
                try:
                    if os.path.isabs(img_path_relative) or len(img_path_relative) > 100:
                        img_url_path = f"failed_faces/{img_filename}"
                    else:
                        img_url_path = img_path_relative.replace(os.sep, '/')
                        if not img_url_path.startswith('failed_faces/'):
                            img_url_path = f"failed_faces/{img_filename}"
                    
                    img_full_url = f"{DJANGO_MEDIA_URL}{img_url_path}"
                    
                    try:
                        st.image(img_full_url, caption=img_filename, width=128)
                    except Exception as img_error:
                        st.warning(f"无法显示图片: {img_filename}")
                        st.text(f"图片路径: {img_full_url}")
                        
                except Exception as e:
                    st.warning(f"图片路径处理失败: {str(e)}")
                    st.text(f"原始路径: {img_path_relative}")
            else:
                st.write("_无对应图片_")
            st.markdown("---")
    else:
        st.info("暂无验证失败记录")

    # 全部审计日志
    limit = st.number_input("显示最近 N 条全部审计日志:", min_value=10, max_value=500, value=50, step=10)
    st.write(f"### 📜 全部审计日志 (最近 {limit} 条)")
    all_rows = get_logs_from_api("audit_logs", params={'limit': limit})

    if all_rows:
        st.table([
            {
                "时间":    log.get('timestamp'),
                "用户":    log.get('username'),
                "操作":    log.get('action'),
                "活体状态": log.get('liveness_status', ''),
                "比对结果": log.get('compare_result', ''),
                "得分":    f"{log.get('score'):.2f}" if log.get('score') is not None else "",
            }
            for log in all_rows
        ])
    else:
        st.info("暂无审计日志")

def api_request(method, endpoint, data=None):
    """API请求辅助函数"""
    api_session = get_api_session()
    url = f"{DJANGO_API_BASE_URL}/{endpoint}/"
    try:
        if method.upper() == 'POST':
            response = api_session.post(url, json=data, timeout=10)
        else:
            response = api_session.get(url, params=data, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API请求失败: {e}")
        return None

def run_admin_panel(username: str, panel_type: str = "audit"):
    """管理员面板主函数"""
    if panel_type == "user_management":
        run_user_management(username)
    else:  # 默认显示审计日志
        run_audit_logs(username)
