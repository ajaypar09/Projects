"""Client for interacting with the PriceCharting API."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests

try:
    from requests import RequestException  # type: ignore
except Exception:  # pragma: no cover - fallback when requests is stubbed
    class RequestException(Exception):
        """Fallback exception when the real requests library is unavailable."""
        pass

API_BASE = "https://www.pricecharting.com/api"


@dataclass
class PriceChartingResult:
    """Relevant fields returned by the PriceCharting API."""

    product_name: str
    console_name: Optional[str]
    price_loose: Optional[float]
    price_cib: Optional[float]
    price_new: Optional[float]
    url: Optional[str]

    def price_points(self) -> List[Optional[float]]:
        return [self.price_loose, self.price_cib, self.price_new]


class PriceChartingClient:
    """Thin wrapper around the PriceCharting REST API."""

    def __init__(self, token: Optional[str] = None, session: Optional[requests.Session] = None):
        self.token = token or os.getenv("PRICECHARTING_TOKEN")
        self.session = session or requests.Session()

    @property
    def is_configured(self) -> bool:
        return bool(self.token)

    def lookup_card(self, name: str, number: Optional[str] = None) -> Optional[PriceChartingResult]:
        if not self.is_configured:
            return None

        query = name
        if number:
            query = f"{name} {number}"

        params: Dict[str, str] = {
            "t": self.token,
            "q": query,
            "type": "pokemon-card",
        }

        try:
            response = self.session.get(f"{API_BASE}/products", params=params, timeout=10)
            response.raise_for_status()
        except RequestException:
            return None

        data = response.json()
        products = data.get("products") or []
        if not products:
            return None

        first_match = products[0]
        return PriceChartingResult(
            product_name=first_match.get("product-name"),
            console_name=first_match.get("console-name"),
            price_loose=_parse_price(first_match.get("loose-price")),
            price_cib=_parse_price(first_match.get("cib-price")),
            price_new=_parse_price(first_match.get("new-price")),
            url=first_match.get("url"),
        )


def _parse_price(value: Optional[str]) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


__all__ = ["PriceChartingClient", "PriceChartingResult"]
