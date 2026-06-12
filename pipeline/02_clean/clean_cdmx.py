"""
Clean CDMX Metro daily ridership → interim/daily_cdmx.parquet
Standardises column names, parses dates, adds match-day flags.
"""
from pathlib import Path
import pandas as pd
import numpy as np

RAW_DIR = Path(__file__).parents[2] / "data" / "raw"
INTERIM_DIR = Path(__file__).parents[2] / "data" / "interim"
MANUAL_DIR = Path(__file__).parents[2] / "data" / "manual"
INTERIM_DIR.mkdir(parents=True, exist_ok=True)


AZTECA_LINE = "Línea 2"  # Estadio Azteca station is on Line 2


def run() -> pd.DataFrame:
    raw_file = RAW_DIR / "cdmx_metro_daily.parquet"
    if not raw_file.exists():
        raise FileNotFoundError("Run fetch_cdmx_metro.py first")

    df = pd.read_parquet(raw_file)
    print(f"[clean_cdmx] Raw: {df.shape}")
    df.columns = [c.strip().lower() for c in df.columns]

    # Typical column names in CDMX dataset: 'fecha', 'linea', 'afluencia'
    date_col = next((c for c in df.columns if "fecha" in c or "date" in c), None)
    line_col = next((c for c in df.columns if "linea" in c or "line" in c), None)
    rides_col = next((c for c in df.columns if "afluencia" in c or "ridership" in c or "total" in c), None)

    if not all([date_col, rides_col]):
        print(f"  Columns found: {df.columns.tolist()}")
        raise ValueError("[clean_cdmx] Could not identify required columns")

    df["date"] = pd.to_datetime(df[date_col], dayfirst=True, errors="coerce")
    df["ridership"] = pd.to_numeric(df[rides_col], errors="coerce")
    df = df.dropna(subset=["date", "ridership"])

    # System-wide daily total
    daily = df.groupby("date")["ridership"].sum().reset_index()
    daily.columns = ["date", "daily_ridership_system"]

    # Line 2 corridor (Azteca)
    if line_col:
        l2 = df[df[line_col].str.contains("2", na=False)].groupby("date")["ridership"].sum().reset_index()
        l2.columns = ["date", "daily_ridership_line2"]
        daily = daily.merge(l2, on="date", how="left")

    # Match-day flags
    matches = pd.read_csv(MANUAL_DIR / "matches.csv")
    cdmx_matches = matches[matches["city_id"] == "cdmx"][["date", "kickoff_local", "round", "strain_rating"]]
    cdmx_matches["date"] = pd.to_datetime(cdmx_matches["date"])
    cdmx_matches = cdmx_matches.rename(columns={"strain_rating": "match_strain_rating"})

    daily = daily.merge(cdmx_matches, on="date", how="left")
    daily["is_match_day"] = daily["kickoff_local"].notna()

    # Filter 2022-present (use as post-COVID baseline)
    daily = daily[daily["date"] >= "2022-01-01"].copy()

    out = INTERIM_DIR / "daily_cdmx.parquet"
    daily.to_parquet(out, index=False)
    print(f"[clean_cdmx] Saved → {out} ({len(daily):,} days)")
    return daily


if __name__ == "__main__":
    df = run()
    print(df.tail(20))
