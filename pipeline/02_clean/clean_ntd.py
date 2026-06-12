"""
Clean raw NTD monthly data → interim/panel_monthly.parquet
Key outputs: agency × month panel with UPT, VRH, host flags.
"""
from pathlib import Path
import pandas as pd
import numpy as np

RAW_DIR = Path(__file__).parents[2] / "data" / "raw"
INTERIM_DIR = Path(__file__).parents[2] / "data" / "interim"
INTERIM_DIR.mkdir(parents=True, exist_ok=True)

# All 2026 host-city agency NTD IDs (exclude from donor pool)
HOST_NTDIDS = {
    "nyc": ["2008", "2006", "2080", "2086"],  # MTA NYC Transit, MTA Bus, NJ Transit
    "cdmx": [],  # Not in NTD (Mexico)
    "tor": [],   # Not in NTD (Canada)
    "van": [],   # Not in NTD (Canada)
    "atl": ["4034"],  # MARTA
    "sea": ["5006", "5011"],  # Sound Transit, King County Metro
    # Other 2026 hosts to exclude from donor:
    "bos": ["1003"],  # MBTA
    "la": ["9003"],   # LA Metro
    "sf": ["9015"],   # BART
    "phi": ["2030"],  # SEPTA
    "mia": ["4022"],  # Miami-Dade Transit
    "dal": ["9013"],  # DART
    "hou": ["6044"],  # Houston Metro
    "kc": ["5028"],   # KC Streetcar area
}

COVID_YEARS = [2020, 2021]  # Excluded from SC/DiD fitting window


def run() -> pd.DataFrame:
    raw_file = RAW_DIR / "ntd_monthly.parquet"
    if not raw_file.exists():
        raise FileNotFoundError(f"Run fetch_ntd.py first: {raw_file}")

    df = pd.read_parquet(raw_file)
    print(f"[clean_ntd] Raw shape: {df.shape}")

    # Standardize column names (Socrata returns lowercase_underscored)
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]

    # Parse period
    df["year"] = pd.to_numeric(df.get("year", df.get("report_year")), errors="coerce")
    df["month"] = pd.to_numeric(df.get("month", df.get("report_period")), errors="coerce")
    df = df.dropna(subset=["year", "month"])
    df["period"] = pd.to_datetime(
        df["year"].astype(int).astype(str) + "-" + df["month"].astype(int).astype(str).str.zfill(2) + "-01"
    )

    # Numeric ridership columns
    for col in ["upt", "vrh", "vrm"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop COVID years for baseline fitting (keep with flag for sensitivity)
    df["is_covid"] = df["year"].isin(COVID_YEARS)

    # Flag host-city agencies
    all_host_ids = set(id_ for ids in HOST_NTDIDS.values() for id_ in ids)
    ntdid_col = next((c for c in df.columns if "ntd" in c.lower() and "id" in c.lower()), None)
    if ntdid_col:
        df["ntdid"] = df[ntdid_col].astype(str)
        df["is_host_city"] = df["ntdid"].isin(all_host_ids)

    # Filter 2015-present
    df = df[df["year"] >= 2015].copy()

    # Add WC treatment window flag
    df["is_wc_window"] = (df["year"] == 2026) & (df["month"].isin([6, 7]))

    out = INTERIM_DIR / "panel_monthly.parquet"
    df.to_parquet(out, index=False)
    print(f"[clean_ntd] Cleaned → {out} ({len(df):,} rows)")
    return df


if __name__ == "__main__":
    df = run()
    print(df[["period", "ntdid", "upt", "is_host_city", "is_wc_window"]].head(20))
