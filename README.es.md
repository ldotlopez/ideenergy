# API de Python para GlobalOmnium

[![GitHub Release](https://img.shields.io/github/v/release/carlos-48/globalomnium)](https://github.com/carlos-48/globalomnium/releases)
[![CodeQL](https://github.com/carlos-48/globalomnium/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/carlos-48/globalomnium/actions/workflows/codeql-analysis.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

Acceso programático a los datos de consumo de agua de [Global Omnium](https://www.globalomnium.com/), el grupo gestor de distribuidores de agua en España.

## 🚀 Características

- **Soporte Multi-entidad**: Compatible con diversas empresas gestoras de Global Omnium (ej. Emivasa, Aguas de Valencia y otras).
- **Python Moderno**: Totalmente actualizado para Python 3.11+ con tipado fuerte y soporte asíncrono (`asyncio` / `aiohttp`).
- **Datos de Consumo**: Obtención de lecturas actuales y consumo horario/histórico.
- **Fiable**: Parsing robusto y gestión de sesiones diseñada para integraciones estables en Home Assistant.

## 📦 Instalación

### Para Desarrollo (Modo Editable)
Si estás contribuyendo o desarrollando un componente basado en esta librería, instálala en modo editable:

```bash
git clone https://github.com/carlos-48/globalomnium.git
cd globalomnium
pip install -e .
```

### Para Producción
```bash
pip install globalomnium
```

## 🛠️ Inicio Rápido

```python
import asyncio
import aiohttp
from globalomnium.client import Client

async def main():
    async with aiohttp.ClientSession() as session:
        # La base_url es obligatoria ya que depende de la empresa gestora de tu municipio
        client = Client(
            session=session,
            username="tu_usuario",
            password="tu_password",
            base_url="https://www.emivasa.es/VirtualOffice" 
        )
        
        # Ejemplo: Obtener medida actual
        measure = await client.get_measure()
        print(f"Lectura Actual: {measure.accumulate} m³")
        print(f"Consumo Instantáneo: {measure.instant} l/h")

asyncio.run(main())
```

## 🧪 Pruebas

La librería incluye una suite de pruebas exhaustiva utilizando `pytest`.

### Tests Unitarios
Ejecuta pruebas rápidas y deterministas utilizando fixtures locales:
```bash
pytest tests/unit
```

### Tests de Integración
Ejecuta pruebas contra la API real de Global Omnium (requiere credenciales):
```bash
pytest --run-integration tests/integration
```

## ⚖️ Licencia y Atribución

Este proyecto está licenciado bajo la **Licencia Pública General GNU v3.0 (GPLv3)**.

**Nota de Atribución:**
Esta librería está basada en el trabajo original de [ldotlopez](https://github.com/ldotlopez), adaptada, refactorizada y actualizada por **carlos-48** para migrar la gestión de datos de energía eléctrica al suministro de agua.

## 🔗 Enlaces Útiles

- [Componente de Home Assistant](https://github.com/carlos-48/ha-globalomnium)
- [API de Python ideenergy original](https://github.com/ldotlopez/ideenergy)
