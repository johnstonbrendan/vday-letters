"""Interactive tuning script for Adafruit STHS34PF80 IR presence sensor.

Run on a Raspberry Pi:
    uv run --with adafruit-circuitpython-sths34pf80 sensor_tuning.py

Workflow:
    1. Type a label describing the current condition (e.g. "empty room", "standing 2m away")
    2. Press Enter — it records 5 seconds of sensor data tagged with that label
    3. Repeat for different conditions
    4. Type 'q' to quit — results are saved to sensor_log.csv
"""

import time
import csv
import os
import board
import adafruit_sths34pf80

SAMPLE_DURATION = 5.0  # seconds per label
SAMPLE_INTERVAL = 0.25  # seconds between readings

LOG_FILE = "sensor_log.csv"

i2c = board.I2C()
sensor = adafruit_sths34pf80.STHS34PF80(i2c)

print("STHS34PF80 Sensor Tuning Tool")
print("=" * 40)
print(f"Each label records {SAMPLE_DURATION:.0f}s of data ({int(SAMPLE_DURATION / SAMPLE_INTERVAL)} samples)")
print(f"Results saved to: {os.path.abspath(LOG_FILE)}")
print()

write_header = not os.path.exists(LOG_FILE)
log = open(LOG_FILE, "a", newline="")
writer = csv.writer(log)
if write_header:
    writer.writerow(["timestamp", "label", "presence_value", "motion_value", "presence_flag", "motion_flag"])

session_data = []

try:
    while True:
        label = input("Label (or 'q' to quit): ").strip()
        if label.lower() == "q":
            break
        if not label:
            print("  Skipped — enter a label or 'q' to quit")
            continue

        num_samples = int(SAMPLE_DURATION / SAMPLE_INTERVAL)
        print(f"  Recording {SAMPLE_DURATION:.0f}s... ", end="", flush=True)

        samples = []
        for i in range(num_samples):
            pv = sensor.presence_value
            mv = sensor.motion_value
            pf = sensor.presence
            mf = sensor.motion
            ts = time.strftime("%H:%M:%S")

            samples.append((pv, mv, pf, mf))
            writer.writerow([ts, label, pv, mv, pf, mf])
            session_data.append((label, pv, mv, pf, mf))
            time.sleep(SAMPLE_INTERVAL)

        log.flush()

        pres_vals = [s[0] for s in samples]
        mot_vals = [s[1] for s in samples]
        abs_pres = [abs(v) for v in pres_vals]

        print("done!")
        print(f"  Presence  — min:{min(pres_vals):6d}  max:{max(pres_vals):6d}  avg:{sum(pres_vals)/len(pres_vals):6.1f}  avg(abs):{sum(abs_pres)/len(abs_pres):6.1f}")
        print(f"  Motion    — min:{min(mot_vals):6d}  max:{max(mot_vals):6d}  avg:{sum(mot_vals)/len(mot_vals):6.1f}")
        print()

except KeyboardInterrupt:
    print("\n\nInterrupted.")

log.close()

# Print summary
if session_data:
    print()
    print("=" * 60)
    print("SESSION SUMMARY")
    print("=" * 60)

    labels = []
    for label, pv, mv, pf, mf in session_data:
        if not labels or labels[-1][0] != label:
            labels.append((label, []))
        labels[-1][1].append((pv, mv))

    print(f"{'Label':<30} {'Pres avg':>9} {'|Pres| avg':>11} {'Mot avg':>9} {'Samples':>8}")
    print("-" * 60)
    for label, vals in labels:
        pvs = [v[0] for v in vals]
        mvs = [v[1] for v in vals]
        apvs = [abs(v) for v in pvs]
        print(f"{label:<30} {sum(pvs)/len(pvs):>9.1f} {sum(apvs)/len(apvs):>11.1f} {sum(mvs)/len(mvs):>9.1f} {len(vals):>8}")

    print()
    print(f"Log saved to: {os.path.abspath(LOG_FILE)}")

print("Done.")
