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
import os
import pprint
import sys
from datetime import datetime, timedelta
from types import SimpleNamespace

import aiohttp
import dotenv

from . import (  # get_credentials,
    Client,
    RequestFailedError,
    UserExpiredError,
)


def build_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", required=False)
    parser.add_argument("-p", "--password", required=False)
    # parser.add_argument("--credentials", required=False)
    parser.add_argument("--trace-http-requests", required=False, action="store_true")
    parser.add_argument("--retries", type=int, default=1)

    parser.add_argument("--contract")
    parser.add_argument("--list-contracts", action="store_true")
    parser.add_argument("--get-measure", action="store_true")
    parser.add_argument("--get-historical-consumption", action="store_true")
    parser.add_argument("--get-historical-generation", action="store_true")
    parser.add_argument("--get-historical-power-demand", action="store_true")

    return parser


async def amain():
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
    username = args.username or os.environ.get("I_DE_ENERGY_USERNAME", "")
    password = args.password or os.environ.get("I_DE_ENERGY_PASSWORD", "")

    if not username or not password:
        print("Missing username or password", file=sys.stderr)
        sys.exit(1)

    trace_config = aiohttp.TraceConfig()
    if args.trace_http_requests:
        trace_config.on_request_start.append(on_request_start)
        trace_config.on_request_end.append(on_request_end)
        trace_config.on_request_chunk_sent.append(on_request_chunk_sent)

    if not (
        args.list_contracts
        or args.get_measure
        or args.get_historical_consumption
        or args.get_historical_generation
        or args.get_historical_power_demand
    ):
        parser.print_help()
        sys.exit(1)

    async with aiohttp.ClientSession(trace_configs=[trace_config]) as session:
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

        except UserExpiredError as e:
            print(f"User expired, renew auth code via web: {e}", file=sys.stderr)
            await session.close()
            sys.exit(1)


async def on_request_start(
    session: aiohttp.ClientSession,
    trace_config_ctx: SimpleNamespace,
    params: aiohttp.TraceRequestStartParams,
):
    print(f"--> Sending request: {params.method} {params.url}")


async def on_request_end(
    session: aiohttp.ClientSession,
    trace_config_ctx: SimpleNamespace,
    params: aiohttp.TraceRequestStartParams,
):
    print(
        f"<-- Received response: {params.response}"  # ty:ignore[unresolved-attribute]
    )


async def on_request_chunk_sent(
    session: aiohttp.ClientSession,
    context: SimpleNamespace,
    params: aiohttp.TraceRequestStartParams,
):
    raw_data = params.chunk.decode("utf-8")  # ty:ignore[unresolved-attribute]
    print(f"--> Sending chunk: {raw_data}")


def main():
    dotenv.load_dotenv()
    return asyncio.run(amain())


if __name__ == "__main__":
    import sys

    sys.exit(main())
