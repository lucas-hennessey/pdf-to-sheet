"""In-app updates: compare VERSION with the one on GitHub, pull the new code, restart."""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import requests

REPO = "lucas-hennessey/pdf-to-sheet"
BRANCH = "main"
ROOT = Path(__file__).parent
# Never overwritten by a ZIP-based update.
KEEP = {".venv", ".git", "__pycache__", "google_client.json"}


def local_version():
    try:
        return (ROOT / "VERSION").read_text().strip()
    except FileNotFoundError:
        return "0"


def _tuple(v):
    try:
        return tuple(int(p) for p in v.strip().split("."))
    except ValueError:
        return (0,)


def remote_version():
    """Latest version on GitHub, or None if it can't be read (offline, private repo...)."""
    try:
        r = requests.get(f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/VERSION", timeout=4)
        return r.text.strip() if r.status_code == 200 else None
    except requests.RequestException:
        return None


def check():
    current, latest = local_version(), remote_version()
    return {
        "current": current,
        "latest": latest,
        "update_available": bool(latest) and _tuple(latest) > _tuple(current),
    }


def _git_update():
    r = subprocess.run(["git", "pull", "--ff-only"], cwd=ROOT, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError("Couldn't update with git (do you have local changes?): "
                           + (r.stderr.strip() or r.stdout.strip()))


def _zip_update():
    url = f"https://github.com/{REPO}/archive/refs/heads/{BRANCH}.zip"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(io.BytesIO(r.content)) as z:
        z.extractall(tmp)
        src = next(Path(tmp).iterdir())  # the single top-level "<repo>-<branch>" folder
        shutil.copytree(src, ROOT, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*KEEP))


def apply():
    """Fetch the new code and install dependencies. Raises RuntimeError on failure."""
    try:
        if (ROOT / ".git").exists() and shutil.which("git"):
            _git_update()
        else:
            _zip_update()
    except requests.RequestException as e:
        raise RuntimeError(f"Couldn't download the update: {e}")
    pip = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt")],
                         capture_output=True, text=True, timeout=600)
    if pip.returncode != 0:
        raise RuntimeError("Updated the code but installing dependencies failed: " + pip.stderr.strip()[-300:])
    return local_version()


def restart():
    """Replace this process with a fresh one (same PID, so a Dock app stays running)."""
    os.environ["PTS_RESTARTED"] = "1"  # tells the new process not to open another browser tab
    os.execv(sys.executable, [sys.executable, "-W", "ignore", str(ROOT / "app.py")])
