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
import datetime
import functools
import json
import logging

import aiohttp

_AUTO_LOGIN = True

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


async def get_session():
    return aiohttp.ClientSession()


def auth_required(fn):
    @functools.wraps(fn)
    async def _wrap(self, *args, **kwargs):
        global _AUTO_LOGIN
        if _AUTO_LOGIN is True and self.user_is_logged is False:
            self._logger.warning("User is not logged or session is too old")
            await self.login()

        return await fn(self, *args, **kwargs)

    return _wrap


class Client:
    _BASE_URL = "https://www.i-de.es/consumidores/rest"
    _CONSUMPTION_PERIOD_ENDPOINT = (
        f"{_BASE_URL}/consumoNew/obtenerDatosConsumoPeriodo/"
        "fechaInicio/{start}00:00:00/"
        "fechaFinal/{end}00:00:00/"
    )
    _CONTRACTS_ENDPOINT = f"{_BASE_URL}/cto/listaCtos/"
    _CONTRACT_DETAILS_ENDPOINT = f"{_BASE_URL}/detalleCto/detalle/"
    _CONTRACT_SELECTION_ENDPOINT = f"{_BASE_URL}/cto/seleccion/"
    _ICP_STATUS_ENDPOINT = f"{_BASE_URL}/rearmeICP/consultarEstado"
    _LOGIN_ENDPOINT = f"{_BASE_URL}/loginNew/login"
    _MEASURE_ENDPOINT = f"{_BASE_URL}/escenarioNew/obtenerMedicionOnline/24"

    _USER_SESSION_TIMEOUT = 300
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
        self.username = username
        self.password = password
        self._logger = logger or logging.getLogger("ideenergy")
        self._sess = session
        self._login_ts = None

    @property
    def user_is_logged(self):
        if not self._login_ts:
            return False

        delta = datetime.datetime.now() - self._login_ts
        return delta.total_seconds() < self._USER_SESSION_TIMEOUT

    async def raw_request(self, method, url, **kwargs):
        headers = kwargs.get("headers", {})
        headers.update(self._HEADERS)
        kwargs["headers"] = headers

        resp = await self._sess.request(method, url, **kwargs)
        if resp.status != 200:
            raise RequestFailedError(resp)

        return resp

    async def request(self, method, url, **kwargs):
        resp = await self.raw_request(method, url, **kwargs)

        if resp.status != 200:
            raise RequestFailedError(resp)

        return await resp.json()

    async def login(self):
        """
        {
            'redirect': 'informacion-del-contrato',
            'zona': 'B',
            'success': 'true',
            'idioma': 'ES',
            'uCcr': ''
        }
        """
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

        data = await self.request("POST", self._LOGIN_ENDPOINT, json=payload)
        if data.get("success", "false") != "true":
            raise CommandError(data)

        self._logger.debug("Login successfully.")
        self._login_ts = datetime.datetime.now()

    @auth_required
    async def is_icp_ready(self):
        """
        {
            'icp': 'trueConectado'
        }
        """
        data = self.request("POST", self._ICP_STATUS_ENDPOINT)
        try:
            return data["icp"] == "trueConectado"
        except KeyError:
            raise InvalidData(data)

    @auth_required
    async def get_contract_details(self):
        """
        {
            "ape1Titular": "xxxxxx                                       ",
            "ape2Titular": "xxxxxx                                       ",
            "codCliente": "12345678",
            "codContrato": 123456789.0,
            "codPoblacion": "000000",
            "codProvincia": "00",
            "codPostal": "00000",
            "codSociedad": 3,
            "codTarifaIblda": "92T0",
            "codTension": "09",
            "cups": "ES0000000000000000XY",
            "direccion": "C/ XXXXXXXXXXXXXXXXXX, 12 , 34 00000-XXXXXXXXXXXXXXXXXXXX - XXXXXXXXX           ",
            "dni": "12345678Y",
            "emailFactElec": "xxxxxxxxx@xxxxx.com",
            "esAutoconsumidor": False,
            "esAutogenerador": False,
            "esPeajeDirecto": False,
            "fecAltaContrato": "2000-01-01",
            "fecBajaContrato": 1600000000000,
            "fecUltActua": "22.10.2021",
            "indEstadioPS": 4,
            "indFraElectrn": "N",
            "nomGestorOficina": "XXXXXXXXXXXX                                      ",
            "nomPoblacion": "XXXXXXXXXXXXXXXXXXXX                         ",
            "nomProvincia": "XXXXXXXXX                                    ",
            "nomTitular": "XXXXX                                        ",
            "numCtaBancaria": "0",
            "numTelefono": "         ",
            "numTelefonoAdicional": "123456789",
            "potDia": 0.0,
            "potMaxima": 5750,
            "presion": "1.00",
            "puntoSuministro": "1234567.0",
            "tipAparato": "CN",
            "tipCualificacion": "PP",
            "tipEstadoContrato": "AL",
            "tipo": "A",
            "tipPuntoMedida": None,
            "tipSectorEne": "01",
            "tipSisLectura": "TG",
            "tipSuministro": None,
            "tipUsoEnerg": "",
            "listContador": [
                {
                    "fecInstalEquipo": "28-01-2011",
                    "propiedadEquipo": "i-DE",
                    "tipAparato": "CONTADOR TELEGESTION",
                    "tipMarca": "ZIV",
                    "numSerieEquipo": 12345678.0,
                }
            ],
            "esTelegestionado": True,
            "esTelegestionadoFacturado": True,
            "esTelemedido": False,
            "cau": None,
        }
        """
        data = await self.request("GET", self._CONTRACT_DETAILS_ENDPOINT)
        if not data.get("codContrato", False):
            raise InvalidData(data)

        return data

    @auth_required
    async def get_contracts(self):
        """
        {
            'success': true,
            'contratos': [
                {
                    'direccion': 'xxxxxxxxxxxxxxxxxxxxxxx',
                    'cups': 'ES0000000000000000AB',
                    'tipo': 'A',
                    'tipUsoEnergiaCorto': '-',
                    'tipUsoEnergiaLargo': '-',
                    'estContrato': 'Alta',
                    'codContrato': '123456789',
                    'esTelegestionado': True,
                    'presion': '1.00',
                    'fecUltActua': '01.01.1970',
                    'esTelemedido': False,
                    'tipSisLectura': 'TG',
                    'estadoAlta': True
                }
            ]
        }
        """
        data = await self.request("GET", self._CONTRACTS_ENDPOINT)
        if not data.get("success", False):
            raise CommandError(data)

        try:
            return data["contratos"]
        except KeyError:
            raise InvalidData(data)

    @auth_required
    async def select_contract(self, id):
        resp = await self.request("GET", self._CONTRACT_SELECTION_ENDPOINT + id)
        if not resp.get("success", False):
            raise InvalidContractError(id)

    @auth_required
    async def get_measure(self):
        """
        {
            "valMagnitud": "158.64",
            "valInterruptor": "1",
            "valEstado": "09",
            "valLecturaContador": "43167",
            "codSolicitudTGT": "012345678901",
        }
        """

        self._logger.debug("Requesting data to the ICP, may take up to a minute.")

        measure = await self.request("GET", self._MEASURE_ENDPOINT)
        self._logger.debug(f"Got reply, raw data: {measure!r}")

        try:
            return Measure(
                accumulate=int(measure["valLecturaContador"]),
                instant=float(measure["valMagnitud"]),
            )

        except (KeyError, ValueError) as e:
            raise InvalidData(measure) from e

    @auth_required
    async def get_consumption_period(self, start, end):
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = end.replace(hour=0, minute=0, second=0, microsecond=0)
        start = min([start, end])
        end = max([start, end])

        url = self._CONSUMPTION_PERIOD_ENDPOINT.format(
            start=start.strftime("%d-%m-%Y"), end=end.strftime("%d-%m-%Y")
        )
        resp = await self.raw_request("GET", url)
        buff = await resp.content.read()
        buff = buff.decode(resp.charset)
        data = json.loads(buff)

        historical = data["y"]["data"][0]
        historical = [x for x in historical if x is not None]
        historical = [
            (start + datetime.timedelta(hours=idx), x.get("valor", None))
            for (idx, x) in enumerate(historical)
        ]
        historical = [(dt, float(x) if x is not None else x) for (dt, x) in historical]

        return {
            "accumulated": float(data["acumulado"]),
            "accumulated-co2": float(data["acumuladoCO2"]),
            "historical": historical,
        }


@dataclasses.dataclass
class Measure:
    accumulate: int
    instant: int

    def asdict(self):
        return dataclasses.asdict(self)


class ClientError(Exception):
    pass


class RequestFailedError(ClientError):
    def __init__(self, response):
        self.response = response

    def __str__(self):
        return f"Invalid response: {self.response.status} - {self.response.reason}"


class CommandError(ClientError):
    def __init__(self, data):
        self.data = data

    def __str__(self):
        return f"Command not succesful: {self.data!r}"


class InvalidData(ClientError):
    def __init__(self, data):
        self.data = data

    def __str__(self):
        return f"Invalid data from server: {self.data!r}"


class InvalidContractError(ClientError):
    def __init__(self, data):
        self.data = data

    def __str__(self):
        return f"Invalid contract code: {self.data}"
