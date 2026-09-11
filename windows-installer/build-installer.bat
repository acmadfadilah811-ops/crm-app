@echo off
REM Build Horilla-CRM Windows Installer
REM Requires NSIS (Nullsoft Scriptable Install System)

setlocal enabledelayedexpansion

echo Building Horilla-CRM Windows Installer...
echo ==========================================

cd /d "%~dp0"

REM Check if NSIS is installed
where makensis >nul 2>&1
if errorlevel 1 (
    echo ERROR: NSIS not found in PATH
    echo.
    echo Please install NSIS from: https://nsis.sourceforge.io/
    echo After installation, add NSIS to your PATH or run:
    echo   "C:\Program Files (x86)\NSIS\makensis.exe" horilla-crm-installer.nsi
    echo.
    pause
    exit /b 1
)

REM Check if required files exist
echo Checking required files...

set REQUIRED_FILES=horilla-crm-installer.nsi scripts\horilla_service.py scripts\setup-environment.bat scripts\horilla-crm-start.bat scripts\horilla-crm-admin.bat scripts\horilla-crm-stop.bat scripts\install-service.bat scripts\uninstall-service.bat config\horilla-crm.conf config\logging.conf config\requirements-windows.txt

for %%f in (%REQUIRED_FILES%) do (
    if not exist "%%f" (
        echo ERROR: Required file not found: %%f
        pause
        exit /b 1
    )
)

REM Create default icons if they don't exist (placeholder files)
echo Creating default icons...
if not exist "icons" mkdir "icons"

if not exist "icons\horilla-icon.ico" (
    echo INFO: Default icon not found, using Windows default
    echo This is normal - you can add custom icons later
)

REM Copy LICENSE file
echo Preparing resources...
if not exist "resources" mkdir "resources"

if exist "..\LICENSE" (
    copy "..\LICENSE" "resources\LICENSE.txt" >nul
) else (
    echo License file not found - creating placeholder
    echo Horilla-CRM License > "resources\LICENSE.txt"
)

REM Create README for installation
echo Creating installation README...
(
echo Horilla-CRM Windows Installation
echo ================================
echo.
echo This installer will set up Horilla-CRM on your Windows system.
echo.
echo System Requirements:
echo - Windows 10 or later ^(64-bit^)
echo - Python 3.12 or later
echo - At least 2GB free disk space
echo - Administrator privileges for service installation
echo.
echo Installation Process:
echo 1. Core application files are installed to Program Files
echo 2. Configuration files are placed in your user AppData folder
echo 3. A Python virtual environment is created with dependencies
echo 4. Optional Windows service installation for background operation
echo.
echo After Installation:
echo - Access via Start Menu shortcuts
echo - Default URL: http://localhost:8000
echo - Admin interface: Use horilla-crm-admin.bat
echo.
echo For support, visit: https://github.com/horilla-opensource/horilla-crm
) > "resources\README.txt"

REM Build the installer
echo Building installer with NSIS...
makensis horilla-crm-installer.nsi

if errorlevel 1 (
    echo ERROR: Failed to build installer
    pause
    exit /b 1
)

REM Check if installer was created
if exist "Horilla-CRM-1.0.0-Setup.exe" (
    echo.
    echo SUCCESS: Installer built successfully!
    echo File: Horilla-CRM-1.0.0-Setup.exe
    echo Size:
    for %%f in ("Horilla-CRM-1.0.0-Setup.exe") do echo   %%~zf bytes
    echo.
    echo You can now distribute this installer to install Horilla-CRM on Windows systems.
    echo.

    REM Ask if user wants to test the installer
    set /p test_install="Do you want to test the installer now? (y/n): "
    if /i "!test_install!"=="y" (
        echo.
        echo Starting installer in test mode...
        echo WARNING: This will install Horilla-CRM on this system!
        timeout /t 5 /nobreak
        start "Horilla-CRM Installer" "Horilla-CRM-1.0.0-Setup.exe"
    )
) else (
    echo ERROR: Installer file not found after build
    exit /b 1
)

echo.
echo Build completed!
pause
