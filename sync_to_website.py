"""
Sync updated dashboard JSON to the Astro website's public folder.
Run after: python run_pipeline.py --export-only

Usage:
    python sync_to_website.py
    python sync_to_website.py --website-dir "D:/MyOtherWebsitePath"
"""
import argparse
import shutil
from pathlib import Path

DEFAULT_WEBSITE = Path("D:/Website")
SRC_DATA = Path(__file__).parent / "site" / "data"
SRC_DASHBOARD = Path(__file__).parent / "site" / "dashboard.html"


def sync(website_dir: Path = DEFAULT_WEBSITE) -> None:
    dest_data = website_dir / "public" / "worldcup-transit" / "data"
    dest_dashboard = website_dir / "public" / "worldcup-transit" / "dashboard.html"

    if not website_dir.exists():
        raise FileNotFoundError(f"Website directory not found: {website_dir}")

    dest_data.mkdir(parents=True, exist_ok=True)

    # Copy JSON data files
    copied = 0
    for json_file in SRC_DATA.glob("*.json"):
        shutil.copy2(json_file, dest_data / json_file.name)
        print(f"  {json_file.name}")
        copied += 1

    # Copy dashboard HTML (in case it changed)
    if SRC_DASHBOARD.exists():
        shutil.copy2(SRC_DASHBOARD, dest_dashboard)
        print(f"  dashboard.html")

    print(f"\nSynced {copied} JSON files + dashboard.html to {website_dir / 'public' / 'worldcup-transit'}")
    print("Run 'astro build' (or 'astro dev') in the website directory to pick up changes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--website-dir", type=Path, default=DEFAULT_WEBSITE)
    args = parser.parse_args()
    sync(args.website_dir)
