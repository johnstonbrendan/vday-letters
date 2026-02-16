#!/usr/bin/env bash
# Pi setup script — run this on each Raspberry Pi
# Usage: sudo bash setup.sh <room_name> <supabase_anon_key>
# Example: sudo bash setup.sh study YOUR_ANON_KEY

set -euo pipefail

ROOM_NAME="${1:-}"
SUPABASE_ANON_KEY="${2:-}"
if [ -z "$ROOM_NAME" ] || [ -z "$SUPABASE_ANON_KEY" ]; then
  echo "Usage: sudo bash setup.sh <room_name> <supabase_anon_key>"
  echo "  e.g.: sudo bash setup.sh study YOUR_ANON_KEY"
  exit 1
fi

SUPABASE_URL="https://uursobeqcefsjqstlorq.supabase.co"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Valentine's Day Voice Player — Pi Setup ==="
echo "Room: $ROOM_NAME"

# Install system dependencies
echo "[1/6] Installing system packages..."
apt-get update -qq && apt-get install -y -qq mpv i2c-tools > /dev/null

# Install uv (for the actual user, not root)
ACTUAL_USER="${SUDO_USER:-$(logname 2>/dev/null || echo pi)}"
ACTUAL_HOME=$(eval echo "~$ACTUAL_USER")
echo "[2/6] Installing uv for $ACTUAL_USER..."
if [ ! -f "$ACTUAL_HOME/.local/bin/uv" ]; then
  sudo -u "$ACTUAL_USER" bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
fi
UV_PATH="$ACTUAL_HOME/.local/bin/uv"

# Deploy script
echo "[3/6] Deploying voice_player.py..."
mkdir -p /opt/voice-player/cache
cp "$SCRIPT_DIR/voice_player.py" /opt/voice-player/voice_player.py 2>/dev/null \
  || cp /tmp/voice_player.py /opt/voice-player/voice_player.py

# Set USB speaker volume
echo "[4/6] Setting USB speaker volume to 90%..."
amixer -c 1 set PCM 90% 2>/dev/null || echo "  (could not set volume — adjust manually)"

# Write env file
echo "[5/6] Writing /etc/voice-player.env..."
cat > /etc/voice-player.env <<EOF
ROOM_NAME=$ROOM_NAME
SUPABASE_URL=$SUPABASE_URL
SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY
MOTION_THRESHOLD=30
EMPTY_THRESHOLD=30
CONSECUTIVE_ENTER=1
CONSECUTIVE_EMPTY=4
AUDIO_DEVICE=plughw:1,0
STATUS_POLL_SECONDS=15
EOF

# Install and enable systemd service
echo "[6/6] Installing systemd service..."
cat > /etc/systemd/system/voice-player.service <<EOF
[Unit]
Description=Valentine's Day Voice Player
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/etc/voice-player.env
ExecStart=$UV_PATH run --with adafruit-circuitpython-sths34pf80,requests /opt/voice-player/voice_player.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable voice-player

echo ""
echo "Setup complete for room '$ROOM_NAME'!"
echo "  Start:   sudo systemctl start voice-player"
echo "  Restart: sudo systemctl restart voice-player"
echo "  Logs:    journalctl -u voice-player -f"
echo "  Config:  /etc/voice-player.env"
