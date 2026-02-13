from unittest.mock import MagicMock

import pytest

from pokemon_price_estimator.estimator import CardQuery, estimate_prices


class DummyTCGProduct:
    def __init__(self, price_points):
        self._price_points = price_points

    def price_points(self):
        return self._price_points


class DummyPriceChartingResult:
    def __init__(self, price_points):
        self._price_points = price_points

    def price_points(self):
        return self._price_points


@pytest.fixture
def tcg_client():
    client = MagicMock()
    client.is_configured = True
    client.lookup_card.return_value = [
        DummyTCGProduct([10.0, 12.0, None]),
        DummyTCGProduct([9.5]),
    ]
    return client


@pytest.fixture
def pricecharting_client():
    client = MagicMock()
    client.is_configured = True
    client.lookup_card.return_value = DummyPriceChartingResult([11.0, None, 10.5])
    return client


def test_estimate_prices_combines_sources(tcg_client, pricecharting_client):
    estimates = estimate_prices(
        [CardQuery(name="Pikachu", number="58")],
        tcgplayer_client=tcg_client,
        pricecharting_client=pricecharting_client,
    )

    assert len(estimates) == 1
    summary = estimates[0].summary()
    assert summary["median_price"] == pytest.approx(10.5, abs=0.01)
    assert summary["tcgplayer_products"] == 2
    assert summary["pricecharting_found"] is True


def test_missing_credentials_are_handled_gracefully(tcg_client):
    pricecharting = MagicMock()
    pricecharting.is_configured = False

    estimates = estimate_prices(
        [CardQuery(name="Charizard")],
        tcgplayer_client=tcg_client,
        pricecharting_client=pricecharting,
    )

    summary = estimates[0].summary()
    assert summary["tcgplayer_products"] == 2
    assert summary["pricecharting_found"] is False
