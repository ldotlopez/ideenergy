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


import sys

from ideenergy import (
    Iberdrola,
    InvalidResponse,
    LoginFailed,
    build_arg_parser,
    get_credentials,
)


def main():
    parser = build_arg_parser()

    args = parser.parse_args()
    username, password = get_credentials(args)

    if not username or not password:
        print("Missing username or password", file=sys.stderr)
        sys.exit(1)

    api = Iberdrola(username, password)

    try:
        measure = api.get_instant_measure().asdict()

    except LoginFailed as e:
        print(f"Login failed: {e.message}", file=sys.stderr)
        sys.exit(1)

    except InvalidResponse as e:
        print(f"Invalid response: {e.message} ({e.data!r})", file=sys.stderr)
        sys.exit(2)

    print(repr(measure))


if __name__ == "__main__":
    main()
