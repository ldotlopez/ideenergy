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


import logging
import sys

from . import cli, get_credentials

try:
    from paho.mqtt import publish
except ImportError as e:
    raise SystemError("Install paho.mqtt") from e


def main():
    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d %(levelname)s %(module)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("ideenergy")
    logger.setLevel(logging.DEBUG)

    parser = cli.build_arg_parser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--topic", default="ideenergy")

    args = parser.parse_args()

    username, password = get_credentials(args)
    measure = cli.get_measure(username, password)
    if not measure:
        sys.exit(1)

    msgs = [
        {"topic": f"{args.topic}/{k}", "payload": v, "retain": True}
        for (k, v) in measure.asdict().items()
    ]

    publish.multiple(msgs, hostname=args.host)


if __name__ == "__main__":
    main()
