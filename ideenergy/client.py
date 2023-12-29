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


import functools
import json
import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from . import parsers
from .types import (
    HistoricalConsumption,
    HistoricalGeneration,
    HistoricalPowerDemand,
    Measure,
)

_BASE_URL = "https://www.i-de.es/consumidores/rest"

#
# URLs not confirmed since begining of the times
#
_CONTRACTS_ENDPOINT = f"{_BASE_URL}/cto/listaCtos/"
_CONTRACT_DETAILS_ENDPOINT = f"{_BASE_URL}/detalleCto/detalle/"
_CONTRACT_SELECTION_ENDPOINT = f"{_BASE_URL}/cto/seleccion/"
_GENERATION_PERIOD_ENDPOINT = (
    f"{_BASE_URL}/consumoNew/obtenerDatosGeneracionPeriodo/"
    "fechaInicio/{start:%d-%m-%Y}00:00:00/"
    "fechaFinal/{end:%d-%m-%Y}00:00:00/"
)
_ICP_STATUS_ENDPOINT = f"{_BASE_URL}/rearmeICP/consultarEstado"
_LOGIN_ENDPOINT = f"{_BASE_URL}/loginNew/login"
_MEASURE_ENDPOINT = f"{_BASE_URL}/escenarioNew/obtenerMedicionOnline/24"

#
# URLs reviewed on 2023-06-22
#
_CONSUMPTION_PERIOD_ENDPOINT = (
    f"{_BASE_URL}/consumoNew/obtenerDatosConsumoDH/"
    "{start:%d-%m-%Y}/"
    "{end:%d-%m-%Y}/"
    "horas/USU/"
)

_POWER_DEMAND_LIMITS_ENDPOINT = f"{_BASE_URL}/consumoNew/obtenerLimitesFechasPotencia/"
_POWER_DEMAND_PERIOD_ENDPOINT = (
    f"{_BASE_URL}/consumoNew/obtenerPotenciasMaximasRangoV2/"
    # fecMin and fecMax are provided by _POWER_DEMAND_LIMITS_ENDPOINT
    "{fecMin}/{fecMax}"
)


async def get_session() -> aiohttp.ClientSession:
    return aiohttp.ClientSession()


def auth_required(fn):
    @functools.wraps(fn)
    async def _wrap(client, *args, **kwargs):
        if client._auto_renew_user_session is True and client.is_logged is False:
            await client.login()

        return await fn(client, *args, **kwargs)

    return _wrap


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
        contract: str | None = None,
        logger: logging.Logger | None = None,
        user_session_timeout: timedelta | int = 300,
        auto_renew_user_session: bool = True,
    ):
        if not isinstance(user_session_timeout, timedelta):
            user_session_timeout = timedelta(seconds=user_session_timeout)

        self._sess = session
        self._username = username
        self._password = password
        self._contract = contract
        self._logger = logger or logging.getLogger("ideenergy")
        self._user_session_timeout = user_session_timeout
        self._auto_renew_user_session = auto_renew_user_session

        self._login_ts: datetime | None = None

    #
    # Some properties
    #

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

        delta = datetime.now() - self._login_ts
        return delta < self.user_session_timeout

    @property
    def user_session_timeout(self) -> timedelta:
        return self._user_session_timeout

    @property
    def auto_renew_user_session(self) -> bool:
        return self._auto_renew_user_session

    #
    # Requests
    #

    async def _request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        headers = kwargs.get("headers", {})
        headers.update(self._HEADERS)
        kwargs["headers"] = headers

        resp = await self._sess.request(method, url, **kwargs)
        if resp.status != 200:
            raise RequestFailedError(resp)

        return resp

    async def request_bytes(self, method: str, url: str, **kwargs) -> bytes:
        resp = await self._request(method, url, **kwargs)
        buff = await resp.content.read()
        return buff

    async def request_json(
        self, method: str, url: str, encoding: str = "utf-8", **kwargs
    ) -> dict[Any, Any]:
        buff = await self.request_bytes(method, url, **kwargs)
        data = json.loads(buff.decode(encoding))
        return data

    #
    # Methods
    #

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
            "Android 6.0",
            "Móvil",
            "Chrome 119.0.0.0",
            "0",
            "",
            "s",
            "",
        ]

        data = await self.request_json("POST", _LOGIN_ENDPOINT, json=payload)
        if not isinstance(data, dict):
            raise InvalidData(data)

        if data.get("success", "false") != "true":
            raise CommandError(data)

        self._login_ts = datetime.now()
        self._logger.info(f"successful authentication as '{self.username}'")

        if self._contract:
            await self.select_contract(self._contract)
            self._logger.info(f"contract '{self._contract}' selected ")

    @auth_required
    async def is_icp_ready(self) -> bool:
        """
        {
            'icp': 'trueConectado'
        }
        """
        data = await self.request_json("POST", _ICP_STATUS_ENDPOINT)
        ret = data.get("icp", "") == "trueConectado"

        return ret

    @auth_required
    async def get_contract_details(self) -> dict[str, Any]:
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
        data = await self.request_json("GET", _CONTRACT_DETAILS_ENDPOINT)
        if not data.get("codContrato", False):
            raise InvalidData(data)

        return data

    @auth_required
    async def get_contracts(self) -> list[dict[str, Any]]:
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
        data = await self.request_json("GET", _CONTRACTS_ENDPOINT)
        if not data.get("success", False):
            raise CommandError(data)

        try:
            return data["contratos"]
        except KeyError:
            raise InvalidData(data)

    @auth_required
    async def select_contract(self, id: str) -> None:
        resp = await self.request_json("GET", _CONTRACT_SELECTION_ENDPOINT + id)
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
        data = await self.request_json("GET", _MEASURE_ENDPOINT)

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
    async def get_historical_consumption(
        self, start: datetime, end: datetime
    ) -> HistoricalConsumption:
        start = min([start, end])
        end = max([start, end])
        url = _CONSUMPTION_PERIOD_ENDPOINT.format(start=start, end=end)

        data = await self.request_json("GET", url, encoding="iso-8859-1")

        ret = parsers.parse_historical_consumption(data)
        ret.periods = [x for x in ret.periods if x.start >= start and x.end < end]
        return ret

    async def get_historical_generation(
        self, start: datetime, end: datetime
    ) -> HistoricalGeneration:
        start = min([start, end])
        end = max([start, end])
        url = _GENERATION_PERIOD_ENDPOINT.format(start=start, end=end)

        data = await self.request_json("GET", url, encoding="iso-8859-1")
        ret = parsers.parse_historical_generation(data)

        return ret

    # @auth_required
    # async def _get_historical_generic_data(
    #     self, url_template: str, start: datetime, end: datetime
    # ) -> Dict[Any, Any]:
    #     start = min([start, end])
    #     end = max([start, end])
    #     url = url_template.format(start=start, end=end)

    #     data = await self.request_json("GET", url, encoding="iso-8859-1")

    #     base_date = datetime(start.year, start.month, start.day)
    #     ret = parsers.parser_generic_historical_data(data, base_date)

    #     return ret

    @auth_required
    async def get_historical_power_demand(self) -> HistoricalPowerDemand:
        @auth_required
        async def _get_available_interval(client):
            url = _POWER_DEMAND_LIMITS_ENDPOINT

            data = await client.request_json("GET", url)
            assert data.get("resultado") == "correcto"

            return data

        limits = await _get_available_interval(self)
        url = _POWER_DEMAND_PERIOD_ENDPOINT.format(**limits)

        data = await self.request_json("GET", url)

        ret = parsers.parse_historical_power_demand_data(data)
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
