# 人脸识别系统 - 前后端分离架构

## 🚀 快速启动指南

### 第一步：启动后端 (Django)

```bash
# 1. 打开命令行，进入项目根目录
cd ./face-recognition-system

# 2. 进入后端目录
cd backend

# 3. 安装后端依赖 (首次运行)
pip install -r requirements.txt

# 4. 数据库迁移 (首次运行或模型更新时)
python manage.py makemigrations
python manage.py migrate

# 5. 启动后端服务器 (允许外部访问)
python manage.py runserver 0.0.0.0:8000
```

**后端启动成功标志：**
```bash
Starting development server at http://0.0.0.0:8000/
Quit the server with CTRL-BREAK.
```

### 第二步：启动前端 (Streamlit)

```bash
# 1. 新开一个命令行窗口，进入项目根目录  
cd ./face-recognition-system

# 2. 进入前端目录
cd frontend

# 3. 安装前端依赖 (首次运行)
pip install -r requirements.txt

# 4. 启动前端应用 (允许外部访问)
streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

**前端启动成功标志：**
```bash
Local URL: http://localhost:8501
Network URL: http://192.168.x.x:8501
```

## 📍 访问地址

### 本地访问
- **前端应用**: http://localhost:8501
- **后端API**: http://localhost:8000/api/
- **Django管理后台**: http://localhost:8000/admin/

### 跨设备访问
- **前端应用**: http://前端设备IP:8501
- **后端API**: http://后端设备IP:8000/api/

## 🔧 跨设备部署配置

### 场景1：同一设备运行前后端
无需特殊配置，按上述命令启动即可。

### 场景2：不同设备运行前后端

#### 后端设备配置
```bash
# 1. 启动后端允许外部访问
python manage.py runserver 0.0.0.0:8000

# 2. 确保防火墙允许8000端口访问
```

#### 前端设备配置
```bash
# 1. 创建或修改 frontend/.env 文件
echo DJANGO_API_URL=http://后端设备IP:8000/api > frontend/.env

# 2. 启动前端
cd frontend
streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

## 🎯 用户使用流程

### 1. 首次使用
1. **访问前端**: 在浏览器打开 http://localhost:8501
2. **注册账户**: 点击"注册"标签，填写用户名密码
3. **上传身份照片**: 选择本地照片或使用摄像头拍照
4. **完成注册**: 系统自动保存用户信息和人脸特征

### 2. 日常使用
1. **登录系统**: 使用注册的用户名密码登录
2. **身份验证**: 点击"开启实时验证"
3. **人脸识别**: 面向摄像头进行活体检测和人脸比对
4. **查看结果**: 系统显示识别结果和置信度

### 3. 管理员功能
1. **创建管理员**: 使用 `python manage.py createsuperuser` 创建
2. **用户管理**: 查看、编辑用户信息
3. **审计日志**: 查看所有用户的识别记录
4. **失败记录**: 查看识别失败的记录和图片

## 📁 项目结构

```
face-recognition-system/
├── frontend/                 # 🎨 前端应用 (Streamlit)
│   ├── app.py               # 主应用入口
│   ├── auth_ui.py           # 用户认证界面
│   ├── recognition_ui.py    # 人脸识别界面
│   ├── admin_ui.py          # 管理员界面
│   ├── config.py            # 配置管理
│   ├── requirements.txt     # 前端依赖包
│   └── .env                 # 环境变量 (可选)
│
├── backend/                 # 🔧 后端服务 (Django)
│   ├── manage.py            # Django管理脚本
│   ├── co_system_project/   # Django项目配置
│   │   ├── settings.py      # Django设置
│   │   ├── urls.py          # URL路由
│   │   └── wsgi.py          # WSGI配置
│   ├── api/                 # API应用模块
│   │   ├── models.py        # 数据模型
│   │   ├── views.py         # API视图
│   │   ├── urls.py          # API路由
│   │   ├── utils_recognition.py  # 人脸识别工具
│   │   ├── db_utils.py      # 数据库工具
│   │   └── audit_utils.py   # 审计日志工具
│   ├── requirements.txt     # 后端依赖包
│   ├── users.db             # SQLite数据库
│   ├── faces_database/      # 用户人脸图片存储
│   ├── failed_faces/        # 识别失败图片存储
│   └── anandfinal.hdf5      # 活体检测AI模型
│
├── README.md                # 项目说明文档
└── .gitignore              # Git忽略文件配置
```

## 🔍 常见问题与解决方案

### 1. 后端启动问题

**问题**: `ModuleNotFoundError: No module named 'django'`
```bash
# 解决方案
cd backend
pip install -r requirements.txt
```

**问题**: 数据库迁移错误
```bash
# 解决方案
python manage.py makemigrations api
python manage.py migrate
```

### 2. 前端连接问题

**问题**: "无法连接到Django后端服务"
```bash
# 检查后端是否启动
curl http://localhost:8000/api/current_user_status/

# 检查配置文件
cat frontend/.env  # Linux/Mac
type frontend\.env # Windows
```

**问题**: 跨设备访问失败
```bash
# 确保后端配置允许外部访问
# backend/co_system_project/settings.py
ALLOWED_HOSTS = ['*']
CORS_ALLOW_ALL_ORIGINS = True
```

### 3. 摄像头问题

**问题**: "无法打开摄像头"
```bash
# 检查OpenCV安装
python -c "import cv2; print('OpenCV版本:', cv2.__version__)"

# 重新安装OpenCV
pip install opencv-python
```

### 4. AI模型问题

**问题**: TensorFlow模型加载失败
```bash
# 检查TensorFlow安装
python -c "import tensorflow as tf; print('TF版本:', tf.__version__)"

# 系统会自动切换到模拟模式
```

## ⚙️ 高级配置

### 环境变量配置

#### frontend/.env
```bash
DJANGO_API_URL=http://localhost:8000/api
FRONTEND_HOST=0.0.0.0
FRONTEND_PORT=8501
```

#### backend/.env
```bash
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=*
DATABASE_URL=sqlite:///users.db
```

### 生产环境部署

```bash
# 后端生产环境启动
python manage.py runserver --settings=co_system_project.settings_prod

# 前端生产环境启动
streamlit run app.py --server.port=8501 --server.headless=true
```

## 🔐 安全配置

### Django安全设置
```python
# settings.py
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
```

### 防火墙配置
```bash
# Windows防火墙
netsh advfirewall firewall add rule name="Django" dir=in action=allow protocol=TCP localport=8000
netsh advfirewall firewall add rule name="Streamlit" dir=in action=allow protocol=TCP localport=8501

# Linux防火墙 (ufw)
sudo ufw allow 8000
sudo ufw allow 8501
```

## 📊 系统特性

- ✅ **前后端分离架构**: Django REST API + Streamlit UI
- ✅ **跨设备部署**: 支持前后端分布式部署
- ✅ **人脸识别**: DeepFace + OpenCV 实现高精度识别
- ✅ **活体检测**: TensorFlow模型防止照片欺骗
- ✅ **用户管理**: 完整的用户注册、登录、权限管理
- ✅ **审计日志**: 详细记录所有用户操作和识别结果
- ✅ **智能降级**: AI组件不可用时自动切换到模拟模式
- ✅ **实时处理**: WebRTC摄像头 + 实时帧处理
- ✅ **安全认证**: 密码哈希 + Session管理
- ✅ **管理员功能**: 用户管理、日志查看、失败记录分析

## 📝 更新日志

### v1.0.0 (当前版本)
- 初始版本发布
- 实现基础人脸识别功能
- 完成前后端分离架构
- 添加用户管理和审计功能

---

**技术支持**: 如有问题请检查日志文件或联系开发团队
