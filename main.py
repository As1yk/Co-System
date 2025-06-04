import os
import sys

# 设置 DeepFace 模型权重缓存路径（可选）
os.environ['DEEPFACE_HOME'] = r"D:\SCUT\co-system"

import streamlit as st
from deepface import DeepFace
import cv2
import numpy as np
from PIL import Image
from tensorflow.keras.models import load_model

liveness_model_path = "anandfinal.hdf5"

try:
    liveness_model = load_model(liveness_model_path)
    model_loaded = True
except Exception as e:
    liveness_model = None
    model_loaded = False
    st.warning(f"无法加载活体检测模型，请检查 {liveness_model_path}：{e}")

st.title("可视化人脸识别界面（实时摄像头 + Liveness 活体检测）")


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

# # 预加载 DeepFace 模型
# with st.spinner("正在准备人脸识别模型，请稍候……"):
#     try:
#         _ = DeepFace.build_model("VGG-Face")
#     except:
#         st.text("error")
#         pass

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

        # resize 到 (32,32,3)
        try:
            face_resized = cv2.resize(face_rgb, (128, 128))
        except Exception:
            continue

        face_input = face_resized.astype("float32") / 255.0
        face_input = np.expand_dims(face_input, axis=0)  # (1,32,32,3)

        # 活体检测
        preds = liveness_model.predict(face_input)[0]
        prob_live = float(preds[1]) if preds.shape[-1] == 2 else float(preds[0])
        live_label = "Liveness" if prob_live >= 0.5 else "Spoof"
        color = (0, 255, 0) if prob_live >= 0.5 else (0, 0, 255)

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
                    model_name="ArcFace"
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
1. **依赖安装**  - 建议安装对应 CUDA 版本的 TensorFlow，以加速模型推理。

2. **准备 sakethbachu/Face-Liveness-Detection**  
1. 克隆仓库：
```
git clone https://github.com/sakethbachu/Face-Liveness-Detection.git
```  
2. 训练或下载预训练模型，将文件命名为 `liveness.model` 并放到：
```
Face-Liveness-Detection/liveness.model
```  
3. 确保目录结构如下：
```
D:\SCUT\Face\Face
├─ Face-Liveness-Detection
│    └─ liveness.model
├─ faces_database
│    ├─ Alice.jpg
│    └─ Bob.jpg
└─ face_recognition_app.py
```

3. **运行脚本**  

4. **工作流程简述**  
- 上传待识别图片后，程序先用 `DeepFace.detectFace` 对齐人脸并裁剪到 (任意大于等于 64×64) 的 RGB 数组；  
- 将裁剪后的人脸缩放到 64×64 （或根据 `liveness.model` 输入尺寸进行调节），归一化到 [0,1]；  
- 调用 `liveness_model.predict(...)` 输出活体概率 `prob_live`；若 `prob_live < 0.5` ，则提示“活体检测未通过”并中止后续比对；  
- 否则调用 `DeepFace.find(...)` 在 `faces_database` 中进行人脸识别，并按距离排序，显示最佳匹配结果。

5. **阈值调整**  
- 本示例将“活体验证阈值”设为 0.5 ，可根据你在测试集上的 Precision/Recall 曲线，在 0.3–0.7 区间调整，以权衡“拒真率”和“误放率”。
""")
