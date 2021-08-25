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
import sys

from ideenergy import (
    IDEEnergy,
    InvalidResponse,
    LoginFailed,
    get_credentials,
)


def build_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=False)
    parser.add_argument("--password", required=False)
    parser.add_argument("--credentials", required=False)

    return parser


def get_measure(username=None, password=None, retries=1, stderr=sys.stderr):
    api = IDEEnergy(username, password)

    for i in range(1, retries + 1):
        try:
            return api.get_measure()

        except LoginFailed as e:
            print(
                f"Login failed: {e.message}",
                file=stderr,
            )
            return

        except InvalidResponse as e:
            print(
                f"Invalid response: {e.message} ({e.data!r}) (attempt {i} of {retries})",
                file=stderr,
            )

    return None


def main():
    parser = build_arg_parser()

    args = parser.parse_args()
    username, password = get_credentials(args)

    if not username or not password:
        print("Missing username or password", file=sys.stderr)
        sys.exit(1)

    measure = get_measure(username, password)
    if not measure:
        sys.exit(1)

    print(repr(measure.asdict()))


if __name__ == "__main__":
    main()
