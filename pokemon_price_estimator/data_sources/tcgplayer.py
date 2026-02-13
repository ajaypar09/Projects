"""Client for interacting with the TCGplayer API."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests

try:
    from requests import RequestException  # type: ignore
except Exception:  # pragma: no cover - fallback when requests is stubbed
    class RequestException(Exception):
        """Fallback exception when the real requests library is unavailable."""
        pass

API_BASE = "https://api.tcgplayer.com"
POKEMON_CATEGORY_ID = 3


@dataclass
class TCGPlayerProduct:
    """Represents a catalog product returned by TCGplayer."""

    product_id: int
    name: str
    number: Optional[str]
    url: Optional[str]
    market_price: Optional[float]
    median_price: Optional[float]
    direct_low_price: Optional[float]

    def price_points(self) -> List[Optional[float]]:
        return [self.market_price, self.median_price, self.direct_low_price]


class TCGPlayerClient:
    """A minimal client for the TCGplayer REST API."""

    def __init__(
        self,
        public_key: Optional[str] = None,
        private_key: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ):
        self.public_key = public_key or os.getenv("TCGPLAYER_PUBLIC_KEY")
        self.private_key = private_key or os.getenv("TCGPLAYER_PRIVATE_KEY")
        self.session = session or requests.Session()
        self._token: Optional[str] = None
        self._token_expiry: float = 0

    @property
    def is_configured(self) -> bool:
        return bool(self.public_key and self.private_key)

    def lookup_card(self, name: str, number: Optional[str] = None) -> List[TCGPlayerProduct]:
        if not self.is_configured:
            return []

        try:
            access_token = self._authenticate()
        except RequestException:
            return []

        headers = {"Authorization": f"bearer {access_token}"}

        params: Dict[str, str] = {
            "categoryId": str(POKEMON_CATEGORY_ID),
            "productName": name,
            "getExtendedFields": "true",
            "limit": "10",
        }
        if number:
            params["productNumber"] = number

        try:
            response = self.session.get(
                f"{API_BASE}/catalog/products",
                params=params,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
        except RequestException:
            return []

        data = response.json()
        results: List[TCGPlayerProduct] = []

        for product in data.get("results", []):
            product_id = product.get("productId")
            built = self._build_product(product_id, product, headers=headers)
            if built is not None:
                results.append(built)

        return results

    def _build_product(
        self,
        product_id: int,
        product_payload: Dict[str, object],
        headers: Dict[str, str],
    ) -> Optional[TCGPlayerProduct]:
        if not product_id:
            return None

        extended_fields = product_payload.get("extendedData") or []
        card_number = None
        for field in extended_fields:
            if field.get("name", "").lower() == "number":
                card_number = field.get("value")
                break

        market_price_data = self._fetch_market_price(product_id, headers=headers)
        url = product_payload.get("url")

        return TCGPlayerProduct(
            product_id=product_id,
            name=product_payload.get("name", ""),
            number=card_number,
            url=url,
            market_price=market_price_data.get("marketPrice"),
            median_price=market_price_data.get("midPrice"),
            direct_low_price=market_price_data.get("directLowPrice"),
        )

    def _fetch_market_price(self, product_id: int, headers: Dict[str, str]) -> Dict[str, Optional[float]]:
        try:
            response = self.session.get(
                f"{API_BASE}/pricing/product/{product_id}", headers=headers, timeout=10
            )
            response.raise_for_status()
        except RequestException:
            return {}

        data = response.json()
        prices = data.get("results") or []
        if not prices:
            return {}
        first = prices[0]
        return {
            "marketPrice": _parse_price(first.get("marketPrice")),
            "midPrice": _parse_price(first.get("midPrice")),
            "directLowPrice": _parse_price(first.get("directLowPrice")),
        }

    def _authenticate(self) -> str:
        if self._token and time.time() < self._token_expiry:
            return self._token

        try:
            response = self.session.post(
                f"{API_BASE}/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.public_key,
                    "client_secret": self.private_key,
                },
                headers={"Accept": "application/json"},
                timeout=10,
            )
            response.raise_for_status()
        except RequestException as exc:
            raise exc
        data = response.json()
        self._token = data["access_token"]
        expires_in = int(data.get("expires_in", 86400))
        self._token_expiry = time.time() + expires_in - 60
        return self._token


def _parse_price(value: Optional[float]) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


__all__ = ["TCGPlayerClient", "TCGPlayerProduct"]
