import json
import uuid
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import IntegrityError
from .models import AuditLog
from .utils_recognition import (
    add_audit_log_entry, 
    save_identity_photo,
    get_system_status,
    create_recognition_session,
    get_recognition_session,
    update_recognition_session,
    process_single_frame,
    finalize_face_recognition
)

def json_response(success=True, data=None, message='', status=200):
    """统一的JSON响应格式"""
    response_data = {
        'status': 'success' if success else 'error',
        'message': message
    }
    if data:
        response_data.update(data)
    return JsonResponse(response_data, status=status)

@csrf_exempt
def login_api(request):
    """用户登录API"""
    if request.method != 'POST':
        return json_response(False, message='Method not allowed', status=405)
    
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return json_response(False, message='用户名和密码不能为空', status=400)
        
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return json_response(True, {
                'username': user.username,
                'is_admin': user.is_superuser
            }, '登录成功')
        else:
            return json_response(False, message='用户名或密码错误', status=401)
            
    except json.JSONDecodeError:
        return json_response(False, message='无效的JSON数据', status=400)
    except Exception as e:
        return json_response(False, message=f'登录失败: {str(e)}', status=500)

@csrf_exempt
def logout_api(request):
    """用户登出API"""
    if request.method != 'POST':
        return json_response(False, message='Method not allowed', status=405)
    
    logout(request)
    return json_response(True, message='登出成功')

@csrf_exempt
def register_api(request):
    """用户注册API"""
    if request.method != 'POST':
        return json_response(False, message='Method not allowed', status=405)
    
    try:
        username = request.POST.get('username')
        password = request.POST.get('password')
        identity_photo = request.FILES.get('identity_photo')
        
        if not all([username, password, identity_photo]):
            return json_response(False, message='用户名、密码和身份照片不能为空', status=400)
        
        try:
            user = User.objects.create_user(username=username, password=password)
            photo_bytes = identity_photo.read()
            success, result = save_identity_photo(username, photo_bytes)
            
            if success:
                return json_response(True, message='注册成功，请登录')
            else:
                user.delete()
                return json_response(False, message=f'保存身份照片失败: {result}', status=500)
                
        except IntegrityError:
            return json_response(False, message='用户名已存在', status=400)
            
    except Exception as e:
        return json_response(False, message=f'注册失败: {str(e)}', status=500)

@csrf_exempt
def current_user_status(request):
    """获取当前用户状态API"""
    if request.user.is_authenticated:
        return json_response(True, {
            'authenticated': True,
            'username': request.user.username,
            'is_admin': request.user.is_superuser
        })
    else:
        return json_response(True, {'authenticated': False})

@csrf_exempt
def system_status_api(request):
    """系统状态API"""
    if request.method != 'GET':
        return json_response(False, message='Method not allowed', status=405)
    
    try:
        status_info = get_system_status()
        return json_response(True, {'system_info': status_info}, '系统状态获取成功')
    except Exception as e:
        return json_response(False, message=f'获取系统状态失败: {str(e)}', status=500)

@csrf_exempt
def recognition_start_api(request):
    """开始识别会话API"""
    if request.method != 'POST':
        return json_response(False, message='Method not allowed', status=405)
    
    try:
        data = json.loads(request.body)
        username = data.get('username')
        
        if not username:
            return json_response(False, message='用户名不能为空', status=400)
        
        session_id = str(uuid.uuid4())
        session_data = create_recognition_session(
            session_id, 
            username, 
            data.get('num_votes', 10), 
            data.get('live_threshold', 0.5)
        )
        
        return json_response(True, {'session_id': session_id}, '识别会话创建成功')
    except Exception as e:
        return json_response(False, message=f'创建识别会话失败: {str(e)}', status=500)

@csrf_exempt
def recognition_process_frame_api(request):
    """处理视频帧API"""
    if request.method != 'POST':
        return json_response(False, message='Method not allowed', status=405)
    
    try:
        session_id = request.POST.get('session_id')
        frame_file = request.FILES.get('frame')
        
        if not session_id or not frame_file:
            return json_response(False, message='会话ID和帧数据不能为空', status=400)
        
        session_data = get_recognition_session(session_id)
        if not session_data:
            return json_response(False, message='会话不存在或已过期', status=404)
        
        result = process_single_frame(frame_file, session_data)
        update_recognition_session(session_id, result['session_data'])
        
        return json_response(True, {
            'result': result['frame_result'],
            'session_status': result['session_status']
        }, '帧处理成功')
    except Exception as e:
        return json_response(False, message=f'处理帧失败: {str(e)}', status=500)

@csrf_exempt
def recognition_finalize_api(request):
    """完成识别API"""
    if request.method != 'POST':
        return json_response(False, message='Method not allowed', status=405)
    
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        if not session_id:
            return json_response(False, message='会话ID不能为空', status=400)
        
        session_data = get_recognition_session(session_id)
        if not session_data:
            return json_response(False, message='会话不存在或已过期', status=404)
        
        final_result = finalize_face_recognition(session_data)
        return json_response(True, {'final_result': final_result}, '识别完成')
    except Exception as e:
        return json_response(False, message=f'完成识别失败: {str(e)}', status=500)

@csrf_exempt
def users_api(request):
    """用户列表API"""
    if request.method != 'GET':
        return json_response(False, message='Method not allowed', status=405)
    
    try:
        limit = int(request.GET.get('limit', 100))
        users = User.objects.all()[:limit]
        
        user_list = [{
            'username': user.username,
            'email': user.email,
            'is_admin': user.is_superuser,
            'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
            'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else '未登录',
            'is_active': user.is_active
        } for user in users]
        
        return json_response(True, {'users': user_list})
    except Exception as e:
        return json_response(False, message=f'获取用户列表失败: {str(e)}', status=500)

@csrf_exempt
def audit_logs_api(request):
    """审计日志API"""
    if request.method != 'GET':
        return json_response(False, message='Method not allowed', status=405)
    
    try:
        limit = int(request.GET.get('limit', 50))
        logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:limit]
        
        log_list = [{
            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'username': log.user.username,
            'action': log.action,
            'liveness_status': log.liveness_status,
            'compare_result': log.compare_result,
            'score': log.score,
            'image_path': log.image_path
        } for log in logs]
        
        return json_response(True, {'logs': log_list})
    except Exception as e:
        return json_response(False, message=f'获取审计日志失败: {str(e)}', status=500)

@csrf_exempt
def alert_logs_api(request):
    """警报日志API"""
    if request.method != 'GET':
        return json_response(False, message='Method not allowed', status=405)
    
    try:
        limit = int(request.GET.get('limit', 10))
        logs = AuditLog.objects.select_related('user').filter(
            liveness_status__in=['FAIL', 'ERROR']
        ).order_by('-timestamp')[:limit]
        
        log_list = [{
            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'username': log.user.username,
            'action': log.action,
            'liveness_status': log.liveness_status,
            'compare_result': log.compare_result,
            'score': log.score,
            'image_path': log.image_path
        } for log in logs]
        
        return json_response(True, {'logs': log_list})
    except Exception as e:
        return json_response(False, message=f'获取警报日志失败: {str(e)}', status=500)

@csrf_exempt
def create_admin_api(request):
    """创建管理员API"""
    if request.method != 'POST':
        return json_response(False, message='Method not allowed', status=405)
    
    if not request.user.is_authenticated or not request.user.is_superuser:
        return json_response(False, message='权限不足', status=403)
    
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return json_response(False, message='用户名和密码不能为空', status=400)
        
        try:
            User.objects.create_user(
                username=username, 
                password=password,
                is_superuser=True,
                is_staff=True
            )
            return json_response(True, message=f'管理员 {username} 创建成功')
        except IntegrityError:
            return json_response(False, message='用户名已存在', status=400)
            
    except Exception as e:
        return json_response(False, message=f'创建管理员失败: {str(e)}', status=500)

@csrf_exempt
def delete_user(request):
    """删除用户"""
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        username = data.get('username')
        
        if not username:
            return JsonResponse({'success': False, 'message': '用户名不能为空'})
        
        user = User.objects.get(username=username)
        user.delete()
        
        # 删除用户的人脸图片文件
        import os
        from django.conf import settings
        user_face_path = os.path.join(settings.BASE_DIR, 'faces_database', f'{username}.jpg')
        if os.path.exists(user_face_path):
            os.remove(user_face_path)
        
        return JsonResponse({'success': True, 'message': '用户删除成功'})
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'删除用户失败: {str(e)}'})

@csrf_exempt
def log_operation_api(request):
    """记录操作日志API"""
    if request.method != 'POST':
        return json_response(False, message='Method not allowed', status=405)
    
    try:
        data = json.loads(request.body)
        username = data.get('username')
        operation = data.get('operation')
        operation_type = data.get('operation_type', 'unknown')
        verification_required = data.get('verification_required', False)
        verification_result = data.get('verification_result', 'not_applicable')
        
        if not username or not operation:
            return json_response(False, message='用户名和操作不能为空', status=400)
        
        # 根据操作类型设置不同的状态
        if operation_type == 'normal':
            status = 'SUCCESS'
            compare_result = 'NORMAL_OP_NO_VERIFICATION'
            score = 1.0
        elif operation_type == 'critical':
            if verification_result == 'success':
                status = 'SUCCESS'
                compare_result = 'CRITICAL_OP_VERIFIED'
                score = 1.0
            elif verification_result == 'failed':
                status = 'FAIL'
                compare_result = 'CRITICAL_OP_VERIFICATION_FAILED'
                score = 0.0
            else:
                status = 'IN_PROGRESS'
                compare_result = 'CRITICAL_OP_VERIFICATION_STARTED'
                score = 0.5
        else:
            status = 'UNKNOWN'
            compare_result = 'UNKNOWN_OPERATION_TYPE'
            score = 0.0
        
        # 记录审计日志
        add_audit_log_entry(
            username=username,
            action=f"{operation_type.upper()}_OPERATION: {operation}",
            status=status,
            compare_result=compare_result,
            score=score
        )
        
        return json_response(True, message='操作日志记录成功')
        
    except Exception as e:
        return json_response(False, message=f'记录操作日志失败: {str(e)}', status=500)

