#!/usr/bin/env python3
"""
Colab heartbeat + restore system.
Run this cell FIRST to restore state, then run the second cell to start Hermes + heartbeat.
"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

# === CONFIG ===
BACKUP_DIR = Path("/content/drive/MyDrive/hermes-colab/hermes-state")
HOME_HERMES = Path("/root/.hermes")
GIST_ID = "9739987481e693ba7cea5c53597356b0"
GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"
# ===============

def restore_from_drive():
    """Restore ~/.hermes from Drive backup."""
    if not BACKUP_DIR.exists():
        print("No backup found — starting fresh.")
        return
    HOME_HERMES.mkdir(parents=True, exist_ok=True)
    skip = {"auth.lock", "gateway.lock", "gateway.pid", "gateway.sock", "gateway-starts.log"}
    for item in BACKUP_DIR.iterdir():
        if item.name in skip:
            continue
        dest = HOME_HERMES / item.name
        try:
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        except Exception as e:
            print(f"  WARN: {item.name}: {e}")
    print("State restored from Drive")

def sync_to_drive():
    """Sync current state back to Drive."""
    if not BACKUP_DIR.exists():
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    skip = {"auth.lock", "gateway.lock", "gateway.pid", "gateway.sock", "gateway-starts.log"}
    for item in HOME_HERMES.iterdir():
        if item.name in skip:
            continue
        dest = BACKUP_DIR / item.name
        try:
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        except Exception as e:
            print(f"  WARN: {item.name}: {e}")
    print("State synced to Drive")

def write_heartbeat():
    """Write heartbeat to GitHub Gist."""
    import urllib.request
    import json
    
    timestamp = datetime.now(timezone.utc).isoformat()
    content = json.dumps({
        "status": "alive",
        "timestamp": timestamp,
        "colab_url": "https://colab.research.google.com/drive/1yfzxR6YpvzGLa2G9GOmEDekH1ne75LtQ"
    })
    
    data = json.dumps({
        "files": {"heartbeat.json": {"content": content}}
    }).encode()
    
    url = f"https://api.github.com/gists/{GIST_ID}"
    req = urllib.request.Request(url, data=data, method="PATCH")
    req.add_header("Authorization", f"token {GITHUB_TOKEN}")
    req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                print(f"Heartbeat written: {timestamp}")
                return True
    except Exception as e:
        print(f"Heartbeat failed: {e}")
    return False

def main():
    from google.colab import drive
    drive.mount("/content/drive", force_remount=True)
    print("Drive mounted.")
    
    restore_from_drive()
    
    # Register shutdown hook
    import atexit
    atexit.register(sync_to_drive)
    
    # Start heartbeat in background
    import threading
    def heartbeat_loop():
        while True:
            write_heartbeat()
            time.sleep(300)  # every 5 min
    
    hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    hb_thread.start()
    print("Heartbeat started (every 5 min)")
    
    # Start Hermes
    print("Starting Hermes gateway...")
    proc = subprocess.Popen(
        ["hermes", "gateway", "run"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        for line in proc.stdout:
            print(line, end="")
    except KeyboardInterrupt:
        print("\nShutting down...")
        proc.terminate()
        proc.wait(timeout=10)
        sync_to_drive()

if __name__ == "__main__":
    main()
