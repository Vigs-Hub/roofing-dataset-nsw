#!/usr/bin/env python3
"""Drop obvious non-roofers; log reasons. Manual review still required."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from common import OUTPUT, load_areas, today, write_csv
from search_businesses import BUSINESS_FIELDS

DROP_NAME_HINTS = [
    "gutter",
    "gutters",
    "supplies",
    "supply",
    "hardware",
    "steel city",
    "bunnings",
    "mitre 10",
    "wholesale",
    "scaffolding",
    "solar only",
]


def classify(row: dict[str, str], keywords: list[str]) -> tuple[str, str]:
    blob = " ".join(
        [
            row.get("name") or "",
            row.get("profile_categories") or "",
            row.get("notes") or "",
        ]
    ).lower()
    for hint in DROP_NAME_HINTS + [k.lower() for k in keywords]:
        if hint and hint in blob:
            # Keep genuine roofers that also do gutters
            if hint in {"gutter", "gutters"} and any(
                t in blob for t in ("roof", "roofer", "roofing", "tiler", "plumber")
            ):
                continue
            return "no", f"auto_drop:{hint}"
    return "pending", ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    cfg = load_areas()
    keywords = cfg.get("exclude_categories_keywords") or []

    with Path(args.input).open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    kept, dropped = [], []
    for row in rows:
        flag, reason = classify(row, keywords)
        row["include_flag"] = flag
        row["drop_reason"] = reason
        if flag == "no":
            dropped.append(row)
        else:
            kept.append(row)

    stamp = today()
    out_kept = OUTPUT / f"businesses_filtered_{stamp}.csv"
    out_drop = OUTPUT / f"businesses_dropped_{stamp}.csv"
    for r in kept + dropped:
        for field in BUSINESS_FIELDS:
            r.setdefault(field, "")
    write_csv(out_kept, kept, BUSINESS_FIELDS)
    write_csv(out_drop, dropped, BUSINESS_FIELDS)
    print(f"Kept {len(kept)} → {out_kept}")
    print(f"Dropped {len(dropped)} → {out_drop}")


if __name__ == "__main__":
    main()
