#!/usr/bin/env python3
"""Live sensor debug — prints motion and presence values every 0.5s."""
import time
import board
import busio
import adafruit_sths34pf80

i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_sths34pf80.STHS34PF80(i2c)
print("Sensor ready. Ctrl+C to stop.\n")
print(f"{'Time':>8}  {'MV':>6}  {'M?':>3}  {'PV':>7}  {'P?':>3}")
print("-" * 38)

try:
    while True:
        mv = sensor.motion_value
        pv = sensor.presence_value
        m = sensor.motion
        p = sensor.presence
        t = time.strftime("%H:%M:%S")
        print(f"{t}  {mv:>6}  {'Y' if m else '.':>3}  {pv:>7}  {'Y' if p else '.':>3}")
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\nDone.")
