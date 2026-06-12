"""
Compute the Transit Strain Index for each city × match.

Formula:
  incremental_riders = stadium_capacity × fill_rate × transit_mode_share
  scheduled_capacity = serving_lines × vehicles_per_peak_hour × capacity_per_vehicle × peak_hours
  strain_raw = incremental_riders / scheduled_capacity
  strain_index = min(strain_raw × 10, 10)  → normalized 0–10

Outputs results_strain.json and updates site/data/strain.json.
"""
from pathlib import Path
import json, pandas as pd, numpy as np
from datetime import date

MANUAL_DIR = Path(__file__).parents[2] / "data" / "manual"
PROCESSED_DIR = Path(__file__).parents[2] / "data" / "processed"
SITE_DATA_DIR = Path(__file__).parents[2] / "site" / "data"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Corridor capacity parameters (sourced from GTFS + agency plans)
CORRIDOR_PARAMS = {
    "nyc": {
        "serving_lines": 3,          # NJT NEC, NJT Meadowlands Rail, NJT Bus
        "vehicles_per_hour": 8,      # trains; enhanced WC service
        "capacity_per_vehicle": 1200,
        "peak_hours": 3.0,
        "normal_vehicles_per_hour": 2,
    },
    "cdmx": {
        "serving_lines": 2,          # Metro Line 2, Line 3 (with transfer)
        "vehicles_per_hour": 40,     # trains per hour (very high frequency)
        "capacity_per_vehicle": 1200,
        "peak_hours": 3.0,
        "normal_vehicles_per_hour": 30,
    },
    "tor": {
        "serving_lines": 3,          # TTC 509, TTC 511, GO Transit
        "vehicles_per_hour": 12,
        "capacity_per_vehicle": 200,
        "peak_hours": 3.0,
        "normal_vehicles_per_hour": 6,
    },
    "van": {
        "serving_lines": 2,          # SkyTrain Expo, SkyTrain Millennium
        "vehicles_per_hour": 20,     # enhanced WC service
        "capacity_per_vehicle": 600,
        "peak_hours": 3.0,
        "normal_vehicles_per_hour": 10,
    },
    "atl": {
        "serving_lines": 1,          # MARTA Red/Gold (single trunk)
        "vehicles_per_hour": 6,      # enhanced service
        "capacity_per_vehicle": 500,
        "peak_hours": 3.0,
        "normal_vehicles_per_hour": 3,
    },
    "sea": {
        "serving_lines": 2,          # Link + KC Metro buses
        "vehicles_per_hour": 10,
        "capacity_per_vehicle": 400,
        "peak_hours": 3.0,
        "normal_vehicles_per_hour": 5,
    },
}

CITY_PARAMS = {
    "nyc":  {"transit_mode_share": 0.45, "typical_fill_rate": 0.95},
    "cdmx": {"transit_mode_share": 0.60, "typical_fill_rate": 0.95},
    "tor":  {"transit_mode_share": 0.72, "typical_fill_rate": 0.90},
    "van":  {"transit_mode_share": 0.80, "typical_fill_rate": 0.95},
    "atl":  {"transit_mode_share": 0.28, "typical_fill_rate": 0.90},
    "sea":  {"transit_mode_share": 0.38, "typical_fill_rate": 0.90},
}


def compute_strain(
    stadium_capacity: int,
    city_id: str,
    fill_rate_override: float | None = None,
    service_uplift_pct: float = 0.0,
) -> dict:
    p = CITY_PARAMS[city_id]
    c = CORRIDOR_PARAMS[city_id]

    fill_rate = fill_rate_override or p["typical_fill_rate"]
    incremental_riders = stadium_capacity * fill_rate * p["transit_mode_share"]

    wc_veh_per_hour = c["vehicles_per_hour"] * (1 + service_uplift_pct / 100)
    scheduled_cap = (
        c["serving_lines"] * wc_veh_per_hour * c["capacity_per_vehicle"] * c["peak_hours"]
    )
    normal_cap = (
        c["serving_lines"] * c["normal_vehicles_per_hour"] * c["capacity_per_vehicle"] * c["peak_hours"]
    )

    strain_raw = incremental_riders / max(scheduled_cap, 1)
    strain_index = min(round(strain_raw * 10, 2), 10.0)

    return {
        "incremental_riders": int(incremental_riders),
        "scheduled_capacity_wc": int(scheduled_cap),
        "normal_capacity": int(normal_cap),
        "capacity_increase_pct": round((wc_veh_per_hour - c["normal_vehicles_per_hour"]) / c["normal_vehicles_per_hour"] * 100, 1),
        "strain_raw": round(strain_raw, 4),
        "strain_index": strain_index,
    }


def run() -> dict:
    matches = pd.read_csv(MANUAL_DIR / "matches.csv")
    results = []

    for _, row in matches.iterrows():
        city_id = row["city_id"]
        if city_id not in CORRIDOR_PARAMS:
            continue
        s = compute_strain(int(row["capacity"]), city_id)
        s.update({
            "match_id": row["match_id"],
            "city_id": city_id,
            "date": row["date"],
            "round": row["round"],
            "strain_index_manual": float(row["strain_rating"]),  # hand-rated from plan
        })
        # Blend manual + computed
        s["strain_index_final"] = round(
            0.5 * s["strain_index"] + 0.5 * s["strain_index_manual"], 2
        )
        results.append(s)

    out = {"meta": {"computed": date.today().isoformat()}, "matches": results}

    (PROCESSED_DIR / "results_strain.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )
    (SITE_DATA_DIR / "strain.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )
    print(f"[strain] Computed {len(results)} match strain values → site/data/strain.json")
    return out


if __name__ == "__main__":
    out = run()
    for m in out["matches"][:5]:
        print(f"{m['match_id']} {m['city_id']} {m['date']}: strain={m['strain_index_final']}")
