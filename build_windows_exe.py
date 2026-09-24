#!/usr/bin/env python3
"""Build a Windows .exe for the MazeInt GUI using PyInstaller.

Run this on a Windows machine or in a GitHub Actions Windows runner.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
SPEC_FILE = ROOT / "MazeIntDigitizer.spec"


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
        return
    except Exception:
        pass
    run([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0"])


def clean() -> None:
    for folder in [DIST_DIR, BUILD_DIR]:
        if folder.exists():
            shutil.rmtree(folder)
    if SPEC_FILE.exists():
        SPEC_FILE.unlink()


def build() -> Path:
    ensure_pyinstaller()
    clean()
    run([
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        "MazeIntDigitizer",
        "--hidden-import=mazeint_digitizer.core",
        "--hidden-import=mazeint_digitizer.gui",
        "--collect-all=pyembroidery",
        "mazeint_digitizer/gui.py",
    ])
    exe = DIST_DIR / "MazeIntDigitizer.exe"
    if not exe.exists():
        raise FileNotFoundError(f"Expected EXE was not created: {exe}")
    return exe


def main() -> int:
    exe = build()
    print(f"Created Windows executable: {exe}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
