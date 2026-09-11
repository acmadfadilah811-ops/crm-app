@echo off
REM Uninstall Horilla-CRM Windows Service

echo Uninstalling Horilla-CRM Windows Service...

cd /d "%~dp0\.."

REM Check if running as administrator
net session >nul 2>&1
if errorlevel 1 (
    echo ERROR: This script must be run as Administrator
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Stop the service if running
echo Stopping service...
net stop HorillaCRM >nul 2>&1

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Remove the service
echo Removing service...
python scripts\horilla_service.py remove

if errorlevel 1 (
    echo WARNING: Failed to remove service cleanly
    echo You may need to remove it manually from Services
) else (
    echo Service removed successfully!
)

pause
