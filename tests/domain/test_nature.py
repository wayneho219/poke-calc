import pytest
from domain.models.nature import BattleStat, Nature, NatureRegistry, ALL_NATURES

ATK = BattleStat.ATTACK
DEF = BattleStat.DEFENSE
SPA = BattleStat.SP_ATTACK
SPD = BattleStat.SP_DEFENSE
SPE = BattleStat.SPEED


class TestNatureModifier:
    def test_boosted_stat_returns_1_1(self):
        jolly = NatureRegistry.get_by_name("Jolly")
        assert jolly.modifier(SPE) == 1.1

    def test_reduced_stat_returns_0_9(self):
        jolly = NatureRegistry.get_by_name("Jolly")
        assert jolly.modifier(SPA) == 0.9

    def test_neutral_stat_returns_1_0(self):
        jolly = NatureRegistry.get_by_name("Jolly")
        assert jolly.modifier(ATK) == 1.0

    def test_neutral_nature_all_stats_1_0(self):
        hardy = NatureRegistry.get_by_name("Hardy")
        for stat in BattleStat:
            assert hardy.modifier(stat) == 1.0


class TestNatureRegistry:
    def test_get_by_english_name(self):
        n = NatureRegistry.get_by_name("Jolly")
        assert n.name_en == "Jolly"

    def test_get_by_english_name_case_insensitive(self):
        n = NatureRegistry.get_by_name("jolly")
        assert n.name_en == "Jolly"

    def test_get_by_traditional_chinese(self):
        n = NatureRegistry.get_by_name("爽朗")
        assert n.name_en == "Jolly"

    def test_get_by_japanese(self):
        n = NatureRegistry.get_by_name("ようき")
        assert n.name_en == "Jolly"

    def test_get_by_unknown_raises(self):
        with pytest.raises(ValueError):
            NatureRegistry.get_by_name("InvalidNature")

    def test_find_by_boosted_speed(self):
        results = NatureRegistry.find_by_boosted(SPE)
        names = {n.name_en for n in results}
        assert names == {"Timid", "Hasty", "Jolly", "Naive"}

    def test_find_by_reduced_speed(self):
        results = NatureRegistry.find_by_reduced(SPE)
        names = {n.name_en for n in results}
        assert names == {"Brave", "Relaxed", "Quiet", "Sassy"}

    def test_find_by_stats_exact(self):
        results = NatureRegistry.find_by_stats(SPE, SPA)
        assert len(results) == 1
        assert results[0].name_en == "Jolly"

    def test_all_natures_count(self):
        assert len(ALL_NATURES) == 25

    def test_get_rash_by_chinese(self):
        n = NatureRegistry.get_by_name("浮躁")
        assert n.name_en == "Rash"
