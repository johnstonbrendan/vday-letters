#!/usr/bin/env bash
# Deploy voice player to Raspberry Pis defined in pi/hosts.json
# Usage: bash deploy.sh [room_name]
#   bash deploy.sh          — deploy to all Pis
#   bash deploy.sh study    — deploy to just the study Pi

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOSTS_FILE="$SCRIPT_DIR/pi/hosts.json"
TARGET_ROOM="${1:-}"

if [ ! -f "$HOSTS_FILE" ]; then
  echo "Error: $HOSTS_FILE not found"
  exit 1
fi

# Extract anon key from hosts.json
ANON_KEY=$(python3 -c "import json; print(json.load(open('$HOSTS_FILE'))['supabase_anon_key'])")

deploy_to_pi() {
  local host="$1" user="$2" room="$3"
  echo ""
  echo "=== Deploying to $room ($user@$host) ==="

  # Copy files
  echo "  Uploading files..."
  scp -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new \
    "$SCRIPT_DIR/pi/voice_player.py" \
    "$SCRIPT_DIR/pi/setup.sh" \
    "$user@$host:/tmp/"

  # Run setup
  echo "  Running setup..."
  ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new "$user@$host" "sudo bash /tmp/setup.sh $room $ANON_KEY"

  # Start the service
  echo "  Starting service..."
  ssh "$user@$host" "sudo systemctl restart voice-player"

  # Verify
  echo "  Checking..."
  ssh "$user@$host" "sleep 3 && sudo journalctl -u voice-player -n 5 --no-pager"

  echo "  Done!"
}

# Read hosts and deploy
python3 -c "
import json, sys
with open('$HOSTS_FILE') as f:
    data = json.load(f)
for pi in data['pis']:
    room = pi['room']
    if '$TARGET_ROOM' and room != '$TARGET_ROOM':
        continue
    print(f\"{pi['host']} {pi['user']} {room}\")
" | while read -r host user room; do
  deploy_to_pi "$host" "$user" "$room" || echo "  FAILED for $room ($host) — skipping"
done

echo ""
echo "=== Deployment complete ==="
