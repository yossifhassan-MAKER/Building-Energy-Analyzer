"""Building Energy Analyzer - main menu connecting Module 1 and Module 2."""
import os
import pandas as pd

from module1_energy_calculator import Room, RoomManager
import module2_analysis as m2

ROOMS_CSV = os.path.join("data", "rooms.csv")
READINGS_CSV = os.path.join("data", "readings.csv")

MENU = """
========== Building Energy Analyzer ==========
 -- Module 1: Energy Consumption Calculator --
  1. Add a room
  2. List rooms
  3. Search rooms
  4. Update a room
  5. Show consumption (per room / total / per m2)
  6. Save rooms to CSV
 -- Module 2: Consumption and Cost Analysis --
  7. Load, clean and merge readings
  8. Cost reports (room / building / month)
  9. AC reduction scenario (NumPy)
 10. Create charts (PNG)
 11. Export reports (CSV)
  0. Exit
==============================================="""


# ---------------------------------------------------------------- input helpers
def ask_float(prompt, check=None, error="Invalid value."):
    """Keep asking until a number that passes `check` is entered."""
    while True:
        try:
            value = float(input(prompt))
        except ValueError:
            print("  Please enter a number.")
            continue
        if check is None or check(value):
            return value
        print(f"  {error}")


def ask_text(prompt):
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("  This field cannot be empty.")


def print_rooms(rooms):
    if not rooms:
        print("  No rooms found.")
        return
    print(f"  {'ID':<4} {'Name':<15} {'Building':<15} {'Area':>9}  {'Power':>8}  {'Hours':>6}  {'Daily kWh':>9}")
    for r in rooms:
        print("  " + str(r))


# ---------------------------------------------------------------- Module 1 actions
def add_room(mgr):
    room_id = ask_text("Room ID (e.g. R09): ").upper()
    if room_id in mgr.index:
        print("  That ID already exists.")
        return
    name = ask_text("Room name: ")
    building = ask_text("Building: ")
    area = ask_float("Area (m2, > 0): ", lambda v: v > 0, "Area must be greater than zero.")
    light = ask_float("Lighting power (kW): ", lambda v: v >= 0, "Power must be non-negative.")
    ac = ask_float("Air-conditioning power (kW): ", lambda v: v >= 0, "Power must be non-negative.")
    equip = ask_float("Equipment power (kW): ", lambda v: v >= 0, "Power must be non-negative.")
    hours = ask_float("Operating hours per day (0-24): ", lambda v: 0 <= v <= 24,
                      "Hours must be between 0 and 24.")
    mgr.add_room(Room(room_id, name, building, area, light, ac, equip, hours))
    print("  Room added.")


def search_rooms(mgr):
    print_rooms(mgr.search(ask_text("Search (id / name / building): ")))


def update_room(mgr):
    room_id = ask_text("Room ID to update: ").upper()
    if room_id not in mgr.index:
        print("  Room not found.")
        return
    fields = {"1": "name", "2": "building", "3": "area_m2", "4": "lighting_kw",
              "5": "ac_kw", "6": "equipment_kw", "7": "hours_per_day"}
    for k, v in fields.items():
        print(f"   {k}. {v}")
    choice = input("Field number: ").strip()
    if choice not in fields:
        print("  Invalid choice.")
        return
    field = fields[choice]
    raw = ask_text(f"New value for {field}: ")
    value = raw if field in ("name", "building") else None
    if value is None:
        try:
            value = float(raw)
        except ValueError:
            print("  Value must be a number.")
            return
    try:
        mgr.update_room(room_id, **{field: value})
        print("  Room updated.")
    except ValueError as e:
        print(f"  Not updated: {e}")


def show_consumption(mgr):
    if not mgr.rooms:
        print("  No rooms loaded.")
        return
    print(f"  {'ID':<4} {'Room':<15} {'kWh/day':>10} {'kWh/day/m2':>12}")
    for room_id, name, kwh, per_m2 in mgr.summary():
        print(f"  {room_id:<4} {name:<15} {kwh:>10.1f} {per_m2:>12.3f}")
    print(f"\n  Total daily consumption: {mgr.total_consumption():.1f} kWh")
    for b, v in mgr.consumption_by_building().items():
        print(f"    {b}: {v:.1f} kWh/day")
    print("  Top 3 consumers: " + ", ".join(r.name for r in mgr.top_consumers(3)))


# ---------------------------------------------------------------- Module 2 actions
def rooms_dataframe(mgr):
    """Bridge between Module 1 and Module 2: Room objects -> DataFrame."""
    return pd.DataFrame([r.to_dict() for r in mgr.rooms])


def load_and_clean(state, mgr):
    if not mgr.rooms:
        print("  Load or add rooms first (Module 1).")
        return
    if not os.path.exists(READINGS_CSV):
        print(f"  File not found: {READINGS_CSV}")
        return
    raw = m2.load_readings(READINGS_CSV)
    clean, report = m2.clean_readings(raw)
    merged = m2.merge_with_rooms(clean, rooms_dataframe(mgr))
    state["merged"] = merged
    print("  Cleaning report:")
    for k, v in report.items():
        print(f"    {k}: {v}")
    print(f"  Merged rows: {len(merged)}")


def need_data(state):
    if "merged" not in state:
        print("  Run option 7 first.")
        return False
    return True


def ask_price():
    return ask_float("Price per kWh: ", lambda v: v >= 0, "Price must be non-negative.")


def cost_reports(state):
    if not need_data(state):
        return
    state["price"] = ask_price()
    df = m2.add_cost(state["merged"], state["price"])
    state["costed"] = df
    pd.set_option("display.width", 140)
    print("\n-- By room --\n", m2.by_room(df).to_string(index=False))
    print("\n-- By building --\n", m2.by_building(df).to_string(index=False))
    print("\n-- By month --\n", m2.by_month(df).to_string(index=False))


def scenario(state, mgr):
    if not mgr.rooms:
        print("  No rooms loaded.")
        return
    pct = ask_float("AC power reduction (%): ", lambda v: 0 <= v <= 100,
                    "Percent must be between 0 and 100.")
    result = m2.ac_reduction_scenario(rooms_dataframe(mgr), pct)
    state["scenario"], state["scenario_pct"] = result, pct
    pd.set_option("display.width", 160)
    print(result.to_string(index=False))
    print(f"\n  Total before: {result['est_kwh_before'].sum():.1f} kWh/day")
    print(f"  Total after : {result['est_kwh_after'].sum():.1f} kWh/day")
    print(f"  Saving      : {result['saving_kwh'].sum():.1f} kWh/day")


def charts(state):
    if "costed" not in state:
        if not need_data(state):
            return
        state["price"] = ask_price()
        state["costed"] = m2.add_cost(state["merged"], state["price"])
    paths = m2.make_charts(state["costed"], "charts")
    if "scenario" in state:
        paths.append(m2.make_scenario_chart(state["scenario"], state["scenario_pct"], "charts"))
    print("  Saved:", *paths, sep="\n   ")


def export(state):
    if "costed" not in state:
        if not need_data(state):
            return
        state["price"] = ask_price()
        state["costed"] = m2.add_cost(state["merged"], state["price"])
    paths = m2.export_reports(state["costed"], state.get("scenario"), "reports")
    print("  Saved:", *paths, sep="\n   ")


# ---------------------------------------------------------------- main loop
def main():
    mgr = RoomManager()
    state = {}                      # results shared between menu options
    if os.path.exists(ROOMS_CSV):
        loaded, errors = mgr.load_csv(ROOMS_CSV)
        print(f"Loaded {loaded} rooms from {ROOMS_CSV}.")
        for e in errors:
            print("  Skipped ->", e)

    actions = {
        "1": lambda: add_room(mgr),
        "2": lambda: print_rooms(mgr.list_rooms()),
        "3": lambda: search_rooms(mgr),
        "4": lambda: update_room(mgr),
        "5": lambda: show_consumption(mgr),
        "6": lambda: (mgr.save_csv(ROOMS_CSV), print(f"  Saved to {ROOMS_CSV}")),
        "7": lambda: load_and_clean(state, mgr),
        "8": lambda: cost_reports(state),
        "9": lambda: scenario(state, mgr),
        "10": lambda: charts(state),
        "11": lambda: export(state),
    }
    while True:
        print(MENU)
        choice = input("Choose: ").strip()
        if choice == "0":
            print("Goodbye.")
            break
        action = actions.get(choice)
        if action is None:
            print("  Invalid option.")
            continue
        try:
            action()
        except Exception as e:      # keep the menu alive on unexpected errors
            print(f"  Error: {e}")


if __name__ == "__main__":
    main()
