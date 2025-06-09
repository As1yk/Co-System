import os
import streamlit as st
import cv2
import numpy as np
from deepface import DeepFace
from tensorflow.keras.models import load_model
from audit_utils import add_audit_log
from datetime import datetime

FAILED_DIR = os.path.join(os.getcwd(), "failed_faces")
os.makedirs(FAILED_DIR, exist_ok=True)

def load_liveness_model(path='anandfinal.hdf5'):
    try:
        model = load_model(path)
        return model, True
    except Exception as e:
        st.warning(f'活体检测模型加载失败: {e}')
        return None, False


def do_face_match(username: str, face_cascade) -> bool:
    """
    只将摄像头采集到的人脸与 faces_database/{username}.jpg 进行一次 verify。
    使用 DeepFace.verify 的位置参数，避免使用 img1/img2 关键字。
    """
    # 1. 读取摄像头一帧
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        st.error("再次采集失败")
        add_audit_log(username, "verify_op", "PASS", "NO_FACE", 0.0)
        return False

    # 2. 探测人脸 ROI
    img = cv2.flip(frame, 1)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))
    if len(faces) == 0:
        st.error("未检测到人脸")
        add_audit_log(username, "verify_op", "PASS", "NO_FACE", 0.0)
        return False

    x, y, w, h = faces[0]
    face_bgr = img[y:y+h, x:x+w]
    face_rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)

    # 3. 定位当前用户的样本照片
    db_path = os.path.join(os.getcwd(), "faces_database")
    identity_img = os.path.join(db_path, f"{username}.jpg")
    if not os.path.isfile(identity_img):
        st.error(f"找不到用户 “{username}” 的库照片：{identity_img}")
        add_audit_log(username, "verify_op", "PASS", "NO_IDENTITY_PHOTO", 0.0)
        return False

    # 4. 调用 DeepFace.verify —— 不要使用 img1= 或 img2= 关键字
    try:
        result = DeepFace.verify(
            face_rgb,                   # 第一个位置参数：待比对图（np.ndarray 或路径）
            identity_img,               # 第二个位置参数：库中图像路径
            enforce_detection=False,
            model_name="Facenet"
        )
    except Exception as e:
        st.error(f"人脸比对出错：{e}")
        add_audit_log(username, "verify_op", "PASS", "ERROR", 0.0)
        return False

    # 5. 解析结果
    verified = result.get("verified", False)
    # DeepFace 返回的距离字段名称各模型可能不同，尝试读取
    distance = result.get("distance", None) or result.get("cosine", None) or 0.0

    # 6. 记录审计并反馈
    compare_result = "MATCH" if verified else "NO_MATCH"
    add_audit_log(username, "verify_op", "PASS", compare_result, float(distance))

    if verified:
        st.success(f"人脸匹配通过 (距离 {distance:.2f})")
        return True
    else:
        st.error(f"身份不符：与 `{username}.jpg` 的距离为 {distance:.2f}")
        return False

def verify_user_identity(username: str,
                         num_votes: int = 10,
                         vote_interval: int = 10,
                         live_threshold: float = 0.5):
    """
    三种返回值：
      - None：尚未点击“开启实时验证”
      - False：验证或匹配执行完毕，但失败
      - True：验证并匹配通过

    流程：
      1. 用户勾选“开启实时验证”后，打开摄像头；
      2. 每隔 vote_interval 帧做一次活体检测，共完成 num_votes 次投票；
      3. 多数票通过后，再做人脸比对。
    """
    st.header("🔒 关键操作身份验证（实时投票）")
    st.write(f"每隔 **{vote_interval}** 帧采样一次，共投票 **{num_votes}** 次；"
             f"活体概率 ≥ {live_threshold:.2f} 计一次通过，多数票通过后继续比对。")

    # ===== 1. 未触发验证前直接返回 None ====
    if not st.checkbox("开启实时验证", key="run_live"):
        return None

    # ===== 2. 活体投票阶段 =====
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        st.error("无法打开摄像头")
        return False

    model, loaded = load_liveness_model()
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    frame_ph = st.empty()
    roi_ph   = st.empty()
    progress = st.progress(0.0)

    total_votes = 0
    pass_votes = 0
    frame_idx = 0

    # 循环投票
    while st.session_state.run_live and total_votes < num_votes:
        ret, frame = cap.read()
        if not ret:
            continue

        frame_idx += 1
        frame_ph.image(frame, channels="BGR", caption=f"实时第 {frame_idx} 帧")

        # 只有采样帧才做活检投票
        if frame_idx % vote_interval != 0:
            continue

        total_votes += 1
        img = cv2.flip(frame, 1)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))

        if len(faces) > 0:
            x, y, w, h = faces[0]
            face_bgr = img[y:y+h, x:x+w]
            face_rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
            face_resized = cv2.resize(face_rgb, (128, 128))
            roi_ph.image(face_resized, caption="人脸 ROI")

            inp = np.expand_dims(face_resized.astype("float32")/255.0, 0)
            if loaded:
                preds = model.predict(inp)[0]
                prob_live = float(preds[1] if preds.shape[-1]==2 else preds[0])
            else:
                prob_live = 0.0

            if prob_live >= live_threshold:
                pass_votes += 1

        progress.progress(total_votes / num_votes)

    cap.release()
    progress.empty()
    frame_ph.empty()
    roi_ph.empty()

    required = (num_votes // 2) + 1
    liveness_status = "PASS" if pass_votes >= required else "FAIL"
    st.write(f"活体验证：{pass_votes}/{num_votes} → **{liveness_status}**")

    # 记录活检审计
    add_audit_log(username, "verify_op",
                  liveness_status,
                  "SKIPPED" if liveness_status == "FAIL" else None,
                  score=pass_votes / num_votes)

    if liveness_status != "PASS":
        # 保存最后一帧的 face_resized
        ts_file = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{username}_{ts_file}_liveness_fail.jpg"
        path = os.path.join(FAILED_DIR, filename)
        # face_resized 必须在这作用域可访问
        cv2.imwrite(path, cv2.cvtColor(face_resized, cv2.COLOR_RGB2BGR))

        add_audit_log(username, "verify_op",
                      liveness_status,
                      "SKIPPED",
                      score=pass_votes / num_votes,
                      image_path=path)
        st.error("活体验证未通过，请重试。")
        return False

    # ===== 3. 人脸比对阶段 =====
    st.success("活体验证通过，开始人脸匹配…")
    return do_face_match(username, face_cascade)





def run_recognition(username: str):
    st.title('普通用户操作界面')

    result = verify_user_identity(username)
    if result is None:
        # 尚未触发验证，什么也不做
        return
    elif result is False:
        # 验证/匹配已执行，但失败
        st.error('验证失败，无法继续操作。')
        return
    else:
        # result == True，验证通过
        st.success('身份验证完成，可执行操作。')




def run_admin(username: str):
    """
    管理员界面：仅查看审计日志
    """
    import pandas as pd
    import sqlite3
    st.title('管理员审计日志查看')
    conn = sqlite3.connect('users.db',check_same_thread=False)
    df = pd.read_sql_query('SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100;', conn)
    st.dataframe(df)
    conn.close()