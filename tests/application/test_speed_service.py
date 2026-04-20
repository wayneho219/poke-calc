from domain.models.nature import NatureRegistry
from domain.models.stats import StatSet
from domain.models.pokemon import Pokemon
from application.calculator import StatCalculator
from application.speed_service import SpeedService

NEUTRAL = NatureRegistry.get_by_name("Hardy")

def make_pokemon(pid: int, base_speed: int) -> Pokemon:
    return Pokemon(
        id=pid, name_en=f"Mon{pid}", name_zh="測試", name_ja="テスト",
        base_stats=StatSet(hp=100, attack=100, defense=100, sp_attack=100, sp_defense=100, speed=base_speed),
        types=["normal"],
    )


svc = SpeedService(StatCalculator())


class TestSpeedService:
    def test_no_sp_needed_already_faster(self):
        # user base 100, target base 80 (both neutral)
        # user speed = 120, target speed = 100
        user   = make_pokemon(1, 100)
        target = make_pokemon(2, 80)
        result = svc.min_sp_to_outspeed(user, target)
        assert result.sp_needed == 0
        assert result.my_speed > result.target_speed

    def test_sp_needed_to_outspeed(self):
        # user base 80 → neutral speed = 100+sp
        # target base 100 → neutral speed = 120
        # Need 100+sp > 120 → sp >= 21
        user   = make_pokemon(1, 80)
        target = make_pokemon(2, 100)
        result = svc.min_sp_to_outspeed(user, target)
        assert result.sp_needed == 21
        assert result.my_speed == 121
        assert result.target_speed == 120

    def test_cannot_outspeed_returns_none(self):
        # user base 60, max speed = 112; target base 100, speed = 120
        user   = make_pokemon(1, 60)
        target = make_pokemon(2, 100)
        result = svc.min_sp_to_outspeed(user, target)
        assert result is None

    def test_equal_base_speed_same_nature(self):
        # Both base 100 neutral: user needs sp=1 to outspeed
        user   = make_pokemon(1, 100)
        target = make_pokemon(2, 100)
        result = svc.min_sp_to_outspeed(user, target)
        assert result.sp_needed == 1
        assert result.my_speed == 121

    def test_nature_aware_timid_vs_brave(self):
        from domain.models.nature import NatureRegistry
        import dataclasses
        # Timid user (×1.1 speed), base 80: speed = int((80+20+0)*1.1) = 110
        # Brave target (×0.9 speed), base 100: speed = int((100+20+0)*0.9) = 108
        # user already faster at sp=0
        timid = NatureRegistry.get_by_name("Timid")
        brave = NatureRegistry.get_by_name("Brave")
        user   = dataclasses.replace(make_pokemon(1, 80),  nature=timid)
        target = dataclasses.replace(make_pokemon(2, 100), nature=brave)
        result = svc.min_sp_to_outspeed(user, target)
        assert result is not None
        assert result.sp_needed == 0
        assert result.my_speed == 110
        assert result.target_speed == 108
