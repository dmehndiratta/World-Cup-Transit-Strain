"""
Clean MTA hourly → interim/daily_nyc.parquet
Aggregates station-level hourly taps to daily system totals + Penn corridor subtotal.
Adds match-day flags and kickoff windows.
"""
from pathlib import Path
import pandas as pd
import numpy as np

RAW_DIR = Path(__file__).parents[2] / "data" / "raw"
INTERIM_DIR = Path(__file__).parents[2] / "data" / "interim"
MANUAL_DIR = Path(__file__).parents[2] / "data" / "manual"
INTERIM_DIR.mkdir(parents=True, exist_ok=True)

PENN_STATIONS = [
    "34 ST-PENN STA",
    "34 ST-PENN STATION",
    "34 ST-HERALD SQ",
    "TIMES SQ-42 ST",
    "34 ST-HUDSON YARDS",
    "28 ST",
    "23 ST",
    "14 ST",
    "14 ST-UNION SQ",
]


def run() -> pd.DataFrame:
    # Load hourly files (multiple years)
    raw_files = list(RAW_DIR.glob("mta_hourly_*.parquet"))
    if not raw_files:
        raise FileNotFoundError("Run fetch_mta_hourly.py first")

    frames = [pd.read_parquet(f) for f in raw_files]
    df = pd.concat(frames, ignore_index=True)
    print(f"[clean_mta] Raw: {df.shape}")

    df.columns = [c.lower().replace(" ", "_") for c in df.columns]

    # Parse timestamp
    ts_col = next((c for c in df.columns if "timestamp" in c or "time" in c), None)
    if ts_col:
        df["ts"] = pd.to_datetime(df[ts_col], errors="coerce")
        df["date"] = df["ts"].dt.date
        df["hour"] = df["ts"].dt.hour

    # Ridership column
    rides_col = next((c for c in df.columns if "ridership" in c or "fare" in c or "count" in c), "ridership")
    df["ridership"] = pd.to_numeric(df.get(rides_col, 0), errors="coerce").fillna(0)

    # Station name for corridor filter
    station_col = next((c for c in df.columns if "station" in c and "name" in c), None)

    # System-wide daily totals
    daily_system = (
        df.groupby("date")["ridership"].sum().reset_index()
        .rename(columns={"ridership": "daily_ridership_system"})
    )

    # Penn corridor daily totals
    if station_col:
        mask = df[station_col].str.upper().str.contains("|".join(PENN_STATIONS), na=False)
        daily_penn = (
            df[mask].groupby("date")["ridership"].sum().reset_index()
            .rename(columns={"ridership": "daily_ridership_penn_corridor"})
        )
        daily_system = daily_system.merge(daily_penn, on="date", how="left")

    # Merge match-day flags
    matches = pd.read_csv(MANUAL_DIR / "matches.csv")
    nyc_matches = matches[matches["city_id"] == "nyc"][["date", "kickoff_local", "round", "strain_rating"]]
    nyc_matches["date"] = pd.to_datetime(nyc_matches["date"]).dt.date
    nyc_matches = nyc_matches.rename(columns={"strain_rating": "match_strain_rating"})

    daily_system["date"] = pd.to_datetime(daily_system["date"])
    nyc_matches["date"] = pd.to_datetime(nyc_matches["date"])
    daily_system = daily_system.merge(nyc_matches, on="date", how="left")
    daily_system["is_match_day"] = daily_system["kickoff_local"].notna()

    out = INTERIM_DIR / "daily_nyc.parquet"
    daily_system.to_parquet(out, index=False)
    print(f"[clean_mta] Saved → {out} ({len(daily_system):,} days)")
    return daily_system


if __name__ == "__main__":
    df = run()
    print(df.tail(30))
