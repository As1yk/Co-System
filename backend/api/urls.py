from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_api, name='login'),
    path('logout/', views.logout_api, name='logout'),
    path('register/', views.register_api, name='register'),
    path('current_user_status/', views.current_user_status, name='current_user_status'),
    path('system_status/', views.system_status_api, name='system_status'),
    
    # 人脸识别API - 修复路径
    path('recognition/start/', views.recognition_start_api, name='recognition_start'),
    path('recognition/process_frame/', views.recognition_process_frame_api, name='recognition_process_frame'),
    path('recognition/finalize/', views.recognition_finalize_api, name='recognition_finalize'),
    
    # 保持原有路径兼容性
    path('recognition_start/', views.recognition_start_api, name='recognition_start_old'),
    path('recognition_process_frame/', views.recognition_process_frame_api, name='recognition_process_frame_old'),
    path('recognition_finalize/', views.recognition_finalize_api, name='recognition_finalize_old'),
    
    path('users/', views.users_api, name='users'),
    path('audit_logs/', views.audit_logs_api, name='audit_logs'),
    path('alert_logs/', views.alert_logs_api, name='alert_logs'),
    path('create_admin/', views.create_admin_api, name='create_admin'),
    path('delete_user/', views.delete_user, name='delete_user'),
]
