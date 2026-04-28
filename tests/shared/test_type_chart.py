import pytest
from shared.type_chart import get_effectiveness, get_matchups


class TestGetEffectiveness:
    def test_neutral(self):
        assert get_effectiveness(["normal"], ["normal"]) == 1.0

    def test_immune(self):
        assert get_effectiveness(["normal"], ["ghost"]) == 0.0

    def test_super_effective(self):
        assert get_effectiveness(["fire"], ["grass"]) == 2.0

    def test_not_very_effective(self):
        assert get_effectiveness(["fire"], ["water"]) == 0.5

    def test_dual_type_multiplicative(self):
        # Rock vs Fire/Flying = 2× (rock>fire) × 2× (rock>flying) = 4×
        assert get_effectiveness(["rock"], ["fire", "flying"]) == 4.0

    def test_ground_vs_flying_immune(self):
        # Ground vs Flying = 0×
        assert get_effectiveness(["ground"], ["flying"]) == 0.0

    def test_ground_vs_fire_flying(self):
        # Ground vs Fire/Flying: 2× (vs fire) × 0× (vs flying) = 0×
        assert get_effectiveness(["ground"], ["fire", "flying"]) == 0.0


class TestGetMatchups:
    def test_charizard_rock_4x(self):
        m = get_matchups(["fire", "flying"])
        assert m["rock"] == 4.0

    def test_charizard_ground_immune(self):
        m = get_matchups(["fire", "flying"])
        assert m["ground"] == 0.0

    def test_charizard_water_2x(self):
        m = get_matchups(["fire", "flying"])
        assert m["water"] == 2.0

    def test_charizard_electric_2x(self):
        m = get_matchups(["fire", "flying"])
        assert m["electric"] == 2.0

    def test_charizard_fire_half(self):
        m = get_matchups(["fire", "flying"])
        assert m["fire"] == 0.5

    def test_returns_all_18_types(self):
        m = get_matchups(["normal"])
        assert len(m) == 18

    def test_matchups_grouping_weaknesses(self):
        m = get_matchups(["fire", "flying"])
        weaknesses = {t for t, v in m.items() if v > 1}
        assert "rock" in weaknesses
        assert "water" in weaknesses
        assert "electric" in weaknesses

    def test_matchups_grouping_immunities(self):
        m = get_matchups(["fire", "flying"])
        immunities = {t for t, v in m.items() if v == 0}
        assert "ground" in immunities
