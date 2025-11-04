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
    serial_number: str | None = None,
    name: str | None = None,
    sales_limit: int = 5,
) -> dict[str, Any] | None:
    """Find a card by identifiers and provide a quick summary."""

    if not serial_number and not name:
        return None

    candidates = db.search_cards(serial_number=serial_number, name_query=name, limit=50)
    if not candidates:
        return None

    serial_lookup = serial_number.lower() if serial_number else None
    name_lookup = name.lower() if name else None

    def _exact_both(card: Card) -> bool:
        return (
            (serial_lookup is None or card.serial_number.lower() == serial_lookup)
            and (name_lookup is None or card.name.lower() == name_lookup)
        )

    def _exact_serial(card: Card) -> bool:
        return serial_lookup is not None and card.serial_number.lower() == serial_lookup

    def _exact_name(card: Card) -> bool:
        return name_lookup is not None and card.name.lower() == name_lookup

    def _partial_serial(card: Card) -> bool:
        return serial_lookup is not None and serial_lookup in card.serial_number.lower()

    def _partial_name(card: Card) -> bool:
        return name_lookup is not None and name_lookup in card.name.lower()

    card = next((candidate for candidate in candidates if _exact_both(candidate)), None)
    if card is None:
        card = next((candidate for candidate in candidates if _exact_serial(candidate)), None)
    if card is None:
        card = next((candidate for candidate in candidates if _exact_name(candidate)), None)
    if card is None:
        card = next((candidate for candidate in candidates if _partial_serial(candidate)), None)
    if card is None:
        card = next((candidate for candidate in candidates if _partial_name(candidate)), None)
    if card is None:
        card = candidates[0]

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
