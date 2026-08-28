@echo off
chcp 65001 >nul
title 客服保险工单系统 - 本地开发启动

echo ============================================
echo   客服保险工单系统 - 本地启动
echo ============================================

REM 1. 检查后端 .env 是否存在
if not exist "backend\.env" (
    echo [提示] backend\.env 不存在，请复制 backend\.env.example 为 .env 并修改数据库配置
    pause
    exit /b
)

REM 2. 启动后端
echo [1/2] 启动后端 FastAPI (http://127.0.0.1:8000)...
start "后端API" cmd /k "cd backend && uvicorn cit_api.main:app --reload --host 0.0.0.0 --port 8000"

REM 3. 启动前端
echo [2/2] 启动前端 Vue3 (http://localhost:5173)...
start "前端Vue" cmd /k "cd frontend && npm run dev"

echo.
echo 启动完成！
echo   后端API: http://127.0.0.1:8000
echo   前端Vue: http://localhost:5173
echo   客服客户端: python -m client.main
echo.
pause
