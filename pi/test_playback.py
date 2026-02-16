"""Isolated download + playback test. No sensor involved.

Run on a Raspberry Pi:
    uv run --with requests test_playback.py

Tests each step independently so you can pinpoint where it breaks:
  1. Download from Supabase (authenticated)
  2. Check the file was saved
  3. List audio devices
  4. Play through mpv
"""

import os
import subprocess
import requests

ROOM_NAME = os.environ.get("ROOM_NAME", "study")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://uursobeqcefsjqstlorq.supabase.co")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

AUDIO_URL = f"{SUPABASE_URL}/storage/v1/object/authenticated/voice-messages/{ROOM_NAME}.webm"
AUDIO_PATH = f"/tmp/{ROOM_NAME}.webm"


def step(num, desc):
    print(f"\n{'='*50}")
    print(f"  Step {num}: {desc}")
    print(f"{'='*50}")


# --- Step 1: Download ---
step(1, "Download audio from Supabase")
print(f"  URL: {AUDIO_URL}")

if not SUPABASE_ANON_KEY:
    print("  WARNING: SUPABASE_ANON_KEY not set, trying without auth...")
    headers = {}
else:
    headers = {"Authorization": f"Bearer {SUPABASE_ANON_KEY}", "apikey": SUPABASE_ANON_KEY}
    print(f"  Auth: using anon key ({SUPABASE_ANON_KEY[:20]}...)")

resp = requests.get(AUDIO_URL, headers=headers, timeout=15)
print(f"  HTTP status: {resp.status_code}")
print(f"  Content-Type: {resp.headers.get('content-type', 'unknown')}")
print(f"  Size: {len(resp.content)} bytes")

if resp.status_code != 200:
    print(f"  FAILED — response body: {resp.text[:200]}")
    exit(1)

with open(AUDIO_PATH, "wb") as f:
    f.write(resp.content)
print(f"  Saved to: {AUDIO_PATH}")


# --- Step 2: Verify file ---
step(2, "Verify downloaded file")
size = os.path.getsize(AUDIO_PATH)
print(f"  File size: {size} bytes")
if size < 100:
    print("  FAILED — file too small, probably not valid audio")
    exit(1)

# Check file type with `file` command
result = subprocess.run(["file", AUDIO_PATH], capture_output=True, text=True)
print(f"  File type: {result.stdout.strip()}")


# --- Step 3: Audio devices ---
step(3, "List audio output devices")
result = subprocess.run(["aplay", "-l"], capture_output=True, text=True)
if result.returncode == 0:
    print(result.stdout)
else:
    print("  aplay -l failed — ALSA might not be available")
    print(f"  stderr: {result.stderr}")

# Also check PulseAudio/PipeWire
result = subprocess.run(["pactl", "list", "sinks", "short"], capture_output=True, text=True)
if result.returncode == 0:
    print("  PulseAudio/PipeWire sinks:")
    print(result.stdout)
else:
    print("  pactl not available (no PulseAudio/PipeWire)")


# --- Step 4: Play with mpv ---
step(4, "Play audio with mpv")
print(f"  Playing: {AUDIO_PATH}")
print(f"  (you should hear sound from the USB speaker now)")
print()

result = subprocess.run(
    ["mpv", "--no-video", AUDIO_PATH],
    timeout=30,
)
print(f"\n  mpv exit code: {result.returncode}")

if result.returncode == 0:
    print("  SUCCESS — if you didn't hear anything, it's a speaker/volume issue")
else:
    print("  FAILED — mpv returned an error")


# --- Step 5: Fallback test with aplay ---
step(5, "Fallback: test speaker with system sound")
test_wav = "/usr/share/sounds/alsa/Front_Center.wav"
if os.path.exists(test_wav):
    print(f"  Playing ALSA test sound: {test_wav}")
    subprocess.run(["aplay", test_wav])
    print("  If you heard 'Front Center', speaker works — issue is with .webm format")
else:
    print(f"  {test_wav} not found, trying speaker-test...")
    subprocess.run(["speaker-test", "-t", "wav", "-c", "2", "-l", "1"], timeout=10)

print("\n" + "="*50)
print("  Done! Check which steps passed/failed above.")
print("="*50)
