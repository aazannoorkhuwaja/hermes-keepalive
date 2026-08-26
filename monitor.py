#!/usr/bin/env python3
"""
Monitor script for GitHub Actions.
Reads heartbeat gist, checks if stale (>15 min), and sends Discord webhook if dead.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

GIST_ID = os.environ.get("GIST_ID", "9739987481e693ba7cea5c53597356b0")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
COLAB_URL = "https://colab.research.google.com/drive/1yfzxR6YpvzGLa2G9GOmEDekH1ne75LtQ"

def main():
    # Fetch heartbeat
    url = f"https://api.github.com/gists/{GIST_ID}"
    req = urllib.request.Request(url)
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"token {GITHUB_TOKEN}")
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"Failed to fetch gist: {e}")
        sys.exit(1)
    
    content = data.get("files", {}).get("heartbeat.json", {}).get("content", "{}")
    heartbeat = json.loads(content)
    
    timestamp_str = heartbeat.get("timestamp", "")
    status = heartbeat.get("status", "unknown")
    
    if not timestamp_str:
        send_death_notification("No heartbeat ever recorded")
        sys.exit(0)
    
    # Parse timestamp
    try:
        ts = datetime.fromisoformat(timestamp_str)
    except ValueError:
        send_death_notification(f"Invalid timestamp: {timestamp_str}")
        sys.exit(0)
    
    now = datetime.now(timezone.utc)
    stale_threshold = timedelta(minutes=15)
    
    if now - ts > stale_threshold:
        stale_min = (now - ts).seconds // 60
        send_death_notification(f"Heartbeat stale for {stale_min} min (status was: {status})")
    else:
        print(f"Alive. Last heartbeat: {ts.isoformat()} ({ (now - ts).seconds // 60 } min ago)")

def send_death_notification(reason):
    """Send Discord webhook notification with restore link."""
    if not DISCORD_WEBHOOK:
        print("No Discord webhook configured")
        print(f"DEAD: {reason}")
        return
    
    content = {
        "content": f"⚠️ **Hermes Colab session ended!**\n"
                   f"Reason: {reason}\n"
                   f"**Tap to restore:** {COLAB_URL}\n"
                   f"Open in browser, then press Ctrl+F9 (or Run All) to restore state from Drive."
    }
    
    data = json.dumps(content).encode()
    req = urllib.request.Request(DISCORD_WEBHOOK, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 204):
                print("Death notification sent to Discord")
                return
    except Exception as e:
        print(f"Discord webhook failed: {e}")
    print(f"DEAD: {reason}")

if __name__ == "__main__":
    main()
