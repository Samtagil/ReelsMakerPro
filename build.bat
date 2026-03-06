@echo off
setlocal enabledelayedexpansion

rem Переход в каталог проекта (расположение этого скрипта)
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

rem Определяем команду Python: сначала пробуем py, затем python
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=py -3"
) else (
    set "PYTHON_CMD=python"
)

echo Используется интерпретатор: %PYTHON_CMD%

if not exist "venv" (
    echo Создание виртуального окружения...
    %PYTHON_CMD% -m venv venv
    if errorlevel 1 (
        echo Ошибка при создании виртуального окружения.
        exit /b 1
    )
)

echo Активация виртуального окружения...
call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo Не удалось активировать виртуальное окружение.
    exit /b 1
)

echo Обновление pip и установка зависимостей...
%PYTHON_CMD% -m pip install --upgrade pip
if exist "requirements.txt" (
    %PYTHON_CMD% -m pip install -r requirements.txt
)

echo Установка/обновление PyInstaller...
%PYTHON_CMD% -m pip install --upgrade pyinstaller

echo Запуск скрипта сборки EXE и установщика...
%PYTHON_CMD% build_exe.py --installer
set "BUILD_EXIT_CODE=%ERRORLEVEL%"

rem Попытка деактивировать окружение (если доступна команда deactivate)
deactivate 2>nul

if not "%BUILD_EXIT_CODE%"=="0" (
    echo Сборка завершилась с ошибкой. Код: %BUILD_EXIT_CODE%.
    exit /b %BUILD_EXIT_CODE%
)

echo.
echo Сборка успешно завершена.
echo   - Портативный EXE: dist\ReelsMakerPro.exe
echo   - Установщик для пользователей: dist\ReelsMakerPro-Setup.exe
echo Распространяйте ReelsMakerPro-Setup.exe — пользователю достаточно запустить его, Python не нужен.

endlocal
exit /b 0

