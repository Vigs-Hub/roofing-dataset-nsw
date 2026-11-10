"""Shared helpers for the roofing dataset pipeline."""

from __future__ import annotations

import csv
import os
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "areas.yaml"
SUBURB_LIST = ROOT / "data" / "processed" / "suburb_list.csv"
OUTPUT = ROOT / "output"
TEMPLATES = ROOT / "sheet_templates"


def load_env() -> None:
    load_dotenv(ROOT / ".env")


def today() -> str:
    return date.today().isoformat()


def load_areas() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_suburbs(main_only: bool = False) -> list[dict[str, str]]:
    if not SUBURB_LIST.exists():
        raise FileNotFoundError(
            f"Missing {SUBURB_LIST}. Run: python scripts/build_suburb_list.py"
        )
    with SUBURB_LIST.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if main_only:
        rows = [r for r in rows if r.get("is_main_suburb") == "yes"]
    return rows


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)
    return path


def env_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing env var {name}. Copy .env.example → .env and fill it.")
    return value


def spend_cap(name: str) -> float | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    return float(raw)
