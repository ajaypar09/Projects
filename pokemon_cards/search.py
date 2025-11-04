"""Search and aggregation helpers for Pokémon card prices."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any, Dict, Iterable

from .database import Card, Database


def _group_prices(price_rows: Iterable[Any]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    grouped: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for row in price_rows:
        grouped[row["source"]][row["price_type"]] = {
            "price": row["price_value"],
            "last_updated": row["last_updated"],
        }
    return grouped


def _estimate_value(grouped_prices: Dict[str, Dict[str, Dict[str, Any]]]) -> float | None:
    values = [details["price"] for source in grouped_prices.values() for details in source.values()]
    if not values:
        return None
    return round(mean(values), 2)


def search_cards(
    db: Database,
    *,
    serial_number: str | None = None,
    name: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search the database for cards and include aggregated price information."""
    cards = db.search_cards(serial_number=serial_number, name_query=name, limit=limit)
    results = []
    for card in cards:
        price_rows = db.fetch_prices(card.id)
        prices = _group_prices(price_rows)
        results.append(
            {
                "card": card,
                "prices": prices,
                "estimated_value": _estimate_value(prices),
            }
        )
    return results


def get_card_details(db: Database, card_id: int) -> dict[str, Any] | None:
    """Fetch detailed information about a single card."""
    card = db.get_card(card_id)
    if card is None:
        return None

    price_rows = db.fetch_prices(card.id)
    sales_rows = db.fetch_sales(card.id)

    prices = _group_prices(price_rows)
    sales: Dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sale in sales_rows:
        sales[sale["source"]].append(
            {
                "date": sale["sale_date"],
                "price": sale["price"],
                "condition": sale["condition"],
                "listing_url": sale["listing_url"],
            }
        )

    return {
        "card": card,
        "prices": prices,
        "sales": dict(sales),
        "estimated_value": _estimate_value(prices),
    }
