import os
import sys
import sqlite3
import hashlib
import streamlit as st
from deepface import DeepFace
import cv2
import numpy as np
from PIL import Image
from tensorflow.keras.models import load_model

# ======================
# —— 1. SQLite 配置 & 辅助函数
# ======================
DB_PATH = "users.db"  # SQLite 数据库文件

def get_db_connection():
    """
    获取 SQLite 连接，若数据库不存在会自动创建。
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

def init_user_table():
    """
    初始化用户表，若不存在则创建。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    """
    对密码进行 SHA-256 哈希，返回十六进制字符串。
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def add_user(username: str, password: str) -> bool:
    """
    尝试向 users 表插入新用户，返回 True 表示成功，False 表示用户名已存在或其他错误。
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        password_hash = hash_password(password)
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?);",
                       (username, password_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # 用户名已存在
        return False
    finally:
        conn.close()

def verify_user(username: str, password: str) -> bool:
    """
    验证用户名和密码是否匹配，返回 True 表示匹配，False 表示不匹配或不存在。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE username = ?;", (username,))
    row = cursor.fetchone()
    conn.close()
    if row:
        stored_hash = row[0]
        return stored_hash == hash_password(password)
    return False

# 在应用启动时，确保用户表已创建
init_user_table()

# ======================
# —— 2. Liveness 模型加载
# ======================
liveness_model_path = "anandfinal.hdf5"

try:
    liveness_model = load_model(liveness_model_path)
    model_loaded = True
except Exception as e:
    liveness_model = None
    model_loaded = False
    st.warning(f"无法加载活体检测模型，请检查 {liveness_model_path}：{e}")

# ======================
# —— 3. Streamlit UI: 注册 / 登录 / 注销 逻辑
# ======================
st.sidebar.title("账号管理")

# session_state 中保存登录状态
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

# 选择“登录”或“注册”
menu = st.sidebar.selectbox("请选择操作", ["登录", "注册", "注销" if st.session_state.logged_in else ""])

if menu == "登录":
    st.sidebar.subheader("用户登录")
    input_user = st.sidebar.text_input("用户名", key="login_user")
    input_pw = st.sidebar.text_input("密码", type="password", key="login_pw")
    if st.sidebar.button("登录"):
        if verify_user(input_user, input_pw):
            st.session_state.logged_in = True
            st.session_state.username = input_user
            st.sidebar.success(f"登录成功，欢迎 {input_user}！")
        else:
            st.sidebar.error("用户名或密码错误，请重试。")

elif menu == "注册":
    st.sidebar.subheader("新用户注册")
    new_user = st.sidebar.text_input("用户名", key="reg_user")
    new_pw = st.sidebar.text_input("密码", type="password", key="reg_pw")
    new_pw_confirm = st.sidebar.text_input("确认密码", type="password", key="reg_pw_confirm")
    if st.sidebar.button("注册"):
        if not new_user or not new_pw:
            st.sidebar.error("用户名和密码不能为空。")
        elif new_pw != new_pw_confirm:
            st.sidebar.error("两次输入的密码不一致。")
        else:
            success = add_user(new_user, new_pw)
            if success:
                st.sidebar.success("注册成功，请前往登录。")
            else:
                st.sidebar.error("用户名已存在，请选择其他用户名。")

elif menu == "注销":
    # 清空登录状态
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.sidebar.info("您已注销。")

# 如果未登录，不显示后续内容
if not st.session_state.logged_in:
    st.title("请先注册或登录，才能使用人脸识别功能")
    st.stop()

# ======================
# —— 4. 用户已登录，显示实时人脸识别界面
# ======================
st.title("可视化人脸识别界面（实时摄像头 + Liveness 活体检测）")
st.subheader(f"当前用户：{st.session_state.username}")

st.header("实时摄像头 + 人脸识别 (含 Liveness 活体检测)")
st.write("""
勾选下方“开启实时检测”以允许浏览器访问摄像头。  
程序会实时读取摄像头帧，先用 Haar Cascade 检测人脸，再对检测到的区域进行活体检测和人脸识别。  
简化处理：每隔若干帧才做一次人脸识别，避免整帧过度耗时，保持流畅。  
已知人脸库请放在 `faces_database` 文件夹中，命名为 `name.jpg`。  
""")

# 控制开关：只使用本地变量 run，不向 session_state 直接赋值
run = st.checkbox("开启实时检测", key="run_live")

# 维护帧计数与上一次识别结果
if "frame_count" not in st.session_state:
    st.session_state.frame_count = 0
if "last_recog" not in st.session_state:
    st.session_state.last_recog = "？？？"

frame_placeholder = st.empty()
cap = None

if run:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        st.error("无法打开摄像头，请检查硬件。")
        run = False

# 加载 Haar Cascade
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# 识别间隔
RECOG_INTERVAL = 10  # 每隔 RECOG_INTERVAL 帧做一次识别

while run:
    ret, frame = cap.read()
    if not ret:
        st.warning("摄像头读取失败，正在尝试重新连接……")
        cap.release()
        cap = cv2.VideoCapture(0)
        continue

    # 翻转镜像
    frame = cv2.flip(frame, 1)
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    display_frame = frame.copy()

    # Haar Cascade 人脸检测
    faces = face_cascade.detectMultiScale(
        gray_frame,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(60, 60)
    )

    # 帧计数递增
    st.session_state.frame_count += 1

    for (x, y, w, h) in faces:
        # 画出人脸框
        cv2.rectangle(display_frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

        # 裁剪并转 RGB
        face_bgr = frame[y:y+h, x:x+w]
        face_rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)

        # resize 到 (128,128,3)
        try:
            face_resized = cv2.resize(face_rgb, (128, 128))
        except Exception:
            continue

        face_input = face_resized.astype("float32") / 255.0
        face_input = np.expand_dims(face_input, axis=0)  # (1,128,128,3)

        # 活体检测
        if model_loaded:
            preds = liveness_model.predict(face_input)[0]
            # 如果模型输出两个元素，则假设 preds=[prob_spoof, prob_live]
            if preds.shape[-1] == 2:
                prob_live = float(preds[1])
            else:
                prob_live = float(preds[0])
            live_label = "Liveness" if prob_live >= 0.5 else "Spoof"
            color = (0, 255, 0) if prob_live >= 0.5 else (0, 0, 255)
        else:
            # 如果模型加载失败，则直接标记为未通过
            prob_live = 0.0
            live_label = "NoModel"
            color = (0, 0, 255)

        # 显示活体结果
        cv2.putText(
            display_frame,
            f"{live_label}: {prob_live:.2f}",
            (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2
        )

        # 每隔 RECOG_INTERVAL 帧才做识别
        if prob_live >= 0.5 and (st.session_state.frame_count % RECOG_INTERVAL == 0):
            try:
                results_list = DeepFace.find(
                    face_rgb,
                    db_path=os.path.join(os.getcwd(), "faces_database"),
                    enforce_detection=False,
                    model_name="Facenet",
                )
                df = results_list[0] if isinstance(results_list, list) else results_list
                if df is not None and not df.empty:
                    dist_col = [c for c in df.columns if 'distance' in c or 'cosine' in c][0]
                    best_match = df.sort_values(by=dist_col).iloc[0]
                    name = os.path.splitext(os.path.basename(best_match['identity']))[0]
                    distance_val = float(best_match[dist_col])
                    st.session_state.last_recog = f"{name} ({distance_val:.2f})"
                else:
                    st.session_state.last_recog = "？？？"
            except Exception as e:
                error_msg = str(e)
                st.session_state.last_recog = f"Error: {error_msg}"
                print(error_msg)

        # 显示识别结果（上一次或“？？？”）
        cv2.putText(
            display_frame,
            f"Result: {st.session_state.last_recog}",
            (x, y + h + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 0),
            2
        )

    # 显示合成后的帧
    frame_placeholder.image(display_frame, channels="BGR")

    # 检查 run 状态是否被取消
    run = st.session_state.run_live

# 释放摄像头
if cap is not None:
    cap.release()

# ---------- 说明区 ----------
st.sidebar.markdown("---")
st.sidebar.info("""
1. **依赖安装**  
   - 建议安装对应 CUDA 版本的 TensorFlow，以加速模型推理。  
   - 需要安装 `mysql-connector-python` 并不再使用，可忽略。

2. **准备 Face-Liveness-Detection**  
   1. 克隆仓库：  
      ```
      git clone https://github.com/sakethbachu/Face-Liveness-Detection.git
      ```  
   2. 训练或下载预训练模型，将文件命名为 `anandfinal.hdf5` 并放到当前目录。  
   3. 确保目录结构如下：  
      ```
      your_project_folder/
      ├─ Face-Liveness-Detection/
      │    └─ liveness.model
      ├─ faces_database/
      │    ├─ Alice.jpg
      │    └─ Bob.jpg
      ├─ anandfinal.hdf5
      ├─ users.db
      └─ face_recognition_app.py
      ```

3. **运行脚本**  
4. **工作流程简述**  
- 注册或登录后，勾选“开启实时检测”会打开摄像头。  
- 程序先用 Haar Cascade 检测人脸，再对检测到的区域进行活体检测。  
- 如果活体检测通过（概率 ≥ 0.5），每隔若干帧通过 DeepFace 在 `faces_database` 中进行识别。  
- 识别结果会显示在人脸框下方。  
- 可以根据 Precision/Recall 曲线，在代码中调整活体验证阈值（当前设为 0.5）。  
""")