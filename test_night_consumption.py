import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from globalomnium import Client, get_session

async def test_night_consumption():
    # Load credentials from environment
    username = os.environ.get('GLOBALOMNIUM_USER')
    password = os.environ.get('GLOBALOMNIUM_PASS')
    
    if not username or not password:
        # Fallback to credentials.json
        try:
            with open('credentials.json', 'r') as f:
                creds = json.load(f)
                username = creds.get('username')
                password = creds.get('password')
        except Exception:
            print("❌ Error: GLOBALOMNIUM_USER or GLOBALOMNIUM_PASS not set in environment and credentials.json not found.")
            return
    
    if not username or not password:
        print("❌ Error: No credentials found.")
        return

    # Default base_url if not provided in env
    base_url = os.environ.get('GLOBALOMNIUM_BASE_URL', "https://www.globalomnium.com/VirtualOffice")

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("test")

    print(f"Starting E2E test for {username} on {base_url}...")

    session = await get_session()
    try:
        async with session:
            client = Client(session, username, password, base_url=base_url, logger=logger)
            
            try:
                print("Attempting login...")
                await client.login()
                print("✅ Login successful")
                
                contracts = await client.get_contracts()
                print(f"Found {len(contracts)} contracts")
                
                if not contracts:
                    print("❌ No contracts found for this user.")
                    return

                # Use the first contract
                contract = contracts[0]
                code = contract.get("code") or contract.get("Code") or contract.get("internal_id")
                if not code:
                    print("❌ Could not determine contract code from first contract.")
                    return
                
                print(f"Selecting contract: {code}")
                await client.select_contract(code)

                # Fetch last 7 days
                end = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                start = end - timedelta(days=7)
                print(f"Requesting historical consumption from {start.strftime('%d/%m/%Y')} to {end.strftime('%d/%m/%Y')}...")
                
                historical = await client.get_historical_consumption(start, end)
                print(f"Successfully retrieved {len(historical.consumptions)} data points.")

                # Calculate night consumption (22:00 to 07:00)
                night_consumption = 0.0
                for c in historical.consumptions:
                    if c.start.hour >= 22 or c.start.hour < 7:
                        night_consumption += c.value

                print("-" * 30)
                print(f"Test Results:")
                print(f"  Total data points: {len(historical.consumptions)}")
                print(f"  Estimated night consumption: {night_consumption:.4f}")
                print("-" * 30)
                print("✅ End-to-end test completed successfully.")

            except Exception as e:
                print(f"❌ E2E Test Failed: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
    finally:
        pass

if __name__ == "__main__":
    asyncio.run(test_night_consumption())
