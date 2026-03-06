import argparse
import io
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen

# Консоль на Windows (в т.ч. GitHub Actions) часто в cp1252 — принудительно UTF-8 для вывода
if sys.platform == "win32":
    try:
        if sys.stdout is not None and getattr(sys.stdout, "encoding", "").lower() not in ("utf-8", "utf8"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        if sys.stderr is not None and getattr(sys.stderr, "encoding", "").lower() not in ("utf-8", "utf8"):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

ROOT_DIR = Path(__file__).resolve().parent


def _get_short_path(path: Path) -> Path:
    """Возвращает короткий (8.3) путь для Windows — только ASCII, обходит баги с кириллицей в PyInstaller."""
    if sys.platform != "win32":
        return path
    path_str = str(path.resolve())
    if not path_str or not path.exists():
        return path
    try:
        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        n = ctypes.windll.kernel32.GetShortPathNameW(path_str, buf, wintypes.MAX_PATH)
        if n and n < wintypes.MAX_PATH:
            return Path(buf.value)
    except Exception:
        pass
    return path
BIN_DIR = ROOT_DIR / "bin"
RESOURCES_DIR = ROOT_DIR / "resources"

YTDLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def download_file(url: str, destination: Path) -> None:
    print(f"Скачивание {url} -> {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=60) as response, destination.open("wb") as out_file:
        shutil.copyfileobj(response, out_file)


def download_file_with_progress(url: str, destination: Path, label: str = "Скачивание") -> None:
    """Скачивает файл и выводит прогресс по мере загрузки (каждые ~5 МБ)."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f"{label}: {url}")
    print("Файл большой (~70 МБ), подождите, идёт загрузка...")
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python-build"})
        with urlopen(req, timeout=300) as response:
            total = response.headers.get("Content-Length")
            total_mb = int(total) / (1024 * 1024) if total else None
            chunk_size = 512 * 1024  # 512 КБ
            downloaded = 0
            step_mb = 5
            next_print_mb = step_mb
            with destination.open("wb") as out_file:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    downloaded_mb = downloaded / (1024 * 1024)
                    if total_mb and downloaded_mb >= next_print_mb:
                        pct = 100 * downloaded / int(total) if total else 0
                        print(f"  {downloaded_mb:.1f} / {total_mb:.1f} МБ ({pct:.0f}%)")
                        next_print_mb += step_mb
                    elif not total_mb and downloaded_mb >= next_print_mb:
                        print(f"  {downloaded_mb:.1f} МБ...")
                        next_print_mb += step_mb
        print("  Готово.")
    except Exception as e:
        if destination.exists():
            destination.unlink(missing_ok=True)
        raise e


def ensure_yt_dlp() -> None:
    target = BIN_DIR / "yt-dlp.exe"
    if target.exists():
        print(f"Найден yt-dlp: {target}")
        return

    try:
        download_file(YTDLP_URL, target)
        print(f"yt-dlp успешно сохранён в {target}")
    except Exception as exc:
        raise RuntimeError(f"Не удалось скачать yt-dlp: {exc}") from exc


def _extract_ffmpeg_binaries(zip_path: Path, ffmpeg_path: Path, ffprobe_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "r") as zf:
        members = zf.namelist()
        ffmpeg_member = next((m for m in members if m.endswith("bin/ffmpeg.exe")), None)
        ffprobe_member = next((m for m in members if m.endswith("bin/ffprobe.exe")), None)

        if not ffmpeg_member or not ffprobe_member:
            raise RuntimeError("В архиве FFmpeg не найдены ffmpeg.exe или ffprobe.exe")

        with zf.open(ffmpeg_member) as src, ffmpeg_path.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        with zf.open(ffprobe_member) as src, ffprobe_path.open("wb") as dst:
            shutil.copyfileobj(src, dst)


def ensure_ffmpeg() -> None:
    ffmpeg_path = BIN_DIR / "ffmpeg.exe"
    ffprobe_path = BIN_DIR / "ffprobe.exe"

    if ffmpeg_path.exists() and ffprobe_path.exists():
        print(f"Найдены ffmpeg/ffprobe в {BIN_DIR}")
        return

    BIN_DIR.mkdir(parents=True, exist_ok=True)

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_zip = Path(tmp_dir) / "ffmpeg.zip"
            download_file_with_progress(FFMPEG_ZIP_URL, tmp_zip, label="Скачивание FFmpeg")
            print("Распаковка ffmpeg.exe и ffprobe.exe...")
            _extract_ffmpeg_binaries(tmp_zip, ffmpeg_path, ffprobe_path)
        print(f"FFmpeg и FFprobe успешно сохранены в {BIN_DIR}")
    except Exception as exc:
        raise RuntimeError(f"Не удалось скачать или распаковать FFmpeg: {exc}") from exc


def clean_previous_build() -> None:
    for name in ("build", "dist"):
        path = ROOT_DIR / name
        if path.exists():
            print(f"Удаление {path}")
            shutil.rmtree(path, ignore_errors=True)

    for spec_name in ("ReelsMakerPro.spec", "main.spec"):
        spec_path = ROOT_DIR / spec_name
        if spec_path.exists():
            print(f"Удаление {spec_path}")
            spec_path.unlink(missing_ok=True)


def _path_has_non_ascii(p: Path) -> bool:
    return any(ord(c) > 127 for c in str(p))


def _make_spec_content(work_dir: Path, script: str, icon_path: Optional[Path], bin_dir: Path, resources_dir: Path, py_exe: Path) -> str:
    """Генерирует содержимое .spec с исключением torch/whisper из анализа (обход access violation при импорте в подпроцессе)."""
    sp = py_exe.resolve().parent / "Lib" / "site-packages"
    datas = [
        (str(bin_dir), "bin"),
        (str(resources_dir), "resources"),
    ]
    excludes = []
    if (sp / "torch").is_dir():
        datas.append((str(sp / "torch"), "torch"))
        excludes.append("torch")
    if (sp / "whisper").is_dir():
        datas.append((str(sp / "whisper"), "whisper"))
        excludes.append("whisper")

    def q(s: str) -> str:
        return repr(s)

    script_path = work_dir / script
    script_q = q(str(script_path))
    datas_py = ",\n        ".join(f"({q(src)}, {q(dest)})" for src, dest in datas)
    excludes_py = repr(excludes) if excludes else "[]"
    icon_block = ""
    if icon_path and icon_path.exists():
        icon_block = f"\n    icon={q(str(icon_path))},"

    return f"""# -*- mode: python ; coding: utf-8 -*-
# Spec сгенерирован build_exe.py: torch/whisper исключены из анализа и добавлены как datas (обход access violation).

a = Analysis(
    [{script_q}],
    pathex=[{q(str(work_dir))}],
    binaries=[],
    datas=[
        {datas_py}
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes={excludes_py},
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ReelsMakerPro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,{icon_block}
)
"""


def _build_via_junction() -> None:
    """Сборка через junction в TEMP (путь только латиница) — обход бага PyInstaller с кириллицей."""
    link = Path(tempfile.gettempdir()) / "Reelsexe_build"
    try:
        if link.exists():
            subprocess.run(["cmd", "/c", "rmdir", str(link)], check=True, capture_output=True)
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(ROOT_DIR.resolve())], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Не удалось создать связку каталогов в {link}. "
            "Перенесите проект в папку без кириллицы (например D:\\Reelsexe) и запустите сборку снова."
        ) from e

    try:
        py_exe = link / "python" / "python.exe"
        if not py_exe.exists():
            raise RuntimeError(f"В связке не найден {py_exe}")
        icon_path = link / "resources" / "icon.ico"
        spec_content = _make_spec_content(
            work_dir=link,
            script="main.py",
            icon_path=icon_path,
            bin_dir=link / "bin",
            resources_dir=link / "resources",
            py_exe=py_exe,
        )
        spec_path = link / "ReelsMakerPro.spec"
        spec_path.write_text(spec_content, encoding="utf-8")
        cmd = [
            str(py_exe),
            "-m", "PyInstaller",
            "--noconfirm", "--clean",
            str(spec_path),
        ]

        print("Запуск PyInstaller из каталога без кириллицы:", link)
        print("Используется .spec: torch/whisper исключены из анализа (обход access violation).")
        print()
        print(" ".join(cmd))
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        r = subprocess.run(cmd, cwd=str(link), env=env)
        if r.returncode != 0:
            raise RuntimeError(f"PyInstaller завершился с кодом {r.returncode}")
        # Junction — та же папка, что и ROOT_DIR, dist/build уже в проекте
    finally:
        if link.exists():
            subprocess.run(["cmd", "/c", "rmdir", str(link)], capture_output=True)


def build_pyinstaller() -> None:
    # Если в пути есть кириллица — собираем через junction в TEMP (только латиница)
    if sys.platform == "win32" and _path_has_non_ascii(ROOT_DIR):
        _build_via_junction()
        return

    work_dir = _get_short_path(ROOT_DIR) if sys.platform == "win32" else ROOT_DIR
    icon_path = RESOURCES_DIR / "icon.ico"
    py_exe = _get_short_path(Path(sys.executable).resolve()) if sys.platform == "win32" else Path(sys.executable)
    bin_dir = _get_short_path(BIN_DIR) if sys.platform == "win32" else BIN_DIR
    resources_dir = _get_short_path(RESOURCES_DIR) if sys.platform == "win32" else RESOURCES_DIR

    spec_content = _make_spec_content(
        work_dir=work_dir,
        script="main.py",
        icon_path=icon_path,
        bin_dir=bin_dir,
        resources_dir=resources_dir,
        py_exe=py_exe,
    )
    spec_path = work_dir / "ReelsMakerPro.spec"
    spec_path.write_text(spec_content, encoding="utf-8")
    cmd = [
        str(py_exe),
        "-m", "PyInstaller",
        "--noconfirm", "--clean",
        str(spec_path),
    ]

    if not icon_path.exists():
        print("Предупреждение: resources/icon.ico не найден, сборка будет без иконки.")
    print("Запуск PyInstaller (torch/whisper исключены из анализа — обход access violation):")
    print(" ".join(cmd))
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    completed = subprocess.run(cmd, cwd=str(work_dir), env=env)
    if completed.returncode != 0:
        raise RuntimeError(f"PyInstaller завершился с кодом {completed.returncode}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Сборка ReelsMakerPro в EXE и опционально в установщик Windows.")
    parser.add_argument(
        "--installer",
        action="store_true",
        help="После сборки EXE создать установщик ReelsMakerPro-Setup.exe (нужен Inno Setup)",
    )
    parser.add_argument(
        "--installer-only",
        action="store_true",
        help="Только собрать установщик (нужны dist/ReelsMakerPro.exe и Inno Setup)",
    )
    args = parser.parse_args()

    if args.installer_only:
        build_installer()
        return

    print("=== Сборка ReelsMakerPro в единый EXE ===")
    print(f"Корень проекта: {ROOT_DIR}")

    BIN_DIR.mkdir(parents=True, exist_ok=True)

    ensure_yt_dlp()
    ensure_ffmpeg()

    clean_previous_build()
    build_pyinstaller()

    exe_path = ROOT_DIR / "dist" / "ReelsMakerPro.exe"
    if exe_path.exists():
        print(f"Сборка EXE завершена. Файл: {exe_path}")
    else:
        print("Сборка завершена, но ReelsMakerPro.exe не найден в папке dist.")
        return

    if args.installer:
        try:
            build_installer()
        except Exception as e:
            print(f"\nУстановщик не создан: {e}")
            print("Чтобы получить ReelsMakerPro-Setup.exe:")
            print("  1. Установите Inno Setup: https://jrsoftware.org/isinfo.php")
            print("  2. Запустите: build_installer_only.bat")
            sys.exit(1)


def _find_iscc() -> Optional[Path]:
    """Ищет компилятор Inno Setup (ISCC.exe)."""
    iscc = shutil.which("iscc")
    if iscc:
        return Path(iscc)
    for path in (
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 5\ISCC.exe"),
    ):
        if path.exists():
            return path
    return None


def build_installer() -> None:
    """Собирает установщик ReelsMakerPro-Setup.exe с помощью Inno Setup."""
    exe_path = ROOT_DIR / "dist" / "ReelsMakerPro.exe"
    if not exe_path.exists():
        raise RuntimeError("Сначала соберите EXE: ReelsMakerPro.exe не найден в dist/")

    iscc = _find_iscc()
    if not iscc:
        raise RuntimeError(
            "Inno Setup не найден. Установите с https://jrsoftware.org/isinfo.php "
            "и добавьте в PATH, либо запустите сборку на машине с Inno Setup 5/6."
        )

    iss_path = ROOT_DIR / "ReelsMakerPro.iss"
    if not iss_path.exists():
        raise RuntimeError(f"Файл скрипта установщика не найден: {iss_path}")

    print("Сборка установщика Windows (Inno Setup)...")
    cmd = [str(iscc), str(iss_path)]
    completed = subprocess.run(cmd, cwd=ROOT_DIR)
    if completed.returncode != 0:
        raise RuntimeError(f"Inno Setup завершился с кодом {completed.returncode}")

    setup_path = ROOT_DIR / "dist" / "ReelsMakerPro-Setup.exe"
    if setup_path.exists():
        print(f"Установщик создан: {setup_path}")
    else:
        print("Компиляция прошла, но ReelsMakerPro-Setup.exe не найден в dist/.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Сборка прервана пользователем.")
        sys.exit(1)
    except Exception as e:
        print(f"ОШИБКА: {e}")
        sys.exit(1)

