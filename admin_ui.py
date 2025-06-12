# admin_ui.py

import streamlit as st
import requests
import os
import json # 用于解析可能的错误响应

# Django API base URL
DJANGO_API_BASE_URL = "http://127.0.0.1:8000/api"
# Django media URL (如果图片由 Django 服务)
DJANGO_MEDIA_URL = "http://127.0.0.1:8000/media/" # 假设 failed_faces 在 media 下

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
            return data.get('logs', [])
        else:
            st.error(f"API 获取日志失败: {data.get('message', '未知错误')}")
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"请求 API ({url}) 失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                st.error(f"错误详情: {e.response.json()}")
            except json.JSONDecodeError:
                 st.error(f"错误详情 (非JSON): {e.response.text}")
        return []
    except json.JSONDecodeError:
        st.error(f"无法解析来自 {url} 的 API 响应。")
        return []


def run_admin_panel(username: str):
    st.title("🛠 管理员面板")
    st.write(f"当前管理员：**{username}**")

    st.subheader("⚠️ 验证失败记录 (来自 API)")
    alert_rows = get_logs_from_api("alert_logs", params={'limit': 10})
    
    if alert_rows:
        for log_entry in alert_rows:
            ts = log_entry.get('timestamp')
            user = log_entry.get('username')
            action = log_entry.get('action')
            live_st = log_entry.get('liveness_status')
            cmp_res = log_entry.get('compare_result')
            score = log_entry.get('score')
            img_path_relative = log_entry.get('image_path') # 这是相对于 Django MEDIA_ROOT 的路径

            st.markdown(f"**[{ts}]**  \n"
                        f"- 用户：{user}   \n"
                        f"- 操作：{action}   \n"
                        f"- 活体状态：{live_st}  \n"
                        f"- 比对结果：{cmp_res or ''}  \n"
                        f"- 得分：{score:.2f}" if score is not None else "- 得分：N/A")
            
            if img_path_relative:
                # 构建完整的图片 URL，假设图片存储在 Django 项目的 media/failed_faces/ 目录下
                # 并且 settings.py 中的 MEDIA_URL 和 MEDIA_ROOT 配置正确
                # img_full_url = f"{DJANGO_MEDIA_URL}{img_path_relative.replace(os.path.join(settings.BASE_DIR, 'failed_faces'), 'failed_faces')}"

                img_filename = os.path.basename(img_path_relative)
                
                # 如果 image_path 是绝对路径，并且 Streamlit 和 Django 在同一台机器上可以直接访问
                # local_image_path = img_path_relative # 如果 image_path 是绝对路径
                # if os.path.isfile(local_image_path):
                #    st.image(local_image_path, width=128)
                # else:
                #    st.write(f"_图片本地路径未找到: {local_image_path}_ (尝试API路径)")
                #    st.write(f"尝试从 API 获取图片: {img_full_url}")
                #    st.image(img_full_url, width=128) # Streamlit 可以直接显示 URL
                
                # 假设 img_path_relative 是相对于 Django 项目根目录的路径，如 "failed_faces/user_timestamp_liveness_fail.jpg"
                # 并且 Django 的 MEDIA_URL 设置为 '/media/'，MEDIA_ROOT 指向 'media' 文件夹
                # 那么图片URL应该是 'http://host:port/media/failed_faces/filename.jpg'
                # 如果 settings.FAILED_DIR_PATH 是 '.../Co-System/failed_faces'
                # 而 settings.BASE_DIR 是 '.../Co-System'
                # 那么 img_path_relative 可能是 '.../Co-System/failed_faces/filename.jpg'
                # 我们需要将其转换为相对于 MEDIA_ROOT 的路径
                
                # 假设 api.utils_recognition.py 中保存的 image_path 是相对于 settings.FAILED_DIR_PATH 的文件名
                # e.g., "username_timestamp_liveness_fail.jpg"
                # 并且 settings.FAILED_DIR_PATH 是 settings.MEDIA_ROOT / "failed_faces"
                # 那么 img_url = DJANGO_MEDIA_URL + "failed_faces/" + os.path.basename(img_path_relative)
                
                # 简化：假设 img_path_relative 是可以直接附加到 MEDIA_URL 的部分
                # 例如，如果 img_path_relative 是 "failed_faces/image.jpg"
                # 并且 MEDIA_URL 是 "/media/", 则完整 URL 是 "/media/failed_faces/image.jpg"
                # 在此示例中，api.utils_recognition.py 保存的是完整路径，这对于跨服务显示不理想。
                # 理想情况下，应保存相对于 MEDIA_ROOT 的路径。
                # 假设 image_path 是 settings.FAILED_DIR_PATH 下的文件名
                
                # 修正：假设 image_path 在 AuditLog 中存储的是相对于 MEDIA_ROOT 的路径
                # 例如 "failed_faces/some_image.jpg"
                if img_path_relative.startswith(str(settings.BASE_DIR)): # 如果是绝对路径
                    relative_to_base = os.path.relpath(img_path_relative, settings.BASE_DIR)
                    # 假设 media 文件夹在 BASE_DIR 下，并且 failed_faces 在 media 下
                    if relative_to_base.startswith("media"):
                         img_url_path = relative_to_base
                    else: # 尝试直接使用文件名，并假设在 media/failed_faces/ 下
                         img_url_path = f"failed_faces/{os.path.basename(img_path_relative)}"
                else: # 已经是相对路径
                    img_url_path = img_path_relative

                img_full_url = f"{DJANGO_MEDIA_URL}{img_url_path.replace(os.sep, '/')}"
                st.image(img_full_url, caption=os.path.basename(img_path_relative), width=128)
            else:
                st.write("_无对应图片_")
            st.markdown("---")
    else:
        st.info("暂无带失败人脸图的告警 (来自 API)。")

    limit = st.number_input("显示最近 N 条全部审计日志:", min_value=10, max_value=500, value=50, step=10)
    st.subheader(f"📜 全部审计日志 (最近 {limit} 条, 来自 API)")
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
        st.info("暂无审计日志 (来自 API)。")
