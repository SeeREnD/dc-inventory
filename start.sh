#!/bin/bash
# 一键启动：后端(8000) + 前端(5173)
cd "$(dirname "$0")"

if [ ! -d backend/.venv ]; then
  echo "首次运行：初始化后端虚拟环境..."
  python3 -m venv backend/.venv
  backend/.venv/bin/pip install -q -r backend/requirements.txt
fi

if [ ! -d frontend/node_modules ]; then
  echo "首次运行：安装前端依赖..."
  (cd frontend && npm install)
fi

echo "启动后端 http://127.0.0.1:8000"
(cd backend && .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &> /tmp/dc-inventory-backend.log &)

echo "启动前端 http://127.0.0.1:5173"
(cd frontend && npm run dev &> /tmp/dc-inventory-frontend.log &)

echo
echo "启动完成！浏览器访问: http://localhost:5173"
echo "默认管理员账号: admin / admin123（登录后请立即修改密码）"
echo "停止服务请运行 ./stop.sh"
