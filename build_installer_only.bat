@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (set "PYTHON_CMD=py -3") else (set "PYTHON_CMD=python")

if not exist "dist\ReelsMakerPro.exe" (
    echo Ошибка: сначала соберите EXE. Запустите build.bat
    exit /b 1
)

if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)

echo Сборка только установщика ReelsMakerPro-Setup.exe...
%PYTHON_CMD% build_exe.py --installer-only
set "EXIT_CODE=%ERRORLEVEL%"
if %EXIT_CODE% neq 0 (
    echo.
    echo Установите Inno Setup: https://jrsoftware.org/isinfo.php
    echo Затем снова запустите build_installer_only.bat
    exit /b %EXIT_CODE%
)
echo Готово: dist\ReelsMakerPro-Setup.exe
endlocal
exit /b 0
