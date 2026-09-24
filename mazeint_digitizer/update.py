"""GitHub-based update checks and installer updates for MazeInt."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

REPO = "slinkykct/mint-digitizer"
GITHUB_API = f"https://api.github.com/repos/{REPO}"


def normalize_version(version: Optional[str]) -> tuple[int, ...]:
    if not version:
        return (0,)
    cleaned = str(version).strip().lower().replace("v", "")
    cleaned = cleaned.split("-")[0]
    cleaned = cleaned.split("+")[0]
    match = re.findall(r"\d+", cleaned)
    if not match:
        return (0,)
    return tuple(int(part) for part in match)


def has_update(current_version: Optional[str], latest_version: Optional[str]) -> bool:
    current = normalize_version(current_version)
    latest = normalize_version(latest_version)
    max_len = max(len(current), len(latest))
    current += (0,) * (max_len - len(current))
    latest += (0,) * (max_len - len(latest))
    return latest > current


def get_local_version() -> str:
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    try:
        text = pyproject.read_text(encoding="utf-8")
    except OSError:
        return "0.0.0"
    match = re.search(r'^version\s*=\s*"?([^"]+)"?', text, re.M)
    if match:
        return match.group(1)
    return "0.0.0"


def get_latest_release_info() -> tuple[str, str]:
    req = urllib.request.Request(
        f"{GITHUB_API}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "MazeInt-Updater"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    tag = payload.get("tag_name") or "0.0.0"
    html_url = payload.get("html_url") or f"https://github.com/{REPO}/releases"
    return str(tag), str(html_url)


def check_for_updates() -> dict:
    current = get_local_version()
    try:
        latest_tag, release_url = get_latest_release_info()
    except Exception:
        return {
            "current_version": current,
            "latest_version": current,
            "has_update": False,
            "release_url": f"https://github.com/{REPO}/releases",
            "error": "Unable to reach the GitHub release API right now.",
        }
    return {
        "current_version": current,
        "latest_version": latest_tag,
        "has_update": has_update(current, latest_tag),
        "release_url": release_url,
        "error": None,
    }


def _git_repo_root() -> Optional[Path]:
    root = Path(__file__).resolve().parent.parent
    try:
        res = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        return Path(res.stdout.strip()) if res.stdout.strip() else None
    except Exception:
        return None


def _run_in_repo(command: list[str]) -> subprocess.CompletedProcess:
    repo_root = _git_repo_root()
    if repo_root is None:
        raise RuntimeError("This install is not a Git checkout, so there is no repository to update.")
    return subprocess.run(command, cwd=str(repo_root), text=True, capture_output=True)


def perform_update() -> dict:
    repo_root = _git_repo_root()
    if repo_root is None:
        raise RuntimeError("Update requires a Git checkout. Please install from GitHub clone or run the installer from the repo.")

    fetch = _run_in_repo(["git", "fetch", "--all", "--tags", "--prune"])
    if fetch.returncode != 0:
        raise RuntimeError(fetch.stderr.strip() or fetch.stdout.strip() or "Git fetch failed.")

    pull = _run_in_repo(["git", "pull", "--ff-only", "origin", "main"])
    if pull.returncode != 0:
        raise RuntimeError(pull.stderr.strip() or pull.stdout.strip() or "Git pull failed.")

    venv_python = Path(repo_root) / ".mazeint_venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if venv_python.exists():
        install = subprocess.run([str(venv_python), "-m", "pip", "install", "-e", str(repo_root)], text=True, capture_output=True)
    else:
        install = subprocess.run([sys.executable, "-m", "pip", "install", "-e", str(repo_root)], text=True, capture_output=True)

    if install.returncode != 0:
        raise RuntimeError(install.stderr.strip() or install.stdout.strip() or "Package reinstall failed.")

    result = check_for_updates()
    return {
        "status": "updated",
        "current_version": result["current_version"],
        "latest_version": result["latest_version"],
        "message": "Application updated successfully.",
    }


def main() -> int:
    try:
        info = check_for_updates()
        if info["has_update"]:
            print(f"Update available: {info['current_version']} -> {info['latest_version']}")
            print(f"Release: {info['release_url']}")
            result = perform_update()
            print(result["message"])
            print(f"Now running version: {result['latest_version']}")
        else:
            print(f"No update available. Current version: {info['current_version']}")
        return 0
    except Exception as exc:
        print(f"Update check failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
