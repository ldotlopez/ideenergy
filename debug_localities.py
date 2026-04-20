import asyncio
import os
from globalomnium import Client, get_session

async def main():
    sess = await get_session()
    client = Client(sess, "user", "pass", "https://test.com")
    print(f"Localities dict: {client._localities}")
    print(f"Number of localities: {len(client._localities)}")
    
    res = await client.get_locations("va")
    print(f"Results for 'va': {res}")
    
    await sess.close()

if __name__ == "__main__":
    asyncio.run(main())
