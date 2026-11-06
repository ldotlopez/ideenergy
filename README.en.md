# ideenergy

[🇪🇸 Español](https://github.com/ldotlopez/ideenergy/blob/main/README.md) · 🇬🇧 English

Programmatic access to consumer electricity data from [i-DE](https://www.i-de.es/) (Iberdrola's Spanish distribution company).

<!-- Code and releases -->

[![PyPI](https://img.shields.io/pypi/v/ideenergy?logo=pypi&logoColor=white)](https://pypi.org/project/ideenergy/)
[![Python](https://img.shields.io/pypi/pyversions/ideenergy?logo=python&logoColor=white)](https://pypi.org/project/ideenergy/)
[![Release](https://img.shields.io/github/v/release/ldotlopez/ideenergy?include_prereleases&logo=github)](https://github.com/ldotlopez/ideenergy/releases)
[![License](https://img.shields.io/github/license/ldotlopez/ideenergy)](https://github.com/ldotlopez/ideenergy/blob/main/LICENSE)

<!-- Workflows -->

[![CI](https://img.shields.io/github/actions/workflow/status/ldotlopez/ideenergy/ci.yml?branch=main&label=CI&logo=githubactions&logoColor=white)](https://github.com/ldotlopez/ideenergy/actions/workflows/ci.yml)
[![Release workflow](https://img.shields.io/github/actions/workflow/status/ldotlopez/ideenergy/release.yml?label=release&logo=githubactions&logoColor=white)](https://github.com/ldotlopez/ideenergy/actions/workflows/release.yml)

<!-- Sponsors -->

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-zepolson-FFDD00?logo=buymeacoffee&logoColor=black)](https://www.buymeacoffee.com/zepolson)

> **Disclaimer:** unofficial project. Not affiliated with, endorsed or sponsored by Iberdrola or i-DE.
> It relies on the private API behind i-DE's website/app, which may change or break without notice.

## ⚠️ Before you start: the API is very restrictive

The i-DE API is heavily rate-limited and **abusive usage can get your account locked**.

- Make as few calls as possible; no loops or aggressive retries.
- Reuse a single session (one `login`) for all your queries.
- `get_measure()` and `get_in_progress_consumption()` query the ICP (meter) and can take up to a minute.
- For development and testing use `MockClient` (see below) instead of the real API.

## Installation

Requires Python 3.11 or later.

```bash
pip install ideenergy
# or with uv
uv add ideenergy
```

## Command line

```bash
export I_DE_ENERGY_USERNAME="your-username"
export I_DE_ENERGY_PASSWORD="your-password"   # a .env file works too

ideenergy --list-contracts
ideenergy --get-measure
ideenergy --get-historical-consumption --start 2026-01-01 --end 2026-01-07
```

Main options: `--contract`, `--list-contracts`, `--get-measure`, `--get-historical-consumption`,
`--get-historical-generation`, `--get-historical-power-demand`, `--get-in-progress-consumption`,
`--start` / `--end` (ISO 8601, last 7 days by default). `-u/--username` and `-p/--password` are also accepted.

> `--trace-http-requests` is for debugging only: it dumps all traffic, **including your password and session cookies**.
> `--check-auth-validity` runs for hours and logs in repeatedly: don't use it against the real API unless you know what you are doing.

## Quickstart

```python
import asyncio
import aiohttp
import ideenergy


async def main():
    async with aiohttp.ClientSession() as session:
        client = ideenergy.Client(
            session=session,
            username="your-username",
            password="your-password",
        )

        # If you have several contracts, pick one
        # contracts = await client.get_contracts()
        # await client.select_contract(contracts[0]["codContrato"])

        # Current meter reading (accumulated kWh and instant kW)
        measure = await client.get_measure()
        print(measure.accumulate, measure.instant)

        # Historical consumption (last 7 days by default)
        history = await client.get_historical_consumption()
        for period in history.periods:
            print(period.start, period.end, period.value)


asyncio.run(main())
```

Login happens automatically on the first call and the session renews itself.

### Available methods

| Method | Description |
|---|---|
| `get_contracts()` / `select_contract(id)` | List and select a contract |
| `get_contract_details()` | Details of the selected contract |
| `get_measure()` | Current meter reading (`Measure`) |
| `get_historical_consumption(start, end)` | Historical consumption (`HistoricalConsumption`) |
| `get_in_progress_consumption()` | Consumption of the ongoing period |
| `get_historical_generation(start, end)` | Historical generation (self-consumption) |
| `get_historical_power_demand()` | Power demand (last year) |
| `is_icp_ready()` | Check whether the ICP is available |

Errors: `ClientError` and subclasses (`RequestFailedError`, `CommandError`, `InvalidData`, `InvalidContractError`, `UserExpiredError`).

## Developing without hitting the real API

`MockClient` mimics the client using recorded data, no network involved:

```python
client = ideenergy.MockClient(session=None, username="x", password="y")
```

Tests (offline):

```bash
uv sync
uv run python -m unittest discover tests
```

## Useful links

- [Related Home-Assistant component](https://github.com/ldotlopez/ha-ideenergy)
- [Documentation about other distributors](https://www.genbeta.com/web/como-saber-consumo-electrico-tiempo-real-casa) (Spanish)

## Home Assistant

If you want your consumption in Home Assistant, use the
[ha-ideenergy](https://github.com/ldotlopez/ha-ideenergy) integration, built on top of this library.

## License

[GPL-3.0-only](https://github.com/ldotlopez/ideenergy/blob/main/LICENSE)
