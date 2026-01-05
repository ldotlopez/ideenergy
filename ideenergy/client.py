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
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
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
    _REST_BASE_URL,
)
from .types import (
    HistoricalConsumption,
    HistoricalGeneration,
    HistoricalPowerDemand,
    Measure,
)

LOGGER = logging.getLogger(__name__)

I_DE_ENERGY_DUMP_DIRECTORY = os.environ.get("I_DE_ENERGY_DUMP_DIRECTORY", "")
I_DE_ENERGY_DUMP = bool(I_DE_ENERGY_DUMP_DIRECTORY)
if I_DE_ENERGY_DUMP:
    I_DE_ENERGY_DUMP_BASE_PATH = Path(I_DE_ENERGY_DUMP_DIRECTORY)
else:
    I_DE_ENERGY_DUMP_DIRECTORY = None


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
    ) -> None:
        if not isinstance(user_session_timeout, timedelta):
            user_session_timeout = timedelta(seconds=user_session_timeout)

        self._sess = session
        self._username = username
        self._password = password
        self._contract = contract
        self._user_session_timeout = user_session_timeout
        self._auto_renew_user_session = auto_renew_user_session

        self._login_ts: datetime | None = None

    def __str__(self) -> str:
        return f"{self.username}" + ("/{self.contract}" if self.contract else "")

    def __repr__(self) -> str:
        return (
            f"<ideenergy.Client "
            f"username={self.username}, "
            f"contract={self.contract or '(none)'}>"
        )

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
    def contract(self) -> str | None:
        return self._contract

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
            LOGGER.error(f"{self}: {method} URL '{url}' failed (status={resp.status})")
            raise RequestFailedError(resp)

        LOGGER.debug(f"{self}: {method} URL '{url}' success (status={resp.status})")
        return resp

    async def request_bytes(self, method: str, url: str, **kwargs) -> bytes:
        resp = await self._request(method, url, **kwargs)
        buff = await resp.content.read()

        if I_DE_ENERGY_DUMP and url.startswith(_REST_BASE_URL):
            dump = I_DE_ENERGY_DUMP_BASE_PATH / (slugify(url) + ".bin")
            dump.parent.mkdir(parents=True, exist_ok=True)
            dump.write_bytes(buff)

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
            LOGGER.warning(f"{self}: auth failed, invalid data")
            raise InvalidData(data)

        if data.get("success", "false") != "true":
            LOGGER.warning(f"{self}: auth failed, no success")
            raise CommandError(data)

        if data.get("success", "") == "userExpired":
            LOGGER.warning(f"{self}: auth failed, user session expired")
            raise UserExpiredError(data)

        self._login_ts = datetime.now()
        LOGGER.debug(f"{self}: succesfully authenticaded")

        if self._contract:
            await self.select_contract(self._contract)

    # async def verify_is_logged(self) -> bool:
    #     sess_info = await self.renew_session()
    #     return bool(sess_info.get("usSes"))

    async def renew_session(self) -> dict:
        ret = await self.request_json("POST", _KEEP_SESSION)
        LOGGER.debug(f"{self}: session renewed")

        return ret

    @auth_required
    async def is_icp_ready(self) -> bool:
        data = await self.request_json("POST", _ICP_STATUS_ENDPOINT)
        if ret := data.get("icp", "") == "trueConectado":
            LOGGER.debug(f"{self}: ICP is ready")
        else:
            LOGGER.debug(f"{self}: ICP is NOT ready")

        return ret

    @auth_required
    async def get_contract_details(self) -> dict[str, Any]:
        data = await self.request_json("GET", _CONTRACT_DETAILS_ENDPOINT)
        if not data.get("codContrato", False):
            LOGGER.warning(f"{self}: contract details fetch failed")
            raise InvalidData(data)

        LOGGER.debug(f"{self}: contract details fetched")
        return data

    @auth_required
    async def get_contracts(self) -> list[dict[str, Any]]:
        data = await self.request_json("GET", _CONTRACTS_ENDPOINT)

        if not data.get("success", False):
            LOGGER.warning(f"{self}: contract list fetch failed")
            raise CommandError(data)

        LOGGER.debug(f"{self}: contract list fetched")
        return data["contratos"]

    @auth_required
    async def select_contract(self, contract_id: str) -> None:
        data = await self.request_json(
            "GET", _CONTRACT_SELECTION_ENDPOINT + contract_id
        )
        if not data.get("success", False):
            LOGGER.warning(f"{self}: contract select failed")
            raise InvalidContractError(contract_id)

        LOGGER.debug(f"{self}: contract '{contract_id}' selected")
        self._contract = contract_id

    @auth_required
    async def get_measure(self) -> Measure:
        LOGGER.info(f"{self}: requesting data to the ICP, may take up to a minute.")
        data = await self.request_json("GET", _MEASURE_ENDPOINT)

        if not data.get("codSolicitudTGT"):
            LOGGER.warning(f"{self}: measure request failed")
            raise CommandError(data)

        ret = Measure(
            accumulate=int(data["valLecturaContador"]),
            instant=float(data["valMagnitud"]),
        )
        LOGGER.debug(f"{self}: measure fetched succesfully")

        return ret

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

        LOGGER.debug(f"{self}: historical consumption fetched succesfully")

        return ret

    async def get_historical_generation(
        self, start: datetime, end: datetime
    ) -> HistoricalGeneration:
        start = min([start, end])
        end = max([start, end])
        url = _GENERATION_PERIOD_ENDPOINT.format(start=start, end=end)

        data = await self.request_json("GET", url, encoding="iso-8859-1")
        ret = parsers.parse_historical_generation(data)

        LOGGER.debug(f"{self}: historical generation fetched succesfully")

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

        LOGGER.debug(f"{self}: historical power demand fetched succesfully")

        return ret


class ClientError(Exception):
    pass


class RequestFailedError(ClientError):
    def __init__(self, response):
        self.response = response

    def __str__(self):
        return (
            f"Invalid response for '{self.response.request.url}': "
            f"{self.response.status} - {self.response.reason}"
        )


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


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", value.lower())
