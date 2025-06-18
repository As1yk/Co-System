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

@csrf_exempt
def login_api(request):
    """用户登录API"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return JsonResponse({
                    'status': 'error',
                    'message': '用户名和密码不能为空'
                }, status=400)
            
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return JsonResponse({
                    'status': 'success',
                    'message': '登录成功',
                    'username': user.username,
                    'is_admin': user.is_superuser
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': '用户名或密码错误'
                }, status=401)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': '无效的JSON数据'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'登录失败: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def logout_api(request):
    """用户登出API"""
    if request.method == 'POST':
        logout(request)
        return JsonResponse({
            'status': 'success',
            'message': '登出成功'
        })
    else:
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def register_api(request):
    """用户注册API"""
    if request.method == 'POST':
        try:
            username = request.POST.get('username')
            password = request.POST.get('password')
            identity_photo = request.FILES.get('identity_photo')
            
            if not username or not password:
                return JsonResponse({
                    'status': 'error',
                    'message': '用户名和密码不能为空'
                }, status=400)
            
            if not identity_photo:
                return JsonResponse({
                    'status': 'error',
                    'message': '必须提供身份照片'
                }, status=400)
            
            # 创建用户
            try:
                user = User.objects.create_user(username=username, password=password)
                
                # 保存身份照片
                photo_bytes = identity_photo.read()
                success, result = save_identity_photo(username, photo_bytes)
                
                if success:
                    return JsonResponse({
                        'status': 'success',
                        'message': '注册成功，请登录'
                    })
                else:
                    # 如果照片保存失败，删除已创建的用户
                    user.delete()
                    return JsonResponse({
                        'status': 'error',
                        'message': f'保存身份照片失败: {result}'
                    }, status=500)
                    
            except IntegrityError:
                return JsonResponse({
                    'status': 'error',
                    'message': '用户名已存在'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'注册失败: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def current_user_status(request):
    """获取当前用户状态API"""
    if request.user.is_authenticated:
        return JsonResponse({
            'status': 'success',
            'authenticated': True,
            'username': request.user.username,
            'is_admin': request.user.is_superuser
        })
    else:
        return JsonResponse({
            'status': 'success',
            'authenticated': False
        })

@csrf_exempt
def system_status_api(request):
    """系统状态API"""
    if request.method == 'GET':
        try:
            status_info = get_system_status()
            return JsonResponse({
                'status': 'success',
                'system_info': status_info,
                'message': '系统状态获取成功'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'获取系统状态失败: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def recognition_start_api(request):
    """开始识别会话API"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            num_votes = data.get('num_votes', 10)
            live_threshold = data.get('live_threshold', 0.6)
            
            if not username:
                return JsonResponse({
                    'status': 'error',
                    'message': '用户名不能为空'
                }, status=400)
            
            # 生成会话ID
            session_id = str(uuid.uuid4())
            
            # 创建会话
            session_data = create_recognition_session(session_id, username, num_votes, live_threshold)
            
            return JsonResponse({
                'status': 'success',
                'session_id': session_id,
                'message': '识别会话创建成功',
                'simulation_mode': get_system_status()['simulation_mode']
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'创建识别会话失败: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def recognition_process_frame_api(request):
    """处理视频帧API"""
    if request.method == 'POST':
        try:
            session_id = request.POST.get('session_id')
            frame_file = request.FILES.get('frame')
            
            if not session_id or not frame_file:
                return JsonResponse({
                    'status': 'error',
                    'message': '会话ID和帧数据不能为空'
                }, status=400)
            
            # 获取会话数据
            session_data = get_recognition_session(session_id)
            if not session_data:
                return JsonResponse({
                    'status': 'error',
                    'message': '会话不存在或已过期'
                }, status=404)
            
            # 处理帧
            result = process_single_frame(frame_file, session_data)
            
            # 更新会话
            update_recognition_session(session_id, result['session_data'])
            
            return JsonResponse({
                'status': 'success',
                'result': result['frame_result'],
                'session_status': result['session_status'],
                'message': '帧处理成功'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'处理帧失败: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def recognition_finalize_api(request):
    """完成识别API"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            session_id = data.get('session_id')
            
            if not session_id:
                return JsonResponse({
                    'status': 'error',
                    'message': '会话ID不能为空'
                }, status=400)
            
            # 获取会话数据
            session_data = get_recognition_session(session_id)
            if not session_data:
                return JsonResponse({
                    'status': 'error',
                    'message': '会话不存在或已过期'
                }, status=404)
            
            # 最终识别
            final_result = finalize_face_recognition(session_data)
            
            return JsonResponse({
                'status': 'success',
                'final_result': final_result,
                'message': '识别完成'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'完成识别失败: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def users_api(request):
    """用户列表API"""
    if request.method == 'GET':
        try:
            limit = int(request.GET.get('limit', 100))
            users = User.objects.all()[:limit]
            
            user_list = []
            for user in users:
                user_list.append({
                    'username': user.username,
                    'email': user.email,
                    'is_admin': user.is_superuser,
                    'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
                    'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else '未登录',
                    'is_active': user.is_active
                })
            
            return JsonResponse({
                'status': 'success',
                'users': user_list
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'获取用户列表失败: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def audit_logs_api(request):
    """审计日志API"""
    if request.method == 'GET':
        try:
            limit = int(request.GET.get('limit', 50))
            logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:limit]
            
            log_list = []
            for log in logs:
                log_list.append({
                    'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'username': log.user.username,
                    'action': log.action,
                    'liveness_status': log.liveness_status,
                    'compare_result': log.compare_result,
                    'score': log.score,
                    'image_path': log.image_path
                })
            
            return JsonResponse({
                'status': 'success',
                'logs': log_list
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'获取审计日志失败: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def alert_logs_api(request):
    """警报日志API"""
    if request.method == 'GET':
        try:
            limit = int(request.GET.get('limit', 10))
            # 获取失败的验证记录
            logs = AuditLog.objects.select_related('user').filter(
                liveness_status__in=['FAIL', 'ERROR']
            ).order_by('-timestamp')[:limit]
            
            log_list = []
            for log in logs:
                log_list.append({
                    'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'username': log.user.username,
                    'action': log.action,
                    'liveness_status': log.liveness_status,
                    'compare_result': log.compare_result,
                    'score': log.score,
                    'image_path': log.image_path
                })
            
            return JsonResponse({
                'status': 'success',
                'logs': log_list
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'获取警报日志失败: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def create_admin_api(request):
    """创建管理员API"""
    if request.method == 'POST':
        try:
            # 检查当前用户是否为管理员
            if not request.user.is_authenticated or not request.user.is_superuser:
                return JsonResponse({
                    'status': 'error',
                    'message': '权限不足'
                }, status=403)
            
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return JsonResponse({
                    'status': 'error',
                    'message': '用户名和密码不能为空'
                }, status=400)
            
            try:
                user = User.objects.create_user(
                    username=username, 
                    password=password,
                    is_superuser=True,
                    is_staff=True
                )
                
                return JsonResponse({
                    'status': 'success',
                    'message': f'管理员 {username} 创建成功'
                })
                
            except IntegrityError:
                return JsonResponse({
                    'status': 'error',
                    'message': '用户名已存在'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'创建管理员失败: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def delete_user(request):
    """删除用户"""
    if request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            
            if not username:
                return JsonResponse({'success': False, 'message': '用户名不能为空'})
            
            # 删除用户 - 无需登录验证
            try:
                user = User.objects.get(username=username)
                user.delete()
                
                # 删除用户的人脸图片文件
                import os
                from django.conf import settings
                user_face_path = os.path.join(settings.BASE_DIR, 'faces_database', f'{username}.jpg')
                if os.path.exists(user_face_path):
                    os.remove(user_face_path)
                
                # 记录审计日志（如果有当前用户的话）
                try:
                    if request.user.is_authenticated:
                        add_audit_log_entry(
                            request.user,
                            'DELETE_USER',
                            'ADMIN',
                            'SUCCESS',
                            1.0,
                            f'删除用户: {username}'
                        )
                except Exception as audit_error:
                    print(f"审计日志记录失败: {audit_error}")
                
                return JsonResponse({'success': True, 'message': '用户删除成功'})
                
            except User.DoesNotExist:
                return JsonResponse({'success': False, 'message': '用户不存在'})
                
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': '无效的JSON数据'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'删除用户失败: {str(e)}'})
    else:
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)

