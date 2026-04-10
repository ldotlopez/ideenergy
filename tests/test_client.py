#!/usr/bin/env python3

# Copyright (C) 2021-2022 Luis López <luis@cuarentaydos.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.


import asyncio
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import aiohttp

from ideenergy import Client, MockClient
from ideenergy.cli import probe_auth_validity
from ideenergy.client import _LOGIN_ENDPOINT

FIXTURES_DIR = os.path.dirname(__file__) + "/fixtures"


def read_fixture(fixture_name: str):
    with open(f"{FIXTURES_DIR}/{fixture_name}.bin", "rb") as fh:
        return fh.read()


class TestClient(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = Client(None, "x", "y")
        self.end = datetime.now().replace(hour=0, minute=0, second=0)
        self.start = self.end - timedelta(days=7)

    async def test_login_ok(self):
        with patch(
            "ideenergy.Client.request_bytes",
            new_class=AsyncMock,
            return_value=read_fixture("login-ok"),
        ) as fn:
            await self.client.login()

        self.assertEqual(fn.await_count, 2)
        self.assertEqual(fn.await_args_list[0].args, ("GET", "https://www.i-de.es"))
        self.assertEqual(fn.await_args_list[1].args, ("POST", _LOGIN_ENDPOINT))

    @patch("ideenergy.Client.is_logged", return_value=True)
    async def test_historical_consumption(self, _):
        with patch(
            "ideenergy.Client.request_bytes",
            new_class=AsyncMock,
            return_value=read_fixture("historical-consumption"),
        ):
            ret = await self.client.get_historical_consumption(self.start, self.end)
            self.assertEqual(ret.total, 48867.0)

    @patch("ideenergy.Client.is_logged", return_value=True)
    async def test_historical_generation(self, _):
        with patch(
            "ideenergy.Client.request_bytes",
            new_class=AsyncMock,
            side_effect=[read_fixture("historical-generation")],
        ):
            ret = await self.client.get_historical_generation(self.start, self.end)

            self.assertEqual(len(ret.periods), 168)
            self.assertEqual(ret.periods[25].start, datetime(2022, 8, 20, 1, 0))
            self.assertEqual(ret.periods[25].value, 0.0)

    @patch("ideenergy.Client.is_logged", return_value=True)
    async def test_historical_power_demand(self, _):
        with patch(
            "ideenergy.Client.request_bytes",
            new_class=AsyncMock,
            side_effect=[
                read_fixture("historical-power-demand-limits"),
                read_fixture("historical-power-demand"),
            ],
        ):
            ret = await self.client.get_historical_power_demand()

            self.assertEqual(len(ret.demands), 58)
            self.assertEqual(ret.demands[25].dt, datetime(2022, 5, 28, 22, 15))
            self.assertEqual(ret.demands[25].value, 2816.0)


class TestMockClient(unittest.IsolatedAsyncioTestCase):
    async def test_login_sets_contract_and_session(self):
        client = MockClient(None, "x", "y", contract="123456789")

        await client.login()

        self.assertTrue(client.is_logged)
        self.assertEqual(client.contract, "123456789")

    async def test_historical_consumption_is_deterministic(self):
        client = MockClient(None, "x", "y")
        start = datetime(2026, 1, 1)
        end = start + timedelta(days=1)

        ret = await client.get_historical_consumption(start, end)

        self.assertEqual(len(ret.periods), 24)
        self.assertEqual(ret.periods[0].start, start)
        self.assertEqual(ret.periods[-1].end, end)
        self.assertEqual(ret.total, sum(period.value for period in ret.periods))

    async def test_concurrent_clients_do_not_share_state(self):
        client1 = MockClient(None, "x", "y", contract="111")
        client2 = MockClient(None, "x", "y", contract="222")

        await asyncio.gather(client1.login(), client2.login())
        details1, details2 = await asyncio.gather(
            client1.get_contract_details(), client2.get_contract_details()
        )

        self.assertEqual(client1.contract, "111")
        self.assertEqual(client2.contract, "222")
        self.assertEqual(details1["codContrato"], 123456789.0)
        self.assertEqual(details2["codContrato"], 123456789.0)


class TestAuthValidityProbe(unittest.IsolatedAsyncioTestCase):
    async def test_probe_stops_on_failure(self):
        class FakeClient:
            def __init__(self):
                self.login_calls = 0
                self.check_calls = 0

            async def login(self):
                self.login_calls += 1

            async def get_historical_consumption(self):
                self.check_calls += 1
                if self.check_calls == 3:
                    raise RuntimeError("auth expired")

            def __str__(self):
                return "fake-client"

        sleeps = []

        async def fake_sleep(seconds):
            sleeps.append(seconds)

        client = FakeClient()
        logger = Mock()

        ret = await probe_auth_validity(client, logger, sleep=fake_sleep)

        self.assertEqual(ret, 1)
        self.assertEqual(client.login_calls, 1)
        self.assertEqual(client.check_calls, 3)
        self.assertEqual(sleeps, [0, 300, 600])


if __name__ == "__main__":
    unittest.main()
