#!/usr/bin/env python3
"""Self-healing installer for MazeInt embroidery digitizer.

This installer auto-detects the host OS and selects the correct Python/venv flow,
then installs the required dependencies and the project itself. If anything fails,
it recreates the environment and retries once before exiting with a clear error.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".mazeint_venv"


def detect_os() -> str:
    system = platform.system().lower()
    release = platform.release().lower()
    chrome_flags = (
        "chrome" in release,
        "cros" in release,
        "chromebook" in release,
        os.path.exists("/mnt/chromeos"),
    )
    if system == "windows":
        return "windows"
    if system == "linux" and any(chrome_flags):
        return "chromeos"
    if system == "linux":
        return "linux"
    if system == "darwin":
        return "macos"
    return "unknown"


def find_python_candidates() -> list[str]:
    os_name = detect_os()
    if os_name == "windows":
        return ["py", "python", "python3"]
    return ["python3", "python"]


def run_command(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=str(ROOT), capture_output=capture, text=True)


def check_python_version(python_exe: str) -> None:
    result = run_command([python_exe, "--version"], capture=True)
    if result.returncode != 0:
        raise RuntimeError(f"Python interpreter not usable: {python_exe}")


def resolve_python() -> str:
    for candidate in find_python_candidates():
        try:
            check_python_version(candidate)
            return candidate
        except Exception:
            continue
    raise RuntimeError("No usable Python interpreter was found on this system.")


def venv_python() -> str:
    if detect_os() == "windows":
        return str(VENV_DIR / "Scripts" / "python.exe")
    return str(VENV_DIR / "bin" / "python")


def ensure_venv(python_exe: str) -> str:
    if VENV_DIR.exists():
        py_path = venv_python()
        if Path(py_path).exists():
            result = run_command([py_path, "--version"], capture=True)
            if result.returncode == 0:
                return py_path
        print(f"Existing environment is broken or stale. Rebuilding {VENV_DIR}...")
        shutil.rmtree(VENV_DIR)

    print(f"Creating virtual environment in {VENV_DIR}...")
    result = run_command([python_exe, "-m", "venv", str(VENV_DIR)], capture=True)
    if result.returncode != 0:
        msg = result.stderr.strip() or result.stdout.strip() or "unknown venv creation failure"
        raise RuntimeError(f"Failed to create a virtual environment: {msg}")
    return venv_python()


def install_dependencies(python_exe: str) -> None:
    print("Installing pip/build tooling...")
    result = run_command([python_exe, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    if result.returncode != 0:
        raise RuntimeError(f"Failed to upgrade pip: {result.stderr or result.stdout}")

    print("Installing project requirements...")
    requirements = ROOT / "requirements.txt"
    if not requirements.exists():
        raise RuntimeError(f"Missing requirements file: {requirements}")
    result = run_command([python_exe, "-m", "pip", "install", "-r", str(requirements)])
    if result.returncode != 0:
        raise RuntimeError(f"Failed to install requirements: {result.stderr or result.stdout}")

    print("Installing project in editable mode...")
    result = run_command([python_exe, "-m", "pip", "install", "-e", str(ROOT)])
    if result.returncode != 0:
        raise RuntimeError(f"Failed to install project package: {result.stderr or result.stdout}")


def validate_install(python_exe: str) -> None:
    test_cmd = [
        python_exe,
        "-c",
        "import cv2, numpy, shapely, pyembroidery, mazeint_digitizer; print('validation-ok')",
    ]
    result = run_command(test_cmd, capture=True)
    if result.returncode != 0:
        raise RuntimeError(f"Environment validation failed: {result.stderr or result.stdout}")
    print("Validation succeeded: required packages and project imports are available.")


def create_launchers() -> None:
    if detect_os() == "windows":
        launcher = ROOT / "run_gui.bat"
        launcher.write_text(
            "@echo off\n"
            'setlocal\n'
            'cd /d "%~dp0"\n'
            '"%~dp0\\.mazeint_venv\\Scripts\\python.exe" -m mazeint_digitizer.gui\n',
            encoding="utf-8",
        )
        print(f"Launcher created: {launcher}")
        return

    launcher = ROOT / "run_gui.sh"
    launcher.write_text(
        "#!/usr/bin/env bash\n"
        "set -e\n"
        "cd \"$(dirname \"$0\")\"\n"
        "\"$(dirname \"$0\")/.mazeint_venv/bin/python\" -m mazeint_digitizer.gui\n",
        encoding="utf-8",
    )
    os.chmod(launcher, 0o755)
    print(f"Launcher created: {launcher}")


def install(start_gui: bool = False) -> int:
    os_name = detect_os()
    if os_name == "unknown":
        raise RuntimeError("Unsupported OS detected; this installer supports Windows, Linux, ChromeOS, and macOS.")

    print(f"Detected OS: {os_name}")
    py = resolve_python()
    print(f"Using Python interpreter: {py}")

    try:
        venv_py = ensure_venv(py)
        install_dependencies(venv_py)
        validate_install(venv_py)
        create_launchers()
        print("\nInstall complete.")
        print(f"Virtual environment: {VENV_DIR}")
        print("Launch the GUI with:")
        if os_name == "windows":
            print("  run_gui.bat")
        else:
            print("  ./run_gui.sh")
        if start_gui:
            print("Starting GUI now...")
            gui_cmd = [venv_py, "-m", "mazeint_digitizer.gui"]
            result = run_command(gui_cmd)
            return result.returncode
        return 0
    except Exception as exc:
        print(f"Installation failed: {exc}")
        print("Attempting self-healing recovery by rebuilding the environment...")
        if VENV_DIR.exists():
            shutil.rmtree(VENV_DIR)
        try:
            venv_py = ensure_venv(py)
            install_dependencies(venv_py)
            validate_install(venv_py)
            create_launchers()
            print("\nRecovery install succeeded.")
            if start_gui:
                print("Starting GUI now...")
                result = run_command([venv_py, "-m", "mazeint_digitizer.gui"])
                return result.returncode
            return 0
        except Exception as retry_exc:
            print(f"Recovery failed: {retry_exc}")
            raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Self-healing MazeInt installer")
    parser.add_argument("--launch-gui", action="store_true", help="Launch the GUI after installation")
    args = parser.parse_args()
    try:
        return install(start_gui=args.launch_gui)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"Fatal error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
