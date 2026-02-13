# Pokémon Card Price Estimator

This project provides a simple command line interface (CLI) and Python package for
estimating Pokémon card prices using publicly available sales data from
[TCGplayer](https://www.tcgplayer.com/) and [PriceCharting](https://www.pricecharting.com/).
The tool accepts card names (and optionally collector numbers) and combines price
information from both services to produce a quick estimate of recent market value.

> **Note:** The script does not store or redistribute any pricing data. It simply
> requests publicly available information from the official APIs. Both services
> require API tokens and may enforce rate limits. Consult their documentation for
> usage policies.

## Features

- Search TCGplayer and PriceCharting for Pokémon cards by name or collector number.
- Aggregate multiple price points (market price, median price, direct low price,
  loose price, complete-in-box price, and new price) into a single median estimate.
- Provide either a human-friendly table or JSON output that can be consumed by other tools.

## Requirements

- Python 3.9+
- API credentials:
  - **TCGplayer**: Obtain a *public key* and *private key* from the
    [TCGplayer developer portal](https://developer.tcgplayer.com/). Set them as
    environment variables `TCGPLAYER_PUBLIC_KEY` and `TCGPLAYER_PRIVATE_KEY`.
  - **PriceCharting**: Request an API token from
    [PriceCharting](https://www.pricecharting.com/partners). Set it as the
    environment variable `PRICECHARTING_TOKEN`.

## Installation

1. Create and activate a virtual environment (recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Export the necessary API credentials:

   ```bash
   export TCGPLAYER_PUBLIC_KEY="your-public-key"
   export TCGPLAYER_PRIVATE_KEY="your-private-key"
   export PRICECHARTING_TOKEN="your-pricecharting-token"
   ```

## Usage

### Command Line

You can provide cards directly as positional arguments using the format
`Name` or `Name#Number` (the collector number is optional but helps disambiguate
cards that share a name).

```bash
python -m pokemon_price_estimator.cli "Pikachu#58" "Charizard"
```

The output defaults to a table summarizing matches and the median estimated price:

```
Query          | Median Price | TCGplayer Matches | PriceCharting Match
--------------+--------------+-------------------+--------------------
pikachu#58     | $45.50       | 3                 | Yes
charizard      | $120.00      | 5                 | Yes
```

#### Using a File

If you have many cards, create a text file with one entry per line:

```
Pikachu#58
Charizard
Mewtwo#10
```

Then run:

```bash
python -m pokemon_price_estimator.cli --input cards.txt
```

#### JSON Output

To integrate with other software, you can request JSON output:

```bash
python -m pokemon_price_estimator.cli "Pikachu#58" --json
```

Example JSON structure:

```json
[
  {
    "query": "pikachu#58",
    "median_price": 45.5,
    "tcgplayer_products": 3,
    "pricecharting_found": true
  }
]
```

### Python Library

You can also use the estimator in your own Python scripts:

```python
from pokemon_price_estimator import CardQuery, estimate_prices

queries = [
    CardQuery(name="Pikachu", number="58"),
    CardQuery(name="Charizard"),
]

for estimate in estimate_prices(queries):
    print(estimate.summary())
```

## Development

Run the unit tests with:

```bash
pytest
```

The tests rely on mocked HTTP responses, so they do not perform live requests.

## Limitations

- Real-time pricing accuracy depends entirely on the upstream APIs.
- Network issues or expired credentials will result in partial data.
- The estimator uses a simple median of available price points; you may want to
  adjust the aggregation strategy for your particular use case.
