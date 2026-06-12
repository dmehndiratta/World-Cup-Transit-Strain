"""
Fetch FTA National Transit Database – Complete Monthly Ridership.
Dataset: data.transportation.gov  Socrata ID: 8bui-9xvu
Pulls UPT (unlinked passenger trips) and VRH (vehicle revenue hours)
for all US agencies, 2015-present. Caches to data/raw/ntd_monthly.parquet.
"""
import os
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import requests
from tqdm import tqdm

RAW_DIR = Path(__file__).parents[2] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

SOCRATA_BASE = "https://data.transportation.gov/resource/8bui-9xvu.json"
APP_TOKEN = os.environ.get("SOCRATA_APP_TOKEN", "")
CACHE_FILE = RAW_DIR / "ntd_monthly.parquet"
CACHE_MAX_AGE_DAYS = 6  # refresh if older than this

# Agencies to keep: host-city systems + donor pool
HOST_AGENCY_IDS = {
    "nyc": ["2008", "2006"],   # MTA NYC Transit, MTA Bus
    "atl": ["4034"],           # MARTA
    "sea": ["5006", "5011"],   # Sound Transit, King County Metro
}
DONOR_NTDIDS = [
    "3030",   # CTA Chicago
    "9015",   # WMATA DC
    "6006",   # TriMet Portland
    "1002",   # RTD Denver
    "9021",   # Dallas DART
    "2012",   # SEPTA (note: exclude from donor pool – Philly is host)
    "3019",   # Metro Transit Minneapolis
    "6009",   # Sacramento RT
    "6003",   # Bay Area BART (host – exclude from donor pool, include for info)
    "9013",   # Houston Metro
    "4008",   # Cleveland RTA
    "2040",   # Pittsburgh PAT
]


def _cache_is_fresh(path: Path, max_age_days: int) -> bool:
    if not path.exists():
        return False
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return (datetime.now() - mtime) < timedelta(days=max_age_days)


def fetch(force: bool = False) -> pd.DataFrame:
    if not force and _cache_is_fresh(CACHE_FILE, CACHE_MAX_AGE_DAYS):
        print(f"[ntd] Cache is fresh ({CACHE_FILE}); skipping download.")
        return pd.read_parquet(CACHE_FILE)

    print("[ntd] Fetching from data.transportation.gov Socrata API…")
    headers = {"X-App-Token": APP_TOKEN} if APP_TOKEN else {}

    # Socrata limit is 50k rows; paginate with offset
    all_rows = []
    limit = 50000
    offset = 0
    while True:
        params = {
            "$limit": limit,
            "$offset": offset,
            "$where": "year >= 2015",
            "$order": "year ASC, month ASC",
        }
        resp = requests.get(SOCRATA_BASE, params=params, headers=headers, timeout=60)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        all_rows.extend(batch)
        print(f"  fetched {len(all_rows):,} rows", end="\r")
        if len(batch) < limit:
            break
        offset += limit

    print(f"\n[ntd] Total rows: {len(all_rows):,}")
    df = pd.DataFrame(all_rows)
    df.to_parquet(CACHE_FILE, index=False)
    print(f"[ntd] Saved → {CACHE_FILE}")
    return df


if __name__ == "__main__":
    df = fetch()
    print(df.dtypes)
    print(df.head())
