import pytest
import asyncio
import os
import aiohttp
from globalomnium import Client, get_session

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_extraction_flow():
    try:
        with open('/config/.openclaw/env/GLOBALOMNIUM_USER', 'r') as f:
            user = f.read().strip()
        with open('/config/.openclaw/env/GLOBALOMNIUM_PASS', 'r') as f:
            password = f.read().strip()
    except Exception as e:
        pytest.fail(f"❌ Error leyendo credenciales: {e}")

    # Usamos la base general por defecto que cubre la mayoría de municipios (incluyendo València en la API)
    base_url = "https://www.globalomnium.com/VirtualOffice"
    print(f"--- Probando conexión con base_url: {base_url} ---")
    
    try:
        sess = await get_session()
        client = Client(sess, user, password, base_url=base_url)
        
        print(f"Intentando login en {client.url_login}...")
        await client.login()
        print("✅ Login exitoso")
        
        contracts = await client.get_contracts()
        print(f"Contratos encontrados: {contracts}")
        
        # Intentamos obtener la lectura
        if contracts and "data" in contracts:
            # Asumiendo que contracts['data'] es la lista de suministros
            suministros = contracts["data"]
            if suministros:
                code = suministros[0].get("Code") or suministros[0].get("code")
                print(f"Seleccionando primer contrato: {code}")
                await client.select_contract(code)
                measure = await client.get_measure()
                print(f"Lectura actual: {measure}")
                assert measure.accumulate is not None
        else:
            pytest.fail("No se encontraron contratos para probar la extracción.")
        
    except Exception as e:
        pytest.fail(f"❌ Error durante la ejecución: {type(e).__name__}: {e}")
    finally:
        if 'sess' in locals():
            await sess.close()
