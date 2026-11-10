#!/usr/bin/env python3
"""Create a local sheet-ready CSV bundle (import into Google Sheets as 5 tabs)."""

from __future__ import annotations

import shutil
from pathlib import Path

from common import OUTPUT, ROOT, TEMPLATES, SUBURB_LIST, today

TAB_MAP = {
    "01_Businesses.csv": "Businesses.csv",
    "02_Area_demand.csv": "Area_demand.csv",
    "03_Roof_signals.csv": "Roof_signals.csv",
    "04_Map_pack.csv": "Map_pack.csv",
    "05_Notes.csv": "Notes.csv",
}


def main() -> None:
    dest = OUTPUT / f"sheet_bundle_{today()}"
    dest.mkdir(parents=True, exist_ok=True)

    for src_name, dest_name in TAB_MAP.items():
        src = TEMPLATES / src_name
        if not src.exists():
            raise SystemExit(f"Missing template: {src}")
        shutil.copy2(src, dest / dest_name)

    # Also drop the suburb driver list into the bundle for reference
    if SUBURB_LIST.exists():
        shutil.copy2(SUBURB_LIST, dest / "suburb_list.csv")

    readme = dest / "IMPORT.txt"
    readme.write_text(
        "\n".join(
            [
                "Import into one Google Sheet as separate tabs:",
                "1) Businesses.csv → tab 'Businesses'",
                "2) Area_demand.csv → tab 'Area demand'",
                "3) Roof_signals.csv → tab 'Roof signals'",
                "4) Map_pack.csv → tab 'Map pack'",
                "5) Notes.csv → tab 'Notes'",
                "",
                "Keep suburb_list.csv as a helper tab or local driver file.",
                "Every data row must keep source_link + collection_date.",
                "",
                f"Generated: {today()}",
                f"Project root: {ROOT}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Sheet bundle ready: {dest}")


if __name__ == "__main__":
    main()
