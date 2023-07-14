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


import itertools
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .types import ConsumptionForPeriod, HistoricalConsumption


def parser_generic_historical_data(data, base_dt: datetime) -> Dict:
    def _normalize_historical_item(idx: int, item: Optional[Dict]) -> Optional[Dict]:
        if item is None:
            return None

        start = base_dt + timedelta(hours=idx)
        try:
            value = float(item["valor"])
        except (KeyError, ValueError, TypeError):
            value = None

        return {
            "start": start,
            "end": start + timedelta(hours=1),
            "value": value,
        }

    historical = data["y"]["data"][0]
    historical = [
        _normalize_historical_item(idx, item) for (idx, item) in enumerate(historical)
    ]
    historical = [x for x in historical if x is not None]

    return {
        "accumulated": float(data["acumulado"]),
        # "accumulated-co2": float(data["acumuladoCO2"]),
        "historical": historical,
    }


def parse_historical_consumption(data) -> HistoricalConsumption:
    def list_to_dict(values, keys):
        return {keys[idx]: values[idx] for idx in range(len(values))}

    # CORREGIR, YA QUE EN GO EXISTE EL CAMPO FECHA DESDE PERO ESTA EN BLANCO, ESTA LA FEHA EN UN CAMPO STRING QUE HAY QUE DECODIFICAR
    start = datetime.strptime(table[0]["FechaDesde"], "%d-%m-%Y").replace(
        hour=0, minute=0, second=0
    )

    period_names = table[0]["Periodo"]

    ret = HistoricalConsumption(
        total=table[0]["Lectura"],
        # desglosed=list_to_dict(data[0]["totalesPeriodosTarifarios"], period_names),
    )

    for idx, value in enumerate(tabla[0]["Lectura"]):
        ret.consumptions.append(
            ConsumptionForPeriod(
                start=start + timedelta(hours=idx),
                end=start + timedelta(hours=idx + 1),
                value=value,
                # desglosed=list_to_dict(
                #     data[0]["valoresPeriodosTarifarios"][idx], period_names
                # ),
            )
        )

    return ret


# def parse_historical_power_demand_data(data) -> List[Dict]:
#     def _normalize_item(item: Dict):
#         return {
#             "dt": datetime.strptime(item["name"], "%d/%m/%Y %H:%M"),
#             "value": item["y"],
#         }
#
#     potMaxMens = data["potMaxMens"]
#     potMaxMens = list(itertools.chain.from_iterable([x for x in potMaxMens]))
#     potMaxMens = [_normalize_item(x) for x in potMaxMens]
#
#    return potMaxMens
