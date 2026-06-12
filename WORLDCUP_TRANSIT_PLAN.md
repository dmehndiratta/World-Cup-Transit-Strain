# PLAN: Full Capacity — How the 2026 World Cup Stress-Tests North American Transit

> Plan file for Claude Code. Execute phases in order. Each phase has acceptance criteria.
> Owner: Dhruv Mehndiratta · Site: dhruv-mehndiratta.com · Started: June 2026 (tournament runs Jun 11 – Jul 19, 2026)

## 0. Project summary

A two-part portfolio project:

1. **Research report** (web-native HTML, long-form): causal-inference analysis of World Cup ridership impact, fare-cost comparison, and operational-strain assessment across six host cities — **Toronto, Vancouver, New York/New Jersey, Atlanta, Seattle, Mexico City** — benchmarked against prior tournaments (Russia 2018, Qatar 2022, Atlanta 1996 Olympics).
2. **Interactive tool** ("Transit Strain Dashboard"): a standalone static HTML/JS page (no backend) embeddable on dhruv-mehndiratta.com. All data pre-computed to JSON by the Python pipeline.

**Skills narrative:** applies an economics background (synthetic control, diff-in-diff, event studies, SARIMA, elasticities) to live event data; demonstrates new skills (GTFS data engineering, public API pipelines, D3/Leaflet front-end); builds domain knowledge of six transit systems.

**Methods bar:** full academic rigor — synthetic control with placebo inference, fixed-effects panel DiD, match-window event studies on daily/hourly data, forecast counterfactuals. Every causal claim needs an identification argument and robustness check.

## 1. Repo structure

```
worldcup-transit/
├── PLAN.md                  # this file
├── README.md
├── data/
│   ├── raw/                 # downloaded source data (gitignore large files)
│   ├── interim/             # cleaned per-source tables
│   └── processed/           # analysis-ready panels + JSON for the dashboard
├── pipeline/
│   ├── 01_fetch/            # one script per source (idempotent, cached)
│   ├── 02_clean/
│   ├── 03_analysis/         # one notebook/script per method
│   └── 04_export/           # writes site/data/*.json
├── site/
│   ├── report.html          # the long-form report
│   ├── dashboard.html       # the interactive tool (self-contained)
│   └── data/                # pre-computed JSON consumed by dashboard
└── tests/                   # data validation + sanity checks
```

Python 3.11+, `pandas`, `statsmodels`, `pysyncon` (or `SparseSC`) for synthetic control, `linearmodels` for panel FE, `requests`, `gtfs-kit`. Front-end: vanilla JS + D3 v7 + Leaflet from CDN, single-file pages.

## 2. Data sources (all free)

### Ridership (core dependent variable)

| City | Source | Granularity | Access |
|---|---|---|---|
| NY/NJ | MTA Subway Hourly Ridership — data.ny.gov (Socrata API; dataset `5wq4-mkjj` = "Beginning 2025" **verified Jun 2026**; `wujg-7c2s` = 2020–2024 archive for baselines) | Hourly, station-level | Socrata API, no key needed for low volume |
| Mexico City | CDMX Portal de Datos Abiertos — "Afluencia diaria del Metro" (datos.cdmx.gob.mx) | Daily, by line/station | CSV/API |
| Toronto | TTC CEO/board monthly reports (ridership + boardings); Toronto Open Data (open.toronto.ca) for subway delay logs; Metrolinx Open Data for GO/UP GTFS | Monthly (weekly during WC if published) | Scrape/manual extract from PDFs + open data |
| Vancouver | TransLink Accountability/Performance dashboards + Transit Service Performance Review; translink.ca open API (key is free) | Monthly system; annual stop-level | API + reports |
| Atlanta | NTD Monthly Ridership (MARTA) + MARTA KPI reports | Monthly | NTD download/Socrata |
| Seattle | NTD Monthly (Sound Transit, King Co. Metro) + Sound Transit ridership dashboards | Monthly; quarterly station-level | NTD + agency portal |
| All US + donor pool | **FTA National Transit Database, Complete Monthly Ridership** — data.transportation.gov dataset `8bui-9xvu` (Socrata API) | Monthly, agency × mode, 2002–present | Primary panel backbone |

Donor pool for synthetic control / DiD controls (non-host systems): Chicago CTA, WMATA (DC), SEPTA-excluded (Philly is a host — exclude!), MBTA-excluded (Boston is a host — exclude!), Montreal STM, Calgary Transit, Edmonton, Portland TriMet, Minneapolis Metro Transit, Denver RTD, Sacramento, San Diego MTS, Pittsburgh, Cleveland, Ottawa OC Transpo. **Rule: donor pool must contain zero 2026 host-city agencies** (16 host cities — check every donor against the full host list: ATL, BOS, DAL, HOU, KC, LA, MIA, NY/NJ, PHL, SF Bay, SEA, TOR, VAN, MEX, GDL, MTY).

### Schedules / capacity / service supply

- GTFS static feeds for all six cities (Transitland index, transit.land; agency portals). Compare June 2026 feed vs. June 2025 feed → measured service-hour and headway changes (supply response).
- GTFS-Realtime where free: TTC (open.toronto.ca), TransLink API, MTA, Sound Transit — used for the dashboard's "live-ish" headway snapshots if time allows (stretch).
- NTD monthly Vehicle Revenue Hours/Miles = supply-side panel variable.

### Fares

- Manual table from agency fare pages (June 2026): base fare, day pass, airport-to-downtown, stadium-trip cost. Capture the NJ Transit World Cup special-fare controversy ($150 Secaucus train package / $80 bus reports — verify current numbers from NJT and news coverage before publishing).
- Event-fare policies: which cities bundle transit with match tickets (Vancouver, Seattle reported; verify all six).

### Match & event data

- Official FIFA match schedule (fifa.com) for all six cities: dates, kickoff times (local), stadium, expected capacity. Build `matches.csv`: city, date, kickoff_local, stadium, capacity, round.
- Fan Festival locations + dates (each host city site).
- Stadium → transit mapping: serving lines/stations, walk distance, park-and-ride.

### Prior tournaments & priors

- Russia 2018 / Qatar 2022: visitor counts (~3M / ~1M), free-transit policies, Doha Metro ridership reports — literature for priors on % lift.
- Atlanta 1996 Olympics: MARTA expansion + ridership during games (historical NTD).
- Academic literature: mega-event transit demand studies; cite 3–5 papers in the report.

## 3. Phases

### Phase 1 — Scaffold & data acquisition (build first)

1. Create repo structure above; `requirements.txt`; `.gitignore` for `data/raw`.
2. Write idempotent fetch scripts (cache to `data/raw`, skip if fresh):
   - `fetch_ntd.py` (Socrata, full monthly panel 2015–present, UPT + VRH by agency×mode)
   - `fetch_mta_hourly.py` (June–July 2025 baseline + rolling 2026 pulls; filter to stations near MetLife access points — Penn Station, Secaucus is NJT not MTA, so also grab NJT data if any is public; otherwise MTA citywide + Penn-corridor)
   - `fetch_cdmx_metro.py` (daily afluencia, 2024–present)
   - `fetch_gtfs.py` (static feeds, all 6 cities, current + archived June 2025 via Transitland archive)
   - Manual-entry CSVs with schema validation: `fares.csv`, `matches.csv`, `surge_plans.csv` (announced service increases, e.g., TransLink +600 bus trips/day, $21.6M budget; TTC 3.8M projected boardings)
3. **Acceptance:** every fetch script runs clean twice (idempotent); row counts logged; a `data_inventory.md` listing each source, vintage, and gaps.

### Phase 2 — Cleaning & panel construction

1. Build `panel_monthly.parquet`: agency × month, UPT, VRH, VRM, 2015–present, host flag, treatment window flag (Jun–Jul 2026). Canada/Mexico agencies appended from agency reports (document any frequency mismatch).
2. Build `daily_nyc.parquet` and `daily_cdmx.parquet` with match-day flags, kickoff windows (±3h), distance-to-stadium station tiers.
3. COVID handling: include 2015–2019 + 2022–2025 in pre-period; never let 2020–21 enter synthetic-control fitting without a dummy/exclusion. Document the choice.
4. **Acceptance:** validation tests pass (no duplicate keys, ridership > 0, continuous month index); summary-stats notebook renders.

### Phase 3 — Econometric analysis (one script per method, each producing figures + a results JSON)

1. **Synthetic control** (`sc_hostcities.py`): per host agency, donor-pool weights on pre-period (2015–2019, 2022–May 2026) monthly UPT; treatment = June/July 2026. Inference: in-space placebos (run every donor as pseudo-treated, rank RMSPE ratios), report pseudo p-values. Sensitivity: leave-one-out donors, alternative pre-periods.
2. **Panel DiD** (`did_panel.py`): log(UPT) on Host×WCwindow with agency and month-year FE, clustered SEs by agency; event-time leads/lags plot to check pre-trends.
3. **Event study, daily/hourly** (`event_nyc.py`, `event_cdmx.py`): match-day regressions with day-of-week × week FE, weather controls if cheap (NOAA/SMN daily); estimate lift by hour relative to kickoff and by station tier. This is the headline micro evidence.
4. **SARIMA counterfactual** (`forecast_baseline.py`): fit through May 2026, forecast Jun–Jul, compare realized vs. forecast with prediction intervals — a transparent robustness companion to SC.
5. **Fare burden & elasticity context** (`fares_analysis.py`): cost of a stadium round-trip per city (absolute, PPP-adjusted, % of local hourly minimum wage); contrast with literature fare elasticities (≈ −0.3 short-run) to discuss what surge pricing does to demand and equity.
6. **Strain index** (`strain_index.py`): per city-matchday composite = projected incremental riders (capacity × transit mode-share assumption) ÷ scheduled capacity in the stadium corridor (from GTFS headways × vehicle capacity), plus announced supply response. Document all assumptions in a table.
7. **Acceptance:** each method outputs (a) figure(s) in `site/assets/`, (b) `results_<method>.json`, (c) a written interpretation block with identification assumptions and caveats. A `robustness.md` collects placebo/sensitivity results. **Verify: no method silently uses 2020–21 as normal data; all SEs/inference methods stated.**

### Phase 4 — Report (`site/report.html`)

Long-form web report, single HTML file, readable typography, charts as inline SVG/PNG from Phase 3. Structure:

1. Hook: opening day (Jun 11, Mexico City) + the NJ $150 train story vs. FIFA's free-transit history.
2. Six city profiles (system, stadium link, baseline vs. pre-COVID ridership, fares, surge plan).
3. What prior tournaments predict (Russia 2018, Qatar 2022, Atlanta 1996).
4. Results: SC + DiD (system level), event studies (micro level), forecast comparison; honest nulls if effects are small — monthly data may dilute a 4-week event, say so.
5. Fare burden & equity.
6. Strain index ranking + business insights: surge-pricing revenue vs. goodwill trade-off; LA 2028 capacity implications; corridor advertising exposure; staffing cost per incremental rider; ticket-transit bundling case.
7. Methods appendix (specs, donor pools, robustness) + full data-source citations with links.

**Acceptance:** every number in the report traces to a pipeline output; citation links resolve; renders well on mobile.

### Phase 5 — Interactive dashboard (`site/dashboard.html`)

Single self-contained file (D3 + Leaflet via CDN, all data from `site/data/*.json`):

1. **Map view**: North America, 6 city markers sized by strain index; click → city panel.
2. **City panel**: match calendar with per-match strain gauge; ridership chart (actual vs. synthetic/forecast counterfactual, shaded match days); stadium corridor mini-map with serving lines.
3. **Fare comparator**: bar chart — stadium round-trip cost per city, toggle absolute / % of minimum wage; NJ special fares highlighted.
4. **What-if widget**: sliders (attendance, transit mode share, service uplift %) → projected load vs. capacity bar; exposes the strain-index math interactively.
5. **Insights strip**: 4–5 headline stats that rotate (e.g., "TransLink: $21.6M for ~600 extra daily bus trips").
6. No backend, no build step, no localStorage requirement; works from `file://` and embeds via iframe on dhruv-mehndiratta.com.

**Acceptance:** loads < 2s on broadband; all data from JSON (no hardcoded numbers in JS); graceful "data pending" states for late-tournament dates; tested in Chrome + mobile viewport.

### Phase 6 — Verification & publish

1. Cross-check 10 random report numbers against raw sources.
2. Re-run full pipeline from clean `data/raw` to confirm reproducibility.
3. Lighthouse pass on both pages; alt text on figures.
4. Write README with reproduction instructions — the README is part of the portfolio story.
5. Publish to dhruv-mehndiratta.com; add an update cadence note (data refreshes weekly during the tournament; final update after Jul 19 final).

## 4. Timeline (tournament-aware)

- **Week 1 (now, group stage):** Phases 1–2. Start collecting daily data immediately — MTA/CDMX history is retained, but agency dashboards and news-reported numbers (e.g., first-match boardings) should be snapshotted now.
- **Weeks 2–3:** Phase 3 on early-tournament data + full pre-period; draft report sections 1–3; build dashboard shell with baseline data.
- **Week 4 (knockouts):** Phase 4–5 with group-stage results in; publish v1 mid-knockouts ("living analysis" framing is a feature).
- **Post-final (late July):** full-tournament re-estimation, final report + dashboard v2. Note: NTD monthly data for June lands ~August; SC/DiD finalize then — publish event-study results first, panel results as an update.

## 5. Risks & mitigations

- **Canadian/Mexican data ≠ NTD uniformity** → accept frequency mismatch; lean on NYC/CDMX for micro evidence, NTD panel for US causal estimates, agency reports for TOR/VAN narrative + monthly points. Be explicit about asymmetry.
- **Monthly granularity dilutes effect** → that's a finding, not a failure; event studies carry the headline.
- **PDF-locked TTC/TransLink numbers** → small manual-entry CSVs with source URL + page number per row.
- **API/dataset IDs drift** → every fetch script prints the dataset vintage; verify Socrata IDs at run time (search portal if 404).
- **Scope creep** → 16-city coverage is OUT of scope except a context table; depth on 6.

## 6. Source links (verify at fetch time)

- NTD monthly: https://www.transit.dot.gov/ntd/data-product/monthly-module-adjusted-data-release and https://data.transportation.gov/Public-Transit/Complete-Monthly-Ridership-with-Adjustments-and-Es/8bui-9xvu
- MTA hourly ridership: https://data.ny.gov/Transportation/MTA-Subway-Hourly-Ridership-Beginning-2025/5wq4-mkjj (note: publication lags ~4–6 weeks; check refresh date before tournament analysis)
- CDMX Metro afluencia: https://datos.cdmx.gob.mx
- Toronto Open Data (TTC GTFS-RT, delays): https://open.toronto.ca ; Metrolinx: https://www.metrolinx.com/en/about-us/open-data
- TransLink API + WC service plan: https://developer.translink.ca ; https://www.translink.ca/rider-guide/taking-transit-to-the-world-cup
- Transitland feed registry/archive: https://www.transit.land
- GTFS ecosystem index: https://github.com/MobilityData/awesome-transit
- FIFA match schedule: https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026
- Context reporting: TransLink $21.6M (Daily Hive), TTC 3.8M boardings (Globe and Mail), NJ fares (Front Office Sports / NBC Boston), host-city transit improvements (Grist, Next City)
