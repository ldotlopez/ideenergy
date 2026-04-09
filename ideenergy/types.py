# Copyright (C) 2021-2026 Luis López <luis@cuarentaydos.com>
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


from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Measure:
    accumulate: int
    instant: float


@dataclass
class PeriodValue:
    start: datetime
    end: datetime
    value: float


@dataclass
class ConsumptionForPeriod(PeriodValue):
    desglosed: dict[str, float] = field(default_factory=dict)


@dataclass
class HistoricalConsumption:
    periods: list[ConsumptionForPeriod] = field(default_factory=list)
    total: float = 0
    desglosed: dict[str, float] = field(default_factory=dict)


@dataclass
class InProgressConsumption:
    periods: list[PeriodValue] = field(default_factory=list)


@dataclass
class HistoricalGeneration:
    periods: list[PeriodValue] = field(default_factory=list)


@dataclass
class DemandAtInstant:
    dt: datetime
    value: float


@dataclass
class HistoricalPowerDemand:
    demands: list[DemandAtInstant] = field(default_factory=list)
