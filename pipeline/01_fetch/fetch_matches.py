"""
Fetch/refresh the FIFA 2026 match schedule.
Primary: reads data/manual/matches.csv (maintained by hand from fifa.com).
Writes data/processed/matches_clean.parquet + site/data/matches.json.
TODO: automate scraping from fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026
when a stable JSON/API endpoint is identified.
"""
from pathlib import Path
import json, pandas as pd
from datetime import datetime

MANUAL_CSV = Path(__file__).parents[2] / "data" / "manual" / "matches.csv"
PROCESSED_DIR = Path(__file__).parents[2] / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

CITY_TIMEZONE = {
    "nyc": "America/New_York",
    "cdmx": "America/Mexico_City",
    "tor": "America/Toronto",
    "van": "America/Vancouver",
    "atl": "America/New_York",
    "sea": "America/Los_Angeles",
}


def load() -> pd.DataFrame:
    df = pd.read_csv(MANUAL_CSV)
    df["date"] = pd.to_datetime(df["date"])
    df["datetime_local"] = pd.to_datetime(
        df["date"].dt.strftime("%Y-%m-%d") + "T" + df["kickoff_local"]
    )
    df = df.sort_values("date").reset_index(drop=True)
    print(f"[matches] {len(df)} matches loaded; date range: {df['date'].min().date()} – {df['date'].max().date()}")
    return df


def save(df: pd.DataFrame) -> None:
    out = PROCESSED_DIR / "matches_clean.parquet"
    df.to_parquet(out, index=False)
    print(f"[matches] Saved → {out}")


if __name__ == "__main__":
    df = load()
    save(df)
    print(df[["match_id", "city_id", "date", "round", "strain_rating"]].to_string(index=False))
