from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_user, name='api_register'),
    path('login/', views.login_user, name='api_login'),
    path('logout/', views.logout_user, name="api_logout"),
    path('current_user/', views.current_user_status, name='api_current_user'),
    path('verify_identity/', views.verify_identity_api, name='api_verify_identity'),
    path('audit_logs/', views.get_audit_logs_api, name='api_get_audit_logs'),
    path('alert_logs/', views.get_alert_logs_api, name='api_get_alert_logs'),
]
