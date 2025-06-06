# recognition_ui.py

import os
import streamlit as st
import cv2
import numpy as np
from deepface import DeepFace
from tensorflow.keras.models import load_model

def load_liveness_model(model_path="anandfinal.hdf5"):
    """
    试图加载 Keras 活体检测模型，返回 (model, model_loaded: bool)。
    """
    try:
        m = load_model(model_path)
        return m, True
    except Exception as e:
        st.warning(f"无法加载活体检测模型，请检查 {model_path}：{e}")
        return None, False

def run_recognition(username: str):
    """
    已登录用户的人脸识别界面：
    - 加载 Haar Cascade、活体检测模型
    - 循环读取摄像头帧，画框 + 活体检测 + DeepFace 检索
    """
    st.title("可视化人脸识别界面（实时摄像头 + Liveness 活体检测）")
    st.subheader(f"当前用户：{username}")

    st.header("实时摄像头 + 人脸识别 (含 Liveness 活体检测)")
    st.write("""
    勾选下方“开启实时检测”以允许浏览器访问摄像头。  
    程序会实时读取摄像头帧，先用 Haar Cascade 检测人脸，再对检测到的区域进行活体检测和人脸识别。  
    简化处理：每隔若干帧才做一次人脸识别，避免整帧过度耗时，保持流畅。  
    已知人脸库请放在 `faces_database` 文件夹中，命名为 `name.jpg`。  
    """)

    # —— 1. 加载活体检测模型 ——
    liveness_model_path = "anandfinal.hdf5"
    liveness_model, model_loaded = load_liveness_model(liveness_model_path)

    # —— 2. 设置摄像头控制与变量 ——
    run = st.checkbox("开启实时检测", key="run_live")
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

    # —— 3. 加载 Haar Cascade ——
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    RECOG_INTERVAL = 10  # 多少帧做一次人脸识别

    while run:
        ret, frame = cap.read()
        if not ret:
            st.warning("摄像头读取失败，正在尝试重新连接……")
            cap.release()
            cap = cv2.VideoCapture(0)
            continue

        # 翻转、灰度化
        frame = cv2.flip(frame, 1)
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        display_frame = frame.copy()

        # 人脸检测
        faces = face_cascade.detectMultiScale(
            gray_frame,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60)
        )
        st.session_state.frame_count += 1

        for (x, y, w, h) in faces:
            # 画框
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

            # 裁剪人脸 & 转 RGB
            face_bgr = frame[y:y+h, x:x+w]
            face_rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)

            # resize 到 (128x128)
            try:
                face_resized = cv2.resize(face_rgb, (128, 128))
            except Exception:
                continue

            face_input = face_resized.astype("float32") / 255.0
            face_input = np.expand_dims(face_input, axis=0)  # (1,128,128,3)

            # —— 活体检测 ——
            if model_loaded:
                preds = liveness_model.predict(face_input)[0]
                # 假设 preds 可能为 [prob_spoof, prob_live] 或单一输出
                if preds.shape[-1] == 2:
                    prob_live = float(preds[1])
                else:
                    prob_live = float(preds[0])
                live_label = "Liveness" if prob_live >= 0.5 else "Spoof"
                color = (0, 255, 0) if prob_live >= 0.5 else (0, 0, 255)
            else:
                # 如果模型未加载，则置为“未通过”
                prob_live = 0.0
                live_label = "NoModel"
                color = (0, 0, 255)

            # 显示活体检测结果
            cv2.putText(
                display_frame,
                f"{live_label}: {prob_live:.2f}",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )

            # —— 如果活体通过且到达识别帧间隔，则调用 DeepFace.find ——
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
                    st.session_state.last_recog = f"Error: {e}"

            # 显示识别结果（上一帧 / “？？？”）
            cv2.putText(
                display_frame,
                f"Result: {st.session_state.last_recog}",
                (x, y + h + 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 0),
                2
            )

        # 最终把帧转换成 Streamlit 可显示格式
        frame_placeholder.image(display_frame, channels="BGR")

        # 检查 run 状态是否被取消
        run = st.session_state.run_live

    # 释放摄像头资源
    if cap is not None:
        cap.release()

    # 底部说明
    st.sidebar.markdown("---")
    st.sidebar.info("""
    1. **依赖安装**  
       - 建议安装对应 CUDA 版本的 TensorFlow，以加速模型推理。  
       - 需要安装：`pip install streamlit deepface opencv-python pillow tensorflow`.

    2. **准备 Face-Liveness-Detection**  
       1. 克隆仓库：  
          ```
          git clone https://github.com/sakethbachu/Face-Liveness-Detection.git
          ```  
       2. 训练或下载预训练模型，并将其重命名为 `anandfinal.hdf5` 放到项目根目录。  
       3. 确保目录结构：  
          ```
          face_recognition_project/
          ├─ Face-Liveness-Detection/
          │    └─ liveness.model
          ├─ faces_database/
          │    ├─ Alice.jpg
          │    └─ Bob.jpg
          ├─ anandfinal.hdf5
          ├─ users.db
          ├─ app.py
          ├─ db_utils.py
          ├─ auth_ui.py
          └─ recognition_ui.py
          ```

    3. **运行脚本**  
       ```
       streamlit run app.py
       ```

    4. **工作流程简述**  
       - 注册或登录后，勾选“开启实时检测”会打开摄像头。  
       - 程序先用 Haar Cascade 检测人脸，再对检测到区域进行活体检测。  
       - 如果活体通过（概率 ≥ 0.5），每隔若干帧用 DeepFace 在 `faces_database` 中进行识别；  
       - 识别结果会显示在人脸框下方。  
       - 阈值（当前设 0.5）可按需调整。  
    """)
