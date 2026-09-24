#!/usr/bin/env python3
"""Small Windows installer wrapper for MazeInt.

This helper downloads the latest published Windows EXE zip from a GitHub release,
extracts it to the user's local app folder, and launches the app.

Update RELEASE_URL to your repository's public release URL before publishing.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

RELEASE_URL = "https://github.com/your-org/your-repo/releases/latest/download/MazeIntDigitizer-Windows.zip"
APP_NAME = "MazeIntDigitizer"
TARGET_DIR = Path.home() / "AppData" / "Local" / APP_NAME


def ensure_windows() -> None:
    if platform.system().lower() != "windows":
        raise SystemExit("This wrapper is for Windows only.")


def download_file(url: str, dest: Path) -> None:
    print(f"Downloading {url}")
    urllib.request.urlretrieve(url, str(dest))


def extract_zip(zip_path: Path, out_dir: Path) -> None:
    print(f"Extracting {zip_path.name} to {out_dir}")
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(out_dir)


def launch_exe(exe_path: Path) -> None:
    print(f"Launching {exe_path}")
    subprocess.Popen([str(exe_path)])


def main() -> int:
    ensure_windows()
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        archive = tmp / "MazeIntDigitizer-Windows.zip"
        try:
            download_file(RELEASE_URL, archive)
        except Exception as exc:
            print(f"Download failed: {exc}")
            print("Please update RELEASE_URL in windows_installer_wrapper.py to point to your real GitHub release asset.")
            return 1

        extract_zip(archive, TARGET_DIR)

        exe_candidates = [
            TARGET_DIR / "MazeIntDigitizer.exe",
            TARGET_DIR / "dist" / "MazeIntDigitizer.exe",
            TARGET_DIR / "MazeIntDigitizer" / "MazeIntDigitizer.exe",
        ]
        exe = next((path for path in exe_candidates if path.exists()), None)
        if exe is None:
            print("No executable was found after extraction.")
            print(f"Checked: {[str(p) for p in exe_candidates]}")
            return 1

        launch_exe(exe)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
