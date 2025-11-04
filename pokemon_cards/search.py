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


def lookup_card(
    db: Database,
    *,
    serial_number: str,
    name: str,
    sales_limit: int = 5,
) -> dict[str, Any] | None:
    """Find a card by identifiers and provide a quick summary."""

    if not serial_number and not name:
        return None

    candidates = db.search_cards(serial_number=serial_number, name_query=name, limit=50)
    if not candidates:
        return None

    serial_lookup = serial_number.lower()
    name_lookup = name.lower()

    def _match(card: Card) -> bool:
        return card.serial_number.lower() == serial_lookup and card.name.lower() == name_lookup

    def _serial_match(card: Card) -> bool:
        return card.serial_number.lower() == serial_lookup

    card = next((candidate for candidate in candidates if _match(candidate)), None)
    if card is None:
        card = next((candidate for candidate in candidates if _serial_match(candidate)), candidates[0])

    price_rows = db.fetch_prices(card.id)
    sales_rows = db.fetch_sales(card.id, limit=max(1, sales_limit))

    prices = _group_prices(price_rows)
    estimated_value = _estimate_value(prices)
    sales = [
        {
            "source": sale["source"],
            "date": sale["sale_date"],
            "price": sale["price"],
            "condition": sale["condition"],
            "listing_url": sale["listing_url"],
        }
        for sale in sales_rows
    ]

    return {
        "card": card,
        "prices": prices,
        "sales": sales,
        "estimated_value": estimated_value,
    }
