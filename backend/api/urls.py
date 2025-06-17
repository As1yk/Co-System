from django.urls import path
from . import views

urlpatterns = [
    # 原有的API端点
    path('login/', views.login_api, name='login_api'),
    path('logout/', views.logout_api, name='logout_api'),
    path('register/', views.register_api, name='register_api'),
    path('current_user_status/', views.current_user_status, name='current_user_status'),
    
    # 新增的API端点
    path('system_status/', views.system_status_api, name='system_status_api'),
    path('recognition/start/', views.recognition_start_api, name='recognition_start_api'),
    path('recognition/process_frame/', views.recognition_process_frame_api, name='recognition_process_frame_api'),
    path('recognition/finalize/', views.recognition_finalize_api, name='recognition_finalize_api'),
    
    # 管理员API端点
    path('users/', views.users_api, name='users_api'),
    path('audit_logs/', views.audit_logs_api, name='audit_logs_api'),
    path('alert_logs/', views.alert_logs_api, name='alert_logs_api'),
    path('create_admin/', views.create_admin_api, name='create_admin_api'),
]
