from dataclasses import dataclass
from typing import Optional
from domain.models.nature import BattleStat
from domain.models.pokemon import Pokemon
from application.calculator import StatCalculator


@dataclass(frozen=True)
class AttackInput:
    power: int
    attacker_atk: int
    is_physical: bool
    type_multiplier: float


@dataclass(frozen=True)
class SurvivalResult:
    sp_hp: int
    sp_def: int
    total_sp: int
    final_hp: int
    final_def: int
    survived: bool


class SurvivalService:

    SP_MAX = 32
    SP_TOTAL_MAX = 66

    def __init__(self, calculator: StatCalculator) -> None:
        self._calc = calculator

    def _damage(self, attack: AttackInput, def_final: int) -> int:
        return int((22 * attack.power * attack.attacker_atk / def_final / 50 + 2) * attack.type_multiplier)

    def _def_stat(self, attack: AttackInput) -> BattleStat:
        return BattleStat.DEFENSE if attack.is_physical else BattleStat.SP_DEFENSE

    def _def_base(self, pokemon: Pokemon, attack: AttackInput) -> int:
        return pokemon.base_stats.defense if attack.is_physical else pokemon.base_stats.sp_defense

    def _min_sp_def_for_hp(self, pokemon: Pokemon, hp_final: int, attack: AttackInput) -> Optional[int]:
        stat = self._def_stat(attack)
        for sp_def in range(0, self.SP_MAX + 1):
            def_final = self._calc.calc_stat(self._def_base(pokemon, attack), sp_def, pokemon.nature, stat)
            if self._damage(attack, def_final) < hp_final:
                return sp_def
        return None

    def optimize(self, pokemon: Pokemon, attack: AttackInput) -> tuple[SurvivalResult, SurvivalResult]:
        best_total = self.SP_TOTAL_MAX + 1
        candidates: list[SurvivalResult] = []
        stat = self._def_stat(attack)

        for sp_hp in range(0, self.SP_MAX + 1):
            hp_final = self._calc.calc_hp(pokemon.base_stats.hp, sp_hp)
            sp_def = self._min_sp_def_for_hp(pokemon, hp_final, attack)

            if sp_def is None or sp_hp + sp_def > self.SP_TOTAL_MAX:
                continue

            total = sp_hp + sp_def
            if total > best_total:
                continue

            def_final = self._calc.calc_stat(self._def_base(pokemon, attack), sp_def, pokemon.nature, stat)
            result = SurvivalResult(sp_hp, sp_def, total, hp_final, def_final, True)

            if total < best_total:
                best_total = total
                candidates = [result]
            else:
                candidates.append(result)

        if not candidates:
            return (
                SurvivalResult(0, 0, 0, self._calc.calc_hp(pokemon.base_stats.hp, 0), 0, False),
                SurvivalResult(0, 0, 0, self._calc.calc_hp(pokemon.base_stats.hp, 0), 0, False),
            )

        prefer_hp  = max(candidates, key=lambda r: r.sp_hp)
        prefer_def = max(candidates, key=lambda r: r.sp_def)
        return prefer_hp, prefer_def
