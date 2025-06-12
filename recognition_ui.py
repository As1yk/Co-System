import os
import streamlit as st
import cv2
import numpy as np
from deepface import DeepFace
from tensorflow.keras.models import load_model
from datetime import datetime
import time # 确保导入 time

# --- Global Setup ---
FAILED_DIR = os.path.join(os.getcwd(), "failed_faces")
os.makedirs(FAILED_DIR, exist_ok=True)

# 模拟 audit_utils.add_audit_log 如果它不存在
# 如果您有 audit_utils.py，请确保它能被正确导入，或者取消注释真实的导入
# from audit_utils import add_audit_log
if 'add_audit_log' not in globals():
    def add_audit_log(username, operation, status, match_result=None, score=0.0, image_path=None, details=None):
        # 在实际应用中，这里会写入数据库或日志文件
        log_message = (
            f"AUDIT LOG (mock): Timestamp={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, "
            f"User={username}, Operation={operation}, Status={status}"
        )
        if match_result:
            log_message += f", MatchResult={match_result}"
        if score is not None: # score 可以是 0.0
            log_message += f", Score={score:.4f}"
        if image_path:
            log_message += f", ImagePath={image_path}"
        if details:
            log_message += f", Details={details}"
        print(log_message)
        pass

# --- Model Loading with Streamlit Cache ---
@st.cache_resource
def load_liveness_model_cached(path='anandfinal.hdf5'): # anandfinal.hdf5 是您原始代码中的模型名
    try:
        model = load_model(path)
        print("INFO: Liveness model loaded successfully.") # 打印到控制台供调试
        return model, True
    except Exception as e:
        print(f"ERROR: Liveness model loading failed: {e}")
        return None, False

@st.cache_resource
def load_face_cascade_cached():
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    if not os.path.exists(cascade_path):
        print(f"ERROR: Haar cascade file not found at {cascade_path}")
        return None # 返回 None 以便后续检查
    face_cascade = cv2.CascadeClassifier(cascade_path)
    if face_cascade.empty():
        print(f"ERROR: Failed to load Haar cascade from {cascade_path}")
        return None # 返回 None
    print("INFO: Face cascade loaded successfully.")
    return face_cascade

# --- Core Functions (Modified from your original version) ---
def do_face_match(username: str, face_cascade, captured_face_rgb) -> bool:
    """
    将传入的已捕获人脸 (captured_face_rgb) 与数据库中的照片进行比对。
    """
    # 增强的输入验证
    if captured_face_rgb is None:
        st.error("人脸比对失败：未提供人脸图像。")
        add_audit_log(username, "face_match_op", "FAIL", "NULL_INPUT_FACE", 0.0)
        return False
    
    if not isinstance(captured_face_rgb, np.ndarray):
        st.error("人脸比对失败：输入的人脸图像格式无效。")
        add_audit_log(username, "face_match_op", "FAIL", "INVALID_INPUT_FORMAT", 0.0)
        return False
    
    if captured_face_rgb.size == 0 or len(captured_face_rgb.shape) != 3:
        st.error("人脸比对失败：输入的人脸图像尺寸无效。")
        add_audit_log(username, "face_match_op", "FAIL", "INVALID_INPUT_SHAPE", 0.0)
        return False

    # 1. 定位当前用户的样本照片
    db_path = os.path.join(os.getcwd(), "faces_database")
    identity_img_path = os.path.join(db_path, f"{username}.jpg")
    if not os.path.isfile(identity_img_path):
        st.error(f"找不到用户 \"{username}\" 的库照片：{identity_img_path}")
        add_audit_log(username, "face_match_op", "FAIL", "NO_IDENTITY_PHOTO", 0.0)
        return False

    # 2. 使用临时文件方式处理Unicode路径问题
    try:
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        
        # 为当前捕获的人脸创建临时文件
        temp_current_face_filename = f"temp_current_face_{temp_timestamp}.jpg"
        temp_current_face_path = os.path.join(temp_dir, temp_current_face_filename)
        
        # 为数据库中的身份照片创建临时文件
        temp_identity_face_filename = f"temp_identity_face_{temp_timestamp}.jpg"
        temp_identity_face_path = os.path.join(temp_dir, temp_identity_face_filename)
        
        # 保存当前捕获的人脸到临时文件
        if captured_face_rgb.shape[2] == 3:  # RGB格式
            face_bgr_for_save = cv2.cvtColor(captured_face_rgb, cv2.COLOR_RGB2BGR)
        else:
            face_bgr_for_save = captured_face_rgb  # 假设已经是BGR
        
        is_success, im_buf_arr = cv2.imencode(".jpg", face_bgr_for_save)
        if not is_success:
            st.error("当前人脸图像编码失败")
            add_audit_log(username, "face_match_op", "FAIL", "CURRENT_FACE_ENCODE_FAILED", 0.0)
            return False
        
        with open(temp_current_face_path, "wb") as f:
            f.write(im_buf_arr.tobytes())

        # 读取并复制数据库中的身份照片到临时文件，以处理Unicode路径
        try:
            # 使用cv2.imdecode读取身份照片，避免Unicode路径问题
            with open(identity_img_path, 'rb') as f:
                identity_img_bytes = f.read()
            identity_img_array = cv2.imdecode(np.frombuffer(identity_img_bytes, np.uint8), cv2.IMREAD_COLOR)
            
            if identity_img_array is None:
                st.error(f"无法解码数据库中的身份照片：{identity_img_path}")
                add_audit_log(username, "face_match_op", "FAIL", "IDENTITY_PHOTO_DECODE_FAILED", 0.0)
                return False
            
            # 将身份照片保存到临时文件
            is_success_identity, identity_buf_arr = cv2.imencode(".jpg", identity_img_array)
            if not is_success_identity:
                st.error("身份照片编码失败")
                add_audit_log(username, "face_match_op", "FAIL", "IDENTITY_PHOTO_ENCODE_FAILED", 0.0)
                return False
            
            with open(temp_identity_face_path, "wb") as f:
                f.write(identity_buf_arr.tobytes())
                
        except Exception as e_identity:
            st.error(f"处理身份照片时出错：{e_identity}")
            add_audit_log(username, "face_match_op", "FAIL", "IDENTITY_PHOTO_PROCESSING_ERROR", 0.0, details=str(e_identity))
            return False

        # 3. 调用 DeepFace.verify，现在使用两个临时文件路径
        result = DeepFace.verify(
            img1_path=temp_current_face_path,    # 临时保存的当前人脸
            img2_path=temp_identity_face_path,   # 临时保存的身份照片
            enforce_detection=False,
            model_name="Facenet"
        )
        
        # 清理临时文件
        try:
            os.remove(temp_current_face_path)
            os.remove(temp_identity_face_path)
        except:
            pass  # 忽略清理失败
            
    except Exception as e:
        st.error(f"人脸比对出错：{e}")
        add_audit_log(username, "face_match_op", "FAIL", "ERROR_IN_DEEPFACE", 0.0, details=str(e))
        # 尝试清理临时文件
        try:
            if 'temp_current_face_path' in locals():
                os.remove(temp_current_face_path)
            if 'temp_identity_face_path' in locals():
                os.remove(temp_identity_face_path)
        except:
            pass
        return False

    # 4. 解析结果
    verified = result.get("verified", False)
    distance = result.get("distance", 0.0)

    # 5. 记录审计并反馈
    compare_result = "MATCH" if verified else "NO_MATCH"
    add_audit_log(username, "face_match_op", "PASS" if verified else "FAIL", compare_result, float(distance))

    if verified:
        st.success(f"人脸匹配通过 (距离 {distance:.2f})")
        return True
    else:
        st.error(f"身份不符：与库中照片的距离为 {distance:.2f}")
        # 保存匹配失败时的图像
        ts_file = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{username}_{ts_file}_facematch_fail.jpg"
        path = os.path.join(FAILED_DIR, filename)
        try:
            # 使用健壮的方式保存图像，以处理Unicode路径
            image_bgr_to_save = cv2.cvtColor(captured_face_rgb, cv2.COLOR_RGB2BGR)
            is_success, im_buf_arr = cv2.imencode(".jpg", image_bgr_to_save)
            if is_success:
                with open(path, "wb") as f_byte:
                    f_byte.write(im_buf_arr.tobytes())
                add_audit_log(username, "face_match_op", "FAIL", "NO_MATCH_IMG_SAVED", float(distance), image_path=path)
            else:
                print(f"Error: cv2.imencode failed for face match fail image: {path}")
        except Exception as e_save:
            print(f"Error saving face match fail image to {path}: {e_save}")
        return False

def verify_user_identity(username: str,
                         num_votes: int = 10,
                         vote_interval: int = 10, # 这是您原始代码中的参数名 (帧数间隔)
                         live_threshold: float = 0.5):
    """
    使用 cv2.VideoCapture 实现自动抓帧进行活体检测和人脸比对。
    UI元素居中显示。
    """
    # 使用列来居中主要UI元素
    col_ui_1, col_ui_2, col_ui_3 = st.columns([1, 3, 1]) # 左右留白，中间内容区

    with col_ui_2:
        st.header("🔒 关键操作身份验证（实时投票）")
        st.write(f"每隔 **{vote_interval}** 帧采样一次，共投票 **{num_votes}** 次；"
                 f"活体概率 ≥ {live_threshold:.2f} 计一次通过，多数票通过后继续比对。")

        # 使用与您原始代码一致的 st.checkbox 和 session_state key "run_live"
        # 为了确保状态正确更新，尤其是在回调中，可以这样管理checkbox状态
        if 'run_live' not in st.session_state:
            st.session_state.run_live = False
        
        run_live_checkbox = st.checkbox("开启实时验证", key="run_live_cb", value=st.session_state.run_live,
                                        on_change=lambda: setattr(st.session_state, 'run_live', st.session_state.run_live_cb))

        if not st.session_state.run_live:
            return None # 未开启验证，或用户取消勾选

        # ===== 活体投票阶段 =====
        model, loaded = load_liveness_model_cached()
        face_cascade = load_face_cascade_cached()

        if face_cascade is None: # 检查级联分类器是否加载成功
            st.error("人脸检测级联分类器加载失败。无法进行验证。")
            st.session_state.run_live = False # 重置checkbox
            return False
        if not loaded:
            st.error("活体检测模型未能加载，无法进行验证。")
            st.session_state.run_live = False # 重置checkbox
            return False

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            st.error("无法打开摄像头")
            st.session_state.run_live = False # 重置checkbox
            return False

        frame_ph = st.empty()
        roi_ph   = st.empty()
        status_ph = st.empty()
        progress = st.progress(0.0)

        total_votes = 0
        pass_votes = 0
        frame_idx = 0
        last_valid_face_rgb = None
        face_resized_for_save_on_fail = None # 用于保存失败时的图像

        try:
            while st.session_state.run_live and total_votes < num_votes: # 检查 st.session_state.run_live
                ret, frame = cap.read()
                if not ret:
                    status_ph.warning("无法从摄像头读取帧...")
                    time.sleep(0.1)
                    continue

                frame_idx += 1
                display_frame = cv2.flip(frame, 1) # 翻转用于显示
                frame_ph.image(display_frame, channels="BGR", caption=f"实时第 {frame_idx} 帧")

                if frame_idx % vote_interval != 0:
                    continue

                total_votes += 1
                status_ph.info(f"正在进行第 {total_votes}/{num_votes} 次活体检测...")
                
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # 使用原始帧进行检测
                faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))

                current_vote_passed = False
                if len(faces) > 0:
                    x, y, w, h = faces[0]
                    face_bgr_roi = frame[y:y+h, x:x+w] # 从原始帧提取ROI
                    face_rgb_roi = cv2.cvtColor(face_bgr_roi, cv2.COLOR_BGR2RGB)
                    face_resized_for_liveness = cv2.resize(face_rgb_roi, (128, 128))
                    
                    display_roi_preview = cv2.flip(face_bgr_roi, 1) # 翻转ROI用于显示
                    roi_ph.image(display_roi_preview, channels="BGR", caption="检测到的人脸区域 (ROI)")

                    last_valid_face_rgb = face_rgb_roi # 保存RGB格式用于后续匹配
                    face_resized_for_save_on_fail = face_resized_for_liveness # 保存这张用于可能失败时的记录

                    inp = np.expand_dims(face_resized_for_liveness.astype("float32")/255.0, 0)
                    preds = model.predict(inp, verbose=0)[0]
                    prob_live = float(preds[0]) # 假设 preds[0] 总是活体概率
                    
                    if prob_live >= live_threshold:
                        pass_votes += 1
                        current_vote_passed = True
                    status_ph.info(f"第 {total_votes} 次投票: 活体概率 {prob_live:.2f} ({'通过' if current_vote_passed else '失败'})")
                else:
                    roi_ph.warning("未检测到人脸")
                    last_valid_face_rgb = None # 本次未检测到，清除
                    status_ph.info(f"第 {total_votes} 次投票: 未检测到人脸")

                progress.progress(total_votes / num_votes)
                # time.sleep(0.01) # 可选：轻微延时控制帧率，减少CPU占用

        finally:
            cap.release()
            progress.empty()
            status_ph.empty() # 清除状态文本，避免在结果出来后还显示旧状态

        # 检查是否是用户中途取消勾选导致的循环结束
        if not st.session_state.run_live and total_votes < num_votes:
             st.warning("验证已取消。")
             # frame_ph.empty() # 清理图像占位符
             # roi_ph.empty()
             return None

        required = (num_votes // 2) + 1
        liveness_status = "PASS" if pass_votes >= required else "FAIL"
        st.write(f"活体验证：{pass_votes}/{num_votes} → **{liveness_status}**")

        add_audit_log(username, "liveness_check_op",
                      liveness_status,
                      "SKIPPED_FACE_MATCH" if liveness_status == "FAIL" else None,
                      score= (pass_votes / num_votes) if num_votes > 0 else 0.0)

        if liveness_status != "PASS":
            if face_resized_for_save_on_fail is not None:
                ts_file = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{username}_{ts_file}_liveness_fail.jpg"
                path = os.path.join(FAILED_DIR, filename)
                try:
                    image_bgr_to_save = cv2.cvtColor(face_resized_for_save_on_fail, cv2.COLOR_RGB2BGR)
                    is_success, im_buf_arr = cv2.imencode(".jpg", image_bgr_to_save)
                    if is_success:
                        with open(path, "wb") as f_byte:
                            f_byte.write(im_buf_arr.tobytes())
                        add_audit_log(username, "liveness_check_op", "FAIL_IMG_SAVED", image_path=path)
                    else:
                        print(f"Error: cv2.imencode failed for liveness fail image: {path}")
                        add_audit_log(username, "liveness_check_op", "FAIL_IMG_ENCODE_FAIL", image_path=None)
                    add_audit_log(username, "liveness_check_op", "FAIL_IMG_SAVED", image_path=path)
                except Exception as e_save_img:
                    print(f"Error saving liveness fail image: {e_save_img}")
            st.error("活体验证未通过，请重试。")
            st.session_state.run_live = False # 流程结束，取消勾选框
            return False

        if last_valid_face_rgb is None:
            st.error("活体验证通过，但在有效检测中未能捕获到清晰人脸用于比对。请重试。")
            st.session_state.run_live = False
            return False
            
        st.info("活体验证通过，开始人脸匹配…") # 显示在主内容区
        match_result = do_face_match(username, face_cascade, last_valid_face_rgb)
        st.session_state.run_live = False # 流程结束，取消勾选框
        return match_result


# --- Main UI Function (from your original version) ---
def run_recognition(username: str):
    st.title('普通用户操作界面') # Streamlit 默认标题是左对齐或根据主题

    # 调用核心验证函数
    result = verify_user_identity(
        username, 
        num_votes=10, 
        vote_interval=5, # 您原始代码中的示例值
        live_threshold=0.6 # 您可以调整此阈值
    )
    
    # 根据验证结果显示最终信息 (这部分会在 verify_user_identity 的 st.columns 之外显示)
    if result is None:
        # verify_user_identity 内部已经有提示，这里可以不重复，或者添加一个更通用的提示
        # st.info("请勾选“开启实时验证”以开始身份验证流程。")
        pass
    elif result is False:
        # verify_user_identity 内部已经显示了具体的错误信息
        # st.error('❌ 身份验证失败。请检查提示信息并重试。')
        pass
    else: # result is True
        # verify_user_identity 内部已经显示了成功信息
        # st.success('✅ 身份验证成功！您可以继续操作。')
        pass

# --- Admin Function (from your original version, with minor path check) ---
def run_admin(username: str):
    import pandas as pd
    import sqlite3
    st.title('管理员审计日志查看')
    db_file_path = os.path.join(os.getcwd(), "users.db") 
    if not os.path.exists(db_file_path):
        st.error(f"数据库文件 users.db 未找到于: {db_file_path}")
        return
        
    conn = sqlite3.connect(db_file_path, check_same_thread=False)
    try:
        df = pd.read_sql_query('SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100;', conn)
        # 使用 st.columns 来居中 dataframe
        col_df1, col_df2, col_df3 = st.columns([0.5, 3, 0.5]) # 调整比例以获得合适的宽度
        with col_df2:
            st.dataframe(df, use_container_width=True) # use_container_width 使其填满列宽
    except Exception as e:
        st.error(f"查询审计日志失败: {e}")
    finally:
        conn.close()