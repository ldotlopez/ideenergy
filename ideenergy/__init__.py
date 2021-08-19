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
import json
import os

from .ideenergy import Iberdrola, InvalidResponse, LoginFailed


def build_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=False)
    parser.add_argument("--password", required=False)
    parser.add_argument("--config-file", required=False)

    return parser


def get_credentials(
    parsedargs=None, config_file=None, environ_prefix="IDEENERGY"
):
    if parsedargs.username:
        return parsedargs.username, parsedargs.password

    config_file = config_file or parsedargs.config_file
    if config_file:
        with open(config_file, mode="r", encoding="utf-8") as fh:
            d = json.loads(fh.read())
        return d["username"], d["password"]

    if environ_prefix:
        environ_prefix = environ_prefix.upper()
        return (
            os.environ.get(f"{environ_prefix}_USERNAME"),
            os.environ.get(f"{environ_prefix}_PASSWORD"),
        )


__all__ = ["Iberdrola", "InvalidResponse", "LoginFailed"]
