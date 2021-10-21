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
import logging
import sys

import aiohttp

from ideenergy import Client, ClientError, RequestFailedError, get_credentials


def build_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", required=False)
    parser.add_argument("-p", "--password", required=False)
    parser.add_argument("--credentials", required=False)
    parser.add_argument("--retries", type=int, default=1)

    return parser


async def async_get_measure(
    username=None, password=None, retries=1, logger=None, stderr=sys.stderr
):
    async with aiohttp.ClientSession() as sess:
        client = Client(sess, username, password, logger=logger)

        try:
            await client.login()
        except ClientError as e:
            print(f"Login failed: {e}", file=stderr)
            return

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


def get_measure(*args, **kwargs):
    measure = None

    async def _fn():
        nonlocal measure
        measure = await async_get_measure(*args, **kwargs)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_fn())

    return measure


def main():
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

    measure = get_measure(
        username, password, retries=args.retries, logger=logger
    )
    if not measure:
        sys.exit(1)

    print(repr(measure.asdict()))
