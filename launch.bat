@echo off
:: Check for Admin Privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting Administrator Privileges...
    powershell -Command "Start-Process '%~dpnx0' -Verb RunAs"
    exit /b
)

title AMD Stability Brain Launcher
echo ==============================================
echo       Starting AMD Stability Brain...
echo ==============================================
echo.

cd /d "%~dp0"

echo [1/3] Starting Python Backend Server...
start "AMD Backend" cmd /c "cd backend && python -m uvicorn app:app --host 127.0.0.1 --port 8000"

timeout /t 2 /nobreak > nul

echo [2/3] Starting Web Frontend Server...
start "AMD Frontend" cmd /c "cd frontend && python -m http.server 8080"

timeout /t 1 /nobreak > nul

echo [3/3] Opening Dashboard in Web Browser...
start http://127.0.0.1:8080/

exit
