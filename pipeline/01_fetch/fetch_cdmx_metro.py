"""
Fetch CDMX Metro daily ridership (afluencia diaria).
Source: datos.cdmx.gob.mx – "Afluencia diaria del Metro"
Caches to data/raw/cdmx_metro_daily.parquet.
"""
import os
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import requests

RAW_DIR = Path(__file__).parents[2] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# CDMX Open Data portal – CSV download
# Verify current URL at datos.cdmx.gob.mx; search "afluencia metro"
CDMX_CSV_URL = "https://datos.cdmx.gob.mx/dataset/afluencia-diaria-del-metro-cdmx/resource/afluencia-diaria-metro-2010-2023.csv"
CDMX_CURRENT_URL = "https://datos.cdmx.gob.mx/dataset/afluencia-diaria-del-metro-cdmx/resource/afluencia-diaria-metro-2024-actual.csv"

CACHE_FILE = RAW_DIR / "cdmx_metro_daily.parquet"
CACHE_MAX_AGE_DAYS = 6


def _cache_is_fresh(path: Path, max_age_days: int) -> bool:
    if not path.exists():
        return False
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return (datetime.now() - mtime) < timedelta(days=max_age_days)


def fetch(force: bool = False) -> pd.DataFrame:
    if not force and _cache_is_fresh(CACHE_FILE, CACHE_MAX_AGE_DAYS):
        print("[cdmx] Cache fresh; skipping download.")
        return pd.read_parquet(CACHE_FILE)

    frames = []
    for url, label in [(CDMX_CSV_URL, "historical"), (CDMX_CURRENT_URL, "current")]:
        print(f"[cdmx] Fetching {label} from {url}…")
        try:
            resp = requests.get(url, timeout=120)
            resp.raise_for_status()
            from io import StringIO
            df = pd.read_csv(StringIO(resp.text), encoding="utf-8-sig")
            frames.append(df)
            print(f"  {len(df):,} rows")
        except Exception as exc:
            print(f"  WARNING: {label} fetch failed: {exc}")

    if not frames:
        raise RuntimeError("[cdmx] No data fetched; check URLs at datos.cdmx.gob.mx")

    result = pd.concat(frames, ignore_index=True)
    result.to_parquet(CACHE_FILE, index=False)
    print(f"[cdmx] Saved → {CACHE_FILE}")
    return result


if __name__ == "__main__":
    df = fetch()
    print(df.shape)
    print(df.columns.tolist())
    print(df.head())
