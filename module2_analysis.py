"""Module 2 - Consumption and Cost Analysis (pandas, NumPy, Matplotlib)."""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")            # save charts to files without needing a display
import matplotlib.pyplot as plt


# ------------------------------------------------------------ load + clean
def load_readings(path):
    return pd.read_csv(path)


def clean_readings(df):
    """Clean readings. Returns (clean_df, report_dict)."""
    report = {"rows_before": len(df)}
    df = df.copy()

    df["room_id"] = df["room_id"].astype(str).str.strip().str.upper()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["actual_kwh"] = pd.to_numeric(df["actual_kwh"], errors="coerce")

    bad_dates = int(df["date"].isna().sum())
    df = df.dropna(subset=["date", "room_id"])
    report["invalid_dates_removed"] = bad_dates

    report["duplicates_removed"] = int(df.duplicated().sum())
    df = df.drop_duplicates()
    # Same room and same date but different values -> keep the first
    df = df.drop_duplicates(subset=["room_id", "date"], keep="first")

    negatives = int((df["actual_kwh"] < 0).sum())
    df.loc[df["actual_kwh"] < 0, "actual_kwh"] = np.nan   # impossible value -> treat as missing
    report["negative_values_set_missing"] = negatives

    # Missing values: fill with the median of the same room and same day type
    # (weekday / weekend), because consumption is very different on weekends.
    report["missing_values_filled"] = int(df["actual_kwh"].isna().sum())
    df["is_weekend"] = df["date"].dt.dayofweek >= 5
    group_median = df.groupby(["room_id", "is_weekend"])["actual_kwh"].transform("median")
    df["actual_kwh"] = df["actual_kwh"].fillna(group_median)
    df["actual_kwh"] = df["actual_kwh"].fillna(df.groupby("room_id")["actual_kwh"].transform("median"))
    df = df.dropna(subset=["actual_kwh"])

    df = df.sort_values(["room_id", "date"]).reset_index(drop=True)
    df["month"] = df["date"].dt.to_period("M").astype(str)
    report["rows_after"] = len(df)
    return df, report


def merge_with_rooms(readings, rooms_df):
    """Merge readings with room data (inner join on room_id)."""
    rooms_df = rooms_df.copy()
    rooms_df["room_id"] = rooms_df["room_id"].astype(str).str.strip().str.upper()
    return readings.merge(rooms_df, on="room_id", how="inner")


# ---------------------------------------------------------- cost analysis
def add_cost(merged, price_per_kwh):
    if price_per_kwh < 0:
        raise ValueError("Price per kWh must be non-negative.")
    out = merged.copy()
    out["cost"] = out["actual_kwh"] * price_per_kwh
    return out


def _aggregate(df, keys):
    return (df.groupby(keys)
              .agg(total_kwh=("actual_kwh", "sum"), avg_daily_kwh=("actual_kwh", "mean"),
                   total_cost=("cost", "sum"))
              .round(2).reset_index())


def by_room(df):
    return _aggregate(df, ["room_id", "room_name", "building"])


def by_building(df):
    return _aggregate(df, ["building"])


def by_month(df):
    return _aggregate(df, ["month"])


def by_building_month(df):
    return _aggregate(df, ["building", "month"])


def by_room_month(df):
    return _aggregate(df, ["room_id", "room_name", "month"])


def filter_rows(df, building=None, min_kwh=None):
    """pandas boolean filtering example."""
    mask = pd.Series(True, index=df.index)
    if building:
        mask &= df["building"] == building
    if min_kwh is not None:
        mask &= df["actual_kwh"] >= min_kwh
    return df[mask]


# ------------------------------------------------- NumPy AC-reduction scenario
def ac_reduction_scenario(rooms_df, reduction_percent):
    """Compare estimated daily consumption before/after cutting AC power.

    Only AC power changes; operating hours and other loads stay the same.
    Returns a DataFrame with one row per room.
    """
    if not 0 <= reduction_percent <= 100:
        raise ValueError("Reduction percent must be between 0 and 100.")
    light = rooms_df["lighting_kw"].to_numpy(dtype=float)
    ac = rooms_df["ac_kw"].to_numpy(dtype=float)
    equip = rooms_df["equipment_kw"].to_numpy(dtype=float)
    hours = rooms_df["hours_per_day"].to_numpy(dtype=float)

    before = (light + ac + equip) * hours
    ac_new = ac * (1 - reduction_percent / 100)
    after = (light + ac_new + equip) * hours
    saving = before - after

    result = rooms_df[["room_id", "room_name", "building"]].copy()
    result["ac_kw_before"] = ac
    result["ac_kw_after"] = np.round(ac_new, 3)
    result["est_kwh_before"] = np.round(before, 2)
    result["est_kwh_after"] = np.round(after, 2)
    result["saving_kwh"] = np.round(saving, 2)
    result["saving_percent"] = np.round(np.divide(saving, before, out=np.zeros_like(saving),
                                                  where=before != 0) * 100, 2)
    return result


# --------------------------------------------------------------- charts
def _save(fig, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def make_charts(df, out_dir="charts"):
    """Create the 4 required charts. Returns the list of saved file paths."""
    paths = []

    # 1) Line: total daily consumption of all rooms
    daily = df.groupby("date")["actual_kwh"].sum()
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(daily.index, daily.values, color="tab:blue", linewidth=1.5)
    ax.set_title("Total Daily Energy Consumption (All Rooms)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Energy (kWh/day)")
    ax.grid(alpha=0.3)
    fig.autofmt_xdate()
    paths.append(_save(fig, os.path.join(out_dir, "line_daily_consumption.png")))

    # 2) Bar: total cost per room
    r = by_room(df)
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["tab:blue" if b == r["building"].iloc[0] else "tab:orange" for b in r["building"]]
    ax.bar(r["room_name"], r["total_cost"], color=colors)
    ax.set_title("Total Energy Cost per Room")
    ax.set_xlabel("Room (blue/orange = building)")
    ax.set_ylabel("Cost (currency units)")
    ax.tick_params(axis="x", rotation=30)
    ax.grid(axis="y", alpha=0.3)
    paths.append(_save(fig, os.path.join(out_dir, "bar_cost_per_room.png")))

    # 3) Scatter: room area vs average daily consumption
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(r.merge(df[["room_id", "area_m2"]].drop_duplicates(), on="room_id")["area_m2"],
               r["avg_daily_kwh"], s=80, color="tab:green")
    for _, row in r.merge(df[["room_id", "area_m2"]].drop_duplicates(), on="room_id").iterrows():
        ax.annotate(row["room_name"], (row["area_m2"], row["avg_daily_kwh"]),
                    textcoords="offset points", xytext=(5, 5), fontsize=8)
    ax.set_title("Room Area vs Average Daily Consumption")
    ax.set_xlabel("Room area (m²)")
    ax.set_ylabel("Average energy (kWh/day)")
    ax.grid(alpha=0.3)
    paths.append(_save(fig, os.path.join(out_dir, "scatter_area_vs_consumption.png")))

    # 4) Histogram: distribution of daily readings
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(df["actual_kwh"], bins=20, color="tab:purple", edgecolor="white")
    ax.set_title("Distribution of Daily Room Readings")
    ax.set_xlabel("Daily energy (kWh)")
    ax.set_ylabel("Number of readings")
    ax.grid(axis="y", alpha=0.3)
    paths.append(_save(fig, os.path.join(out_dir, "hist_daily_readings.png")))

    return paths


def make_scenario_chart(scenario_df, percent, out_dir="charts"):
    """Bonus chart: estimated consumption before vs after AC reduction."""
    x = np.arange(len(scenario_df))
    w = 0.4
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - w / 2, scenario_df["est_kwh_before"], w, label="Before")
    ax.bar(x + w / 2, scenario_df["est_kwh_after"], w, label=f"After (-{percent}% AC)")
    ax.set_xticks(x)
    ax.set_xticklabels(scenario_df["room_name"], rotation=30)
    ax.set_title("Estimated Daily Consumption Before vs After AC Reduction")
    ax.set_xlabel("Room")
    ax.set_ylabel("Energy (kWh/day)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    return _save(fig, os.path.join(out_dir, "bar_ac_scenario.png"))


# --------------------------------------------------------------- reports
def export_reports(df, scenario_df=None, out_dir="reports"):
    os.makedirs(out_dir, exist_ok=True)
    files = {
        "report_by_room.csv": by_room(df),
        "report_by_building.csv": by_building(df),
        "report_by_month.csv": by_month(df),
        "report_by_building_month.csv": by_building_month(df),
        "report_by_room_month.csv": by_room_month(df),
        "cleaned_merged_data.csv": df.assign(date=df["date"].dt.strftime("%Y-%m-%d")),
    }
    if scenario_df is not None:
        files["report_ac_scenario.csv"] = scenario_df
    paths = []
    for name, frame in files.items():
        p = os.path.join(out_dir, name)
        frame.to_csv(p, index=False)
        paths.append(p)
    return paths
