"""Quick test script for Adafruit STHS34PF80 IR presence sensor.

Run on a Raspberry Pi with the sensor connected via I2C:
    uv run --with adafruit-circuitpython-sths34pf80 presence_test.py
"""

import time
import board
import adafruit_sths34pf80

i2c = board.I2C()
sensor = adafruit_sths34pf80.STHS34PF80(i2c)

print("STHS34PF80 Presence Test")
print("========================")
print("Sensor connected OK")
print("Polling every 0.5s — Ctrl+C to stop\n")

try:
    while True:
        presence = sensor.presence
        motion = sensor.motion
        temp = sensor.object_temperature

        status = ""
        if presence:
            status += " [PRESENCE]"
        if motion:
            status += " [MOTION]"
        if not status:
            status = " --"

        print(f"Temp: {temp:6.1f}°C  Pres: {sensor.presence_value:6d}  Mot: {sensor.motion_value:6d} {status}")
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\nDone.")
