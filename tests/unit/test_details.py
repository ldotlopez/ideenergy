import asyncio
import aiohttp
import json
import logging
# Use absolute import for the package
from globalomnium.client import Client

async def main():

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("test_details")
    
    with open('/config/.openclaw/env/GLOBALOMNIUM_USER', 'r') as f:
        user = f.read().strip()
    with open('/config/.openclaw/env/GLOBALOMNIUM_PASS', 'r') as f:
        password = f.read().strip()
    
    base_url = 'https://www.emivasa.es/VirtualOffice'
    
    async with aiohttp.ClientSession() as session:
        client = Client(
            session=session,
            username=user,
            password=password,
            base_url=base_url,
            logger=logger
        )
        
        try:
            print("Logging in...")
            await client.login()
            
            print("Fetching contracts...")
            contracts = await client.get_contracts()
            print(f"Found {len(contracts)} contracts.")
            
            if not contracts:
                print("No contracts found. Cannot fetch details.")
                return
                
            # Use the first contract for the test
            contract_code = contracts[0].get('referencia')
            if not contract_code:
                # Try to find another field that might be the code
                contract_code = contracts[0].get('id') or list(contracts[0].values())[0]
            
            print(f"Selecting contract: {contract_code}")
            await client.select_contract(contract_code)
            
            print("Fetching contract details (this may take a while)...")
            details = await client.get_contract_details()
            
            print("\n--- FULL CONTRACT DETAILS RESPONSE ---")
            print(json.dumps(details, indent=2, ensure_ascii=False))
            print("--- END RESPONSE ---\n")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    asyncio.run(main())
