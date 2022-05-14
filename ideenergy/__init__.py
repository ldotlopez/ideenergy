#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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


import json
import os

from .client import (
    Client,
    ClientError,
    CommandError,
    get_session,
    HistoricalRequest,
    InvalidContractError,
    InvalidData,
    RequestFailedError,
)


def get_credentials(parsedargs=None, credentials=None, environ_prefix="IDEENERGY"):
    if parsedargs and parsedargs.username:
        return parsedargs.username, parsedargs.password

    credentials = credentials or getattr(parsedargs, "credentials", None)
    if credentials:
        with open(credentials, mode="r", encoding="utf-8") as fh:
            d = json.loads(fh.read())
        return d["username"], d["password"]

    if environ_prefix:
        environ_prefix = environ_prefix.upper()
        return (
            os.environ.get(f"{environ_prefix}_USERNAME"),
            os.environ.get(f"{environ_prefix}_PASSWORD"),
        )


def sanitize_address(address):
    return " ".join([x.strip().capitalize() for x in address.split(" ") if x])


__all__ = [
    "Client",
    "ClientError",
    "CommandError",
    "get_credentials",
    "get_session",
    "HistoricalRequest",
    "InvalidContractError",
    "InvalidData",
    "RequestFailedError",
    "sanitize_address",
]

__doc__ = """
    # Returned JSON payloads for login phase:

    scenario: Valid credentials.
    response code: 200
    response json:
    {
        "redirect": "informacion-del-contrato",
        "zona": "B",
        "success": "true",
        "idioma": "ES",
        "uCcr": "",
    }

    scenario: Invalid credentials.
    response code: 200
    response json:
    {
        "success": "false",
        "message": "El usuario o la contraseña que has introducido son incorrectos. Por favor, inténtalo de nuevo.",
    }


    scenario: Several login retries with invalid credentials.
    response code: 200
    response json:
    {
      "success": "false",
      "message": "Número de intentos de acceso excedido. Usuario bloqueado temporalmente. Vuelva a intentarlo dentro de 5 minutos."
    }

    # Retuned JSON payloads for measures (exposed keys: "valLecturaContador", "valMagnitud", "valEstado")

    scenario: valid measure
    response code: 200
    response json:
    {
        "valMagnitud": "10.31",
        "valInterruptor": "1",
        "valEstado": "09",
        "valLecturaContador": "42290",
        "codSolicitudTGT": "009016617100"
    }
    {
        "valMagnitud": "10.49",
        "valInterruptor": "1",
        "valEstado": "09",
        "valLecturaContador": "42290",
        "codSolicitudTGT": "009016672300",
    }

    # Cookies from server:
    [{'version': 0,
      'name': 'JSESSIONID',
      'value': '^0000[0-9a-zA-Z]{18}_[0-9a-zA-Z]{4}:[0-9a-zA-Z]{9}$',
      'port': None,
      'port_specified': False,
      'domain': 'www.i-de.es',
      'domain_specified': False,
      'domain_initial_dot': False,
      'path': '/',
      'path_specified': True,
      'secure': True,
      'expires': None,
      'discard': True,
      'comment': None,
      'comment_url': None,
      'rfc2109': False,
      '_rest': {'HttpOnly': None}},
     {'version': 0,
      'name': 'NSC_wt_mc_mbssvo0Y-[0-9]{5}',
      'value': '^[0-9a-f]{72}$',
      'port': None,
      'port_specified': False,
      'domain': 'www.i-de.es',
      'domain_specified': False,
      'domain_initial_dot': False,
      'path': '/',
      'path_specified': True,
      'secure': True,
      'expires': 1626089796,               # Aprox. 2 minutes
      'discard': False,
      'comment': None,
      'comment_url': None,
      'rfc2109': False,
      '_rest': {'httponly': None}}]
"""
