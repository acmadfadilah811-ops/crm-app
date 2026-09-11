@echo off
REM Setup Environment for Horilla-CRM

echo Setting up Horilla-CRM environment...

cd /d "%~dp0\.."

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.12+ and try again
    pause
    exit /b 1
)

REM Create virtual environment
echo Creating Python virtual environment...
if not exist "venv" (
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo Installing Python dependencies...
if exist "requirements.txt" (
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install requirements
        pause
        exit /b 1
    )
)

REM Install additional Windows dependencies
echo Installing Windows-specific dependencies...
pip install gunicorn==22.0.0 whitenoise==6.7.0 psycopg2-binary==2.9.9
pip install pywin32 python-windows-service

REM Create necessary directories
echo Creating application directories...
if not exist "%APPDATA%\Horilla-CRM\data" mkdir "%APPDATA%\Horilla-CRM\data"
if not exist "%APPDATA%\Horilla-CRM\logs" mkdir "%APPDATA%\Horilla-CRM\logs"
if not exist "%APPDATA%\Horilla-CRM\media" mkdir "%APPDATA%\Horilla-CRM\media"
if not exist "%APPDATA%\Horilla-CRM\config" mkdir "%APPDATA%\Horilla-CRM\config"

REM Copy default configuration if it doesn't exist
if not exist "%APPDATA%\Horilla-CRM\config\horilla-crm.conf" (
    copy "config\horilla-crm.conf" "%APPDATA%\Horilla-CRM\config\"
)

echo Environment setup completed successfully!
echo.
echo Run the following commands to get started:
echo   horilla-crm-start.bat    - Start the application
echo   horilla-crm-admin.bat    - Access admin commands
echo.
pause
