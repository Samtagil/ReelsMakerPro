@echo off
if "%~1"=="__run__" goto :main
cmd /k "%~f0" __run__
exit /b

:main
chcp 65001 >nul
set PYTHONUTF8=1
setlocal
cd /d "%~dp0"

set "PY_DIR=%~dp0python"
set "PY_EXE=%PY_DIR%\python.exe"

:: Всегда используем только локальную папку python\ (без системного py/python)
:: Если её нет — скачиваем встроенный Python один раз (через отдельный .ps1, чтобы не ломать скобки в bat)
if not exist "%PY_EXE%" (
    echo Python не найден. Скачиваю встроенный Python, один раз, нужен интернет...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_python_embed.ps1"
    if errorlevel 1 (
        echo Ошибка загрузки Python. Проверьте интернет и повторите.
        pause
        exit /b 1
    )
)

:: Добавить Lib/site-packages в ._pth, чтобы python.exe -m pip и скрипты видели пакеты
powershell -NoProfile -Command "Get-ChildItem '%PY_DIR%\python*._pth' -ErrorAction SilentlyContinue | ForEach-Object { $c = Get-Content $_.FullName -Raw; if ($c -and $c -notmatch 'Lib/site-packages') { Add-Content -Path $_.FullName -Value 'Lib/site-packages' } }"

:do_build
echo/
echo Установка зависимостей (pip, требования, PyInstaller)...
"%PY_EXE%" -m pip install --upgrade pip -q
"%PY_EXE%" -m pip install -r requirements.txt -q
"%PY_EXE%" -m pip install pyinstaller -q

echo/
echo Сборка приложения ReelsMakerPro.exe (скачивание ffmpeg/yt-dlp, PyInstaller)...
"%PY_EXE%" build_exe.py
if errorlevel 1 (
    echo Сборка приложения не удалась.
    pause
    exit /b 1
)

echo/
echo Сборка установщика ReelsMakerPro-Setup.exe...
"%PY_EXE%" build_setup_exe.py
if errorlevel 1 (
    echo Сборка установщика не удалась.
    pause
    exit /b 1
)

echo/
echo Готово.
echo   Установщик: dist\ReelsMakerPro-Setup.exe
echo   Портативный EXE: dist\ReelsMakerPro.exe
pause
endlocal
exit /b 0
