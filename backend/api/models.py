from django.db import models
from django.contrib.auth.models import User # 使用 Django 内置 User
from django.utils import timezone

# 如果需要扩展 User 模型，例如添加 is_admin 字段，可以这样做：
# from django.contrib.auth.models import AbstractUser
# class User(AbstractUser):
#     is_admin_custom = models.BooleanField(default=False) # 避免与 is_staff/is_superuser 混淆

class AuditLog(models.Model):
    # Django User 模型有 is_staff 字段可以表示管理员
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now)
    action = models.CharField(max_length=100)
    liveness_status = models.CharField(max_length=50, null=True, blank=True)
    compare_result = models.CharField(max_length=50, null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    image_path = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.timestamp} - {self.user.username} - {self.action}"

    class Meta:
        ordering = ['-timestamp']
