import asyncio
import aiohttp

async def test_account():
    with open('/config/.openclaw/env/GLOBALOMNIUM_USER', 'r') as f:
        user = f.read().strip()
    with open('/config/.openclaw/env/GLOBALOMNIUM_PASS', 'r') as f:
        password = f.read().strip()
    base_url = "https://www.emivasa.es/VirtualOffice"
    sess = aiohttp.ClientSession()
    headers = {
        "Accept": "*/*",
        "User-Agent": "py-globalomnium/2023.12.1",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }
    # Login
    login_url = base_url + "/action_Login/"
    login_payload = f"login={user}&pass={password}&remember=true&suministro="
    async with sess.post(login_url, data=login_payload, headers=headers) as resp:
        if resp.status != 200:
            print(f"Login failed: {resp.status}")
            return
        login_data = await resp.json()
        print(f"Login response: {login_data}")
        if not login_data.get("result"):
            print("Login not successful")
            return
    print("Login successful")
    # Now try to get the account page
    account_url = base_url + "/Secure/Account"
    async with sess.get(account_url, headers=headers) as resp:
        print(f"GET {account_url} -> status {resp.status}")
        if resp.status == 200:
            text = await resp.text()
            # Look for any URLs in the text that might be API endpoints
            import re
            # Find all strings that look like URLs or endpoints
            urls = re.findall(r'[\'"](/[^\s\'"]+)[\'"]', text)
            print(f"Found {len(urls)} potential endpoint references in HTML")
            for u in urls[:10]:
                print(f"  {u}")
            # Also look for action_ patterns
            actions = re.findall(r'action_[a-zA-Z_]+', text)
            print(f"Found {len(actions)} action references: {actions[:10]}")
            # Print first 500 chars of text for inspection
            print(f"First 500 chars of response: {text[:500]}")
        else:
            text = await resp.text()
            print(f"Non-200 response: {text[:200]}")
    await sess.close()

if __name__ == "__main__":
    asyncio.run(test_account())