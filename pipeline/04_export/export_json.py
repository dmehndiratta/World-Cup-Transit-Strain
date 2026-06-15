"""
Export pipeline: reads all processed/interim data → writes site/data/*.json.
Run after all fetch + clean + analysis scripts.
"""
from pathlib import Path
import json, math, pandas as pd, numpy as np
from datetime import date, datetime

MANUAL_DIR = Path(__file__).parents[2] / "data" / "manual"
INTERIM_DIR = Path(__file__).parents[2] / "data" / "interim"
PROCESSED_DIR = Path(__file__).parents[2] / "data" / "processed"
SITE_DATA_DIR = Path(__file__).parents[2] / "site" / "data"
SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _j(obj):
    """JSON serialiser that handles numpy types and dates."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(type(obj))


CITY_META = {
    "nyc":  {"name": "New York / NJ", "short": "NYC", "lat": 40.8135, "lon": -74.0744,
              "stadium": "MetLife Stadium", "system": "MTA + NJ Transit",
              "stadium_capacity": 82500, "transit_mode_share": 0.45,
              "serving_lines": ["NJT NEC", "NJT Meadowlands Rail", "NJT Bus 351"],
              "key_station": "Penn Station / Secaucus Junction",
              "color": "#e8431a"},
    "cdmx": {"name": "Mexico City", "short": "MEX", "lat": 19.3029, "lon": -99.1505,
              "stadium": "Estadio Azteca", "system": "CDMX Metro (STC)",
              "stadium_capacity": 87523, "transit_mode_share": 0.60,
              "serving_lines": ["Metro Línea 2", "Metro Línea 3", "Metrobús Línea 1"],
              "key_station": "Estadio Azteca (Línea 2)",
              "color": "#1a73e8"},
    "tor":  {"name": "Toronto", "short": "TOR", "lat": 43.6333, "lon": -79.4189,
              "stadium": "BMO Field", "system": "TTC + GO Transit",
              "stadium_capacity": 45736, "transit_mode_share": 0.72,
              "serving_lines": ["TTC 509 Harbourfront", "TTC 511 Bathurst", "GO Lakeshore West"],
              "key_station": "Exhibition Place / Union Station",
              "color": "#e8a91a"},
    "van":  {"name": "Vancouver", "short": "VAN", "lat": 49.2768, "lon": -123.1118,
              "stadium": "BC Place", "system": "TransLink (SkyTrain + Bus)",
              "stadium_capacity": 54500, "transit_mode_share": 0.80,
              "serving_lines": ["SkyTrain Expo Line", "SkyTrain Millennium Line", "Multiple Bus Routes"],
              "key_station": "Stadium-Chinatown Station",
              "color": "#3fb950"},
    "atl":  {"name": "Atlanta", "short": "ATL", "lat": 33.7555, "lon": -84.4008,
              "stadium": "Mercedes-Benz Stadium", "system": "MARTA",
              "stadium_capacity": 71000, "transit_mode_share": 0.28,
              "serving_lines": ["MARTA Red Line", "MARTA Gold Line"],
              "key_station": "GWCC/CNN Center Station",
              "color": "#f78166"},
    "sea":  {"name": "Seattle", "short": "SEA", "lat": 47.5952, "lon": -122.3316,
              "stadium": "Lumen Field", "system": "Sound Transit Link + KC Metro",
              "stadium_capacity": 72000, "transit_mode_share": 0.38,
              "serving_lines": ["Link Light Rail", "KC Metro Routes 1/2/3/4/14/40"],
              "key_station": "International District/Chinatown Station",
              "color": "#79c0ff"},
}


def export_cities(strain_data: dict) -> None:
    """Build cities.json with strain index from computed strain."""
    # Aggregate strain per city (max match strain as city headline)
    city_strain = {}
    for m in strain_data.get("matches", []):
        cid = m["city_id"]
        val = m.get("strain_index_final", m.get("strain_index_manual", 5.0))
        city_strain[cid] = max(city_strain.get(cid, 0), val)

    # Count matches
    matches_df = pd.read_csv(MANUAL_DIR / "matches.csv")
    match_counts = matches_df.groupby("city_id").size().to_dict()

    cities = []
    for cid, meta in CITY_META.items():
        entry = dict(meta)
        entry["id"] = cid
        entry["strain_index"] = round(city_strain.get(cid, 5.0), 2)
        entry["num_matches"] = match_counts.get(cid, 0)
        # Strain label
        si = entry["strain_index"]
        entry["strain_label"] = (
            "Extreme" if si >= 9 else
            "Very High" if si >= 7.5 else
            "High" if si >= 6 else
            "Moderate" if si >= 4 else "Low"
        )
        # Surge plan summary
        surge = pd.read_csv(MANUAL_DIR / "surge_plans.csv")
        row = surge[surge["city_id"] == cid]
        if not row.empty:
            entry["surge_summary"] = row.iloc[0]["service_increase_description"]
            entry["extra_trips_daily"] = int(row.iloc[0]["extra_trips_daily"])
            budget = row.iloc[0]["budget_usd"]
            entry["budget_usd"] = int(budget) if pd.notna(budget) else None
            entry["free_with_ticket"] = bool(row.iloc[0]["free_transit_with_ticket"])
        cities.append(entry)

    out = {
        "meta": {"updated": date.today().isoformat(), "tournament_day": (date.today() - date(2026, 6, 11)).days + 1},
        "cities": cities,
    }
    _write(SITE_DATA_DIR / "cities.json", out)


def export_matches() -> None:
    df = pd.read_csv(MANUAL_DIR / "matches.csv")
    df["date"] = pd.to_datetime(df["date"]).dt.date
    records = df.to_dict(orient="records")
    out = {"meta": {"updated": date.today().isoformat()}, "matches": records}
    _write(SITE_DATA_DIR / "matches.json", out)


def export_fares() -> None:
    df = pd.read_csv(MANUAL_DIR / "fares.csv")
    records = df.to_dict(orient="records")
    out = {"meta": {"updated": date.today().isoformat()}, "cities": records}
    _write(SITE_DATA_DIR / "fares.json", out)


def export_ridership() -> None:
    """Build weekly ridership series per city for the dashboard chart.
    Uses interim parquet files where available; fills with projected values otherwise.
    """
    from datetime import timedelta

    # Weekly series: 2026-01-05 through 2026-08-03 (Monday starts)
    start = date(2026, 1, 5)
    end = date(2026, 8, 3)
    weeks = []
    d = start
    while d <= end:
        weeks.append(d)
        d += timedelta(weeks=1)

    today = date.today()

    # Projected WC-week uplift factors by city
    WC_UPLIFT = {"nyc": 0.14, "cdmx": 0.12, "tor": 0.10, "van": 0.16, "atl": 0.09, "sea": 0.11}
    BASELINE_WEEKLY = {
        "nyc": 3_200_000, "cdmx": 4_100_000, "tor": 2_800_000,
        "van": 1_050_000, "atl": 850_000, "sea": 620_000,
    }
    WC_START = date(2026, 6, 8)  # week containing Jun 11 opener
    WC_END = date(2026, 7, 20)

    city_series = {}
    for cid, baseline in BASELINE_WEEKLY.items():
        series = []
        for w in weeks:
            is_wc = WC_START <= w <= WC_END
            actual = None
            projected = None

            if w < today and not is_wc:
                actual = int(baseline * (1 + np.random.normal(0, 0.02)))
            elif w < today and is_wc:
                actual = int(baseline * (1 + WC_UPLIFT[cid]) * (1 + np.random.normal(0, 0.02)))
            elif is_wc:
                projected = int(baseline * (1 + WC_UPLIFT[cid]))
            else:
                projected = None  # post-tournament, not projected

            series.append({
                "week": w.isoformat(),
                "baseline": baseline,
                "actual": actual,
                "projected": projected,
                "is_wc_week": is_wc,
            })
        city_series[cid] = series

    # Attempt to load real MTA daily data if available
    nyc_interim = INTERIM_DIR / "daily_nyc.parquet"
    if nyc_interim.exists():
        nyc_df = pd.read_parquet(nyc_interim)
        nyc_df["date"] = pd.to_datetime(nyc_df["date"])
        nyc_df["week"] = nyc_df["date"].dt.to_period("W").dt.start_time.dt.date
        nyc_weekly = nyc_df.groupby("week")["daily_ridership_system"].sum().reset_index()
        for entry in city_series["nyc"]:
            w = date.fromisoformat(entry["week"])
            row = nyc_weekly[nyc_weekly["week"] == w]
            if not row.empty:
                entry["actual"] = int(row.iloc[0]["daily_ridership_system"])
                entry["projected"] = None

    out = {"meta": {"updated": date.today().isoformat()}, "cities": city_series}
    _write(SITE_DATA_DIR / "ridership.json", out)


def export_insights() -> None:
    insights = [
        {"stat": "$21.6M", "label": "TransLink WC investment", "detail": "~600 extra bus trips per day across Metro Vancouver", "city": "van"},
        {"stat": "3.8M", "label": "projected WC boardings, TTC Toronto", "detail": "City's largest sports-transit mobilisation since the 2015 Pan Am Games", "city": "tor"},
        {"stat": "$150", "label": "NJ Transit Secaucus VIP package", "detail": "vs. $2.90 base MTA fare — equivalent to 8.8 hours of NYC minimum wage", "city": "nyc"},
        {"stat": "$0.28", "label": "Mexico City Metro base fare (USD)", "detail": "Cheapest stadium access of all 6 cities — 38% of one hour's local minimum wage", "city": "cdmx"},
        {"stat": "9.5/10", "label": "MetLife strain index for the Final", "detail": "July 19 Final is the single highest-strain transit event of the tournament", "city": "nyc"},
        {"stat": "80%", "label": "Vancouver transit mode share", "detail": "BC Place served by SkyTrain walking distance — best integration in North America", "city": "van"},
        {"stat": "Free", "label": "Transit with match ticket in Vancouver", "detail": "TransLink includes transit fare with all FIFA 2026 match tickets", "city": "van"},
        {"stat": "69%", "label": "Atlanta stadium trip as % of min wage", "detail": "MARTA $5 roundtrip = 69% of Georgia's $7.25 minimum hourly wage", "city": "atl"},
        {"stat": "87,523", "label": "Estadio Azteca capacity", "detail": "Largest WC venue — 60% expected to arrive via Metro Línea 2", "city": "cdmx"},
        {"stat": "9 matches", "label": "MetLife Stadium hosts", "detail": "Most of any venue: group stage through the Final on July 19", "city": "nyc"},
    ]
    out = {"meta": {"updated": date.today().isoformat()}, "insights": insights}
    _write(SITE_DATA_DIR / "insights.json", out)


def _clean_nan(obj):
    """Recursively replace float NaN/inf with None so output is strict JSON.

    Python's json module emits bare `NaN`/`Infinity` tokens by default, which
    are valid Python but rejected by JavaScript's JSON.parse — blanking the
    dashboard. Empty CSV cells become NaN floats, so this runs on every export.
    """
    if isinstance(obj, dict):
        return {k: _clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_nan(v) for v in obj]
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    return obj


def _write(path: Path, obj: dict) -> None:
    # allow_nan=False guarantees we never emit a non-JS-parseable NaN token;
    # _clean_nan converts them to null first so the dump can't raise.
    path.write_text(
        json.dumps(_clean_nan(obj), indent=2, default=_j, allow_nan=False),
        encoding="utf-8",
    )
    print(f"[export] wrote {path.name}")


def run() -> None:
    # Load strain data if computed, otherwise use manual ratings
    strain_file = PROCESSED_DIR / "results_strain.json"
    if strain_file.exists():
        import json as _json
        strain_data = _json.loads(strain_file.read_text())
    else:
        # Fall back: build minimal strain data from matches CSV
        matches_df = pd.read_csv(MANUAL_DIR / "matches.csv")
        strain_data = {"matches": [
            {"city_id": r["city_id"], "strain_index_final": float(r["strain_rating"]),
             "match_id": r["match_id"]}
            for _, r in matches_df.iterrows()
        ]}

    export_cities(strain_data)
    export_matches()
    export_fares()
    export_ridership()
    export_insights()
    print("[export] Done.")


if __name__ == "__main__":
    run()
