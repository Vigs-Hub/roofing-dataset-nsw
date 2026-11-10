#!/usr/bin/env python3
"""
Step 2 — Find roofers via DataForSEO Google Maps (Places Text Search backup).

Usage:
  python scripts/search_businesses.py --limit-suburbs 2          # dry-ish smoke
  python scripts/search_businesses.py --lga Wollongong
  python scripts/search_businesses.py --provider places          # backup API
  python scripts/search_businesses.py                            # full run
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import requests

from common import (
    OUTPUT,
    env_required,
    load_areas,
    load_env,
    load_suburbs,
    spend_cap,
    today,
    write_csv,
)

BUSINESS_FIELDS = [
    "business_id",
    "name",
    "address",
    "suburb",
    "lga",
    "phone",
    "website",
    "rating",
    "review_count",
    "place_id",
    "maps_url",
    "newest_review_date",
    "profile_categories",
    "abn",
    "entity_type",
    "abn_start_date",
    "years_trading",
    "abn_status",
    "gst_registered",
    "nsw_licence_number",
    "nsw_licence_class",
    "nsw_licence_status",
    "nsw_licence_expiry",
    "services",
    "owner_director_public",
    "crew_size_signal",
    "include_flag",
    "drop_reason",
    "source_search_term",
    "source_provider",
    "source_link",
    "collection_date",
    "notes",
]


def _auth_header(login: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


def dataforseo_maps_live(query: str, location_name: str) -> list[dict[str, Any]]:
    """Live Google Maps search via DataForSEO."""
    login = env_required("DATAFORSEO_LOGIN")
    password = env_required("DATAFORSEO_PASSWORD")
    url = "https://api.dataforseo.com/v3/business_data/google/maps/search/live"
    payload = [
        {
            "keyword": query,
            "location_name": location_name,
            "language_code": "en",
            "depth": 20,
        }
    ]
    resp = requests.post(url, headers=_auth_header(login, password), json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status_code") != 20000:
        raise RuntimeError(f"DataForSEO error: {data.get('status_message')} | {json.dumps(data)[:500]}")

    items: list[dict[str, Any]] = []
    for task in data.get("tasks") or []:
        for result in task.get("result") or []:
            items.extend(result.get("items") or [])
    return items


def places_text_search(query: str) -> list[dict[str, Any]]:
    """Official Google Places Text Search (New) backup."""
    key = env_required("GOOGLE_PLACES_API_KEY")
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,"
            "places.nationalPhoneNumber,places.websiteUri,"
            "places.rating,places.userRatingCount,places.googleMapsUri,"
            "places.types"
        ),
    }
    body = {"textQuery": query, "regionCode": "AU", "languageCode": "en"}
    resp = requests.post(url, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    return resp.json().get("places") or []


def normalize_dataforseo(item: dict[str, Any], suburb: str, lga: str, term: str) -> dict[str, Any]:
    place_id = item.get("place_id") or item.get("cid") or ""
    name = item.get("title") or item.get("name") or ""
    phone = item.get("phone") or ""
    website = item.get("url") or item.get("domain") or ""
    address = item.get("address") or ""
    rating = item.get("rating", {}).get("value") if isinstance(item.get("rating"), dict) else item.get("rating")
    reviews = item.get("rating", {}).get("votes_count") if isinstance(item.get("rating"), dict) else item.get("reviews_count")
    maps_url = item.get("url") or (f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else "")
    categories = item.get("category") or item.get("category_ids") or ""
    if isinstance(categories, list):
        categories = "|".join(str(c) for c in categories)
    bid = hashlib.sha1(f"{place_id}|{phone}|{website}|{name}".encode()).hexdigest()[:12]
    return {
        "business_id": bid,
        "name": name,
        "address": address,
        "suburb": suburb,
        "lga": lga,
        "phone": phone,
        "website": website,
        "rating": rating or "",
        "review_count": reviews or "",
        "place_id": place_id,
        "maps_url": maps_url,
        "newest_review_date": "",
        "profile_categories": categories,
        "include_flag": "pending",
        "drop_reason": "",
        "source_search_term": term,
        "source_provider": "dataforseo_google_maps",
        "source_link": maps_url or "https://api.dataforseo.com/v3/business_data/google/maps/search/live",
        "collection_date": today(),
        "notes": "",
    }


def normalize_places(item: dict[str, Any], suburb: str, lga: str, term: str) -> dict[str, Any]:
    place_id = item.get("id") or ""
    name = (item.get("displayName") or {}).get("text") or ""
    phone = item.get("nationalPhoneNumber") or ""
    website = item.get("websiteUri") or ""
    address = item.get("formattedAddress") or ""
    rating = item.get("rating") or ""
    reviews = item.get("userRatingCount") or ""
    maps_url = item.get("googleMapsUri") or ""
    categories = "|".join(item.get("types") or [])
    bid = hashlib.sha1(f"{place_id}|{phone}|{website}|{name}".encode()).hexdigest()[:12]
    return {
        "business_id": bid,
        "name": name,
        "address": address,
        "suburb": suburb,
        "lga": lga,
        "phone": phone,
        "website": website,
        "rating": rating,
        "review_count": reviews,
        "place_id": place_id,
        "maps_url": maps_url,
        "newest_review_date": "",
        "profile_categories": categories,
        "include_flag": "pending",
        "drop_reason": "",
        "source_search_term": term,
        "source_provider": "google_places_text_search",
        "source_link": maps_url or "https://developers.google.com/maps/documentation/places/web-service/text-search",
        "collection_date": today(),
        "notes": "",
    }


def dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dedupe on Place ID, then phone, then website."""
    seen_place: set[str] = set()
    seen_phone: set[str] = set()
    seen_web: set[str] = set()
    out: list[dict[str, Any]] = []
    for r in rows:
        pid = (r.get("place_id") or "").strip()
        phone = (r.get("phone") or "").strip().replace(" ", "")
        web = (r.get("website") or "").strip().rstrip("/").lower()
        if pid and pid in seen_place:
            continue
        if phone and phone in seen_phone:
            continue
        if web and web in seen_web:
            continue
        if pid:
            seen_place.add(pid)
        if phone:
            seen_phone.add(phone)
        if web:
            seen_web.add(web)
        out.append(r)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Search roofing businesses by suburb")
    parser.add_argument("--provider", choices=["dataforseo", "places"], default="dataforseo")
    parser.add_argument("--lga", default="", help="Filter to one LGA name")
    parser.add_argument("--limit-suburbs", type=int, default=0, help="Smoke-test limit")
    parser.add_argument("--sleep", type=float, default=1.0, help="Seconds between API calls")
    args = parser.parse_args()

    load_env()
    cfg = load_areas()
    terms = cfg["search_terms"]
    suburbs = load_suburbs()
    if args.lga:
        suburbs = [s for s in suburbs if s["lga"].lower() == args.lga.lower()]
    if args.limit_suburbs:
        suburbs = suburbs[: args.limit_suburbs]

    cap_name = "DATAFORSEO_SPEND_CAP_USD" if args.provider == "dataforseo" else "GOOGLE_PLACES_SPEND_CAP_USD"
    cap = spend_cap(cap_name)
    if cap is None:
        print(f"WARNING: {cap_name} not set (Neal still to confirm). Proceed carefully.")

    raw_dir = OUTPUT / "raw_searches" / today()
    raw_dir.mkdir(parents=True, exist_ok=True)

    collected: list[dict[str, Any]] = []
    calls = 0
    for suburb_row in suburbs:
        suburb = suburb_row["suburb"]
        lga = suburb_row["lga"]
        for term in terms:
            query = f"{term} {suburb} NSW"
            print(f"[{args.provider}] {query}")
            try:
                if args.provider == "dataforseo":
                    location_name = f"{suburb},New South Wales,Australia"
                    items = dataforseo_maps_live(query, location_name)
                    (raw_dir / f"{suburb}_{term}.json").write_text(
                        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    for item in items:
                        collected.append(normalize_dataforseo(item, suburb, lga, term))
                else:
                    items = places_text_search(query)
                    (raw_dir / f"{suburb}_{term}.json").write_text(
                        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    for item in items:
                        collected.append(normalize_places(item, suburb, lga, term))
            except Exception as exc:  # noqa: BLE001 — log and continue suburb loop
                print(f"  ERROR: {exc}")
            calls += 1
            time.sleep(args.sleep)

    deduped = dedupe(collected)
    out = OUTPUT / f"businesses_raw_{today()}.csv"
    # Ensure all template columns exist
    for r in deduped:
        for f in BUSINESS_FIELDS:
            r.setdefault(f, "")
    write_csv(out, deduped, BUSINESS_FIELDS)
    print(f"API calls: {calls}")
    print(f"Raw rows: {len(collected)} → deduped: {len(deduped)}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
