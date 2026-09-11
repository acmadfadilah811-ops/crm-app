@echo off
REM Start Horilla-CRM Application

setlocal enabledelayedexpansion

echo Starting Horilla-CRM...

cd /d "%~dp0\.."

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found
    echo Please run setup-environment.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Set environment variables
set DJANGO_SETTINGS_MODULE=horilla.settings
set PYTHONPATH=%CD%

REM Load configuration from file
set CONFIG_FILE=%APPDATA%\Horilla-CRM\config\horilla-crm.conf
if exist "%CONFIG_FILE%" (
    for /f "usebackq tokens=1,2 delims==" %%a in ("%CONFIG_FILE%") do (
        set "%%a=%%b"
    )
)

REM Run database migrations
echo Running database migrations...
python manage.py migrate --noinput
if errorlevel 1 (
    echo ERROR: Database migration failed
    pause
    exit /b 1
)

REM Collect static files
echo Collecting static files...
python manage.py collectstatic --noinput

REM Check if port is available
echo Checking if port 8000 is available...
netstat -an | find "127.0.0.1:8000" >nul
if not errorlevel 1 (
    echo WARNING: Port 8000 is already in use
    echo Another instance might be running
)

REM Start the server
echo Starting Horilla-CRM server on http://127.0.0.1:8000
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start Gunicorn server
gunicorn ^
    --bind 127.0.0.1:8000 ^
    --workers 3 ^
    --timeout 120 ^
    --access-logfile "%APPDATA%\Horilla-CRM\logs\access.log" ^
    --error-logfile "%APPDATA%\Horilla-CRM\logs\error.log" ^
    --log-level info ^
    horilla.wsgi:application

echo Server stopped.
pause
