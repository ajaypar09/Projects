"""Command line interface for estimating Pokémon card prices."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List

from .estimator import CardEstimate, CardQuery, estimate_prices


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Estimate Pokémon card prices using online market data."
    )
    parser.add_argument(
        "cards",
        nargs="*",
        help=(
            "Card descriptions in the form 'Name' or 'Name#Number'. "
            "If omitted, --input must be provided."
        ),
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Path to a text file containing one card per line (Name or Name#Number).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output the price summaries as JSON instead of a table.",
    )
    return parser.parse_args()


def load_queries(args: argparse.Namespace) -> List[CardQuery]:
    entries: List[str] = []
    if args.cards:
        entries.extend(args.cards)
    if args.input:
        entries.extend([line.strip() for line in args.input.read_text().splitlines() if line.strip()])
    if not entries:
        raise SystemExit("Provide card names via positional arguments or --input.")

    return [parse_card_entry(entry) for entry in entries]


def parse_card_entry(entry: str) -> CardQuery:
    if "#" in entry:
        name, number = entry.split("#", maxsplit=1)
        return CardQuery(name=name.strip(), number=number.strip())
    return CardQuery(name=entry.strip())


def format_estimates(estimates: Iterable[CardEstimate], as_json: bool) -> str:
    if as_json:
        return json.dumps([estimate.summary() for estimate in estimates], indent=2)

    headers = ["Query", "Median Price", "TCGplayer Matches", "PriceCharting Match"]
    rows = []
    for estimate in estimates:
        summary = estimate.summary()
        price_display = (
            f"${summary['median_price']:.2f}" if summary["median_price"] is not None else "-"
        )
        rows.append(
            [
                summary["query"],
                price_display,
                str(summary["tcgplayer_products"]),
                "Yes" if summary["pricecharting_found"] else "No",
            ]
        )

    column_widths = [max(len(str(row[idx])) for row in rows + [headers]) for idx in range(len(headers))]
    divider = "+".join("-" * (width + 2) for width in column_widths)

    lines = [" | ".join(header.ljust(width) for header, width in zip(headers, column_widths))]
    lines.append(divider)
    for row in rows:
        lines.append(" | ".join(value.ljust(width) for value, width in zip(row, column_widths)))
    return "\n".join(lines)


def main() -> None:
    args = parse_arguments()
    queries = load_queries(args)
    estimates = estimate_prices(queries)
    output = format_estimates(estimates, as_json=args.json)
    print(output)


if __name__ == "__main__":
    main()
