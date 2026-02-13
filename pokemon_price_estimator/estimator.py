"""Aggregate Pokémon card price information from multiple sources."""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from .data_sources.pricecharting import PriceChartingClient, PriceChartingResult
from .data_sources.tcgplayer import TCGPlayerClient, TCGPlayerProduct


@dataclass
class CardQuery:
    """User supplied card lookup information."""

    name: str
    number: Optional[str] = None

    def normalized(self) -> str:
        """Return a normalized string for comparisons."""
        if self.number:
            return f"{self.name.strip()}#{self.number.strip()}".lower()
        return self.name.strip().lower()


@dataclass
class CardEstimate:
    """Aggregate pricing details for a card."""

    query: CardQuery
    tcgplayer_matches: List[TCGPlayerProduct] = field(default_factory=list)
    pricecharting_match: Optional[PriceChartingResult] = None

    def available_prices(self) -> List[float]:
        prices: List[float] = []
        for product in self.tcgplayer_matches:
            prices.extend(product.price_points())
        if self.pricecharting_match:
            prices.extend(self.pricecharting_match.price_points())
        return [price for price in prices if price is not None]

    def median_price(self) -> Optional[float]:
        prices = self.available_prices()
        if not prices:
            return None
        return round(statistics.median(prices), 2)

    def summary(self) -> Dict[str, Optional[float]]:
        return {
            "query": self.query.normalized(),
            "median_price": self.median_price(),
            "tcgplayer_products": len(self.tcgplayer_matches),
            "pricecharting_found": bool(self.pricecharting_match),
        }


def estimate_prices(
    queries: Iterable[CardQuery],
    tcgplayer_client: Optional[TCGPlayerClient] = None,
    pricecharting_client: Optional[PriceChartingClient] = None,
) -> List[CardEstimate]:
    """Return pricing data for the provided queries.

    Missing credentials for an individual provider will result in that provider
    being skipped rather than the entire estimation failing.
    """

    tcgplayer_client = tcgplayer_client or TCGPlayerClient()
    pricecharting_client = pricecharting_client or PriceChartingClient()

    estimates: List[CardEstimate] = []

    for query in queries:
        estimate = CardEstimate(query=query)

        tcgplayer_matches: List[TCGPlayerProduct] = []
        if tcgplayer_client.is_configured:
            tcgplayer_matches = tcgplayer_client.lookup_card(query.name, query.number)
        estimate.tcgplayer_matches = tcgplayer_matches

        pricecharting_result: Optional[PriceChartingResult] = None
        if pricecharting_client.is_configured:
            pricecharting_result = pricecharting_client.lookup_card(query.name, query.number)
        estimate.pricecharting_match = pricecharting_result

        estimates.append(estimate)

    return estimates


__all__ = [
    "CardQuery",
    "CardEstimate",
    "estimate_prices",
]
