#!/usr/bin/env python3
"""Build ABS SAL → LGA suburb list for configured LGAs."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from common import CONFIG_PATH, ROOT, load_areas, today, write_csv

REF = ROOT / "data" / "reference" / "CG_SAL_2021_LGA_2021.csv"
OUT = ROOT / "data" / "processed" / "suburb_list.csv"
ABS_SOURCE = (
    "https://www.abs.gov.au/statistics/standards/"
    "australian-statistical-geography-standard-asgs/"
    "edition-3-july-2021-june-2026/access-and-downloads/correspondences"
)


def main() -> None:
    if not REF.exists():
        raise SystemExit(
            f"Missing {REF}. Download ASGS correspondences ZIP from data.gov.au "
            "and extract CG_SAL_2021_LGA_2021.csv into data/reference/."
        )

    cfg = load_areas()
    target = {str(x["code"]): x["name"] for x in cfg["lgas"]}
    area_label = {x["name"]: x["area_label"] for x in cfg["lgas"]}
    main = cfg.get("main_suburbs", {})

    by_sal: dict[str, list[dict[str, str]]] = defaultdict(list)
    with REF.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            by_sal[row["SAL_CODE_2021"]].append(row)

    selected: list[dict[str, object]] = []
    for sal_code, rows in by_sal.items():
        primary = max(rows, key=lambda r: float(r["RATIO_FROM_TO"]))
        lga_code = primary["LGA_CODE_2021"]
        if lga_code not in target:
            continue
        ratio = float(primary["RATIO_FROM_TO"])
        if ratio < 0.5:
            continue
        lga = target[lga_code]
        suburb = primary["SAL_NAME_2021"]
        selected.append(
            {
                "sal_code": sal_code,
                "suburb": suburb,
                "lga_code": lga_code,
                "lga": lga,
                "area_label": area_label[lga],
                "ratio_to_lga": ratio,
                "quality": primary["OVERALL_QUALITY_INDICATOR"],
                "source_link": ABS_SOURCE,
                "source_file": REF.name,
                "collection_date": today(),
                "is_main_suburb": "yes" if suburb in set(main.get(lga, [])) else "no",
            }
        )

    selected.sort(key=lambda r: (str(r["lga"]), str(r["suburb"])))
    fields = list(selected[0].keys()) if selected else []
    write_csv(OUT, selected, fields)

    counts: dict[str, int] = {}
    for r in selected:
        counts[str(r["lga"])] = counts.get(str(r["lga"]), 0) + 1
    print(f"Wrote {OUT} ({len(selected)} suburbs)")
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")
    print(f"Config: {CONFIG_PATH}")


if __name__ == "__main__":
    main()
