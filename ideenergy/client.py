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
from .endpoints import (
    _BASE_URL,
    _CONSUMPTION_PERIOD_ENDPOINT,
    _CONTRACT_DETAILS_ENDPOINT,
    _CONTRACT_SELECTION_ENDPOINT,
    _CONTRACTS_ENDPOINT,
    _GENERATION_PERIOD_ENDPOINT,
    _ICP_STATUS_ENDPOINT,
    _KEEP_SESSION,
    _LOGIN_ENDPOINT,
    _MEASURE_ENDPOINT,
    _POWER_DEMAND_LIMITS_ENDPOINT,
    _POWER_DEMAND_PERIOD_ENDPOINT,
)
from .types import (
    HistoricalConsumption,
    HistoricalGeneration,
    HistoricalPowerDemand,
    Measure,
)


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

    # POST /consumidores/rest/loginNew/login HTTP/2
    # Host: www.i-de.es
    # User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0
    # Accept: application/json, text/plain, */*
    # Accept-Language: es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3
    # Accept-Encoding: gzip, deflate, br, zstd
    # dispositivo: desktop
    # AppVersion: v2
    # Content-Type: application/json; charset=UTF-8
    # Content-Length: 104
    # Origin: https://www.i-de.es
    # Connection: keep-alive
    # Cookie: [redacted]
    # Sec-Fetch-Dest: empty
    # Sec-Fetch-Mode: cors
    # Sec-Fetch-Site: same-origin
    # Priority: u=0
    # Pragma: no-cache
    # Cache-Control: no-cache
    # TE: trailers
    #
    # _HEADERS = {
    #     "dispositivo": "desktop",
    #     "AppVersion": "v2",
    #     "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0",
    # }

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
        # payload = [
        #     self.username,
        #     self.password,
        #     None,
        #     "Linux -",
        #     "PC",
        #     "Firefox 145.0",
        #     "0",
        #     "",
        #     "s",
        #     None,
        #     None,
        #     None,
        # ]

        await self.request_bytes("GET", _BASE_URL)
        data = await self.request_json("POST", _LOGIN_ENDPOINT, json=payload)

        if not isinstance(data, dict):
            raise InvalidData(data)

        if data.get("success", "") == "userExpired":
            raise UserExpiredError(data)

        if data.get("success", "false") != "true":
            raise CommandError(data)

        self._login_ts = datetime.now()
        self._logger.info(f"successful authentication as '{self.username}'")

        if self._contract:
            await self.select_contract(self._contract)
            self._logger.info(f"contract '{self._contract}' selected ")

    # async def verify_is_logged(self) -> bool:
    #     sess_info = await self.renew_session()
    #     return bool(sess_info.get("usSes"))

    async def renew_session(self) -> dict:
        return await self.request_json("POST", _KEEP_SESSION)

    @auth_required
    async def is_icp_ready(self) -> bool:
        data = await self.request_json("POST", _ICP_STATUS_ENDPOINT)
        ret = data.get("icp", "") == "trueConectado"

        return ret

    @auth_required
    async def get_contract_details(self) -> dict[str, Any]:
        data = await self.request_json("GET", _CONTRACT_DETAILS_ENDPOINT)
        if not data.get("codContrato", False):
            raise InvalidData(data)

        return data

    @auth_required
    async def get_contracts(self) -> list[dict[str, Any]]:
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
        if limits.get("resultado") != "correcto":
            raise CommandError(limits)

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


class UserExpiredError(ClientError):
    def __init__(self, data):
        self.data = data

    def __str__(self):
        return f"User expired: {self.data!r}"
