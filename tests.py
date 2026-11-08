"""Test 3 valid and 3 invalid cases. Writes test_results.csv and prints a table."""
import csv
import pandas as pd
from module1_energy_calculator import Room, RoomManager
import module2_analysis as m2

results = []


def record(name, kind, expected, actual):
    results.append({"test": name, "type": kind, "expected": expected, "actual": actual,
                    "result": "PASS" if str(expected) == str(actual) else "FAIL"})


def outcome_of(func):
    """Return 'accepted' or 'rejected: <message>'."""
    try:
        func()
        return "accepted"
    except (ValueError, KeyError) as e:
        return f"rejected: {e}"


# ------------------------------------------------------------- VALID cases
r = Room("T1", "Test Room", "B1", 100, 1.0, 5.0, 2.0, 10)
record("V1 daily energy: (1+5+2) kW x 10 h", "valid", 80.0, r.daily_energy_kwh())
record("V2 per m2: 80 kWh / 100 m2", "valid", 0.8, round(r.energy_per_m2(), 3))

rooms_df = pd.DataFrame([r.to_dict()])
sc = m2.ac_reduction_scenario(rooms_df, 20)       # AC 5 -> 4 kW  => (1+4+2)*10 = 70
record("V3 AC -20%: estimated after-kWh", "valid", 70.0, float(sc["est_kwh_after"].iloc[0]))

# ------------------------------------------------------------- INVALID cases
record("I1 area = 0", "invalid", "rejected: Area must be greater than zero.",
       outcome_of(lambda: Room("T2", "X", "B1", 0, 1, 1, 1, 8)))
record("I2 negative AC power", "invalid", "rejected: AC power must be non-negative.",
       outcome_of(lambda: Room("T3", "X", "B1", 20, 1, -3, 1, 8)))
record("I3 hours = 25", "invalid", "rejected: Operating hours must be between 0 and 24.",
       outcome_of(lambda: Room("T4", "X", "B1", 20, 1, 3, 1, 25)))

# --------------------------------------------------------------- output
with open("test_results.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(results[0]))
    w.writeheader()
    w.writerows(results)

for t in results:
    print(f"[{t['result']}] {t['test']}\n        expected: {t['expected']}\n        actual  : {t['actual']}")
print(f"\n{sum(t['result'] == 'PASS' for t in results)}/{len(results)} tests passed")
