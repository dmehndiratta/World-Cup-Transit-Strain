"""
Master pipeline runner. Execute in order:
  1. Fetch (idempotent, cached)
  2. Clean
  3. Analysis
  4. Export JSON for dashboard

Usage:
  python run_pipeline.py             # full pipeline
  python run_pipeline.py --export-only  # skip fetch/clean, regenerate JSON only
"""
import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def _load(rel_path: str):
    """Load a module from a path that may start with a digit (e.g., 01_fetch/)."""
    abs_path = ROOT / rel_path
    spec = importlib.util.spec_from_file_location(abs_path.stem, abs_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_step(label: str, rel_path: str, fn: str = "run", **kwargs):
    try:
        mod = _load(rel_path)
        getattr(mod, fn)(**kwargs)
    except Exception as exc:
        print(f"  [skip] {label}: {exc}")


def run_full():
    print("=" * 60)
    print("PHASE 1 — FETCH")
    print("=" * 60)
    run_step("fetch_ntd", "pipeline/01_fetch/fetch_ntd.py", fn="fetch")
    run_step("fetch_mta_hourly", "pipeline/01_fetch/fetch_mta_hourly.py", fn="fetch",
             years=[2024, 2025, 2026])
    run_step("fetch_cdmx_metro", "pipeline/01_fetch/fetch_cdmx_metro.py", fn="fetch")
    run_step("fetch_matches", "pipeline/01_fetch/fetch_matches.py", fn="load")

    print("\n" + "=" * 60)
    print("PHASE 2 — CLEAN")
    print("=" * 60)
    run_step("clean_ntd", "pipeline/02_clean/clean_ntd.py")
    run_step("clean_mta", "pipeline/02_clean/clean_mta.py")
    run_step("clean_cdmx", "pipeline/02_clean/clean_cdmx.py")

    print("\n" + "=" * 60)
    print("PHASE 3 — ANALYSIS")
    print("=" * 60)
    run_step("strain_index", "pipeline/03_analysis/strain_index.py")

    run_export()


def run_export():
    print("\n" + "=" * 60)
    print("PHASE 4 — EXPORT JSON")
    print("=" * 60)
    run_step("export_json", "pipeline/04_export/export_json.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Worldcup Transit pipeline")
    parser.add_argument("--export-only", action="store_true",
                        help="Skip fetch/clean, only regenerate site/data/*.json")
    args = parser.parse_args()

    if args.export_only:
        run_export()
    else:
        run_full()
