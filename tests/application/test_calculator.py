from domain.models.nature import NatureRegistry, BattleStat
from domain.models.stats import StatSet, SPAllocation
from domain.models.pokemon import Pokemon
from application.calculator import StatCalculator

NEUTRAL = NatureRegistry.get_by_name("Hardy")
JOLLY   = NatureRegistry.get_by_name("Jolly")   # +Speed, -SpA

# Garchomp base stats
GARCHOMP_BASE = StatSet(hp=108, attack=130, defense=95, sp_attack=80, sp_defense=85, speed=102)


def make_garchomp(nature=NEUTRAL) -> Pokemon:
    return Pokemon(
        id=445, name_en="Garchomp", name_zh="烈咬陸鯊", name_ja="ガブリアス",
        base_stats=GARCHOMP_BASE, types=["dragon", "ground"], nature=nature,
    )


calc = StatCalculator()


class TestCalcHP:
    def test_no_sp(self):
        assert calc.calc_hp(108, 0) == 183   # 108 + 75 + 0

    def test_with_sp(self):
        assert calc.calc_hp(108, 10) == 193  # 108 + 75 + 10


class TestCalcStat:
    def test_neutral_no_sp(self):
        # int((102 + 20 + 0) * 1.0) = 122
        assert calc.calc_stat(102, 0, NEUTRAL, BattleStat.SPEED) == 122

    def test_jolly_speed_no_sp(self):
        # int((102 + 20 + 0) * 1.1) = int(134.2) = 134
        assert calc.calc_stat(102, 0, JOLLY, BattleStat.SPEED) == 134

    def test_jolly_sp_attack_reduced(self):
        # int((80 + 20 + 0) * 0.9) = int(90.0) = 90
        assert calc.calc_stat(80, 0, JOLLY, BattleStat.SP_ATTACK) == 90

    def test_floors_not_rounds(self):
        # int((102 + 20 + 4) * 1.1) = int(138.6) = 138
        assert calc.calc_stat(102, 4, JOLLY, BattleStat.SPEED) == 138


class TestCalcAll:
    def test_returns_statset_type(self):
        result = calc.calc_all(make_garchomp(JOLLY), SPAllocation())
        assert isinstance(result, StatSet)

    def test_hp_matches_calc_hp(self):
        result = calc.calc_all(make_garchomp(), SPAllocation(hp=8))
        assert result.hp == calc.calc_hp(108, 8)

    def test_attack_matches_calc_stat(self):
        result = calc.calc_all(make_garchomp(NEUTRAL), SPAllocation(attack=4))
        assert result.attack == calc.calc_stat(130, 4, NEUTRAL, BattleStat.ATTACK)

    def test_defense_matches_calc_stat(self):
        result = calc.calc_all(make_garchomp(NEUTRAL), SPAllocation(defense=4))
        assert result.defense == calc.calc_stat(95, 4, NEUTRAL, BattleStat.DEFENSE)

    def test_sp_attack_matches_calc_stat(self):
        result = calc.calc_all(make_garchomp(JOLLY), SPAllocation(sp_attack=4))
        assert result.sp_attack == calc.calc_stat(80, 4, JOLLY, BattleStat.SP_ATTACK)

    def test_sp_defense_matches_calc_stat(self):
        result = calc.calc_all(make_garchomp(NEUTRAL), SPAllocation(sp_defense=4))
        assert result.sp_defense == calc.calc_stat(85, 4, NEUTRAL, BattleStat.SP_DEFENSE)

    def test_speed_matches_calc_stat(self):
        result = calc.calc_all(make_garchomp(JOLLY), SPAllocation(speed=4))
        assert result.speed == calc.calc_stat(102, 4, JOLLY, BattleStat.SPEED)
