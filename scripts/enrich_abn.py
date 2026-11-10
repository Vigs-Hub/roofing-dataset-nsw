#!/usr/bin/env python3
"""Step 3a — ABN Lookup by business name (ABR web services)."""

from __future__ import annotations

import argparse
import csv
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

from common import OUTPUT, env_required, load_env, today, write_csv
from search_businesses import BUSINESS_FIELDS

NS = {"abr": "http://abr.business.gov.au/ABRXMLSearch/"}


def abr_search_by_name(name: str, guid: str) -> dict[str, str]:
    url = "https://abr.business.gov.au/abrxmlsearch/AbrXmlSearch.asmx/ABRSearchByNameAdvancedSimple2017"
    params = {
        "name": name,
        "postcode": "",
        "legalName": "Y",
        "tradingName": "Y",
        "businessName": "Y",
        "activeABNsOnly": "Y",
        "NSW": "Y",
        "SA": "N",
        "ACT": "N",
        "VIC": "N",
        "WA": "N",
        "NT": "N",
        "QLD": "N",
        "TAS": "N",
        "authenticationGuid": guid,
        "searchWidth": "Typical",
        "minimumScore": "80",
        "maxSearchResults": "5",
    }
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    result = root.find(".//abr:searchResultsList/abr:searchResultsRecord", NS)
    if result is None:
        return {}
    abn = (result.findtext(".//abr:ABN/abr:identifierValue", default="", namespaces=NS) or "").strip()
    status = (result.findtext(".//abr:ABN/abr:identifierStatus", default="", namespaces=NS) or "").strip()
    entity = (result.findtext(".//abr:entityType/abr:entityDescription", default="", namespaces=NS) or "").strip()
    # GST / start dates vary by payload shape; keep blanks when absent
    return {
        "abn": abn,
        "abn_status": status,
        "entity_type": entity,
        "abn_start_date": "",
        "gst_registered": "",
        "years_trading": "",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="businesses CSV from search_businesses.py")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--sleep", type=float, default=0.4)
    args = parser.parse_args()
    load_env()
    guid = env_required("ABN_GUID")

    with Path(args.input).open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if args.limit:
        rows = rows[: args.limit]

    for i, row in enumerate(rows, start=1):
        name = (row.get("name") or "").strip()
        if not name:
            continue
        print(f"[{i}/{len(rows)}] ABN: {name}")
        try:
            info = abr_search_by_name(name, guid)
            row.update(info)
            row["notes"] = (row.get("notes") or "") + f" | ABN checked {today()}"
        except Exception as exc:  # noqa: BLE001
            row["notes"] = (row.get("notes") or "") + f" | ABN error: {exc}"
        time.sleep(args.sleep)

    out = OUTPUT / f"businesses_abn_{today()}.csv"
    for r in rows:
        for field in BUSINESS_FIELDS:
            r.setdefault(field, "")
    write_csv(out, rows, BUSINESS_FIELDS)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
