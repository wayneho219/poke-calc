import pytest
from domain.models.stats import StatSet, SPAllocation


class TestSPAllocation:
    def test_total_sums_all_fields(self):
        sp = SPAllocation(hp=10, attack=5, defense=3, sp_attack=0, sp_defense=8, speed=12)
        assert sp.total() == 38

    def test_default_total_is_zero(self):
        assert SPAllocation().total() == 0

    def test_validate_passes_within_limits(self):
        sp = SPAllocation(hp=32, speed=32, defense=2)
        assert sp.validate() is True

    def test_validate_fails_if_total_exceeds_66(self):
        sp = SPAllocation(hp=32, attack=32, defense=3)
        assert sp.validate() is False

    def test_validate_fails_if_single_stat_exceeds_32(self):
        sp = SPAllocation(hp=33)
        assert sp.validate() is False

    def test_validate_fails_if_negative(self):
        sp = SPAllocation(hp=-1)
        assert sp.validate() is False

    def test_validate_passes_at_exact_limits(self):
        sp = SPAllocation(hp=32, attack=32, defense=2)
        assert sp.total() == 66
        assert sp.validate() is True
