# -*- coding: utf-8 -*-

# Copyright (C) 2021-2022 Luis López <luis@cuarentaydos.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

import dataclasses
import functools
import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Final

import aiohttp

from . import parsers
from .go_types import HistoricalConsumption

# Standard endpoints for all Global Omnium entities
_PATH_CONTRACTS = "/Secure/action_getSuministrosAsociados"
_PATH_BILLING_CANDIDATES = "/Secure/action_getSuministrosCandidatosFacturaE"
_PATH_MANAGEMENT_HISTORY = "/Secure/action_getHistorialGestiones"
_PATH_CONTRACT_DETAILS = "/Secure/action_getSuministro/"
_PATH_CONTRACT_SELECTION = "/Secure/action_setSuministroActivo/"
_PATH_LOGIN = "/action_Login/"
_PATH_MEASURE = "/Secure/action_getDatosLecturaHorariaEntreFechas"
_PATH_CONSUMPTION_PERIOD = "/Secure/action_getDatosLecturaHorariaEntreFechas"
_LOGIN_ENDPOINT = "/action_Login/"
_LOCATIONS_ENDPOINT = "https://www.globalomnium.com/Direcciones/DameMunicipiosWebs"

@dataclasses.dataclass
class Measure:
    accumulate: float
    instant: float

    def asdict(self) -> Dict[str, float]:
        return dataclasses.asdict(self)


def auth_required(func):
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        if not self.is_logged:
            await self.login()
        return await func(self, *args, **kwargs)
    return wrapper

class Client:
    _HEADERS = {
        "Accept": "*/*",
        "User-Agent": "py-globalomnium/2023.12.1",
    }

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        base_url: str,
        contract: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
        user_session_timeout: Union[timedelta, int] = 300,
        auto_renew_user_session: bool = True,
    ):
        if not isinstance(user_session_timeout, timedelta):
            user_session_timeout = timedelta(seconds=user_session_timeout)

        self._sess = session
        self._username = username
        self._password = password
        self._contract = contract
        self._logger = logger or logging.getLogger("globalomnium")
        self._user_session_timeout = user_session_timeout
        self._auto_renew_user_session = auto_renew_user_session
        self.base_url = base_url

        self._login_ts: Optional[datetime] = None
        
        # Base URLs resolution
        self._base_urls: List[str] = []
        self._load_base_urls()
        self._localities: Dict[str, str] = {}
        self._load_localities_dump()

    def _load_base_urls(self) -> None:
        try:
            base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            urls_path = os.path.join(base_path, "base_urls.json")
            if os.path.exists(urls_path):
                with open(urls_path, "r", encoding="utf-8") as f:
                    self._base_urls = json.load(f)
                self._logger.info(f"Loaded {len(self._base_urls)} base URLs from dump")
            else:
                self._logger.warning(f"Base URLs dump not found at {urls_path}")
                print(f"DEBUG: Base URLs dump NOT found at {urls_path}")
        except Exception as e:
            self._logger.error(f"Error loading base URLs dump: {e}")
            print(f"DEBUG: Error loading base URLs dump: {e}")

    def _load_localities_dump(self) -> None:
        try:
            base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            dump_path = os.path.join(base_path, "localities_dump.json")
            if os.path.exists(dump_path):
                with open(dump_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._localities = {item["text"].upper(): item["url"] for item in data if "text" in item and "url" in item}
                    elif isinstance(data, dict):
                        self._localities = data
                    else:
                        self._localities = {}
                self._logger.info(f"Loaded {len(self._localities)} localities from dump")
            else:
                self._logger.warning(f"Localities dump not found at {dump_path}")
                print(f"DEBUG: Localities dump NOT found at {dump_path}")
        except Exception as e:
            self._logger.error(f"Error loading localities dump: {e}")
            print(f"DEBUG: Error loading localities dump: {e}")

    @property
    def url_login(self) -> str:
        return f"{self.base_url}{_PATH_LOGIN}"

    @property
    def url_contracts(self) -> str:
        return f"{self.base_url}{_PATH_CONTRACTS}"

    @property
    def url_billing_candidates(self) -> str:
        return f"{self.base_url}{_PATH_BILLING_CANDIDATES}"

    @property
    def url_management_history(self) -> str:
        return f"{self.base_url}{_PATH_MANAGEMENT_HISTORY}"

    @property
    def url_contract_details(self) -> str:
        return f"{self.base_url}{_PATH_CONTRACT_DETAILS}"

    @property
    def url_contract_selection(self) -> str:
        return f"{self.base_url}{_PATH_CONTRACT_SELECTION}"

    @property
    def url_measure(self) -> str:
        return f"{self.base_url}{_PATH_MEASURE}"

    @property
    def url_consumption(self) -> str:
        return f"{self.base_url}{_PATH_CONSUMPTION_PERIOD}"

    @property
    def user_session_timeout(self) -> timedelta:
        return self._user_session_timeout

    @property
    def is_logged(self) -> bool:
        if not self._login_ts:
            return False
        delta = datetime.now() - self._login_ts
        return delta < self.user_session_timeout

    @property
    def username(self) -> str:
        return self._username

    @property
    def password(self) -> str:
        return self._password

    async def request_json(
        self, method: str, url: str, encoding: str = "utf-8", **kwargs
    ) -> Dict[Any, Any]:
        buff = await self.request_bytes(method, url, **kwargs)
        return json.loads(buff.decode(encoding))

    async def request_bytes(self, method: str, url: str, **kwargs) -> bytes:
        resp = await self._request(method, url, **kwargs)
        return await resp.content.read()

    async def _request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        headers = kwargs.get("headers", {}).copy()
        for k, v in self._HEADERS.items():
            headers.setdefault(k, v)
        kwargs["headers"] = headers
        resp = await self._sess.request(method, url, **kwargs)
        if resp.status != 200:
            body = await resp.text()
            self._logger.error(f"Request failed with status {resp.status}. Body: {body[:500]}")
            raise RequestFailedError(resp)
        return resp

    async def login(self) -> None:
        login_payload = {
            "login": self.username,
            "pass": self.password,
            "remember": "true",
            "suministro": ""
        }
        data = await self.request_json("POST", self.url_login, data=login_payload)
        
        # The API sometimes returns a list containing the result dict
        if isinstance(data, list) and len(data) > 0:
            data = data[0]

        if not isinstance(data, dict) or data.get("result", "false") != True:
            raise CommandError(data)
        self._login_ts = datetime.now()
        if self._contract:
            await self.select_contract(self._contract)
        self._logger.info(f"{self}: successful authentication")

    async def get_base_urls(self, filtro: Optional[str] = None) -> List[str]:
        if not filtro:
            return self._base_urls
        filtro_lower = filtro.lower()
        return [url for url in self._base_urls if filtro_lower in url.lower()]

    async def get_locations(self, filtro: str) -> List[Dict[str, Any]]:
        # Resolve from static dump to avoid API instability
        filtro_upper = filtro.upper()
        results = []
        
        # 1. Exact match
        if filtro_upper in self._localities:
            url = self._localities[filtro_upper]
            results.append({"text": filtro_upper, "url": url})
        
        # 2. Partial matches (if no exact match)
        if not results:
            for text, url in self._localities.items():
                if filtro_upper in text:
                    results.append({"text": text, "url": url})
        
        # Limit results to avoid overloading
        return results[:10]

    @auth_required
    async def get_contract_details(self) -> Dict[str, Any]:
        data = await self.request_json("POST", self.url_contract_details, json={"code": self._contract})
        if data.get("result", "false") != True:
            raise CommandError(data)
        return data

    @auth_required
    async def get_contracts(self) -> List[Dict[str, Any]]:
        data = await self.request_json("POST", self.url_contracts, json={})
        if not data.get("result", False):
            raise CommandError(data)
        
        contracts = data.get("data", [])
        if not isinstance(contracts, list):
            contracts = [contracts] if contracts else []

        # Extract the real internal ID from the HTML in 'datos' field
        for c in contracts:
            if isinstance(c, dict) and "datos" in c:
                match = re.search(r"Editar\('([^']+)'\)", c["datos"])
                if match:
                    c["internal_id"] = match.group(1)
        
        return contracts

    @auth_required
    async def get_billing_candidates(self) -> List[Dict[str, Any]]:
        data = await self.request_json("POST", self.url_billing_candidates, json={})
        if not data.get("result", False):
            raise CommandError(data)
        return data.get("data", [])

    @auth_required
    async def get_management_history(self, start: datetime, end: datetime) -> Dict[str, Any]:
        params = {
            "start": start.strftime("%d/%m/%Y"),
            "end": end.strftime("%d/%m/%Y"),
            "_": int(datetime.now().timestamp() * 1000)
        }
        data = await self.request_json("GET", self.url_management_history, params=params)
        return data

    @auth_required
    async def select_contract(self, contract_code: str) -> None:
        # TODO: Pendiente de desarrollo y pruebas exhaustivas cuando haya acceso 
        # a un usuario con varios contratos. Actualmente devuelve error genérico 
        # con el internal_id en algunas cuentas.
        resp = await self.request_json("POST", self.url_contract_selection, json={"suministro": contract_code})
        if not resp.get("success", False):
            self._logger.error(f"Select contract failed for {contract_code}: {resp}")
            raise InvalidContractError(contract_code)
        self._contract = contract_code
        self._logger.info(f"{self}: '{contract_code}' contract selected")

    @auth_required
    async def get_measure(self) -> Measure:
        self._logger.debug("Requesting data.")
        end_today = datetime.now().strftime("%d/%m/%Y")
        start_yesterday = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
        data = await self.request_json(
            "GET", 
            self.url_measure, 
            params={"start": start_yesterday, "end": end_today}
        )
        try:
            measure = Measure(
                accumulate=parsers.convert_str_comma_to_float(data["table"][-1]["Lectura"]),
                instant=parsers.convert_str_comma_to_float(data["table"][-1]["Consumo"]),
            )
        except (KeyError, ValueError, IndexError) as e:
            raise InvalidData(data) from e
        return measure

    async def get_historical_consumption(self, start: datetime, end: datetime) -> HistoricalConsumption:
        return await self._get_historical_consumption(start, end)

    async def _get_historical_consumption(self, start: datetime, end: datetime) -> HistoricalConsumption:
        start, end = min(start, end), max(start, end)
        data = await self.request_json(
            "GET", 
            self.url_consumption, 
            params={
                "start": start.strftime("%d/%m/%Y"),
                "end": end.strftime("%d/%m/%Y")
            }
        )
        ret = parsers.parse_historical_consumption(data)
        ret.consumptions = [x for x in ret.consumptions if x.start >= start and x.end < end]
        return ret

    def __repr__(self):
        return f"<globalomnium.Client username={self.username}, contract={self._contract}>"


class ClientError(Exception): pass
class RequestFailedError(ClientError): pass
class CommandError(ClientError): pass
class InvalidData(ClientError): pass
class InvalidContractError(ClientError): pass


async def get_session():
    return aiohttp.ClientSession()

async def get_credentials():
    return {"username": "user", "password": "pass"}
