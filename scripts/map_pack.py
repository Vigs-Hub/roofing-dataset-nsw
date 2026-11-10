#!/usr/bin/env python3
"""Step 6 — Map pack: top 3 'roofer [suburb]' for each main suburb (monthly re-run)."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from common import OUTPUT, load_env, load_suburbs, today, write_csv
from search_businesses import dataforseo_maps_live, places_text_search

FIELDS = [
    "suburb",
    "lga",
    "rank",
    "name",
    "rating",
    "review_count",
    "place_id",
    "maps_url",
    "search_query",
    "source_provider",
    "source_link",
    "date_checked",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["dataforseo", "places"], default="dataforseo")
    parser.add_argument("--sleep", type=float, default=1.0)
    args = parser.parse_args()
    load_env()

    suburbs = load_suburbs(main_only=True)
    rows = []
    for s in suburbs:
        suburb, lga = s["suburb"], s["lga"]
        query = f"roofer {suburb}"
        print(f"Map pack: {query}")
        try:
            if args.provider == "dataforseo":
                items = dataforseo_maps_live(query, f"{suburb},New South Wales,Australia")
                provider = "dataforseo_google_maps"
                for i, item in enumerate(items[:3], start=1):
                    rating = item.get("rating", {})
                    rating_val = rating.get("value") if isinstance(rating, dict) else item.get("rating")
                    reviews = rating.get("votes_count") if isinstance(rating, dict) else item.get("reviews_count")
                    place_id = item.get("place_id") or ""
                    maps_url = item.get("url") or ""
                    rows.append(
                        {
                            "suburb": suburb,
                            "lga": lga,
                            "rank": i,
                            "name": item.get("title") or item.get("name") or "",
                            "rating": rating_val or "",
                            "review_count": reviews or "",
                            "place_id": place_id,
                            "maps_url": maps_url,
                            "search_query": query,
                            "source_provider": provider,
                            "source_link": maps_url or "https://api.dataforseo.com/v3/business_data/google/maps/search/live",
                            "date_checked": today(),
                        }
                    )
            else:
                items = places_text_search(query)
                for i, item in enumerate(items[:3], start=1):
                    place_id = item.get("id") or ""
                    maps_url = item.get("googleMapsUri") or ""
                    rows.append(
                        {
                            "suburb": suburb,
                            "lga": lga,
                            "rank": i,
                            "name": (item.get("displayName") or {}).get("text") or "",
                            "rating": item.get("rating") or "",
                            "review_count": item.get("userRatingCount") or "",
                            "place_id": place_id,
                            "maps_url": maps_url,
                            "search_query": query,
                            "source_provider": "google_places_text_search",
                            "source_link": maps_url or "https://developers.google.com/maps/documentation/places/web-service/text-search",
                            "date_checked": today(),
                        }
                    )
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR: {exc}")
            rows.append(
                {
                    "suburb": suburb,
                    "lga": lga,
                    "rank": "",
                    "name": "",
                    "rating": "",
                    "review_count": "",
                    "place_id": "",
                    "maps_url": "",
                    "search_query": query,
                    "source_provider": args.provider,
                    "source_link": "",
                    "date_checked": today(),
                }
            )
        time.sleep(args.sleep)

    out = OUTPUT / f"map_pack_{today()}.csv"
    write_csv(out, rows, FIELDS)
    print(f"Wrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
