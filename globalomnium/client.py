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
import functools
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import aiohttp

from . import parsers
from .go_types import HistoricalConsumption

#_BASE_URL = "https://www.aguasdevalencia.es/VirtualOffice"
_BASE_URL = "https://www.globalomnium.com/VirtualOffice"

_CONTRACTS_ENDPOINT = f"{_BASE_URL}/Secure/action_getSuministros/"
_CONTRACT_DETAILS_ENDPOINT = f"{_BASE_URL}/Secure/action_getSuministro/" # Not working at the moment
_CONTRACT_SELECTION_ENDPOINT = f"{_BASE_URL}/Secure/action_setSuministroActivo/" # Not tested
_LOGIN_ENDPOINT = f"{_BASE_URL}/action_Login/"
_MEASURE_ENDPOINT = (
    f"{_BASE_URL}/Secure/action_getDatosLecturaHorariaEntreFechas"
    "?start={start:%d/%m/%y}"
    "&end={end:%d/%m/%y}"
)

#
# URLs reviewed on 2024-05-16
#
_CONSUMPTION_PERIOD_ENDPOINT = (
    f"{_BASE_URL}/Secure/action_getDatosLecturaHorariaEntreFechas"
#    f"{_BASE_URL}/action_getHistorialLecturasWmtM/"
#    # "{start:%d-%m-%Y}/"
#    # "{end:%d-%m-%Y}/"
    "?start={start:%d/%m/%y}"
    "&end={end:%d/%m/%y}"
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


@dataclasses.dataclass
class Measure:
    accumulate: int
    instant: float

    def asdict(self) -> Dict[str, Union[int, float]]:
        return dataclasses.asdict(self)


class Client:
    _HEADERS = {
        "Accept": "*/*",
        "User-Agent": "py-globalomnium/2023.12.1",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
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

        self._login_ts: Optional[datetime] = None

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

    async def request_json(
        self, method: str, url: str, encoding: str = "utf-8", **kwargs
    ) -> Dict[Any, Any]:
        buff = await self.request_bytes(method, url, **kwargs)
        data = json.loads(buff.decode(encoding))
        return data

    async def request_bytes(self, method: str, url: str, **kwargs) -> bytes:
        resp = await self._request(method, url, **kwargs)
        buff = await resp.content.read()
        return buff

    async def _request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        headers = kwargs.get("headers", {})
        headers.update(self._HEADERS)
        kwargs["headers"] = headers

        resp = await self._sess.request(method, url, **kwargs)
        if resp.status != 200:
            raise RequestFailedError(resp)

        return resp

    async def login(self) -> None:
        """
        {
        "result": true,
        "error": "",
        "redirectURL": "/VirtualOffice/Secure/action_login"
        }
        """
        login_payload = "login="+ self.username +"&pass="+ self.password + "&remember=true" + "&suministro="


        #data = await self.request_json("POST", _LOGIN_ENDPOINT, data=login_payload) #cambiar entre request_json y _request
        data = await self._request("POST", _LOGIN_ENDPOINT, data=login_payload) #cambiar entre request_json y _request
        if not isinstance(data, dict):
            raise InvalidData(data)

        if data.get("result", "false") != True:
            raise CommandError(data)

        self._login_ts = datetime.now()

    # Desconozco como está funcionando la parte de los contratos así que la comento para descartar errores
    #    if self._contract:
    #        await self.select_contract(self._contract)

        self._logger.info(f"{self}: successful authentication")


    @auth_required
    async def get_contract_details(self) -> Dict[str, Any]:
        """
        {
            "result": true,
            "data": "\r\n
                    \u003cscript src=\"/bundles/account-form?v=91246\"\u003e\u003c/script\u003e\r\n
                    \r\n
                    \u003cscript\u003e\r\n
                    var DatoValido = \"Introduzca un dato válido\";\r\n
                    var AnadirTelfContacto = \"Añadir teléfono\";\r\n
                    \r\n
                    \r\n
                    var codEstadoFactMensual = \"\";\r\n
                    var poblacion = \"1200@010@VAL\u0026#200;NCIA                                \";\r\n
                    var referencia = \"00000000/000\";\r\n
                    var email = \"usuario@dominio.com\";\r\n
                    var nombre = \"MI NOMBRE\";\r\n
                    var ape1 = \"PRIMER APELLIDO\";\r\n
                    var ape2 = \"SEGUNDO APELLIDO\";\r\n
                    var documento = \"48594742C\";\r\n
                    var telefono = \"625966487\";\r\n
                    var descPeriodoFacturacion = \"BIMESTRAL\";\r\n
                    var codSuministro = \"...\";\r\n
                    \u003c/script\u003e\r\n\u003cstyle type=\"text/css\"\u003e\r\n
                    ...
                    \u003c/style\u003e\r\n
                    \u003c!-- INICIO / MODAL Suministro --\u003e\r\n
                    ...
                    \u003ch4 class=\"modal-title\"\u003eDatos del suministro: C/AAAAA BBBBBB CCCCC, 0, ABC, 132                      . VAL\u0026#200;NCIA                                 (VALENCIA                      )\u003c/h4\u003e\r\n
                    \u003c/div\u003e\r\n
                    \u003cdiv class=\"modal-body\"\u003e\r\n
                    \u003ch2\u003eDatos del suministro\u003c/h2\u003e\r\n
                    \u003cform\u003e\r\n
                    \u003cdiv class=\"row\"\u003e\r\n
                    \r\n
                    \u003cdiv class=\"form-group\"\u003e\r\n
                    \u003cdiv class=\"col-md-4\"\u003e\r\n
                    \u003clabel\u003eReferencia\u003c/label\u003e\r\n
                    \u003cinput type=\"text\" maxlength=\"100\" class=\"form-control\" value=\"00000000/000\" disabled=\"disabled\"\u003e\r\n
                    \u003c/div\u003e\r\n
                    \u003cdiv class=\"col-md-4\"\u003e\r\n
                    \u003clabel\u003eFecha de contrataci\u0026#243;n\u003c/label\u003e\r\n
                    \u003cinput type=\"text\" maxlength=\"100\" class=\"form-control\" value=\"01/01/2000\" disabled=\"disabled\"\u003e\r\n
                    \r\n
                    \u003c/div\u003e\r\n
                    \u003cdiv class=\"col-md-4\"\u003e\r\n
                    \u003clabel\u003eTipo\u003c/label\u003e\r\n
                    \u003cinput type=\"text\" maxlength=\"100\" class=\"form-control\" value=\"Contador Simple     \" disabled=\"disabled\"\u003e\r\n
                    \u003c/div\u003e\r\n 
                    \u003c/div\u003e\r\n
                    \u003cdiv class=\"form-group\"\u003e\r\n
                    \u003cdiv class=\"col-md-3\"\u003e\r\n
                    \u003clabel\u003eCalibre contador\u003c/label\u003e\r\n
                    \u003cinput type=\"text\" maxlength=\"100\" class=\"form-control\" value=\"015 mm\" disabled=\"disabled\"\u003e\r\n
                    \u003c/div\u003e\r\n
                    \u003cdiv class=\"col-md-3\"\u003e\r\n
                    \u003clabel\u003eUso\u003c/label\u003e\r\n
                    \u003cinput type=\"text\" maxlength=\"100\" class=\"form-control\" value=\"DOMESTICO                \" disabled=\"disabled\"\u003e\r\n
                    \u003c/div\u003e\r\n
                    \u003cdiv class=\"col-md-3\"\u003e\r\n
                    \u003clabel\u003eDestino\u003c/label\u003e\r\n
                    \u003cinput type=\"text\" maxlength=\"100\" class=\"form-control\" value=\"Normal                        \" disabled=\"disabled\"\u003e\r\n
                    \u003c/div\u003e\r\n
                    \u003cdiv class=\"col-md-3\"\u003e\r\n
                    \u003clabel\u003eEmplazamiento\u003c/label\u003e\r\n
                    \u003cinput type=\"text\" maxlength=\"100\" class=\"form-control\" value=\"BATERIA             \" disabled=\"disabled\"\u003e\r\n
                    \r\n
                    \u003c/div\u003e\r\n
                    \u003c/div\u003e\r\n
                    \u003cdiv class=\"form-group\"\u003e\r\n
                    \u003cdiv class=\"col-md-6\"\u003e\r\n
                    \u003clabel\u003eDirecci\u0026#243;n\u003c/label\u003e\r\n
                    \u003cinput type=\"text\" maxlength=\"100\" class=\"form-control\" value=\"C/AAAAA BBBBBB CCCCC, 0, ABC, 132           \" disabled=\"disabled\"\u003e\r\n
                    \u003c/div\u003e\r\n
                    \u003cdiv class=\"col-md-6\"\u003e\r\n
                    \u003clabel\u003ePoblaci\u0026#243;n\u003c/label\u003e\r\n
                    \u003cinput type=\"text\" maxlength=\"100\" class=\"form-control\" value=\"VAL\u0026#200;NCIA                                \" disabled=\"disabled\"\u003e\r\n
                    \u003c/div\u003e\r\n
                    \u003c/div\u003e\r\n
                    \u003c/div\u003e\r\n
                    \r\n
                    \u003c/form\u003e\r\n
                    \u003chr /\u003e\r\n
                    \r\n
                    \u003cdiv class=\"row\"\u003e\r\n
                    \u003cdiv class=\"form-group\"\u003e\r\n
                    \u003cdiv class=\"col-md-12\"\u003e\r\n
                    \u003ch2\u003eDatos generales\u003c/h2\u003e\r\n
                    \u003c/div\u003e\r\n
                    \r\n
                    \u003c/div\u003e\r\n
                    \r\n
                    \u003cdiv class=\"form-group\"\u003e\r\n
                    \u003cdiv class=\"col-md-6\"\u003e\r\n
                    \u003cform\u003e\r\n
                    \u003clabel\u003eEm@il \u003c/label\u003e\r\n
                    \u003cinput id=\"frm_sol_email\" value=\"USUARIO@DOMINIO.COM\" name=\"frm_sol_email\" required disabled=\"disabled\" type=\"email\" class=\"form-control\" maxlength=\"110\"\u003e\r\n
                    \u003c/form\u003e\r\n
                    ...
                    \u003ch2\u003eDirecci\u0026#243;n de env\u0026#237;o postal\u003c/h2\u003e\r\n
                    ...
                    \u003ch2\u003eCuenta bancaria\u003c/h2\u003e\r\n
                    ...
                    \u003clabel\u003eTitular *\u003c/label\u003e
                    \u003cinput type=\"text\" value=\"MI NOMPRE PRIMER APELLIDO SEGUNDO APELLIDO" maxlength=\"100\" class=\"form-control disabled\" disabled=\"disabled\"\u003e\r\n
                    \u003clabel\u003eCuenta bancaria *\u003c/label\u003e\r\n
                    \u003cinput type=\"text\" value=\"ES00/0000/0000/00/0000******\" data-msg-required=\"Por favor rellene el campo\" class=\"form-control\" style=\"text-transform: uppercase\" data-original=\"ES05/0182/5020/29/0201******\"\r\n
                    ...
                    u003c!-- FIN / MODAL Suministro --\u003e"
        }
        """
        data = await self.request_json("GET", _CONTRACT_DETAILS_ENDPOINT)
        if not data.get("codContrato", False):
            raise InvalidData(data)

        return data

    @auth_required
    async def get_contracts(self) -> List[Dict[str, Any]]:
        """
        {
        "data": [
            {
            "referencia": "00000000/000",
            "direccion": "C/AAAAA BBBBBB CCCCC, 0, ABC, 132           ",
            "poblacion": "VALÈNCIA                                ",
            "estado": "Activo",
            "datos": "...",
            "tipo": "..."
            }
        ]
        }
        """
        current_timestamp = int(datetime.now().timestamp() * 1000)
        json_payload = json.dumps({"order": "asc", "_": str(current_timestamp)})
        data = await self.request_json("GET", _CONTRACTS_ENDPOINT, json=json_payload) #no tengo claro si hay que usar json= o data= en los argumentos
        if not data.get("result", False):
            raise CommandError(data)

        try:
            # return data["contratos"]
            return data  # en realidad el código "variable" del contrato va metido en medio de la cadena ["datos"]
        except KeyError:
            raise InvalidData(data)

# Desconozco como está funcionando la parte de los contratos así que la comento para descartar errores
#    @auth_required
#    async def select_contract(self, id: str) -> None:
#        resp = await self.request_json(
#            "GET", _CONTRACT_SELECTION_ENDPOINT + id
#        )  # para GO utiliza el Payload suministro=abcd124.....
#        if not resp.get("result", False):
#            raise InvalidContractError(id)
#
#        self._contract = id
#        self._logger.info(f"{self}: '{id}' contract selected")

    @auth_required
    async def get_measure(self) -> Measure:
        """
        {
        "result": true,
        "data": {
            "labels": [
            "22/12 00:00",
            "22/12 01:00"
            ],
            "datasets": [
            {
                "label": "Consumo litros",
                "data": [
                {
                    "title": "160,684",
                    "y": 0
                },
                {
                    "title": "160,684",
                    "y": 1
                }
                ]
            },
            {
                "label": "Lectura m3",
                "data": null
            }
            ]
        },
        "table": [
            {
            "Fecha": "/Date(1703199600000)/",
            "FechaString": "<span style='display:none'>202312220000 - </span>22/12/2023 0:00:00",
            "FechaDesde": null,
            "FechaHasta": null,
            "Periodo": null,
            "Consumo": "0",
            "TipoLectura": null,
            "Observacion": "22/12 00:00",
            "Lectura": "160,684"
            },
            {
            "Fecha": "/Date(1703203200000)/",
            "FechaString": "<span style='display:none'>202312220100 - </span>22/12/2023 1:00:00",
            "FechaDesde": null,
            "FechaHasta": null,
            "Periodo": null,
            "Consumo": "1",
            "TipoLectura": null,
            "Observacion": "22/12 01:00",
            "Lectura": "160,684"
            }
        ],
        "alarmas": ""
        }
        """

        self._logger.debug("Requesting data may take up to a minute.")

        end_today = datetime.now().strftime("%d/%m/%Y")
        start_yesterday = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
        payload = f"start={start_yesterday}&end={end_today}"

       # data = await self.request_json("GET", _MEASURE_ENDPOINT, data=payload) #cambiar entre request_json y _request
        data = await self._request("GET", _MEASURE_ENDPOINT, data=payload) #cambiar entre request_json y _request

        self._logger.debug(f"Got reply, raw data: {data!r}")

        try:
            measure = Measure(
                accumulate=int(
                    data["table"][-1]["Lectura"]
                ),  # accedo solo al último elemento para la lectura "instantanea"
                instant=float(
                    data["table"][-1]["Consumo"]
                ),  # accedo solo al último elemento para la lectura "instantanea"
            )

        except (KeyError, ValueError) as e:
            raise InvalidData(data) from e

        self._logger.info(f"{self}: Measure reading successful")
        return measure

    async def get_historical_consumption(
        self, start: datetime, end: datetime
    ) -> HistoricalConsumption:
        return await self._get_historical_consumption(start, end)


    @auth_required # este trozo de abajo también se puede quitar???
    async def _get_historical_generic_data(
        self, url_template: str, start: datetime, end: datetime
    ) -> Dict[Any, Any]:
        start = min([start, end])
        end = max([start, end])
        url = url_template.format(start=start, end=end)

        data = await self.request_json("GET", url, encoding="iso-8859-1")

        base_date = datetime(start.year, start.month, start.day)
        ret = parsers.parser_generic_historical_data(data, base_date)

        return ret # este trozo de arriba también se puede quitar???

    @auth_required
    async def _get_historical_consumption(
        self, start: datetime, end: datetime
    ) -> HistoricalConsumption:
        start = min([start, end])
        end = max([start, end])
        payload = f"start={start}&end={end}"

        #data = await self._request("GET", _CONSUMPTION_PERIOD_ENDPOINT, data=payload) #cambiar entre request_json y _request
        data = await self.request_json("GET", _CONSUMPTION_PERIOD_ENDPOINT, data=payload) #cambiar entre request_json y _request

        ret = parsers.parse_historical_consumption(data)
        ret.consumptions = [
            x for x in ret.consumptions if x.start >= start and x.end < end
        ]
        return ret


    def __repr__(self):
        return (
            f"<globalomnium.Client username={self.username}, contract={self._contract}>"
        )


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
