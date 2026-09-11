@echo off
REM Stop Horilla-CRM Application

echo Stopping Horilla-CRM...

REM Stop Windows service if running
sc query "HorillaCRM" >nul 2>&1
if not errorlevel 1 (
    echo Stopping Horilla-CRM service...
    net stop HorillaCRM
)

REM Kill any running Python processes for Horilla-CRM
echo Checking for running processes...
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV ^| find "python.exe"') do (
    set PID=%%i
    set PID=!PID:"=!
    echo Stopping process !PID!
    taskkill /PID !PID! /F >nul 2>&1
)

REM Kill any running Gunicorn processes
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq gunicorn.exe" /FO CSV ^| find "gunicorn.exe"') do (
    set PID=%%i
    set PID=!PID:"=!
    echo Stopping Gunicorn process !PID!
    taskkill /PID !PID! /F >nul 2>&1
)

echo Horilla-CRM stopped.
pause
