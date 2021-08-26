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


import dataclasses
import functools
import logging


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
      'value': '0000EP17M58b2nl0OeDgoC_G82u:1f4c1hiiv',
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
      'name': 'NSC_wt_mc_mbssvo0Y-12009',  # last portion (12009) can vary
      'value': '<erased>',                 # matches ^[0-9a-f]{72}$
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


def require_login(fn):
    @functools.wraps(fn)
    async def wrap(api):
        if not api.logged:
            await api.login()

        return await fn(api)

    return wrap


class Client:
    _BASE_URL = "https://www.i-de.es/consumidores/rest/"
    _HEADERS = {
        "Content-Type": "application/json; charset=utf-8",
        "esVersionNueva": "1",
        "idioma": "es",
        "movilAPP": "si",
        "tipoAPP": "ios",
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 11_4_1 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15G77"
        ),
    }

    def __init__(self, session, username, password, logger=None):
        self.logger = logger or logging.getLogger("ideenergy")
        self.baseurl = self._BASE_URL
        self.username = username
        self.password = password

        self.sess = session
        self.sess.headers.update(self._HEADERS)

    @property
    def logged(self):
        # self.sess.cookies.clear_expired_cookies()

        cookie = self.sess.cookie_jar.filter_cookies(self._BASE_URL)
        return bool(cookie.get("JSESSIONID"))

        # for c in self.sess.cookies:
        #     if (
        #         c.name.startswith("NSC_wt_mc_")
        #         and re.search(r"^[0-9-a-f]{72}$", c.value, re.IGNORECASE)
        #         != None
        #     ):
        #         return True

        # return False

    async def login(self):
        payload = [
            self.username,
            self.password,
            "",
            "iOS 11.4.1",
            "Movil",
            "Aplicación móvil V. 15",
            "0",
            "0",
            "0",
            "",
            "n",
        ]

        self.logger.debug("Trying log-in into consumer panel")

        async with self.sess.post(
            self.baseurl + "loginNew/login", json=payload
        ) as resp:

            if resp.status != 200:
                raise LoginFailed(resp.status, None)

            data = await resp.json()
            if data.get("success", "false") != "true":
                raise LoginFailed(resp.status, data.get("message"))

        self.logger.debug("Login successfully.")

    @require_login
    async def get_measure(self):
        self.logger.debug("Measure request…")

        async with self.sess.get(
            self.baseurl + "escenarioNew/obtenerMedicionOnline/24"
        ) as resp:
            if not resp.status == 200:
                raise InvalidResponse("Invalid response code", resp.status)

            data = await resp.json()
            self.logger.debug(f"Measure raw data: {data!r}")

            if not data:
                raise InvalidResponse("Empty data", data)

            try:
                return Measure(
                    accumulate=int(data["valLecturaContador"]),
                    instant=float(data["valMagnitud"]),
                )

            except (KeyError, ValueError) as e:
                raise InvalidResponse("Invalid measure data", data) from e


@dataclasses.dataclass
class Measure:
    accumulate: int
    instant: int

    def asdict(self):
        return dataclasses.asdict(self)


class IDEEnergyException(Exception):
    pass


class LoginFailed(IDEEnergyException):
    __doc__ = """
        Cookies
        <RequestsCookieJar[
            Cookie(
                version=0,
                name='JSESSIONID',
                value='0000MGXnAS19ktAlLSZ8dgI1oJ0:1f4c1hi2c',
                port=None,
                port_specified=False,
                domain='www.i-de.es',
                domain_specified=False,
                domain_initial_dot=False,
                path='/',
                path_specified=True,
                secure=True,
                expires=None,
                discard=True,
                comment=None,
                comment_url=None,
                rest={'HttpOnly': None},
                rfc2109=False
            ),
            # This cookie expires
            Cookie(version=0,
                name='NSC_wt_mc_mbssvo0Y-12009',
                value='5ccba3d89f4919c8612dbceb2dd5f7d574280f294e10e218aa1e35122183a20833fbe6dc',
                port=None,
                port_specified=False,
                domain='www.i-de.es',
                domain_specified=False,
                domain_initial_dot=False,
                path='/',
                path_specified=True,
                secure=True,
                expires=1626087405,
                discard=False,
                comment=None,
                comment_url=None,
                rest={'httponly': None},
                rfc2109=False)
        ]>
    """

    def __init__(self, code, message):
        self.code = code
        self.message = message


class InvalidResponse(IDEEnergyException):
    def __init__(self, message, data):
        self.message = message
        self.data = data
