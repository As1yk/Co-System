# admin_ui.py

import streamlit as st
import requests
import pandas as pd
from config import Config
import json
from datetime import datetime

config = Config()

def run_admin_panel(username, selected_function="user_management"):
    """运行管理员面板 - 主入口函数"""
    show_admin_panel(username, selected_function)

def show_admin_panel(username=None, selected_function="user_management"):
    """显示管理员面板"""
    
    if username:
        st.title(f"🔧 管理员控制面板 - {username}")
    else:
        st.title("🔧 管理员控制面板")
    
    # 根据选择的功能显示对应界面
    if selected_function == "user_management":
        show_user_management_section()
    elif selected_function == "audit_logs":
        show_audit_logs_section()
    else:
        # 默认显示用户管理
        show_user_management_section()

def show_user_management_section():
    """显示用户管理部分"""
    # 创建子标签页
    tab1, tab2 = st.tabs(["👥 用户管理", "🗑️ 删除用户"])
    
    with tab1:
        show_user_management()
    
    with tab2:
        show_user_deletion()

def show_audit_logs_section():
    """显示审计日志部分"""
    # 创建子标签页
    tab1, tab2 = st.tabs(["📊 审计日志", "❌ 失败记录"])
    
    with tab1:
        show_audit_logs()
    
    with tab2:
        show_failed_records()

def show_user_management():
    """显示用户管理"""
    st.subheader("👥 用户管理")
    
    # 获取用户列表
    try:
        response = st.session_state.requests_session.get(f"{config.DJANGO_API_URL}/users/")
        
        if response.status_code == 200:
            data = response.json()
            users = data.get('users', [])
            
            if users:
                # 显示用户统计
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("总用户数", len(users))
                with col2:
                    admin_count = sum(1 for user in users if user.get('is_admin'))
                    st.metric("管理员数", admin_count)
                with col3:
                    active_count = sum(1 for user in users if user.get('is_active'))
                    st.metric("活跃用户", active_count)
                
                # 用户列表表格
                df = pd.DataFrame(users)
                st.dataframe(
                    df[['username', 'email', 'is_admin', 'date_joined', 'last_login', 'is_active']],
                    use_container_width=True
                )
                
                # 创建新管理员
                st.subheader("➕ 创建新管理员")
                with st.form("create_admin_form"):
                    new_admin_username = st.text_input("管理员用户名")
                    new_admin_password = st.text_input("管理员密码", type="password")
                    create_admin_btn = st.form_submit_button("创建管理员", type="primary")
                    
                    if create_admin_btn:
                        if new_admin_username and new_admin_password:
                            try:
                                create_admin_response = st.session_state.requests_session.post(
                                    f"{config.DJANGO_API_URL}/create_admin/",
                                    json={
                                        'username': new_admin_username,
                                        'password': new_admin_password
                                    },
                                    headers={'Content-Type': 'application/json'}
                                )
                                
                                if create_admin_response.status_code == 200:
                                    result = create_admin_response.json()
                                    if result.get('status') == 'success':
                                        st.success("✅ 管理员创建成功！")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ 创建失败: {result.get('message')}")
                                else:
                                    st.error(f"❌ 服务器连接失败，状态码: {create_admin_response.status_code}")
                            except Exception as e:
                                st.error(f"❌ 请求失败: {str(e)}")
                        else:
                            st.error("❌ 请填写完整信息")
            else:
                st.info("暂无用户数据")
        else:
            st.error(f"❌ 无法获取用户列表，状态码: {response.status_code}")
    except Exception as e:
        st.error(f"❌ 获取用户信息失败: {str(e)}")

def show_user_deletion():
    """显示用户删除功能"""
    st.subheader("🗑️ 删除用户")
    
    # 获取所有用户列表
    try:
        response = st.session_state.requests_session.get(f"{config.DJANGO_API_URL}/users/")
        
        if response.status_code == 200:
            data = response.json()
            users = data.get('users', [])
            
            if not users:
                st.info("暂无用户")
                return
            
            # 显示所有用户供删除
            st.write("**选择要删除的用户：**")
            
            for i, user in enumerate(users):
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.write(f"👤 **{user['username']}**")
                        st.write(f"注册时间: {user.get('date_joined', 'N/A')}")
                    
                    with col2:
                        status = "🟢 管理员" if user.get('is_admin') else "🔴 普通用户"
                        st.write(f"状态: {status}")
                    
                    with col3:
                        # 使用唯一的key
                        delete_key = f"delete_user_{i}_{user['username']}"
                        confirm_key = f"confirm_delete_{i}_{user['username']}"
                        
                        if st.button("🗑️ 删除", key=delete_key, type="secondary"):
                            st.session_state[confirm_key] = True
                            st.rerun()
                    
                    # 显示确认删除提示
                    if st.session_state.get(confirm_key, False):
                        st.warning(f"⚠️ 确认删除用户 **{user['username']}** 吗？此操作不可恢复！")
                        
                        col_confirm, col_cancel = st.columns(2)
                        
                        with col_confirm:
                            confirm_yes_key = f"confirm_yes_{i}_{user['username']}"
                            if st.button("✅ 确认删除", key=confirm_yes_key, type="primary"):
                                # 执行删除
                                try:
                                    delete_response = st.session_state.requests_session.delete(
                                        f"{config.DJANGO_API_URL}/delete_user/",
                                        json={'username': user['username']},
                                        headers={'Content-Type': 'application/json'}
                                    )
                                    
                                    if delete_response.status_code == 200:
                                        result = delete_response.json()
                                        if result.get('success'):
                                            st.success(f"✅ 用户 {user['username']} 删除成功！")
                                            # 清除确认状态
                                            if confirm_key in st.session_state:
                                                del st.session_state[confirm_key]
                                            st.rerun()
                                        else:
                                            st.error(f"❌ 删除失败: {result.get('message')}")
                                    else:
                                        st.error(f"❌ 服务器连接失败，状态码: {delete_response.status_code}")
                                except Exception as e:
                                    st.error(f"❌ 请求异常: {str(e)}")
                        
                        with col_cancel:
                            cancel_key = f"confirm_no_{i}_{user['username']}"
                            if st.button("❌ 取消", key=cancel_key):
                                # 清除确认状态
                                if confirm_key in st.session_state:
                                    del st.session_state[confirm_key]
                                st.rerun()
                    
                    st.divider()
            
            # 批量删除功能
            st.subheader("🗑️ 批量删除")
            
            # 多选框选择用户
            selected_users = st.multiselect(
                "选择要批量删除的用户：",
                options=[user['username'] for user in users],
                format_func=lambda x: f"👤 {x}",
                key="batch_delete_multiselect"
            )
            
            if selected_users:
                st.write(f"已选择 {len(selected_users)} 个用户进行删除")
                
                col_batch, col_clear = st.columns([1, 1])
                
                with col_batch:
                    if st.button("🗑️ 批量删除选中用户", key="batch_delete_btn", type="primary"):
                        success_count = 0
                        failed_users = []
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        for idx, username in enumerate(selected_users):
                            status_text.text(f"正在删除用户: {username}")
                            progress_bar.progress((idx + 1) / len(selected_users))
                            
                            try:
                                delete_response = requests.delete(
                                    f"{config.DJANGO_API_URL}/delete_user/",
                                    json={'username': username},
                                    headers={'Content-Type': 'application/json'}
                                )
                                
                                if delete_response.status_code == 200:
                                    result = delete_response.json()
                                    if result.get('success'):
                                        success_count += 1
                                    else:
                                        failed_users.append(f"{username}: {result.get('message')}")
                                else:
                                    failed_users.append(f"{username}: 服务器连接失败 (状态码: {delete_response.status_code})")
                            except Exception as e:
                                failed_users.append(f"{username}: 请求异常 ({str(e)})")
                        
                        # 显示结果
                        status_text.empty()
                        progress_bar.empty()
                        
                        if success_count > 0:
                            st.success(f"✅ 成功删除 {success_count} 个用户")
                        
                        if failed_users:
                            st.error("❌ 以下用户删除失败：")
                            for error in failed_users:
                                st.write(f"• {error}")
                        
                        if success_count > 0:
                            st.rerun()
                
                with col_clear:
                    if st.button("🔄 清空选择", key="clear_selection_btn"):
                        st.rerun()
        else:
            st.error(f"❌ 无法获取用户列表，状态码: {response.status_code}")
    except Exception as e:
        st.error(f"❌ 获取用户信息失败: {str(e)}")

def show_audit_logs():
    """显示审计日志"""
    st.subheader("📊 审计日志")
    
    try:
        response = st.session_state.requests_session.get(f"{config.DJANGO_API_URL}/audit_logs/")
        
        if response.status_code == 200:
            data = response.json()
            logs = data.get('logs', [])
            
            if logs:
                # 显示日志统计
                df = pd.DataFrame(logs)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("总记录数", len(logs))
                with col2:
                    success_count = len([log for log in logs if log.get('liveness_status') == 'PASS'])
                    st.metric("成功识别", success_count)
                
                # 显示日志表格
                st.dataframe(df, use_container_width=True)
            else:
                st.info("暂无审计日志")
        else:
            st.error("❌ 无法获取审计日志")
    except Exception as e:
        st.error(f"❌ 获取审计日志失败: {str(e)}")

def show_failed_records():
    """显示失败记录"""
    st.subheader("❌ 识别失败记录")
    
    try:
        response = st.session_state.requests_session.get(f"{config.DJANGO_API_URL}/alert_logs/")
        
        if response.status_code == 200:
            data = response.json()
            logs = data.get('logs', [])
            
            if logs:
                st.warning(f"⚠️ 发现 {len(logs)} 条失败记录")
                
                # 显示失败记录表格
                df = pd.DataFrame(logs)
                st.dataframe(df, use_container_width=True)
            else:
                st.success("✅ 暂无失败记录")
        else:
            st.error("❌ 无法获取失败记录")
    except Exception as e:
        st.error(f"❌ 获取失败记录失败: {str(e)}")
