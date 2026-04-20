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

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from .go_types import ConsumptionForPeriod, HistoricalConsumption


def parser_generic_historical_data(data: Dict[str, Any], base_dt: datetime) -> Dict[str, Any]:
    def _normalize_historical_item(idx: int, item: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
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
        "historical": historical,
    }


def parse_historical_consumption(data: Dict[str, Any]) -> HistoricalConsumption:
    # Extract timestamp from the "Fecha" string (e.g., "/Date(1234567890000)/")
    timestamp_matches = re.findall(r'\d+', data["table"][0]["Fecha"])
    if not timestamp_matches:
        raise ValueError("Could not find timestamp in data['table'][0]['Fecha']")
    
    timestamp = int(timestamp_matches[0]) // 1000
    start = datetime.fromtimestamp(timestamp)

    first_reading = convert_str_comma_to_float(data["table"][0]["Lectura"])
    last_reading = convert_str_comma_to_float(data["table"][-1]["Lectura"])
    
    ret = HistoricalConsumption(
        total=round(last_reading - first_reading, 3),
    )

    for idx, value in enumerate(data["table"]):
        ret.consumptions.append(
            ConsumptionForPeriod(
                start=start + timedelta(hours=idx),
                end=start + timedelta(hours=idx + 1),
                value=convert_str_comma_to_float(value["Consumo"]) / 1000,
            )
        )

    return ret


def convert_str_comma_to_float(string: str) -> float:
    """Converts a string with comma as decimal separator to float."""
    try:
        return round(float(string.replace(",", ".")), 3)
    except (ValueError, TypeError):
        return 0.0
    