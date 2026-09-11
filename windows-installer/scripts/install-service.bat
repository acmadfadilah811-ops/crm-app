@echo off
REM Install Horilla-CRM as Windows Service

echo Installing Horilla-CRM Windows Service...

cd /d "%~dp0\.."

REM Check if running as administrator
net session >nul 2>&1
if errorlevel 1 (
    echo ERROR: This script must be run as Administrator
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install the service
echo Installing service...
python scripts\horilla_service.py install

if errorlevel 1 (
    echo ERROR: Failed to install service
    pause
    exit /b 1
)

REM Set service to start automatically
echo Configuring service for automatic startup...
sc config HorillaCRM start= auto

REM Start the service
echo Starting service...
net start HorillaCRM

if errorlevel 1 (
    echo WARNING: Service installed but failed to start
    echo You can start it manually from Services or by running:
    echo   net start HorillaCRM
) else (
    echo Service installed and started successfully!
    echo.
    echo The service will now start automatically when Windows boots.
    echo You can access Horilla-CRM at: http://127.0.0.1:8000
)

pause
