"""Data import utilities for the Pokémon card price database."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .database import Database

PRICECHARTING_PRICE_FIELDS = {
    "price": "market_price",
    "loose_price": "loose_price",
    "cib_price": "complete_price",
    "new_price": "sealed_price",
}

TCGPLAYER_PRICE_FIELDS = {
    "market_price": "market_price",
    "listed_median": "listed_median",
    "high_price": "high_price",
    "low_price": "low_price",
    "direct_low": "direct_low",
}


def _normalize_price_items(
    source_payload: dict[str, Any],
    field_map: dict[str, str],
    *,
    default_last_updated: str | None = None,
) -> dict[str, tuple[float, str | None]]:
    """Convert raw payload fields into `(price_type, (value, last_updated))`."""
    price_items: dict[str, tuple[float, str | None]] = {}
    last_updated = source_payload.get("last_updated", default_last_updated)
    for raw_key, normalized in field_map.items():
        if raw_key in source_payload and source_payload[raw_key] is not None:
            price_items[normalized] = (float(source_payload[raw_key]), last_updated)
    return price_items


def import_cards_from_json(db: Database, json_file: str | Path) -> int:
    """Load cards from a JSON file into the database.

    Args:
        db: Database instance.
        json_file: Path to the JSON file containing card entries.

    Returns:
        Number of cards processed.
    """
    path = Path(json_file)
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, list):
        raise ValueError("Expected the JSON payload to be a list of card entries")

    processed = 0
    for entry in payload:
        if not isinstance(entry, dict):
            continue

        serial_number = entry.get("serial_number")
        name = entry.get("name")
        if not serial_number or not name:
            raise ValueError("Each card entry must include 'serial_number' and 'name'")

        card_id = db.upsert_card(
            serial_number=serial_number,
            name=name,
            set_name=entry.get("set_name"),
            rarity=entry.get("rarity"),
        )

        pricecharting_payload = entry.get("pricecharting") or {}
        tcgplayer_payload = entry.get("tcgplayer") or {}

        pricecharting_prices = _normalize_price_items(
            pricecharting_payload, PRICECHARTING_PRICE_FIELDS
        )
        if pricecharting_prices:
            db.upsert_prices(card_id, "PriceCharting", pricecharting_prices)

        tcgplayer_prices = _normalize_price_items(tcgplayer_payload, TCGPLAYER_PRICE_FIELDS)
        if tcgplayer_prices:
            db.upsert_prices(card_id, "TCGplayer", tcgplayer_prices)

        recent_sales_pc = pricecharting_payload.get("recent_sales") or []
        if recent_sales_pc:
            db.replace_sales(card_id, "PriceCharting", recent_sales_pc)

        recent_sales_tcg = tcgplayer_payload.get("recent_sales") or []
        if recent_sales_tcg:
            db.replace_sales(card_id, "TCGplayer", recent_sales_tcg)

        processed += 1

    return processed
