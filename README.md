# GlobalOmnium Python API

[![GitHub Release](https://img.shields.io/github/v/release/carlos-48/globalomnium)](https://github.com/carlos-48/globalomnium/releases)
[![CodeQL](https://github.com/carlos-48/globalomnium/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/carlos-48/globalomnium/actions/workflows/codeql-analysis.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

Programmatic access to water consumption data from [Global Omnium](https://www.globalomnium.com/), the Spanish water distributor management group.

## 🚀 Features

- **Multi-entity Support**: Compatible with various Global Omnium management companies (e.g., Emivasa, Aguas de Valencia, and others).
- **Modern Python**: Fully updated for Python 3.11+ with strong type hinting and asynchronous support (`asyncio` / `aiohttp`).
- **Consumption Data**: Retrieve current readings and hourly/historical consumption.
- **Reliable**: Robust parsing and session management designed for stable Home Assistant integrations.

## 📦 Installation

### For Development (Editable Mode)
If you are contributing or developing a component based on this library, install it in editable mode:

```bash
git clone https://github.com/carlos-48/globalomnium.git
cd globalomnium
pip install -e .
```

### For Production
```bash
pip install globalomnium
```

## 🛠️ Quick Start

```python
import asyncio
import aiohttp
from globalomnium.client import Client

async def main():
    async with aiohttp.ClientSession() as session:
        # base_url is mandatory as it depends on the management company of your municipality
        client = Client(
            session=session,
            username="your_username",
            password="your_password",
            base_url="https://www.emivasa.es/VirtualOffice" 
        )
        
        # Example: Get current measure
        measure = await client.get_measure()
        print(f"Current Reading: {measure.accumulate} m³")
        print(f"Instant Consumption: {measure.instant} l/h")

asyncio.run(main())
```

## 🧪 Testing

The library includes a comprehensive test suite using `pytest`.

### Unit Tests
Run fast, deterministic tests using local fixtures:
```bash
pytest tests/unit
```

### Integration Tests
Run tests against the live Global Omnium API (requires credentials):
```bash
pytest --run-integration tests/integration
```

## ⚖️ License & Attribution

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**.

**Attribution Notice:**
This library is based on the original work by [ldotlopez](https://github.com/ldotlopez), adapted, refactored, and updated by **carlos-48** to migrate from electrical energy data (original project) to water supply data.

## 🔗 Useful Links

- [Home Assistant Component](https://github.com/carlos-48/ha-globalomnium)
- [Original ideenergy Python API](https://github.com/ldotlopez/ideenergy)
