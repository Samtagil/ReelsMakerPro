"""
Скрипт установщика: копирует ReelsMakerPro.exe в папку пользователя и создаёт ярлыки.
Собирается в ReelsMakerPro-Setup.exe через PyInstaller с --add-data dist/ReelsMakerPro.exe;app
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

APP_NAME = "ReelsMaker Pro"
EXE_NAME = "ReelsMakerPro.exe"


def get_bundled_exe_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) / "app"
    else:
        base = Path(__file__).resolve().parent / "app"
    exe = base / EXE_NAME
    if not exe.exists():
        raise FileNotFoundError(f"Не найден встроенный {EXE_NAME} в {base}")
    return exe


def get_install_dir() -> Path:
    local = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    return Path(local) / "ReelsMakerPro"


def create_shortcut(target_exe: Path, shortcut_path: Path, description: str = APP_NAME) -> None:
    shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    ps = f'''
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("{shortcut_path}")
$s.TargetPath = "{target_exe}"
$s.WorkingDirectory = "{target_exe.parent}"
$s.Description = "{description}"
$s.Save()
'''
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        check=True,
        capture_output=True,
    )


def main() -> None:
    try:
        src = get_bundled_exe_path()
    except FileNotFoundError as e:
        print(str(e))
        input("Нажмите Enter для выхода...")
        sys.exit(1)

    install_dir = get_install_dir()
    install_dir.mkdir(parents=True, exist_ok=True)
    dest = install_dir / EXE_NAME

    print(f"Установка в {install_dir}")
    shutil.copy2(src, dest)

    start_menu = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    if start_menu.exists():
        create_shortcut(dest, start_menu / f"{APP_NAME}.lnk")
        print("Ярлык в меню «Пуск» создан.")

    desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
    if desktop.exists():
        create_shortcut(dest, desktop / f"{APP_NAME}.lnk")
        print("Ярлык на рабочем столе создан.")

    print(f"\nГотово. {APP_NAME} установлен в:\n  {install_dir}")
    print("\nЗапустить сейчас? (да/нет): ", end="")
    if input().strip().lower() in ("да", "yes", "y", "д"):
        os.startfile(str(dest))


if __name__ == "__main__":
    main()
