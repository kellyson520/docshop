@echo off
chcp 65001 >nul

REM ============================================
REM   DocShop 文档分发系统 - 局域网模式
REM   自动获取本机IP，无需手动修改
REM ============================================

REM 获取局域网IPv4地址
setlocal enabledelayedexpansion
set "LAN_IP="
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "127.0.0.1"') do (
    set "ip=%%a"
    set "ip=!ip: =!"
    if "!LAN_IP!"=="" set "LAN_IP=!ip!"
)
if "%LAN_IP%"=="" set "LAN_IP=localhost"

title DocShop Server - http://%LAN_IP%:3000

echo.
echo ============================================
echo   DocShop 文档分发系统 - 局域网模式
echo ============================================
echo   后端 API:  http://%LAN_IP%:8000
echo   前端界面:  http://%LAN_IP%:3000
echo   API 文档:  http://%LAN_IP%:8000/docs
echo ============================================
echo.

echo [1/3] 设置环境变量...
set DOCX2PDF_TIMEOUT_SECONDS=300

echo [2/3] 启动后端 (FastAPI + Uvicorn)...
start "DocShop-Backend" cmd /c "cd /d C:\Users\lihuo\Desktop\docshop\backend && set DOCX2PDF_TIMEOUT_SECONDS=300 && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo [3/3] 启动前端 (Vite Dev Server)...
start "DocShop-Frontend" cmd /c "cd /d C:\Users\lihuo\Desktop\docshop\frontend && npm run dev -- --host 0.0.0.0"

echo.
echo ============================================
echo   启动完成! 等待几秒后访问:
echo   前端: http://%LAN_IP%:3000
echo   后端: http://%LAN_IP%:8000
echo ============================================
echo.
pause
