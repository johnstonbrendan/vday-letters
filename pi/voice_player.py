#!/usr/bin/env python3
"""
Valentine's Day Voice Player — Raspberry Pi (Play-Once Mode)

Polls an Adafruit STHS34PF80 IR presence sensor over I2C.
Checks Supabase room_status table for pending messages (played_at IS NULL).
When a pending message exists and someone enters the room:
  1. Downloads the audio (or uses cached copy)
  2. Plays it once through the USB speaker
  3. Marks it as played in Supabase (sets played_at)
  4. Goes dormant until a new recording is uploaded or replay is triggered

States:
  DORMANT  → no pending message, ignore sensor
  READY    → pending message exists, waiting for someone to enter
  OCCUPIED → someone is in the room, audio already played this visit

Config is read from environment variables (set in /etc/voice-player.env):
  ROOM_NAME            — e.g. "bedroom", "study", "bathroom", "living-room"
  SUPABASE_URL         — e.g. "https://xxxxx.supabase.co"
  SUPABASE_ANON_KEY    — anon/public key from Supabase project settings
  MOTION_THRESHOLD     — motion_value above this triggers entry (default 30)
  EMPTY_THRESHOLD      — presence_value below this = room empty (default 30)
  CONSECUTIVE_ENTER    — consecutive motion readings above threshold to trigger (default 1)
  CONSECUTIVE_EMPTY    — consecutive presence readings below empty threshold to reset (default 4)
  AUDIO_DEVICE         — ALSA device for playback (default "plughw:1,0" = USB speaker)
  STATUS_POLL_SECONDS  — how often to check room_status table (default 15)
"""

import os
import sys
import time
import signal
import logging
import datetime
import subprocess

import board
import busio
import adafruit_sths34pf80
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("voice-player")

# --- Config ---
ROOM_NAME = os.environ.get("ROOM_NAME")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
MOTION_THRESHOLD = int(os.environ.get("MOTION_THRESHOLD", "30"))
EMPTY_THRESHOLD = int(os.environ.get("EMPTY_THRESHOLD", "30"))
CONSECUTIVE_ENTER = int(os.environ.get("CONSECUTIVE_ENTER", "1"))
CONSECUTIVE_EMPTY = int(os.environ.get("CONSECUTIVE_EMPTY", "4"))
AUDIO_DEVICE = os.environ.get("AUDIO_DEVICE", "plughw:1,0")
STATUS_POLL_SECONDS = int(os.environ.get("STATUS_POLL_SECONDS", "15"))
POLL_INTERVAL = 0.5  # seconds between sensor reads
OCCUPIED_TIMEOUT = 600  # 10 minutes max in OCCUPIED before forcing reset

# States
STATE_DORMANT = "DORMANT"
STATE_READY = "READY"
STATE_OCCUPIED = "OCCUPIED"

if not ROOM_NAME or not SUPABASE_URL or not SUPABASE_ANON_KEY:
    log.error("ROOM_NAME, SUPABASE_URL, and SUPABASE_ANON_KEY must be set")
    sys.exit(1)

AUDIO_URL = f"{SUPABASE_URL}/storage/v1/object/authenticated/voice-messages/{ROOM_NAME}.webm"
STATUS_API = f"{SUPABASE_URL}/rest/v1/room_status?room_name=eq.{ROOM_NAME}&select=*"
STATUS_PATCH = f"{SUPABASE_URL}/rest/v1/room_status?room_name=eq.{ROOM_NAME}"
AUTH_HEADERS = {
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "apikey": SUPABASE_ANON_KEY,
}
AUDIO_DIR = "/opt/voice-player/cache"
AUDIO_PATH = os.path.join(AUDIO_DIR, f"{ROOM_NAME}.webm")

os.makedirs(AUDIO_DIR, exist_ok=True)

# Track the updated_at we last downloaded for, so we only re-download on new uploads
cached_updated_at = None


def _timeout_handler(signum, frame):
    raise TimeoutError("I2C sensor read timed out")


def init_sensor():
    """Initialize the STHS34PF80 sensor over I2C."""
    i2c = busio.I2C(board.SCL, board.SDA)
    sensor = adafruit_sths34pf80.STHS34PF80(i2c)
    log.info("Sensor initialized (STHS34PF80 at 0x5A)")
    return sensor


def read_sensor(sensor):
    """Read motion and presence values with a timeout to guard against I2C hangs."""
    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(5)  # 5-second watchdog
    try:
        mv = sensor.motion_value
        pv = sensor.presence_value
        return mv, pv
    finally:
        signal.alarm(0)  # cancel alarm


def check_status():
    """Check the room_status table. Returns (is_pending, updated_at) or (False, None) on error."""
    try:
        resp = requests.get(
            STATUS_API,
            headers={**AUTH_HEADERS, "Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            return False, None
        row = rows[0]
        is_pending = row.get("played_at") is None
        updated_at = row.get("updated_at")
        return is_pending, updated_at
    except requests.RequestException as e:
        log.error("Status check failed: %s", e)
        return False, None


def mark_played():
    """Set played_at to now in room_status."""
    try:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        resp = requests.patch(
            STATUS_PATCH,
            headers={**AUTH_HEADERS, "Content-Type": "application/json", "Prefer": "return=minimal"},
            json={"played_at": now},
            timeout=10,
        )
        resp.raise_for_status()
        log.info("Marked room '%s' as played", ROOM_NAME)
    except requests.RequestException as e:
        log.error("Failed to mark as played: %s", e)


def download_audio(updated_at):
    """Download the audio file from Supabase. Skips if cached version matches. Returns True on success."""
    global cached_updated_at

    if cached_updated_at == updated_at and os.path.exists(AUDIO_PATH):
        log.info("Using cached audio (updated_at unchanged: %s)", updated_at)
        return True

    try:
        resp = requests.get(AUDIO_URL, headers=AUTH_HEADERS, timeout=15)
        if resp.status_code == 404:
            log.warning("No audio file found for room '%s'", ROOM_NAME)
            return False
        resp.raise_for_status()
        with open(AUDIO_PATH, "wb") as f:
            f.write(resp.content)
        cached_updated_at = updated_at
        log.info("Downloaded %d bytes → %s", len(resp.content), AUDIO_PATH)
        return True
    except requests.RequestException as e:
        log.error("Download failed: %s", e)
        return False


def play_audio():
    """Play the webm file through the USB speaker via mpv."""
    log.info("Playing %s on device alsa/%s", AUDIO_PATH, AUDIO_DEVICE)
    try:
        subprocess.run(
            ["mpv", "--no-video", "--volume-gain=10",
             f"--audio-device=alsa/{AUDIO_DEVICE}", AUDIO_PATH],
            check=True, timeout=120,
        )
        log.info("Playback complete")
    except subprocess.TimeoutExpired:
        log.warning("Playback timed out after 120s")
    except subprocess.CalledProcessError as e:
        log.error("mpv error: %s", e)


def main():
    log.info("Starting voice player for room '%s' (play-once mode)", ROOM_NAME)
    log.info("Enter: mv > %d x%d | Empty: pv < %d x%d | Status poll: %ds",
             MOTION_THRESHOLD, CONSECUTIVE_ENTER,
             EMPTY_THRESHOLD, CONSECUTIVE_EMPTY,
             STATUS_POLL_SECONDS)

    sensor = init_sensor()
    state = STATE_DORMANT
    enter_count = 0
    empty_count = 0
    last_status_check = 0
    current_updated_at = None
    occupied_since = None  # watchdog timer for OCCUPIED state
    # After transitioning from OCCUPIED to READY, skip sensor for a
    # brief settle period so the person leaving doesn't re-trigger.
    settle_until = 0

    log.info("State: DORMANT — checking for pending messages")

    while True:
        try:
            now = time.time()

            # --- Periodically check room_status (in all states) ---
            if now - last_status_check >= STATUS_POLL_SECONDS:
                is_pending, updated_at = check_status()
                last_status_check = now

                if state == STATE_DORMANT:
                    if is_pending:
                        current_updated_at = updated_at
                        log.info("Pending message found (updated_at=%s) — pre-downloading", updated_at)
                        if download_audio(updated_at):
                            state = STATE_READY
                            enter_count = 0
                            settle_until = now + 3  # 3s settle after becoming READY
                            log.info("State: READY — waiting for someone to enter")
                        else:
                            log.warning("Download failed, staying DORMANT")

                elif state == STATE_READY:
                    if not is_pending:
                        log.info("Message no longer pending — back to DORMANT")
                        state = STATE_DORMANT
                    elif updated_at != current_updated_at:
                        log.info("New recording detected (updated_at=%s) — re-downloading", updated_at)
                        current_updated_at = updated_at
                        download_audio(updated_at)

                elif state == STATE_OCCUPIED:
                    if is_pending and updated_at != current_updated_at:
                        log.info("New recording while occupied — will play after room empties and re-enters")
                        current_updated_at = updated_at

            # --- OCCUPIED watchdog: force reset after 10 minutes ---
            if state == STATE_OCCUPIED and occupied_since and (now - occupied_since > OCCUPIED_TIMEOUT):
                log.warning("OCCUPIED for >%d min — forcing reset", OCCUPIED_TIMEOUT // 60)
                state = STATE_DORMANT
                occupied_since = None
                empty_count = 0
                last_status_check = 0  # force immediate status check
                time.sleep(POLL_INTERVAL)
                continue

            # --- Sensor polling ---
            mv, pv = read_sensor(sensor)

            if state == STATE_READY:
                # Skip sensor during settle period (prevents re-trigger from person leaving)
                if now < settle_until:
                    time.sleep(POLL_INTERVAL)
                    continue

                if mv > MOTION_THRESHOLD:
                    enter_count += 1
                else:
                    enter_count = 0

                if enter_count >= CONSECUTIVE_ENTER:
                    log.info("Motion detected (motion=%d, presence=%d) — playing audio", mv, pv)
                    state = STATE_OCCUPIED
                    occupied_since = now
                    enter_count = 0
                    empty_count = 0
                    play_audio()
                    mark_played()
                    log.info("State: OCCUPIED — waiting for room to empty")

            elif state == STATE_OCCUPIED:
                if pv < EMPTY_THRESHOLD:
                    empty_count += 1
                else:
                    empty_count = 0

                if empty_count >= CONSECUTIVE_EMPTY:
                    log.info("Room empty (presence=%d) — checking for new pending messages", pv)
                    empty_count = 0
                    # Check immediately if there's a new pending message
                    is_pending, updated_at = check_status()
                    last_status_check = time.time()
                    if is_pending:
                        current_updated_at = updated_at
                        if download_audio(updated_at):
                            state = STATE_READY
                            settle_until = time.time() + 3  # 3s settle
                            log.info("State: READY — new pending message, waiting for entry")
                        else:
                            state = STATE_DORMANT
                            log.info("State: DORMANT — download failed")
                    else:
                        state = STATE_DORMANT
                        log.info("State: DORMANT — no pending messages")
                    occupied_since = None

            time.sleep(POLL_INTERVAL)

        except TimeoutError:
            log.error("I2C sensor read timed out — reinitializing sensor")
            try:
                sensor = init_sensor()
            except Exception as e2:
                log.error("Sensor reinit failed: %s — retrying in 10s", e2)
                time.sleep(10)
        except KeyboardInterrupt:
            log.info("Shutting down")
            break
        except Exception as e:
            log.error("Unexpected error: %s", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
