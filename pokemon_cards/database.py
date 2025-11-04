"""SQLite persistence layer for the Pokémon card price database."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import os
import sqlite3
from typing import Iterable, Iterator, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY,
    serial_number TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    set_name TEXT,
    rarity TEXT
);

CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY,
    card_id INTEGER NOT NULL,
    source TEXT NOT NULL,
    price_type TEXT NOT NULL,
    price_value REAL NOT NULL,
    last_updated TEXT,
    UNIQUE(card_id, source, price_type),
    FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY,
    card_id INTEGER NOT NULL,
    source TEXT NOT NULL,
    sale_date TEXT,
    price REAL NOT NULL,
    condition TEXT,
    listing_url TEXT,
    FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE
);
"""


@dataclass(slots=True)
class Card:
    """Lightweight representation of card metadata."""

    id: int
    serial_number: str
    name: str
    set_name: Optional[str]
    rarity: Optional[str]


class Database:
    """High-level helper around the SQLite database."""

    def __init__(self, path: str = "pokemon_cards.db") -> None:
        self.path = path
        self._ensure_parent_directory()

    def _ensure_parent_directory(self) -> None:
        parent = os.path.dirname(os.path.abspath(self.path))
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def initialize(self) -> None:
        """Create tables if they do not already exist."""
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            conn.commit()

    # ------------------------------------------------------------------
    # Write helpers
    # ------------------------------------------------------------------
    def upsert_card(
        self,
        serial_number: str,
        name: str,
        set_name: Optional[str] = None,
        rarity: Optional[str] = None,
    ) -> int:
        """Insert a card or return the existing primary key."""
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO cards (serial_number, name, set_name, rarity)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(serial_number) DO UPDATE SET
                    name = excluded.name,
                    set_name = excluded.set_name,
                    rarity = excluded.rarity
                RETURNING id
                """,
                (serial_number, name, set_name, rarity),
            )
            row = cursor.fetchone()
            conn.commit()
        return int(row[0])

    def upsert_prices(
        self,
        card_id: int,
        source: str,
        price_items: dict[str, tuple[float, Optional[str]]],
    ) -> None:
        """Upsert a batch of price entries for a card.

        Args:
            card_id: Card primary key.
            source: Name of the price source (e.g. "PriceCharting").
            price_items: Mapping of price type to (value, last_updated).
        """
        with self.connect() as conn:
            for price_type, (value, last_updated) in price_items.items():
                conn.execute(
                    """
                    INSERT INTO prices (card_id, source, price_type, price_value, last_updated)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(card_id, source, price_type) DO UPDATE SET
                        price_value = excluded.price_value,
                        last_updated = excluded.last_updated
                    """,
                    (card_id, source, price_type, value, last_updated),
                )
            conn.commit()

    def replace_sales(
        self,
        card_id: int,
        source: str,
        sales: Iterable[dict],
    ) -> None:
        """Replace the sales history for a card/source pair."""
        sales = list(sales)
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM sales WHERE card_id = ? AND source = ?",
                (card_id, source),
            )
            conn.executemany(
                """
                INSERT INTO sales (card_id, source, sale_date, price, condition, listing_url)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        card_id,
                        source,
                        sale.get("date"),
                        float(sale.get("price", 0.0)),
                        sale.get("condition"),
                        sale.get("listing_url"),
                    )
                    for sale in sales
                ],
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------
    def search_cards(
        self,
        *,
        serial_number: Optional[str] = None,
        name_query: Optional[str] = None,
        limit: int = 25,
    ) -> list[Card]:
        """Search for cards by serial number or name."""
        conditions: list[str] = []
        params: list[str] = []

        if serial_number:
            conditions.append("serial_number LIKE ?")
            params.append(f"%{serial_number}%")
        if name_query:
            conditions.append("LOWER(name) LIKE ?")
            params.append(f"%{name_query.lower()}%")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with self.connect() as conn:
            cursor = conn.execute(
                f"""
                SELECT id, serial_number, name, set_name, rarity
                FROM cards
                WHERE {where_clause}
                ORDER BY name ASC
                LIMIT ?
                """,
                (*params, limit),
            )
            rows = cursor.fetchall()

        return [
            Card(
                id=row["id"],
                serial_number=row["serial_number"],
                name=row["name"],
                set_name=row["set_name"],
                rarity=row["rarity"],
            )
            for row in rows
        ]

    def fetch_prices(self, card_id: int) -> list[sqlite3.Row]:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                SELECT source, price_type, price_value, last_updated
                FROM prices
                WHERE card_id = ?
                ORDER BY source, price_type
                """,
                (card_id,),
            )
            return cursor.fetchall()

    def fetch_sales(self, card_id: int) -> list[sqlite3.Row]:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                SELECT source, sale_date, price, condition, listing_url
                FROM sales
                WHERE card_id = ?
                ORDER BY (sale_date IS NULL), sale_date DESC, price DESC
                LIMIT 20
                """,
                (card_id,),
            )
            return cursor.fetchall()

    def get_card(self, card_id: int) -> Optional[Card]:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                SELECT id, serial_number, name, set_name, rarity
                FROM cards
                WHERE id = ?
                """,
                (card_id,),
            )
            row = cursor.fetchone()

        if row is None:
            return None
        return Card(
            id=row["id"],
            serial_number=row["serial_number"],
            name=row["name"],
            set_name=row["set_name"],
            rarity=row["rarity"],
        )
