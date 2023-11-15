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


import argparse
import asyncio
import logging
import pprint
import sys
from datetime import datetime, timedelta

from . import Client, RequestFailedError, get_credentials, get_session


def build_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", required=False)
    parser.add_argument("-p", "--password", required=False)
    parser.add_argument("--credentials", required=False)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--contract")

    parser.add_argument("--list-contracts", action="store_true")
    parser.add_argument("--get-measure", action="store_true")
    parser.add_argument("--get-historical-consumption", action="store_true")
    parser.add_argument("--get-historical-generation", action="store_true")
    parser.add_argument("--get-historical-power-demand", action="store_true")

    return parser


async def _main():
    async def get_requested_data():
        if args.list_contracts:
            contracts = await client.get_contracts()
            contracts = {x["codContrato"]: x for x in contracts}
            return contracts

        if args.contract:
            await client.select_contract(args.contract)

        if args.get_measure:
            return await client.get_measure()

        end = datetime.now().replace(hour=0, minute=0, second=0)
        start = end - timedelta(days=7)

        if args.get_historical_consumption:
            return await client.get_historical_consumption(start, end)

        if args.get_historical_generation:
            return await client.get_historical_generation(start, end)

        if args.get_historical_power_demand:
            return await client.get_historical_power_demand()

    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d %(levelname)s %(module)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("ideenergy")
    logger.setLevel(logging.DEBUG)

    parser = build_arg_parser()
    args = parser.parse_args()
    username, password = get_credentials(args)

    if not username or not password:
        print("Missing username or password", file=sys.stderr)
        sys.exit(1)

    session = await get_session()
    client = Client(
        username=username, password=password, session=session, logger=logger
    )

    try:
        if data := await get_requested_data():
            print(pprint.pformat(data))

    except RequestFailedError as e:
        print(f"Request failed: {e}", file=sys.stderr)
        await session.close()
        sys.exit(1)

    await session.close()


def main():
    return asyncio.run(_main())


if __name__ == "__main__":
    import sys

    sys.exit(main())
