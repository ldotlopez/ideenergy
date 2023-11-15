from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


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
    desglosed: Dict[str, float] = field(default_factory=dict)


@dataclass
class HistoricalConsumption:
    periods: List[ConsumptionForPeriod] = field(default_factory=list)
    total: float = 0
    desglosed: Dict[str, float] = field(default_factory=dict)


@dataclass
class HistoricalGeneration:
    periods: List[PeriodValue] = field(default_factory=list)


@dataclass
class DemandAtInstant:
    dt: datetime
    value: float


@dataclass
class HistoricalPowerDemand:
    demands: List[DemandAtInstant] = field(default_factory=list)
