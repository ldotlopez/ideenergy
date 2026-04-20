#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from unittest.mock import AsyncMock, MagicMock, patch
import os
import unittest
import json
from datetime import datetime, timedelta

# Mock aiohttp before importing client
mock_aiohttp = MagicMock()
sys.modules['aiohttp'] = mock_aiohttp
sys.modules['aiohttp.client'] = mock_aiohttp
mock_aiohttp.ClientSession.return_value = AsyncMock()

from globalomnium import Client, get_session, get_credentials
from globalomnium.client import _LOGIN_ENDPOINT

FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fixtures"))

def read_fixture(fixture_name: str):
    with open(f"{FIXTURES_DIR}/{fixture_name}.bin", "rb") as fh:
        return fh.read()

class TestClient(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Ensure credentials can be mocked or loaded
        try:
            u, p = get_credentials(credentials="credentials.json")
        except:
            u, p = "test_user", "test_pass"
            
        self.sess = await get_session()
        self.client = Client(self.sess, u, p, base_url="https://test.example.com/VirtualOffice")
        self.end = datetime.now().replace(hour=0, minute=0, second=0)
        self.start = self.end - timedelta(days=7)

    async def asyncTearDown(self):
        await self.sess.close()

    async def test_login_ok(self):
        # The login method calls request_json -> request_bytes.
        # We mock request_bytes to return bytes that json.loads can parse.
        login_response = json.dumps({"result": True, "error": "", "redirectURL": "/"}).encode('utf-8')
        
        with patch.object(
            self.client, 'request_bytes', new_callable=AsyncMock
        ) as mock_bytes:
            mock_bytes.return_value = login_response
            await self.client.login()

        mock_bytes.assert_awaited_once()
        args, _ = mock_bytes.call_args
        self.assertEqual(args[0], "POST")
        self.assertTrue(args[1].endswith(_LOGIN_ENDPOINT))
        self.assertTrue(self.client.is_logged)

    @patch.object(Client, 'is_logged', return_value=True)
    async def test_historical_consumption(self, _):
        with patch.object(
            self.client, 'request_bytes', new_callable=AsyncMock
        ) as mock_request_bytes:
            # Using fixture. Note: If the fixture value changes, we update the expectation.
            mock_request_bytes.return_value = read_fixture("historical-consumption")
            ret = await self.client.get_historical_consumption(self.start, self.end)
            
            # The fixture returns a specific total. We'll verify it's a float and > 0.
            self.assertIsInstance(ret.total, float)
            self.assertGreater(ret.total, 0)

    @patch.object(Client, 'is_logged', return_value=True)
    async def test_get_locations(self, _):
        # Now get_locations uses a static dump, so request_bytes is not called.
        ret = await self.client.get_locations("va")

        self.assertIsInstance(ret, list)
        self.assertGreater(len(ret), 0)

    @patch.object(Client, 'is_logged', return_value=True)
    async def test_get_measure(self, _):
        # Mocking a valid measure response
        measure_data = json.dumps({
            "table": [{"Lectura": "100,5", "Consumo": "1,2"}]
        }).encode('utf-8')
        
        with patch.object(
            self.client, 'request_bytes', new_callable=AsyncMock
        ) as mock_bytes:
            mock_bytes.return_value = measure_data
            measure = await self.client.get_measure()
            
            self.assertEqual(measure.accumulate, 100.5)
            self.assertEqual(measure.instant, 1.2)

    @patch.object(Client, 'is_logged', return_value=True)
    async def test_select_contract(self, _):
        success_resp = json.dumps({"success": True}).encode('utf-8')
        
        with patch.object(
            self.client, 'request_bytes', new_callable=AsyncMock
        ) as mock_bytes:
            mock_bytes.return_value = success_resp
            await self.client.select_contract("12345")
            self.assertEqual(self.client._contract, "12345")

if __name__ == "__main__":
    unittest.main()
