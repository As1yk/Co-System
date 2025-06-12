import json
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt # 仅用于简化示例，生产环境慎用
from django.views.decorators.http import require_POST, require_GET
from django.db import transaction
from django.conf import settings
import base64 # 用于处理可能的 base64 编码图像数据
import os # 用于文件路径处理

from .models import AuditLog
from .utils_recognition import add_audit_log_entry, perform_liveness_check_and_match, perform_face_match, save_identity_photo # 添加 save_identity_photo

@csrf_exempt # 生产中应使用更安全的方法，例如 CSRF token
@require_POST
def register_user(request):
    try:
        # multipart/form-data 请求时，文本字段在 request.POST 中
        # 文件在 request.FILES 中
        username = request.POST.get('username')
        password = request.POST.get('password')
        identity_photo_file = request.FILES.get('identity_photo')

        if not username or not password:
            return JsonResponse({'status': 'error', 'message': '用户名和密码不能为空'}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({'status': 'error', 'message': '用户名已存在'}, status=400)

        # 使用事务确保用户创建和照片保存的原子性
        with transaction.atomic():
            user = User.objects.create_user(username=username, password=password)
            
            photo_saved_successfully = False
            photo_message = "未提供身份照片"

            if identity_photo_file:
                image_bytes = identity_photo_file.read()
                photo_saved_successfully, photo_message = save_identity_photo(username, image_bytes)
                if not photo_saved_successfully:
                    # 如果照片保存失败，回滚用户创建（因为在事务中）
                    # 并返回错误信息
                    # transaction.set_rollback(True) # Django 会在异常时自动回滚
                    raise Exception(f"照片处理失败: {photo_message}") # 抛出异常以触发回滚

            add_audit_log_entry(username, 'register_api', 'SUCCESS', 
                                compare_result="PHOTO_PROVIDED" if identity_photo_file and photo_saved_successfully else "NO_PHOTO")
            
            response_message = '注册成功。'
            if identity_photo_file:
                if photo_saved_successfully:
                    response_message += f" 照片已保存: {os.path.basename(photo_message)}"
                else: # 此处理论上已被上面的 raise 捕获，但作为保险
                    response_message += f" 但照片处理失败: {photo_message}"
            
            return JsonResponse({'status': 'success', 'message': response_message})

    except Exception as e:
        # 确保为通用异常也记录审计（如果用户名已获取）
        # username_for_log = request.POST.get('username', 'unknown_user_reg_fail')
        # add_audit_log_entry(username_for_log, 'register_api', 'FAIL', str(e)[:100])
        return JsonResponse({'status': 'error', 'message': f'注册失败: {str(e)}'}, status=500)

@csrf_exempt
@require_POST
def login_user(request):
    try:
        # 确保 request.body 被正确解码为字符串，然后再解析 JSON
        # request.body 是字节串，Django 通常会根据 Content-Type 的 charset 来处理
        # 但为了保险，我们可以显式解码
        body_unicode = request.body.decode('utf-8')
        data = json.loads(body_unicode)
        username = data.get('username')
        password = data.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user) # 创建 Django session
            add_audit_log_entry(username, 'login_api', 'SUCCESS')
            return JsonResponse({
                'status': 'success',
                'message': '登录成功',
                'username': user.username,
                'is_admin': user.is_staff or user.is_superuser # Django 的管理员标志
            })
        else:
            add_audit_log_entry(username, 'login_api', 'FAIL', 'INVALID_CREDENTIALS')
            return JsonResponse({'status': 'error', 'message': '用户名或密码错误'}, status=401)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': '无效的 JSON 数据'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'登录失败: {str(e)}'}, status=500)

@csrf_exempt # 确保 Streamlit 可以调用
@require_POST # 或者 GET 如果只是检查 session
def logout_user(request):
    username = request.user.username if request.user.is_authenticated else "unknown_user_logout"
    logout(request) # 清除 Django session
    add_audit_log_entry(username, 'logout_api', 'SUCCESS')
    return JsonResponse({'status': 'success', 'message': '已注销'})

@require_GET
def current_user_status(request):
    if request.user.is_authenticated:
        return JsonResponse({
            'logged_in': True,
            'username': request.user.username,
            'is_admin': request.user.is_staff or request.user.is_superuser
        })
    else:
        return JsonResponse({'logged_in': False})

@csrf_exempt
@require_POST
def verify_identity_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': '用户未登录'}, status=401)

    username = request.user.username
    
    # Streamlit 将发送包含多帧图像的列表，每帧是 bytes
    # 假设请求体是 {"frames": [base64_encoded_frame1, base64_encoded_frame2, ...], "live_threshold": 0.5}
    # 或者直接发送文件列表 request.FILES.getlist('frames')
    try:
        # 尝试从 request.FILES 获取图像数据 (multipart/form-data)
        frames_files = request.FILES.getlist('frames')
        if not frames_files: # 如果没有文件，尝试从 JSON body 获取 base64 编码的图像
            data = json.loads(request.body)
            base64_frames = data.get('frames', [])
            frame_bytes_list = [base64.b64decode(bf) for bf in base64_frames]
            live_threshold = float(data.get('live_threshold', 0.5))
        else: # 处理上传的文件
            frame_bytes_list = [f.read() for f in frames_files]
            # live_threshold 可以从 POST 数据中获取
            live_threshold = float(request.POST.get('live_threshold', 0.5))


        if not frame_bytes_list:
            return JsonResponse({'status': 'error', 'message': '未提供图像帧'}, status=400)

        result = perform_liveness_check_and_match(username, frame_bytes_list, live_threshold)
        return JsonResponse({'status': 'success', 'result': result})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': '无效的 JSON 数据 (frames/live_threshold)'}, status=400)
    except Exception as e:
        add_audit_log_entry(username, "verify_identity_api", "ERROR", f"API_ERROR: {str(e)[:50]}")
        return JsonResponse({'status': 'error', 'message': f'处理请求时发生错误: {str(e)}'}, status=500)


@require_GET
def get_audit_logs_api(request):
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'status': 'error', 'message': '无权访问'}, status=403)

    limit = int(request.GET.get('limit', 100))
    # 排除管理员自身的日志（如果需要）
    # logs = AuditLog.objects.filter(user__is_staff=False, user__is_superuser=False).order_by('-timestamp')[:limit]
    logs = AuditLog.objects.all().order_by('-timestamp')[:limit] # 获取所有日志
    
    data = [{
        'id': log.id,
        'timestamp': log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        'username': log.user.username,
        'action': log.action,
        'liveness_status': log.liveness_status,
        'compare_result': log.compare_result,
        'score': log.score,
        'image_path': log.image_path # 注意：这应该是相对于 MEDIA_URL 的路径或完整 URL
    } for log in logs]
    return JsonResponse({'status': 'success', 'logs': data})

@require_GET
def get_alert_logs_api(request):
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'status': 'error', 'message': '无权访问'}, status=403)

    limit = int(request.GET.get('limit', 10))
    # 仅获取包含 image_path 且非管理员用户的日志
    logs = AuditLog.objects.filter(
        image_path__isnull=False
    ).exclude(
        user__is_staff=True
    ).exclude(
        user__is_superuser=True
    ).order_by('-id')[:limit]

    data = [{
        'timestamp': log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        'username': log.user.username,
        'action': log.action,
        'liveness_status': log.liveness_status,
        'compare_result': log.compare_result,
        'score': log.score,
        'image_path': log.image_path # Django 应配置为能服务此路径的图片
    } for log in logs]
    return JsonResponse({'status': 'success', 'logs': data})

