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
from typing import Any

from .types import (
    ConsumptionForPeriod,
    DemandAtInstant,
    HistoricalConsumption,
    HistoricalGeneration,
    HistoricalPowerDemand,
    PeriodValue,
)


def parser_generic_historical_data(data, base_dt: datetime) -> dict[str, Any]:
    def _normalize(idx: int, item: dict | None) -> PeriodValue | None:
        if item is None:
            return None

        start = base_dt + timedelta(hours=idx)
        try:
            return PeriodValue(
                start=start, end=start + timedelta(hours=1), value=float(item["valor"])
            )
        except (KeyError, ValueError, TypeError):
            return None

    g = (_normalize(idx, item) for (idx, item) in enumerate(data["y"]["data"][0]))
    historical_values = [x for x in g if x is not None]

    return {
        # "accumulated": float(data["acumulado"]),
        # "accumulated-co2": float(data["acumuladoCO2"]),
        "historical": historical_values,
    }


def parse_historical_consumption(data) -> HistoricalConsumption:
    def list_to_dict(values, keys):
        return {keys[idx]: values[idx] for idx in range(len(values))}

    start = datetime.strptime(data[0]["fechaDesde"], "%d-%m-%Y").replace(
        hour=0, minute=0, second=0
    )

    period_names = data[0]["periodos"]

    ret = HistoricalConsumption(
        total=data[0]["total"],
        desglosed=list_to_dict(data[0]["totalesPeriodosTarifarios"], period_names),
    )

    for idx, value in enumerate(data[0]["valores"]):
        ret.periods.append(
            ConsumptionForPeriod(
                start=start + timedelta(hours=idx),
                end=start + timedelta(hours=idx + 1),
                value=value,
                desglosed=list_to_dict(
                    data[0]["valoresPeriodosTarifarios"][idx], period_names
                ),
            )
        )

    return ret


def parse_historical_generation(data) -> HistoricalGeneration:
    start = datetime.strptime(data["fechaPeriodo"], "%d-%m-%Y%H:%M:%S").replace(
        hour=0, minute=0, second=0
    )

    parsed = parser_generic_historical_data(data, start)

    return HistoricalGeneration(periods=parsed["historical"])


def parse_historical_power_demand_data(data) -> HistoricalPowerDemand:
    def _normalize_item(item: dict) -> DemandAtInstant:
        return DemandAtInstant(
            dt=datetime.strptime(item["name"], "%d/%m/%Y %H:%M"),
            value=item["y"],
        )

    potMaxMens = data["potMaxMens"]
    potMaxMens = list(itertools.chain.from_iterable([x for x in potMaxMens]))

    demands = [_normalize_item(x) for x in potMaxMens]
    demands = list(sorted(demands, key=lambda x: x.dt))

    return HistoricalPowerDemand(demands=demands)
