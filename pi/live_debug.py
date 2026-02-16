"""Live sensor debug — shows all sensor values and simulated state machine.

Run on a Raspberry Pi (stop voice-player first):
    sudo systemctl stop voice-player
    uv run --with adafruit-circuitpython-sths34pf80 live_debug.py
"""

import time
import board
import busio
import adafruit_sths34pf80

MOTION_THRESHOLD = 30
EMPTY_THRESHOLD = 30
CONSECUTIVE_ENTER = 1
CONSECUTIVE_EMPTY = 4

i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_sths34pf80.STHS34PF80(i2c)

state = "IDLE"
enter_count = 0
empty_count = 0

print("Live Sensor Debug (Ctrl+C to stop)")
print(f"Enter: mv > {MOTION_THRESHOLD} x{CONSECUTIVE_ENTER} | Empty: pv < {EMPTY_THRESHOLD} x{CONSECUTIVE_EMPTY}")
print()
print(f"{'MV':>7} {'M?':>3} {'PV':>7} {'P?':>3} {'State':<10} {'En#':>4} {'Em#':>4}  Notes")
print("-" * 70)

try:
    while True:
        mv = sensor.motion_value
        pv = sensor.presence_value
        m_flag = sensor.motion
        p_flag = sensor.presence

        notes = ""

        if state == "IDLE":
            if mv > MOTION_THRESHOLD:
                enter_count += 1
            else:
                enter_count = 0
            if enter_count >= CONSECUTIVE_ENTER:
                state = "OCCUPIED"
                enter_count = 0
                empty_count = 0
                notes = ">>> TRIGGERED"

        elif state == "OCCUPIED":
            if pv < EMPTY_THRESHOLD:
                empty_count += 1
            else:
                empty_count = 0
            if empty_count >= CONSECUTIVE_EMPTY:
                state = "IDLE"
                empty_count = 0
                notes = ">>> RESET"

        m_str = "Y" if m_flag else "."
        p_str = "Y" if p_flag else "."

        print(f"{mv:>7} {m_str:>3} {pv:>7} {p_str:>3} {state:<10} {enter_count:>4} {empty_count:>4}  {notes}")
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\nDone.")
