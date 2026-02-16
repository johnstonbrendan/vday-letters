# Valentine's Day Voice Letters

A surprise voice-message system that plays personalized audio letters when someone walks into a room. Record a message from the web app, and a Raspberry Pi with a motion sensor detects when someone enters and plays it through a speaker.

## How It Works

1. **Record** a voice message for a room using the web app
2. The **Raspberry Pi** in that room polls for new messages
3. When the IR presence sensor detects someone entering, it **plays the message** through a USB speaker
4. The message is marked as played; use the web app to **replay** or record a new one

## Architecture

- **Web App** (`web-app/`) — React + Vite + TypeScript. Floor-plan UI for recording, playing, deleting, and replaying voice messages per room.
- **Pi Player** (`pi/`) — Python script running as a systemd service. Uses an Adafruit STHS34PF80 IR sensor for presence detection and `mpv` for audio playback.
- **Backend** — Supabase (Postgres + Storage). `room_status` table tracks message state per room; `voice-messages` bucket stores audio files.

## Pi State Machine

```
DORMANT  →  no pending message, polling periodically
READY    →  message pending, waiting for motion
OCCUPIED →  someone entered, message played, waiting for room to empty
```

## Setup

### Web App

```bash
cd web-app
npm install
cp .env.example .env   # fill in your Supabase credentials
npm run dev
```

### Raspberry Pi

Each Pi needs:
- Adafruit STHS34PF80 IR sensor wired via I2C
- USB speaker
- Network access to Supabase

```bash
# On the Pi:
sudo bash pi/setup.sh <room_name> <your_supabase_anon_key>
sudo systemctl start voice-player
```

### Database

Run `supabase_setup.sql` in your Supabase SQL editor to create the `room_status` table and storage bucket.

## Deployment

- **Web app**: Deployed on Vercel
- **Pi deploy script**: `bash deploy.sh` copies files to all Pis over SSH and restarts the service
