"""Download all archived voice recordings from Supabase.

Usage:
    uv run --with requests download_archive.py

Downloads to: ./archive/{room}_{timestamp}.webm
"""

import os
import json
import requests

HOSTS_FILE = os.path.join(os.path.dirname(__file__), "pi", "hosts.json")

with open(HOSTS_FILE) as f:
    config = json.load(f)

SUPABASE_URL = config["supabase_url"]
SUPABASE_KEY = config["supabase_anon_key"]
BUCKET = "voice-messages"
HEADERS = {"Authorization": f"Bearer {SUPABASE_KEY}", "apikey": SUPABASE_KEY}

OUT_DIR = os.path.join(os.path.dirname(__file__), "archive")
os.makedirs(OUT_DIR, exist_ok=True)


def list_files(prefix=""):
    resp = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/list/{BUCKET}",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={"prefix": prefix, "limit": 1000},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def download_file(path, dest):
    resp = requests.get(
        f"{SUPABASE_URL}/storage/v1/object/authenticated/{BUCKET}/{path}",
        headers=HEADERS,
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"  FAILED ({resp.status_code}): {path}")
        return False
    with open(dest, "wb") as f:
        f.write(resp.content)
    print(f"  {len(resp.content):,} bytes -> {dest}")
    return True


# Download active recordings
print("=== Active recordings ===")
active_files = [f for f in list_files("") if f.get("name", "").endswith(".webm")]
for f in active_files:
    name = f["name"]
    download_file(name, os.path.join(OUT_DIR, f"active_{name}"))

if not active_files:
    print("  (none)")

# Download archived recordings
print("\n=== Archived recordings ===")
archive_files = [f for f in list_files("archive") if f.get("name", "").endswith(".webm")]
for f in archive_files:
    name = f["name"]
    download_file(f"archive/{name}", os.path.join(OUT_DIR, name))

if not archive_files:
    print("  (none)")

total = len(active_files) + len(archive_files)
print(f"\nDone. {total} file(s) downloaded to {OUT_DIR}/")
