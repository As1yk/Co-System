import os
import streamlit as st
import cv2
import numpy as np
from deepface import DeepFace
from tensorflow.keras.models import load_model
from audit_utils import add_audit_log


def load_liveness_model(path='anandfinal.hdf5'):
    try:
        model = load_model(path)
        return model, True
    except Exception as e:
        st.warning(f'活体检测模型加载失败: {e}')
        return None, False


def do_face_match(username: str, face_cascade) -> bool:
    """
    采集一帧并用 DeepFace 做一次人脸匹配，返回 True/False。
    """
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        st.error("再次采集失败")
        add_audit_log(username, "verify_op", "PASS", "NO_FACE", 0.0)
        return False

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

    results = DeepFace.find(
        face_rgb,
        db_path=os.path.join(os.getcwd(), "faces_database"),
        enforce_detection=False,
        model_name="Facenet"
    )
    df = results[0] if isinstance(results, list) else results
    if df is None or df.empty:
        st.error("人脸库中未找到匹配")
        add_audit_log(username, "verify_op", "PASS", "NO_MATCH", 0.0)
        return False

    dist_col = [c for c in df.columns if "distance" in c or "cosine" in c][0]
    best = df.sort_values(by=dist_col).iloc[0]
    match_name = os.path.splitext(os.path.basename(best["identity"]))[0]
    score = float(best[dist_col])
    compare = "MATCH" if match_name == username else "NO_MATCH"

    add_audit_log(username, "verify_op", "PASS", compare, score)
    if compare == "MATCH":
        st.success(f"人脸匹配通过：匹配到 {match_name} (得分 {score:.2f})")
        return True
    else:
        st.error(f"身份不符：匹配到 {match_name} (得分 {score:.2f})")
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