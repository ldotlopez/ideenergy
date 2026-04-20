import pytest
import asyncio
import os
import aiohttp
from globalomnium import Client, get_session

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_extraction_final_flow():
    try:
        with open('/config/.openclaw/env/GLOBALOMNIUM_USER', 'r') as f:
            user = f.read().strip()
        with open('/config/.openclaw/env/GLOBALOMNIUM_PASS', 'r') as f:
            password = f.read().strip()
    except Exception as e:
        pytest.fail(f"❌ Error leyendo credenciales: {e}")

    # Usamos la base_url descubierta para València
    base_url = "https://www.emivasa.es/VirtualOffice"
    print(f"--- Probando conexión con base_url: {base_url} ---")
    
    try:
        sess = await get_session()
        client = Client(sess, user, password, base_url=base_url)
        
        print(f"Intentando login en {client.url_login}...")
        await client.login()
        print("✅ Login exitoso")
        
        contracts = await client.get_contracts()
        print(f"Contratos encontrados: {contracts}")
        
        # The API might return a list directly or a dict with a 'data' key
        suministros = contracts.get("data", contracts) if isinstance(contracts, dict) else contracts
    
        if suministros and isinstance(suministros, list):
            if suministros:
                # Try different possible keys for the contract code
                code = None
                first_item = suministros[0]
                if isinstance(first_item, dict):
                    # Prioritize the internal_id extracted by the Client
                    code = first_item.get("internal_id") or first_item.get("Code") or first_item.get("code") or first_item.get("referencia")
                
                if code:
                    print(f"Seleccionando primer contrato por ID: {code}")
                    await client.select_contract(code)
                    measure = await client.get_measure()
                    print(f"Lectura actual: {measure}")
                    assert measure.accumulate is not None
                else:
                    pytest.fail("No se encontró un código de contrato válido en el primer suministro.")
        else:
            pytest.fail(f"No se encontraron suministros válidos. Respuesta: {contracts}")
    
    except Exception as e:
        pytest.fail(f"❌ Error durante la ejecución: {type(e).__name__}: {e}")
    finally:
        if 'sess' in locals():
            await sess.close()
