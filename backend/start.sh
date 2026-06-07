#!/bin/bash
set -e

# 创建必要目录
mkdir -p ./data/uploads

# 初始化数据库
cd /app
python -c "from app.database import init_db; import app.models; init_db()"

# 从环境变量读取管理员凭据（安全方式：通过 os.environ 而非 shell 插值）
if [ -n "$ADMIN_USERNAME" ] && [ -n "$ADMIN_PASSWORD" ]; then
    python -c "
import os, bcrypt
from app.database import SessionLocal
from app.models.user import User
admin_user = os.environ.get('ADMIN_USERNAME', '')
admin_pass = os.environ.get('ADMIN_PASSWORD', '')
if not admin_user or not admin_pass:
    print('管理员凭据为空，跳过创建')
    exit(0)
db = SessionLocal()
try:
    admin = db.query(User).filter(User.username == admin_user).first()
    if not admin:
        hashed = bcrypt.hashpw(admin_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        admin = User(username=admin_user, password_hash=hashed, role='admin')
        db.add(admin)
        db.commit()
        print(f'管理员账户已创建: {admin_user}')
    else:
        print('管理员账户已存在，跳过创建')
finally:
    db.close()
"
else
    echo "未设置 ADMIN_USERNAME / ADMIN_PASSWORD，跳过创建默认管理员"
fi

# 测试 Nginx 配置
nginx -t

# 启动后端应用（绑定 127.0.0.1，仅 Nginx 可访问）
uvicorn app.main:app --host 127.0.0.1 --port 8000 &

# 启动 Nginx（前台，作为容器主进程）
exec nginx -g 'daemon off;'
