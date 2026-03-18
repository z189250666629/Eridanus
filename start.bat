@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo Eridanus Bot
echo =============
echo.

python main.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Bot exited with code %ERRORLEVEL%
)

echo.
pause
