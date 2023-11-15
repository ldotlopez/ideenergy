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
from datetime import datetime, timedelta

from ideenergy import client, get_credentials, get_session


async def main():
    u, p = get_credentials(credentials="credentials.json")
    sess = await get_session()
    api = client.Client(username=u, password=p, session=sess)
    await api.login()

    end = datetime.now().replace(hour=0, minute=0, second=0)
    start = end - timedelta(days=7)

    async def _dump_measure():
        with open("tests/fixtures/measure.bin", mode="wb") as fh:
            url = client._MEASURE_ENDPOINT
            fh.write(await api.request_bytes("GET", url))

    # Dump historical consumption
    async def _dump_historical_consumption():
        with open("tests/fixtures/historical-consumption.bin", mode="wb") as fh:
            url = client._CONSUMPTION_PERIOD_ENDPOINT.format(start=start, end=end)
            fh.write(await api.request_bytes("GET", url))

    # Dump historical generation
    async def _dump_historical_generation():
        with open("tests/fixtures/historical-generation.bin", mode="wb") as fh:
            url = client._GENERATION_PERIOD_ENDPOINT.format(start=start, end=end)
            fh.write(await api.request_bytes("GET", url))

    # Dump power demand
    async def _dump_historical_power_demand():
        with open("tests/fixtures/historical-power-demand.bin", mode="wb") as fh:
            data = await api.request_json("GET", client._POWER_DEMAND_LIMITS_ENDPOINT)
            url = client._POWER_DEMAND_PERIOD_ENDPOINT.format(**data)
            buff = await api.request_bytes("GET", url)
            fh.write(buff)

    for fn in [
        _dump_historical_consumption,
        _dump_historical_generation,
        _dump_historical_power_demand,
        _dump_measure,
    ]:
        print(f"Running {fn.__name__}", end="")
        try:
            await fn()

        except client.RequestFailedError as e:
            print(f": failed ({e})")
            continue

        print(": OK")

    await sess.close()

    # pp(await api.get_historical_consumption(start, end))
    # pp(await api.get_historical_generation(start, end))
    # pp(await api.get_historical_power_demand())


asyncio.run(main())
