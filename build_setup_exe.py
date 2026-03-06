"""
Собирает ReelsMakerPro-Setup.exe из simple_installer.py и dist/ReelsMakerPro.exe.
Inno Setup не нужен — установщик на Python (копия в папку пользователя + ярлыки).
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST_EXE = ROOT / "dist" / "ReelsMakerPro.exe"
# PyInstaller --add-data: на Windows разделитель ";", путь относительно cwd (ROOT)
APP_DATA = "dist" + os.sep + "ReelsMakerPro.exe;app"


def main() -> None:
    if not DIST_EXE.exists():
        print("Сначала соберите приложение: запустите build_exe.py (без --installer)")
        sys.exit(1)

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--name", "ReelsMakerPro-Setup",
        "--add-data", APP_DATA,
        "simple_installer.py",
    ]

    print("Сборка установщика ReelsMakerPro-Setup.exe...")
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        sys.exit(r.returncode)

    out = ROOT / "dist" / "ReelsMakerPro-Setup.exe"
    if out.exists():
        print(f"Готово: {out}")
    else:
        print("Ошибка: файл не создан.")


if __name__ == "__main__":
    main()
