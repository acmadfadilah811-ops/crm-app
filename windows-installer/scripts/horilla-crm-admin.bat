@echo off
REM Horilla-CRM Administration Interface

setlocal enabledelayedexpansion

echo Horilla-CRM Administration Interface
echo ===================================

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

:menu
echo.
echo Available commands:
echo 1. Create superuser
echo 2. Run database migrations
echo 3. Collect static files
echo 4. Open Django shell
echo 5. Run tests
echo 6. Show application status
echo 7. View logs
echo 8. Reset database (WARNING: This will delete all data!)
echo 9. Custom Django command
echo 0. Exit
echo.

set /p choice="Enter your choice (0-9): "

if "%choice%"=="1" goto create_superuser
if "%choice%"=="2" goto migrate
if "%choice%"=="3" goto collectstatic
if "%choice%"=="4" goto shell
if "%choice%"=="5" goto test
if "%choice%"=="6" goto status
if "%choice%"=="7" goto logs
if "%choice%"=="8" goto reset_db
if "%choice%"=="9" goto custom_command
if "%choice%"=="0" goto exit
goto menu

:create_superuser
echo Creating superuser...
python manage.py createsuperuser
goto menu

:migrate
echo Running database migrations...
python manage.py migrate
goto menu

:collectstatic
echo Collecting static files...
python manage.py collectstatic --noinput
goto menu

:shell
echo Opening Django shell...
python manage.py shell
goto menu

:test
echo Running tests...
python manage.py test
goto menu

:status
echo Application Status:
echo ===================
sc query "HorillaCRM" 2>nul
if errorlevel 1 (
    echo Service: Not installed
) else (
    echo Service: Installed
)

netstat -an | find "127.0.0.1:8000" >nul
if errorlevel 1 (
    echo Server: Not running on port 8000
) else (
    echo Server: Running on http://127.0.0.1:8000
)

echo.
echo Database status:
python manage.py check --database default
goto menu

:logs
echo Recent logs:
echo ===========
if exist "%APPDATA%\Horilla-CRM\logs\error.log" (
    echo Error log (last 20 lines):
    powershell "Get-Content '%APPDATA%\Horilla-CRM\logs\error.log' -Tail 20"
) else (
    echo No error log found
)
echo.
if exist "%APPDATA%\Horilla-CRM\logs\access.log" (
    echo Access log (last 10 lines):
    powershell "Get-Content '%APPDATA%\Horilla-CRM\logs\access.log' -Tail 10"
) else (
    echo No access log found
)
goto menu

:reset_db
echo WARNING: This will delete all data in the database!
set /p confirm="Are you sure? Type 'YES' to confirm: "
if not "%confirm%"=="YES" (
    echo Operation cancelled.
    goto menu
)

echo Resetting database...
if exist "db.sqlite3" del "db.sqlite3"
if exist "%APPDATA%\Horilla-CRM\data\db.sqlite3" del "%APPDATA%\Horilla-CRM\data\db.sqlite3"

python manage.py migrate
echo Database reset complete. You may need to create a new superuser.
goto menu

:custom_command
set /p command="Enter Django management command: "
echo Running: python manage.py %command%
python manage.py %command%
goto menu

:exit
echo Goodbye!
pause
