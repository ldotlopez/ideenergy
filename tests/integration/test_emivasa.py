import pytest
import asyncio
import aiohttp
from globalomnium import Client, get_session

@pytest.mark.integration
async def test_endpoints():
    # Load credentials
    with open('/config/.openclaw/env/GLOBALOMNIUM_USER', 'r') as f:
        user = f.read().strip()
    with open('/config/.openclaw/env/GLOBALOMNIUM_PASS', 'r') as f:
        password = f.read().strip()
    
    base_url = "https://www.emivasa.es/VirtualOffice"
    print(f"Testing with base_url: {base_url}")
    
    sess = await get_session()
    client = Client(sess, user, password, base_url=base_url)
    
    try:
        await client.login()
        print("Login successful")
        
        # Try to get contracts with the original path
        print(f"Trying contracts endpoint: {client.url_contracts}")
        try:
            contracts = await client.get_contracts()
            print(f"Contracts: {contracts}")
        except Exception as e:
            print(f"Failed to get contracts: {e}")
            
        # If contracts work, try measure
        if 'contracts' in locals() and contracts:
            # Select first contract
            if isinstance(contracts, dict) and 'data' in contracts:
                supplies = contracts['data']
                if supplies:
                    code = supplies[0].get('Code') or supplies[0].get('code')
                    print(f"Selecting contract: {code}")
                    await client.select_contract(code)
                    measure = await client.get_measure()
                    print(f"Measure: {measure}")
                    
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await sess.close()

if __name__ == "__main__":
    asyncio.run(test_endpoints())