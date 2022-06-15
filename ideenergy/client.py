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


import dataclasses
import enum
import datetime
import functools
import json
import logging
from typing import Any, Dict, List, Optional, Union

import aiohttp

_BASE_URL = "https://www.i-de.es/consumidores/rest"
_CONSUMPTION_PERIOD_ENDPOINT = (
    f"{_BASE_URL}/consumoNew/obtenerDatosConsumoPeriodo/"
    "fechaInicio/{start}00:00:00/fechaFinal/{end}00:00:00/"
)
_CONTRACTS_ENDPOINT = f"{_BASE_URL}/cto/listaCtos/"
_CONTRACT_DETAILS_ENDPOINT = f"{_BASE_URL}/detalleCto/detalle/"
_CONTRACT_SELECTION_ENDPOINT = f"{_BASE_URL}/cto/seleccion/"
_GENERATION_PERIOD_ENDPOINT = (
    f"{_BASE_URL}/consumoNew/obtenerDatosGeneracionPeriodo/"
    "fechaInicio/{start}00:00:00/fechaFinal/{end}00:00:00/"
)
_ICP_STATUS_ENDPOINT = f"{_BASE_URL}/rearmeICP/consultarEstado"
_LOGIN_ENDPOINT = f"{_BASE_URL}/loginNew/login"
_MEASURE_ENDPOINT = f"{_BASE_URL}/escenarioNew/obtenerMedicionOnline/24"


async def get_session() -> aiohttp.ClientSession:
    return aiohttp.ClientSession()


def auth_required(fn):
    @functools.wraps(fn)
    async def _wrap(client, *args, **kwargs):
        if client._auto_renew_user_session is True and client.is_logged is False:
            await client.login()

        return await fn(client, *args, **kwargs)

    return _wrap


@dataclasses.dataclass
class Measure:
    accumulate: int
    instant: float

    def asdict(self) -> Dict[str, Union[int, float]]:
        return dataclasses.asdict(self)


class HistoricalRequest(enum.Enum):
    CONSUMPTION = enum.auto()
    GENERATION = enum.auto()


class Client:
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

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        contract: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
        user_session_timeout: Union[datetime.timedelta, int] = 300,
        auto_renew_user_session: bool = True,
    ):
        if not isinstance(user_session_timeout, datetime.timedelta):
            user_session_timeout = datetime.timedelta(seconds=user_session_timeout)

        self._sess = session
        self._username = username
        self._password = password
        self._contract = contract
        self._logger = logger or logging.getLogger("ideenergy")
        self._user_session_timeout = user_session_timeout
        self._auto_renew_user_session = auto_renew_user_session

        self._login_ts: Optional[datetime.datetime] = None

    @property
    def username(self) -> str:
        return self._username

    @property
    def password(self) -> str:
        return self._password

    @property
    def is_logged(self) -> bool:
        if not self._login_ts:
            return False

        delta = datetime.datetime.now() - self._login_ts
        return delta < self.user_session_timeout

    @property
    def user_session_timeout(self) -> datetime.timedelta:
        return self._user_session_timeout

    @property
    def auto_renew_user_session(self) -> bool:
        return self._auto_renew_user_session

    async def raw_request(
        self, method: str, url: str, **kwargs
    ) -> aiohttp.ClientResponse:
        headers = kwargs.get("headers", {})
        headers.update(self._HEADERS)
        kwargs["headers"] = headers

        resp = await self._sess.request(method, url, **kwargs)
        if resp.status != 200:
            raise RequestFailedError(resp)

        return resp

    async def request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        resp = await self.raw_request(method, url, **kwargs)

        if resp.status != 200:
            raise RequestFailedError(resp)

        return await resp.json()

    async def login(self) -> None:
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

        data = await self.request("POST", _LOGIN_ENDPOINT, json=payload)
        if not isinstance(data, dict):
            raise InvalidData(data)

        if data.get("success", "false") != "true":
            raise CommandError(data)

        self._login_ts = datetime.datetime.now()

        if self._contract:
            await self.select_contract(self._contract)

        self._logger.info(
            f"Login successful for {self.username}, "
            f"using {self._contract if self._contract else 'default'} contract"
        )

    @auth_required
    async def is_icp_ready(self) -> bool:
        """
        {
            'icp': 'trueConectado'
        }
        """
        data = await self.request("POST", _ICP_STATUS_ENDPOINT)
        try:
            ret = data.get("icp", "") == "trueConectado"
        except KeyError:
            raise InvalidData(data)

        self._logger.info(f"{self}: ICP is {'ready' if ret else 'NOT ready'}")
        return ret

    @auth_required
    async def get_contract_details(self) -> Dict[str, Any]:
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
            "direccion": "C/ XXXXXXXXXXXXXXXXXX, 12 , 34 00000-XXXXXXXXXXXXXXXXXXXX"
                " - XXXXXXXXX           ",
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
        data = await self.request("GET", _CONTRACT_DETAILS_ENDPOINT)
        if not data.get("codContrato", False):
            raise InvalidData(data)

        return data

    @auth_required
    async def get_contracts(self) -> List[Dict[str, Any]]:
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
        data = await self.request("GET", _CONTRACTS_ENDPOINT)
        if not data.get("success", False):
            raise CommandError(data)

        try:
            return data["contratos"]
        except KeyError:
            raise InvalidData(data)

    @auth_required
    async def select_contract(self, id: str) -> None:
        resp = await self.request("GET", _CONTRACT_SELECTION_ENDPOINT + id)
        if not resp.get("success", False):
            raise InvalidContractError(id)

        self._contract = id
        self._logger.info(f"{self}: '{id}' contract selected")

    @auth_required
    async def get_measure(self) -> Measure:
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
        data = await self.request("GET", _MEASURE_ENDPOINT)
        self._logger.debug(f"Got reply, raw data: {data!r}")

        try:
            measure = Measure(
                accumulate=int(data["valLecturaContador"]),
                instant=float(data["valMagnitud"]),
            )

        except (KeyError, ValueError) as e:
            raise InvalidData(data) from e

        self._logger.info(f"{self}: ICP measure reading successful")
        return measure

    @auth_required
    async def get_historical_data(
        self, req_type: HistoricalRequest, start: datetime.date, end: datetime.date
    ) -> Dict[str, Any]:
        def _historical_parser(data: Dict) -> Dict[str, Any]:
            base = datetime.datetime(start.year, start.month, start.day)
            historical = data["y"]["data"][0]
            historical = [x for x in historical if x is not None]
            historical = [
                (base + datetime.timedelta(hours=idx), x.get("valor", None))
                for (idx, x) in enumerate(historical)
            ]
            historical = [
                (dt, float(x) if x is not None else x) for (dt, x) in historical
            ]

            return {
                "accumulated": float(data["acumulado"]),
                "accumulated-co2": float(data["acumuladoCO2"]),
                "historical": historical,
            }

        def _consumption_parser(data: Dict) -> Dict[str, Any]:
            return _historical_parser(data)

        def _generation_parser(data) -> Dict[str, Any]:
            return _historical_parser(data)

        backends = {
            HistoricalRequest.CONSUMPTION: (
                _CONSUMPTION_PERIOD_ENDPOINT,
                _consumption_parser,
            ),
            HistoricalRequest.GENERATION: (
                _GENERATION_PERIOD_ENDPOINT,
                _generation_parser,
            ),
        }

        try:
            endpoint_url, parser = backends[req_type]
        except KeyError as e:
            raise ValueError(req_type, "Unknow historical request") from e

        start = min([start, end])
        end = max([start, end])

        url = endpoint_url.format(
            start=start.strftime("%d-%m-%Y"), end=end.strftime("%d-%m-%Y")
        )
        resp = await self.raw_request("GET", url)
        buff = await resp.content.read()

        try:
            buff = buff.decode(resp.charset)
            data = json.loads(buff)

            ret = parser(data)

        except (TypeError, json.JSONDecodeError) as e:
            raise InvalidData(buff) from e

        except NotImplementedError as e:
            raise NotImplementedError(
                f"Request type not implemented: {req_type}. server data: {buff!r}"
            ) from e

        self._logger.info(f"{self}: {req_type} reading successful")
        return ret

    def __repr__(self):
        return f"<ideenergy.Client username={self.username}, contract={self._contract}>"


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
        return f"Invalid contract code: {self.data!r}"
