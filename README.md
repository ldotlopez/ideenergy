# ideenergy

🇪🇸 Español · [🇬🇧 English](https://github.com/ldotlopez/ideenergy/blob/main/README.en.md)

Acceso programático al consumo eléctrico de consumidores en [i-DE](https://www.i-de.es/) (Iberdrola Distribución Eléctrica).

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

> **Aviso:** proyecto no oficial. No está afiliado, respaldado ni patrocinado por Iberdrola ni por i-DE.
> Usa la API privada de la web/app de i-DE, que puede cambiar o dejar de funcionar sin previo aviso.

## ⚠️ Antes de empezar: la API es muy restrictiva

La API de i-DE limita mucho las peticiones y **un uso abusivo puede bloquear tu cuenta**.

- Haz las mínimas llamadas posibles y no las metas en bucles ni reintentos agresivos.
- Reutiliza una única sesión (un solo `login`) para todas las consultas.
- `get_measure()` y `get_in_progress_consumption()` consultan al ICP (contador) y pueden tardar hasta un minuto.
- Para desarrollar y probar, usa `MockClient` (ver más abajo) en lugar de la API real.

## Instalación

Requiere Python 3.11 o superior.

```bash
pip install ideenergy
# o con uv
uv add ideenergy
```

## Línea de comandos

```bash
export I_DE_ENERGY_USERNAME="tu-usuario"
export I_DE_ENERGY_PASSWORD="tu-contraseña"   # también puedes usar un fichero .env

ideenergy --list-contracts
ideenergy --get-measure
ideenergy --get-historical-consumption --start 2026-01-01 --end 2026-01-07
```

Opciones principales: `--contract`, `--list-contracts`, `--get-measure`, `--get-historical-consumption`,
`--get-historical-generation`, `--get-historical-power-demand`, `--get-in-progress-consumption`,
`--start` / `--end` (ISO 8601, por defecto los últimos 7 días). También acepta `-u/--username` y `-p/--password`.

> `--trace-http-requests` es solo para depuración: vuelca todo el tráfico, **incluida tu contraseña y cookies de sesión**.
> `--check-auth-validity` se ejecuta durante horas y hace logins repetidos: no lo uses contra la API real salvo que sepas lo que haces.

## Uso rápido

```python
import asyncio
import aiohttp
import ideenergy


async def main():
    async with aiohttp.ClientSession() as session:
        client = ideenergy.Client(
            session=session,
            username="tu-usuario",
            password="tu-contraseña",
        )

        # Si tienes varios contratos, selecciona uno
        # contracts = await client.get_contracts()
        # await client.select_contract(contracts[0]["codContrato"])

        # Lectura actual del contador (acumulado en kWh e instantáneo en kW)
        measure = await client.get_measure()
        print(measure.accumulate, measure.instant)

        # Consumo histórico (por defecto, últimos 7 días)
        history = await client.get_historical_consumption()
        for period in history.periods:
            print(period.start, period.end, period.value)


asyncio.run(main())
```

El login es automático en la primera llamada y la sesión se renueva sola.

### Métodos disponibles

| Método | Descripción |
|---|---|
| `get_contracts()` / `select_contract(id)` | Lista y selecciona contrato |
| `get_contract_details()` | Detalles del contrato seleccionado |
| `get_measure()` | Lectura actual del contador (`Measure`) |
| `get_historical_consumption(start, end)` | Consumo histórico (`HistoricalConsumption`) |
| `get_in_progress_consumption()` | Consumo del periodo en curso |
| `get_historical_generation(start, end)` | Generación histórica (autoconsumo) |
| `get_historical_power_demand()` | Demanda de potencia (último año) |
| `is_icp_ready()` | Comprueba si el ICP está disponible |

Errores: `ClientError` y derivadas (`RequestFailedError`, `CommandError`, `InvalidData`, `InvalidContractError`, `UserExpiredError`).

## Desarrollo sin tocar la API real

`MockClient` imita al cliente con datos grabados, sin red:

```python
client = ideenergy.MockClient(session=None, username="x", password="y")
```

Tests (offline):

```bash
uv sync
uv run python -m unittest discover tests
```

## Enlaces útiles

- [Componente relacionado para Home Assistant](https://github.com/ldotlopez/ha-ideenergy)
- [Documentación sobre otras distribuidoras](https://www.genbeta.com/web/como-saber-consumo-electrico-tiempo-real-casa)

## Home Assistant

Si lo que buscas es ver tu consumo en Home Assistant, usa la integración
[ha-ideenergy](https://github.com/ldotlopez/ha-ideenergy), que está construida sobre esta librería.

## Licencia

[GPL-3.0-only](https://github.com/ldotlopez/ideenergy/blob/main/LICENSE)
