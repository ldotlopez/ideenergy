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
import datetime
from typing import Dict


def parser_generic_historical_data(data, base_dt: datetime.datetime) -> Dict:
    def _normalize_historical_item(idx: int, item: Dict | None) -> Dict | None:
        if item is None:
            return None

        start = base_dt + datetime.timedelta(hours=idx)
        try:
            value = float(item["valor"])
        except (KeyError, ValueError, TypeError):
            value = None

        return {
            "start": start,
            "end": start + datetime.timedelta(hours=1),
            "value": value,
        }

    historical = data["y"]["data"][0]
    historical = [
        _normalize_historical_item(idx, item) for (idx, item) in enumerate(historical)
    ]
    historical = [x for x in historical if x is not None]

    return {
        "accumulated": float(data["acumulado"]),
        "accumulated-co2": float(data["acumuladoCO2"]),
        "historical": historical,
    }


def parse_historical_power_demand_data(data) -> Dict:
    def _normalize_power_spike_item(item: Dict):
        return {
            "dt": datetime.datetime.strptime(item["name"], "%d/%m/%Y %H:%M"),
            "value": item["y"],
        }

    assert data.get("resultado") == "correcto"

    potMaxMens = data["potMaxMens"]
    potMaxMens = list(itertools.chain.from_iterable([x for x in potMaxMens]))
    potMaxMens = [_normalize_power_spike_item(x) for x in potMaxMens]

    return potMaxMens
