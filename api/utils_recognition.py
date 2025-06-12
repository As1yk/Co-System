import os
import cv2
import numpy as np
from deepface import DeepFace
from tensorflow.keras.models import load_model
from django.conf import settings
from datetime import datetime
from .models import AuditLog, User # Django User model
from typing import Tuple # 添加这一行
import logging # 添加 logging

logger = logging.getLogger(__name__)

# 全局加载模型，避免重复加载
LIVENESS_MODEL = None
LIVENESS_MODEL_LOADED = False
FACE_CASCADE = None

def load_models_globally():
    global LIVENESS_MODEL, LIVENESS_MODEL_LOADED, FACE_CASCADE
    if not LIVENESS_MODEL_LOADED:
        try:
            LIVENESS_MODEL = load_model(settings.LIVENESS_MODEL_PATH)
            LIVENESS_MODEL_LOADED = True
            print("Liveness model loaded successfully.")
        except Exception as e:
            print(f'Failed to load liveness model: {e}')
            LIVENESS_MODEL_LOADED = False
    
    if FACE_CASCADE is None:
        FACE_CASCADE = cv2.CascadeClassifier(settings.FACE_CASCADE_PATH)
        if FACE_CASCADE.empty():
            print(f"Failed to load face cascade from {settings.FACE_CASCADE_PATH}")
        else:
            print("Face cascade loaded successfully.")

load_models_globally() # 应用启动时加载

def add_audit_log_entry(username_str: str, action: str, liveness_status: str = None,
                        compare_result: str = None, score: float = None, image_path: str = None):
    try:
        user_obj = User.objects.get(username=username_str)
        # 管理员操作不记录到普通审计日志（或根据需求调整）
        if user_obj.is_staff or user_obj.is_superuser:
             # print(f"Admin action by {username_str}, not logging to general audit.")
             # return # 或者有专门的管理员日志
             pass # 示例中允许记录管理员操作

        AuditLog.objects.create(
            user=user_obj,
            action=action,
            liveness_status=liveness_status,
            compare_result=compare_result,
            score=score,
            image_path=image_path
        )
    except User.DoesNotExist:
        print(f"User {username_str} not found for audit logging.")
    except Exception as e:
        print(f"Error adding audit log: {e}")


def save_identity_photo(username: str, image_bytes: bytes) -> Tuple[bool, str]: # 修改这里的 tuple 为 Tuple
    """
    处理并保存用户注册时的人脸照片。
    - image_bytes: 图像的字节流。
    - 返回: (success_boolean, message_or_filepath_string)
    """
    if FACE_CASCADE is None or FACE_CASCADE.empty():
        logger.error("Face cascade not loaded during save_identity_photo.")
        return False, "人脸检测器未加载"

    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_bgr is None:
            logger.error(f"Failed to decode image for user {username}.")
            return False, "无法解码图像"

        # img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB) # Not needed for saving with cv2.imwrite
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        
        # 检测人脸
        faces = FACE_CASCADE.detectMultiScale(gray, 1.1, 5, minSize=(100, 100)) # 注册照要求高一点

        if len(faces) == 0:
            logger.warning(f"No face detected for user {username} during registration photo save.")
            return False, "未检测到人脸，请确保面部清晰可见且正对摄像头。"
        if len(faces) > 1:
            logger.warning(f"Multiple faces detected for user {username} during registration photo save.")
            return False, "检测到多张人脸，请确保只有您一人在画面中。"

        x, y, w, h = faces[0]
        face_to_save = img_bgr[y:y+h, x:x+w] # 保存 BGR 格式

        # 确保 faces_database 目录存在
        try:
            os.makedirs(settings.FACES_DATABASE_PATH, exist_ok=True)
            logger.info(f"Ensured directory exists: {settings.FACES_DATABASE_PATH}")
        except OSError as e:
            logger.error(f"Error creating directory {settings.FACES_DATABASE_PATH}: {e}")
            return False, f"无法创建照片存储目录: {e}"
        
        save_path = os.path.join(settings.FACES_DATABASE_PATH, f"{username}.jpg")
        logger.info(f"Attempting to save identity photo for user {username} to: {save_path}")
        
        # 使用 cv2.imencode 将图像编码到内存缓冲区，然后用 Python 的文件 IO 写入
        # 这通常能更好地处理包含 Unicode 字符的文件路径
        try:
            # 确保 face_to_save 不是空的
            if face_to_save is None or face_to_save.size == 0:
                logger.error(f"Face ROI (face_to_save) is empty for user {username}.")
                return False, "检测到的人脸区域为空"

            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 95] # JPEG 质量 95
            result, encoded_image = cv2.imencode('.jpg', face_to_save, encode_param)
            
            if not result:
                logger.error(f"cv2.imencode failed for user {username}.")
                return False, "图像编码失败 (cv2.imencode)"

            with open(save_path, 'wb') as f:
                f.write(encoded_image)
            logger.info(f"Successfully wrote image buffer to {save_path} using Python's open().")
            
            # 再次确认文件是否存在且非空
            if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                logger.info(f"Successfully saved and verified photo: {save_path}")
                return True, save_path
            else:
                logger.error(f"Python's open() seemed to succeed, but file not found or empty at {save_path}. This is unexpected.")
                return False, "照片保存后验证失败 (文件不存在或为空，即使使用 Python I/O)"
                
        except Exception as e_write:
            logger.exception(f"Exception during writing image for user {username} to {save_path} using Python's open(): {e_write}")
            return False, f"使用 Python I/O 写入照片时发生错误: {str(e_write)}"

    except Exception as e:
        logger.exception(f"Exception during save_identity_photo for user {username}: {e}") # Logs full traceback
        return False, f"处理照片时发生内部错误: {str(e)}"


def perform_face_match(username_str: str, frame_bytes: bytes) -> dict:
    """
    将给定帧中的人脸与数据库中该用户的照片进行比对。
    """
    identity_photo_path = os.path.join(settings.FACES_DATABASE_PATH, f"{username_str}.jpg")
    logger.info(f"User {username_str}: Attempting to perform face match. Identity photo path: {identity_photo_path}")

    if not os.path.exists(identity_photo_path):
        logger.error(f"User {username_str}: Identity photo not found at {identity_photo_path}")
        return {"error": "Identity photo not found for user.", "verified": False, "distance": -1.0}

    try:
        # 使用 Python 的 open() 和 cv2.imdecode() 来读取包含 Unicode 字符路径的图像
        with open(identity_photo_path, 'rb') as f:
            identity_photo_bytes = f.read()
        
        img1_bgr = cv2.imdecode(np.frombuffer(identity_photo_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img1_bgr is None:
            logger.error(f"User {username_str}: Failed to decode identity photo from {identity_photo_path} using imdecode.")
            return {"error": "Failed to decode identity photo.", "verified": False, "distance": -1.0}
        
        # 将摄像头帧字节解码为图像
        nparr_frame = np.frombuffer(frame_bytes, np.uint8)
        img2_bgr = cv2.imdecode(nparr_frame, cv2.IMREAD_COLOR)
        if img2_bgr is None:
            logger.error(f"User {username_str}: Failed to decode current frame for face matching.")
            return {"error": "Failed to decode current frame.", "verified": False, "distance": -1.0}

        # DeepFace.verify 期望 BGR 格式的图像
        # img1_path 可以是实际路径，也可以是 numpy 数组 (BGR)
        # img2_path 可以是实际路径，也可以是 numpy 数组 (BGR)
        # 使用 enforce_detection=False 是因为我们通常已经在前端或活体检测中确认了人脸
        # 但如果 DeepFace 内部再次检测失败，也可能出问题。可以考虑先用我们的 FACE_CASCADE 检测 img2_bgr
        
        logger.info(f"User {username_str}: Calling DeepFace.verify with identity photo shape: {img1_bgr.shape}, current frame shape: {img2_bgr.shape}")
        
        # 确保 DeepFace 使用正确的模型和距离度量
        # 默认模型是 VGG-Face, 默认距离度量是 cosine
        # models = ["VGG-Face", "Facenet", "Facenet512", "OpenFace", "DeepFace", "DeepID", "ArcFace", "Dlib", "SFace"]
        # metrics = ["cosine", "euclidean", "euclidean_l2"]
        result = DeepFace.verify(img1_path=img1_bgr, 
                                 img2_path=img2_bgr, 
                                 model_name="VGG-Face", 
                                 distance_metric="cosine", 
                                 enforce_detection=False, 
                                 detector_backend='opencv'
                                 )
        
        logger.info(f"User {username_str}: DeepFace.verify result: {result}")
        
        verified_status = bool(result.get("verified", False))
        distance_val = result.get("distance", -1.0)
        threshold_val = result.get("threshold", -1.0) # 获取阈值

        return {
            "verified": verified_status,
            "distance": distance_val,
            "threshold": threshold_val, # 返回阈值
            "model": result.get("model"),
            "similarity_metric": result.get("similarity_metric")
        }

    except Exception as e:
        logger.exception(f"User {username_str}: Error during face comparison: {e}")
        return {"error": f"Face comparison error: {str(e)}", "verified": False, "distance": -1.0}


def perform_liveness_check_and_match(username_str: str, frame_bytes_list: list, live_threshold: float = 0.5) -> dict:
    """
    执行活体检测投票和人脸比对。
    frame_bytes_list: 多帧图像字节列表，用于活体检测投票。最后一帧用于比对。
    """
    if not LIVENESS_MODEL_LOADED or LIVENESS_MODEL is None:
        logger.error(f"Liveness model not loaded for user {username_str}.")
        return {"error": "Liveness model not loaded", "liveness_passed": False, "match_passed": False, "details": "Liveness model not available."}
    if FACE_CASCADE is None or FACE_CASCADE.empty():
        logger.error(f"Face cascade not loaded for user {username_str}.")
        return {"error": "Face cascade not loaded", "liveness_passed": False, "match_passed": False, "details": "Face cascade not available."}

    pass_votes = 0
    num_votes_received = len(frame_bytes_list)
    processed_frames = 0
    last_face_resized_rgb = None 
    all_probs_live = [] # 存储每帧的活体概率

    logger.info(f"User {username_str}: Starting liveness check with {num_votes_received} frames, threshold {live_threshold}.")

    for i, frame_bytes in enumerate(frame_bytes_list):
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            logger.warning(f"User {username_str}: Frame {i+1}/{num_votes_received} failed to decode.")
            continue
        
        processed_frames += 1
        img = frame 
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = FACE_CASCADE.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))

        if len(faces) > 0:
            x, y, w, h = faces[0]
            face_bgr = img[y:y+h, x:x+w]
            face_rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
            face_resized = cv2.resize(face_rgb, (128, 128))
            last_face_resized_rgb = face_resized 

            inp = np.expand_dims(face_resized.astype("float32")/255.0, 0)
            preds = LIVENESS_MODEL.predict(inp, verbose=0)[0] # verbose=0 减少 Keras 日志
            
            # --- 关键：确定如何从 preds 计算 prob_live ---
            # 原始 preds 输出，用于调试
            logger.info(f"User {username_str}: Frame {i+1}, Raw model prediction (preds): {preds}")

            # 可能性 1: preds[1] 是活体概率 (如果模型输出 [fake_prob, live_prob])
            # prob_live = float(preds[1]) 

            # 可能性 2: preds[0] 是活体概率 (如果模型输出 [live_prob, fake_prob] 或单值 live_prob)
            # prob_live = float(preds[0])

            # 可能性 3: preds[0] 是 fake_prob, 所以 live_prob = 1 - preds[0] (如果模型输出单值 fake_prob)
            # prob_live = 1.0 - float(preds[0])

            # 可能性 4: preds 是 logits, 需要 sigmoid
            # logit_live = float(preds[0]) # 或者 preds[1] 取决于模型结构
            # prob_live = 1 / (1 + np.exp(-logit_live))
            
            # 当前的假设 (需要验证或修改):
            if preds.shape[-1] == 2: # 假设输出是 [fake_prob, live_prob] 或 [live_prob, fake_prob]
                # 尝试 preds[1] 作为活体概率
                prob_live_candidate1 = float(preds[1])
                # 尝试 preds[0] 作为活体概率
                prob_live_candidate2 = float(preds[0])
                logger.info(f"User {username_str}: Frame {i+1}, preds has 2 values. Candidate live_prob from preds[1]: {prob_live_candidate1:.4f}, from preds[0]: {prob_live_candidate2:.4f}")
                # **** 根据日志，preds[0] 似乎是活体概率 ****
                prob_live = prob_live_candidate2 # <--- 修改：使用 preds[0]
            elif preds.shape[-1] == 1: # 假设输出是单个值
                prob_live_single_val = float(preds[0])
                logger.info(f"User {username_str}: Frame {i+1}, preds has 1 value. Candidate live_prob: {prob_live_single_val:.4f}. Candidate 1-val: {1.0-prob_live_single_val:.4f}")
                # **** 您需要根据模型文档或实验来决定是直接用它，还是 1-它，还是 sigmoid(它) ****
                # **** 临时选择直接用它进行测试 ****
                prob_live = prob_live_single_val 
            else:
                logger.error(f"User {username_str}: Frame {i+1}, Unexpected shape for preds: {preds.shape}. Preds: {preds}")
                prob_live = 0.0 # 无法解析，设为0

            all_probs_live.append(prob_live)
            logger.info(f"User {username_str}: Frame {i+1}, Face detected. Calculated Liveness prob: {prob_live:.4f}.") # 记录计算后的 prob_live

            if prob_live >= live_threshold:
                pass_votes += 1
        else:
            logger.warning(f"User {username_str}: Frame {i+1}, No face detected.")
            all_probs_live.append(-1.0) # 表示未检测到人脸

    if processed_frames == 0:
        logger.error(f"User {username_str}: No frames could be processed.")
        return {"error": "No frames processed", "liveness_passed": False, "match_passed": False, "details": "All frames failed to decode or process."}

    liveness_score_ratio = pass_votes / processed_frames if processed_frames > 0 else 0.0
    # 修改投票通过逻辑：需要超过一半的已处理帧通过
    required_passes = (processed_frames // 2) + 1 
    liveness_passed = pass_votes >= required_passes

    logger.info(f"User {username_str}: Liveness check complete. Votes: {pass_votes}/{processed_frames}. Required: {required_passes}. Passed: {liveness_passed}. Probs: {all_probs_live}")

    liveness_status_str = "PASS" if liveness_passed else "FAIL"
    
    saved_image_path = None
    if not liveness_passed and last_face_resized_rgb is not None:
        # 确保 FAILED_DIR_PATH 目录存在 (settings.py 中已创建，但再次检查无害)
        try:
            os.makedirs(settings.FAILED_DIR_PATH, exist_ok=True)
        except OSError as e:
            logger.error(f"Error creating FAILED_DIR_PATH {settings.FAILED_DIR_PATH} for user {username_str}: {e}")
            # 如果目录创建失败，后续保存也会失败，但至少记录了错误

        ts_file = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 构建文件名时，确保 username_str 中的特殊字符不会导致问题
        # Python 的 os.path.join 和 open() 通常能很好地处理 unicode 文件名
        filename = f"{username_str}_{ts_file}_liveness_fail.jpg"
        potential_save_path = os.path.join(settings.FAILED_DIR_PATH, filename)
        logger.info(f"Attempting to save failed liveness image for user {username_str} to: {potential_save_path}")

        try:
            # 使用 cv2.imencode 和 Python 的 open() 来保存，以更好地处理 Unicode 文件名
            # last_face_resized_rgb 是 RGB 格式，需要转回 BGR 给 imencode (如果需要)
            # 或者直接编码 RGB (JPEG 不关心颜色顺序，但 imwrite 通常期望 BGR)
            # 为了与 imwrite 的通常行为一致，我们先转为 BGR
            img_to_save_bgr = cv2.cvtColor(last_face_resized_rgb, cv2.COLOR_RGB2BGR)

            if img_to_save_bgr is None or img_to_save_bgr.size == 0:
                logger.error(f"Image to save (img_to_save_bgr) is empty for failed liveness, user {username_str}.")
            else:
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90] # JPEG 质量 90
                result, encoded_image = cv2.imencode('.jpg', img_to_save_bgr, encode_param)
            
                if not result:
                    logger.error(f"cv2.imencode failed for failed liveness image, user {username_str}.")
                else:
                    with open(potential_save_path, 'wb') as f:
                        f.write(encoded_image)
                    logger.info(f"Successfully wrote failed liveness image buffer to {potential_save_path} using Python's open().")
                    
                    if os.path.exists(potential_save_path) and os.path.getsize(potential_save_path) > 0:
                        saved_image_path = potential_save_path # 确认保存成功后才赋值
                        logger.info(f"Successfully saved and verified failed liveness image: {saved_image_path}")
                    else:
                        logger.error(f"Python's open() for failed liveness seemed to succeed, but file not found or empty at {potential_save_path}.")
                        # saved_image_path 保持为 None
        except Exception as e:
            logger.exception(f"Error saving failed liveness image for user {username_str} to {potential_save_path}: {e}")
            # saved_image_path 保持为 None

    add_audit_log_entry(username_str, "liveness_check_op",
                        liveness_status_str,
                        "SKIPPED" if not liveness_passed else None,
                        score=liveness_score_ratio,
                        image_path=saved_image_path)

    if not liveness_passed:
        return {
            "error": "Liveness check failed",
            "liveness_passed": False,
            "liveness_votes": f"{pass_votes}/{processed_frames}",
            "required_passes": required_passes,
            "live_probabilities": all_probs_live, # 返回每帧的概率以供调试
            "match_passed": False,
            "image_path": saved_image_path,
            "details": f"Liveness votes {pass_votes}/{processed_frames}. Probabilities: {['{:.2f}'.format(p) for p in all_probs_live]}"
        }

    # 活体通过，进行人脸比对 (使用最后一帧)
    if not frame_bytes_list: 
         logger.error(f"User {username_str}: No frames provided for matching though liveness supposedly passed (this shouldn't happen).")
         return {"error": "No frames provided for matching", "liveness_passed": True, "match_passed": False, "details": "Liveness passed but no frames for matching."}

    match_result = perform_face_match(username_str, frame_bytes_list[-1]) 
    
    logger.info(f"User {username_str}: Liveness passed. Match result: {match_result}")

    match_passed_status = bool(match_result.get('verified', False))
    match_distance_val = match_result.get('distance', -1.0)
    match_threshold_val = match_result.get('threshold', -1.0) # 获取阈值

    return {
        "error": match_result.get("error"),
        "liveness_passed": True,
        "liveness_votes": f"{pass_votes}/{processed_frames}",
        "live_probabilities": all_probs_live,
        "match_passed": match_passed_status,
        "match_distance": match_distance_val,
        "match_threshold": match_threshold_val, # 返回阈值
        "image_path": saved_image_path, 
        "details": f"Liveness votes {pass_votes}/{processed_frames}. Match verified: {match_passed_status}. Distance: {match_distance_val:.2f}, Threshold: {match_threshold_val:.2f}" # 更新 details
    }

