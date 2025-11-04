"""Command-line interface for the Pokémon card price database."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from pokemon_cards.database import Database
from pokemon_cards.importer import import_cards_from_json
from pokemon_cards.search import get_card_details, lookup_card, search_cards

DEFAULT_DB_PATH = "pokemon_cards.db"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Store and search Pokémon card price data from PriceCharting and TCGplayer."
    )
    parser.add_argument(
        "--db",
        dest="db_path",
        default=DEFAULT_DB_PATH,
        help=f"Path to the SQLite database file (default: {DEFAULT_DB_PATH})",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="Initialize the SQLite database")

    import_parser = subparsers.add_parser(
        "import-json", help="Import card data from a JSON export"
    )
    import_parser.add_argument("json_file", help="Path to the JSON file to import")

    search_parser = subparsers.add_parser("search", help="Search for cards in the database")
    search_parser.add_argument("--serial-number", dest="serial_number", help="Serial number filter")
    search_parser.add_argument("--name", dest="name", help="Card name filter")
    search_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results to show (default: 10)",
    )

    detail_parser = subparsers.add_parser("show", help="Show details for a specific card ID")
    detail_parser.add_argument("card_id", type=int, help="Database ID of the card")

    lookup_parser = subparsers.add_parser(
        "lookup",
        help="Quickly look up a card by serial number and name to view recent sales",
    )
    lookup_parser.add_argument("--serial-number", required=True, help="Exact serial number of the card")
    lookup_parser.add_argument("--name", required=True, help="Exact card name")
    lookup_parser.add_argument(
        "--sales-limit",
        type=int,
        default=5,
        help="Number of recent sales to display (default: 5)",
    )

    return parser


def _print_price_sources(prices: dict[str, dict[str, dict[str, Any]]]) -> None:
    for source, values in prices.items():
        print(f"  {source}:")
        for price_type, details in values.items():
            price = details["price"]
            last_updated = details.get("last_updated") or "n/a"
            print(f"    {price_type}: ${price:.2f} (updated {last_updated})")


def _print_sales(sales: dict[str, list[dict[str, Any]]]) -> None:
    if not sales:
        print("  No recent sales recorded.")
        return
    for source, records in sales.items():
        print(f"  {source} sales:")
        for sale in records:
            date = sale.get("date") or "unknown date"
            price = sale.get("price")
            condition = sale.get("condition")
            listing_url = sale.get("listing_url")
            extra = f" | Condition: {condition}" if condition else ""
            extra += f" | Listing: {listing_url}" if listing_url else ""
            print(f"    {date}: ${price:.2f}{extra}")


def _print_recent_sales(sales: list[dict[str, Any]]) -> None:
    if not sales:
        print("No recent sales found.")
        return
    for sale in sales:
        date = sale.get("date") or "unknown date"
        price = sale.get("price")
        source = sale.get("source") or "Unknown source"
        condition = sale.get("condition")
        listing_url = sale.get("listing_url")
        extra = f" | Condition: {condition}" if condition else ""
        extra += f" | Listing: {listing_url}" if listing_url else ""
        print(f"- {date}: ${price:.2f} ({source}{extra})")


def app(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    db = Database(args.db_path)

    if args.command == "init-db":
        db.initialize()
        print(f"Database initialized at {Path(args.db_path).resolve()}")
        return

    if args.command == "import-json":
        db.initialize()
        count = import_cards_from_json(db, args.json_file)
        print(f"Imported {count} cards from {args.json_file}")
        return

    if args.command == "search":
        db.initialize()
        results = search_cards(
            db,
            serial_number=args.serial_number,
            name=args.name,
            limit=args.limit,
        )
        if not results:
            print("No matching cards found.")
            return
        for entry in results:
            card = entry["card"]
            est = entry.get("estimated_value")
            header = f"{card.name} ({card.serial_number})"
            if card.set_name:
                header += f" – {card.set_name}"
            if card.rarity:
                header += f" [{card.rarity}]"
            print(header)
            if est is not None:
                print(f"  Estimated value: ${est:.2f}")
            else:
                print("  Estimated value: n/a")
            _print_price_sources(entry["prices"])
            print()
        return

    if args.command == "show":
        db.initialize()
        details = get_card_details(db, args.card_id)
        if details is None:
            print(f"Card with ID {args.card_id} was not found.")
            return
        card = details["card"]
        print(f"{card.name} ({card.serial_number})")
        if card.set_name:
            print(f"Set: {card.set_name}")
        if card.rarity:
            print(f"Rarity: {card.rarity}")
        est = details.get("estimated_value")
        if est is not None:
            print(f"Estimated value: ${est:.2f}")
        else:
            print("Estimated value: n/a")
        print("Prices:")
        _print_price_sources(details["prices"])
        print("Sales:")
        _print_sales(details["sales"])
        return

    if args.command == "lookup":
        db.initialize()
        summary = lookup_card(
            db,
            serial_number=args.serial_number,
            name=args.name,
            sales_limit=args.sales_limit,
        )
        if summary is None:
            print("No matching cards found.")
            return
        card = summary["card"]
        print(f"{card.name} ({card.serial_number})")
        est = summary.get("estimated_value")
        if est is not None:
            print(f"Estimated value: ${est:.2f}")
        else:
            print("Estimated value: n/a")
        print("Recent sales:")
        _print_recent_sales(summary["sales"])
        return

    parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    app()
