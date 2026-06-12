"""
Fetch MTA Subway Hourly Ridership (New York).
Dataset: data.ny.gov  Socrata ID: 5wq4-mkjj  (Beginning 2025)
            archive: wujg-7c2s (2020-2024, for baselines)
Pulls hourly station-level tap counts. Note: publication lags ~4-6 weeks.
Caches to data/raw/mta_hourly_{year}.parquet.
"""
import os
from pathlib import Path
from datetime import datetime, timedelta, date

import pandas as pd
import requests

RAW_DIR = Path(__file__).parents[2] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

SOCRATA_BASE_2025 = "https://data.ny.gov/resource/5wq4-mkjj.json"
SOCRATA_BASE_ARCHIVE = "https://data.ny.gov/resource/wujg-7c2s.json"
APP_TOKEN = os.environ.get("SOCRATA_APP_TOKEN", "")

# Stations near MetLife access corridors (Penn Station area)
PENN_COMPLEX_STATIONS = [
    "Penn Station",
    "34 St-Penn Station",
    "34 St-Herald Sq",
    "Times Sq-42 St",
    "34 St-Hudson Yards",
    "28 St",
    "23 St",
    "14 St",
]

CACHE_MAX_AGE_DAYS = 6


def _cache_file(year: int) -> Path:
    return RAW_DIR / f"mta_hourly_{year}.parquet"


def _cache_is_fresh(path: Path, max_age_days: int) -> bool:
    if not path.exists():
        return False
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return (datetime.now() - mtime) < timedelta(days=max_age_days)


def fetch_year(year: int, force: bool = False) -> pd.DataFrame:
    cache = _cache_file(year)
    if not force and _cache_is_fresh(cache, CACHE_MAX_AGE_DAYS):
        print(f"[mta] Cache fresh for {year}; skipping.")
        return pd.read_parquet(cache)

    base = SOCRATA_BASE_2025 if year >= 2025 else SOCRATA_BASE_ARCHIVE
    headers = {"X-App-Token": APP_TOKEN} if APP_TOKEN else {}
    print(f"[mta] Fetching {year} from {base}…")

    all_rows = []
    limit = 50000
    offset = 0
    while True:
        params = {
            "$limit": limit,
            "$offset": offset,
            "$where": f"transit_timestamp >= '{year}-01-01T00:00:00' AND transit_timestamp < '{year+1}-01-01T00:00:00'",
            "$order": "transit_timestamp ASC",
        }
        resp = requests.get(base, params=params, headers=headers, timeout=120)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        all_rows.extend(batch)
        print(f"  {len(all_rows):,} rows…", end="\r")
        if len(batch) < limit:
            break
        offset += limit

    print(f"\n[mta] {year}: {len(all_rows):,} rows")
    df = pd.DataFrame(all_rows)
    df.to_parquet(cache, index=False)
    print(f"[mta] Saved → {cache}")
    return df


def fetch(years: list[int] | None = None, force: bool = False) -> pd.DataFrame:
    current_year = date.today().year
    if years is None:
        years = list(range(2022, current_year + 1))
    frames = [fetch_year(y, force=force) for y in years]
    return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    df = fetch(years=[2025, 2026])
    print(df.shape)
    print(df.columns.tolist())
