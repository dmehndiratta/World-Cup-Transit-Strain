# Full Capacity: How the 2026 World Cup Stress-Tests North American Transit

**Author:** Dhruv Mehndiratta · [dhruv-mehndiratta.com](https://dhruv-mehndiratta.com)  
**Tournament:** FIFA World Cup 2026 · Jun 11 – Jul 19, 2026  
**Focus cities:** New York/New Jersey · Mexico City · Toronto · Vancouver · Atlanta · Seattle

---

## What this is

A two-part portfolio project:

1. **[Research Report](site/report.html)** — causal-inference analysis of World Cup ridership impact, fare-cost comparison, and operational-strain assessment across six host cities. Methods: synthetic control, panel DiD, event studies, SARIMA, elasticities.

2. **[Interactive Dashboard](site/dashboard.html)** — standalone static HTML/JS page embeddable on dhruv-mehndiratta.com. All data pre-computed to JSON by this Python pipeline.

Data refreshes **weekly** during the tournament via GitHub Actions.

---

## Reproduce locally

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_pipeline.py
```

This fetches the latest data from all sources, runs the analysis, and regenerates `site/data/*.json`.  
Open `site/dashboard.html` in a browser — no server required.

---

## Data sources

| Source | Granularity | Access |
|--------|------------|--------|
| FTA National Transit Database (NTD) | Monthly, agency×mode | data.transportation.gov Socrata API |
| MTA Subway Hourly Ridership | Hourly, station-level | data.ny.gov Socrata API |
| CDMX Metro Afluencia | Daily, line/station | datos.cdmx.gob.mx |
| GTFS static feeds | Schedule/capacity | Transitland archive |
| FIFA match schedule | Match-level | fifa.com |
| Agency fares & surge plans | Manual lookup | `data/manual/` |

See `data/manual/data_inventory.md` for vintage, gaps, and verification notes.

---

## Pipeline

```
pipeline/
├── 01_fetch/   — idempotent downloaders (cache to data/raw/, skip if fresh)
├── 02_clean/   — validated, typed parquet outputs in data/interim/
├── 03_analysis/— strain index + event study results → results_*.json
└── 04_export/  — writes site/data/*.json consumed by dashboard
```

---

## Auto-update (GitHub Actions)

`.github/workflows/weekly_update.yml` runs every Sunday at 06:00 UTC, regenerates all JSON, and commits changes. Enable GitHub Pages (`gh-pages` branch or `docs/` folder) for a live URL.

---

## Methodology notes

- **COVID exclusion:** 2020–21 excluded from synthetic-control fitting; 2022–present used as post-treatment recovery baseline.
- **Donor pool:** non-host US/Canadian agencies only (see plan for excluded cities).
- **Lag:** MTA and NTD data publish with ~4–6 week lag; event-study results appear mid-tournament; panel DiD results finalize post-NTD August release.
- Every number in the report traces to a `site/data/` JSON output.
