@echo off
echo ========================================
echo   FoodCalorie 백엔드 서비스 종료
echo ========================================

echo.
echo Redis 서버 종료 중...
taskkill /f /im redis-server.exe 2>nul
if %errorlevel% == 0 (
    echo Redis 서버가 종료되었습니다.
) else (
    echo Redis 서버가 실행 중이지 않습니다.
)

echo.
echo Celery 워커 종료 중...
taskkill /f /im python.exe /fi "WINDOWTITLE eq Celery Worker*" 2>nul
if %errorlevel% == 0 (
    echo Celery 워커가 종료되었습니다.
) else (
    echo Celery 워커가 실행 중이지 않습니다.
)

echo.
echo Django 서버 종료 중...
taskkill /f /im python.exe /fi "WINDOWTITLE eq Django*" 2>nul

echo.
echo 모든 서비스가 종료되었습니다.
pause