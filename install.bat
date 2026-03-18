@echo off
setlocal

set "SCRIPT_DIR=%~dp0"

REM If no arguments provided (double-click), default to --profile all
if "%~1"=="" (
    echo Eridanus Installer
    echo ===================
    echo.
    echo Installing all dependencies...
    echo.
    python "%SCRIPT_DIR%install.py" --profile all
) else (
    python "%SCRIPT_DIR%install.py" %*
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Installation failed with code %ERRORLEVEL%
)

echo.
pause
