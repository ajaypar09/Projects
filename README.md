# Pokémon Card Price Database

This project provides a lightweight, file-based database that helps you store and search Pokémon card price information pulled from PriceCharting and TCGplayer exports.

The tooling focuses on:

* **Consistent identifiers** – every entry is keyed by the card's serial number and name so that you can easily differentiate between variants.
* **Source-aware pricing** – each card can keep separate values for PriceCharting and TCGplayer, alongside historical sales snapshots.
* **Quick lookups** – search the catalog by serial number or by (partial) card name and receive an estimated market value based on the tracked sources.

## Getting started

1. Create a virtual environment (optional) and install the project in editable mode if you want command aliases:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

2. Initialize a database (defaults to `pokemon_cards.db` in the project root):

   ```bash
   python main.py init-db
   ```

3. Import pricing data from a JSON export (see [`data/sample_cards.json`](data/sample_cards.json) for the expected structure):

   ```bash
   python main.py import-json data/sample_cards.json
   ```

4. Search the database by serial number or card name:

   ```bash
   python main.py search --serial-number "SM115"
   python main.py search --name "charizard"
   python main.py search --serial-number "151-199"
   ```

5. Quickly look up a card by both serial number and name to view its blended estimate and most recent sales (defaults to the five latest records):

   ```bash
   python main.py lookup --serial-number "151-199" --name "Charizard ex"
   ```

## Data model

The application stores data in a local SQLite database with three tables:

* `cards` – base card metadata (serial number, name, set, rarity).
* `prices` – latest price snapshots for each data source and price type.
* `sales` – normalized records of recent sales that back the price information.

The `search` command combines price snapshots from PriceCharting and TCGplayer and computes a blended estimated value (simple average) whenever multiple price points are available.

## Import format

The importer accepts JSON arrays of card objects with the following shape:

```json
{
  "serial_number": "SM115",
  "name": "Charizard-GX",
  "set_name": "Hidden Fates",
  "rarity": "Ultra Rare",
  "pricecharting": {
    "price": 150.0,
    "last_updated": "2024-01-12",
    "recent_sales": [
      { "date": "2024-01-10", "price": 148.0, "source": "PriceCharting" }
    ]
  },
  "tcgplayer": {
    "market_price": 155.0,
    "listed_median": 160.0,
    "last_updated": "2024-01-11",
    "recent_sales": [
      { "date": "2024-01-09", "price": 152.5, "source": "TCGplayer" }
    ]
  }
}
```

Only the fields relevant to your export need to be included. The importer ignores missing keys and deduplicates existing data when re-run.

## Development

The codebase is intentionally dependency-light and sticks to the Python standard library. Unit tests are not bundled, but you can extend the modules under `pokemon_cards/` and invoke them directly from scripts or notebooks.

