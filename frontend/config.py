"""
配置管理模块 - 支持跨设备部署
"""
import os
import json
from pathlib import Path

class Config:
    """统一配置管理类"""
    
    def __init__(self):
        self.load_config()
    
    def load_config(self):
        """加载配置 - 优先级：环境变量 > 配置文件 > 默认值"""
        
        # 尝试从配置文件加载
        config_file = Path("config.json")
        file_config = {}
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
            except:
                pass
        
        # 后端配置
        self.BACKEND_HOST = os.environ.get('BACKEND_HOST', 
                                         file_config.get('backend_host', '127.0.0.1'))
        self.BACKEND_PORT = int(os.environ.get('BACKEND_PORT', 
                                             file_config.get('backend_port', 8000)))
        self.DJANGO_API_URL = os.environ.get('DJANGO_API_URL', 
                                            file_config.get('backend_url', 
                                            f"http://{self.BACKEND_HOST}:{self.BACKEND_PORT}/api"))
        
        # 前端配置
        self.FRONTEND_HOST = os.environ.get('FRONTEND_HOST', 
                                          file_config.get('frontend_host', '127.0.0.1'))
        self.FRONTEND_PORT = int(os.environ.get('FRONTEND_PORT', 
                                               file_config.get('frontend_port', 8501)))
        
        # 安全配置
        self.USE_HTTPS = os.environ.get('USE_HTTPS', '').lower() == 'true'
        self.API_TOKEN = os.environ.get('API_TOKEN', file_config.get('api_token', ''))
        
        # 部署环境
        self.ENVIRONMENT = os.environ.get('ENVIRONMENT', 
                                        file_config.get('environment', 'development'))
    
    def get_api_url(self):
        """获取API基础URL"""
        return self.DJANGO_API_URL
    
    def is_production(self):
        """是否为生产环境"""
        return self.ENVIRONMENT.lower() == 'production'
    
    def create_sample_config(self):
        """创建示例配置文件"""
        sample_config = {
            "backend_host": "192.168.1.100",
            "backend_port": 8000,
            "backend_url": "http://192.168.1.100:8000/api",
            "frontend_host": "0.0.0.0",
            "frontend_port": 8501,
            "environment": "production",
            "api_token": "your-api-token-here",
            "use_https": False
        }
        
        with open("config.example.json", 'w', encoding='utf-8') as f:
            json.dump(sample_config, f, indent=2, ensure_ascii=False)
        
        return sample_config

# 全局配置实例
config = Config()
