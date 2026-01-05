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


import logging
import os
import random
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiohttp

from .client import Client, auth_required
from .types import HistoricalGeneration  # noqa: F401
from .types import HistoricalPowerDemand  # noqa: F401
from .types import (
    ConsumptionForPeriod,
    HistoricalConsumption,
    Measure,
)

LOGGER = logging.getLogger(__name__)

I_DE_ENERGY_DUMP_DIRECTORY = os.environ.get("I_DE_ENERGY_DUMP_DIRECTORY", "")
I_DE_ENERGY_DUMP = bool(I_DE_ENERGY_DUMP_DIRECTORY)
if I_DE_ENERGY_DUMP:
    I_DE_ENERGY_DUMP_BASE_PATH = Path(I_DE_ENERGY_DUMP_DIRECTORY)
else:
    I_DE_ENERGY_DUMP_DIRECTORY = None


class MockClient(Client):
    #
    # Requests
    #

    async def _request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        raise TypeError("This should not be called")

    async def request_bytes(self, method: str, url: str, **kwargs) -> bytes:
        raise TypeError("This should not be called")

    async def request_json(
        self, method: str, url: str, encoding: str = "utf-8", **kwargs
    ) -> dict[Any, Any]:
        raise TypeError("This should not be called")

    #
    # Methods
    #

    async def login(self) -> None:
        self._login_ts = datetime.now()

        if self._contract:
            await self.select_contract(self._contract)

    async def renew_session(self) -> dict:
        return {"total": "900", "usSes": "12345678901X12", "aviso": "15"}

    @auth_required
    async def is_icp_ready(self) -> bool:
        return True

    @auth_required
    async def get_contracts(self) -> dict:
        return {
            "success": True,
            "contratos": [
                {
                    "direccion": "xxxxxxxxxxxxxxxxxxxxxxx",
                    "cups": "ES0000000000000000AB",
                    "tipo": "A",
                    "tipUsoEnergiaCorto": "-",
                    "tipUsoEnergiaLargo": "-",
                    "estContrato": "Alta",
                    "codContrato": "123456789",
                    "esTelegestionado": True,
                    "presion": "1.00",
                    "fecUltActua": "01.01.1970",
                    "esTelemedido": False,
                    "tipSisLectura": "TG",
                    "estadoAlta": True,
                }
            ],
        }

    @auth_required
    async def get_contract_details(self) -> dict:
        return {
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

    @auth_required
    async def select_contract(self, contract_id: str) -> None:
        self._contract = contract_id

    @auth_required
    async def get_measure(self) -> Measure:
        data = {
            "valMagnitud": random.randint(0, 500),  # "158.64",
            "valInterruptor": "1",
            "valEstado": "09",
            "valLecturaContador": random.randint(0, 5_000),  # "43167",
            "codSolicitudTGT": "012345678901",
        }

        return Measure(
            accumulate=int(data["valLecturaContador"]),
            instant=float(data["valMagnitud"]),
        )

    @auth_required
    async def get_historical_consumption(
        self, start: datetime, end: datetime
    ) -> HistoricalConsumption:

        with preseed_random((start, end)) as rand:
            periods = [
                ConsumptionForPeriod(
                    start=dt,
                    end=dt + timedelta(hours=1),
                    value=rand.randint(0, 1000),
                    desglosed={},
                )
                for dt in datetime_range(start, end, step=timedelta(hours=1))
            ]

            return HistoricalConsumption(
                periods=periods, total=sum([x.value for x in periods]), desglosed={}
            )


def datetime_range(
    start: datetime, end: datetime, step: timedelta
) -> Iterator[datetime]:
    curr = start
    while curr < end:
        yield curr
        curr = curr + step


@contextmanager
def preseed_random(seed) -> Iterator[random.Random]:
    yield random.Random(repr(seed))
