#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # 设置Django设置模块
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'co_system_project.settings')
    
    # 减少Django文件监控的冗余输出
    if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
        # 设置日志级别，减少文件监控信息
        os.environ.setdefault('DJANGO_LOG_LEVEL', 'INFO')
        # 禁用自动重载的详细输出
        if '--verbosity' not in ' '.join(sys.argv):
            sys.argv.extend(['--verbosity', '1'])
    
    # 加载环境变量文件
    try:
        from dotenv import load_dotenv
        load_dotenv()
        if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
            print("✅ 环境变量加载成功")
    except ImportError:
        if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
            print("⚠️ python-dotenv未安装，正在使用默认配置")
            print("💡 建议运行: pip install python-dotenv")
    
    # 检查AI模型依赖
    if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
        print("\n🔍 检查AI模型依赖状态:")
        
        # 检查TensorFlow
        try:
            import tensorflow as tf
            print(f"✅ TensorFlow: {tf.__version__}")
        except ImportError:
            print("❌ TensorFlow未安装 - pip install tensorflow")
        
        # 检查DeepFace
        try:
            from deepface import DeepFace
            print("✅ DeepFace: 已安装")
        except ImportError:
            print("❌ DeepFace未安装 - pip install deepface")
        
        # 检查OpenCV
        try:
            import cv2
            print(f"✅ OpenCV: {cv2.__version__}")
        except ImportError:
            print("❌ OpenCV未安装 - pip install opencv-python")
        
        # 检查模型文件
        model_path = os.path.join(os.path.dirname(__file__), 'anandfinal.hdf5')
        if os.path.exists(model_path):
            print(f"✅ 活体检测模型: {model_path}")
        else:
            print(f"❌ 活体检测模型文件不存在: {model_path}")
            print("💡 请确保 anandfinal.hdf5 在 backend 目录中")
        
        print("-" * 50)
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "❌ 无法导入Django。请确保Django已安装并且 "
            "在PYTHONPATH环境变量中可用。您是否忘记激活虚拟环境？"
        ) from exc
    
    # 显示启动信息和命令行指南
    if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
        print("🚀 正在启动Django后端服务器...")
        print("📍 默认地址: http://127.0.0.1:8000")
        print("🔗 API地址: http://127.0.0.1:8000/api/")
        print("💡 提示: 文件监控信息已最小化")
        print("⏹️  按 Ctrl+C 停止服务器")
        print("-" * 50)
    elif len(sys.argv) == 1:
        print("📋 Django管理命令提示：")
        print("  python manage.py runserver          # 启动开发服务器")
        print("  python manage.py runserver --noreload  # 启动服务器(无文件监控)")
        print("  python manage.py migrate            # 数据库迁移")
        print("  python manage.py createsuperuser    # 创建超级用户")
        print("  python manage.py help               # 查看所有命令")
        print("-" * 50)
    
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
