from dataclasses import dataclass
from typing import Optional
from domain.models.nature import BattleStat
from domain.models.pokemon import Pokemon
from application.calculator import StatCalculator


@dataclass(frozen=True)
class SpeedResult:
    sp_needed: int
    my_speed: int
    target_speed: int


class SpeedService:

    def __init__(self, calculator: StatCalculator) -> None:
        self._calc = calculator

    def min_sp_to_outspeed(self, user: Pokemon, target: Pokemon) -> Optional[SpeedResult]:
        target_speed = self._calc.calc_stat(
            target.base_stats.speed, 0, target.nature, BattleStat.SPEED
        )
        for sp in range(0, 33):
            my_speed = self._calc.calc_stat(
                user.base_stats.speed, sp, user.nature, BattleStat.SPEED
            )
            if my_speed > target_speed:
                return SpeedResult(sp_needed=sp, my_speed=my_speed, target_speed=target_speed)
        return None
