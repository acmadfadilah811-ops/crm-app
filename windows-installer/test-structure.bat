@echo off
REM Test Horilla-CRM Windows Installer Structure

echo Testing Horilla-CRM Windows Installer Structure...
echo ==================================================

cd /d "%~dp0"

set ERRORS=0

echo Checking required files...

REM Check main installer script
if not exist "horilla-crm-installer.nsi" (
    echo ERROR: Main installer script not found
    set /a ERRORS+=1
) else (
    echo ✓ Main installer script found
)

REM Check scripts directory
if not exist "scripts\" (
    echo ERROR: Scripts directory not found
    set /a ERRORS+=1
) else (
    echo ✓ Scripts directory found

    REM Check individual scripts
    set SCRIPTS=horilla_service.py setup-environment.bat horilla-crm-start.bat horilla-crm-stop.bat horilla-crm-admin.bat install-service.bat uninstall-service.bat

    for %%s in (%SCRIPTS%) do (
        if not exist "scripts\%%s" (
            echo ERROR: Script not found: scripts\%%s
            set /a ERRORS+=1
        ) else (
            echo ✓ scripts\%%s
        )
    )
)

REM Check config directory
if not exist "config\" (
    echo ERROR: Config directory not found
    set /a ERRORS+=1
) else (
    echo ✓ Config directory found

    REM Check config files
    set CONFIGS=horilla-crm.conf logging.conf requirements-windows.txt

    for %%c in (%CONFIGS%) do (
        if not exist "config\%%c" (
            echo ERROR: Config file not found: config\%%c
            set /a ERRORS+=1
        ) else (
            echo ✓ config\%%c
        )
    )
)

REM Check build scripts
if not exist "build-installer.bat" (
    echo ERROR: Windows build script not found
    set /a ERRORS+=1
) else (
    echo ✓ Windows build script found
)

if not exist "build-installer.sh" (
    echo ERROR: Cross-platform build script not found
    set /a ERRORS+=1
) else (
    echo ✓ Cross-platform build script found
)

REM Check documentation
if not exist "README.md" (
    echo ERROR: Documentation not found
    set /a ERRORS+=1
) else (
    echo ✓ Documentation found
)

echo.
if %ERRORS% == 0 (
    echo SUCCESS: All required files found!
    echo.
    echo The installer structure is complete and ready for building.
    echo.
    echo To build the installer:
    echo 1. Install NSIS from: https://nsis.sourceforge.io/
    echo 2. Run: build-installer.bat
    echo.
    echo The installer will be named: Horilla-CRM-1.0.0-Setup.exe
) else (
    echo FAILED: %ERRORS% errors found!
    echo Please check the missing files above.
)

echo.
pause
