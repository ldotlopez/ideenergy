#!/usr/bin/env python3

# Copyright (C) 2021-2026 Luis López <luis@cuarentaydos.com>
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
import time
from collections.abc import Generator
from datetime import datetime, timedelta
from types import SimpleNamespace

import aiohttp
import dotenv

from . import Client, RequestFailedError, UserExpiredError


def build_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", required=False)
    parser.add_argument("-p", "--password", required=False)
    parser.add_argument("--configfile", required=False)
    parser.add_argument("--trace-http-requests", required=False, action="store_true")
    parser.add_argument("--retries", type=int, default=1)

    parser.add_argument("--contract")
    parser.add_argument("--list-contracts", action="store_true")
    parser.add_argument("--get-measure", action="store_true")
    parser.add_argument("--get-historical-consumption", action="store_true")
    parser.add_argument("--get-historical-generation", action="store_true")
    parser.add_argument("--get-historical-power-demand", action="store_true")
    parser.add_argument("--get-in-progress-consumption", action="store_true")
    parser.add_argument("--start", type=datetime.fromisoformat)
    parser.add_argument("--end", type=datetime.fromisoformat)

    parser.add_argument(
        "--check-auth-validity",
        action="store_true",
        help="Login and periodically verify how long the auth remains valid",
    )

    return parser


async def probe_auth_validity(client, logger, sleep=asyncio.sleep) -> int:
    try:
        await client.login()
    except Exception as exc:
        logger.exception(f"{client}: initial auth check failed: {exc}")
        return 1

    def wait_g() -> Generator[int]:
        yield from (0, 5, 10, 20, 30)
        while True:
            yield 30

    start = time.monotonic()
    for wait_minutes in wait_g():
        checkpoint = round((time.monotonic() - start) / 60)
        logger.info(f"{client}: waiting {wait_minutes} minutes")
        await sleep(wait_minutes * 60)

        try:
            await client.get_historical_consumption()
        except Exception:
            logger.exception(f"{client}: auth failed after {checkpoint} minutes")
            return 1

        logger.info(f"{client}: auth valid after {checkpoint} minutes")

    return 0


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

        now_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        seven_days = timedelta(days=7)
        start = args.start
        end = args.end
        if not end:
            if start:
                end = min(now_day, start + seven_days)
            else:
                end = now_day
        if not start:
            start = end - seven_days

        if args.get_historical_consumption:
            return await client.get_historical_consumption(start, end)

        if args.get_historical_generation:
            return await client.get_historical_generation(start, end)

        if args.get_historical_power_demand:
            return await client.get_historical_power_demand()

        if args.get_in_progress_consumption:
            return await client.get_in_progress_consumption()

    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d %(levelname)s %(module)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("ideenergy")
    logger.setLevel(logging.DEBUG)

    parser = build_arg_parser()
    args = parser.parse_args()

    conf = dotenv.dotenv_values(args.configfile)
    username = args.username or conf.get("I_DE_ENERGY_USERNAME", "")
    password = args.password or conf.get("I_DE_ENERGY_PASSWORD", "")

    if not username or not password:
        print("Missing username or password", file=sys.stderr)
        return 1

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
        or args.get_in_progress_consumption
        or args.check_auth_validity
    ):
        parser.print_help()
        return 1

    async with aiohttp.ClientSession(trace_configs=[trace_config]) as session:
        client = Client(
            username=username,
            password=password,
            session=session,
            logger=logger,
            session_auto_refresh=not args.check_auth_validity,
        )

        if args.check_auth_validity:
            return await probe_auth_validity(client, logger)

        try:
            if data := await get_requested_data():
                print(pprint.pformat(data))
                return 0
            else:
                print("Got empty response", file=sys.stderr)
                return 1

        except RequestFailedError as e:
            print(f"Request failed: {e}", file=sys.stderr)
            return 1

        except UserExpiredError as e:
            print(f"User expired, renew auth code via web: {e}", file=sys.stderr)
            return 1


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
    return asyncio.run(amain())


if __name__ == "__main__":
    import sys

    sys.exit(main())
