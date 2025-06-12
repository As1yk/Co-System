from django.contrib import admin
from .models import AuditLog # Assuming User is Django's built-in
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

# 如果你创建了自定义的 Profile 或扩展了 User
# class UserProfileInline(admin.StackedInline):
# model = UserProfile # 假设你有一个 UserProfile 模型
# can_delete = False
# verbose_name_plural = 'profile'

# class UserAdmin(BaseUserAdmin):
#     inlines = (UserProfileInline,)

# admin.site.unregister(User) # 取消注册默认的 User
# admin.site.register(User, UserAdmin) # 注册你自定义的 UserAdmin

admin.site.register(AuditLog)
