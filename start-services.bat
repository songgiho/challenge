@echo off
echo ========================================
echo   FoodCalorie 백엔드 서비스 시작
echo ========================================

echo.
echo [1/4] Redis 서버 시작 중...
start "Redis Server" cmd /k "cd /d %~dp0redis-windows && redis-server.exe --port 6379"

echo.
echo [2/4] 3초 대기 (Redis 시작 대기)...
timeout /t 3 /nobreak > nul

echo.
echo [3/4] Celery 워커 시작 중...
start "Celery Worker" cmd /k "cd /d %~dp0 && uv run celery -A config worker -l info --pool=solo"

echo.
echo [4/4] Django 서버 시작 중...
echo Django 서버가 시작됩니다. 브라우저에서 http://localhost:8000 으로 접속하세요.
echo.
uv run manage.py runserver

echo.
echo 모든 서비스가 종료되었습니다.
pause