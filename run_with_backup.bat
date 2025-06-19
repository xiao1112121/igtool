@echo off
chcp 65001 >nul
title Instagram Tool - Auto Backup & Run

echo 🔄 Instagram Tool - Auto Backup ^& Run
echo ==================================================

REM Kiểm tra Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python không được cài đặt hoặc không có trong PATH
    echo Vui lòng cài đặt Python và thêm vào PATH
    pause
    exit /b 1
)

REM Chạy script Python
python run_with_backup.py

echo.
echo ✅ Script đã hoàn tất
pause 