#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (C) 2021 Luis López <luis@cuarentaydos.com>
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
import datetime
import logging
import pprint
import sys

import aiohttp

from ideenergy import Client, ClientError, RequestFailedError, get_credentials


def build_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", required=False)
    parser.add_argument("-p", "--password", required=False)
    parser.add_argument("--credentials", required=False)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--contract")

    parser.add_argument("--list-contracts", action="store_true")
    parser.add_argument("--get-measure", action="store_true")
    parser.add_argument("--get-historical", action="store_true")

    return parser


async def get_contracts(username, password, logger=None):
    async with aiohttp.ClientSession() as sess:
        client = Client(sess, username, password, logger=logger)
        return await client.get_contracts()


async def get_measure(
    username=None,
    password=None,
    contract=None,
    retries=1,
    logger=None,
    stderr=sys.stderr,
):
    async with aiohttp.ClientSession() as sess:
        client = Client(sess, username, password, logger=logger)

        try:
            await client.login()
        except ClientError as e:
            print(f"Login failed: {e}", file=stderr)
            return

        if contract:
            await client.select_contract(contract)

        for i in range(1, retries + 1):
            try:
                return await client.get_measure()

            except RequestFailedError as e:
                print(f"Request failed, aborted: {e}")
                break

            except ClientError as e:
                print(
                    f"Client error: {e}) " f"(attempt {i} of {retries})",
                    file=stderr,
                )

    return None


async def get_consumption_period(username, password, contract=None, logger=None):
    async with aiohttp.ClientSession() as sess:
        client = Client(sess, username, password, logger=logger)
        if contract:
            await client.select_contract(contract)

        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=7)
        return await client.get_consumption_period(start, end)


async def main():
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

    if args.list_contracts:
        contracts = await get_contracts(username, password, logger=logger)
        contracts = {x["codContrato"]: x for x in contracts}
        print(pprint.pformat(contracts))

    if args.get_measure:
        measure = await get_measure(
            username,
            password,
            retries=args.retries,
            contract=args.contract,
            logger=logger,
        )

        if not measure:
            sys.exit(1)

        print(pprint.pformat(measure.asdict()))

    if args.get_historical:
        historical = await get_consumption_period(
            username, password, contract=args.contract, logger=logger
        )
        print(pprint.pformat(historical))


if __name__ == "__main__":
    asyncio.run(main())
