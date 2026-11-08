"""Module 1 - Energy Consumption Calculator.

Contains the Room class and the RoomManager that adds, lists, searches,
updates, calculates and saves rooms to CSV.
"""
import csv
import os

FIELDS = ["room_id", "room_name", "building", "area_m2",
          "lighting_kw", "ac_kw", "equipment_kw", "hours_per_day"]


# ---------------------------------------------------------------- validation
def validate_room_values(area, lighting, ac, equipment, hours):
    """Return (True, "") if valid, else (False, error message)."""
    if area <= 0:
        return False, "Area must be greater than zero."
    for label, value in (("Lighting", lighting), ("AC", ac), ("Equipment", equipment)):
        if value < 0:
            return False, f"{label} power must be non-negative."
    if not 0 <= hours <= 24:
        return False, "Operating hours must be between 0 and 24."
    return True, ""


class Room:
    """A room with its power loads and daily operating hours."""

    def __init__(self, room_id, name, building, area_m2,
                 lighting_kw, ac_kw, equipment_kw, hours_per_day):
        area_m2, lighting_kw, ac_kw = float(area_m2), float(lighting_kw), float(ac_kw)
        equipment_kw, hours_per_day = float(equipment_kw), float(hours_per_day)
        ok, msg = validate_room_values(area_m2, lighting_kw, ac_kw, equipment_kw, hours_per_day)
        if not ok:
            raise ValueError(msg)
        self.room_id = str(room_id).strip()
        self.name = str(name).strip()
        self.building = str(building).strip()
        self.area_m2 = area_m2
        self.lighting_kw = lighting_kw
        self.ac_kw = ac_kw
        self.equipment_kw = equipment_kw
        self.hours_per_day = hours_per_day

    # ------------------------------------------------------------ calculations
    @property
    def total_power_kw(self):
        return self.lighting_kw + self.ac_kw + self.equipment_kw

    def daily_energy_kwh(self):
        """Daily energy (kWh) = total power (kW) x operating hours."""
        return self.total_power_kw * self.hours_per_day

    def energy_per_m2(self):
        """Consumption per square meter = daily energy / area."""
        return self.daily_energy_kwh() / self.area_m2

    def to_dict(self):
        return {"room_id": self.room_id, "room_name": self.name, "building": self.building,
                "area_m2": self.area_m2, "lighting_kw": self.lighting_kw, "ac_kw": self.ac_kw,
                "equipment_kw": self.equipment_kw, "hours_per_day": self.hours_per_day}

    def __str__(self):
        return (f"{self.room_id:<4} {self.name:<15} {self.building:<15} "
                f"{self.area_m2:>7.1f} m2  {self.total_power_kw:>6.1f} kW  "
                f"{self.hours_per_day:>4.1f} h  {self.daily_energy_kwh():>8.1f} kWh")


class RoomManager:
    """Keeps rooms in a list (ordered) and a dict (fast lookup by id)."""

    def __init__(self):
        self.rooms = []        # list of Room
        self.index = {}        # dict: room_id -> Room

    # ------------------------------------------------------------------ CRUD
    def add_room(self, room):
        if room.room_id in self.index:
            raise ValueError(f"Room ID {room.room_id} already exists.")
        self.rooms.append(room)
        self.index[room.room_id] = room

    def list_rooms(self):
        return list(self.rooms)

    def search(self, keyword):
        """Case-insensitive search in id, name and building."""
        kw = keyword.strip().lower()
        return [r for r in self.rooms
                if kw in r.room_id.lower() or kw in r.name.lower() or kw in r.building.lower()]

    def update_room(self, room_id, **changes):
        """Update any of: name, building, area_m2, lighting_kw, ac_kw, equipment_kw, hours_per_day."""
        if room_id not in self.index:
            raise KeyError(f"Room ID {room_id} not found.")
        room = self.index[room_id]
        current = {"name": room.name, "building": room.building, "area_m2": room.area_m2,
                   "lighting_kw": room.lighting_kw, "ac_kw": room.ac_kw,
                   "equipment_kw": room.equipment_kw, "hours_per_day": room.hours_per_day}
        unknown = set(changes) - set(current)          # set difference
        if unknown:
            raise KeyError(f"Unknown field(s): {sorted(unknown)}")
        current.update(changes)
        # Build a new Room first so validation runs before anything is changed
        new_room = Room(room_id, current["name"], current["building"], current["area_m2"],
                        current["lighting_kw"], current["ac_kw"], current["equipment_kw"],
                        current["hours_per_day"])
        self.rooms[self.rooms.index(room)] = new_room
        self.index[room_id] = new_room

    # --------------------------------------------------------- calculations
    def total_consumption(self):
        return sum(r.daily_energy_kwh() for r in self.rooms)

    def summary(self):
        """List of tuples: (room_id, name, daily_kwh, kwh_per_m2)."""
        return [(r.room_id, r.name, r.daily_energy_kwh(), r.energy_per_m2()) for r in self.rooms]

    def buildings(self):
        return sorted({r.building for r in self.rooms})   # set -> unique buildings

    def consumption_by_building(self):
        totals = {}
        for r in self.rooms:
            totals[r.building] = totals.get(r.building, 0) + r.daily_energy_kwh()
        return totals

    def top_consumers(self, n=3):
        ranked = sorted(self.rooms, key=lambda r: r.daily_energy_kwh(), reverse=True)
        return ranked[:n]                                  # slicing

    # ------------------------------------------------------------------ CSV
    def save_csv(self, path):
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            for r in self.rooms:
                writer.writerow(r.to_dict())

    def load_csv(self, path):
        """Load rooms from CSV. Invalid rows are skipped and reported. Returns (loaded, errors)."""
        loaded, errors = 0, []
        with open(path, newline="", encoding="utf-8") as f:
            for line_no, row in enumerate(csv.DictReader(f), start=2):
                try:
                    self.add_room(Room(row["room_id"], row["room_name"], row["building"],
                                       row["area_m2"], row["lighting_kw"], row["ac_kw"],
                                       row["equipment_kw"], row["hours_per_day"]))
                    loaded += 1
                except (ValueError, KeyError) as e:
                    errors.append(f"Line {line_no}: {e}")
        return loaded, errors
