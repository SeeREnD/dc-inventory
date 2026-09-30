#!/bin/bash
pkill -f "uvicorn app.main:app"
pkill -f "vite"
echo "服务已停止"
