@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo.
    echo   [错误] 还没安装环境，请先双击运行：安装环境.bat
    echo.
    pause
    exit /b 1
)

echo ============================================================
echo   校园二手交易平台 - 启动
echo ============================================================
echo.
echo   访问地址：  http://127.0.0.1:8000/
echo   后台管理：  http://127.0.0.1:8000/admin/
echo.
echo   按 Ctrl + C 可停止服务器
echo ============================================================
echo.

start "" http://127.0.0.1:8000/
venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000

pause
